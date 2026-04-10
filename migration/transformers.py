from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from migration.enrichments import (
    apply_contract_enrichment,
    apply_contract_source_enrichment,
    apply_property_owner_enrichment,
    apply_property_source_enrichment,
    apply_tenant_enrichment,
    should_exclude_property_from_current_migration,
    should_exclude_tenant_from_current_migration,
)

KNOWN_SOCIO_ACCOUNT_BY_NUMBER = {
    '8240131105': '17366287-4',
}
CURRENT_COMMUNITY_DESIGNATED_REPRESENTATIVE_RUT = '17366287-4'
DEFAULT_LEGACY_PARTICIPATION_START_DATE = '2017-03-16'


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def compact_join(*parts):
    return ', '.join(str(part).strip() for part in parts if part not in (None, ''))


def map_company_state(row):
    return 'activa' if row.get('activa', True) else 'inactiva'


def map_property_state(row):
    if row.get('estado') == 'no_arriendo':
        return 'inactiva'
    return 'activa'


def map_inmueble_type(row):
    raw = row.get('tipo_propiedad') or row.get('tipo') or 'otro'
    mapping = {
        'departamento': 'departamento',
        'casa': 'casa',
        'local': 'local',
        'oficina': 'oficina',
        'bodega': 'bodega',
        'estacionamiento': 'estacionamiento',
        'otro': 'otro',
    }
    return mapping.get(raw, 'otro')


def map_arrendatario_contact_state(row):
    return row.get('estado_registro', 'pendiente').replace('dado_de_baja', 'inactivo')


def normalize_rut_like(value):
    return ''.join(character for character in str(value or '') if character.isalnum()).upper()


def infer_region_from_location(*, comuna='', ciudad='', raw_region=''):
    if raw_region:
        return raw_region
    normalized_comuna = str(comuna or '').strip().lower()
    normalized_ciudad = str(ciudad or '').strip().lower()
    if normalized_comuna == 'temuco' or normalized_ciudad == 'temuco':
        return 'La Araucania'
    return ''


def resolve_current_community_representative_legacy_id(socio_by_legacy_id):
    target = normalize_rut_like(CURRENT_COMMUNITY_DESIGNATED_REPRESENTATIVE_RUT)
    for legacy_id, socio in socio_by_legacy_id.items():
        if normalize_rut_like(socio.get('rut')) == target:
            return legacy_id
    return None


def resolve_legacy_participation_start_date(raw_value):
    return raw_value or DEFAULT_LEGACY_PARTICIPATION_START_DATE


def normalize_contract_periods(contract_row, period_rows, warnings):
    sorted_rows = sorted(
        period_rows,
        key=lambda item: (
            item.get('fecha_inicio') or '',
            item.get('fecha_termino') or '',
            item.get('numero_periodo') or 0,
            str(item.get('id') or ''),
        ),
    )
    raw_numbers = [row.get('numero_periodo') for row in sorted_rows]
    requires_resequence = any(number in (None, 0, '') for number in raw_numbers) or len(set(raw_numbers)) != len(raw_numbers)
    if requires_resequence and sorted_rows:
        warnings.append(
            f"Contract legacy {contract_row['id']} period numbers were re-sequenced chronologically for canonical import."
        )

    normalized = []
    for index, period in enumerate(sorted_rows, start=1):
        numero_periodo = index if requires_resequence else period.get('numero_periodo') or index
        normalized.append(
            {
                'legacy_id': period['id'],
                'numero_periodo': numero_periodo,
                'legacy_numero_periodo': period.get('numero_periodo'),
                'fecha_inicio': period['fecha_inicio'],
                'fecha_fin': period['fecha_termino'],
                'monto_base': str(period['valor_arriendo']),
                'moneda_base': period['moneda'],
                'legacy_contrato_id': contract_row['id'],
            }
        )
    return normalized


def resolve_property_owner_from_property_participations(property_participations):
    active_rows = [row for row in property_participations if row.get('activa', True)]
    candidate_rows = active_rows or property_participations
    socio_ids = {row.get('socio_id') for row in candidate_rows if row.get('socio_id')}
    total_pct = sum(float(row.get('porcentaje_participacion') or row.get('porcentaje') or 0) for row in candidate_rows)
    if len(socio_ids) == 1 and abs(total_pct - 100.0) < 0.0001:
        return ('socio', next(iter(socio_ids)))
    return (None, None)


