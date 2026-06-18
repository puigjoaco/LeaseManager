from __future__ import annotations

import hashlib
import json
from typing import Any

from core.company_accounting_progress import collect_company_accounting_progress
from core.company_bank_support_coverage import audit_company_bank_support_coverage


COMPANY_ACCOUNTING_REVIEW_PACKAGE_VERSION = 'company-accounting-review-package.v1'
COMPANY_ACCOUNTING_REVIEW_PACKAGE_BOUNDARY = {
    'purpose': 'preparar_revision_contable_renta_por_empresa_y_ano',
    'reads_real_documents': False,
    'stores_real_attachments': False,
    'uses_external_integrations': False,
    'opens_bank_gate': False,
    'opens_sii_gate': False,
    'autonomous_accounting': False,
    'final_tax_calculation': False,
    'sii_submission': False,
    'requires_responsible_review': True,
    'requires_expert_or_official_validation': True,
}


def canonical_company_review_ref(empresa_id: int) -> str:
    return f'company-{int(empresa_id)}'


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _issue(code: str, message: str, *, severity: str = 'blocking', count: int = 1) -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _classification(*, ready: bool, bank_support_ready: bool, has_accounting_data: bool) -> str:
    if ready:
        return 'preparado'
    if not has_accounting_data and not bank_support_ready:
        return 'sin_datos'
    return 'parcial'


def build_company_accounting_review_package(
    *,
    empresa_id: int,
    fiscal_year: int,
    bank_support_payload: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(bank_support_payload, dict):
        raise ValueError('bank_support_payload debe ser un objeto JSON.')

    accounting_progress = collect_company_accounting_progress(
        empresa_id=empresa_id,
        fiscal_year=fiscal_year,
    )
    bank_support = audit_company_bank_support_coverage(payload=bank_support_payload)
    expected_tax_year = fiscal_year + 1
    expected_company_ref = canonical_company_review_ref(empresa_id)
    bank_support_company_ref = bank_support.get('company_ref') or ''

    issues = []
    if not accounting_progress['ready_for_company_accounting_review']:
        issues.append(
            _issue(
                'company_accounting_review.accounting_progress_incomplete',
                'La empresa/ano no tiene completa la capa contable-renta local hasta dossier/export revisable.',
                count=accounting_progress['issue_counts']['blocking'],
            )
        )
    if not bank_support['ready_for_accounting_document_review']:
        issues.append(
            _issue(
                'company_accounting_review.bank_support_incomplete',
                'La empresa/ano no tiene cobertura bancaria/leasing redactada lista para revision contable.',
                count=bank_support['issue_counts']['blocking'],
            )
        )
    if bank_support.get('fiscal_year') != fiscal_year:
        issues.append(
            _issue(
                'company_accounting_review.bank_support_fiscal_year_mismatch',
                'El manifiesto bancario/leasing no corresponde al ano comercial auditado.',
            )
        )
    if bank_support.get('tax_year') not in (None, expected_tax_year):
        issues.append(
            _issue(
                'company_accounting_review.bank_support_tax_year_mismatch',
                'El manifiesto bancario/leasing no corresponde al ano tributario esperado.',
            )
        )
    if not bank_support_company_ref:
        issues.append(
            _issue(
                'company_accounting_review.bank_support_company_ref_missing',
                'El manifiesto bancario/leasing debe declarar company_ref redactado y verificable.',
            )
        )
    elif bank_support_company_ref != expected_company_ref:
        issues.append(
            _issue(
                'company_accounting_review.bank_support_company_ref_mismatch',
                'El manifiesto bancario/leasing no corresponde a la empresa auditada.',
            )
        )

    blocking_issues = [issue for issue in issues if issue['severity'] == 'blocking']
    has_accounting_data = accounting_progress['classification'] != 'sin_datos'
    ready = (
        accounting_progress['ready_for_company_accounting_review']
        and bank_support['ready_for_accounting_document_review']
        and not blocking_issues
    )
    warnings = [
        {
            **warning,
            'code': f'company_accounting_review.{warning["code"]}',
        }
        for warning in bank_support['warnings']
    ]
    summary = {
        'empresa_id': accounting_progress['empresa']['id'],
        'fiscal_year': fiscal_year,
        'tax_year': expected_tax_year,
        'expected_company_ref': expected_company_ref,
        'bank_support_company_ref': bank_support_company_ref,
        'accounting_progress_classification': accounting_progress['classification'],
        'accounting_progress_percent': accounting_progress['progress_percent'],
        'bank_support_classification': bank_support['classification'],
        'bank_support_coverage_percent': bank_support['coverage_percent'],
        'ready_for_company_accounting_review': accounting_progress['ready_for_company_accounting_review'],
        'ready_for_accounting_document_review': bank_support['ready_for_accounting_document_review'],
        'ready_for_productive_accounting_review': ready,
        'blocking_issues_total': len(blocking_issues),
        'warnings_total': len(warnings),
    }
    evidence = {
        'accounting_progress_hash': _canonical_hash(accounting_progress),
        'bank_support_hash': _canonical_hash(bank_support),
    }
    package = {
        'schema_version': COMPANY_ACCOUNTING_REVIEW_PACKAGE_VERSION,
        'classification': _classification(
            ready=ready,
            bank_support_ready=bank_support['ready_for_accounting_document_review'],
            has_accounting_data=has_accounting_data,
        ),
        'ready_for_productive_accounting_review': ready,
        'summary': summary,
        'empresa': accounting_progress['empresa'],
        'fiscal_year': fiscal_year,
        'tax_year': expected_tax_year,
        'accounting_progress': accounting_progress,
        'bank_support_coverage': bank_support,
        'evidence': evidence,
        'issues': issues,
        'warnings': warnings,
        'boundary': dict(COMPANY_ACCOUNTING_REVIEW_PACKAGE_BOUNDARY),
    }
    package['package_hash'] = _canonical_hash({
        'schema_version': package['schema_version'],
        'summary': package['summary'],
        'evidence': package['evidence'],
        'issues': package['issues'],
        'warnings': package['warnings'],
        'boundary': package['boundary'],
    })
    return package
