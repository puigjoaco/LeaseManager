from __future__ import annotations


EDIFICIO_Q_DEPTO_1014_OVERRIDE = {
    'codigo': 46,
    'direccion_contains': 'Edificio Q Dpto 1014',
    'candidate_owner_model': 'comunidad',
    'participaciones_count': 6,
    'total_pct': 100.0,
    'participantes': [
        {
            'participante_tipo': 'socio',
            'participante_nombre': 'Cecilia Jacqueline Vittini De Ruyt',
            'participante_rut': '7.768.066-7',
            'porcentaje': '16.67',
            'activo': True,
            'vigente_desde': '2017-03-16',
            'vigente_hasta': None,
            'vigente_desde_source': 'explicit_user_confirmed_override',
        },
        {
            'participante_tipo': 'socio',
            'participante_nombre': 'Trinidad Puig Jequier',
            'participante_rut': '20.785.966-4',
            'porcentaje': '16.67',
            'activo': True,
            'vigente_desde': '2017-03-16',
            'vigente_hasta': None,
            'vigente_desde_source': 'explicit_user_confirmed_override',
        },
        {
            'participante_tipo': 'socio',
            'participante_nombre': 'Catalina Puig Jequier',
            'participante_rut': '21.180.524-2',
            'porcentaje': '16.67',
            'activo': True,
            'vigente_desde': '2017-03-16',
            'vigente_hasta': None,
            'vigente_desde_source': 'explicit_user_confirmed_override',
        },
        {
            'participante_tipo': 'socio',
            'participante_nombre': 'Cristóbal José Puig Vittini',
            'participante_rut': '16.531.864-1',
            'porcentaje': '16.66',
            'activo': True,
            'vigente_desde': '2017-03-16',
            'vigente_hasta': None,
            'vigente_desde_source': 'explicit_user_confirmed_override',
        },
        {
            'participante_tipo': 'socio',
            'participante_nombre': 'Geraldine Stefanie Puig Vittini',
            'participante_rut': '15.244.057-K',
            'porcentaje': '16.67',
            'activo': True,
            'vigente_desde': '2017-03-16',
            'vigente_hasta': None,
            'vigente_desde_source': 'explicit_user_confirmed_override',
        },
        {
            'participante_tipo': 'empresa',
            'participante_nombre': 'Inmobiliaria Puig SpA',
            'participante_rut': '76.311.245-4',
            'porcentaje': '16.66',
            'activo': True,
            'vigente_desde': '2017-03-16',
            'vigente_hasta': None,
            'vigente_desde_source': 'explicit_user_confirmed_override',
        },
    ],
    'representacion_sugerida': {
        'modo_representacion': 'designado',
        'socio_rut': '17.366.287-4',
        'source': 'explicit_user_confirmed_override',
    },
}

EDIFICIO_Q_BOD_17_EST_33_OVERRIDE = {
    'codigo': 40,
    'direccion_contains': 'Edificio Q Bod.',
    'candidate_owner_model': 'comunidad',
    'participaciones_count': 6,
    'total_pct': 100.0,
    'participantes': EDIFICIO_Q_DEPTO_1014_OVERRIDE['participantes'],
    'representacion_sugerida': EDIFICIO_Q_DEPTO_1014_OVERRIDE['representacion_sugerida'],
}


PROPERTY_OWNER_ENRICHMENTS = [
    EDIFICIO_Q_DEPTO_1014_OVERRIDE,
    EDIFICIO_Q_BOD_17_EST_33_OVERRIDE,
]


PROPERTY_SOURCE_ENRICHMENTS = [
    {
        'direccion_contains': 'Estacionamiento 97',
        'owner_kind': 'socio',
        'owner_rut': '17.366.287-4',
        'estado': 'arrendada',
        'source': 'explicit_user_confirmed_override',
    }
]


PROPERTY_MIGRATION_EXCLUSIONS = [
    {
        'direccion_contains': 'Estacionamiento 96',
        'source': 'explicit_user_confirmed_out_of_portfolio',
    }
]


CONTRACT_FIELD_ENRICHMENTS = {
    '08fe72fc-0890-460d-974f-d934931b7e19': {
        'dia_pago_mensual': 5,
        'source': 'explicit_user_confirmed_override',
    },
    'b1634538-d8a8-406a-a1f3-bcb3ff391a2a': {
        'propiedad_legacy_id': '54c7de96-c6bb-4446-971f-90c062edffae',
        'dia_pago_mensual': 5,
        'source': 'explicit_user_confirmed_override',
    },
}


