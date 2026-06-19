from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.company_accounting_responsible_questions import (
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION,
)
from core.reference_validation import contains_sensitive_reference


COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION = 'company-accounting-responsible-answers.v1'
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION = 'company-accounting-responsible-answers-review.v1'
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST = 'company-accounting-responsible-answers-review.json'
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
    next_action_ref = answer.get('next_action_ref') or answer.get('next_action') or ''

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

    company_ref = _safe_ref(
        answers_payload.get('company_ref') or questions_packet.get('company_ref'),
        fallback='company-ref-pending',
    )
    fiscal_year = _safe_int(answers_payload.get('fiscal_year') or questions_packet.get('fiscal_year'))
    tax_year = _safe_int(answers_payload.get('tax_year') or questions_packet.get('tax_year'))

    if questions_packet.get('company_ref') and answers_payload.get('company_ref'):
        if _safe_ref(questions_packet.get('company_ref')) != _safe_ref(answers_payload.get('company_ref')):
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
    for field_name, field_value in (
        ('responsible_ref', fallback_responsible_ref),
        ('decision_ref', fallback_decision_ref),
    ):
        if not _is_safe_ref(field_value):
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
        )
        answers.append(safe_answer)
        issues.extend(answer_issues)

    missing_questions = sorted(set(questions.keys()) - answered_keys)
    if require_complete and missing_questions:
        issues.append(_issue('responsible_answers.questions_unanswered', count=len(missing_questions)))

    issue_counter = Counter(issue['code'] for issue in issues if issue.get('severity') == 'blocking')
    state_counter = Counter(answer['decision_state'] for answer in answers)
    category_counter = Counter(answer['category'] for answer in answers)
    ready = bool(questions) and not issue_counter and (not require_complete or not missing_questions)

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
