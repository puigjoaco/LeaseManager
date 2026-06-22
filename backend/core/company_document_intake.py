from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from core.annual_tax_source_manifest import (
    CATEGORY_META,
    EXPECTED_ANNUAL_TAX_REGISTER_KEYS,
    EXPECTED_DDJJ_FORMS,
    MANIFEST_SCHEMA_VERSION as ANNUAL_TAX_SOURCE_MANIFEST_SCHEMA_VERSION,
    MONTHS,
    payload_hash,
)
from core.company_bank_support_coverage import (
    BANK_SUPPORT_MANIFEST_SCHEMA_VERSION,
    KNOWN_SUPPORT_CATEGORIES,
    audit_company_bank_support_coverage,
)
from core.reference_validation import (
    REDACTED_SENSITIVE_REFERENCE,
    contains_chilean_rut_reference,
    contains_local_absolute_path_reference,
    contains_sensitive_reference,
)


DOCUMENT_INTAKE_SCHEMA_VERSION = 'company-document-intake-manifest.v1'
DOCUMENT_INTAKE_PACKAGE_SCHEMA_VERSION = 'company-document-intake-package.v1'
DOCUMENT_INTAKE_PACKAGE_MANIFEST = 'company-document-intake-package.json'
DOCUMENT_INTAKE_AUDIT_FILE = 'company-document-intake-audit.json'
BANK_SUPPORT_MANIFEST_DRAFT_FILE = 'company-bank-support-coverage-manifest.json'
ANNUAL_SOURCE_INTAKE_BRIDGE_FILE = 'annual-tax-source-intake-bridge.json'
ANNUAL_SOURCE_INTAKE_BRIDGE_SCHEMA_VERSION = 'annual-tax-source-intake-bridge.v1'
ALL_OPERATIONS = '*'

SOURCE_KINDS = frozenset(
    {
        'accounting_archive',
        'bank_portal_download',
        'external_folder',
        'gmail_thread',
        'manual_review_packet',
        'sii_download',
        'other_controlled_source',
    }
)

BANK_SUPPORT_CATEGORY_ALIASES = {
    'bank_contract_or_schedule': 'contract_or_schedule',
    'leasing_contract_or_schedule': 'contract_or_schedule',
    'bank_payment_history': 'payment_history',
    'leasing_payment_history': 'payment_history',
    'bank_invoice_or_tax_document_bundle': 'invoice_or_tax_document_bundle',
    'leasing_invoice_or_tax_document_bundle': 'invoice_or_tax_document_bundle',
    'bank_debt_status': 'debt_status',
    'leasing_debt_status': 'debt_status',
    'bank_insurance_or_fee_support': 'insurance_or_fee_support',
    'leasing_insurance_or_fee_support': 'insurance_or_fee_support',
    'bank_confirmation': 'bank_confirmation',
    'leasing_confirmation': 'bank_confirmation',
}

MONTHLY_ANNUAL_SOURCE_CATEGORIES = (
    'rcv_structured_input',
    'f29_support_input',
    'purchase_sales_books_support',
    'payroll_support',
)
ANNUAL_SOURCE_CATEGORIES = (
    'annual_ledger_input',
    'ownership_source_input',
    'ownership_source_candidate',
    'annual_balance_expected_output',
    'annual_tax_register_expected_output',
    'real_estate_support',
    'ddjj_expected_output',
    'f22_expected_output',
    'tax_certificate_support',
    'bank_reconciliation_candidate',
)

COMPANY_DOCUMENT_INTAKE_BOUNDARY = {
    'purpose': 'ingreso_redactado_de_respaldo_documental_contable_renta',
    'reads_real_documents': False,
    'stores_real_attachments': False,
    'uses_email_connector': False,
    'uses_external_integrations': False,
    'opens_bank_gate': False,
    'opens_sii_gate': False,
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
        or contains_chilean_rut_reference(normalized)
        or contains_local_absolute_path_reference(normalized)
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
    return any(contains_chilean_rut_reference(item) for item in _string_values(value))


def _has_absolute_path(value: Any) -> bool:
    return any(contains_local_absolute_path_reference(item) for item in _string_values(value))


def _issue(code: str, message: str, *, severity: str = 'blocking', count: int = 1) -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)


def _read_canonical_json(path: Path) -> Any:
    try:
        raw_content = path.read_text(encoding='utf-8')
        payload = json.loads(raw_content)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f'No se pudo leer JSON canonico en {path.name}: {error}') from error
    if raw_content != _canonical_json(payload):
        raise ValueError(f'JSON no canonico en {path.name}.')
    return payload


def _prepare_clean_output_dir(output_dir: Any) -> Path:
    target_dir = Path(output_dir)
    if target_dir.exists() and not target_dir.is_dir():
        raise ValueError('El destino del paquete de intake documental debe ser un directorio.')
    if target_dir.exists() and any(target_dir.iterdir()):
        raise ValueError('El directorio destino del paquete de intake documental debe estar vacio.')
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def _expected_package_files() -> set[str]:
    return {
        DOCUMENT_INTAKE_PACKAGE_MANIFEST,
        DOCUMENT_INTAKE_AUDIT_FILE,
        BANK_SUPPORT_MANIFEST_DRAFT_FILE,
        ANNUAL_SOURCE_INTAKE_BRIDGE_FILE,
    }


