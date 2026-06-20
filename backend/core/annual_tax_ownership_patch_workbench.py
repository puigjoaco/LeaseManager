from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.annual_tax_ownership_patch_validator import OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION
from core.annual_tax_ownership_review_checklist import OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION
from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION
from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION,
)
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import contains_sensitive_reference


OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION = 'annual-tax-ownership-patch-workbench.v1'
OWNERSHIP_PATCH_WORKBENCH_MANIFEST_FILENAME = 'ownership-patch-workbench.json'
OWNERSHIP_PATCH_DRAFT_PRIVATE_FILENAME = 'ownership-patch-draft.private.json'
CHILEAN_RUT_PATTERN = re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b')
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r'(^|[\s"\'])([A-Za-z]:[\\/]|\\\\)')
SAFE_REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:-]+$')


def _context_from_template(template: dict[str, Any]) -> tuple[str, int, int]:
    return (
        str(template.get('company_ref') or '').strip(),
        int(template.get('commercial_year') or 0),
        int(template.get('tax_year') or 0),
    )


def _template_hash(template: dict[str, Any]) -> str:
    return payload_hash(
        {
            'schema_version': template.get('schema_version'),
            'company_ref': template.get('company_ref'),
            'commercial_year': template.get('commercial_year'),
            'tax_year': template.get('tax_year'),
            'source_review_hash': template.get('source_review_hash'),
            'candidate_sources': template.get('candidate_sources'),
        }
    )


def _checklist_summary(checklist: dict[str, Any] | None, *, context: tuple[str, int, int]) -> dict[str, Any]:
    if checklist is None:
        return {
            'present': False,
            'hash': '',
            'reviewable_candidates_total': 0,
            'rendered_candidates_total': 0,
            'validation_present': False,
            'participants_count': 0,
            'percentage_total': '0.00',
            'blocking_items_total': 0,
            'ready_for_manual_review': False,
            'ready_for_controlled_db_load': False,
            'blocking_item_keys': [],
            'validation_blockers': [],
        }
    if checklist.get('schema_version') != OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION:
        raise ValueError(f'checklist.schema_version debe ser {OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION}.')
    company_ref, commercial_year, tax_year = context
    if str(checklist.get('company_ref') or '') != company_ref:
        raise ValueError('checklist.company_ref no coincide con template.company_ref.')
    if int(checklist.get('commercial_year') or 0) != commercial_year:
        raise ValueError('checklist.commercial_year no coincide con template.commercial_year.')
    if int(checklist.get('tax_year') or 0) != tax_year:
        raise ValueError('checklist.tax_year no coincide con template.tax_year.')

    summary = checklist.get('summary') if isinstance(checklist.get('summary'), dict) else {}
    checklist_items = checklist.get('checklist_items') if isinstance(checklist.get('checklist_items'), list) else []
    validation_summary = (
        checklist.get('validation_summary') if isinstance(checklist.get('validation_summary'), dict) else {}
    )
    return {
        'present': True,
        'hash': payload_hash(
            {
                'schema_version': checklist.get('schema_version'),
                'company_ref': checklist.get('company_ref'),
                'commercial_year': checklist.get('commercial_year'),
                'tax_year': checklist.get('tax_year'),
                'source_template_hash': checklist.get('source_template_hash'),
                'summary': summary,
                'checklist_items': checklist_items,
            }
        ),
        'reviewable_candidates_total': int(summary.get('reviewable_candidates_total') or 0),
        'rendered_candidates_total': int(summary.get('rendered_candidates_total') or 0),
        'validation_present': bool(summary.get('validation_present')),
        'participants_count': int(summary.get('participants_count') or 0),
        'percentage_total': str(summary.get('percentage_total') or '0.00'),
        'blocking_items_total': int(summary.get('blocking_items_total') or 0),
        'ready_for_manual_review': bool(summary.get('ready_for_manual_review')),
        'ready_for_controlled_db_load': bool(summary.get('ready_for_controlled_db_load')),
        'blocking_item_keys': [
            _safe_summary_ref(item.get('key'), fallback='redacted-checklist-item')
            for item in checklist_items
            if isinstance(item, dict) and str(item.get('status') or '') != 'ready'
        ],
        'validation_blockers': _safe_summary_refs(
            validation_summary.get('blockers'),
            fallback='redacted-validation-blocker',
        ),
    }


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _is_safe_ref(value: Any) -> bool:
    text = str(value or '').strip()
    return bool(text) and not (
        contains_sensitive_reference(text)
        or CHILEAN_RUT_PATTERN.search(text)
        or WINDOWS_ABSOLUTE_PATH_PATTERN.search(text)
        or not SAFE_REF_PATTERN.fullmatch(text)
    )


