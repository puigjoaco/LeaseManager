from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from core.reference_validation import REDACTED_SENSITIVE_REFERENCE, contains_sensitive_reference


BANK_SUPPORT_MANIFEST_SCHEMA_VERSION = 'company-bank-support-coverage-manifest.v1'
DEFAULT_REQUIRED_OPERATION_CATEGORIES = (
    'contract_or_schedule',
    'payment_history',
    'invoice_or_tax_document_bundle',
)
KNOWN_SUPPORT_CATEGORIES = frozenset(
    {
        'contract_or_schedule',
        'payment_history',
        'invoice_or_tax_document_bundle',
        'debt_status',
        'insurance_or_fee_support',
        'bank_confirmation',
        'other_support',
    }
)
STRONG_CONFIRMATION_STRENGTHS = frozenset({'verified_complete'})
ACCEPTED_CONFIRMATION_STRENGTHS = frozenset({'expected_complete', 'verified_complete'})
KNOWN_CONFIRMATION_STRENGTHS = frozenset({'expected_complete', 'verified_complete'})
ALL_OPERATIONS = '*'
CHILEAN_RUT_PATTERN = re.compile(r'(?<!\d)\d{1,2}\.?\d{3}\.?\d{3}-[\dkK](?!\d)')
WINDOWS_ABSOLUTE_PATH_PATTERN = re.compile(r'(^|[\s"\'])([A-Za-z]:[\\/]|\\\\)')
COMPANY_BANK_SUPPORT_BOUNDARY = {
    'purpose': 'auditar_cobertura_documental_bancaria_para_revision_contable',
    'reads_documents': False,
    'stores_real_attachments': False,
    'uses_external_integrations': False,
    'opens_bank_gate': False,
    'autonomous_accounting': False,
    'final_tax_calculation': False,
    'sii_submission': False,
    'requires_responsible_review': True,
}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _normalize_ref(value: Any) -> str:
    return str(value or '').strip()


