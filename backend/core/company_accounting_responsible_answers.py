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
COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_SCHEMA_VERSION = (
    'company-accounting-responsible-handoff-packet.v1'
)
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST = 'company-accounting-responsible-answers-review.json'
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_SCHEMA_VERSION = (
    'company-accounting-responsible-answers-template.v1'
)
COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST = 'company-accounting-responsible-answers.template.json'
COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST = 'company-accounting-responsible-handoff-packet.json'

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
    source_summaries = _questions_source_summaries(questions_packet)

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
            'readiness_sources_total': len(source_summaries),
            'decision_states': dict(sorted(state_counter.items())),
            'categories': dict(sorted(category_counter.items())),
            'ready_for_responsible_decision_handoff': ready,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'question_source_summaries': source_summaries,
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
            'question_source_summaries': review['question_source_summaries'],
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


def _safe_ready_flags(raw_flags: Any) -> dict[str, bool]:
    if not isinstance(raw_flags, dict):
        return {}
    flags: dict[str, bool] = {}
    for key, value in raw_flags.items():
        key_text = str(key or '').strip()
        if _is_safe_ref(key_text) and isinstance(value, bool):
            flags[key_text] = value
    return {key: flags[key] for key in sorted(flags)}


def _safe_source_issue_codes(raw_issue_codes: Any) -> list[dict[str, str]]:
    if not isinstance(raw_issue_codes, list):
        return []
    issue_codes: list[dict[str, str]] = []
    for raw_issue in raw_issue_codes:
        if not isinstance(raw_issue, dict):
            continue
        code = _safe_issue_code(raw_issue.get('code'))
        if not code:
            continue
        issue_codes.append(
            {
                'code': code,
                'severity': _safe_ref(raw_issue.get('severity'), fallback='blocking'),
            }
        )
    return sorted(issue_codes, key=lambda item: (item['code'], item['severity']))


def _questions_source_summaries(questions_packet: dict[str, Any]) -> list[dict[str, Any]]:
    raw_summaries = questions_packet.get('source_summaries')
    if not isinstance(raw_summaries, list):
        return []

    summaries: list[dict[str, Any]] = []
    for raw_summary in raw_summaries:
        if not isinstance(raw_summary, dict):
            continue
        summaries.append(
            {
                'label': _safe_ref(raw_summary.get('label'), fallback='source'),
                'schema_version': _safe_ref(raw_summary.get('schema_version'), fallback='schema-version-pending'),
                'classification': _safe_ref(raw_summary.get('classification'), fallback='classification-pending'),
                'ready_flags': _safe_ready_flags(raw_summary.get('ready_flags')),
                'issues_total': _safe_int(raw_summary.get('issues_total')),
                'safe_issue_codes': _safe_source_issue_codes(raw_summary.get('safe_issue_codes')),
                'source_hash': _safe_ref(raw_summary.get('source_hash'), fallback='source-hash-pending'),
            }
        )
    return sorted(summaries, key=lambda item: (item['label'], item['source_hash']))


def _handoff_packet_fingerprint(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        'schema_version': manifest.get('schema_version'),
        'company_ref': manifest.get('company_ref'),
        'fiscal_year': manifest.get('fiscal_year'),
        'tax_year': manifest.get('tax_year'),
        'manifest_files': manifest.get('manifest_files'),
        'artifacts': manifest.get('artifacts'),
        'summary': manifest.get('summary'),
        'issue_codes': manifest.get('issue_codes'),
        'boundary': manifest.get('boundary'),
    }


