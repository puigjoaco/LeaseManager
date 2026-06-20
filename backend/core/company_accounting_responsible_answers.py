from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.company_accounting_responsible_questions import (
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION,
)
from core.reference_validation import contains_sensitive_reference


COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION = 'company-accounting-responsible-answers.v1'
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION = 'company-accounting-responsible-answers-review.v1'
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_DISCOVERY_SCHEMA_VERSION = (
    'company-accounting-responsible-answers-review-discovery.v1'
)
COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PREFLIGHT_SCHEMA_VERSION = (
    'company-accounting-responsible-handoff-preflight.v1'
)
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST = 'company-accounting-responsible-answers-review.json'
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_SCHEMA_VERSION = (
    'company-accounting-responsible-answers-template.v1'
)
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST = 'company-accounting-responsible-answers.template.json'

CHILEAN_RUT_PATTERN = re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b')
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r'(^|[\s"\'])([A-Za-z]:[\\/]|\\\\)')
SAFE_REF_PATTERN = re.compile(r'^[A-Za-z0-9_.:-]+$')

ALLOWED_DECISION_STATES = {'pendiente', 'observado', 'respondido', 'resuelto_controlado'}
RAW_TEXT_FIELDS = {
    'answer',
    'answer_text',
    'comment',
    'comments',
    'detalle',
    'message',
    'mensaje',
    'note',
    'notes',
    'observacion',
    'raw',
    'raw_text',
    'texto',
}

RESPONSIBLE_ANSWERS_BOUNDARY = {
    'purpose': 'validar_respuestas_no_sensibles_a_preguntas_responsables_contabilidad_renta',
    'reads_real_documents': False,
    'stores_real_attachments': False,
    'stores_person_names': False,
    'stores_rut_values': False,
    'stores_raw_answers': False,
    'uses_external_integrations': False,
    'opens_bank_gate': False,
    'opens_sii_gate': False,
    'autonomous_accounting': False,
    'final_tax_calculation': False,
    'sii_submission': False,
    'requires_responsible_review': True,
}


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _is_safe_ref(value: Any) -> bool:
    text = str(value or '').strip()
    return bool(text) and not (
        contains_sensitive_reference(text)
        or CHILEAN_RUT_PATTERN.search(text)
        or WINDOWS_ABSOLUTE_PATH_PATTERN.search(text)
        or not SAFE_REF_PATTERN.fullmatch(text)
    )


def _safe_ref(value: Any, *, fallback: str = 'ref-pending') -> str:
    text = str(value or '').strip()
    return text if _is_safe_ref(text) else fallback


def _first_safe_ref(*values: Any, fallback: str = 'ref-pending') -> str:
    for value in values:
        text = str(value or '').strip()
        if _is_safe_ref(text):
            return text
    return fallback


def _safe_issue_code(value: Any, *, fallback: str = 'redacted-issue-code') -> str:
    text = str(value or '').strip()
    return text if _is_safe_ref(text) else fallback


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _issue(code: str, *, severity: str = 'blocking', count: int = 1) -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
    }


