from __future__ import annotations

from copy import deepcopy
from typing import Any

from sii.models import TipoAnnualTaxOfficialSource, is_safe_public_sii_source_url


STAGE6_OFFICIAL_COMPATIBILITY_VERSION = 'stage6-official-compatibility-at2025-at2026-v1'
STAGE6_OFFICIAL_COMPATIBILITY_VERIFIED_ON = '2026-06-18'

F22_DECLARATION_OPTIONS_URL = 'https://www.sii.cl/preguntas_frecuentes/declaracion_renta/001_140_8395.htm'
DDJJ_IMPORTER_MANUAL_URL = 'https://alerce.sii.cl/dior/dej/html/manual/DJ_Manual/01.html'

OFFICIAL_COMPATIBILITY_SOURCES_BY_YEAR = {
    2025: {
        'f22_certification_url': 'https://www.sii.cl/noticias/2025/120225noti01aav.htm',
        'f22_instructions_url': 'https://www.sii.cl/servicios_online/renta/guia_trib_suplemento_2025.html',
        'f22_record_format_url': '',
        'ddjj_media_url': 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2025-2171.html',
        'ddjj_forms_url': 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-formularios_y_plazos_2025-2171.html',
        'ddjj_software_houses_url': 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-casas_sw_2025-2171.html',
        'ddjj_certification_news_url': 'https://www.sii.cl/noticias/2024/251124noti01rp.htm',
        'ddjj_review_procedure_url': 'https://alerce.sii.cl/dior/dej/pdf/Procedimiento_de_Revision_AT2025.pdf',
    },
    2026: {
        'f22_certification_url': 'https://www.sii.cl/noticias/2026/060226noti02pcr.htm',
        'f22_instructions_url': 'https://www.sii.cl/servicios_online/renta/guia_trib_suplemento_2026.html',
        'f22_record_format_url': 'https://alerce.sii.cl/dior/ren_mp/pdf/6_Formato_de_Registro_F22_AT2026.pdf',
        'ddjj_media_url': 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html',
        'ddjj_forms_url': 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-formularios_y_plazos_2026-2171.html',
        'ddjj_software_houses_url': 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-casas_sw_2026-2171.html',
        'ddjj_certification_news_url': 'https://www.sii.cl/noticias/2025/241125noti03smn.htm',
        'ddjj_review_procedure_url': 'https://alerce.sii.cl/dior/dej/html/dj_autoverificacion.html',
    },
}

EXPECTED_DDJJ_MEDIA = {
    'formulario_electronico',
    'transferencia_archivos_importador',
    'transferencia_archivos_upload',
    'software_comercial',
    'asistente',
}


def _row(
    *,
    key: str,
    target_kind: str,
    source_type: str,
    source_url: str,
    evidence_reading: str,
    boundary: dict[str, Any] | None = None,
    supported_media: list[str] | None = None,
) -> dict[str, Any]:
    return {
        'key': key,
        'target_kind': target_kind,
        'source_type': source_type,
        'source_url': source_url,
        'verified_on': STAGE6_OFFICIAL_COMPATIBILITY_VERIFIED_ON,
        'evidence_reading': evidence_reading,
        'supported_media': supported_media or [],
        'boundary': {
            'public_api_confirmed': False,
            'official_submission_allowed': False,
            'final_tax_calculation': False,
            'content_consistency_certified': False,
            'requires_responsible_review': True,
            **(boundary or {}),
        },
    }