def build_company_accounting_responsible_handoff_packet(
    *,
    questions_packet: dict[str, Any],
    answers_template: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(questions_packet, dict):
        raise ValueError('questions_packet debe ser un objeto JSON.')
    if not isinstance(answers_template, dict):
        raise ValueError('answers_template debe ser un objeto JSON.')

    questions_issues = _validate_questions_packet(questions_packet)
    if questions_issues:
        raise ValueError('questions_packet no es materializable como handoff responsable.')
    if answers_template.get('schema_version') != COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION:
        raise ValueError('answers_template tiene schema_version incompatible.')
    if answers_template.get('template_schema_version') != COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_SCHEMA_VERSION:
        raise ValueError('answers_template no es un template rellenable vigente.')

    review = validate_company_accounting_responsible_answers(
        questions_packet=questions_packet,
        answers_payload=answers_template,
        require_complete=True,
    )
    review_issue_codes = sorted({issue['code'] for issue in review['issues']})
    allowed_template_issues = {'responsible_answers.decision_pending'}
    if set(review_issue_codes) - allowed_template_issues:
        raise ValueError('answers_template contiene inconsistencias distintas de decisiones pendientes.')

    questions_total = len(_question_index(questions_packet))
    answers_total = len(answers_template.get('answers') if isinstance(answers_template.get('answers'), list) else [])
    pending_answers_total = sum(
        1
        for answer in answers_template.get('answers', [])
        if isinstance(answer, dict) and answer.get('decision_state') == 'pendiente'
    )
    if questions_total <= 0 or answers_total != questions_total or pending_answers_total != questions_total:
        raise ValueError('answers_template debe cubrir todas las preguntas en estado pendiente.')
    if answers_template.get('questions_packet_hash') != review['questions_packet_hash']:
        raise ValueError('answers_template no corresponde al paquete de preguntas informado.')

    template_summary = answers_template.get('template_summary') if isinstance(answers_template.get('template_summary'), dict) else {}
    if template_summary.get('ready_for_responsible_decision_handoff') not in (False, None):
        raise ValueError('answers_template no puede declarar handoff responsable listo.')
    if template_summary.get('final_tax_calculation') not in (False, None) or template_summary.get('sii_submission') not in (False, None):
        raise ValueError('answers_template no puede declarar calculo tributario final ni presentacion SII.')

    questions_summary = questions_packet.get('summary') if isinstance(questions_packet.get('summary'), dict) else {}
    source_summaries = _questions_source_summaries(questions_packet)
    manifest = {
        'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': review['company_ref'],
        'fiscal_year': review['fiscal_year'],
        'tax_year': review['tax_year'],
        'manifest_files': {
            'handoff_packet': COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
            'questions_packet': COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
            'answers_template': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
        },
        'artifacts': {
            'questions_packet': {
                'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
                'schema_version': questions_packet.get('schema_version'),
                'questions_total': questions_total,
                'categories_total': _safe_int(questions_summary.get('categories_total')),
                'source_summaries': source_summaries,
                'readiness_sources_total': len(source_summaries),
                'payload_hash': _canonical_hash(questions_packet),
                'package_hash': questions_packet.get('package_hash') or _canonical_hash(questions_packet),
            },
            'answers_template': {
                'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
                'schema_version': answers_template.get('schema_version'),
                'template_schema_version': answers_template.get('template_schema_version'),
                'answers_total': answers_total,
                'pending_answers_total': pending_answers_total,
                'payload_hash': _canonical_hash(answers_template),
                'template_hash': answers_template.get('template_hash') or _canonical_hash(answers_template),
            },
        },
        'summary': {
            'questions_total': questions_total,
            'answers_total': answers_total,
            'pending_answers_total': pending_answers_total,
            'readiness_sources_total': len(source_summaries),
            'ready_for_responsible_answer_completion': True,
            'ready_for_responsible_decision_handoff': False,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'issue_codes': ['responsible_handoff.review_pending'],
        'boundary': {
            'purpose': 'agrupar_preguntas_y_template_para_revision_responsable_contabilidad_renta',
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
        },
    }
    manifest['package_hash'] = _canonical_hash(_handoff_packet_fingerprint(manifest))
    return manifest


def write_company_accounting_responsible_handoff_packet(
    *,
    questions_packet: dict[str, Any],
    answers_template: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('El destino del handoff responsable debe ser un directorio.')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('El directorio destino del handoff responsable debe estar vacio.')
    manifest = build_company_accounting_responsible_handoff_packet(
        questions_packet=questions_packet,
        answers_template=answers_template,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST
    questions_path = output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST
    template_path = output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True, default=str),
        encoding='utf-8',
    )
    questions_path.write_text(
        json.dumps(questions_packet, indent=2, ensure_ascii=True, sort_keys=True, default=str),
        encoding='utf-8',
    )
    template_path.write_text(
        json.dumps(answers_template, indent=2, ensure_ascii=True, sort_keys=True, default=str),
        encoding='utf-8',
    )
    return {
        'manifest_file': str(manifest_path),
        'questions_file': str(questions_path),
        'answers_template_file': str(template_path),
    }


def verify_company_accounting_responsible_handoff_packet(*, package_dir: Path) -> dict[str, Any]:
    if not package_dir.exists() or not package_dir.is_dir():
        raise ValueError('El paquete de handoff responsable debe ser un directorio existente.')

    expected_files = {
        COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
        COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
        COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
    }
    actual_files = {path.name for path in package_dir.iterdir() if path.is_file()}
    if actual_files != expected_files or any(path.is_dir() for path in package_dir.iterdir()):
        raise ValueError('El paquete de handoff responsable debe contener solo los manifests esperados.')

    try:
        manifest = json.loads(
            (package_dir / COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST).read_text(encoding='utf-8')
        )
        questions_packet = json.loads(
            (package_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).read_text(encoding='utf-8')
        )
        answers_template = json.loads(
            (package_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).read_text(encoding='utf-8')
        )
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError('El paquete de handoff responsable contiene JSON invalido o ilegible.') from error
    if not isinstance(manifest, dict) or not isinstance(questions_packet, dict) or not isinstance(answers_template, dict):
        raise ValueError('Los manifests del paquete de handoff responsable deben ser objetos JSON.')

    expected_manifest = build_company_accounting_responsible_handoff_packet(
        questions_packet=questions_packet,
        answers_template=answers_template,
    )
    if _handoff_packet_fingerprint(manifest) != _handoff_packet_fingerprint(expected_manifest):
        raise ValueError('El manifest de handoff responsable no coincide con preguntas y template.')
    if manifest.get('package_hash') != expected_manifest.get('package_hash'):
        raise ValueError('El hash del paquete de handoff responsable no coincide.')

    return {
        'schema_version': manifest['schema_version'],
        'verified': True,
        'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
        'questions_file': COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
        'answers_template_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
        'company_ref': manifest['company_ref'],
        'fiscal_year': manifest['fiscal_year'],
        'tax_year': manifest['tax_year'],
        'package_hash': manifest['package_hash'],
        'summary': manifest['summary'],
        'question_source_summaries': manifest['artifacts']['questions_packet'].get('source_summaries') or [],
        'issue_codes': manifest['issue_codes'],
        'raw_paths_returned': False,
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
    source_summaries = _questions_source_summaries(
        {'source_summaries': payload.get('question_source_summaries') or payload.get('source_summaries')}
    )
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
        'readiness_sources_total': len(source_summaries),
        'question_source_summaries': source_summaries,
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
        'readiness_sources_total': len(source_summaries),
        'question_source_summaries': source_summaries,
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
                    'content_hash': '',
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
    source_summaries = _questions_source_summaries(payload)
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
    content_hash = _canonical_hash(
        {
            'schema_version': payload.get('schema_version'),
            'company_ref': payload.get('company_ref'),
            'fiscal_year': payload.get('fiscal_year'),
            'tax_year': payload.get('tax_year'),
            'questions': sorted(
                [question for question in questions if isinstance(question, dict)],
                key=lambda item: str(item.get('key') or ''),
            ),
            'source_summaries': source_summaries,
            'boundary': boundary,
        }
    )
    package_hash = str(payload.get('package_hash') or '').strip()
    fingerprint = {
        'path_hash': path_hash,
        'content_hash': content_hash,
        'package_hash': package_hash if _is_safe_ref(package_hash) else '',
        'schema_valid': schema_valid,
        'company_ref': _safe_ref(company_ref_raw, fallback='company-ref-invalid'),
        'fiscal_year': _safe_int(payload.get('fiscal_year')),
        'tax_year': _safe_int(payload.get('tax_year')),
        'questions_total': questions_total,
        'categories_total': categories_total,
        'readiness_sources_total': len(source_summaries),
        'source_summaries': source_summaries,
        'reported_ready_for_responsible_review': reported_ready,
        'ready_for_responsible_review': effective_ready,
        'issue_codes': sorted_issue_codes,
    }
    return {
        'candidate_hash': _canonical_hash(fingerprint),
        'path_hash': path_hash,
        'content_hash': content_hash,
        'package_hash': fingerprint['package_hash'],
        'manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
        'schema_valid': schema_valid,
        'company_ref': fingerprint['company_ref'],
        'fiscal_year': fingerprint['fiscal_year'],
        'tax_year': fingerprint['tax_year'],
        'questions_total': questions_total,
        'categories_total': categories_total,
        'readiness_sources_total': len(source_summaries),
        'source_summaries': source_summaries,
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
    content_hash = _canonical_hash(
        {
            'schema_version': payload.get('schema_version'),
            'template_schema_version': payload.get('template_schema_version'),
            'company_ref': payload.get('company_ref'),
            'fiscal_year': payload.get('fiscal_year'),
            'tax_year': payload.get('tax_year'),
            'questions_packet_hash': payload.get('questions_packet_hash'),
            'next_action_ref': payload.get('next_action_ref'),
            'answers': sorted(
                [answer for answer in answers if isinstance(answer, dict)],
                key=lambda item: str(item.get('question_key') or ''),
            ),
            'template_summary': summary,
            'boundary': boundary,
        }
    )
    template_hash = str(payload.get('template_hash') or '').strip()
    fingerprint = {
        'path_hash': path_hash,
        'content_hash': content_hash,
        'template_hash': template_hash if _is_safe_ref(template_hash) else '',
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
        'content_hash': content_hash,
        'template_hash': fingerprint['template_hash'],
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


def _unique_ready_candidates(
    candidates: list[dict[str, Any]],
    *,
    ready_field: str,
    preferred_hash_field: str,
) -> list[dict[str, Any]]:
    unique_candidates: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not candidate.get(ready_field):
            continue
        candidate_hash = str(candidate.get(preferred_hash_field) or '').strip()
        if not candidate_hash:
            candidate_hash = str(candidate.get('content_hash') or '').strip()
        if not candidate_hash:
            candidate_hash = str(candidate.get('candidate_hash') or '').strip()
        unique_candidates.setdefault(candidate_hash, candidate)
    return list(unique_candidates.values())


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
    raw_ready_questions = [candidate for candidate in question_candidates if candidate.get('ready_for_responsible_review')]
    raw_ready_templates = [candidate for candidate in template_candidates if candidate.get('ready_for_manual_completion')]
    ready_questions = _unique_ready_candidates(
        question_candidates,
        ready_field='ready_for_responsible_review',
        preferred_hash_field='package_hash',
    )
    ready_templates = _unique_ready_candidates(
        template_candidates,
        ready_field='ready_for_manual_completion',
        preferred_hash_field='template_hash',
    )
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
            'duplicate_ready_question_packets_total': max(len(raw_ready_questions) - len(ready_questions), 0),
            'template_candidates_total': len(template_candidates),
            'ready_answer_templates_total': len(ready_templates),
            'duplicate_ready_answer_templates_total': max(len(raw_ready_templates) - len(ready_templates), 0),
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
