from datetime import timedelta
from decimal import Decimal

from django.db import models, transaction

from audit.services import create_audit_event
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference

from .models import ComunidadPatrimonial, Empresa, EstadoPatrimonial, ParticipacionPatrimonial, Socio


PARTICIPATION_TRANSFER_EVENT_TYPE = 'patrimonio.participacion.transfer_executed'


def _owner_filter(owner):
    if isinstance(owner, Empresa):
        return {'empresa_owner': owner}
    return {'comunidad_owner': owner}


def _resolve_participant(participant_type, participant_id):
    if participant_type == 'socio':
        try:
            participant = Socio.objects.get(pk=participant_id)
        except Socio.DoesNotExist as exc:
            raise ValueError('El socio destino indicado no existe.') from exc
        if not participant.activo:
            raise ValueError('La participacion destino requiere un socio activo.')
        return {'participante_socio': participant, 'participante_empresa': None}

    if participant_type == 'empresa':
        try:
            participant = Empresa.objects.get(pk=participant_id)
        except Empresa.DoesNotExist as exc:
            raise ValueError('La empresa destino indicada no existe.') from exc
        if participant.estado != EstadoPatrimonial.ACTIVE or not participant.participaciones_completas():
            raise ValueError('La participacion destino requiere una empresa activa con participaciones completas.')
        return {'participante_socio': None, 'participante_empresa': participant}

    raise ValueError('Tipo de participante no soportado.')


def _participant_key_from_payload(payload):
    if payload.get('participante_socio'):
        return ('socio', payload['participante_socio'].pk)
    return ('empresa', payload['participante_empresa'].pk)


def _effective_participations_for_owner(owner, effective_date):
    return (
        ParticipacionPatrimonial.objects.filter(**_owner_filter(owner), activo=True, vigente_desde__lte=effective_date)
        .filter(models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=effective_date))
    )


def _validate_transfer_result(owner, *, origin, target_rows, effective_date):
    existing_rows = [
        item
        for item in _effective_participations_for_owner(owner, effective_date).select_related(
            'participante_socio',
            'participante_empresa',
        )
        if item.pk != origin.pk
    ]
    total = sum((item.porcentaje for item in existing_rows), Decimal('0.00'))
    total += sum((item['porcentaje'] for item in target_rows), Decimal('0.00'))
    if total != Decimal('100.00'):
        raise ValueError('La transferencia debe conservar participaciones activas por 100.00 en la fecha efectiva.')

    participant_keys = []
    for item in existing_rows:
        participant_keys.append((item.participante_tipo, item.participante_id))
    for item in target_rows:
        participant_keys.append(_participant_key_from_payload(item))
    if len(participant_keys) != len(set(participant_keys)):
        raise ValueError('La transferencia no puede dejar participantes duplicados en el set vigente.')


@transaction.atomic
def execute_participation_transfer(
    *,
    owner,
    origin_participant_type,
    origin_participant_id,
    effective_date,
    transfers,
    reason,
    evidence_ref,
    actor_user=None,
    ip_address=None,
):
    reason = (reason or '').strip()
    if not reason:
        raise ValueError('La transferencia requiere motivo auditable.')
    if contains_sensitive_reference(reason):
        raise ValueError('El motivo de transferencia no puede contener URLs, correos, tokens ni credenciales.')
    if not evidence_ref or not evidence_ref.strip():
        raise ValueError('La transferencia requiere referencia de evidencia no sensible.')
    if not is_non_sensitive_reference(evidence_ref):
        raise ValueError('La evidencia de transferencia debe ser una referencia no sensible.')

    owner_participations = ParticipacionPatrimonial.objects.select_for_update().filter(**_owner_filter(owner))
    origin_filter = {
        'participante_socio_id': origin_participant_id if origin_participant_type == 'socio' else None,
        'participante_empresa_id': origin_participant_id if origin_participant_type == 'empresa' else None,
    }
    try:
        origin = (
            owner_participations.filter(**origin_filter, activo=True, vigente_desde__lte=effective_date)
            .filter(models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=effective_date))
            .get()
        )
    except ParticipacionPatrimonial.DoesNotExist as exc:
        raise ValueError('No existe una participacion origen vigente para la fecha efectiva.') from exc
    except ParticipacionPatrimonial.MultipleObjectsReturned as exc:
        raise ValueError('Existe mas de una participacion origen vigente; debe corregirse antes de transferir.') from exc

    if effective_date <= origin.vigente_desde:
        raise ValueError('La fecha efectiva debe ser posterior al inicio de la participacion origen.')

    if not transfers:
        raise ValueError('La transferencia requiere al menos un destino.')

    target_rows = []
    target_total = Decimal('0.00')
    target_keys = set()
    for transfer in transfers:
        participant = _resolve_participant(transfer['participante_tipo'], transfer['participante_id'])
        participant_key = _participant_key_from_payload(participant)
        if participant_key == (origin.participante_tipo, origin.participante_id):
            raise ValueError('El destino no puede ser el mismo participante origen.')
        if participant_key in target_keys:
            raise ValueError('La transferencia no puede repetir un participante destino.')
        target_keys.add(participant_key)
        percentage = Decimal(transfer['porcentaje'])
        target_total += percentage
        target_rows.append(
            {
                **participant,
                'porcentaje': percentage,
                'vigente_desde': effective_date,
                'vigente_hasta': None,
                'activo': True,
            }
        )

    if target_total != origin.porcentaje:
        raise ValueError('La suma de destinos debe igualar el porcentaje de la participacion origen.')

    _validate_transfer_result(owner, origin=origin, target_rows=target_rows, effective_date=effective_date)

    origin.vigente_hasta = effective_date - timedelta(days=1)
    origin.save(update_fields=['vigente_hasta', 'updated_at'])

    created_targets = []
    for row in target_rows:
        new_participation = ParticipacionPatrimonial(**_owner_filter(owner), **row)
        new_participation.full_clean()
        new_participation.save()
        created_targets.append(new_participation)

    event = create_audit_event(
        event_type=PARTICIPATION_TRANSFER_EVENT_TYPE,
        entity_type='participacion_patrimonial',
        entity_id=str(origin.pk),
        summary='Transferencia patrimonial ejecutada con conservacion de porcentaje total.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'owner_tipo': 'empresa' if isinstance(owner, Empresa) else 'comunidad',
            'owner_id': owner.pk,
            'origin_participation_id': origin.pk,
            'origin_participant_type': origin.participante_tipo,
            'origin_participant_id': origin.participante_id,
            'effective_date': effective_date.isoformat(),
            'reason': reason,
            'evidence_ref': evidence_ref.strip(),
            'target_participation_ids': [item.pk for item in created_targets],
            'target_count': len(created_targets),
            'transferred_percentage': str(target_total),
        },
    )

    return {'origin': origin, 'targets': created_targets, 'audit_event': event}
