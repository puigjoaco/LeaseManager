from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from core.annual_tax_source_manifest import payload_hash


LOAD_PLAN_SCHEMA_VERSION = 'annual-tax-controlled-load-plan.v1'

CALCULATION_INPUT_CATEGORIES = {
    'annual_ledger_input',
    'rcv_structured_input',
    'f29_support_input',
    'purchase_sales_books_support',
    'payroll_support',
    'real_estate_support',
    'tax_certificate_support',
}

COMPARISON_ONLY_CATEGORIES = {
    'annual_balance_expected_output',
    'annual_tax_register_expected_output',
    'ddjj_expected_output',
    'f22_expected_output',
}

CATEGORY_TARGETS = {
    'annual_ledger_input': {
        'target_models': ['contabilidad.LibroDiario', 'contabilidad.LibroMayor', 'sii.AnnualTaxTrialBalanceLine'],
        'load_mode': 'pdf_or_controlled_manual_extraction_to_ledger_snapshots',
        'parser_status': 'blocked_pdf_or_manual_extraction_required',
    },
    'rcv_structured_input': {
        'target_models': [
            'contabilidad.ObligacionTributariaMensual',
            'sii.F29PreparacionMensual',
            'sii.MonthlyTaxFact',
        ],
        'load_mode': 'csv_structured_monthly_facts',
        'parser_status': 'ready_for_loader_implementation',
    },
    'f29_support_input': {
        'target_models': ['contabilidad.ObligacionTributariaMensual', 'sii.F29PreparacionMensual'],
        'load_mode': 'f29_pdf_or_controlled_manual_summary',
        'parser_status': 'blocked_pdf_or_manual_extraction_required',
    },
    'purchase_sales_books_support': {
        'target_models': ['contabilidad.LibroDiario', 'contabilidad.LibroMayor', 'sii.MonthlyTaxFact'],
        'load_mode': 'support_reconciliation_against_rcv_and_ledger',
        'parser_status': 'support_only_pdf_review_required',
    },
    'payroll_support': {
        'target_models': ['sii.MonthlyTaxFact', 'sii.DDJJPreparacionAnual'],
        'load_mode': 'payroll_support_for_dj1887',
        'parser_status': 'blocked_pdf_or_manual_extraction_required',
    },
    'real_estate_support': {
        'target_models': ['sii.AnnualRealEstateSection'],
        'load_mode': 'real_estate_contributions_support',
        'parser_status': 'blocked_until_source_present',
    },
    'tax_certificate_support': {
        'target_models': ['sii.AnnualTaxOfficialSource'],
        'load_mode': 'reference_only_official_support',
        'parser_status': 'reference_only',
    },
    'annual_balance_expected_output': {
        'target_models': ['contabilidad.BalanceComprobacion', 'sii.AnnualTaxTrialBalance'],
        'load_mode': 'comparison_target_only',
        'parser_status': 'not_loaded_as_input',
    },
    'annual_tax_register_expected_output': {
        'target_models': [
            'sii.AnnualTaxWorkbook',
            'sii.AnnualEnterpriseRegisterSet',
            'sii.AnnualTaxDossier',
        ],
        'load_mode': 'comparison_target_only',
        'parser_status': 'not_loaded_as_input',
    },
    'ddjj_expected_output': {
        'target_models': ['sii.DDJJPreparacionAnual', 'sii.AnnualTaxArtifactMatrix'],
        'load_mode': 'comparison_target_only',
        'parser_status': 'not_loaded_as_input',
    },
    'f22_expected_output': {
        'target_models': ['sii.F22PreparacionAnual', 'sii.AnnualTaxExport'],
        'load_mode': 'comparison_target_only',
        'parser_status': 'not_loaded_as_input',
    },
    'bank_reconciliation_candidate': {
        'target_models': ['conciliacion.MovimientoBancarioImportado', 'conciliacion.CuadraturaBancaria'],
        'load_mode': 'bank_reconciliation_support',
        'parser_status': 'blocked_until_source_present',
    },
    'unclassified_support': {
        'target_models': [],
        'load_mode': 'manual_classification_required',
        'parser_status': 'blocked_unclassified',
    },
}


