from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import ManualResolution
from audit.services import resolve_migration_property_owner_manual_resolution
from contratos.models import Arrendatario, AvisoTermino, Contrato, ContratoPropiedad, EstadoAvisoTermino, PeriodoContractual
from operacion.models import CuentaRecaudadora, MandatoOperacion
from migration.transformers import CURRENT_COMMUNITY_DESIGNATED_REPRESENTATIVE_RUT, DEFAULT_LEGACY_PARTICIPATION_START_DATE
from patrimonio.models import (
    ComunidadPatrimonial,
    Empresa,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
)
from patrimonio.validators import normalize_rut


@dataclass
class ImportReport:
    created: dict[str, int] = field(default_factory=dict)
    updated: dict[str, int] = field(default_factory=dict)
    skipped: dict[str, list[dict]] = field(default_factory=dict)

    def bump(self, bucket: str, key: str):
        store = getattr(self, bucket)
        store[key] = store.get(key, 0) + 1

    def add_skip(self, key: str, payload: dict):
        self.skipped.setdefault(key, []).append(payload)


LEGACY_CONTRACT_STATE_MAP = {
    'activo': 'vigente',
    'vigente': 'vigente',
    'pendiente': 'pendiente_activacion',
    'borrador': 'pendiente_activacion',
    'futuro': 'futuro',
    'finalizado': 'finalizado',
    'terminado': 'finalizado',
    'terminado_anticipadamente': 'terminado_anticipadamente',
    'cancelado': 'cancelado',
}

CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER = '8240452907'

EXPECTED_CURRENT_MIGRATION_FINAL_STATE = {
    'comunidades': 16,
    'participaciones_comunidad': 70,
    'mandatos': 66,
    'contratos': 56,
    'periodos': 748,
    'manual_resolutions_abiertas': 0,
}

EXPECTED_CURRENT_MIGRATION_EMPTY_STATE = {
    'socios': 0,
    'empresas': 0,
    'comunidades': 0,
    'participaciones_comunidad': 0,
    'participaciones_empresa': 0,
    'propiedades': 0,
    'cuentas_recaudadoras': 0,
    'mandatos': 0,
    'arrendatarios': 0,
    'contratos': 0,
    'periodos': 0,
    'manual_resolutions_abiertas': 0,
    'manual_resolutions_resueltas': 0,
}


def derive_effective_code(propiedad):
    raw = ''.join(character for character in str(propiedad.codigo_propiedad) if character.isdigit())
    if not raw:
        return None
    return raw[-3:].zfill(3)


def resolve_unique_active_mandate(propiedad):
    mandates = list(MandatoOperacion.objects.filter(propiedad=propiedad, estado='activa'))
    if len(mandates) == 1:
        return mandates[0]
    return None


def safe_normalize_rut(report, bucket, item, entity_label):
    try:
        return normalize_rut(item['rut'])
    except (KeyError, ValidationError):
        report.add_skip(
            bucket,
            {
                'legacy_id': item.get('legacy_id', 'unknown'),
                'reason': f'El {entity_label} legacy no tiene un RUT valido y no se puede importar de forma segura.',
            },
        )
        return None


def missing_required_values(item, required_fields):
    missing = []
    for field in required_fields:
        value = item.get(field)
        if value is None:
            missing.append(field)
        elif isinstance(value, str) and not value.strip():
            missing.append(field)
    return missing


def upsert_manual_resolution(*, category, scope_type, scope_reference, summary, metadata):
    existing = ManualResolution.objects.filter(
        category=category,
        scope_type=scope_type,
        scope_reference=scope_reference,
    ).first()
    if existing and existing.status in [ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW]:
        existing.summary = summary
        existing.metadata = metadata
        existing.save(update_fields=['summary', 'metadata'])
        return False
    if existing and existing.status == ManualResolution.Status.RESOLVED:
        return None

    ManualResolution.objects.create(
        category=category,
        scope_type=scope_type,
        scope_reference=scope_reference,
        summary=summary,
        metadata=metadata,
    )
    return True