def build_stage6_official_compatibility_matrix(*, anio_tributario: int = 2026) -> dict[str, Any]:
    anio_tributario = int(anio_tributario)
    sources = OFFICIAL_COMPATIBILITY_SOURCES_BY_YEAR.get(anio_tributario)
    if sources is None:
        return {
            'schema_version': STAGE6_OFFICIAL_COMPATIBILITY_VERSION,
            'anio_tributario': anio_tributario,
            'verified_on': STAGE6_OFFICIAL_COMPATIBILITY_VERIFIED_ON,
            'supported_tax_years': sorted(OFFICIAL_COMPATIBILITY_SOURCES_BY_YEAR),
            'source_policy': (
                'Only public SII URLs and non-sensitive metadata. No SII session, no credentials, '
                'no EDIG execution, no real submission and no final tax calculation.'
            ),
            'public_api_general_available': False,
            'official_submission_allowed': False,
            'final_tax_calculation': False,
            'current_decision': 'Unsupported tax year; add explicit public SII evidence before use.',
            'known_gaps': [
                {
                    'key': f'official_compatibility_{anio_tributario}',
                    'status': 'unsupported_tax_year',
                    'required_before_official_use': True,
                }
            ],
            'rows': [],
        }

    rows = [
        _row(
            key=f'f22_certification_{anio_tributario}',
            target_kind='F22',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION,
            source_url=sources['f22_certification_url'],
            evidence_reading=(
                f'SII abre certificacion para casas de software que generan archivos F22 AT{anio_tributario}; '
                'la certificacion acredita recepcion/formato en el alcance informado, no contenido '
                'ni consistencia tributaria.'
            ),
            boundary={
                'certified_file_path_exists': True,
                'certified_file_requires_process': True,
                'requires_explicit_authorization': True,
            },
        ),
        _row(
            key=f'f22_instructions_{anio_tributario}',
            target_kind='F22',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_INSTRUCTIONS,
            source_url=sources['f22_instructions_url'],
            evidence_reading=f'SII publica guia/suplemento de Renta {anio_tributario} para codigos e instrucciones F22.',
        ),
        _row(
            key=f'f22_commercial_software_or_portal_{anio_tributario}',
            target_kind='F22',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_INSTRUCTIONS,
            source_url=F22_DECLARATION_OPTIONS_URL,
            evidence_reading=(
                'SII permite declarar F22 por formulario en pantalla, datos guardados o software '
                'comercial; no documenta una API REST general para presentacion autonoma.'
            ),
            boundary={'supervised_portal_path_exists': True},
        ),
        _row(
            key=f'ddjj_media_{anio_tributario}',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_MEDIA,
            source_url=sources['ddjj_media_url'],
            evidence_reading=f'SII publica medios por formulario DDJJ Renta {anio_tributario}.',
            supported_media=sorted(EXPECTED_DDJJ_MEDIA),
            boundary={'requires_form_specific_media': True},
        ),
        _row(
            key=f'ddjj_forms_{anio_tributario}',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_FORMS,
            source_url=sources['ddjj_forms_url'],
            evidence_reading=(
                f'SII publica formularios, plazos, instrucciones, certificados y resoluciones DDJJ AT{anio_tributario}.'
            ),
        ),
        _row(
            key=f'ddjj_software_houses_{anio_tributario}',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_SOFTWARE_HOUSES,
            source_url=sources['ddjj_software_houses_url'],
            evidence_reading=f'SII publica casas de software DDJJ AT{anio_tributario} y formularios certificados por proveedor.',
            boundary={'commercial_software_file_path_exists': True},
        ),
        _row(
            key=f'ddjj_certification_process_{anio_tributario}',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_SOFTWARE_HOUSES,
            source_url=sources['ddjj_review_procedure_url'],
            evidence_reading=(
                f'SII documenta la revision/certificacion de archivos DDJJ Renta AT{anio_tributario} para casas '
                'de software; este flujo es de archivo/upload controlado, no API REST general.'
            ),
            boundary={
                'format_review_help_exists': True,
                'file_upload_certification_path_exists': True,
                'public_api_confirmed': False,
                'production_environment_warning': anio_tributario == 2025,
            },
        ),
        _row(
            key=f'ddjj_certification_news_{anio_tributario}',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_SOFTWARE_HOUSES,
            source_url=sources['ddjj_certification_news_url'],
            evidence_reading=f'SII informa el proceso de certificacion de software DDJJ para Operacion Renta {anio_tributario}.',
            boundary={'certification_window_documented': True},
        ),
        _row(
            key=f'ddjj_importer_manual_{anio_tributario}',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_MEDIA,
            source_url=DDJJ_IMPORTER_MANUAL_URL,
            evidence_reading='SII documenta importador DDJJ como ruta de archivo/CSV, no API REST general.',
            boundary={'file_importer_path_exists': True},
        ),
    ]

    known_gaps: list[dict[str, Any]] = []
    f22_record_format_url = sources.get('f22_record_format_url')
    if f22_record_format_url:
        rows.insert(
            2,
            _row(
                key=f'f22_record_format_{anio_tributario}',
                target_kind='F22',
                source_type=TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION,
                source_url=f22_record_format_url,
                evidence_reading=f'SII publica formato de registro fixed-width para archivos F22 AT{anio_tributario}.',
                boundary={
                    'fixed_width_record_contract_exists': True,
                    'record_length': 90,
                    'record_types': ['0', '1'],
                },
            ),
        )
    else:
        known_gaps.append(
            {
                'key': f'f22_record_format_{anio_tributario}',
                'status': 'not_confirmed_from_public_source',
                'required_before_official_f22_file': True,
                'boundary': {
                    'fixed_width_record_contract_exists': False,
                    'official_submission_allowed': False,
                    'requires_explicit_sii_format_source': True,
                },
            }
        )

    return {
        'schema_version': STAGE6_OFFICIAL_COMPATIBILITY_VERSION,
        'anio_tributario': anio_tributario,
        'verified_on': STAGE6_OFFICIAL_COMPATIBILITY_VERIFIED_ON,
        'supported_tax_years': sorted(OFFICIAL_COMPATIBILITY_SOURCES_BY_YEAR),
        'source_policy': (
            'Only public SII URLs and non-sensitive metadata. No SII session, no credentials, '
            'no EDIG execution, no real submission and no final tax calculation.'
        ),
        'public_api_general_available': False,
        'official_submission_allowed': False,
        'final_tax_calculation': False,
        'current_decision': (
            'LeaseManager may generate local controlled export candidates and review dossiers. '
            'Official files/submission require current SII format/certification, explicit '
            'authorization and responsible tax review.'
        ),
        'known_gaps': known_gaps,
        'rows': rows,
    }