def _classification(*, documents_total: int, blocking_issues: list[dict[str, Any]]) -> str:
    if documents_total <= 0:
        return 'sin_datos'
    if blocking_issues:
        return 'parcial'
    return 'preparado'


def _support_category_for(category: str) -> str:
    if category in KNOWN_SUPPORT_CATEGORIES:
        return category
    return BANK_SUPPORT_CATEGORY_ALIASES.get(category, '')


def _annual_category_for(category: str) -> str:
    if category in CATEGORY_META:
        return category
    return ''


def _parse_months(values: Any) -> tuple[list[int], int]:
    months = set()
    invalid = 0
    for value in _as_list(values):
        try:
            month = int(value)
        except (TypeError, ValueError):
            invalid += 1
            continue
        if month not in MONTHS:
            invalid += 1
            continue
        months.add(month)
    return sorted(months), invalid


def _parse_ddjj_forms(values: Any) -> tuple[list[str], int]:
    forms = set()
    invalid = 0
    for value in _as_list(values):
        normalized = _normalize_ref(value)
        if not re.fullmatch(r'\d{4}', normalized):
            invalid += 1
            continue
        forms.add(normalized)
    return sorted(forms), invalid


def _safe_ref_list(values: Any) -> list[str]:
    return [_safe_ref(item) for item in _as_list(values) if _normalize_ref(item)]