def sync_migration_manual_resolutions(bundle, report):
    created = 0
    updated = 0

    blocked_contracts_by_property = {}
    for item in report.skipped.get('contratos_candidates', []):
        property_legacy_id = item.get('property_legacy_id')
        if not property_legacy_id:
            continue
        blocked_contracts_by_property.setdefault(property_legacy_id, []).append(item.get('legacy_id'))

    for item in bundle.get('unresolved', {}).get('propiedades_sin_owner', []):
        created_now = upsert_manual_resolution(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference=str(item['legacy_id']),
            summary='Propiedad legacy multipropietario sin owner canónico seguro.',
            metadata={
                **item,
                'blocked_contract_legacy_ids': blocked_contracts_by_property.get(item['legacy_id'], []),
            },
        )
        if created_now is True:
            created += 1
        elif created_now is False:
            updated += 1

    for item in report.skipped.get('arrendatarios', []):
        created_now = upsert_manual_resolution(
            category='migration.arrendatario.invalid_rut',
            scope_type='legacy_arrendatario',
            scope_reference=str(item['legacy_id']),
            summary='Arrendatario legacy sin RUT válido; requiere resolución manual.',
            metadata=item,
        )
        if created_now is True:
            created += 1
        elif created_now is False:
            updated += 1

    for item in report.skipped.get('contratos_candidates', []):
        if 'dia_pago_mensual' not in item.get('reason', ''):
            continue
        created_now = upsert_manual_resolution(
            category='migration.contrato.missing_dia_pago',
            scope_type='legacy_contrato',
            scope_reference=str(item['legacy_id']),
            summary='Contrato legacy sin dia_pago_mensual; requiere resolución manual.',
            metadata=item,
        )
        if created_now is True:
            created += 1
        elif created_now is False:
            updated += 1

    return {'created': created, 'updated': updated}


def resolve_current_community_admin():
    return Socio.objects.filter(rut=normalize_rut(CURRENT_COMMUNITY_DESIGNATED_REPRESENTATIVE_RUT)).first()


def resolve_current_community_account():
    return CuentaRecaudadora.objects.filter(numero_cuenta=CURRENT_COMMUNITY_RECAUDADORA_ACCOUNT_NUMBER).first()


def load_resolved_property_map():
    return {scope_reference: data['propiedad'] for scope_reference, data in load_resolved_property_context().items()}


def load_resolved_property_context():
    property_map = {}
    resolutions = ManualResolution.objects.filter(
        category='migration.propiedad.owner_manual_required',
        status=ManualResolution.Status.RESOLVED,
    )
    for resolution in resolutions:
        property_id = resolution.metadata.get('resolved_canonical_property_id') if resolution.metadata else None
        if not property_id:
            continue
        propiedad = Propiedad.objects.filter(pk=property_id).first()
        if not propiedad:
            continue
        property_map[resolution.scope_reference] = {
            'propiedad': propiedad,
            'metadata': resolution.metadata or {},
        }
    return property_map


def resolve_current_community_manual_resolutions(*, actor_user=None, ip_address=None):
    resolved = 0
    skipped = []
    representative = resolve_current_community_admin()
    if representative is None:
        raise ValueError('No existe el socio canónico Joaquín Puig Vittini para resolver comunidades actuales.')

    resolutions = ManualResolution.objects.filter(
        category='migration.propiedad.owner_manual_required',
        status=ManualResolution.Status.OPEN,
    ).order_by('scope_reference')

    for resolution in resolutions:
        metadata = resolution.metadata or {}
        if metadata.get('candidate_owner_model') != 'comunidad':
            skipped.append(
                {
                    'scope_reference': resolution.scope_reference,
                    'reason': 'candidate_owner_model no soportado para auto-resolución.',
                }
            )
            continue
        if not (metadata.get('participantes') or metadata.get('socios')):
            skipped.append(
                {
                    'scope_reference': resolution.scope_reference,
                    'reason': 'La metadata no contiene participantes suficientes para auto-resolución.',
                }
            )
            continue
        nombre_comunidad = metadata.get('direccion') or f"Comunidad {metadata.get('codigo') or resolution.scope_reference}"
        resolve_migration_property_owner_manual_resolution(
            resolution=resolution,
            nombre_comunidad=nombre_comunidad,
            representante_socio_id=representative.pk,
            representante_modo=ModoRepresentacionComunidad.DESIGNATED,
            region=metadata.get('region', ''),
            actor_user=actor_user,
            ip_address=ip_address,
        )
        resolved += 1

    return {'resolved': resolved, 'skipped': skipped}