def _question_index(questions_packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    questions = questions_packet.get('questions')
    if not isinstance(questions, list):
        return {}
    indexed = {}
    for question in questions:
        if not isinstance(question, dict):
            continue
        key = str(question.get('key') or '').strip()
        if key:
            indexed[key] = {
                'key': key,
                'category': _safe_ref(question.get('category'), fallback='responsible_review'),
                'source_issue_code': _safe_ref(question.get('source_issue_code'), fallback='blocking-code'),
                'severity': _safe_ref(question.get('severity'), fallback='blocking'),
            }
    return indexed


def _validate_questions_packet(questions_packet: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    if questions_packet.get('schema_version') != COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION:
        issues.append(_issue('responsible_answers.questions_schema_unsupported'))
    boundary = questions_packet.get('boundary') if isinstance(questions_packet.get('boundary'), dict) else {}
    if boundary.get('final_tax_calculation') not in (False, None) or boundary.get('sii_submission') not in (False, None):
        issues.append(_issue('responsible_answers.questions_boundary_invalid'))
    if not _question_index(questions_packet):
        issues.append(_issue('responsible_answers.questions_missing'))
    return issues


def _safe_answer_entry(
    *,
    answer: dict[str, Any],
    question: dict[str, Any],
    fallback_responsible_ref: str,
    fallback_decision_ref: str,
    fallback_evidence_ref: str,
    fallback_next_action_ref: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues = []
    raw_keys = sorted(set(answer.keys()) & RAW_TEXT_FIELDS)
    if raw_keys:
        issues.append(_issue('responsible_answers.raw_text_field_not_allowed', count=len(raw_keys)))

    decision_state = str(answer.get('decision_state') or '').strip()
    if decision_state not in ALLOWED_DECISION_STATES:
        issues.append(_issue('responsible_answers.decision_state_invalid'))
        decision_state = 'pendiente'
    elif decision_state == 'pendiente':
        issues.append(_issue('responsible_answers.decision_pending'))

    responsible_ref = answer.get('responsible_ref') or fallback_responsible_ref
    decision_ref = answer.get('decision_ref') or fallback_decision_ref
    evidence_ref = answer.get('evidence_ref') or fallback_evidence_ref
    next_action_ref = answer.get('next_action_ref') or answer.get('next_action') or fallback_next_action_ref

    if not _is_safe_ref(responsible_ref):
        issues.append(_issue('responsible_answers.responsible_ref_invalid'))
    if not _is_safe_ref(decision_ref):
        issues.append(_issue('responsible_answers.decision_ref_invalid'))
    if decision_state in {'observado', 'respondido', 'resuelto_controlado'} and not _is_safe_ref(evidence_ref):
        issues.append(_issue('responsible_answers.evidence_ref_invalid'))
    if not _is_safe_ref(next_action_ref):
        issues.append(_issue('responsible_answers.next_action_ref_invalid'))

    safe_entry = {
        'question_key': question['key'],
        'category': question['category'],
        'source_issue_code': question['source_issue_code'],
        'source_severity': question['severity'],
        'decision_state': decision_state,
        'responsible_ref': _safe_ref(responsible_ref, fallback='responsible-ref-invalid'),
        'decision_ref': _safe_ref(decision_ref, fallback='decision-ref-invalid'),
        'evidence_ref': _safe_ref(evidence_ref, fallback='evidence-ref-invalid'),
        'next_action_ref': _safe_ref(next_action_ref, fallback='next-action-ref-invalid'),
        'raw_text_stored': False,
        'answer_should_contain_pii': False,
        'answer_should_be_stored_in_git': False,
    }
    safe_entry['answer_hash'] = _canonical_hash(
        {
            'question_key': safe_entry['question_key'],
            'decision_state': safe_entry['decision_state'],
            'responsible_ref': safe_entry['responsible_ref'],
            'decision_ref': safe_entry['decision_ref'],
            'evidence_ref': safe_entry['evidence_ref'],
            'next_action_ref': safe_entry['next_action_ref'],
        }
    )
    return safe_entry, issues


def validate_company_accounting_responsible_answers(
    *,
    questions_packet: dict[str, Any],
    answers_payload: dict[str, Any],
    require_complete: bool = True,
) -> dict[str, Any]:
    if not isinstance(questions_packet, dict):
        raise ValueError('questions_packet debe ser un objeto JSON.')
    if not isinstance(answers_payload, dict):
        raise ValueError('answers_payload debe ser un objeto JSON.')

    questions = _question_index(questions_packet)
    issues = _validate_questions_packet(questions_packet)
    if answers_payload.get('schema_version') != COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION:
        issues.append(_issue('responsible_answers.answers_schema_unsupported'))
    raw_payload_keys = sorted(set(answers_payload.keys()) & RAW_TEXT_FIELDS)
    if raw_payload_keys:
        issues.append(_issue('responsible_answers.raw_text_field_not_allowed', count=len(raw_payload_keys)))

    questions_company_ref = str(questions_packet.get('company_ref') or '').strip()
    answers_company_ref = str(answers_payload.get('company_ref') or '').strip()
    if questions_company_ref and not _is_safe_ref(questions_company_ref):
        issues.append(_issue('responsible_answers.questions_company_ref_invalid'))
    if answers_company_ref and not _is_safe_ref(answers_company_ref):
        issues.append(_issue('responsible_answers.company_ref_invalid'))

    company_ref = _first_safe_ref(
        answers_company_ref,
        questions_company_ref,
        fallback='company-ref-pending',
    )
    fiscal_year = _safe_int(answers_payload.get('fiscal_year') or questions_packet.get('fiscal_year'))
    tax_year = _safe_int(answers_payload.get('tax_year') or questions_packet.get('tax_year'))

    if questions_company_ref and answers_company_ref and _is_safe_ref(questions_company_ref) and _is_safe_ref(answers_company_ref):
        if questions_company_ref != answers_company_ref:
            issues.append(_issue('responsible_answers.company_ref_mismatch'))
    if questions_packet.get('fiscal_year') and answers_payload.get('fiscal_year'):
        if _safe_int(questions_packet.get('fiscal_year')) != _safe_int(answers_payload.get('fiscal_year')):
            issues.append(_issue('responsible_answers.fiscal_year_mismatch'))
    if questions_packet.get('tax_year') and answers_payload.get('tax_year'):
        if _safe_int(questions_packet.get('tax_year')) != _safe_int(answers_payload.get('tax_year')):
            issues.append(_issue('responsible_answers.tax_year_mismatch'))

    fallback_responsible_ref = str(answers_payload.get('responsible_ref') or '').strip()
    fallback_decision_ref = str(answers_payload.get('decision_ref') or '').strip()
    fallback_evidence_ref = str(answers_payload.get('evidence_ref') or '').strip()
    fallback_next_action_ref = str(answers_payload.get('next_action_ref') or answers_payload.get('next_action') or '').strip()
    for field_name, field_value in (
        ('responsible_ref', fallback_responsible_ref),
        ('decision_ref', fallback_decision_ref),
    ):
        if not _is_safe_ref(field_value):
            issues.append(_issue(f'responsible_answers.{field_name}_invalid'))
    for field_name, field_value in (
        ('evidence_ref', fallback_evidence_ref),
        ('next_action_ref', fallback_next_action_ref),
    ):
        if field_value and not _is_safe_ref(field_value):
            issues.append(_issue(f'responsible_answers.{field_name}_invalid'))

    raw_answers = answers_payload.get('answers')
    if not isinstance(raw_answers, list):
        raw_answers = []
        issues.append(_issue('responsible_answers.answers_missing'))

    answers = []
    answered_keys = set()
    for raw_answer in raw_answers:
        if not isinstance(raw_answer, dict):
            issues.append(_issue('responsible_answers.answer_not_object'))
            continue
        question_key = str(raw_answer.get('question_key') or '').strip()
        if not _is_safe_ref(question_key):
            issues.append(_issue('responsible_answers.question_key_invalid'))
            continue
        question = questions.get(question_key)
        if not question:
            issues.append(_issue('responsible_answers.question_key_unknown'))
            continue
        if question_key in answered_keys:
            issues.append(_issue('responsible_answers.question_key_duplicate'))
            continue
        answered_keys.add(question_key)
        safe_answer, answer_issues = _safe_answer_entry(
            answer=raw_answer,
            question=question,
            fallback_responsible_ref=fallback_responsible_ref,
            fallback_decision_ref=fallback_decision_ref,
            fallback_evidence_ref=fallback_evidence_ref,
            fallback_next_action_ref=fallback_next_action_ref,
        )
        answers.append(safe_answer)
        issues.extend(answer_issues)

    # `require_complete=False` preserves observed-review materialization, not readiness.
    missing_questions = sorted(set(questions.keys()) - answered_keys)
    if missing_questions:
        issues.append(_issue('responsible_answers.questions_unanswered', count=len(missing_questions)))

    issue_counter = Counter(issue['code'] for issue in issues if issue.get('severity') == 'blocking')
    state_counter = Counter(answer['decision_state'] for answer in answers)
    category_counter = Counter(answer['category'] for answer in answers)
    ready = bool(questions) and not issue_counter and not missing_questions

    review = {
        'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': company_ref,
        'fiscal_year': fiscal_year,
        'tax_year': tax_year,
        'questions_packet_hash': _canonical_hash(
            {
                'schema_version': questions_packet.get('schema_version'),
                'company_ref': questions_packet.get('company_ref'),
                'fiscal_year': questions_packet.get('fiscal_year'),
                'tax_year': questions_packet.get('tax_year'),
                'questions': sorted(questions.values(), key=lambda item: item['key']),
                'boundary': questions_packet.get('boundary') if isinstance(questions_packet.get('boundary'), dict) else {},
            }
        ),
        'summary': {
            'questions_total': len(questions),
            'answers_total': len(answers),
            'missing_questions_total': len(missing_questions),
            'blocking_issues_total': sum(issue_counter.values()),
            'decision_states': dict(sorted(state_counter.items())),
            'categories': dict(sorted(category_counter.items())),
            'ready_for_responsible_decision_handoff': ready,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'missing_question_keys': missing_questions,
        'answers': sorted(answers, key=lambda item: item['question_key']),
        'issues': [
            {'code': code, 'severity': 'blocking', 'count': count}
            for code, count in sorted(issue_counter.items())
        ],
        'boundary': dict(RESPONSIBLE_ANSWERS_BOUNDARY),
    }
    review['package_hash'] = _canonical_hash(
        {
            'schema_version': review['schema_version'],
            'company_ref': review['company_ref'],
            'fiscal_year': review['fiscal_year'],
            'tax_year': review['tax_year'],
            'questions_packet_hash': review['questions_packet_hash'],
            'summary': review['summary'],
            'missing_question_keys': review['missing_question_keys'],
            'answers': review['answers'],
            'issues': review['issues'],
            'boundary': review['boundary'],
        }
    )
    return review


def build_company_accounting_responsible_answers_template(
    *,
    questions_packet: dict[str, Any],
    responsible_ref: str = 'responsible-ref-pending',
    decision_ref: str = 'decision-ref-pending',
    evidence_ref: str = 'evidence-ref-pending',
    next_action_ref: str = 'next-action-pending',
) -> dict[str, Any]:
    if not isinstance(questions_packet, dict):
        raise ValueError('questions_packet debe ser un objeto JSON.')

    issues = _validate_questions_packet(questions_packet)
    if issues:
        raise ValueError('questions_packet no es materializable como template de respuestas responsables.')

    questions = _question_index(questions_packet)
    fallback_responsible_ref = _safe_ref(responsible_ref, fallback='responsible-ref-pending')
    fallback_decision_ref = _safe_ref(decision_ref, fallback='decision-ref-pending')
    fallback_evidence_ref = _safe_ref(evidence_ref, fallback='evidence-ref-pending')
    fallback_next_action_ref = _safe_ref(next_action_ref, fallback='next-action-pending')

    answers = []
    for question in sorted(questions.values(), key=lambda item: item['key']):
        answers.append(
            {
                'question_key': question['key'],
                'category': question['category'],
                'source_issue_code': question['source_issue_code'],
                'source_severity': question['severity'],
                'decision_state': 'pendiente',
                'responsible_ref': fallback_responsible_ref,
                'decision_ref': fallback_decision_ref,
                'evidence_ref': fallback_evidence_ref,
                'next_action_ref': fallback_next_action_ref,
            }
        )

    template = {
        'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION,
        'template_schema_version': 'company-accounting-responsible-answers-template.v1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': _safe_ref(questions_packet.get('company_ref'), fallback='company-ref-pending'),
        'fiscal_year': _safe_int(questions_packet.get('fiscal_year')),
        'tax_year': _safe_int(questions_packet.get('tax_year')),
        'responsible_ref': fallback_responsible_ref,
        'decision_ref': fallback_decision_ref,
        'evidence_ref': fallback_evidence_ref,
        'next_action_ref': fallback_next_action_ref,
        'questions_packet_hash': _canonical_hash(
            {
                'schema_version': questions_packet.get('schema_version'),
                'company_ref': questions_packet.get('company_ref'),
                'fiscal_year': questions_packet.get('fiscal_year'),
                'tax_year': questions_packet.get('tax_year'),
                'questions': sorted(questions.values(), key=lambda item: item['key']),
                'boundary': questions_packet.get('boundary') if isinstance(questions_packet.get('boundary'), dict) else {},
            }
        ),
        'answers': answers,
        'template_summary': {
            'questions_total': len(questions),
            'answers_total': len(answers),
            'decision_state': 'pendiente',
            'ready_for_responsible_decision_handoff': False,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'boundary': dict(RESPONSIBLE_ANSWERS_BOUNDARY),
    }
    template['template_hash'] = _canonical_hash(
        {
            'schema_version': template['schema_version'],
            'template_schema_version': template['template_schema_version'],
            'company_ref': template['company_ref'],
            'fiscal_year': template['fiscal_year'],
            'tax_year': template['tax_year'],
            'questions_packet_hash': template['questions_packet_hash'],
            'next_action_ref': template['next_action_ref'],
            'answers': template['answers'],
            'template_summary': template['template_summary'],
            'boundary': template['boundary'],
        }
    )
    return template


def write_company_accounting_responsible_answers_template(
    *,
    template: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('El destino del template de respuestas responsables debe ser un directorio.')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('El directorio destino del template de respuestas responsables debe estar vacio.')
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST
    manifest_path.write_text(
        json.dumps(template, indent=2, ensure_ascii=True, sort_keys=True, default=str),
        encoding='utf-8',
    )
    return {
        'manifest_file': str(manifest_path),
    }


def write_company_accounting_responsible_answers_review(*, review: dict[str, Any], output_dir: Path) -> dict[str, str]:
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('El destino de respuestas responsables debe ser un directorio.')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('El directorio destino de respuestas responsables debe estar vacio.')
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST
    manifest_path.write_text(
        json.dumps(review, indent=2, ensure_ascii=True, sort_keys=True, default=str),
        encoding='utf-8',
    )
    return {
        'manifest_file': str(manifest_path),
    }


def _review_discovery_candidate(*, payload: dict[str, Any], relative_path_ref: str) -> dict[str, Any]:
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    issues = payload.get('issues') if isinstance(payload.get('issues'), list) else []
    answers = payload.get('answers') if isinstance(payload.get('answers'), list) else []
    missing_question_keys = (
        payload.get('missing_question_keys') if isinstance(payload.get('missing_question_keys'), list) else []
    )
    boundary = payload.get('boundary') if isinstance(payload.get('boundary'), dict) else {}
    schema_valid = payload.get('schema_version') == COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION
    company_ref_raw = str(payload.get('company_ref') or '').strip()
    company_ref_safe = _is_safe_ref(company_ref_raw)
    company_ref = _safe_ref(company_ref_raw, fallback='company-ref-invalid')
    questions_total = _safe_int(summary.get('questions_total'))
    answers_total = max(_safe_int(summary.get('answers_total')), len(answers))
    missing_questions_total = max(_safe_int(summary.get('missing_questions_total')), len(missing_question_keys))
    issue_codes = {
        _safe_issue_code(issue.get('code'))
        for issue in issues
        if isinstance(issue, dict) and str(issue.get('code') or '').strip()
    }
    if not schema_valid:
        issue_codes.add('responsible_answers.review_schema_invalid')
    if not company_ref_safe:
        issue_codes.add('responsible_answers.company_ref_invalid')
    if missing_questions_total:
        issue_codes.add('responsible_answers.questions_unanswered')
    if questions_total and answers_total < questions_total:
        issue_codes.add('responsible_answers.answer_count_mismatch')
    if boundary.get('final_tax_calculation') not in (False, None) or boundary.get('sii_submission') not in (False, None):
        issue_codes.add('responsible_answers.review_boundary_invalid')
    sorted_issue_codes = sorted(issue_codes)
    blocking_issues_total = max(
        _safe_int(summary.get('blocking_issues_total')),
        sum(max(_safe_int(issue.get('count')), 1) for issue in issues if isinstance(issue, dict)),
        missing_questions_total,
        len(sorted_issue_codes),
    )
    reported_ready = bool(summary.get('ready_for_responsible_decision_handoff'))
    effective_ready = (
        schema_valid
        and company_ref_safe
        and questions_total > 0
        and answers_total >= questions_total
        and missing_questions_total == 0
        and blocking_issues_total == 0
        and not sorted_issue_codes
        and reported_ready
    )
    path_hash = _canonical_hash({'relative_path_ref': relative_path_ref})
    package_hash = str(payload.get('package_hash') or '').strip()
    candidate_fingerprint = {
        'path_hash': path_hash,
        'package_hash': package_hash if _is_safe_ref(package_hash) else '',
        'schema_valid': schema_valid,
        'company_ref': company_ref,
        'fiscal_year': _safe_int(payload.get('fiscal_year')),
        'tax_year': _safe_int(payload.get('tax_year')),
        'questions_packet_hash': _safe_ref(payload.get('questions_packet_hash'), fallback='questions-packet-hash-invalid'),
        'questions_total': questions_total,
        'answers_total': answers_total,
        'missing_questions_total': missing_questions_total,
        'blocking_issues_total': blocking_issues_total,
        'issue_codes': sorted_issue_codes,
        'reported_ready_for_responsible_decision_handoff': reported_ready,
        'ready_for_responsible_decision_handoff': effective_ready,
    }
    return {
        'candidate_hash': _canonical_hash(candidate_fingerprint),
        'path_hash': path_hash,
        'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
        'schema_valid': schema_valid,
        'company_ref': company_ref,
        'fiscal_year': candidate_fingerprint['fiscal_year'],
        'tax_year': candidate_fingerprint['tax_year'],
        'questions_total': questions_total,
        'answers_total': answers_total,
        'missing_questions_total': missing_questions_total,
        'blocking_issues_total': blocking_issues_total,
        'issue_codes': sorted_issue_codes,
        'reported_ready_for_responsible_decision_handoff': reported_ready,
        'ready_for_responsible_decision_handoff': effective_ready,
        'raw_path_returned': False,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def audit_company_accounting_responsible_answers_review_presence(*, search_root: Path) -> dict[str, Any]:
    root = Path(search_root).resolve()
    candidates: list[dict[str, Any]] = []
    read_errors_total = 0
    if root.exists():
        for manifest_path in sorted(root.rglob(COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST)):
            try:
                relative_path_ref = manifest_path.resolve().relative_to(root).as_posix()
            except ValueError:
                relative_path_ref = COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST
            try:
                payload = json.loads(manifest_path.read_text(encoding='utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('manifest JSON debe ser objeto')
            except (json.JSONDecodeError, OSError, ValueError):
                read_errors_total += 1
                candidates.append(
                    {
                        'candidate_hash': _canonical_hash(
                            {
                                'relative_path_ref': relative_path_ref,
                                'error': 'responsible_answers.review_read_failed',
                            }
                        ),
                        'path_hash': _canonical_hash({'relative_path_ref': relative_path_ref}),
                        'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
                        'schema_valid': False,
                        'company_ref': 'company-ref-invalid',
                        'fiscal_year': 0,
                        'tax_year': 0,
                        'questions_total': 0,
                        'answers_total': 0,
                        'missing_questions_total': 0,
                        'blocking_issues_total': 1,
                        'issue_codes': ['responsible_answers.review_read_failed'],
                        'reported_ready_for_responsible_decision_handoff': False,
                        'ready_for_responsible_decision_handoff': False,
                        'raw_path_returned': False,
                        'final_tax_calculation': False,
                        'sii_submission': False,
                    }
                )
                continue
            candidates.append(_review_discovery_candidate(payload=payload, relative_path_ref=relative_path_ref))
    ready_candidates = [candidate for candidate in candidates if candidate['ready_for_responsible_decision_handoff']]
    issue_codes = set()
    if not candidates:
        issue_codes.add('responsible_answers.review_missing')
    if read_errors_total:
        issue_codes.add('responsible_answers.review_read_failed')
    if len(ready_candidates) > 1:
        issue_codes.add('responsible_answers.multiple_ready_reviews')
    if candidates and not ready_candidates:
        issue_codes.add('responsible_answers.review_not_ready')
    selected_ready_candidate_hash = ready_candidates[0]['candidate_hash'] if len(ready_candidates) == 1 else ''
    return {
        'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_DISCOVERY_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'search': {
            'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
            'raw_paths_returned': False,
            'reads_real_documents': False,
            'uses_external_integrations': False,
            'opens_bank_gate': False,
            'opens_sii_gate': False,
        },
        'summary': {
            'candidates_total': len(candidates),
            'ready_candidates_total': len(ready_candidates),
            'read_errors_total': read_errors_total,
            'ready_for_responsible_decision_handoff': len(ready_candidates) == 1,
            'selected_ready_candidate_hash': selected_ready_candidate_hash,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'issue_codes': sorted(issue_codes),
        'candidates': candidates,
    }


def _read_manifest_candidates(*, root: Path, manifest_name: str, builder) -> tuple[list[dict[str, Any]], int]:
    candidates: list[dict[str, Any]] = []
    read_errors_total = 0
    if not root.exists():
        return candidates, read_errors_total
    for manifest_path in sorted(root.rglob(manifest_name)):
        try:
            relative_path_ref = manifest_path.resolve().relative_to(root).as_posix()
        except ValueError:
            relative_path_ref = manifest_name
        try:
            payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            if not isinstance(payload, dict):
                raise ValueError('manifest JSON debe ser objeto')
        except (json.JSONDecodeError, OSError, ValueError):
            read_errors_total += 1
            candidates.append(
                {
                    'candidate_hash': _canonical_hash(
                        {'relative_path_ref': relative_path_ref, 'error': 'responsible_handoff.manifest_read_failed'}
                    ),
                    'path_hash': _canonical_hash({'relative_path_ref': relative_path_ref}),
                    'manifest_file': manifest_name,
                    'schema_valid': False,
                    'company_ref': 'company-ref-invalid',
                    'fiscal_year': 0,
                    'tax_year': 0,
                    'issue_codes': ['responsible_handoff.manifest_read_failed'],
                    'raw_path_returned': False,
                }
            )
            continue
        candidates.append(builder(payload=payload, relative_path_ref=relative_path_ref))
    return candidates, read_errors_total


def _questions_discovery_candidate(*, payload: dict[str, Any], relative_path_ref: str) -> dict[str, Any]:
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    boundary = payload.get('boundary') if isinstance(payload.get('boundary'), dict) else {}
    schema_valid = payload.get('schema_version') == COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION
    company_ref_raw = str(payload.get('company_ref') or '').strip()
    company_ref_safe = _is_safe_ref(company_ref_raw)
    questions = payload.get('questions') if isinstance(payload.get('questions'), list) else []
    reported_questions_total = _safe_int(summary.get('questions_total'))
    questions_total = len(questions)
    categories_total = _safe_int(summary.get('categories_total'))
    reported_ready = bool(summary.get('ready_for_responsible_review'))
    issue_codes = set()
    if not schema_valid:
        issue_codes.add('responsible_handoff.questions_schema_invalid')
    if not company_ref_safe:
        issue_codes.add('responsible_handoff.questions_company_ref_invalid')
    if questions_total <= 0:
        issue_codes.add('responsible_handoff.questions_missing')
    if reported_questions_total and questions_total < reported_questions_total:
        issue_codes.add('responsible_handoff.question_count_mismatch')
    if boundary.get('final_tax_calculation') not in (False, None) or boundary.get('sii_submission') not in (False, None):
        issue_codes.add('responsible_handoff.questions_boundary_invalid')
    sorted_issue_codes = sorted(issue_codes)
    effective_ready = schema_valid and company_ref_safe and questions_total > 0 and reported_ready and not sorted_issue_codes
    path_hash = _canonical_hash({'relative_path_ref': relative_path_ref})
    fingerprint = {
        'path_hash': path_hash,
        'schema_valid': schema_valid,
        'company_ref': _safe_ref(company_ref_raw, fallback='company-ref-invalid'),
        'fiscal_year': _safe_int(payload.get('fiscal_year')),
        'tax_year': _safe_int(payload.get('tax_year')),
        'questions_total': questions_total,
        'categories_total': categories_total,
        'reported_ready_for_responsible_review': reported_ready,
        'ready_for_responsible_review': effective_ready,
        'issue_codes': sorted_issue_codes,
    }
    return {
        'candidate_hash': _canonical_hash(fingerprint),
        'path_hash': path_hash,
        'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
        'schema_valid': schema_valid,
        'company_ref': fingerprint['company_ref'],
        'fiscal_year': fingerprint['fiscal_year'],
        'tax_year': fingerprint['tax_year'],
        'questions_total': questions_total,
        'categories_total': categories_total,
        'reported_ready_for_responsible_review': reported_ready,
        'ready_for_responsible_review': effective_ready,
        'issue_codes': sorted_issue_codes,
        'raw_path_returned': False,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def _template_discovery_candidate(*, payload: dict[str, Any], relative_path_ref: str) -> dict[str, Any]:
    summary = payload.get('template_summary') if isinstance(payload.get('template_summary'), dict) else {}
    boundary = payload.get('boundary') if isinstance(payload.get('boundary'), dict) else {}
    schema_valid = payload.get('schema_version') == COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION
    template_schema_valid = (
        payload.get('template_schema_version') == COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_SCHEMA_VERSION
    )
    company_ref_raw = str(payload.get('company_ref') or '').strip()
    company_ref_safe = _is_safe_ref(company_ref_raw)
    answers = payload.get('answers') if isinstance(payload.get('answers'), list) else []
    questions_total = _safe_int(summary.get('questions_total'))
    reported_answers_total = _safe_int(summary.get('answers_total'))
    answers_total = len(answers)
    pending_answers_total = sum(1 for answer in answers if isinstance(answer, dict) and answer.get('decision_state') == 'pendiente')
    issue_codes = set()
    if not schema_valid:
        issue_codes.add('responsible_handoff.template_answers_schema_invalid')
    if not template_schema_valid:
        issue_codes.add('responsible_handoff.template_schema_invalid')
    if not company_ref_safe:
        issue_codes.add('responsible_handoff.template_company_ref_invalid')
    if questions_total <= 0 or answers_total <= 0:
        issue_codes.add('responsible_handoff.template_answers_missing')
    if reported_answers_total and answers_total < reported_answers_total:
        issue_codes.add('responsible_handoff.template_answer_count_mismatch')
    if questions_total and answers_total < questions_total:
        issue_codes.add('responsible_handoff.template_answer_count_mismatch')
    if boundary.get('final_tax_calculation') not in (False, None) or boundary.get('sii_submission') not in (False, None):
        issue_codes.add('responsible_handoff.template_boundary_invalid')
    sorted_issue_codes = sorted(issue_codes)
    ready_for_manual_completion = (
        schema_valid
        and template_schema_valid
        and company_ref_safe
        and questions_total > 0
        and answers_total >= questions_total
        and not sorted_issue_codes
    )
    path_hash = _canonical_hash({'relative_path_ref': relative_path_ref})
    fingerprint = {
        'path_hash': path_hash,
        'schema_valid': schema_valid,
        'template_schema_valid': template_schema_valid,
        'company_ref': _safe_ref(company_ref_raw, fallback='company-ref-invalid'),
        'fiscal_year': _safe_int(payload.get('fiscal_year')),
        'tax_year': _safe_int(payload.get('tax_year')),
        'questions_total': questions_total,
        'answers_total': answers_total,
        'pending_answers_total': pending_answers_total,
        'ready_for_manual_completion': ready_for_manual_completion,
        'issue_codes': sorted_issue_codes,
    }
    return {
        'candidate_hash': _canonical_hash(fingerprint),
        'path_hash': path_hash,
        'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
        'schema_valid': schema_valid,
        'template_schema_valid': template_schema_valid,
        'company_ref': fingerprint['company_ref'],
        'fiscal_year': fingerprint['fiscal_year'],
        'tax_year': fingerprint['tax_year'],
        'questions_total': questions_total,
        'answers_total': answers_total,
        'pending_answers_total': pending_answers_total,
        'ready_for_manual_completion': ready_for_manual_completion,
        'ready_for_responsible_decision_handoff': False,
        'issue_codes': sorted_issue_codes,
        'raw_path_returned': False,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def audit_company_accounting_responsible_handoff_preflight(*, search_root: Path) -> dict[str, Any]:
    root = Path(search_root).resolve()
    question_candidates, question_read_errors = _read_manifest_candidates(
        root=root,
        manifest_name=COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
        builder=_questions_discovery_candidate,
    )
    template_candidates, template_read_errors = _read_manifest_candidates(
        root=root,
        manifest_name=COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
        builder=_template_discovery_candidate,
    )
    review_audit = audit_company_accounting_responsible_answers_review_presence(search_root=root)
    ready_questions = [candidate for candidate in question_candidates if candidate.get('ready_for_responsible_review')]
    ready_templates = [candidate for candidate in template_candidates if candidate.get('ready_for_manual_completion')]
    review_ready = bool(review_audit['summary']['ready_for_responsible_decision_handoff'])
    issue_codes = set(review_audit['issue_codes'])
    if not question_candidates:
        issue_codes.add('responsible_handoff.questions_missing')
    if question_read_errors:
        issue_codes.add('responsible_handoff.questions_read_failed')
    if len(ready_questions) > 1:
        issue_codes.add('responsible_handoff.multiple_ready_question_packets')
    if question_candidates and not ready_questions:
        issue_codes.add('responsible_handoff.questions_not_ready')
    if not template_candidates:
        issue_codes.add('responsible_handoff.template_missing')
    if template_read_errors:
        issue_codes.add('responsible_handoff.template_read_failed')
    if len(ready_templates) > 1:
        issue_codes.add('responsible_handoff.multiple_ready_answer_templates')
    if template_candidates and not ready_templates:
        issue_codes.add('responsible_handoff.template_not_ready')
    ready_for_answer_completion = len(ready_questions) == 1 and len(ready_templates) == 1 and not review_ready
    if ready_for_answer_completion:
        issue_codes.add('responsible_handoff.review_pending')
    return {
        'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PREFLIGHT_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'search': {
            'manifest_files': [
                COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
                COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
                COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
            ],
            'raw_paths_returned': False,
            'reads_real_documents': False,
            'uses_external_integrations': False,
            'opens_bank_gate': False,
            'opens_sii_gate': False,
        },
        'summary': {
            'questions_candidates_total': len(question_candidates),
            'ready_question_packets_total': len(ready_questions),
            'template_candidates_total': len(template_candidates),
            'ready_answer_templates_total': len(ready_templates),
            'review_candidates_total': review_audit['summary']['candidates_total'],
            'ready_review_candidates_total': review_audit['summary']['ready_candidates_total'],
            'ready_for_responsible_answer_completion': ready_for_answer_completion,
            'ready_for_responsible_decision_handoff': review_ready,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'issue_codes': sorted(issue_codes),
        'questions': {
            'read_errors_total': question_read_errors,
            'candidates': question_candidates,
        },
        'answer_templates': {
            'read_errors_total': template_read_errors,
            'candidates': template_candidates,
        },
        'reviews': {
            'read_errors_total': review_audit['summary']['read_errors_total'],
            'candidates': review_audit['candidates'],
        },
    }
