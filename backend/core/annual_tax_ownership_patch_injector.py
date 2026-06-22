from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_readiness import audit_annual_tax_controlled_package_readiness
from core.annual_tax_controlled_package_template import (
    CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
    CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
)
from core.annual_tax_ownership_patch_validator import (
    OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
    validate_annual_tax_ownership_patch,
)
from core.annual_tax_ownership_patch_workbench import OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION
from core.reference_validation import (
    contains_chilean_rut_reference,
    contains_local_absolute_path_reference,
    contains_sensitive_reference,
)


OWNERSHIP_PATCH_INJECTION_SCHEMA_VERSION = 'annual-tax-ownership-patch-injection.v1'
SAFE_REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:-]+$')


def _extract_package(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    schema_version = str(payload.get('schema_version') or '')
    if schema_version == CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION:
        package = payload.get('package_draft')
        if not isinstance(package, dict):
            raise ValueError('package_draft debe ser un objeto JSON.')
        comparison_targets = payload.get('comparison_targets') if isinstance(payload.get('comparison_targets'), dict) else None
        return deepcopy(package), deepcopy(comparison_targets), schema_version
    if schema_version != CONTROLLED_DB_LOAD_SCHEMA_VERSION:
        raise ValueError(
            f'package.schema_version debe ser {CONTROLLED_DB_LOAD_SCHEMA_VERSION} '
            f'o {CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION}.'
        )
    return deepcopy(payload), None, schema_version


def _extract_ownership(patch: dict[str, Any]) -> dict[str, Any]:
    ownership = patch.get('ownership') if isinstance(patch.get('ownership'), dict) else patch
    if not isinstance(ownership, dict):
        raise ValueError('patch ownership debe ser un objeto JSON.')
    return deepcopy(ownership)


def _context_matches(*, package: dict[str, Any], validation: dict[str, Any]) -> None:
    for field_name in ('company_ref', 'commercial_year', 'tax_year'):
        if str(package.get(field_name) or '') != str(validation.get(field_name) or ''):
            raise ValueError(f'El patch ownership validado no coincide con package.{field_name}.')


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _is_safe_ref(value: Any) -> bool:
    text = str(value or '').strip()
    return bool(text) and not (
        contains_sensitive_reference(text)
        or contains_chilean_rut_reference(text)
        or contains_local_absolute_path_reference(text)
        or not SAFE_REF_PATTERN.fullmatch(text)
    )


def _safe_summary_ref(value: Any, *, fallback: str) -> str:
    text = str(value or '').strip()
    return text if _is_safe_ref(text) else fallback


def _safe_ready_flags(raw_flags: Any) -> dict[str, bool]:
    if not isinstance(raw_flags, dict):
        return {}
    flags: dict[str, bool] = {}
    for raw_key, raw_value in raw_flags.items():
        key = str(raw_key or '').strip()
        if _is_safe_ref(key) and isinstance(raw_value, bool):
            flags[key] = raw_value
    return {key: flags[key] for key in sorted(flags)}


def _safe_source_issue_codes(raw_issue_codes: Any) -> list[dict[str, str]]:
    if not isinstance(raw_issue_codes, list):
        return []
    issue_codes: list[dict[str, str]] = []
    for raw_issue in raw_issue_codes:
        if not isinstance(raw_issue, dict):
            continue
        code = _safe_summary_ref(raw_issue.get('code'), fallback='redacted-issue-code')
        if not code:
            continue
        issue_codes.append(
            {
                'code': code,
                'severity': _safe_summary_ref(raw_issue.get('severity'), fallback='blocking'),
            }
        )
    return sorted(issue_codes, key=lambda item: (item['code'], item['severity']))


def _question_source_summaries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_summaries = payload.get('question_source_summaries')
    if not isinstance(raw_summaries, list):
        raw_summaries = payload.get('source_summaries')
    if not isinstance(raw_summaries, list):
        return []

    summaries: list[dict[str, Any]] = []
    for raw_summary in raw_summaries:
        if not isinstance(raw_summary, dict):
            continue
        summaries.append(
            {
                'label': _safe_summary_ref(raw_summary.get('label'), fallback='source'),
                'schema_version': _safe_summary_ref(
                    raw_summary.get('schema_version'),
                    fallback='schema-version-pending',
                ),
                'classification': _safe_summary_ref(
                    raw_summary.get('classification'),
                    fallback='classification-pending',
                ),
                'ready_flags': _safe_ready_flags(raw_summary.get('ready_flags')),
                'issues_total': _safe_int(raw_summary.get('issues_total')),
                'safe_issue_codes': _safe_source_issue_codes(raw_summary.get('safe_issue_codes')),
                'source_hash': _safe_summary_ref(raw_summary.get('source_hash'), fallback='source-hash-pending'),
            }
        )
    return sorted(summaries, key=lambda item: (item['label'], item['source_hash']))


def _workbench_question_source_summaries(
    ownership_workbench: dict[str, Any] | None,
    *,
    validation: dict[str, Any],
) -> list[dict[str, Any]]:
    if ownership_workbench is None:
        return []
    if not isinstance(ownership_workbench, dict):
        raise ValueError('ownership_workbench debe ser un objeto JSON.')
    if ownership_workbench.get('schema_version') != OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION:
        raise ValueError(f'ownership_workbench.schema_version debe ser {OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION}.')
    for field_name in ('company_ref', 'commercial_year', 'tax_year'):
        if str(ownership_workbench.get(field_name) or '') != str(validation.get(field_name) or ''):
            raise ValueError(f'ownership_workbench.{field_name} no coincide con el patch validado.')
    responsible_answers_summary = ownership_workbench.get('responsible_answers_summary')
    if not isinstance(responsible_answers_summary, dict):
        return []
    return _question_source_summaries(responsible_answers_summary)


def _updated_ownership_review(
    *,
    existing_review: Any,
    validation: dict[str, Any],
    ownership_workbench: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review = deepcopy(existing_review) if isinstance(existing_review, dict) else {}
    source_summaries = _workbench_question_source_summaries(ownership_workbench, validation=validation)
    if not source_summaries:
        source_summaries = _question_source_summaries(review)
    review.update(
        {
            'schema_version': CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
            'validation_present': True,
            'participants_count': int((validation.get('summary') or {}).get('participants_count') or 0),
            'percentage_total': str((validation.get('summary') or {}).get('percentage_total') or '0.00'),
            'blocking_items_total': 0,
            'blocking_item_keys': [],
            'validation_blockers': [],
            'ready_for_manual_review': True,
            'ready_for_controlled_db_load': True,
            'can_inject_ownership_into_controlled_package': True,
            'next_action': 'package_ownership_injected_reaudit_readiness',
            'writes_database': False,
            'stores_source_paths': False,
            'stores_person_names': False,
            'stores_rut_values': False,
            'auto_generates_ownership': False,
            'redacted_patch_hash': validation.get('redacted_patch_hash', ''),
            'readiness_sources_total': len(source_summaries),
            'question_source_summaries': source_summaries,
        }
    )
    return review


def inject_annual_tax_ownership_patch_into_controlled_package(
    *,
    package_payload: dict[str, Any],
    template: dict[str, Any],
    patch: dict[str, Any],
    ownership_workbench: dict[str, Any] | None = None,
    replace_existing: bool = False,
) -> dict[str, Any]:
    if not isinstance(package_payload, dict):
        raise ValueError('package_payload debe ser un objeto JSON.')
    if not isinstance(template, dict):
        raise ValueError('template debe ser un objeto JSON.')
    if not isinstance(patch, dict):
        raise ValueError('patch debe ser un objeto JSON.')

    package, comparison_targets, input_schema_version = _extract_package(package_payload)
    if package.get('ownership') not in (None, {}) and not replace_existing:
        raise ValueError('package.ownership ya existe; use replace_existing solo con decision controlada.')

    validation = validate_annual_tax_ownership_patch(template=template, patch=patch)
    if not validation.get('ready_for_controlled_db_load'):
        blockers = ','.join(validation.get('blockers') or [])
        raise ValueError(f'Ownership patch no listo para inyectar: blockers={blockers}.')
    _context_matches(package=package, validation=validation)

    package['ownership'] = _extract_ownership(patch)
    package['ownership_review'] = _updated_ownership_review(
        existing_review=package.get('ownership_review'),
        validation=validation,
        ownership_workbench=ownership_workbench,
    )

    readiness_payload: dict[str, Any] = deepcopy(package)
    if comparison_targets is not None:
        readiness_payload = {
            'schema_version': CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
            'package_draft': deepcopy(package),
            'comparison_targets': comparison_targets,
        }
    readiness = audit_annual_tax_controlled_package_readiness(payload=readiness_payload)

    return {
        'schema_version': OWNERSHIP_PATCH_INJECTION_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'input_schema_version': input_schema_version,
        'package_schema_version': package.get('schema_version'),
        'ownership_patch_schema_version': str(patch.get('schema_version') or OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION),
        'company_ref': package.get('company_ref', ''),
        'commercial_year': package.get('commercial_year'),
        'tax_year': package.get('tax_year'),
        'validation': validation,
        'readiness': readiness,
        'package': package,
        'comparison_targets': comparison_targets or {},
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'opens_external_auth': False,
            'uses_expected_outputs_as_inputs': False,
            'validates_patch_before_injection': True,
            'output_contains_ownership_pii': True,
            'ready_to_version_output': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'summary': {
            'ownership_injected': True,
            'participants_count': int((validation.get('summary') or {}).get('participants_count') or 0),
            'ownership_review_readiness_sources_total': int(
                package['ownership_review'].get('readiness_sources_total') or 0
            ),
            'ready_for_db_writer': bool(readiness.get('ready_for_db_writer')),
            'ready_for_annual_generation': bool(readiness.get('ready_for_annual_generation')),
            'annual_generation_blockers': list(readiness.get('annual_generation_blockers') or []),
            'blockers': list(readiness.get('blockers') or []),
        },
    }