def _safe_ref(value: Any) -> str:
    normalized = _normalize_ref(value)
    if not normalized:
        return ''
    if (
        contains_sensitive_reference(normalized)
        or CHILEAN_RUT_PATTERN.search(normalized)
        or WINDOWS_ABSOLUTE_PATH_PATTERN.search(normalized)
    ):
        return REDACTED_SENSITIVE_REFERENCE
    return normalized


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values = []
        for key, item in value.items():
            if isinstance(key, str):
                values.append(key)
            values.extend(_string_values(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_string_values(item))
        return values
    return []


def _has_rut(value: Any) -> bool:
    return any(CHILEAN_RUT_PATTERN.search(item) for item in _string_values(value))


def _has_absolute_path(value: Any) -> bool:
    return any(WINDOWS_ABSOLUTE_PATH_PATTERN.search(item) for item in _string_values(value))


def _issue(code: str, message: str, *, severity: str = 'blocking', count: int = 1) -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _required_categories(operation: dict[str, Any]) -> list[str]:
    raw_categories = _as_list(operation.get('required_categories'))
    if not raw_categories:
        return list(DEFAULT_REQUIRED_OPERATION_CATEGORIES)
    return sorted({_normalize_ref(category) for category in raw_categories if _normalize_ref(category)})


def _coverage_percent(total_required: int, total_covered: int) -> int:
    if total_required <= 0:
        return 0
    return round((total_covered / total_required) * 100)


def _classification(*, operations_total: int, blocking_issues: list[dict[str, Any]]) -> str:
    if operations_total <= 0:
        return 'sin_datos'
    if blocking_issues:
        return 'parcial'
    return 'preparado'


def _operation_refs_for_attachment(attachment: dict[str, Any]) -> list[str]:
    refs = [_normalize_ref(item) for item in _as_list(attachment.get('operation_refs'))]
    refs = [item for item in refs if item]
    if refs:
        return refs
    operation_ref = _normalize_ref(attachment.get('operation_ref'))
    return [operation_ref] if operation_ref else []


def audit_company_bank_support_coverage(*, payload: dict[str, Any]) -> dict[str, Any]:
    required_operations_raw = _as_list(payload.get('required_operations'))
    attachments_raw = _as_list(payload.get('attachments'))
    confirmations_raw = _as_list(payload.get('confirmations'))

    safety_issues = []
    if contains_sensitive_reference(payload, include_sensitive_keys=True):
        safety_issues.append(
            _issue(
                'company_bank_support.sensitive_reference',
                'El manifiesto contiene referencias sensibles, URLs, correos, claves o tokens.',
            )
        )
    if _has_rut(payload):
        safety_issues.append(
            _issue(
                'company_bank_support.rut_exposed',
                'El manifiesto no debe contener RUT completos; usar company_ref/operation_ref redactados.',
            )
        )
    if _has_absolute_path(payload):
        safety_issues.append(
            _issue(
                'company_bank_support.absolute_path_exposed',
                'El manifiesto no debe contener rutas absolutas locales; usar refs opacas o path_ref hasheado.',
            )
        )

    operations = []
    operation_refs = set()
    invalid_required_categories = set()
    for operation in required_operations_raw:
        if not isinstance(operation, dict):
            continue
        operation_ref = _normalize_ref(operation.get('operation_ref'))
        if not operation_ref:
            continue
        required_categories = _required_categories(operation)
        invalid_required_categories.update(
            category for category in required_categories if category not in KNOWN_SUPPORT_CATEGORIES
        )
        operation_refs.add(operation_ref)
        operations.append(
            {
                'raw_operation_ref': operation_ref,
                'operation_ref': _safe_ref(operation_ref),
                'label_ref': _safe_ref(operation.get('label_ref')),
                'required_categories': required_categories,
            }
        )

    attachment_categories_by_operation: dict[str, set[str]] = defaultdict(set)
    attachment_counts_by_operation: dict[str, int] = defaultdict(int)
    invalid_attachment_categories = set()
    unknown_attachment_operation_refs = set()
    attachments_without_operation = 0
    for attachment in attachments_raw:
        if not isinstance(attachment, dict):
            continue
        category = _normalize_ref(attachment.get('category'))
        if category not in KNOWN_SUPPORT_CATEGORIES:
            invalid_attachment_categories.add(category or '<missing>')
            continue
        refs = _operation_refs_for_attachment(attachment)
        if not refs:
            attachments_without_operation += 1
            continue
        for ref in refs:
            targets = sorted(operation_refs) if ref == ALL_OPERATIONS else [ref]
            for target_ref in targets:
                if target_ref not in operation_refs:
                    unknown_attachment_operation_refs.add(target_ref)
                    continue
                attachment_categories_by_operation[target_ref].add(category)
                attachment_counts_by_operation[target_ref] += 1

    operation_results = []
    total_required_categories = 0
    total_covered_categories = 0
    for operation in operations:
        required_categories = operation['required_categories']
        covered_categories = sorted(attachment_categories_by_operation.get(operation['raw_operation_ref'], set()))
        missing_categories = [category for category in required_categories if category not in covered_categories]
        total_required_categories += len(required_categories)
        total_covered_categories += len(required_categories) - len(missing_categories)
        operation_results.append(
            {
                'operation_ref': operation['operation_ref'],
                'label_ref': operation['label_ref'],
                'required_categories': required_categories,
                'status': 'covered' if not missing_categories else 'partial',
                'covered_categories': covered_categories,
                'missing_categories': missing_categories,
                'attachments_count': attachment_counts_by_operation.get(operation['raw_operation_ref'], 0),
            }
        )

    confirmation_strengths = set()
    invalid_confirmation_strengths = set()
    for item in confirmations_raw:
        if not isinstance(item, dict):
            continue
        strength = _normalize_ref(item.get('statement_strength'))
        if not strength:
            continue
        if strength not in KNOWN_CONFIRMATION_STRENGTHS:
            invalid_confirmation_strengths.add(strength)
            continue
        confirmation_strengths.add(strength)
    accepted_confirmation_present = bool(confirmation_strengths & ACCEPTED_CONFIRMATION_STRENGTHS)
    strong_confirmation_present = bool(confirmation_strengths & STRONG_CONFIRMATION_STRENGTHS)

    issues = list(safety_issues)
    schema_version = payload.get('schema_version')
    if schema_version in {'', None}:
        issues.append(
            _issue(
                'company_bank_support.schema_version_missing',
                'Falta schema_version del manifiesto de cobertura bancaria/leasing.',
            )
        )
    elif schema_version != BANK_SUPPORT_MANIFEST_SCHEMA_VERSION:
        issues.append(
            _issue(
                'company_bank_support.unsupported_schema_version',
                'Version de manifiesto no soportada para cobertura bancaria contable.',
            )
        )
    if not operations:
        issues.append(
            _issue(
                'company_bank_support.required_operations_missing',
                'Falta listar operaciones bancarias/leasing requeridas para revision contable.',
            )
        )
    if invalid_required_categories:
        issues.append(
            _issue(
                'company_bank_support.invalid_required_category',
                'Hay categorias requeridas no reconocidas.',
                count=len(invalid_required_categories),
            )
        )
    if invalid_attachment_categories:
        issues.append(
            _issue(
                'company_bank_support.invalid_attachment_category',
                'Hay adjuntos clasificados con categorias no reconocidas.',
                count=len(invalid_attachment_categories),
            )
        )
    if attachments_without_operation:
        issues.append(
            _issue(
                'company_bank_support.attachment_without_operation',
                'Hay adjuntos sin operacion asociada ni comodin global.',
                count=attachments_without_operation,
            )
        )
    if unknown_attachment_operation_refs:
        issues.append(
            _issue(
                'company_bank_support.attachment_unknown_operation',
                'Hay adjuntos asociados a operaciones no listadas como requeridas.',
                count=len(unknown_attachment_operation_refs),
            )
        )
    if invalid_confirmation_strengths:
        issues.append(
            _issue(
                'company_bank_support.invalid_confirmation_strength',
                'Hay confirmaciones bancarias con statement_strength no reconocido.',
                count=len(invalid_confirmation_strengths),
            )
        )

    missing_operation_results = [item for item in operation_results if item['missing_categories']]
    if missing_operation_results:
        issues.append(
            _issue(
                'company_bank_support.operation_support_missing',
                'Faltan categorias de respaldo bancario/leasing para una o mas operaciones.',
                count=len(missing_operation_results),
            )
        )
    if not accepted_confirmation_present:
        issues.append(
            _issue(
                'company_bank_support.bank_confirmation_missing',
                'Falta confirmacion bancaria redactada sobre completitud esperada o verificada del respaldo.',
            )
        )

    warnings = []
    if accepted_confirmation_present and not strong_confirmation_present:
        warnings.append(
            _issue(
                'company_bank_support.bank_confirmation_not_file_by_file_verified',
                'La confirmacion bancaria permite revisar, pero no prueba verificacion archivo por archivo.',
                severity='warning',
            )
        )

    blocking_issues = [issue for issue in issues if issue['severity'] == 'blocking']
    ready = bool(operations) and not blocking_issues
    formal_ready = ready and strong_confirmation_present
    operations_with_full_support = sum(1 for item in operation_results if item['status'] == 'covered')

    return {
        'schema_version': BANK_SUPPORT_MANIFEST_SCHEMA_VERSION,
        'company_ref': _safe_ref(payload.get('company_ref')),
        'fiscal_year': payload.get('fiscal_year'),
        'tax_year': payload.get('tax_year'),
        'classification': _classification(operations_total=len(operations), blocking_issues=blocking_issues),
        'coverage_percent': _coverage_percent(total_required_categories, total_covered_categories),
        'ready_for_accounting_document_review': ready,
        'ready_for_formal_bank_support_review': formal_ready,
        'boundary': dict(COMPANY_BANK_SUPPORT_BOUNDARY),
        'summary': {
            'required_operations': len(operations),
            'operations_with_full_support': operations_with_full_support,
            'attachments_total': len(attachments_raw),
            'confirmations_total': len(confirmations_raw),
            'accepted_confirmation_present': accepted_confirmation_present,
            'strong_confirmation_present': strong_confirmation_present,
            'required_categories_total': total_required_categories,
            'covered_categories_total': total_covered_categories,
        },
        'operations': operation_results,
        'issue_counts': {
            'blocking': len(blocking_issues),
            'warning': len(warnings),
        },
        'issues': issues,
        'warnings': warnings,
        'next_blocking_operation': next(
            (item['operation_ref'] for item in operation_results if item['missing_categories']),
            '',
        ),
        'manifest_policy': {
            'real_documents_allowed_in_manifest': False,
            'raw_email_bodies_allowed': False,
            'full_rut_allowed': False,
            'password_or_credential_allowed': False,
            'absolute_paths_allowed': False,
        },
    }