def build_property_participation_summary(property_participations, socio_by_legacy_id):
    active_rows = [row for row in property_participations if row.get('activa', True)]
    candidate_rows = active_rows or property_participations
    total_pct = sum(float(row.get('porcentaje_participacion') or row.get('porcentaje') or 0) for row in candidate_rows)
    participantes = []
    socios = []
    for row in candidate_rows:
        socio = socio_by_legacy_id.get(row.get('socio_id'))
        participant_payload = {
            'participante_tipo': 'socio',
            'participante_legacy_id': row.get('socio_id'),
            'participante_nombre': socio['nombre'] if socio else '',
            'participante_rut': socio['rut'] if socio else '',
            'porcentaje': str(row.get('porcentaje_participacion') or row.get('porcentaje') or 0),
            'activo': bool(row.get('activa', True)),
            'vigente_desde': resolve_legacy_participation_start_date(row.get('fecha_inicio')),
            'vigente_hasta': row.get('fecha_fin'),
            'vigente_desde_source': 'legacy' if row.get('fecha_inicio') else 'default_symbolic_inheritance_2017_03_16',
        }
        participantes.append(participant_payload)
        socios.append(
            {
                'socio_legacy_id': participant_payload['participante_legacy_id'],
                'socio_nombre': participant_payload['participante_nombre'],
                'socio_rut': participant_payload['participante_rut'],
                'porcentaje': participant_payload['porcentaje'],
                'activo': participant_payload['activo'],
                'vigente_desde': participant_payload['vigente_desde'],
                'vigente_hasta': participant_payload['vigente_hasta'],
            }
        )
    candidate_owner_model = None
    if len({row['socio_legacy_id'] for row in socios if row['socio_legacy_id']}) > 1 and abs(total_pct - 100.0) < 0.0001:
        candidate_owner_model = 'comunidad'
    representacion_sugerida = None
    designated_representative_legacy_id = resolve_current_community_representative_legacy_id(socio_by_legacy_id)
    if len(candidate_rows) > 1 and designated_representative_legacy_id:
        representacion_sugerida = {
            'modo_representacion': 'designado',
            'socio_legacy_id': designated_representative_legacy_id,
            'source': 'business_rule_current_communities',
        }
    return {
        'participaciones_count': len(candidate_rows),
        'total_pct': total_pct,
        'candidate_owner_model': candidate_owner_model,
        'participantes': participantes,
        'socios': socios,
        'representacion_sugerida': representacion_sugerida,
    }