TENANT_MIGRATION_EXCLUSIONS = {
    '780bba00-db91-4b63-bfc0-35706db6e6a5': {
        'source': 'explicit_user_confirmed_no_longer_tenant',
    },
    '714b5efc-68de-4457-b950-e57d4c4ee14c': {
        'source': 'explicit_user_confirmed_no_longer_tenant',
    },
    'bbd1123f-86b4-45c4-abc8-5546d8df2f8d': {
        'source': 'explicit_user_confirmed_no_longer_tenant',
    },
}


TENANT_FIELD_ENRICHMENTS = {
    '0f7aa310-231a-40a9-b397-99a7f53a4f03': {
        'rut': '19.076.873-2',
        'source': 'explicit_user_confirmed_override',
    },
}


def apply_property_owner_enrichment(base_item: dict) -> dict:
    enriched = dict(base_item)
    codigo = base_item.get('codigo')
    direccion = str(base_item.get('direccion') or '')

    for override in PROPERTY_OWNER_ENRICHMENTS:
        if override.get('codigo') != codigo:
            continue
        if override.get('direccion_contains') and override['direccion_contains'] not in direccion:
            continue
        enriched.update(
            {
                'candidate_owner_model': override['candidate_owner_model'],
                'participaciones_count': override['participaciones_count'],
                'total_pct': override['total_pct'],
                'participantes': override['participantes'],
                'socios': [
                    {
                        'socio_legacy_id': None,
                        'socio_nombre': item['participante_nombre'],
                        'socio_rut': item['participante_rut'],
                        'porcentaje': item['porcentaje'],
                        'activo': item['activo'],
                        'vigente_desde': item['vigente_desde'],
                        'vigente_hasta': item['vigente_hasta'],
                    }
                    for item in override['participantes']
                    if item['participante_tipo'] == 'socio'
                ],
                'representacion_sugerida': override['representacion_sugerida'],
                'enrichment_source': 'explicit_user_confirmed_override',
            }
        )
        return enriched

    return enriched


def apply_contract_enrichment(base_item: dict) -> dict:
    enriched = dict(base_item)
    override = CONTRACT_FIELD_ENRICHMENTS.get(base_item.get('legacy_id'))
    if not override:
        return enriched
    enriched.update(override)
    return enriched


def apply_contract_source_enrichment(raw_contract_row: dict) -> dict:
    enriched = dict(raw_contract_row)
    override = CONTRACT_FIELD_ENRICHMENTS.get(raw_contract_row.get('id'))
    if not override:
        return enriched
    if 'propiedad_legacy_id' in override:
        enriched['propiedad_id'] = override['propiedad_legacy_id']
    if 'dia_pago_mensual' in override:
        enriched['dia_pago'] = override['dia_pago_mensual']
    return enriched


def should_exclude_property_from_current_migration(raw_property_row: dict) -> bool:
    address = ' '.join(str(x) for x in [raw_property_row.get('direccion'), raw_property_row.get('numero'), raw_property_row.get('depto')] if x)
    for rule in PROPERTY_MIGRATION_EXCLUSIONS:
        if rule.get('direccion_contains') and rule['direccion_contains'] in address:
            return True
    return False


def apply_property_source_enrichment(raw_property_row: dict, socio_by_legacy_id: dict) -> dict:
    enriched = dict(raw_property_row)
    address = ' '.join(str(x) for x in [raw_property_row.get('direccion'), raw_property_row.get('numero'), raw_property_row.get('depto')] if x)
    for rule in PROPERTY_SOURCE_ENRICHMENTS:
        if rule.get('direccion_contains') and rule['direccion_contains'] not in address:
            continue
        enriched['estado'] = rule.get('estado', enriched.get('estado'))
        if rule.get('owner_kind') == 'socio':
            target_rut = ''.join(ch for ch in str(rule.get('owner_rut') or '') if ch.isalnum()).upper()
            for legacy_id, socio in socio_by_legacy_id.items():
                socio_rut = ''.join(ch for ch in str(socio.get('rut') or '') if ch.isalnum()).upper()
                if socio_rut == target_rut:
                    enriched['socio_id'] = legacy_id
                    enriched['empresa_id'] = None
                    enriched['comunidad_id'] = None
                    return enriched
    return enriched


def should_exclude_tenant_from_current_migration(legacy_tenant_id: str) -> bool:
    return legacy_tenant_id in TENANT_MIGRATION_EXCLUSIONS


def apply_tenant_enrichment(base_item: dict) -> dict:
    enriched = dict(base_item)
    override = TENANT_FIELD_ENRICHMENTS.get(base_item.get('legacy_id'))
    if not override:
        return enriched
    enriched.update(override)
    return enriched