def collect_migration_state_snapshot():
    return {
        'socios': Socio.objects.count(),
        'empresas': Empresa.objects.count(),
        'comunidades': ComunidadPatrimonial.objects.count(),
        'participaciones_comunidad': ParticipacionPatrimonial.objects.filter(comunidad_owner__isnull=False).count(),
        'participaciones_empresa': ParticipacionPatrimonial.objects.filter(empresa_owner__isnull=False).count(),
        'propiedades': Propiedad.objects.count(),
        'cuentas_recaudadoras': CuentaRecaudadora.objects.count(),
        'mandatos': MandatoOperacion.objects.count(),
        'arrendatarios': Arrendatario.objects.count(),
        'contratos': Contrato.objects.count(),
        'periodos': PeriodoContractual.objects.count(),
        'manual_resolutions_abiertas': ManualResolution.objects.filter(
            status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW]
        ).count(),
        'manual_resolutions_resueltas': ManualResolution.objects.filter(status=ManualResolution.Status.RESOLVED).count(),
    }


def compare_migration_state(snapshot, *, expected):
    mismatches = {}
    for key, expected_value in expected.items():
        actual_value = snapshot.get(key)
        if actual_value != expected_value:
            mismatches[key] = {
                'expected': expected_value,
                'actual': actual_value,
            }
    return {
        'ok': not mismatches,
        'expected': expected,
        'actual': snapshot,
        'mismatches': mismatches,
    }


def validate_current_migration_state(snapshot, *, expected=None):
    return compare_migration_state(
        snapshot,
        expected=expected or EXPECTED_CURRENT_MIGRATION_FINAL_STATE,
    )


def validate_current_migration_empty_state(snapshot):
    return compare_migration_state(
        snapshot,
        expected=EXPECTED_CURRENT_MIGRATION_EMPTY_STATE,
    )


def run_current_migration_flow(bundle):
    pass_1 = import_bundle(bundle)
    community_resolution = resolve_current_community_manual_resolutions()
    pass_2 = import_bundle(bundle)
    pass_3 = import_bundle(bundle)
    final_state = collect_migration_state_snapshot()
    validation = validate_current_migration_state(final_state)
    return {
        'pass_1': {'created': pass_1.created, 'updated': pass_1.updated, 'skipped': pass_1.skipped},
        'community_resolution': community_resolution,
        'pass_2': {'created': pass_2.created, 'updated': pass_2.updated, 'skipped': pass_2.skipped},
        'pass_3': {'created': pass_3.created, 'updated': pass_3.updated, 'skipped': pass_3.skipped},
        'final_state': final_state,
        'validation': validation,
    }