def transform_legacy_bundle(legacy_rows):
    warnings = []
    unresolved = defaultdict(list)

    sociedades = []
    sociedad_by_legacy_id = {}
    for row in legacy_rows.get('empresas', []):
        item = {
            'legacy_id': row['id'],
            'rut': row['rut'],
            'razon_social': row.get('razon_social') or row.get('nombre') or row['rut'],
            'domicilio': compact_join(row.get('direccion'), row.get('comuna'), row.get('ciudad')),
            'giro': row.get('giro') or '',
            'codigo_actividad_sii': '',
            'estado': map_company_state(row),
        }
        sociedades.append(item)
        sociedad_by_legacy_id[row['id']] = item

    socios = []
    socio_by_legacy_id = {}
    for row in legacy_rows.get('socios', []):
        full_name = row.get('nombre_completo') or compact_join(
            row.get('nombre'),
            row.get('apellido_paterno'),
            row.get('apellido_materno'),
        )
        item = {
            'legacy_id': row['id'],
            'rut': row['rut'],
            'nombre': full_name,
            'email': row.get('email') or '',
            'telefono': row.get('telefono') or '',
            'domicilio': row.get('domicilio') or row.get('direccion') or '',
            'activo': True,
        }
        socios.append(item)
        socio_by_legacy_id[row['id']] = item

    comunidades = []
    comunidad_by_legacy_id = {}
    designated_representative_legacy_id = resolve_current_community_representative_legacy_id(socio_by_legacy_id)
    for row in legacy_rows.get('comunidades', []):
        item = {
            'legacy_id': row['id'],
            'nombre': row['nombre'],
            'descripcion': row.get('descripcion') or '',
            'estado': 'borrador',
            'representante_legacy_id': None,
            'representacion_sugerida': (
                {
                    'modo_representacion': 'designado',
                    'socio_legacy_id': designated_representative_legacy_id,
                    'source': 'business_rule_current_communities',
                }
                if designated_representative_legacy_id
                else None
            ),
        }
        comunidades.append(item)
        comunidad_by_legacy_id[row['id']] = item

    participaciones = []
    property_participation_rows = 0
    property_participations_by_property = defaultdict(list)
    for row in legacy_rows.get('participaciones', []):
        owner_kind = None
        owner_legacy_id = None
        if row.get('empresa_id'):
            owner_kind = 'empresa'
            owner_legacy_id = row['empresa_id']
        elif row.get('comunidad_id'):
            owner_kind = 'comunidad'
            owner_legacy_id = row['comunidad_id']
        elif row.get('propiedad_id'):
            property_participation_rows += 1
            property_participations_by_property[row['propiedad_id']].append(row)
            unresolved['participaciones_propiedad'].append(
                {
                    'legacy_id': row['id'],
                    'propiedad_legacy_id': row['propiedad_id'],
                    'socio_legacy_id': row.get('socio_id'),
                    'reason': 'Canonical bundle ignores property-scoped participations; property ownership is carried by Propiedad owner fields.',
                }
            )
            continue
        else:
            unresolved['participaciones_sin_owner'].append({'legacy_id': row['id'], 'reason': 'No owner found in legacy row.'})
            continue

        if not row.get('socio_id'):
            unresolved['participaciones_sin_socio'].append({'legacy_id': row['id'], 'reason': 'No socio_id found in legacy row.'})
            continue

        participaciones.append(
            {
                'legacy_id': row['id'],
                'owner_kind': owner_kind,
                'owner_legacy_id': owner_legacy_id,
                'participante_kind': 'socio',
                'participante_legacy_id': row['socio_id'],
                'socio_legacy_id': row['socio_id'],
                'porcentaje': str(row.get('porcentaje_participacion') or row.get('porcentaje') or 0),
                'vigente_desde': resolve_legacy_participation_start_date(row.get('fecha_inicio')),
                'vigente_hasta': row.get('fecha_fin'),
                'activo': bool(row.get('activa', True)),
                'vigente_desde_source': 'legacy' if row.get('fecha_inicio') else 'default_symbolic_inheritance_2017_03_16',
            }
        )

    # Pick a provisional representative for communities only when deterministic.
    participation_by_community = defaultdict(list)
    for item in participaciones:
        if item['owner_kind'] == 'comunidad':
            participation_by_community[item['owner_legacy_id']].append(item)
    for community in comunidades:
        rows = participation_by_community.get(community['legacy_id'], [])
        if designated_representative_legacy_id and rows:
            community['representante_legacy_id'] = designated_representative_legacy_id
            community['estado'] = 'activa'
        elif rows:
            community['estado'] = 'activa'

    propiedades = []
    excluded_property_legacy_ids = set()
    for row in legacy_rows.get('propiedades', []):
        row = apply_property_source_enrichment(row, socio_by_legacy_id)
        if should_exclude_property_from_current_migration(row):
            excluded_property_legacy_ids.add(row['id'])
            continue
        owner_kind = None
        owner_legacy_id = None
        if row.get('empresa_id'):
            owner_kind = 'empresa'
            owner_legacy_id = row['empresa_id']
        elif row.get('comunidad_id'):
            owner_kind = 'comunidad'
            owner_legacy_id = row['comunidad_id']
        elif row.get('socio_id'):
            owner_kind = 'socio'
            owner_legacy_id = row['socio_id']
        else:
            participation_summary = build_property_participation_summary(
                property_participations_by_property.get(row['id'], []),
                socio_by_legacy_id,
            )
            owner_kind, owner_legacy_id = resolve_property_owner_from_property_participations(
                property_participations_by_property.get(row['id'], [])
            )
            if not owner_kind:
                unresolved_item = {
                    'legacy_id': row['id'],
                    'reason': 'No owner found in legacy row.',
                    'codigo': row.get('codigo'),
                    'codigo_propiedad': row.get('codigo_propiedad'),
                    'direccion': compact_join(row.get('direccion'), row.get('numero'), row.get('depto')),
                    'estado': row.get('estado') or '',
                    'canonical_estado': map_property_state(row),
                    'rol_avaluo': row.get('rol_tributario') or row.get('rol') or '',
                    'comuna': row.get('comuna') or '',
                    'region': infer_region_from_location(
                        comuna=row.get('comuna') or '',
                        ciudad=row.get('ciudad') or '',
                        raw_region='',
                    ),
                    'tipo_inmueble': map_inmueble_type(row),
                    **participation_summary,
                }
                unresolved['propiedades_sin_owner'].append(apply_property_owner_enrichment(unresolved_item))
                continue

        propiedades.append(
            {
                'legacy_id': row['id'],
                'owner_kind': owner_kind,
                'owner_legacy_id': owner_legacy_id,
                'rol_avaluo': row.get('rol_tributario') or row.get('rol') or '',
                'direccion': compact_join(row.get('direccion'), row.get('numero'), row.get('depto')),
                'comuna': row.get('comuna') or '',
                'region': infer_region_from_location(
                    comuna=row.get('comuna') or '',
                    ciudad=row.get('ciudad') or '',
                    raw_region='',
                ),
                'tipo_inmueble': map_inmueble_type(row),
                'codigo_propiedad': str(row.get('codigo_propiedad') or row.get('codigo')),
                'estado': map_property_state(row),
                'legacy_estado': row.get('estado') or '',
            }
        )

    cuentas_recaudadoras = []
    socio_by_normalized_rut = {
        normalize_rut_like(item['rut']): item
        for item in socios
        if item.get('rut')
    }
    for row in legacy_rows.get('cuentas_bancarias', []):
        if not row.get('empresa_id'):
            owner_rut = KNOWN_SOCIO_ACCOUNT_BY_NUMBER.get(str(row.get('numero_cuenta') or ''))
            owner = socio_by_normalized_rut.get(normalize_rut_like(owner_rut))
            if not owner:
                unresolved['cuentas_sin_empresa'].append({'legacy_id': row['id'], 'reason': 'Legacy bank account has no empresa_id.'})
                continue
            cuentas_recaudadoras.append(
                {
                    'legacy_id': row['id'],
                    'owner_kind': 'socio',
                    'owner_legacy_id': owner['legacy_id'],
                    'institucion': row.get('nombre_banco') or row.get('banco') or '',
                    'numero_cuenta': row['numero_cuenta'],
                    'tipo_cuenta': row['tipo_cuenta'],
                    'titular_nombre': owner['nombre'],
                    'titular_rut': owner['rut'],
                    'moneda_operativa': row.get('moneda') or 'CLP',
                    'estado_operativo': 'activa' if row.get('activa', True) else 'inactiva',
                }
            )
            warnings.append(
                f"Legacy bank account {row['id']} without empresa_id mapped to documented socio owner via account number."
            )
            continue
        empresa = sociedad_by_legacy_id.get(row['empresa_id'])
        if not empresa:
            unresolved['cuentas_empresa_desconocida'].append(
                {'legacy_id': row['id'], 'empresa_legacy_id': row['empresa_id'], 'reason': 'empresa_id not found in empresas export.'}
            )
            continue
        cuentas_recaudadoras.append(
            {
                'legacy_id': row['id'],
                'owner_kind': 'empresa',
                'owner_legacy_id': row['empresa_id'],
                'institucion': row.get('nombre_banco') or row.get('banco') or '',
                'numero_cuenta': row['numero_cuenta'],
                'tipo_cuenta': row['tipo_cuenta'],
                'titular_nombre': empresa['razon_social'],
                'titular_rut': empresa['rut'],
                'moneda_operativa': row.get('moneda') or 'CLP',
                'estado_operativo': 'activa' if row.get('activa', True) else 'inactiva',
            }
        )

    arrendatarios = []
    arrendatario_by_legacy_id = {}
    for row in legacy_rows.get('arrendatarios', []):
        if should_exclude_tenant_from_current_migration(row['id']):
            continue
        item = {
            'legacy_id': row['id'],
            'tipo_arrendatario': row.get('tipo') or 'persona_natural',
            'nombre_razon_social': row.get('nombre_completo') or row.get('razon_social') or compact_join(
                row.get('nombre'),
                row.get('apellido_paterno'),
                row.get('apellido_materno'),
            ),
            'rut': row['rut'],
            'email': row.get('email') or '',
            'telefono': row.get('telefono') or '',
            'domicilio_notificaciones': compact_join(row.get('direccion'), row.get('comuna'), row.get('ciudad')),
            'estado_contacto': map_arrendatario_contact_state(row),
            'whatsapp_bloqueado': False,
        }
        item = apply_tenant_enrichment(item)
        arrendatarios.append(item)
        arrendatario_by_legacy_id[row['id']] = item

    contratos_candidates = []
    periods_candidates = []
    period_rows_by_contract = defaultdict(list)
    for row in legacy_rows.get('periodos_contractuales', []):
        period_rows_by_contract[row['contrato_id']].append(row)

    for row in legacy_rows.get('contratos', []):
        row = apply_contract_source_enrichment(row)
        if row.get('propiedad_id') in excluded_property_legacy_ids:
            continue
        if should_exclude_tenant_from_current_migration(row.get('arrendatario_id')):
            continue
        periods = normalize_contract_periods(row, period_rows_by_contract.get(row['id'], []), warnings)
        periods_candidates.extend(periods)
        contract_candidate = {
            'legacy_id': row['id'],
            'arrendatario_legacy_id': row['arrendatario_id'],
            'propiedad_legacy_id': row['propiedad_id'],
            'fecha_inicio': row['fecha_inicio'],
            'fecha_fin_vigente': row['fecha_termino'],
            'fecha_entrega': row['fecha_inicio'],
            'dia_pago_mensual': row['dia_pago'],
            'plazo_notificacion_termino_dias': row.get('dias_aviso_termino') or 60,
            'dias_prealerta_admin': row.get('dias_alerta_admin') or 90,
            'estado_legacy': row.get('estado') or '',
            'aviso_termino_registrado': bool(row.get('aviso_termino_registrado')),
            'fecha_aviso_termino': row.get('fecha_aviso_termino'),
            'notas_aviso_termino': row.get('notas_aviso_termino') or '',
            'tiene_garantia': bool(row.get('garantia_requerida') or row.get('requiere_garantia')),
            'periodos': periods,
            'import_strategy': 'candidate_only',
            'unresolved_reason': 'Requires MandatoOperacion mapping from canonical Propiedad/CuentaRecaudadora before safe import.',
        }
        contratos_candidates.append(apply_contract_enrichment(contract_candidate))

    metadata = {
        'generated_at': iso_now(),
        'source': 'legacy_read_only',
        'counts': {
            'socios': len(socios),
            'empresas': len(sociedades),
            'comunidades': len(comunidades),
            'participaciones': len(participaciones),
            'propiedades': len(propiedades),
            'cuentas_recaudadoras': len(cuentas_recaudadoras),
            'arrendatarios': len(arrendatarios),
            'contratos_candidates': len(contratos_candidates),
            'periodos_candidates': len(periods_candidates),
            'property_participation_rows_skipped': property_participation_rows,
        },
    }

    return {
        'metadata': metadata,
        'warnings': warnings,
        'patrimonio': {
            'socios': socios,
            'empresas': sociedades,
            'comunidades': comunidades,
            'participaciones': participaciones,
            'propiedades': propiedades,
        },
        'operacion': {
            'cuentas_recaudadoras': cuentas_recaudadoras,
        },
        'contratos': {
            'arrendatarios': arrendatarios,
            'contratos_candidates': contratos_candidates,
            'periodos_candidates': periods_candidates,
        },
        'unresolved': dict(unresolved),
    }
