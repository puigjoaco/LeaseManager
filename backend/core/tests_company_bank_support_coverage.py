import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.company_bank_support_coverage import audit_company_bank_support_coverage


def _complete_manifest(*, statement_strength='expected_complete'):
    operations = [
        {'operation_ref': f'leasing-op-{index:02d}', 'label_ref': f'bank-leasing-{index:02d}'}
        for index in range(1, 6)
    ]
    attachments = []
    for operation in operations:
        ref = operation['operation_ref']
        attachments.append(
            {
                'attachment_ref': f'{ref}-contract-schedule',
                'operation_refs': [ref],
                'category': 'contract_or_schedule',
                'source_ref': 'gmail-thread-redacted',
                'size_bytes': 1234,
            }
        )
        attachments.append(
            {
                'attachment_ref': f'{ref}-payment-history',
                'operation_refs': [ref],
                'category': 'payment_history',
                'source_ref': 'gmail-thread-redacted',
                'size_bytes': 2345,
            }
        )
    attachments.append(
        {
            'attachment_ref': 'invoice-bundle-redacted',
            'operation_refs': ['*'],
            'category': 'invoice_or_tax_document_bundle',
            'source_ref': 'gmail-thread-redacted',
            'size_bytes': 9876,
        }
    )
    return {
        'schema_version': 'company-bank-support-coverage-manifest.v1',
        'company_ref': 'inmobiliaria-puig-redacted',
        'fiscal_year': 2025,
        'tax_year': 2026,
        'required_operations': operations,
        'attachments': attachments,
        'confirmations': [
            {
                'confirmation_ref': 'bank-confirmation-redacted',
                'source_ref': 'gmail-thread-redacted',
                'statement_strength': statement_strength,
            }
        ],
    }


class CompanyBankSupportCoverageTests(TestCase):
    def test_complete_redacted_manifest_is_ready_for_accounting_document_review(self):
        result = audit_company_bank_support_coverage(payload=_complete_manifest())

        self.assertEqual(result['classification'], 'preparado')
        self.assertEqual(result['coverage_percent'], 100)
        self.assertTrue(result['ready_for_accounting_document_review'])
        self.assertFalse(result['ready_for_formal_bank_support_review'])
        self.assertEqual(result['summary']['required_operations'], 5)
        self.assertEqual(result['summary']['operations_with_full_support'], 5)
        self.assertTrue(result['summary']['accepted_confirmation_present'])
        self.assertFalse(result['summary']['strong_confirmation_present'])
        self.assertEqual(result['issue_counts']['blocking'], 0)
        self.assertEqual(result['issue_counts']['warning'], 1)
        self.assertIn(
            'company_bank_support.bank_confirmation_not_file_by_file_verified',
            {warning['code'] for warning in result['warnings']},
        )
        self.assertFalse(result['boundary']['reads_documents'])
        self.assertFalse(result['boundary']['autonomous_accounting'])
        self.assertFalse(result['boundary']['final_tax_calculation'])
        self.assertFalse(result['boundary']['sii_submission'])
        self.assertTrue(result['boundary']['requires_responsible_review'])
        self.assertNotIn('://', json.dumps(result))
        self.assertNotIn('@', json.dumps(result))

    def test_verified_complete_manifest_is_ready_for_formal_bank_support_review(self):
        result = audit_company_bank_support_coverage(payload=_complete_manifest(statement_strength='verified_complete'))

        self.assertEqual(result['classification'], 'preparado')
        self.assertEqual(result['coverage_percent'], 100)
        self.assertTrue(result['ready_for_accounting_document_review'])
        self.assertTrue(result['ready_for_formal_bank_support_review'])
        self.assertTrue(result['summary']['accepted_confirmation_present'])
        self.assertTrue(result['summary']['strong_confirmation_present'])
        self.assertEqual(result['issue_counts']['blocking'], 0)
        self.assertEqual(result['issue_counts']['warning'], 0)

    def test_missing_invoice_bundle_blocks_affected_operations(self):
        manifest = _complete_manifest()
        manifest['attachments'] = [
            item for item in manifest['attachments'] if item['category'] != 'invoice_or_tax_document_bundle'
        ]

        result = audit_company_bank_support_coverage(payload=manifest)

        self.assertEqual(result['classification'], 'parcial')
        self.assertEqual(result['coverage_percent'], 67)
        self.assertFalse(result['ready_for_accounting_document_review'])
        self.assertEqual(result['summary']['operations_with_full_support'], 0)
        self.assertEqual(result['next_blocking_operation'], 'leasing-op-01')
        self.assertIn('company_bank_support.operation_support_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['operations'][0]['missing_categories'], ['invoice_or_tax_document_bundle'])

    def test_sensitive_manifest_is_blocking_and_does_not_leak_values(self):
        manifest = _complete_manifest()
        manifest['company_ref'] = 'company_76.123.456-7'
        manifest['attachments'][0]['source_ref'] = 'https://bank.example.test/file?token=secret'
        manifest['attachments'][1]['local_path'] = 'C:\\Users\\owner\\Downloads\\factura.pdf'
        manifest['confirmations'][0]['password'] = 'last-six-rut-digits'

        result = audit_company_bank_support_coverage(payload=manifest)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_accounting_document_review'])
        self.assertIn('company_bank_support.sensitive_reference', issue_codes)
        self.assertIn('company_bank_support.rut_exposed', issue_codes)
        self.assertIn('company_bank_support.absolute_path_exposed', issue_codes)
        rendered = json.dumps(result)
        self.assertNotIn('https://bank.example.test', rendered)
        self.assertNotIn('last-six-rut-digits', rendered)
        self.assertNotIn('76.123.456-7', rendered)

    def test_invalid_manifest_metadata_and_mappings_are_blocking(self):
        manifest = _complete_manifest()
        del manifest['schema_version']
        manifest['attachments'].append(
            {
                'attachment_ref': 'orphan-support-redacted',
                'operation_refs': ['leasing-op-unknown'],
                'category': 'payment_history',
            }
        )
        manifest['confirmations'] = [
            {
                'confirmation_ref': 'bank-confirmation-redacted',
                'statement_strength': 'looks_complete',
            }
        ]

        result = audit_company_bank_support_coverage(payload=manifest)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_accounting_document_review'])
        self.assertIn('company_bank_support.schema_version_missing', issue_codes)
        self.assertIn('company_bank_support.attachment_unknown_operation', issue_codes)
        self.assertIn('company_bank_support.invalid_confirmation_strength', issue_codes)
        self.assertIn('company_bank_support.bank_confirmation_missing', issue_codes)

    def test_command_outputs_audit_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(_complete_manifest()), encoding='utf-8')
            stdout = StringIO()

            call_command('audit_company_bank_support_coverage', manifest=str(manifest_path), stdout=stdout)

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['classification'], 'preparado')

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_company_bank_support_coverage',
                    manifest=str(manifest_path),
                    output='docs/company-bank-support-coverage.json',
                    stdout=StringIO(),
                )

    def test_command_can_fail_on_incomplete_coverage(self):
        manifest = _complete_manifest()
        manifest['confirmations'] = []

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'Cobertura bancaria/leasing incompleta'):
                call_command(
                    'audit_company_bank_support_coverage',
                    manifest=str(manifest_path),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )
