from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_load_plan import CALCULATION_INPUT_CATEGORIES, COMPARISON_ONLY_CATEGORIES
from core.annual_tax_source_manifest import payload_hash


CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION = 'annual-tax-controlled-db-load-template.v1'
MONTHS = tuple(range(1, 13))

MONTHLY_INPUT_CATEGORIES = (
    'rcv_structured_input',
    'f29_support_input',
    'purchase_sales_books_support',
    'payroll_support',
)

ANNUAL_INPUT_CATEGORIES = (
    'annual_ledger_input',
    'real_estate_support',
    'tax_certificate_support',
)


def _files_by_category(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in manifest.get('files') or []:
        if isinstance(item, dict):
            grouped[str(item.get('category') or 'unclassified_support')].append(item)
    return dict(grouped)


def _file_ref(item: dict[str, Any]) -> dict[str, Any]:
    return {
        'path_ref': item.get('path_ref', ''),
        'category': item.get('category', ''),
        'artifact_key': item.get('artifact_key', ''),
        'months': item.get('months') or [],
        'ddjj_forms': item.get('ddjj_forms') or [],
        'output_status': item.get('output_status', ''),
        'sha256': item.get('sha256', ''),
    }


def _month_refs(grouped: dict[str, list[dict[str, Any]]], month: int) -> dict[str, list[dict[str, Any]]]:
    refs: dict[str, list[dict[str, Any]]] = {}
    for category in MONTHLY_INPUT_CATEGORIES:
        refs[category] = [
            _file_ref(item)
            for item in grouped.get(category, [])
            if month in [int(raw) for raw in item.get('months') or []]
        ]
    return refs


def _annual_refs(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        category: [_file_ref(item) for item in grouped.get(category, [])]
        for category in ANNUAL_INPUT_CATEGORIES
    }


def _comparison_refs(grouped: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        category: [_file_ref(item) for item in grouped.get(category, [])]
        for category in sorted(COMPARISON_ONLY_CATEGORIES)
    }


def _source_manifest_hash(manifest: dict[str, Any]) -> str:
    draft = manifest.get('annual_tax_source_bundle_draft')
    if isinstance(draft, dict) and draft.get('hash_fuentes'):
        return str(draft['hash_fuentes'])
    return payload_hash(
        {
            'schema_version': manifest.get('schema_version', ''),
            'company_ref': manifest.get('company_ref', ''),
            'commercial_year': manifest.get('commercial_year'),
            'tax_year': manifest.get('tax_year'),
            'summary': manifest.get('summary') or {},
            'coverage': manifest.get('coverage') or {},
        }
    )


def _package_month(
    *,
    company_ref: str,
    commercial_year: int,
    month: int,
    refs: dict[str, list[dict[str, Any]]],
    f29_no_declaration_months: set[int],
) -> dict[str, Any]:
    month_ref = f'{company_ref}-AC{commercial_year}-{month:02d}-controlled-load'
    f29_no_declaration = month in f29_no_declaration_months and not refs.get('f29_support_input')
    return {
        'month': month,
        'source_ref': month_ref,
        'input_source_refs': refs,
        'ledger': {
            'libro_diario_ref': '',
            'libro_mayor_ref': '',
            'asientos_count': None,
            'cuentas_count': None,
            'total_debe': '',
            'total_haber': '',
        },
        'balance': {
            'balance_ref': '',
            'total_debe': '',
            'total_haber': '',
            'cuadrado': None,
        },
        'obligations': [],
        'f29': {
            'estado_preparacion': 'no_aplica' if f29_no_declaration else 'preparado',
            'borrador_ref': '',
            'resumen': {
                'no_declaration': True,
                'source': 'manifest.f29_no_declaration_months',
            }
            if f29_no_declaration
            else {},
        },
        'payroll': {
            'source_ref': '',
            'has_movements': None,
            'resumen': {},
        },
    }


def build_annual_tax_controlled_db_load_template(*, manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise ValueError('Manifest JSON must be an object.')

    grouped = _files_by_category(manifest)
    company_ref = str(manifest.get('company_ref') or '').strip()
    commercial_year = int(manifest.get('commercial_year') or 0)
    tax_year = int(manifest.get('tax_year') or commercial_year + 1)
    source_manifest_hash = _source_manifest_hash(manifest)
    coverage = manifest.get('coverage') if isinstance(manifest.get('coverage'), dict) else {}
    f29_no_declaration_months = {
        int(month)
        for month in coverage.get('f29_no_declaration_months') or []
        if 1 <= int(month) <= 12
    }
    missing_months_by_category = {
        category: [
            month
            for month in MONTHS
            if not _month_refs(grouped, month).get(category)
            and not (category == 'f29_support_input' and month in f29_no_declaration_months)
        ]
        for category in MONTHLY_INPUT_CATEGORIES
    }
    comparison_targets = _comparison_refs(grouped)
    annual_inputs = _annual_refs(grouped)
    monthly_input_refs_complete = all(not months for months in missing_months_by_category.values())
    annual_ledger_refs_complete = bool(annual_inputs.get('annual_ledger_input'))
    package_draft = {
        'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': source_manifest_hash,
        'responsible_ref': 'pending-responsible-ref',
        'approval_ref': 'pending-approval-ref',
        'expected_outputs_used_as_inputs': False,
        'annual_input_source_refs': annual_inputs,
        'months': [
            _package_month(
                company_ref=company_ref,
                commercial_year=commercial_year,
                month=month,
                refs=_month_refs(grouped, month),
                f29_no_declaration_months=f29_no_declaration_months,
            )
            for month in MONTHS
        ],
    }

    input_categories_present = sorted(
        category
        for category in CALCULATION_INPUT_CATEGORIES
        if grouped.get(category)
    )
    comparison_categories_present = sorted(
        category
        for category in COMPARISON_ONLY_CATEGORIES
        if grouped.get(category)
    )

    return {
        'schema_version': CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_manifest_schema_version': manifest.get('schema_version', ''),
        'package_schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': source_manifest_hash,
        'safety': {
            'writes_database': False,
            'copies_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'expected_outputs_used_as_inputs': False,
            'comparison_targets_separated': True,
        },
        'summary': {
            'source_documentation_confirmed_for_ac2024_at2025': bool(
                coverage.get('ready_for_mirror_source_bundle')
            ),
            'input_categories_present': input_categories_present,
            'comparison_target_categories_present': comparison_categories_present,
            'missing_months_by_category': missing_months_by_category,
            'monthly_input_refs_complete': monthly_input_refs_complete,
            'annual_ledger_refs_complete': annual_ledger_refs_complete,
            'ready_for_writer': False,
            'reason_not_ready_for_writer': 'manual_values_required',
        },
        'manual_completion_required': [
            'Revisar/transcribir totales mensuales de Libro Diario y Libro Mayor desde fuente AC2024 controlada.',
            'Revisar/transcribir BalanceComprobacion mensual cuadrado desde fuente AC2024 controlada.',
            'Completar obligaciones mensuales PPM/F29 desde fuente AC2024 controlada.',
            'Completar fuente laboral/previsional mensual si aplica a DJ1887/remuneraciones.',
            'Reemplazar responsible_ref y approval_ref pendientes por referencias no sensibles antes de aplicar writer.',
        ],
        'package_draft': package_draft,
        'comparison_targets': comparison_targets,
    }


def load_manifest_json(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Manifest JSON must be an object.')
    return payload
