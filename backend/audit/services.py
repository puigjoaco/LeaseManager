from django.db import transaction
from django.utils import timezone

from patrimonio.models import (
    ComunidadPatrimonial,
    Empresa,
    EstadoPatrimonial,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
)
from patrimonio.validators import normalize_rut

from .models import AuditEvent, ManualResolution


CURRENT_COMMUNITY_DESIGNATED_REPRESENTATIVE_RUT = '17366287-4'


def create_audit_event(
    *,
    event_type,
    entity_type,
    summary,
    severity='info',
    actor_user=None,
    actor_identifier='',
    entity_id='',
    metadata=None,
    request_id='',
    ip_address=None,
):
    return AuditEvent.objects.create(
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        event_type=event_type,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary,
        metadata=metadata or {},
        request_id=request_id,
        ip_address=ip_address,
    )


def _resolve_participants_from_metadata(metadata):
    participant_rows = metadata.get('participantes') or metadata.get('socios', [])
    resolved = []
    for item in participant_rows:
        participante_tipo = item.get('participante_tipo', 'socio')
        participante_rut = item.get('participante_rut') or item.get('socio_rut')
        if not participante_rut:
            raise ValueError('La resolucion no contiene participante_rut suficiente para recrear participaciones.')
        normalized_rut = normalize_rut(participante_rut)
        if participante_tipo == 'socio':
            try:
                socio = Socio.objects.get(rut=normalized_rut)
            except Socio.DoesNotExist as exc:
                raise ValueError(f'No existe socio canónico para RUT {participante_rut}.') from exc
            resolved.append(
                (
                    {
                        'participante_tipo': 'socio',
                        'participante_socio_obj': socio,
                        'participante_empresa_obj': None,
                    },
                    item,
                )
            )
        elif participante_tipo == 'empresa':
            try:
                empresa = Empresa.objects.get(rut=normalized_rut)
            except Empresa.DoesNotExist as exc:
                raise ValueError(f'No existe empresa canónica para RUT {participante_rut}.') from exc
            resolved.append(
                (
                    {
                        'participante_tipo': 'empresa',
                        'participante_socio_obj': None,
                        'participante_empresa_obj': empresa,
                    },
                    item,
                )
            )
        else:
            raise ValueError(f"participante_tipo no soportado en metadata: {participante_tipo}")
    if not resolved:
        raise ValueError('La resolucion no contiene participantes suficientes para recrear participaciones.')
    return resolved


def resolve_default_current_community_representative():
    representante = Socio.objects.filter(rut=normalize_rut(CURRENT_COMMUNITY_DESIGNATED_REPRESENTATIVE_RUT)).first()
    if not representante:
        raise ValueError('No existe el socio canónico Joaquín Puig Vittini para representar comunidades actuales.')
    return representante


