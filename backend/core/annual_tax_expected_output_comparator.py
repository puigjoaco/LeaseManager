from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from contabilidad.models import EstadoPreparacionTributaria
from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.annual_tax_expected_output_content import extract_expected_output_content_signals
from core.annual_tax_source_manifest import EXPECTED_DDJJ_FORMS, EXPECTED_ANNUAL_TAX_REGISTER_KEYS
from sii.models import (
    AnnualEnterpriseRegisterSet,
    AnnualTaxArtifactMatrix,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxReviewChecklist,
    AnnualTaxTrialBalance,
    AnnualTaxWorkbook,
    DDJJPreparacionAnual,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxReviewChecklist,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    F22PreparacionAnual,
    ProcesoRentaAnual,
    TipoAnnualEnterpriseRegister,
    TipoAnnualTaxWorkbook,
)


EXPECTED_OUTPUT_COMPARISON_SCHEMA_VERSION = 'annual-tax-expected-output-comparison.v1'

REGISTER_KEY_TARGETS = {
    'capital_propio': {'workbooks': {TipoAnnualTaxWorkbook.CPT}, 'enterprise_registers': set()},
    'razonabilidad_cpt': {'workbooks': {TipoAnnualTaxWorkbook.CPT}, 'enterprise_registers': set()},
    'renta_liquida': {'workbooks': {TipoAnnualTaxWorkbook.RLI}, 'enterprise_registers': set()},
    'determinacion_rai': {'workbooks': set(), 'enterprise_registers': {TipoAnnualEnterpriseRegister.RAI}},
    'rentas_empresariales': {
        'workbooks': set(),
        'enterprise_registers': {
            TipoAnnualEnterpriseRegister.RAI,
            TipoAnnualEnterpriseRegister.SAC,
            TipoAnnualEnterpriseRegister.RETIROS,
            TipoAnnualEnterpriseRegister.DIVIDENDOS,
        },
    },
}


def _normalize_forms(values: Any) -> list[str]:
    forms = set()
    for value in values or []:
        normalized = str(value or '').strip()
        if normalized:
            forms.add(normalized)
    return sorted(forms)