def _require_safe_ref(value: Any, *, field_name: str) -> str:
    text = str(value or '').strip()
    if not _is_safe_ref(text):
        raise ValueError(f'{field_name} debe ser una referencia no sensible.')
    return text


def _safe_summary_ref(value: Any, *, fallback: str) -> str:
    text = str(value or '').strip()
    return text if _is_safe_ref(text) else fallback


def _safe_summary_counts(value: Any, *, fallback: str) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        key = _safe_summary_ref(raw_key, fallback=fallback)
        count = _safe_int(raw_count)
        if count <= 0:
            count = 1
        counts[key] = counts.get(key, 0) + count
    return dict(sorted(counts.items()))


def _safe_summary_refs(values: Any, *, fallback: str) -> list[str]:
    if not isinstance(values, list):
        return []
    safe_refs = {
        _safe_summary_ref(value, fallback=fallback)
        for value in values
        if str(value or '').strip()
    }
    return sorted(safe_refs)


def _responsible_answers_summary(
    responsible_answers_review: dict[str, Any] | None,
    *,
    context: tuple[str, int, int],
) -> dict[str, Any]:
    if responsible_answers_review is None:
        return {
            'present': False,
            'hash': '',
            'questions_total': 0,
            'answers_total': 0,
            'missing_questions_total': 0,
            'blocking_issues_total': 0,
            'decision_states': {},
            'categories': {},
            'issue_codes': [],
            'ready_for_responsible_decision_handoff': False,
        }
    if responsible_answers_review.get('schema_version') != COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION:
        raise ValueError(
            f'responsible_answers_review.schema_version debe ser '
            f'{COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION}.'
        )
    company_ref, commercial_year, tax_year = context
    if str(responsible_answers_review.get('company_ref') or '') != company_ref:
        raise ValueError('responsible_answers_review.company_ref no coincide con template.company_ref.')
    if _safe_int(responsible_answers_review.get('fiscal_year')) != commercial_year:
        raise ValueError('responsible_answers_review.fiscal_year no coincide con template.commercial_year.')
    if _safe_int(responsible_answers_review.get('tax_year')) != tax_year:
        raise ValueError('responsible_answers_review.tax_year no coincide con template.tax_year.')

    summary = responsible_answers_review.get('summary') if isinstance(responsible_answers_review.get('summary'), dict) else {}
    issues = responsible_answers_review.get('issues') if isinstance(responsible_answers_review.get('issues'), list) else []
    decision_states = _safe_summary_counts(summary.get('decision_states'), fallback='redacted-decision-state')
    categories = _safe_summary_counts(summary.get('categories'), fallback='redacted-category')
    issue_codes = {
        _safe_summary_ref(issue.get('code'), fallback='redacted-issue-code')
        for issue in issues
        if isinstance(issue, dict) and str(issue.get('code') or '').strip()
    }
    missing_question_keys = (
        responsible_answers_review.get('missing_question_keys')
        if isinstance(responsible_answers_review.get('missing_question_keys'), list)
        else []
    )
    missing_questions_total = max(
        _safe_int(summary.get('missing_questions_total')),
        len(missing_question_keys),
    )
    if missing_questions_total:
        issue_codes.add('responsible_answers.questions_unanswered')
    questions_total = _safe_int(summary.get('questions_total'))
    answers_total = _safe_int(summary.get('answers_total'))
    if questions_total and answers_total < questions_total:
        issue_codes.add('responsible_answers.answer_count_mismatch')
    sorted_issue_codes = sorted(issue_codes)
    blocking_issues_total = max(
        _safe_int(summary.get('blocking_issues_total')),
        sum(max(_safe_int(issue.get('count')), 1) for issue in issues if isinstance(issue, dict)),
        missing_questions_total,
        len(sorted_issue_codes),
    )
    reported_ready = bool(summary.get('ready_for_responsible_decision_handoff'))
    effective_ready = (
        reported_ready
        and questions_total > 0
        and answers_total >= questions_total
        and missing_questions_total == 0
        and blocking_issues_total == 0
        and not sorted_issue_codes
    )
    fingerprint = {
        'schema_version': responsible_answers_review.get('schema_version'),
        'company_ref': responsible_answers_review.get('company_ref'),
        'fiscal_year': responsible_answers_review.get('fiscal_year'),
        'tax_year': responsible_answers_review.get('tax_year'),
        'questions_packet_hash': responsible_answers_review.get('questions_packet_hash'),
        'summary': {
            'questions_total': questions_total,
            'answers_total': answers_total,
            'missing_questions_total': missing_questions_total,
            'blocking_issues_total': blocking_issues_total,
            'decision_states': decision_states,
            'categories': categories,
            'reported_ready_for_responsible_decision_handoff': reported_ready,
            'ready_for_responsible_decision_handoff': effective_ready,
        },
        'issue_codes': sorted_issue_codes,
    }
    return {
        'present': True,
        'hash': payload_hash(fingerprint),
        'questions_total': fingerprint['summary']['questions_total'],
        'answers_total': fingerprint['summary']['answers_total'],
        'missing_questions_total': fingerprint['summary']['missing_questions_total'],
        'blocking_issues_total': fingerprint['summary']['blocking_issues_total'],
        'decision_states': fingerprint['summary']['decision_states'],
        'categories': fingerprint['summary']['categories'],
        'issue_codes': sorted_issue_codes,
        'reported_ready_for_responsible_decision_handoff': fingerprint['summary'][
            'reported_ready_for_responsible_decision_handoff'
        ],
        'ready_for_responsible_decision_handoff': fingerprint['summary']['ready_for_responsible_decision_handoff'],
    }


