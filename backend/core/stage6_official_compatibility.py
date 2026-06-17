from __future__ import annotations

from copy import deepcopy
from typing import Any

from sii.models import TipoAnnualTaxOfficialSource, is_safe_public_sii_source_url


STAGE6_OFFICIAL_COMPATIBILITY_VERSION = 'stage6-official-compatibility-at2026-v1'
STAGE6_OFFICIAL_COMPATIBILITY_VERIFIED_ON = '2026-06-17'

DDJJ_MEDIA_2026_URL = 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html'
DDJJ_FORMS_2026_URL = 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-formularios_y_plazos_2026-2171.html'
DDJJ_SOFTWARE_HOUSES_2026_URL = 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-casas_sw_2026-2171.html'
DDJJ_AUTOVERIFICATION_2026_URL = 'https://alerce.sii.cl/dior/dej/html/dj_autoverificacion.html'
DDJJ_IMPORTER_MANUAL_URL = 'https://alerce.sii.cl/dior/dej/html/manual/DJ_Manual/01.html'
F22_CERTIFICATION_2026_URL = 'https://www.sii.cl/noticias/2026/060226noti02pcr.htm'
F22_INSTRUCTIONS_2026_URL = 'https://www.sii.cl/servicios_online/renta/guia_trib_suplemento_2026.html'
F22_DECLARATION_OPTIONS_2026_URL = 'https://www.sii.cl/preguntas_frecuentes/declaracion_renta/001_140_8395.htm'

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
    rows = [
        _row(
            key='f22_certification_2026',
            target_kind='F22',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION,
            source_url=F22_CERTIFICATION_2026_URL,
            evidence_reading=(
                'SII abre certificacion para casas de software que generan archivos F22 AT2026; '
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
            key='f22_instructions_2026',
            target_kind='F22',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_INSTRUCTIONS,
            source_url=F22_INSTRUCTIONS_2026_URL,
            evidence_reading='SII publica guia/suplemento de Renta 2026 para codigos e instrucciones F22.',
        ),
        _row(
            key='f22_commercial_software_or_portal_2026',
            target_kind='F22',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_INSTRUCTIONS,
            source_url=F22_DECLARATION_OPTIONS_2026_URL,
            evidence_reading=(
                'SII permite declarar F22 por formulario en pantalla, datos guardados o software '
                'comercial; no documenta una API REST general para presentacion autonoma.'
            ),
            boundary={'supervised_portal_path_exists': True},
        ),
        _row(
            key='ddjj_media_2026',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_MEDIA,
            source_url=DDJJ_MEDIA_2026_URL,
            evidence_reading='SII publica medios por formulario DDJJ Renta 2026.',
            supported_media=sorted(EXPECTED_DDJJ_MEDIA),
            boundary={'requires_form_specific_media': True},
        ),
        _row(
            key='ddjj_forms_2026',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_FORMS,
            source_url=DDJJ_FORMS_2026_URL,
            evidence_reading='SII publica formularios, plazos, instrucciones, certificados y resoluciones DDJJ AT2026.',
        ),
        _row(
            key='ddjj_software_houses_2026',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_SOFTWARE_HOUSES,
            source_url=DDJJ_SOFTWARE_HOUSES_2026_URL,
            evidence_reading='SII publica casas de software DDJJ AT2026 y formularios certificados por proveedor.',
            boundary={'commercial_software_file_path_exists': True},
        ),
        _row(
            key='ddjj_autoverification_2026',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_SOFTWARE_HOUSES,
            source_url=DDJJ_AUTOVERIFICATION_2026_URL,
            evidence_reading='SII publica ayudas de revision/autoverificacion DDJJ Renta AT2026.',
            boundary={'format_review_help_exists': True},
        ),
        _row(
            key='ddjj_importer_manual',
            target_kind='DDJJ',
            source_type=TipoAnnualTaxOfficialSource.SII_DDJJ_MEDIA,
            source_url=DDJJ_IMPORTER_MANUAL_URL,
            evidence_reading='SII documenta importador DDJJ como ruta de archivo/CSV, no API REST general.',
            boundary={'file_importer_path_exists': True},
        ),
    ]

    return {
        'schema_version': STAGE6_OFFICIAL_COMPATIBILITY_VERSION,
        'anio_tributario': int(anio_tributario),
        'verified_on': STAGE6_OFFICIAL_COMPATIBILITY_VERIFIED_ON,
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
        'rows': rows,
    }


def validate_stage6_official_compatibility_matrix(matrix: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    rows = list(matrix.get('rows') or [])
    by_key = {row.get('key'): row for row in rows if isinstance(row, dict)}

    if matrix.get('schema_version') != STAGE6_OFFICIAL_COMPATIBILITY_VERSION:
        issues.append('schema_version_mismatch')
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

    f22_certification = by_key.get('f22_certification_2026') or {}
    if not f22_certification:
        issues.append('f22_certification_2026_missing')
    else:
        boundary = f22_certification.get('boundary') or {}
        if boundary.get('certified_file_path_exists') is not True:
            issues.append('f22_certification_2026.certified_file_path_missing')
        if boundary.get('public_api_confirmed') is True:
            issues.append('f22_certification_2026.public_api_must_not_be_confirmed')
        if boundary.get('content_consistency_certified') is True:
            issues.append('f22_certification_2026.content_consistency_must_not_be_certified')

    ddjj_media = by_key.get('ddjj_media_2026') or {}
    media = set(ddjj_media.get('supported_media') or [])
    missing_media = sorted(EXPECTED_DDJJ_MEDIA - media)
    if not ddjj_media:
        issues.append('ddjj_media_2026_missing')
    elif missing_media:
        issues.append(f"ddjj_media_2026.missing_media:{','.join(missing_media)}")

    if 'ddjj_autoverification_2026' not in by_key:
        issues.append('ddjj_autoverification_2026_missing')
    if 'ddjj_importer_manual' not in by_key:
        issues.append('ddjj_importer_manual_missing')

    return issues


def assert_stage6_official_compatibility_matrix(matrix: dict[str, Any]) -> None:
    issues = validate_stage6_official_compatibility_matrix(matrix)
    if issues:
        raise ValueError('; '.join(issues))


def clone_stage6_official_compatibility_matrix(*, anio_tributario: int = 2026) -> dict[str, Any]:
    return deepcopy(build_stage6_official_compatibility_matrix(anio_tributario=anio_tributario))