def _files_by_category(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in manifest.get('files') or []:
        category = str(item.get('category') or '').strip()
        if category in COMPARISON_ONLY_CATEGORIES:
            grouped[category].append(item)
    return dict(grouped)


def _artifact_keys(files: list[dict[str, Any]]) -> list[str]:
    keys = {
        str(item.get('artifact_key') or '').strip()
        for item in files
        if str(item.get('artifact_key') or '').strip()
    }
    return sorted(keys)


def _expected_ddjj_forms(files: list[dict[str, Any]]) -> list[str]:
    forms = set()
    for item in files:
        if str(item.get('output_status') or '').strip() != 'accepted':
            continue
        for form in item.get('ddjj_forms') or []:
            normalized = str(form or '').strip()
            if normalized:
                forms.add(normalized)
    return sorted(forms)


def _generated_process(empresa, tax_year: int) -> ProcesoRentaAnual | None:
    return (
        ProcesoRentaAnual.objects.filter(empresa=empresa, anio_tributario=tax_year)
        .select_related('source_bundle')
        .first()
    )


def _generated_inventory(process: ProcesoRentaAnual | None) -> dict[str, Any]:
    if process is None:
        return {
            'process_present': False,
            'prepared_trial_balance_count': 0,
            'prepared_workbook_types': [],
            'prepared_enterprise_register_types': [],
            'prepared_ddjj_forms': [],
            'prepared_f22': False,
            'artifact_matrix_present': False,
            'dossier_present': False,
            'export_present': False,
            'review_checklist_present': False,
            'review_warning_counts': {},
            'review_blockers_total': 0,
        }

    trial_balances = AnnualTaxTrialBalance.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxTrialBalance.PREPARED,
    )
    workbooks = AnnualTaxWorkbook.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
    )
    registers = AnnualEnterpriseRegisterSet.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualEnterpriseRegister.PREPARED,
    )
    ddjj = DDJJPreparacionAnual.objects.filter(
        proceso_renta_anual=process,
        estado_preparacion=EstadoPreparacionTributaria.PREPARED,
    ).first()
    f22 = F22PreparacionAnual.objects.filter(
        proceso_renta_anual=process,
        estado_preparacion=EstadoPreparacionTributaria.PREPARED,
    ).first()
    matrix = AnnualTaxArtifactMatrix.objects.filter(proceso_renta_anual=process).first()
    dossier = AnnualTaxDossier.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxDossier.PREPARED,
    ).first()
    annual_export = AnnualTaxExport.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxExport.PREPARED,
    ).first()
    checklist = AnnualTaxReviewChecklist.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxReviewChecklist.PREPARED,
    ).first()

    ddjj_summary = ddjj.resumen_paquete if ddjj and isinstance(ddjj.resumen_paquete, dict) else {}
    prepared_ddjj_forms = _normalize_forms(ddjj_summary.get('ddjj_habilitadas'))

    review_warning_counts = Counter()
    review_blockers_total = 0
    if matrix is not None:
        matrix_summary = matrix.resumen_matriz if isinstance(matrix.resumen_matriz, dict) else {}
        review_warning_counts['artifact_matrix_warnings'] += int(matrix_summary.get('warnings_total') or 0)
        review_states = matrix_summary.get('review_state_counts') if isinstance(matrix_summary, dict) else {}
        if isinstance(review_states, dict):
            review_blockers_total += int(review_states.get(EstadoAnnualTaxArtifactReview.BLOCKED) or 0)
    if dossier is not None:
        review_warning_counts['dossier_warnings'] += int(dossier.warnings_total or 0)
        if dossier.review_state != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW:
            review_warning_counts[f'dossier_{dossier.review_state}'] += 1
    if annual_export is not None:
        review_warning_counts['export_warnings'] += int(annual_export.warnings_total or 0)
        if annual_export.review_state != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW:
            review_warning_counts[f'export_{annual_export.review_state}'] += 1
    if checklist is not None:
        review_warning_counts['checklist_warnings'] += int(checklist.warnings_total or 0)
        review_blockers_total += int(checklist.blockers_total or 0)

    return {
        'process_present': True,
        'process_id': process.id,
        'process_state': process.estado,
        'source_bundle_id': process.source_bundle_id,
        'prepared_trial_balance_count': trial_balances.count(),
        'prepared_workbook_types': sorted({str(item.tipo) for item in workbooks}),
        'prepared_enterprise_register_types': sorted({str(item.tipo_registro) for item in registers}),
        'prepared_ddjj_forms': prepared_ddjj_forms,
        'prepared_f22': f22 is not None,
        'artifact_matrix_present': matrix is not None,
        'dossier_present': dossier is not None,
        'export_present': annual_export is not None,
        'review_checklist_present': checklist is not None,
        'review_warning_counts': dict(sorted((key, value) for key, value in review_warning_counts.items() if value)),
        'review_blockers_total': review_blockers_total,
    }


