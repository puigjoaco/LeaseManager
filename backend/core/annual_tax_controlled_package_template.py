from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_load_plan import CALCULATION_INPUT_CATEGORIES, COMPARISON_ONLY_CATEGORIES
from core.annual_tax_ownership_review_checklist import OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import (
    contains_chilean_rut_reference,
    contains_local_absolute_path_reference,
    contains_sensitive_reference,
)


CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION = 'annual-tax-controlled-db-load-template.v1'
CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION = 'annual-tax-ownership-review-handoff.v1'
MONTHS = tuple(range(1, 13))
SAFE_REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:-]+$')

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


def _labor_previsional_section(
    *,
    coverage: dict[str, Any],
    grouped: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    required = bool(coverage.get('labor_previsional_required'))
    source_refs = [_file_ref(item) for item in grouped.get('payroll_support', [])]
    return {
        'required': required,
        'required_by_ddjj_forms': coverage.get('labor_previsional_required_by_ddjj_forms') or [],
        'source_ref': '',
        'source_refs': source_refs,
        'monthly_support_months': coverage.get('payroll_support_months') or [],
        'status': 'pending_source_review' if required else 'not_required_by_manifest',
        'final_tax_calculation': False,
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


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _is_safe_handoff_ref(value: Any) -> bool:
    text = str(value or '').strip()
    return bool(text) and not (
        contains_sensitive_reference(text)
        or contains_chilean_rut_reference(text)
        or contains_local_absolute_path_reference(text)
        or not SAFE_REF_PATTERN.fullmatch(text)
    )


def _safe_handoff_ref(value: Any, *, fallback: str) -> str:
    text = str(value or '').strip()
    return text if _is_safe_handoff_ref(text) else fallback


def _safe_handoff_refs(values: Any, *, fallback: str) -> list[str]:
    if not isinstance(values, list):
        return []
    refs = {
        _safe_handoff_ref(value, fallback=fallback)
        for value in values
        if str(value or '').strip()
    }
    return sorted(refs)


def _ownership_review_handoff(
    *,
    checklist: dict[str, Any] | None,
    company_ref: str,
    commercial_year: int,
    tax_year: int,
) -> dict[str, Any] | None:
    if checklist is None:
        return None
    if not isinstance(checklist, dict):
        raise ValueError('ownership_review_checklist JSON must be an object.')
    if checklist.get('schema_version') != OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION:
        raise ValueError(
            f'ownership_review_checklist.schema_version debe ser {OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION}.'
        )
    if str(checklist.get('company_ref') or '').strip() != company_ref:
        raise ValueError('ownership_review_checklist.company_ref no coincide con el manifiesto.')
    if _int_value(checklist.get('commercial_year')) != commercial_year:
        raise ValueError('ownership_review_checklist.commercial_year no coincide con el manifiesto.')
    if _int_value(checklist.get('tax_year')) != tax_year:
        raise ValueError('ownership_review_checklist.tax_year no coincide con el manifiesto.')

    summary = checklist.get('summary') if isinstance(checklist.get('summary'), dict) else {}
    validation_summary = (
        checklist.get('validation_summary') if isinstance(checklist.get('validation_summary'), dict) else {}
    )
    decision = checklist.get('decision') if isinstance(checklist.get('decision'), dict) else {}
    checklist_items = [
        item
        for item in (checklist.get('checklist_items') or [])
        if isinstance(item, dict)
    ]
    blocking_item_keys = [
        _safe_handoff_ref(item.get('key'), fallback='redacted-checklist-item')
        for item in checklist_items
        if str(item.get('status') or '').strip() != 'ready' and str(item.get('key') or '').strip()
    ]
    validation_blockers = _safe_handoff_refs(
        validation_summary.get('blockers'),
        fallback='redacted-validation-blocker',
    )
    ready_for_controlled_db_load = bool(summary.get('ready_for_controlled_db_load'))
    return {
        'schema_version': CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
        'source_checklist_hash': payload_hash(
            {
                'schema_version': checklist.get('schema_version'),
                'company_ref': checklist.get('company_ref'),
                'commercial_year': checklist.get('commercial_year'),
                'tax_year': checklist.get('tax_year'),
                'source_template_hash': checklist.get('source_template_hash'),
                'summary': summary,
                'validation_summary': validation_summary,
                'checklist_items': checklist_items,
            }
        ),
        'reviewable_candidates_total': _int_value(summary.get('reviewable_candidates_total')),
        'rendered_candidates_total': _int_value(summary.get('rendered_candidates_total')),
        'validation_present': bool(summary.get('validation_present')),
        'participants_count': _int_value(summary.get('participants_count')),
        'percentage_total': str(summary.get('percentage_total') or '0.00'),
        'blocking_items_total': _int_value(summary.get('blocking_items_total')),
        'blocking_item_keys': blocking_item_keys,
        'validation_blockers': validation_blockers,
        'ready_for_manual_review': bool(summary.get('ready_for_manual_review')),
        'ready_for_controlled_db_load': ready_for_controlled_db_load,
        'can_inject_ownership_into_controlled_package': bool(
            decision.get('can_inject_ownership_into_controlled_package')
        ),
        'next_action': (
            'inject_validated_ownership_snapshot_into_package_ownership'
            if ready_for_controlled_db_load
            else 'complete_validated_ownership_patch_before_package_ownership'
        ),
        'writes_database': False,
        'stores_source_paths': False,
        'stores_person_names': False,
        'stores_rut_values': False,
        'auto_generates_ownership': False,
    }


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


def build_annual_tax_controlled_db_load_template(
    *,
    manifest: dict[str, Any],
    ownership_review_checklist: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
    labor_previsional = _labor_previsional_section(coverage=coverage, grouped=grouped)
    ownership_review = _ownership_review_handoff(
        checklist=ownership_review_checklist,
        company_ref=company_ref,
        commercial_year=commercial_year,
        tax_year=tax_year,
    )
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
        'labor_previsional': labor_previsional,
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
    if ownership_review is not None:
        package_draft['ownership_review'] = ownership_review

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

    manual_completion_required = [
        'Revisar/transcribir totales mensuales de Libro Diario y Libro Mayor desde fuente AC2024 controlada.',
        'Revisar/transcribir BalanceComprobacion mensual cuadrado desde fuente AC2024 controlada.',
        'Completar obligaciones mensuales PPM/F29 desde fuente AC2024 controlada.',
        'Completar fuente laboral/previsional mensual si aplica a DJ1887/remuneraciones.',
        'Completar labor_previsional.source_ref con una referencia no sensible si DJ1887/remuneraciones aplica.',
        'Reemplazar responsible_ref y approval_ref pendientes por referencias no sensibles antes de aplicar writer.',
    ]
    if ownership_review is not None:
        manual_completion_required.append(
            'Inyectar snapshot package.ownership solo despues de validar el patch ownership controlado.'
            if ownership_review['ready_for_controlled_db_load']
            else 'Completar patch ownership controlado antes de crear package.ownership.'
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
            'labor_previsional_required': labor_previsional['required'],
            'labor_previsional_source_present': bool(labor_previsional['source_refs']),
            'labor_previsional_required_by_ddjj_forms': labor_previsional['required_by_ddjj_forms'],
            'ownership_review_present': ownership_review is not None,
            'ownership_review_ready_for_manual_review': bool(
                ownership_review and ownership_review['ready_for_manual_review']
            ),
            'ownership_review_ready_for_controlled_db_load': bool(
                ownership_review and ownership_review['ready_for_controlled_db_load']
            ),
            'ownership_review_rendered_candidates_total': (
                ownership_review['rendered_candidates_total'] if ownership_review else 0
            ),
            'ready_for_writer': False,
            'reason_not_ready_for_writer': 'manual_values_required',
        },
        'manual_completion_required': manual_completion_required,
        'package_draft': package_draft,
        'comparison_targets': comparison_targets,
    }


def load_manifest_json(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('Manifest JSON must be an object.')
    return payload