def _files_by_category(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in manifest.get('files') or []:
        grouped[str(item.get('category') or 'unclassified_support')].append(item)
    return dict(grouped)


def _months_from_files(files: list[dict[str, Any]]) -> list[int]:
    months = set()
    for item in files:
        for month in item.get('months') or []:
            try:
                normalized = int(month)
            except (TypeError, ValueError):
                continue
            if 1 <= normalized <= 12:
                months.add(normalized)
    return sorted(months)


def _forms_from_files(files: list[dict[str, Any]]) -> list[str]:
    forms = set()
    for item in files:
        for form in item.get('ddjj_forms') or []:
            normalized = str(form or '').strip()
            if normalized:
                forms.add(normalized)
    return sorted(forms)


def _artifact_keys_from_files(files: list[dict[str, Any]]) -> list[str]:
    keys = {
        str(item.get('artifact_key') or '').strip()
        for item in files
        if str(item.get('artifact_key') or '').strip()
    }
    return sorted(keys)


def _category_item(category: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    target = CATEGORY_TARGETS.get(category, CATEGORY_TARGETS['unclassified_support'])
    role = 'comparison_only' if category in COMPARISON_ONLY_CATEGORIES else (
        'calculation_input' if category in CALCULATION_INPUT_CATEGORIES else 'support'
    )
    parser_status = target['parser_status']
    if category in COMPARISON_ONLY_CATEGORIES:
        status = 'comparison_target_only'
    elif parser_status == 'ready_for_loader_implementation':
        status = 'ready_for_loader'
    elif parser_status in {'reference_only', 'support_only_pdf_review_required'}:
        status = 'support_only'
    else:
        status = 'blocked'

    return {
        'category': category,
        'role': role,
        'status': status,
        'files_total': len(files),
        'months': _months_from_files(files),
        'ddjj_forms': _forms_from_files(files),
        'artifact_keys': _artifact_keys_from_files(files),
        'target_models': target['target_models'],
        'load_mode': target['load_mode'],
        'parser_status': parser_status,
        'used_as_calculation_input': role == 'calculation_input',
        'used_as_comparison_target': role == 'comparison_only',
    }


def build_annual_tax_controlled_load_plan(*, manifest: dict[str, Any]) -> dict[str, Any]:
    files = manifest.get('files') or []
    coverage = manifest.get('coverage') if isinstance(manifest.get('coverage'), dict) else {}
    mirror = (
        manifest.get('mirror_proof_readiness')
        if isinstance(manifest.get('mirror_proof_readiness'), dict)
        else {}
    )
    grouped = _files_by_category(manifest)
    categories = sorted(set(CATEGORY_TARGETS).union(grouped))
    load_items = [_category_item(category, grouped.get(category, [])) for category in categories]

    calculation_items = [item for item in load_items if item['used_as_calculation_input']]
    comparison_items = [item for item in load_items if item['used_as_comparison_target']]
    expected_outputs_as_inputs = [
        item['category']
        for item in load_items
        if item['category'] in COMPARISON_ONLY_CATEGORIES and item['used_as_calculation_input']
    ]
    blocking_items = [
        item
        for item in load_items
        if item['role'] == 'calculation_input' and item['status'] == 'blocked' and item['files_total'] > 0
    ]
    missing_required_files = [
        item['category']
        for item in load_items
        if item['category'] in {
            'annual_ledger_input',
            'rcv_structured_input',
            'annual_balance_expected_output',
            'annual_tax_register_expected_output',
            'ddjj_expected_output',
            'f22_expected_output',
        }
        and item['files_total'] == 0
    ]
    blockers = []
    if not files:
        blockers.append('manifest_file_list_missing')
    if not coverage.get('ready_for_mirror_source_bundle'):
        blockers.append('source_documentation_not_complete')
    if expected_outputs_as_inputs:
        blockers.append('expected_outputs_misclassified_as_calculation_input')
    if missing_required_files:
        blockers.append('required_source_categories_missing')
    if blocking_items:
        blockers.append('calculation_input_parsers_or_manual_load_required')

    source_ready = bool(coverage.get('ready_for_mirror_source_bundle'))
    expected_outputs_excluded = not expected_outputs_as_inputs
    ready_for_db_load = source_ready and expected_outputs_excluded and not blocking_items and not missing_required_files and bool(files)

    plan_summary = {
        'source_documentation_confirmed_for_ac2024_at2025': source_ready,
        'expected_outputs_used_as_inputs': bool(expected_outputs_as_inputs),
        'expected_outputs_excluded_from_calculation_inputs': expected_outputs_excluded,
        'calculation_input_categories': [item['category'] for item in calculation_items if item['files_total']],
        'comparison_target_categories': [item['category'] for item in comparison_items if item['files_total']],
        'blocking_input_categories': [item['category'] for item in blocking_items],
        'ready_for_db_load': ready_for_db_load,
        'ready_for_mirror_generation': False,
        'reason_not_ready_for_mirror_generation': (
            'normalized_source_package_not_ready'
            if not ready_for_db_load
            else 'expected_output_value_equality_completion_missing'
        ),
        'missing_capabilities_after_plan': [
            'normalized_controlled_source_package_values_required' if not ready_for_db_load else '',
            'expected_output_value_equality_completion',
        ],
    }
    plan_summary['missing_capabilities_after_plan'] = [
        item for item in plan_summary['missing_capabilities_after_plan'] if item
    ]

    plan_payload = {
        'schema_version': LOAD_PLAN_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_manifest_schema_version': manifest.get('schema_version', ''),
        'company_ref': manifest.get('company_ref', ''),
        'commercial_year': manifest.get('commercial_year'),
        'tax_year': manifest.get('tax_year'),
        'source_root_ref': manifest.get('source_root_ref', ''),
        'manifest_hash': payload_hash(
            {
                'schema_version': manifest.get('schema_version', ''),
                'source_root_ref': manifest.get('source_root_ref', ''),
                'summary': manifest.get('summary', {}),
                'coverage': coverage,
                'annual_tax_source_bundle_draft': manifest.get('annual_tax_source_bundle_draft', {}),
            }
        ),
        'safety': {
            'read_only_manifest': True,
            'writes_database': False,
            'copies_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'expected_outputs_used_as_inputs': bool(expected_outputs_as_inputs),
        },
        'source_confirmation': {
            'source_documentation_confirmed_for_ac2024_at2025': source_ready,
            'manifest_ready_for_mirror_source_bundle': coverage.get('ready_for_mirror_source_bundle', False),
            'mirror_architecture_complete_before_plan': mirror.get('architecture_complete_for_mirror_run', False),
        },
        'summary': plan_summary,
        'load_items': load_items,
        'blockers': sorted(set(blockers)),
        'next_actions': [
            'Generar y completar template de carga controlada para Libro Diario, Libro Mayor, Inventario, F29 PDF y remuneraciones.',
            'Aplicar writer DB local con apply_annual_tax_controlled_db_load sobre un paquete normalizado validado.',
            'Generar artefactos LeaseManager AT2025 desde esa DB local.',
            'Implementar extractores de valores contra Balance/RLI/CPT/DDJJ/F22 definitivos sin usarlos como input de calculo.',
        ],
    }
    return plan_payload


def load_manifest_json(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Manifest JSON must be an object.')
    return payload