def _compare_balance(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected = bool(expected_files)
    generated = int(inventory['prepared_trial_balance_count']) > 0
    return {
        'expected': expected,
        'expected_files': len(expected_files),
        'expected_artifact_keys': _artifact_keys(expected_files),
        'generated': generated,
        'generated_count': inventory['prepared_trial_balance_count'],
        'matched': not expected or generated,
    }


def _compare_registers(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected_keys = _artifact_keys(expected_files)
    generated_workbooks = set(inventory['prepared_workbook_types'])
    generated_registers = set(inventory['prepared_enterprise_register_types'])
    by_key = {}
    missing = []
    for key in expected_keys:
        spec = REGISTER_KEY_TARGETS.get(key, {'workbooks': set(), 'enterprise_registers': set()})
        required_workbooks = {str(value) for value in spec['workbooks']}
        required_registers = {str(value) for value in spec['enterprise_registers']}
        missing_workbooks = sorted(required_workbooks - generated_workbooks)
        missing_registers = sorted(required_registers - generated_registers)
        matched = not missing_workbooks and not missing_registers
        by_key[key] = {
            'required_workbooks': sorted(required_workbooks),
            'required_enterprise_registers': sorted(required_registers),
            'missing_workbooks': missing_workbooks,
            'missing_enterprise_registers': missing_registers,
            'matched': matched,
        }
        if not matched:
            missing.append(key)
    return {
        'expected_artifact_keys': expected_keys,
        'generated_workbook_types': sorted(generated_workbooks),
        'generated_enterprise_register_types': sorted(generated_registers),
        'by_key': by_key,
        'missing_artifact_keys': sorted(missing),
        'matched': not missing,
    }


def _compare_ddjj(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected_forms = _expected_ddjj_forms(expected_files)
    generated_forms = set(inventory['prepared_ddjj_forms'])
    missing_forms = sorted(set(expected_forms) - generated_forms)
    unexpected_forms = sorted(generated_forms - set(EXPECTED_DDJJ_FORMS))
    return {
        'expected_forms': expected_forms,
        'generated_forms': sorted(generated_forms),
        'missing_forms': missing_forms,
        'unexpected_forms': unexpected_forms,
        'matched': not missing_forms,
    }


def _compare_f22(expected_files: list[dict[str, Any]], inventory: dict[str, Any]) -> dict[str, Any]:
    expected = bool(expected_files)
    generated = bool(inventory['prepared_f22'])
    return {
        'expected': expected,
        'expected_files': len(expected_files),
        'expected_artifact_keys': _artifact_keys(expected_files),
        'generated': generated,
        'matched': not expected or generated,
    }


def compare_annual_tax_expected_outputs(
    *,
    empresa,
    commercial_year: int,
    tax_year: int,
    manifest: dict[str, Any],
    source_root: Path | None = None,
) -> dict[str, Any]:
    if tax_year != commercial_year + 1:
        raise ValueError('tax_year debe ser commercial_year + 1.')

    grouped = _files_by_category(manifest)
    process = _generated_process(empresa, tax_year)
    inventory = _generated_inventory(process)
    matches = {
        'annual_balance_expected_output': _compare_balance(
            grouped.get('annual_balance_expected_output', []),
            inventory,
        ),
        'annual_tax_register_expected_output': _compare_registers(
            grouped.get('annual_tax_register_expected_output', []),
            inventory,
        ),
        'ddjj_expected_output': _compare_ddjj(grouped.get('ddjj_expected_output', []), inventory),
        'f22_expected_output': _compare_f22(grouped.get('f22_expected_output', []), inventory),
    }
    coverage_match_keys = tuple(matches.keys())

    content_signals = None
    content_identity_ready = False
    value_equality_extractors_ready = False
    if source_root is not None:
        content_signals = extract_expected_output_content_signals(source_root=source_root, manifest=manifest)
        content_summary = content_signals['summary']
        content_ddjj_forms = set(content_summary['accepted_ddjj_forms_from_content'])
        generated_forms = set(inventory['prepared_ddjj_forms'])
        matches['ddjj_content_identity'] = {
            'expected_forms_from_content': sorted(content_ddjj_forms),
            'generated_forms': sorted(generated_forms),
            'missing_forms': sorted(content_ddjj_forms - generated_forms),
            'accepted_folios_by_form': content_summary['accepted_ddjj_folios_by_form'],
            'matched': bool(content_ddjj_forms) and not (content_ddjj_forms - generated_forms),
        }
        matches['f22_content_identity'] = {
            'expected_folios_from_content': content_summary['f22_folios_from_content'],
            'generated_f22_present': bool(inventory['prepared_f22']),
            'official_folio_generated': False,
            'matched': bool(content_summary['f22_folios_from_content']) and bool(inventory['prepared_f22']),
        }
        matches['annual_balance_content_identity'] = {
            'expected_text_extractable': bool(content_summary['balance_text_extractable']),
            'generated_trial_balance_present': int(inventory['prepared_trial_balance_count']) > 0,
            'matched': bool(content_summary['balance_text_extractable'])
            and int(inventory['prepared_trial_balance_count']) > 0,
        }
        matches['annual_tax_register_content_identity'] = {
            'expected_register_keys_with_text': content_summary['annual_tax_register_keys_with_text'],
            'generated_workbook_types': inventory['prepared_workbook_types'],
            'generated_enterprise_register_types': inventory['prepared_enterprise_register_types'],
            'missing_expected_register_text': sorted(
                set(EXPECTED_ANNUAL_TAX_REGISTER_KEYS) - set(content_summary['annual_tax_register_keys_with_text'])
            ),
            'matched': set(content_summary['annual_tax_register_keys_with_text'])
            >= set(EXPECTED_ANNUAL_TAX_REGISTER_KEYS),
        }
        content_identity_ready = (
            bool(content_summary['identity_signals_ready'])
            and matches['ddjj_content_identity']['matched']
            and matches['f22_content_identity']['matched']
            and matches['annual_balance_content_identity']['matched']
            and matches['annual_tax_register_content_identity']['matched']
        )

    coverage_ready = bool(inventory['process_present']) and all(matches[key]['matched'] for key in coverage_match_keys)
    review_warning_counts = inventory['review_warning_counts']
    review_blockers_total = int(inventory['review_blockers_total'])

    blockers = []
    if not inventory['process_present']:
        blockers.append('annual_process_missing')
    if not all(matches[key]['matched'] for key in coverage_match_keys):
        blockers.append('expected_output_coverage_mismatch')
    if review_warning_counts or review_blockers_total:
        blockers.append('generated_artifacts_require_review')
    if source_root is None:
        blockers.append('expected_output_identity_extractors_not_run')
    elif content_signals and content_signals['extraction_errors']:
        blockers.append('expected_output_identity_extraction_errors')
    elif not content_identity_ready:
        blockers.append('expected_output_identity_mismatch')
    if not value_equality_extractors_ready:
        blockers.append('expected_output_value_extractors_missing')

    return {
        'schema_version': EXPECTED_OUTPUT_COMPARISON_SCHEMA_VERSION,
        'empresa_id': empresa.id,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': manifest.get('hash_manifest') or manifest.get('source_manifest_hash') or '',
        'comparison_scope': {
            'level': 'coverage_traceability_and_identity' if source_root is not None else 'coverage_and_traceability',
            'content_identity_extraction_performed': source_root is not None,
            'content_comparison_performed': source_root is not None,
            'numeric_equality_performed': False,
            'categories': sorted(COMPARISON_ONLY_CATEGORIES),
        },
        'expected_targets': {
            category: {
                'files': len(files),
                'artifact_keys': _artifact_keys(files),
                'ddjj_forms': _expected_ddjj_forms(files) if category == 'ddjj_expected_output' else [],
            }
            for category, files in sorted(grouped.items())
        },
        'generated_inventory': inventory,
        'expected_output_content_signals': content_signals,
        'matches': matches,
        'summary': {
            'coverage_ready_for_content_comparison': coverage_ready,
            'content_identity_extractors_ready': content_identity_ready,
            'value_equality_extractors_ready': value_equality_extractors_ready,
            'ready_for_mirror_conclusion': (
                coverage_ready
                and content_identity_ready
                and value_equality_extractors_ready
                and not review_warning_counts
                and review_blockers_total == 0
            ),
            'blockers': blockers,
        },
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'final_tax_calculation': False,
            'stores_raw_expected_output_text': False,
        },
    }
