from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.reference_validation import contains_sensitive_reference


COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION = 'company-accounting-responsible-questions.v1'
COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST = 'company-accounting-responsible-questions.json'

CHILEAN_RUT_PATTERN = re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b')
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r'(^|[\s"\'])([A-Za-z]:[\\/]|\\\\)')
CANONICAL_ISSUE_CODE_PATTERN = re.compile(r'^[A-Za-z0-9_.:-]+$')

RESPONSIBLE_QUESTIONS_BOUNDARY = {
    'purpose': 'juntar_preguntas_concretas_para_revision_responsable_contabilidad_renta',
    'reads_real_documents': False,
    'stores_real_attachments': False,
    'stores_person_names': False,
    'stores_rut_values': False,
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


def _safe_label(value: Any, *, fallback: str = 'source') -> str:
    text = str(value or '').strip()
    if not text:
        return fallback
    if contains_sensitive_reference(text) or CHILEAN_RUT_PATTERN.search(text) or WINDOWS_ABSOLUTE_PATH_PATTERN.search(text):
        return 'sensitive-source-redacted'
    normalized = re.sub(r'[^A-Za-z0-9_.:-]+', '-', text).strip('-._:')
    return normalized or fallback


def _safe_issue_code(value: Any, *, fallback: str = 'blocking-code') -> str:
    text = str(value or '').strip()
    if not text:
        return fallback
    if (
        contains_sensitive_reference(text)
        or CHILEAN_RUT_PATTERN.search(text)
        or WINDOWS_ABSOLUTE_PATH_PATTERN.search(text)
        or not CANONICAL_ISSUE_CODE_PATTERN.fullmatch(text)
    ):
        return 'noncanonical-issue-code'
    return _safe_label(text, fallback=fallback)


def _safe_source_label(value: Any, *, fallback: str = 'source') -> str:
    text = str(value or '').strip()
    if not text:
        return fallback
    if (
        contains_sensitive_reference(text)
        or CHILEAN_RUT_PATTERN.search(text)
        or WINDOWS_ABSOLUTE_PATH_PATTERN.search(text)
        or not CANONICAL_ISSUE_CODE_PATTERN.fullmatch(text)
    ):
        return 'source-redacted'
    return _safe_label(text, fallback=fallback)


def _context_value(payload: dict[str, Any], *keys: str) -> Any:
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    for key in keys:
        if key in payload and payload.get(key) not in (None, ''):
            return payload.get(key)
        if key in summary and summary.get(key) not in (None, ''):
            return summary.get(key)
    return ''


def _ready_flags_from_payload(payload: dict[str, Any]) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    summary = payload.get('summary') if isinstance(payload.get('summary'), dict) else {}
    for source in (summary, payload):
        for key, value in source.items():
            if (key.startswith('ready_for_') or '_ready_for_' in key) and isinstance(value, bool):
                flags[key] = value
    return {key: flags[key] for key in sorted(flags)}


def _source_summary(*, label: str, payload: dict[str, Any]) -> dict[str, Any]:
    issues = _issues_from_payload(payload)
    return {
        'label': _safe_source_label(label),
        'schema_version': str(payload.get('schema_version') or ''),
        'classification': str(payload.get('classification') or ''),
        'company_ref_present': bool(_context_value(payload, 'company_ref', 'expected_company_ref')),
        'fiscal_year': _context_value(payload, 'fiscal_year', 'commercial_year'),
        'tax_year': _context_value(payload, 'tax_year'),
        'ready_flags': _ready_flags_from_payload(payload),
        'issues_total': len(issues),
        'source_hash': _canonical_hash(_safe_source_fingerprint_payload(payload)),
    }


def _safe_source_fingerprint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'schema_version': str(payload.get('schema_version') or ''),
        'classification': str(payload.get('classification') or ''),
        'company_ref_present': bool(_context_value(payload, 'company_ref', 'expected_company_ref')),
        'fiscal_year': _context_value(payload, 'fiscal_year', 'commercial_year'),
        'tax_year': _context_value(payload, 'tax_year'),
        'ready_flags': _ready_flags_from_payload(payload),
        'safe_issue_codes': [
            {
                'code': _safe_issue_code(issue['code']),
                'severity': _safe_label(issue['severity'], fallback='blocking'),
            }
            for issue in _issues_from_payload(payload)
        ],
    }