@transaction.atomic
def resolve_migration_property_owner_manual_resolution(
    *,
    resolution,
    nombre_comunidad,
    representante_socio_id,
    representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
    participaciones=None,
    region='',
    actor_user=None,
    ip_address=None,
):
    if resolution.category != 'migration.propiedad.owner_manual_required':
        raise ValueError('La resolucion indicada no corresponde a owner manual de propiedad.')
    if resolution.status == ManualResolution.Status.RESOLVED:
        raise ValueError('La resolucion ya fue marcada como resuelta.')

    metadata = resolution.metadata or {}
    if metadata.get('candidate_owner_model') != 'comunidad':
        raise ValueError('Esta resolucion solo soporta crear comunidad patrimonial.')

    participant_rows = []
    if participaciones:
        participant_rows = [
            (
                {
                    'participante_tipo': item['participante_tipo'],
                    'participante_socio_obj': item.get('participante_socio_obj'),
                    'participante_empresa_obj': item.get('participante_empresa_obj'),
                },
                item,
            )
            for item in participaciones
        ]
    else:
        participant_rows = _resolve_participants_from_metadata(metadata)

    representante = Socio.objects.get(pk=representante_socio_id) if representante_socio_id else None
    if representante is None and representante_modo == ModoRepresentacionComunidad.DESIGNATED:
        representante = resolve_default_current_community_representative()
    if representante is None:
        raise ValueError('Debe indicar un representante para la comunidad.')
    active_participant_socio_ids = {
        resolved_participant['participante_socio_obj'].pk
        for resolved_participant, item in participant_rows
        if resolved_participant.get('participante_socio_obj')
        and item.get('activo', True)
    }
    if (
        representante_modo == ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT
        and representante.pk not in active_participant_socio_ids
    ):
        raise ValueError('El representante patrimonial debe pertenecer al set de participaciones socio activas.')

    comunidad = ComunidadPatrimonial.objects.create(
        nombre=nombre_comunidad,
        estado=EstadoPatrimonial.DRAFT,
    )
    RepresentacionComunidad.objects.create(
        comunidad=comunidad,
        modo_representacion=representante_modo,
        socio_representante=representante,
        vigente_desde=timezone.localdate(),
        activo=True,
    )
    participaciones = []
    for resolved_participant, item in participant_rows:
        participacion = ParticipacionPatrimonial(
            participante_socio=resolved_participant.get('participante_socio_obj'),
            participante_empresa=resolved_participant.get('participante_empresa_obj'),
            comunidad_owner=comunidad,
            porcentaje=item['porcentaje'],
            vigente_desde=item['vigente_desde'],
            vigente_hasta=item.get('vigente_hasta'),
            activo=item.get('activo', True),
        )
        participacion.full_clean()
        participaciones.append(participacion)
    ParticipacionPatrimonial.objects.bulk_create(participaciones)
    comunidad.estado = EstadoPatrimonial.ACTIVE
    comunidad.full_clean()
    comunidad.save(update_fields=['estado', 'updated_at'])

    property_code = str(metadata.get('codigo_propiedad') or metadata.get('codigo') or '').strip()
    if not property_code:
        raise ValueError('La resolucion no contiene codigo_propiedad/codigo suficiente para crear la propiedad.')

    canonical_region = metadata.get('region') or region or ''

    propiedad = Propiedad(
        rol_avaluo=metadata.get('rol_avaluo', ''),
        direccion=metadata.get('direccion', ''),
        comuna=metadata.get('comuna', ''),
        region=canonical_region,
        tipo_inmueble=metadata.get('tipo_inmueble', 'otro'),
        codigo_propiedad=property_code,
        estado=metadata.get('canonical_estado', 'activa'),
        comunidad_owner=comunidad,
    )
    propiedad.full_clean()
    propiedad.save()

    resolution.status = ManualResolution.Status.RESOLVED
    resolution.resolved_at = timezone.now()
    resolution.resolved_by = actor_user
    resolution.metadata = {
        **metadata,
        'resolved_canonical_comunidad_id': comunidad.pk,
        'resolved_canonical_property_id': propiedad.pk,
        'resolved_with': 'comunidad',
        'resolved_nombre_comunidad': nombre_comunidad,
        'resolved_representante_socio_id': representante.pk,
        'resolved_representante_modo': representante_modo,
        'resolved_participaciones_count': len(participaciones),
        'resolved_region': canonical_region,
    }
    resolution.save(update_fields=['status', 'resolved_at', 'resolved_by', 'metadata'])

    create_audit_event(
        event_type='audit.manual_resolution.resolved',
        entity_type='manual_resolution',
        entity_id=str(resolution.pk),
        summary='Se resolvio manualmente owner de propiedad legacy de migracion.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'resolution_category': resolution.category,
            'canonical_comunidad_id': comunidad.pk,
            'canonical_property_id': propiedad.pk,
        },
    )

    return {'comunidad': comunidad, 'propiedad': propiedad, 'resolution': resolution}