def validate_stage6_official_compatibility_matrix(matrix: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    rows = list(matrix.get('rows') or [])
    by_key = {row.get('key'): row for row in rows if isinstance(row, dict)}

    if matrix.get('schema_version') != STAGE6_OFFICIAL_COMPATIBILITY_VERSION:
        issues.append('schema_version_mismatch')
    anio_tributario = matrix.get('anio_tributario')
    if anio_tributario not in OFFICIAL_COMPATIBILITY_SOURCES_BY_YEAR:
        issues.append('unsupported_tax_year')
    if matrix.get('public_api_general_available') is True:
        issues.append('public_api_general_must_not_be_assumed')
    if matrix.get('official_submission_allowed') is True:
        issues.append('official_submission_must_remain_blocked')
    if matrix.get('final_tax_calculation') is True:
        issues.append('final_tax_calculation_must_remain_blocked')

    for row in rows:
        key = row.get('key') or 'unknown'
        source_url = row.get('source_url')
        boundary = row.get('boundary') or {}
        if not is_safe_public_sii_source_url(source_url):
            issues.append(f'{key}.source_url_not_safe_public_sii')
        if boundary.get('public_api_confirmed') is True and not is_safe_public_sii_source_url(boundary.get('api_evidence_url')):
            issues.append(f'{key}.public_api_without_safe_evidence')
        if boundary.get('official_submission_allowed') is True:
            issues.append(f'{key}.official_submission_must_not_be_enabled')
        if boundary.get('final_tax_calculation') is True:
            issues.append(f'{key}.final_tax_calculation_must_not_be_enabled')
        if boundary.get('content_consistency_certified') is True:
            issues.append(f'{key}.content_consistency_must_not_be_certified_by_sii_file_gate')

    f22_certification = by_key.get(f'f22_certification_{anio_tributario}') or {}
    if not f22_certification:
        issues.append(f'f22_certification_{anio_tributario}_missing')
    else:
        boundary = f22_certification.get('boundary') or {}
        if boundary.get('certified_file_path_exists') is not True:
            issues.append(f'f22_certification_{anio_tributario}.certified_file_path_missing')
        if boundary.get('public_api_confirmed') is True:
            issues.append(f'f22_certification_{anio_tributario}.public_api_must_not_be_confirmed')
        if boundary.get('content_consistency_certified') is True:
            issues.append(f'f22_certification_{anio_tributario}.content_consistency_must_not_be_certified')

    f22_record_format = by_key.get(f'f22_record_format_{anio_tributario}') or {}
    known_gap_keys = {gap.get('key') for gap in matrix.get('known_gaps') or [] if isinstance(gap, dict)}
    if not f22_record_format and f'f22_record_format_{anio_tributario}' not in known_gap_keys:
        issues.append(f'f22_record_format_{anio_tributario}_missing_or_gap_not_explicit')
    else:
        boundary = f22_record_format.get('boundary') or {}
        if f22_record_format:
            if boundary.get('fixed_width_record_contract_exists') is not True:
                issues.append(f'f22_record_format_{anio_tributario}.fixed_width_contract_missing')
            if boundary.get('record_length') != 90:
                issues.append(f'f22_record_format_{anio_tributario}.record_length_mismatch')
            if set(boundary.get('record_types') or []) != {'0', '1'}:
                issues.append(f'f22_record_format_{anio_tributario}.record_types_mismatch')

    ddjj_media = by_key.get(f'ddjj_media_{anio_tributario}') or {}
    media = set(ddjj_media.get('supported_media') or [])
    missing_media = sorted(EXPECTED_DDJJ_MEDIA - media)
    if not ddjj_media:
        issues.append(f'ddjj_media_{anio_tributario}_missing')
    elif missing_media:
        issues.append(f"ddjj_media_{anio_tributario}.missing_media:{','.join(missing_media)}")

    if f'ddjj_certification_process_{anio_tributario}' not in by_key:
        issues.append(f'ddjj_certification_process_{anio_tributario}_missing')
    if f'ddjj_certification_news_{anio_tributario}' not in by_key:
        issues.append(f'ddjj_certification_news_{anio_tributario}_missing')
    if f'ddjj_importer_manual_{anio_tributario}' not in by_key:
        issues.append(f'ddjj_importer_manual_{anio_tributario}_missing')

    return issues


def assert_stage6_official_compatibility_matrix(matrix: dict[str, Any]) -> None:
    issues = validate_stage6_official_compatibility_matrix(matrix)
    if issues:
        raise ValueError('; '.join(issues))


def clone_stage6_official_compatibility_matrix(*, anio_tributario: int = 2026) -> dict[str, Any]:
    return deepcopy(build_stage6_official_compatibility_matrix(anio_tributario=anio_tributario))