def _patch_draft(
    *,
    template: dict[str, Any],
    responsible_ref: str,
    approval_ref: str,
) -> dict[str, Any]:
    company_ref, commercial_year, tax_year = _context_from_template(template)
    safe_responsible_ref = _require_safe_ref(responsible_ref, field_name='responsible_ref')
    safe_approval_ref = _require_safe_ref(approval_ref, field_name='approval_ref')
    ownership_template = deepcopy(template.get('ownership_patch_template'))
    if not isinstance(ownership_template, dict):
        ownership_template = {}
    if not isinstance(ownership_template.get('participants'), list):
        ownership_template['participants'] = []
    ownership_template.setdefault('source_ref', '')
    ownership_template.setdefault('as_of', f'{commercial_year}-12-31' if commercial_year else '')

    return {
        'schema_version': OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'responsible_ref': safe_responsible_ref,
        'approval_ref': safe_approval_ref,
        'ownership': ownership_template,
    }


def _review_questions(*, commercial_year: int) -> list[dict[str, Any]]:
    return [
        {
            'key': 'ownership_source_ref',
            'answer_location': '$.ownership.source_ref',
            'required': True,
            'contains_pii': False,
            'store_only_in_private_patch': False,
            'expected': 'Referencia no sensible de la fuente societaria/controlada revisada.',
        },
        {
            'key': 'ownership_as_of',
            'answer_location': '$.ownership.as_of',
            'required': True,
            'contains_pii': False,
            'store_only_in_private_patch': False,
            'expected': f'Fecha de vigencia ownership al 31-12-{commercial_year}.',
        },
        {
            'key': 'participants',
            'answer_location': '$.ownership.participants[]',
            'required': True,
            'contains_pii': True,
            'store_only_in_private_patch': True,
            'expected': (
                'Completar socios vigentes con participant_ref, name, rut, percentage, '
                'vigente_desde, vigente_hasta y evidence_ref no sensible.'
            ),
        },
        {
            'key': 'percentage_total',
            'answer_location': '$.ownership.participants[].percentage',
            'required': True,
            'contains_pii': False,
            'store_only_in_private_patch': True,
            'expected': 'La suma de porcentajes vigentes debe ser 100.00.',
        },
        {
            'key': 'responsible_and_approval_refs',
            'answer_location': '$.responsible_ref / $.approval_ref',
            'required': True,
            'contains_pii': False,
            'store_only_in_private_patch': False,
            'expected': 'Refs no sensibles de responsable y aprobacion del patch.',
        },
    ]