def _issues_from_payload(payload: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for key in ('issues', 'warnings'):
        raw_items = payload.get(key)
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if isinstance(item, dict):
                code = str(item.get('code') or '').strip()
                severity = str(item.get('severity') or ('warning' if key == 'warnings' else 'blocking')).strip()
            else:
                code = str(item or '').strip()
                severity = 'warning' if key == 'warnings' else 'blocking'
            if code:
                issues.append({'code': code, 'severity': severity})

    for key in ('blockers', 'annual_generation_blockers', 'validation_blockers'):
        raw_codes = payload.get(key)
        if not isinstance(raw_codes, list):
            continue
        for raw_code in raw_codes:
            code = str(raw_code or '').strip()
            if code:
                issues.append({'code': code, 'severity': 'blocking'})

    return issues


def _question_template(code: str, *, fiscal_year: int, tax_year: int) -> dict[str, str]:
    normalized = code.lower()
    if 'ownership' in normalized or 'participant' in normalized or 'socio' in normalized:
        return {
            'category': 'ownership',
            'question': (
                f'Confirmar snapshot ownership/vigencia al 31-12-{fiscal_year}: socios vigentes, '
                'RUT validos, porcentajes que suman 100.00, vigencias y evidence_ref no sensible.'
            ),
            'expected_answer': 'Patch ownership privado validado y aprobado para inyectar en paquete AC/AT.',
        }
    if 'bank' in normalized or 'leasing' in normalized or 'confirmation' in normalized:
        return {
            'category': 'bank_leasing',
            'question': (
                f'Confirmar respaldo Banco Chile/leasing AC{fiscal_year}: contrato/cronograma, historial de pagos, '
                'facturas/documentos tributarios y confirmacion bancaria formal o motivo de soporte observado.'
            ),
            'expected_answer': 'Manifiesto bancario/leasing redactado con cobertura y fuerza de confirmacion suficiente.',
        }
    if 'tax' in normalized or 'fiscal' in normalized or 'f22' in normalized or 'ddjj' in normalized or 'sii' in normalized:
        return {
            'category': 'tax_criteria',
            'question': (
                f'Confirmar criterio tributario AT{tax_year}: reglas aplicables, fuente oficial/experta y decision '
                'responsable antes de preparar presentacion o calculo final.'
            ),
            'expected_answer': 'Decision tributaria trazable no sensible con responsable, evidencia y alcance.',
        }
    if 'document' in normalized or 'source' in normalized or 'support' in normalized or 'evidence' in normalized:
        return {
            'category': 'missing_documents',
            'question': 'Completar o justificar documentos faltantes con refs no sensibles y sin adjuntos reales en Git.',
            'expected_answer': 'Refs de respaldo controladas o decision responsable de soporte observado.',
        }
    if 'accounting' in normalized or 'ledger' in normalized or 'monthly' in normalized or 'balance' in normalized:
        return {
            'category': 'accounting_progress',
            'question': (
                f'Completar capa contable AC{fiscal_year}: cierres mensuales, balances, hechos normalizados, '
                'paquete anual y comparacion revisable.'
            ),
            'expected_answer': 'Paquete contable/renta local listo para revision responsable, sin cierre automatico.',
        }
    return {
        'category': 'responsible_review',
        'question': f'Resolver blocker `{_safe_issue_code(code, fallback="blocking-code")}` mediante decision responsable trazable.',
        'expected_answer': 'Decision no sensible con responsable, evidencia y proximo paso.',
    }


def _add_question(
    questions: list[dict[str, Any]],
    seen: set[tuple[str, str]],
    *,
    code: str,
    source_label: str,
    severity: str,
    fiscal_year: int,
    tax_year: int,
) -> None:
    safe_code = _safe_issue_code(code, fallback='blocking-code')
    template = _question_template(safe_code, fiscal_year=fiscal_year, tax_year=tax_year)
    key = (template['category'], safe_code)
    if key in seen:
        return
    seen.add(key)
    questions.append(
        {
            'key': f'{template["category"]}.{safe_code}',
            'category': template['category'],
            'source_label': _safe_source_label(source_label),
            'source_issue_code': safe_code,
            'severity': _safe_label(severity, fallback='blocking'),
            'question': template['question'],
            'expected_answer': template['expected_answer'],
            'answer_should_contain_pii': False,
            'answer_should_be_stored_in_git': False,
            'requires_responsible_review': True,
        }
    )


def build_company_accounting_responsible_questions(
    *,
    source_payloads: dict[str, dict[str, Any]],
    company_ref: str = '',
    fiscal_year: int | None = None,
    tax_year: int | None = None,
) -> dict[str, Any]:
    if not isinstance(source_payloads, dict) or not source_payloads:
        raise ValueError('source_payloads debe contener al menos un artefacto JSON redactado.')

    safe_sources: dict[str, dict[str, Any]] = {}
    for label, payload in source_payloads.items():
        if not isinstance(payload, dict):
            safe_label = _safe_source_label(label, fallback='source')
            raise ValueError(f'source_payloads[{safe_label}] debe ser un objeto JSON.')
        safe_sources[_safe_source_label(label)] = payload

    inferred_company_ref = company_ref or ''
    inferred_fiscal_year = int(fiscal_year or 0)
    inferred_tax_year = int(tax_year or 0)
    for payload in safe_sources.values():
        inferred_company_ref = inferred_company_ref or str(
            _context_value(payload, 'company_ref', 'expected_company_ref') or ''
        )
        if not inferred_fiscal_year:
            inferred_fiscal_year = int(_context_value(payload, 'fiscal_year', 'commercial_year') or 0)
        if not inferred_tax_year:
            inferred_tax_year = int(_context_value(payload, 'tax_year') or 0)

    questions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for label, payload in safe_sources.items():
        for issue in _issues_from_payload(payload):
            _add_question(
                questions,
                seen,
                code=issue['code'],
                source_label=label,
                severity=issue['severity'],
                fiscal_year=inferred_fiscal_year,
                tax_year=inferred_tax_year,
            )

    categories = sorted({question['category'] for question in questions})
    return {
        'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': _safe_label(inferred_company_ref, fallback='company-ref-pending'),
        'fiscal_year': inferred_fiscal_year,
        'tax_year': inferred_tax_year,
        'source_summaries': [
            _source_summary(label=label, payload=payload)
            for label, payload in sorted(safe_sources.items())
        ],
        'summary': {
            'questions_total': len(questions),
            'categories_total': len(categories),
            'categories': categories,
            'ready_for_responsible_review': bool(questions),
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'questions': questions,
        'boundary': dict(RESPONSIBLE_QUESTIONS_BOUNDARY),
        'package_hash': _canonical_hash(
            {
                'company_ref': _safe_label(inferred_company_ref, fallback='company-ref-pending'),
                'fiscal_year': inferred_fiscal_year,
                'tax_year': inferred_tax_year,
                'source_hashes': {
                    label: _canonical_hash(_safe_source_fingerprint_payload(payload))
                    for label, payload in sorted(safe_sources.items())
                },
                'questions': questions,
                'boundary': RESPONSIBLE_QUESTIONS_BOUNDARY,
            }
        ),
    }


def write_company_accounting_responsible_questions(*, packet: dict[str, Any], output_dir: Path) -> dict[str, str]:
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError('El destino de preguntas responsables debe ser un directorio.')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError('El directorio destino de preguntas responsables debe estar vacio.')
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST
    manifest_path.write_text(
        json.dumps(packet, indent=2, ensure_ascii=True, sort_keys=True, default=str),
        encoding='utf-8',
    )
    return {
        'manifest_file': str(manifest_path),
    }