def sync_bundle_participaciones(*, bundle_participaciones, socio_map, empresa_map, comunidad_map, report):
    imported_owner_ids = defaultdict(set)
    retained_participation_ids = defaultdict(set)

    for item in bundle_participaciones:
        participant_kind = item.get('participante_kind', 'socio')
        participant_legacy_id = item.get('participante_legacy_id') or item.get('socio_legacy_id')
        participant_socio = socio_map.get(participant_legacy_id) if participant_kind == 'socio' else None
        participant_empresa = empresa_map.get(participant_legacy_id) if participant_kind == 'empresa' else None
        if participant_kind == 'socio' and not participant_socio:
            report.add_skip(
                'participaciones',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': 'No se encontro el socio canónico para la participación.',
                    'participante_legacy_id': participant_legacy_id,
                },
            )
            continue
        if participant_kind == 'empresa' and not participant_empresa:
            report.add_skip(
                'participaciones',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': 'No se encontro la empresa canónica participante para la participación.',
                    'participante_legacy_id': participant_legacy_id,
                },
            )
            continue
        if participant_kind not in {'socio', 'empresa'}:
            report.add_skip(
                'participaciones',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': f"participante_kind no soportado para importación: {participant_kind}",
                },
            )
            continue

        owner_kind = item['owner_kind']
        owner = None
        lookup = {
            'participante_socio': participant_socio,
            'participante_empresa': participant_empresa,
            'vigente_desde': item.get('vigente_desde') or DEFAULT_LEGACY_PARTICIPATION_START_DATE,
            'vigente_hasta': item['vigente_hasta'],
        }
        if owner_kind == 'empresa':
            owner = empresa_map.get(item['owner_legacy_id'])
            if not owner:
                report.add_skip(
                    'participaciones',
                    {
                        'legacy_id': item['legacy_id'],
                        'reason': 'No se encontro la empresa canónica para la participación.',
                        'owner_legacy_id': item['owner_legacy_id'],
                    },
                )
                continue
            lookup['empresa_owner'] = owner
        elif owner_kind == 'comunidad':
            owner = comunidad_map.get(item['owner_legacy_id'])
            if not owner:
                report.add_skip(
                    'participaciones',
                    {
                        'legacy_id': item['legacy_id'],
                        'reason': 'No se encontro la comunidad canónica para la participación.',
                        'owner_legacy_id': item['owner_legacy_id'],
                    },
                )
                continue
            lookup['comunidad_owner'] = owner
        else:
            report.add_skip(
                'participaciones',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': f"owner_kind no soportado para importación: {owner_kind}",
                },
            )
            continue

        obj, created = ParticipacionPatrimonial.objects.update_or_create(
            **lookup,
            defaults={
                'porcentaje': item['porcentaje'],
                'activo': item['activo'],
            },
        )
        imported_owner_ids[owner_kind].add(owner.pk)
        retained_participation_ids[(owner_kind, owner.pk)].add(obj.pk)
        report.bump('created' if created else 'updated', 'participaciones')

    for owner_kind, owner_ids in imported_owner_ids.items():
        for owner_id in owner_ids:
            if owner_kind == 'empresa':
                queryset = ParticipacionPatrimonial.objects.filter(empresa_owner_id=owner_id)
            else:
                queryset = ParticipacionPatrimonial.objects.filter(comunidad_owner_id=owner_id)
            stale_ids = queryset.exclude(pk__in=retained_participation_ids[(owner_kind, owner_id)]).values_list('pk', flat=True)
            if stale_ids:
                ParticipacionPatrimonial.objects.filter(pk__in=list(stale_ids)).delete()