def build_annual_tax_ownership_patch_workbench(
    *,
    template: dict[str, Any],
    checklist: dict[str, Any] | None = None,
    responsible_answers_review: dict[str, Any] | None = None,
    responsible_ref: str = 'pending-responsible-review',
    approval_ref: str = 'pending-approval',
) -> dict[str, Any]:
    if not isinstance(template, dict):
        raise ValueError('template debe ser un objeto JSON.')
    if template.get('schema_version') != OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION:
        raise ValueError(f'template.schema_version debe ser {OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION}.')
    if checklist is not None and not isinstance(checklist, dict):
        raise ValueError('checklist debe ser un objeto JSON.')

    company_ref, commercial_year, tax_year = _context_from_template(template)
    checklist_summary = _checklist_summary(checklist, context=(company_ref, commercial_year, tax_year))
    responsible_answers_summary = _responsible_answers_summary(
        responsible_answers_review,
        context=(company_ref, commercial_year, tax_year),
    )
    patch_draft = _patch_draft(
        template=template,
        responsible_ref=responsible_ref,
        approval_ref=approval_ref,
    )
    questions = _review_questions(commercial_year=commercial_year)
    manifest = {
        'schema_version': OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_template_hash': _template_hash(template),
        'checklist_hash': checklist_summary['hash'],
        'responsible_answers_review_hash': responsible_answers_summary['hash'],
        'files': {
            'manifest': OWNERSHIP_PATCH_WORKBENCH_MANIFEST_FILENAME,
            'private_patch_draft': OWNERSHIP_PATCH_DRAFT_PRIVATE_FILENAME,
        },
        'summary': {
            'draft_ready_for_manual_completion': True,
            'reviewable_candidates_total': checklist_summary['reviewable_candidates_total'],
            'rendered_candidates_total': checklist_summary['rendered_candidates_total'],
            'checklist_present': checklist_summary['present'],
            'checklist_ready_for_manual_review': checklist_summary['ready_for_manual_review'],
            'checklist_ready_for_controlled_db_load': checklist_summary['ready_for_controlled_db_load'],
            'checklist_blocking_items_total': checklist_summary['blocking_items_total'],
            'responsible_answers_present': responsible_answers_summary['present'],
            'responsible_answers_ready': responsible_answers_summary['ready_for_responsible_decision_handoff'],
            'responsible_answers_blocking_issues_total': responsible_answers_summary['blocking_issues_total'],
            'patch_participants_count': len(patch_draft['ownership'].get('participants') or []),
            'questions_total': len(questions),
            'private_questions_total': sum(1 for item in questions if item['store_only_in_private_patch']),
        },
        'checklist_summary': checklist_summary,
        'responsible_answers_summary': responsible_answers_summary,
        'review_questions': questions,
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'opens_external_auth': False,
            'uses_expected_outputs_as_inputs': False,
            'stores_raw_text': False,
            'stores_source_paths': False,
            'stores_person_names': False,
            'stores_rut_values': False,
            'private_patch_may_store_person_names': True,
            'private_patch_may_store_rut_values': True,
            'ready_to_version_manifest': True,
            'ready_to_version_private_patch': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'decision': {
            'ready_for_manual_patch_completion': True,
            'responsible_answers_ready_for_patch_completion': responsible_answers_summary[
                'ready_for_responsible_decision_handoff'
            ],
            'ready_for_controlled_db_load': False,
            'next_actions': [
                'Completar y validar company-accounting-responsible-answers si responsible_answers_ready=false.',
                'Completar ownership-patch-draft.private.json solo bajo local-evidence/ o ruta externa controlada.',
                'No versionar el patch privado completado porque puede contener nombres y RUTs.',
                'Ejecutar validate_annual_tax_ownership_patch sobre el patch completado.',
                'Inyectar el patch validado al paquete controlado y reauditar readiness.',
            ],
        },
    }
    return {
        'manifest': manifest,
        'patch_draft': patch_draft,
    }


def write_annual_tax_ownership_patch_workbench(*, workbench: dict[str, Any], output_dir: Path) -> dict[str, str]:
    if not isinstance(workbench, dict):
        raise ValueError('workbench debe ser un objeto JSON.')
    manifest = workbench.get('manifest')
    patch_draft = workbench.get('patch_draft')
    if not isinstance(manifest, dict) or not isinstance(patch_draft, dict):
        raise ValueError('workbench debe contener manifest y patch_draft.')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('output_dir debe estar vacio o no existir.')

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / OWNERSHIP_PATCH_WORKBENCH_MANIFEST_FILENAME
    patch_path = output_dir / OWNERSHIP_PATCH_DRAFT_PRIVATE_FILENAME
    manifest_path.write_text(
        json_dumps(manifest),
        encoding='utf-8',
    )
    patch_path.write_text(
        json_dumps(patch_draft),
        encoding='utf-8',
    )
    return {
        'manifest_file': str(manifest_path),
        'private_patch_draft_file': str(patch_path),
    }


def json_dumps(payload: dict[str, Any]) -> str:
    import json

    return json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True, default=str)