def _source_batches(payload: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    batches = {}
    source_batches_raw = _as_list(payload.get('source_batches'))
    if not source_batches_raw:
        issues.append(
            _issue(
                'company_document_intake.source_batches_missing',
                'Falta declarar el origen redactado de los documentos revisados.',
            )
        )
        return batches

    for item in source_batches_raw:
        if not isinstance(item, dict):
            issues.append(
                _issue(
                    'company_document_intake.invalid_source_batch',
                    'Cada source_batch debe ser un objeto JSON.',
                )
            )
            continue
        batch_ref = _normalize_ref(item.get('batch_ref'))
        if not batch_ref:
            issues.append(
                _issue(
                    'company_document_intake.source_batch_ref_missing',
                    'Cada source_batch debe declarar batch_ref no sensible.',
                )
            )
            continue
        source_kind = _normalize_ref(item.get('source_kind'))
        if source_kind not in SOURCE_KINDS:
            issues.append(
                _issue(
                    'company_document_intake.invalid_source_kind',
                    'Hay source_batch con source_kind no reconocido.',
                )
            )
        batches[batch_ref] = {
            'batch_ref': _safe_ref(batch_ref),
            'raw_batch_ref': batch_ref,
            'source_kind': source_kind,
            'source_ref': _safe_ref(item.get('source_ref')),
            'declared_complete': bool(item.get('declared_complete')),
            'statement_strength': _normalize_ref(item.get('statement_strength')),
        }
    return batches


def _required_bank_operations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    operations = []
    for item in _as_list(payload.get('required_bank_operations')):
        if not isinstance(item, dict):
            continue
        operation_ref = _normalize_ref(item.get('operation_ref'))
        if not operation_ref:
            continue
        operation = {
            'operation_ref': _safe_ref(operation_ref),
            'label_ref': _safe_ref(item.get('label_ref')),
        }
        required_categories = [
            _normalize_ref(category)
            for category in _as_list(item.get('required_categories'))
            if _normalize_ref(category)
        ]
        if required_categories:
            operation['required_categories'] = sorted(set(required_categories))
        operations.append(operation)
    return operations


def _document_entry(
    *,
    item: dict[str, Any],
    batches: dict[str, dict[str, Any]],
    fiscal_year: int | None,
    tax_year: int | None,
    issues: list[dict[str, Any]],
) -> dict[str, Any] | None:
    document_ref = _normalize_ref(item.get('document_ref'))
    if not document_ref:
        issues.append(
            _issue(
                'company_document_intake.document_ref_missing',
                'Cada documento debe declarar document_ref no sensible.',
            )
        )
        return None

    category = _normalize_ref(item.get('category'))
    support_category = _support_category_for(category)
    annual_category = _annual_category_for(category)
    if not support_category and not annual_category:
        issues.append(
            _issue(
                'company_document_intake.invalid_document_category',
                'Hay documentos con categoria no reconocida para contabilidad/renta.',
            )
        )

    batch_ref = _normalize_ref(item.get('batch_ref'))
    batch = batches.get(batch_ref)
    if not batch_ref:
        issues.append(
            _issue(
                'company_document_intake.document_batch_missing',
                'Cada documento debe apuntar a un source_batch redactado.',
            )
        )
    elif batch is None:
        issues.append(
            _issue(
                'company_document_intake.document_unknown_batch',
                'Hay documentos asociados a source_batch no declarado.',
            )
        )

    months, invalid_months = _parse_months(item.get('months'))
    if invalid_months:
        issues.append(
            _issue(
                'company_document_intake.invalid_month',
                'Hay documentos con meses fuera del rango 1..12.',
                count=invalid_months,
            )
        )

    ddjj_forms, invalid_ddjj_forms = _parse_ddjj_forms(item.get('ddjj_forms'))
    if invalid_ddjj_forms:
        issues.append(
            _issue(
                'company_document_intake.invalid_ddjj_form',
                'Hay documentos con formularios DDJJ no canonicos de cuatro digitos.',
                count=invalid_ddjj_forms,
            )
        )

    doc_fiscal_year = item.get('fiscal_year')
    if doc_fiscal_year not in (None, '') and fiscal_year is not None:
        try:
            normalized_doc_fiscal_year = int(doc_fiscal_year)
        except (TypeError, ValueError):
            normalized_doc_fiscal_year = None
            issues.append(
                _issue(
                    'company_document_intake.invalid_document_fiscal_year',
                    'Hay documentos con fiscal_year no numerico.',
                )
            )
        if normalized_doc_fiscal_year is not None and normalized_doc_fiscal_year != fiscal_year:
            issues.append(
                _issue(
                    'company_document_intake.document_fiscal_year_mismatch',
                    'Hay documentos que declaran un ano comercial distinto al manifiesto.',
                )
            )
    doc_tax_year = item.get('tax_year')
    if doc_tax_year not in (None, '') and tax_year is not None:
        try:
            normalized_doc_tax_year = int(doc_tax_year)
        except (TypeError, ValueError):
            normalized_doc_tax_year = None
            issues.append(
                _issue(
                    'company_document_intake.invalid_document_tax_year',
                    'Hay documentos con tax_year no numerico.',
                )
            )
        if normalized_doc_tax_year is not None and normalized_doc_tax_year != tax_year:
            issues.append(
                _issue(
                    'company_document_intake.document_tax_year_mismatch',
                    'Hay documentos que declaran un ano tributario distinto al manifiesto.',
                )
            )

    return {
        'raw_document_ref': document_ref,
        'document_ref': _safe_ref(document_ref),
        'batch_ref': _safe_ref(batch_ref),
        'source_ref': batch['source_ref'] if batch else _safe_ref(item.get('source_ref')),
        'category': category,
        'support_category': support_category,
        'annual_category': annual_category,
        'role': CATEGORY_META[annual_category]['role'] if annual_category else 'support',
        'months': months,
        'ddjj_forms': ddjj_forms,
        'operation_refs': _safe_ref_list(item.get('operation_refs')),
        'artifact_key': _safe_ref(item.get('artifact_key')),
        'output_status': _safe_ref(item.get('output_status')),
        'statement_strength': _normalize_ref(item.get('statement_strength')),
        'size_bytes': item.get('size_bytes') if isinstance(item.get('size_bytes'), int) else None,
        'sha256_ref': _safe_ref(item.get('sha256_ref')),
    }


def _documents(
    *,
    payload: dict[str, Any],
    batches: dict[str, dict[str, Any]],
    fiscal_year: int | None,
    tax_year: int | None,
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    documents_raw = _as_list(payload.get('documents'))
    if not documents_raw:
        issues.append(
            _issue(
                'company_document_intake.documents_missing',
                'Falta listar documentos o adjuntos revisados en forma redactada.',
            )
        )
        return []

    documents = []
    document_ref_counts: Counter[str] = Counter()
    for item in documents_raw:
        if not isinstance(item, dict):
            issues.append(
                _issue(
                    'company_document_intake.invalid_document',
                    'Cada documento debe ser un objeto JSON.',
                )
            )
            continue
        document = _document_entry(
            item=item,
            batches=batches,
            fiscal_year=fiscal_year,
            tax_year=tax_year,
            issues=issues,
        )
        if document is None:
            continue
        document_ref_counts[document['raw_document_ref']] += 1
        documents.append(document)

    duplicated_refs = [ref for ref, count in document_ref_counts.items() if count > 1]
    if duplicated_refs:
        issues.append(
            _issue(
                'company_document_intake.duplicate_document_ref',
                'Hay document_ref duplicados en el manifiesto de intake documental.',
                count=len(duplicated_refs),
            )
        )
    return documents


def _bank_support_manifest_draft(
    *,
    payload: dict[str, Any],
    documents: list[dict[str, Any]],
    fiscal_year: int | None,
    tax_year: int | None,
) -> dict[str, Any]:
    attachments = []
    confirmations = []
    for document in documents:
        support_category = document.get('support_category') or ''
        if not support_category:
            continue
        if support_category == 'bank_confirmation':
            confirmations.append(
                {
                    'confirmation_ref': document['document_ref'],
                    'source_ref': document['source_ref'],
                    'statement_strength': document.get('statement_strength') or 'expected_complete',
                }
            )
            continue
        attachment = {
            'attachment_ref': document['document_ref'],
            'operation_refs': document.get('operation_refs') or [],
            'category': support_category,
            'source_ref': document['source_ref'],
        }
        if document.get('size_bytes') is not None:
            attachment['size_bytes'] = document['size_bytes']
        attachments.append(attachment)

    return {
        'schema_version': BANK_SUPPORT_MANIFEST_SCHEMA_VERSION,
        'company_ref': _safe_ref(payload.get('company_ref')),
        'fiscal_year': fiscal_year,
        'tax_year': tax_year,
        'required_operations': _required_bank_operations(payload),
        'attachments': attachments,
        'confirmations': confirmations,
    }


def _months_for(documents: list[dict[str, Any]], category: str) -> list[int]:
    months = set()
    for document in documents:
        if document.get('annual_category') == category:
            months.update(document.get('months') or [])
    return sorted(months)


def _annual_source_bridge(
    *,
    company_ref: str,
    fiscal_year: int | None,
    tax_year: int | None,
    documents: list[dict[str, Any]],
    intake_blocking_issues: list[dict[str, Any]],
) -> dict[str, Any]:
    annual_documents = [document for document in documents if document.get('annual_category')]
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for document in annual_documents:
        by_category[document['annual_category']].append(document)

    ddjj_forms = sorted(
        {
            form
            for document in by_category.get('ddjj_expected_output', [])
            for form in document.get('ddjj_forms') or []
        }
    )
    annual_tax_register_keys = sorted(
        {
            document.get('artifact_key') or ''
            for document in by_category.get('annual_tax_register_expected_output', [])
            if (document.get('artifact_key') or '') in EXPECTED_ANNUAL_TAX_REGISTER_KEYS
        }
    )
    checks = [
        {
            'key': 'rcv_12_months',
            'status': 'ready' if _months_for(annual_documents, 'rcv_structured_input') == list(MONTHS) else 'partial',
            'months': _months_for(annual_documents, 'rcv_structured_input'),
        },
        {
            'key': 'f29_periods',
            'status': 'ready' if _months_for(annual_documents, 'f29_support_input') == list(MONTHS) else 'partial',
            'months': _months_for(annual_documents, 'f29_support_input'),
        },
        {
            'key': 'annual_ledger_inputs',
            'status': 'ready' if by_category.get('annual_ledger_input') else 'missing',
            'files': len(by_category.get('annual_ledger_input', [])),
        },
        {
            'key': 'ownership_source',
            'status': 'ready' if by_category.get('ownership_source_input') else 'missing',
            'files': len(by_category.get('ownership_source_input', [])),
        },
        {
            'key': 'annual_balance_expected_output',
            'status': 'ready' if by_category.get('annual_balance_expected_output') else 'missing',
            'files': len(by_category.get('annual_balance_expected_output', [])),
        },
        {
            'key': 'annual_tax_register_expected_outputs',
            'status': 'ready'
            if not [key for key in EXPECTED_ANNUAL_TAX_REGISTER_KEYS if key not in annual_tax_register_keys]
            else 'partial',
            'artifact_keys': annual_tax_register_keys,
            'missing_artifact_keys': [
                key for key in EXPECTED_ANNUAL_TAX_REGISTER_KEYS if key not in annual_tax_register_keys
            ],
        },
        {
            'key': 'ddjj_expected_outputs',
            'status': 'ready' if not [form for form in EXPECTED_DDJJ_FORMS if form not in ddjj_forms] else 'partial',
            'forms': ddjj_forms,
            'missing_forms': [form for form in EXPECTED_DDJJ_FORMS if form not in ddjj_forms],
        },
        {
            'key': 'f22_expected_output',
            'status': 'ready' if by_category.get('f22_expected_output') else 'missing',
            'files': len(by_category.get('f22_expected_output', [])),
        },
        {
            'key': 'bank_reconciliation',
            'status': 'candidate_found' if by_category.get('bank_reconciliation_candidate') else 'not_ready',
            'files': len(by_category.get('bank_reconciliation_candidate', [])),
        },
    ]
    categories_present = sorted(by_category)
    document_refs = [
        {
            'document_ref': document['document_ref'],
            'category': document['annual_category'],
            'role': document['role'],
            'months': document.get('months') or [],
            'ddjj_forms': document.get('ddjj_forms') or [],
            'artifact_key': document.get('artifact_key') or '',
        }
        for document in annual_documents
    ]
    ready_for_source_manifest_reconciliation = bool(annual_documents) and not intake_blocking_issues
    return {
        'schema_version': ANNUAL_SOURCE_INTAKE_BRIDGE_SCHEMA_VERSION,
        'target_source_manifest_schema_version': ANNUAL_TAX_SOURCE_MANIFEST_SCHEMA_VERSION,
        'company_ref': _safe_ref(company_ref),
        'commercial_year': fiscal_year,
        'tax_year': tax_year,
        'ready_for_source_manifest_reconciliation': ready_for_source_manifest_reconciliation,
        'can_replace_read_only_source_scan': False,
        'requires_read_only_source_root_scan_for_file_hashes': True,
        'expected_outputs_used_as_inputs': False,
        'categories_present': categories_present,
        'category_counts': {category: len(by_category.get(category, [])) for category in sorted(CATEGORY_META)},
        'monthly_source_months': {
            category: _months_for(annual_documents, category)
            for category in MONTHLY_ANNUAL_SOURCE_CATEGORIES
        },
        'checks': checks,
        'document_refs': document_refs,
    }


def audit_company_document_intake(*, payload: dict[str, Any]) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if contains_sensitive_reference(payload, include_sensitive_keys=True):
        issues.append(
            _issue(
                'company_document_intake.sensitive_reference',
                'El manifiesto contiene URLs, correos, claves, tokens, credenciales o campos sensibles.',
            )
        )
    if _has_rut(payload):
        issues.append(
            _issue(
                'company_document_intake.rut_exposed',
                'El manifiesto no debe contener RUT completos; usar company_ref y document_ref redactados.',
            )
        )
    if _has_absolute_path(payload):
        issues.append(
            _issue(
                'company_document_intake.absolute_path_exposed',
                'El manifiesto no debe contener rutas absolutas; usar refs opacas o hashes.',
            )
        )

    schema_version = payload.get('schema_version')
    if schema_version in {'', None}:
        issues.append(
            _issue(
                'company_document_intake.schema_version_missing',
                'Falta schema_version del manifiesto de intake documental.',
            )
        )
    elif schema_version != DOCUMENT_INTAKE_SCHEMA_VERSION:
        issues.append(
            _issue(
                'company_document_intake.unsupported_schema_version',
                'Version de manifiesto de intake documental no soportada.',
            )
        )

    company_ref = _normalize_ref(payload.get('company_ref'))
    if not company_ref:
        issues.append(
            _issue(
                'company_document_intake.company_ref_missing',
                'El manifiesto debe declarar company_ref no sensible.',
            )
        )

    try:
        fiscal_year = int(payload.get('fiscal_year')) if payload.get('fiscal_year') not in (None, '') else None
    except (TypeError, ValueError):
        fiscal_year = None
        issues.append(
            _issue(
                'company_document_intake.invalid_fiscal_year',
                'fiscal_year debe ser numerico.',
            )
        )
    if fiscal_year is None:
        issues.append(
            _issue(
                'company_document_intake.fiscal_year_missing',
                'El manifiesto debe declarar fiscal_year.',
            )
        )
    try:
        tax_year = int(payload.get('tax_year')) if payload.get('tax_year') not in (None, '') else None
    except (TypeError, ValueError):
        tax_year = None
        issues.append(
            _issue(
                'company_document_intake.invalid_tax_year',
                'tax_year debe ser numerico cuando se declara.',
            )
        )
    if tax_year is None and fiscal_year is not None:
        tax_year = fiscal_year + 1

    batches = _source_batches(payload, issues)
    documents = _documents(
        payload=payload,
        batches=batches,
        fiscal_year=fiscal_year,
        tax_year=tax_year,
        issues=issues,
    )

    bank_manifest = _bank_support_manifest_draft(
        payload=payload,
        documents=documents,
        fiscal_year=fiscal_year,
        tax_year=tax_year,
    )
    bank_support = audit_company_bank_support_coverage(payload=bank_manifest)
    bank_support_required = bool(bank_manifest['required_operations'] or bank_manifest['attachments'] or bank_manifest['confirmations'])

    intake_blocking_issues = [issue for issue in issues if issue['severity'] == 'blocking']
    annual_bridge = _annual_source_bridge(
        company_ref=company_ref,
        fiscal_year=fiscal_year,
        tax_year=tax_year,
        documents=documents,
        intake_blocking_issues=intake_blocking_issues,
    )
    annual_source_present = bool(annual_bridge['document_refs'])
    if not bank_support_required and not annual_source_present:
        warnings.append(
            _issue(
                'company_document_intake.no_target_bridge',
                'El manifiesto no contiene documentos bancarios/leasing ni fuentes anuales reconocidas.',
                severity='warning',
            )
        )

    ready_for_document_intake_review = bool(documents) and not intake_blocking_issues
    ready_for_bank_support_manifest = bank_support_required and bank_support['ready_for_accounting_document_review']
    ready_for_formal_bank_support_manifest = (
        bank_support_required and bank_support['ready_for_formal_bank_support_review']
    )
    ready_for_productive_document_review = ready_for_document_intake_review and (
        (not bank_support_required or ready_for_formal_bank_support_manifest)
        and (bank_support_required or annual_source_present)
    )

    safe_documents = [
        {
            key: value
            for key, value in document.items()
            if key
            not in {
                'raw_document_ref',
            }
        }
        for document in documents
    ]
    summary = {
        'company_ref': _safe_ref(company_ref),
        'fiscal_year': fiscal_year,
        'tax_year': tax_year,
        'source_batches_total': len(batches),
        'documents_total': len(documents),
        'bank_support_required': bank_support_required,
        'annual_source_documents_total': len(annual_bridge['document_refs']),
        'ready_for_document_intake_review': ready_for_document_intake_review,
        'ready_for_bank_support_manifest': ready_for_bank_support_manifest,
        'ready_for_formal_bank_support_manifest': ready_for_formal_bank_support_manifest,
        'ready_for_source_manifest_reconciliation': annual_bridge['ready_for_source_manifest_reconciliation'],
        'ready_for_productive_document_review': ready_for_productive_document_review,
    }
    evidence = {
        'document_intake_hash': payload_hash(
            {
                'schema_version': DOCUMENT_INTAKE_SCHEMA_VERSION,
                'summary': summary,
                'documents': safe_documents,
                'bank_support_manifest_draft': bank_manifest,
                'annual_source_bridge': {
                    'categories_present': annual_bridge['categories_present'],
                    'document_refs': annual_bridge['document_refs'],
                },
            }
        ),
        'bank_support_manifest_hash': payload_hash(bank_manifest),
        'annual_source_bridge_hash': payload_hash(annual_bridge),
    }

    return {
        'schema_version': DOCUMENT_INTAKE_SCHEMA_VERSION,
        'classification': _classification(documents_total=len(documents), blocking_issues=intake_blocking_issues),
        'ready_for_document_intake_review': ready_for_document_intake_review,
        'ready_for_bank_support_manifest': ready_for_bank_support_manifest,
        'ready_for_formal_bank_support_manifest': ready_for_formal_bank_support_manifest,
        'ready_for_source_manifest_reconciliation': annual_bridge['ready_for_source_manifest_reconciliation'],
        'ready_for_productive_document_review': ready_for_productive_document_review,
        'summary': summary,
        'source_batches': [
            {
                key: value
                for key, value in batch.items()
                if key != 'raw_batch_ref'
            }
            for batch in batches.values()
        ],
        'documents': safe_documents,
        'bank_support_manifest_draft': bank_manifest,
        'bank_support_coverage': bank_support,
        'annual_source_bridge': annual_bridge,
        'evidence': evidence,
        'issue_counts': {
            'blocking': len(intake_blocking_issues),
            'bank_support_blocking': bank_support['issue_counts']['blocking'],
            'warning': len(warnings) + bank_support['issue_counts']['warning'],
        },
        'issues': issues,
        'warnings': warnings + [
            {
                **warning,
                'code': f'company_document_intake.{warning["code"]}',
            }
            for warning in bank_support['warnings']
        ],
        'boundary': dict(COMPANY_DOCUMENT_INTAKE_BOUNDARY),
        'manifest_policy': {
            'raw_email_bodies_allowed': False,
            'real_attachments_allowed_in_git': False,
            'full_rut_allowed': False,
            'absolute_paths_allowed': False,
            'urls_or_email_addresses_allowed': False,
            'password_or_credential_allowed': False,
            'document_refs_must_be_opaque': True,
        },
    }


def _package_manifest_for(audit_result: dict[str, Any]) -> dict[str, Any]:
    ready_for_formal_bank_support_manifest = audit_result.get(
        'ready_for_formal_bank_support_manifest',
        bool(
            (audit_result.get('bank_support_coverage') or {}).get(
                'ready_for_formal_bank_support_review'
            )
        ),
    )
    files = [
        {
            'file': DOCUMENT_INTAKE_AUDIT_FILE,
            'kind': 'company_document_intake_audit',
            'schema_version': audit_result['schema_version'],
            'payload_hash': payload_hash(audit_result),
        },
        {
            'file': BANK_SUPPORT_MANIFEST_DRAFT_FILE,
            'kind': 'company_bank_support_coverage_manifest_draft',
            'schema_version': audit_result['bank_support_manifest_draft']['schema_version'],
            'payload_hash': audit_result['evidence']['bank_support_manifest_hash'],
        },
        {
            'file': ANNUAL_SOURCE_INTAKE_BRIDGE_FILE,
            'kind': 'annual_tax_source_intake_bridge',
            'schema_version': audit_result['annual_source_bridge']['schema_version'],
            'payload_hash': audit_result['evidence']['annual_source_bridge_hash'],
        },
    ]
    manifest = {
        'schema_version': DOCUMENT_INTAKE_PACKAGE_SCHEMA_VERSION,
        'source_schema_version': DOCUMENT_INTAKE_SCHEMA_VERSION,
        'classification': audit_result['classification'],
        'ready_for_document_intake_review': audit_result['ready_for_document_intake_review'],
        'ready_for_bank_support_manifest': audit_result['ready_for_bank_support_manifest'],
        'ready_for_formal_bank_support_manifest': ready_for_formal_bank_support_manifest,
        'ready_for_source_manifest_reconciliation': audit_result['ready_for_source_manifest_reconciliation'],
        'ready_for_productive_document_review': audit_result['ready_for_productive_document_review'],
        'summary': audit_result['summary'],
        'evidence': audit_result['evidence'],
        'issue_counts': audit_result['issue_counts'],
        'files': files,
        'boundary': audit_result['boundary'],
        'manifest_policy': audit_result['manifest_policy'],
    }
    manifest['package_hash'] = payload_hash(
        {
            'schema_version': manifest['schema_version'],
            'source_schema_version': manifest['source_schema_version'],
            'classification': manifest['classification'],
            'summary': manifest['summary'],
            'evidence': manifest['evidence'],
            'issue_counts': manifest['issue_counts'],
            'files': manifest['files'],
            'boundary': manifest['boundary'],
            'manifest_policy': manifest['manifest_policy'],
        }
    )
    return manifest


def write_company_document_intake_package(
    *,
    payload: dict[str, Any],
    output_dir: Any,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('payload debe ser un objeto JSON.')

    audit_result = audit_company_document_intake(payload=payload)
    package_manifest = _package_manifest_for(audit_result)
    target_dir = _prepare_clean_output_dir(output_dir)
    file_payloads = {
        DOCUMENT_INTAKE_PACKAGE_MANIFEST: package_manifest,
        DOCUMENT_INTAKE_AUDIT_FILE: audit_result,
        BANK_SUPPORT_MANIFEST_DRAFT_FILE: audit_result['bank_support_manifest_draft'],
        ANNUAL_SOURCE_INTAKE_BRIDGE_FILE: audit_result['annual_source_bridge'],
    }
    for file_name, file_payload in file_payloads.items():
        (target_dir / file_name).write_text(_canonical_json(file_payload), encoding='utf-8')

    return {
        **package_manifest,
        'output_dir': str(target_dir),
        'package_manifest_file': str(target_dir / DOCUMENT_INTAKE_PACKAGE_MANIFEST),
        'audit_file': str(target_dir / DOCUMENT_INTAKE_AUDIT_FILE),
        'bank_support_manifest_file': str(target_dir / BANK_SUPPORT_MANIFEST_DRAFT_FILE),
        'annual_source_bridge_file': str(target_dir / ANNUAL_SOURCE_INTAKE_BRIDGE_FILE),
    }


def verify_company_document_intake_package(
    *,
    payload: dict[str, Any],
    package_dir: Any,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('payload debe ser un objeto JSON.')

    expected_audit = audit_company_document_intake(payload=payload)
    expected_manifest = _package_manifest_for(expected_audit)
    target_dir = Path(package_dir)
    if not target_dir.exists() or not target_dir.is_dir():
        raise ValueError('El directorio del paquete de intake documental no existe.')
    entries = list(target_dir.iterdir())
    if {entry.name for entry in entries if entry.is_file()} != _expected_package_files():
        raise ValueError('El paquete de intake documental contiene archivos no declarados.')
    if any(not entry.is_file() for entry in entries):
        raise ValueError('El paquete de intake documental contiene entradas no permitidas.')

    manifest = _read_canonical_json(target_dir / DOCUMENT_INTAKE_PACKAGE_MANIFEST)
    audit_payload = _read_canonical_json(target_dir / DOCUMENT_INTAKE_AUDIT_FILE)
    bank_manifest = _read_canonical_json(target_dir / BANK_SUPPORT_MANIFEST_DRAFT_FILE)
    annual_bridge = _read_canonical_json(target_dir / ANNUAL_SOURCE_INTAKE_BRIDGE_FILE)

    if manifest != expected_manifest:
        raise ValueError('El manifest del paquete de intake documental no coincide con el estado esperado.')
    if audit_payload != expected_audit:
        raise ValueError('La auditoria de intake documental no coincide con el estado esperado.')
    if bank_manifest != expected_audit['bank_support_manifest_draft']:
        raise ValueError('El manifiesto bancario/leasing derivado no coincide con el estado esperado.')
    if annual_bridge != expected_audit['annual_source_bridge']:
        raise ValueError('El puente anual derivado no coincide con el estado esperado.')
    if manifest.get('package_hash') != _package_manifest_for(audit_payload)['package_hash']:
        raise ValueError('El paquete de intake documental no coincide con su hash.')

    boundary = manifest.get('boundary') or {}
    if (
        boundary.get('reads_real_documents') is not False
        or boundary.get('stores_real_attachments') is not False
        or boundary.get('uses_email_connector') is not False
        or boundary.get('opens_bank_gate') is not False
        or boundary.get('opens_sii_gate') is not False
        or boundary.get('autonomous_accounting') is not False
        or boundary.get('final_tax_calculation') is not False
        or boundary.get('sii_submission') is not False
        or boundary.get('requires_responsible_review') is not True
    ):
        raise ValueError('El paquete de intake documental rompe el boundary de revision responsable.')

    return {
        'verified': True,
        'schema_version': manifest['schema_version'],
        'package_hash': manifest['package_hash'],
        'classification': manifest['classification'],
        'ready_for_document_intake_review': manifest['ready_for_document_intake_review'],
        'ready_for_bank_support_manifest': manifest['ready_for_bank_support_manifest'],
        'ready_for_formal_bank_support_manifest': manifest['ready_for_formal_bank_support_manifest'],
        'ready_for_source_manifest_reconciliation': manifest['ready_for_source_manifest_reconciliation'],
        'ready_for_productive_document_review': manifest['ready_for_productive_document_review'],
        'summary': manifest['summary'],
        'issue_counts': manifest['issue_counts'],
        'files': manifest['files'],
        'boundary': boundary,
        'package_manifest_file': str(target_dir / DOCUMENT_INTAKE_PACKAGE_MANIFEST),
        'audit_file': str(target_dir / DOCUMENT_INTAKE_AUDIT_FILE),
        'bank_support_manifest_file': str(target_dir / BANK_SUPPORT_MANIFEST_DRAFT_FILE),
        'annual_source_bridge_file': str(target_dir / ANNUAL_SOURCE_INTAKE_BRIDGE_FILE),
    }


def verify_company_document_intake_package_from_disk(*, package_dir: Any) -> dict[str, Any]:
    target_dir = Path(package_dir)
    if not target_dir.exists() or not target_dir.is_dir():
        raise ValueError('El directorio del paquete de intake documental no existe.')
    entries = list(target_dir.iterdir())
    if {entry.name for entry in entries if entry.is_file()} != _expected_package_files():
        raise ValueError('El paquete de intake documental contiene archivos no declarados.')
    if any(not entry.is_file() for entry in entries):
        raise ValueError('El paquete de intake documental contiene entradas no permitidas.')

    manifest = _read_canonical_json(target_dir / DOCUMENT_INTAKE_PACKAGE_MANIFEST)
    audit_payload = _read_canonical_json(target_dir / DOCUMENT_INTAKE_AUDIT_FILE)
    bank_manifest = _read_canonical_json(target_dir / BANK_SUPPORT_MANIFEST_DRAFT_FILE)
    annual_bridge = _read_canonical_json(target_dir / ANNUAL_SOURCE_INTAKE_BRIDGE_FILE)

    if manifest.get('schema_version') != DOCUMENT_INTAKE_PACKAGE_SCHEMA_VERSION:
        raise ValueError('El manifest del paquete de intake documental tiene version no soportada.')
    if manifest.get('source_schema_version') != DOCUMENT_INTAKE_SCHEMA_VERSION:
        raise ValueError('El manifest del paquete de intake documental no apunta al schema de intake soportado.')
    if audit_payload.get('schema_version') != DOCUMENT_INTAKE_SCHEMA_VERSION:
        raise ValueError('La auditoria de intake documental tiene version no soportada.')

    expected_manifest = _package_manifest_for(audit_payload)
    if manifest != expected_manifest:
        raise ValueError('El manifest del paquete de intake documental no coincide con la auditoria incluida.')
    if bank_manifest != audit_payload.get('bank_support_manifest_draft'):
        raise ValueError('El manifiesto bancario/leasing derivado no coincide con la auditoria incluida.')
    if annual_bridge != audit_payload.get('annual_source_bridge'):
        raise ValueError('El puente anual derivado no coincide con la auditoria incluida.')
    if manifest.get('package_hash') != expected_manifest['package_hash']:
        raise ValueError('El paquete de intake documental no coincide con su hash.')

    payload_by_file = {
        DOCUMENT_INTAKE_AUDIT_FILE: audit_payload,
        BANK_SUPPORT_MANIFEST_DRAFT_FILE: bank_manifest,
        ANNUAL_SOURCE_INTAKE_BRIDGE_FILE: annual_bridge,
    }
    for file_spec in manifest.get('files') or []:
        file_name = file_spec.get('file')
        if file_name not in payload_by_file:
            raise ValueError('El manifest del paquete de intake documental declara un archivo no permitido.')
        if file_spec.get('payload_hash') != payload_hash(payload_by_file[file_name]):
            raise ValueError(f'Hash desalineado en {file_name}.')

    boundary = manifest.get('boundary') or {}
    if (
        boundary.get('reads_real_documents') is not False
        or boundary.get('stores_real_attachments') is not False
        or boundary.get('uses_email_connector') is not False
        or boundary.get('opens_bank_gate') is not False
        or boundary.get('opens_sii_gate') is not False
        or boundary.get('autonomous_accounting') is not False
        or boundary.get('final_tax_calculation') is not False
        or boundary.get('sii_submission') is not False
        or boundary.get('requires_responsible_review') is not True
    ):
        raise ValueError('El paquete de intake documental rompe el boundary de revision responsable.')

    return {
        'verified': True,
        'schema_version': manifest['schema_version'],
        'package_hash': manifest['package_hash'],
        'classification': manifest['classification'],
        'ready_for_document_intake_review': manifest['ready_for_document_intake_review'],
        'ready_for_bank_support_manifest': manifest['ready_for_bank_support_manifest'],
        'ready_for_formal_bank_support_manifest': manifest['ready_for_formal_bank_support_manifest'],
        'ready_for_source_manifest_reconciliation': manifest['ready_for_source_manifest_reconciliation'],
        'ready_for_productive_document_review': manifest['ready_for_productive_document_review'],
        'summary': manifest['summary'],
        'issue_counts': manifest['issue_counts'],
        'files': manifest['files'],
        'boundary': boundary,
        'bank_support_manifest': bank_manifest,
        'annual_source_bridge': annual_bridge,
        'package_manifest_file': str(target_dir / DOCUMENT_INTAKE_PACKAGE_MANIFEST),
        'audit_file': str(target_dir / DOCUMENT_INTAKE_AUDIT_FILE),
        'bank_support_manifest_file': str(target_dir / BANK_SUPPORT_MANIFEST_DRAFT_FILE),
        'annual_source_bridge_file': str(target_dir / ANNUAL_SOURCE_INTAKE_BRIDGE_FILE),
    }