def import_bundle(bundle):
    report = ImportReport()

    socio_map = {}
    for item in bundle['patrimonio']['socios']:
        normalized_rut = safe_normalize_rut(report, 'socios', item, 'socio')
        if not normalized_rut:
            continue
        obj, created = Socio.objects.update_or_create(
            rut=normalized_rut,
            defaults={
                'nombre': item['nombre'],
                'email': item['email'],
                'telefono': item['telefono'],
                'domicilio': item['domicilio'],
                'activo': item['activo'],
            },
        )
        socio_map[item['legacy_id']] = obj
        report.bump('created' if created else 'updated', 'socios')

    empresa_map = {}
    for item in bundle['patrimonio']['empresas']:
        normalized_rut = safe_normalize_rut(report, 'empresas', item, 'empresa')
        if not normalized_rut:
            continue
        obj, created = Empresa.objects.update_or_create(
            rut=normalized_rut,
            defaults={
                'razon_social': item['razon_social'],
                'domicilio': item['domicilio'],
                'giro': item['giro'],
                'codigo_actividad_sii': item['codigo_actividad_sii'],
                'estado': item['estado'],
            },
        )
        empresa_map[item['legacy_id']] = obj
        report.bump('created' if created else 'updated', 'empresas')

    comunidad_map = {}
    for item in bundle['patrimonio']['comunidades']:
        representation_hint = item.get('representacion_sugerida') or {}
        representative_legacy_id = representation_hint.get('socio_legacy_id') or item.get('representante_legacy_id')
        representative = socio_map.get(representative_legacy_id) if representative_legacy_id else None
        obj, created = ComunidadPatrimonial.objects.update_or_create(
            nombre=item['nombre'],
            defaults={
                'estado': item['estado'],
            },
        )
        if representative:
            current_representation = obj.representacion_vigente()
            representation_mode = representation_hint.get('modo_representacion', ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT)
            if (
                current_representation is None
                or current_representation.socio_representante_id != representative.id
                or current_representation.modo_representacion != representation_mode
            ):
                obj.representaciones.filter(activo=True).update(activo=False)
                RepresentacionComunidad.objects.create(
                    comunidad=obj,
                    modo_representacion=representation_mode,
                    socio_representante=representative,
                    vigente_desde=timezone.localdate(),
                    activo=True,
                    observaciones='Importado desde bundle legacy.',
                )
        comunidad_map[item['legacy_id']] = obj
        report.bump('created' if created else 'updated', 'comunidades')

    sync_bundle_participaciones(
        bundle_participaciones=bundle['patrimonio']['participaciones'],
        socio_map=socio_map,
        empresa_map=empresa_map,
        comunidad_map=comunidad_map,
        report=report,
    )

    property_map = {}
    for item in bundle['patrimonio']['propiedades']:
        defaults = {
            'rol_avaluo': item['rol_avaluo'],
            'direccion': item['direccion'],
            'comuna': item['comuna'],
            'region': item['region'],
            'tipo_inmueble': item['tipo_inmueble'],
            'estado': item['estado'],
            'empresa_owner': empresa_map.get(item['owner_legacy_id']) if item['owner_kind'] == 'empresa' else None,
            'comunidad_owner': comunidad_map.get(item['owner_legacy_id']) if item['owner_kind'] == 'comunidad' else None,
            'socio_owner': socio_map.get(item['owner_legacy_id']) if item['owner_kind'] == 'socio' else None,
        }
        owner_filters = {
            'empresa_owner': defaults['empresa_owner'],
            'comunidad_owner': defaults['comunidad_owner'],
            'socio_owner': defaults['socio_owner'],
        }
        obj, created = Propiedad.objects.update_or_create(
            codigo_propiedad=item['codigo_propiedad'],
            **owner_filters,
            defaults=defaults,
        )
        property_map[item['legacy_id']] = obj
        report.bump('created' if created else 'updated', 'propiedades')

    imported_accounts_by_owner = {}
    for item in bundle['operacion']['cuentas_recaudadoras']:
        empresa_owner = empresa_map.get(item['owner_legacy_id']) if item['owner_kind'] == 'empresa' else None
        socio_owner = socio_map.get(item['owner_legacy_id']) if item['owner_kind'] == 'socio' else None
        if item['owner_kind'] == 'empresa' and not empresa_owner:
            report.add_skip(
                'cuentas_recaudadoras',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': 'No se encontro la empresa canónica para la cuenta recaudadora.',
                    'owner_legacy_id': item['owner_legacy_id'],
                },
            )
            continue
        if item['owner_kind'] == 'socio' and not socio_owner:
            report.add_skip(
                'cuentas_recaudadoras',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': 'No se encontro el socio canónico para la cuenta recaudadora.',
                    'owner_legacy_id': item['owner_legacy_id'],
                },
            )
            continue
        obj, created = CuentaRecaudadora.objects.update_or_create(
            institucion=item['institucion'],
            numero_cuenta=item['numero_cuenta'],
            defaults={
                'empresa_owner': empresa_owner,
                'socio_owner': socio_owner,
                'tipo_cuenta': item['tipo_cuenta'],
                'titular_nombre': item['titular_nombre'],
                'titular_rut': item['titular_rut'],
                'moneda_operativa': item['moneda_operativa'],
                'estado_operativo': item['estado_operativo'],
            },
        )
        imported_accounts_by_owner[(item['owner_kind'], item['owner_legacy_id'])] = obj
        report.bump('created' if created else 'updated', 'cuentas_recaudadoras')

    mandate_map = {}
    resolved_property_context = load_resolved_property_context()
    property_map.update({scope_reference: data['propiedad'] for scope_reference, data in resolved_property_context.items()})

    mandate_candidates = list(bundle['patrimonio']['propiedades'])
    deterministic_property_ids = {item['legacy_id'] for item in mandate_candidates}
    for scope_reference, context in resolved_property_context.items():
        if scope_reference in deterministic_property_ids:
            continue
        propiedad = context['propiedad']
        mandate_candidates.append(
            {
                'legacy_id': scope_reference,
                'owner_kind': propiedad.owner_tipo,
                'owner_legacy_id': None,
            }
        )

    for item in mandate_candidates:
        propiedad = property_map[item['legacy_id']]
        active_mandate = resolve_unique_active_mandate(propiedad)
        if active_mandate:
            mandate_map[item['legacy_id']] = active_mandate
            report.bump('updated', 'mandatos_operacion')
            continue

        if item['owner_kind'] != 'empresa':
            if item['owner_kind'] == 'comunidad':
                owner = comunidad_map.get(item['owner_legacy_id']) or getattr(propiedad, 'comunidad_owner', None)
                admin = resolve_current_community_admin()
                cuenta = resolve_current_community_account()
                if not owner or not admin or not cuenta:
                    report.add_skip(
                        'mandatos_candidates',
                        {
                            'property_legacy_id': item['legacy_id'],
                            'reason': 'No existe contexto suficiente para derivar mandato comunitario automático.',
                        },
                    )
                    continue

                active_company_participants = list(
                    owner.participaciones_activas().filter(participante_empresa__isnull=False).select_related('participante_empresa')
                )
                if len(active_company_participants) > 1:
                    report.add_skip(
                        'mandatos_candidates',
                        {
                            'property_legacy_id': item['legacy_id'],
                            'reason': 'La comunidad tiene múltiples empresas participantes activas y no se puede derivar una única entidad facturadora.',
                        },
                    )
                    continue

                entidad_facturadora = active_company_participants[0].participante_empresa if len(active_company_participants) == 1 else None
                mandato, created = MandatoOperacion.objects.update_or_create(
                    propiedad=propiedad,
                    estado='activa',
                    defaults={
                        'propietario_empresa_owner': None,
                        'propietario_comunidad_owner': owner,
                        'propietario_socio_owner': None,
                        'administrador_empresa_owner': None,
                        'administrador_socio_owner': admin,
                        'recaudador_empresa_owner': cuenta.empresa_owner,
                        'recaudador_socio_owner': cuenta.socio_owner,
                        'entidad_facturadora': entidad_facturadora,
                        'cuenta_recaudadora': cuenta,
                        'tipo_relacion_operativa': 'legacy_import_auto_comunidad',
                        'autoriza_recaudacion': True,
                        'autoriza_facturacion': bool(entidad_facturadora),
                        'autoriza_comunicacion': True,
                        'vigencia_desde': timezone.localdate(),
                        'vigencia_hasta': None,
                    },
                )
                mandate_map[item['legacy_id']] = mandato
                report.bump('created' if created else 'updated', 'mandatos_operacion')
                continue

            if item['owner_kind'] == 'socio':
                cuenta = imported_accounts_by_owner.get((item['owner_kind'], item['owner_legacy_id']))
                owner = socio_map.get(item['owner_legacy_id'])
                if not cuenta or not owner:
                    report.add_skip(
                        'mandatos_candidates',
                        {
                            'property_legacy_id': item['legacy_id'],
                            'reason': 'No existe cuenta recaudadora importada inequívoca para el owner socio.',
                        },
                    )
                    continue
                mandato, created = MandatoOperacion.objects.update_or_create(
                    propiedad=propiedad,
                    estado='activa',
                    defaults={
                        'propietario_empresa_owner': None,
                        'propietario_comunidad_owner': None,
                        'propietario_socio_owner': owner,
                        'administrador_empresa_owner': None,
                        'administrador_socio_owner': owner,
                        'recaudador_empresa_owner': None,
                        'recaudador_socio_owner': owner,
                        'entidad_facturadora': None,
                        'cuenta_recaudadora': cuenta,
                        'tipo_relacion_operativa': 'legacy_import_auto',
                        'autoriza_recaudacion': True,
                        'autoriza_facturacion': False,
                        'autoriza_comunicacion': True,
                        'vigencia_desde': timezone.localdate(),
                        'vigencia_hasta': None,
                    },
                )
                mandate_map[item['legacy_id']] = mandato
                report.bump('created' if created else 'updated', 'mandatos_operacion')
                continue

            report.add_skip(
                'mandatos_candidates',
                {
                    'property_legacy_id': item['legacy_id'],
                    'reason': 'Solo se auto-derivan mandatos legacy para propiedades con owner empresa o socio y cuenta recaudadora inequívoca.',
                },
            )
            continue

        cuenta = imported_accounts_by_owner.get((item['owner_kind'], item['owner_legacy_id']))
        owner = empresa_map.get(item['owner_legacy_id'])
        if not cuenta or not owner:
            report.add_skip(
                'mandatos_candidates',
                {
                    'property_legacy_id': item['legacy_id'],
                    'reason': 'No existe cuenta recaudadora importada inequívoca para el owner empresa.',
                },
            )
            continue

        mandato, created = MandatoOperacion.objects.update_or_create(
            propiedad=propiedad,
            estado='activa',
            defaults={
                'propietario_empresa_owner': owner,
                'propietario_comunidad_owner': None,
                'propietario_socio_owner': None,
                'administrador_empresa_owner': owner,
                'administrador_socio_owner': None,
                'recaudador_empresa_owner': owner,
                'recaudador_socio_owner': None,
                'entidad_facturadora': owner,
                'cuenta_recaudadora': cuenta,
                'tipo_relacion_operativa': 'legacy_import_auto',
                'autoriza_recaudacion': True,
                'autoriza_facturacion': True,
                'autoriza_comunicacion': True,
                'vigencia_desde': timezone.localdate(),
                'vigencia_hasta': None,
            },
        )
        mandate_map[item['legacy_id']] = mandato
        report.bump('created' if created else 'updated', 'mandatos_operacion')

    arrendatario_map = {}
    for item in bundle['contratos']['arrendatarios']:
        normalized_rut = safe_normalize_rut(report, 'arrendatarios', item, 'arrendatario')
        if not normalized_rut:
            continue
        obj, created = Arrendatario.objects.update_or_create(
            rut=normalized_rut,
            defaults={
                'tipo_arrendatario': item['tipo_arrendatario'],
                'nombre_razon_social': item['nombre_razon_social'],
                'email': item['email'],
                'telefono': item['telefono'],
                'domicilio_notificaciones': item['domicilio_notificaciones'],
                'estado_contacto': item['estado_contacto'],
                'whatsapp_bloqueado': item['whatsapp_bloqueado'],
            },
        )
        arrendatario_map[item['legacy_id']] = obj
        report.bump('created' if created else 'updated', 'arrendatarios')

    imported_contract_ids = set()
    for item in bundle['contratos']['contratos_candidates']:
        required_fields = {
            'legacy_id',
            'propiedad_legacy_id',
            'arrendatario_legacy_id',
            'fecha_inicio',
            'fecha_fin_vigente',
            'fecha_entrega',
            'dia_pago_mensual',
            'plazo_notificacion_termino_dias',
            'dias_prealerta_admin',
        }
        missing = sorted(required_fields - set(item.keys()))
        if missing:
            report.add_skip(
                'contratos_candidates',
                {
                    'legacy_id': item.get('legacy_id', 'unknown'),
                    'reason': f'Contrato candidato incompleto; faltan campos: {", ".join(missing)}',
                },
            )
            continue
        missing_values = missing_required_values(item, required_fields)
        if missing_values:
            report.add_skip(
                'contratos_candidates',
                {
                    'legacy_id': item.get('legacy_id', 'unknown'),
                    'reason': f'Contrato candidato con valores vacios/no definidos: {", ".join(sorted(missing_values))}',
                },
            )
            continue

        propiedad = property_map.get(item['propiedad_legacy_id'])
        arrendatario = arrendatario_map.get(item['arrendatario_legacy_id'])
        if not propiedad:
            report.add_skip(
                'contratos_candidates',
                {
                    'legacy_id': item['legacy_id'],
                    'property_legacy_id': item['propiedad_legacy_id'],
                    'reason': 'No se encontro la propiedad canónica para el contrato.',
                },
            )
            continue
        if not arrendatario:
            report.add_skip(
                'contratos_candidates',
                {'legacy_id': item['legacy_id'], 'reason': 'No se encontro el arrendatario canónico para el contrato.'},
            )
            continue

        mandate = mandate_map.get(item['propiedad_legacy_id']) or resolve_unique_active_mandate(propiedad)
        if not mandate:
            report.add_skip(
                'contratos_candidates',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': 'No existe un MandatoOperacion activo y único para la propiedad canónica.',
                    'property_legacy_id': item['propiedad_legacy_id'],
                },
            )
            continue

        canonical_state = LEGACY_CONTRACT_STATE_MAP.get((item.get('estado_legacy') or '').lower())
        if not canonical_state:
            report.add_skip(
                'contratos_candidates',
                {'legacy_id': item['legacy_id'], 'reason': f"Estado legacy no soportado: {item.get('estado_legacy')}"},
            )
            continue

        effective_code = derive_effective_code(propiedad)
        if not effective_code:
            report.add_skip(
                'contratos_candidates',
                {'legacy_id': item['legacy_id'], 'reason': 'No se pudo derivar codigo de conciliacion efectivo desde la propiedad.'},
            )
            continue

        contrato, created = Contrato.objects.update_or_create(
            codigo_contrato=f'LEGACY-{item["legacy_id"]}',
            defaults={
                'mandato_operacion': mandate,
                'arrendatario': arrendatario,
                'fecha_inicio': item['fecha_inicio'],
                'fecha_fin_vigente': item['fecha_fin_vigente'],
                'fecha_entrega': item['fecha_entrega'],
                'dia_pago_mensual': item['dia_pago_mensual'],
                'plazo_notificacion_termino_dias': item['plazo_notificacion_termino_dias'],
                'dias_prealerta_admin': item['dias_prealerta_admin'],
                'estado': canonical_state,
                'tiene_tramos': False,
                'tiene_gastos_comunes': False,
                'snapshot_representante_legal': {'legacy_contract_id': item['legacy_id']},
            },
        )
        report.bump('created' if created else 'updated', 'contratos')
        imported_contract_ids.add(item['legacy_id'])

        _, contrato_propiedad_created = ContratoPropiedad.objects.update_or_create(
            contrato=contrato,
            propiedad=propiedad,
            defaults={
                'rol_en_contrato': 'principal',
                'porcentaje_distribucion_interna': Decimal('100.00'),
                'codigo_conciliacion_efectivo_snapshot': effective_code,
            },
        )
        report.bump('created' if contrato_propiedad_created else 'updated', 'contrato_propiedades')

        if item.get('aviso_termino_registrado') and item.get('fecha_aviso_termino'):
            aviso, created_aviso = AvisoTermino.objects.update_or_create(
                contrato=contrato,
                estado=EstadoAvisoTermino.REGISTERED,
                defaults={
                    'fecha_efectiva': item['fecha_aviso_termino'],
                    'causal': item.get('notas_aviso_termino') or 'Aviso importado desde legacy',
                },
            )
            report.bump('created' if created_aviso else 'updated', 'avisos_termino')

    for item in bundle['contratos']['periodos_candidates']:
        required_period_fields = {'legacy_id', 'legacy_contrato_id', 'numero_periodo', 'fecha_inicio', 'fecha_fin', 'monto_base', 'moneda_base'}
        missing = sorted(required_period_fields - set(item.keys()))
        if missing:
            report.add_skip(
                'periodos_candidates',
                {
                    'legacy_id': item.get('legacy_id', 'unknown'),
                    'reason': f'Periodo candidato incompleto; faltan campos: {", ".join(missing)}',
                },
            )
            continue
        if item['legacy_contrato_id'] not in imported_contract_ids:
            report.add_skip(
                'periodos_candidates',
                {
                    'legacy_id': item['legacy_id'],
                    'reason': 'Periodo omitido porque el contrato padre no fue importado de forma segura.',
                    'legacy_contract_id': item['legacy_contrato_id'],
                },
            )
            continue
        contrato = Contrato.objects.get(codigo_contrato=f'LEGACY-{item["legacy_contrato_id"]}')
        period, created = PeriodoContractual.objects.update_or_create(
            contrato=contrato,
            numero_periodo=item['numero_periodo'],
            defaults={
                'fecha_inicio': item['fecha_inicio'],
                'fecha_fin': item['fecha_fin'],
                'monto_base': item['monto_base'],
                'moneda_base': item['moneda_base'],
                'tipo_periodo': 'importado_legacy',
                'origen_periodo': 'legacy',
            },
        )
        report.bump('created' if created else 'updated', 'periodos_contractuales')

    report.skipped.setdefault('periodos_candidates', [])
    report.skipped['unresolved'] = bundle.get('unresolved', {})
    manual_resolution_counts = sync_migration_manual_resolutions(bundle, report)
    if manual_resolution_counts['created']:
        report.created['manual_resolutions'] = report.created.get('manual_resolutions', 0) + manual_resolution_counts['created']
    if manual_resolution_counts['updated']:
        report.updated['manual_resolutions'] = report.updated.get('manual_resolutions', 0) + manual_resolution_counts['updated']
    return report
