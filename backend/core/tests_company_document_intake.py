import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.company_document_intake import audit_company_document_intake
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE


def _complete_manifest():
    operations = [
        {'operation_ref': f'leasing-op-{index:02d}', 'label_ref': f'banco-chile-leasing-{index:02d}'}
        for index in range(1, 3)
    ]
    documents = []
    for operation in operations:
        operation_ref = operation['operation_ref']
        documents.extend(
            [
                {
                    'document_ref': f'{operation_ref}-contract-schedule',
                    'batch_ref': 'banco-chile-thread-redacted',
                    'category': 'bank_contract_or_schedule',
                    'operation_refs': [operation_ref],
                    'size_bytes': 1200,
                },
                {
                    'document_ref': f'{operation_ref}-payment-history',
                    'batch_ref': 'banco-chile-thread-redacted',
                    'category': 'bank_payment_history',
                    'operation_refs': [operation_ref],
                    'size_bytes': 1300,
                },
            ]
        )
    documents.extend(
        [
            {
                'document_ref': 'banco-chile-invoices-bundle',
                'batch_ref': 'banco-chile-thread-redacted',
                'category': 'bank_invoice_or_tax_document_bundle',
                'operation_refs': ['*'],
                'size_bytes': 4300,
            },
            {
                'document_ref': 'banco-chile-confirmation',
                'batch_ref': 'banco-chile-thread-redacted',
                'category': 'bank_confirmation',
                'statement_strength': 'verified_complete',
            },
            {
                'document_ref': 'rcv-2025-controlled',
                'batch_ref': 'annual-tax-source-redacted',
                'category': 'rcv_structured_input',
                'months': list(range(1, 13)),
            },
            {
                'document_ref': 'f29-2025-controlled',
                'batch_ref': 'annual-tax-source-redacted',
                'category': 'f29_support_input',
                'months': list(range(1, 13)),
            },
            {
                'document_ref': 'ledger-2025-controlled',
                'batch_ref': 'annual-tax-source-redacted',
                'category': 'annual_ledger_input',
                'artifact_key': 'libro_diario',
            },
            {
                'document_ref': 'f22-at2026-controlled',
                'batch_ref': 'annual-tax-source-redacted',
                'category': 'f22_expected_output',
                'output_status': 'final',
            },
        ]
    )
    return {
        'schema_version': 'company-document-intake-manifest.v1',
        'company_ref': 'company-1',
        'fiscal_year': 2025,
        'tax_year': 2026,
        'source_batches': [
            {
                'batch_ref': 'banco-chile-thread-redacted',
                'source_kind': 'gmail_thread',
                'source_ref': 'gmail-thread-banco-chile-redacted',
                'declared_complete': True,
            },
            {
                'batch_ref': 'annual-tax-source-redacted',
                'source_kind': 'external_folder',
                'source_ref': 'annual-source-folder-redacted',
                'declared_complete': False,
            },
        ],
        'required_bank_operations': operations,
        'documents': documents,
    }


class CompanyDocumentIntakeTests(SimpleTestCase):
    def test_complete_redacted_intake_builds_bank_manifest_and_annual_bridge(self):
        result = audit_company_document_intake(payload=_complete_manifest())

        self.assertEqual(result['classification'], 'preparado')
        self.assertTrue(result['ready_for_document_intake_review'])
        self.assertTrue(result['ready_for_bank_support_manifest'])
        self.assertTrue(result['ready_for_source_manifest_reconciliation'])
        self.assertTrue(result['ready_for_productive_document_review'])
        self.assertEqual(result['summary']['company_ref'], 'company-1')
        self.assertEqual(result['bank_support_coverage']['classification'], 'preparado')
        self.assertEqual(result['bank_support_coverage']['coverage_percent'], 100)
        self.assertEqual(result['bank_support_manifest_draft']['schema_version'], 'company-bank-support-coverage-manifest.v1')
        self.assertEqual(result['annual_source_bridge']['target_source_manifest_schema_version'], 'annual-tax-source-manifest.v1')
        self.assertFalse(result['annual_source_bridge']['can_replace_read_only_source_scan'])
        self.assertTrue(result['annual_source_bridge']['requires_read_only_source_root_scan_for_file_hashes'])
        self.assertFalse(result['boundary']['reads_real_documents'])
        self.assertFalse(result['boundary']['autonomous_accounting'])
        self.assertFalse(result['boundary']['final_tax_calculation'])
        self.assertFalse(result['boundary']['sii_submission'])
        self.assertTrue(result['boundary']['requires_responsible_review'])
        rendered = json.dumps(result)
        self.assertNotIn('://', rendered)
        self.assertNotIn('@', rendered)

    def test_sensitive_intake_blocks_without_leaking_values(self):
        manifest = _complete_manifest()
        manifest['company_ref'] = '76.123.456-7'
        manifest['source_batches'][0]['source_ref'] = 'https://mail.example.test/thread?token=secret'
        manifest['documents'][0]['local_path'] = 'C:\\Users\\owner\\Downloads\\factura.pdf'
        manifest['documents'][1]['password'] = 'last-six-rut-digits'

        result = audit_company_document_intake(payload=manifest)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_document_intake_review'])
        self.assertIn('company_document_intake.sensitive_reference', issue_codes)
        self.assertIn('company_document_intake.rut_exposed', issue_codes)
        self.assertIn('company_document_intake.absolute_path_exposed', issue_codes)
        rendered = json.dumps(result)
        self.assertNotIn('https://mail.example.test', rendered)
        self.assertNotIn('last-six-rut-digits', rendered)
        self.assertNotIn('76.123.456-7', rendered)
        self.assertNotIn('C:\\Users\\owner\\Downloads', rendered)
        self.assertIn(REDACTED_SENSITIVE_REFERENCE, rendered)

    def test_invalid_mapping_metadata_is_blocking(self):
        manifest = _complete_manifest()
        del manifest['schema_version']
        manifest['documents'].append(
            {
                'document_ref': 'bad-doc',
                'batch_ref': 'unknown-batch',
                'category': 'invented_category',
                'months': [13],
                'ddjj_forms': ['DJ1887'],
                'fiscal_year': 2024,
            }
        )
        manifest['documents'].append(dict(manifest['documents'][0]))

        result = audit_company_document_intake(payload=manifest)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_document_intake_review'])
        self.assertIn('company_document_intake.schema_version_missing', issue_codes)
        self.assertIn('company_document_intake.document_unknown_batch', issue_codes)
        self.assertIn('company_document_intake.invalid_document_category', issue_codes)
        self.assertIn('company_document_intake.invalid_month', issue_codes)
        self.assertIn('company_document_intake.invalid_ddjj_form', issue_codes)
        self.assertIn('company_document_intake.document_fiscal_year_mismatch', issue_codes)
        self.assertIn('company_document_intake.duplicate_document_ref', issue_codes)

    def test_command_outputs_audit_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            manifest_path.write_text(json.dumps(_complete_manifest()), encoding='utf-8')
            stdout = StringIO()

            call_command('audit_company_document_intake', manifest=str(manifest_path), stdout=stdout)

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['classification'], 'preparado')

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_company_document_intake',
                    manifest=str(manifest_path),
                    output='docs/company-document-intake.json',
                    stdout=StringIO(),
                )

    def test_command_can_fail_on_incomplete_intake(self):
        manifest = _complete_manifest()
        manifest['documents'] = []

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'Intake documental contable/renta incompleto'):
                call_command(
                    'audit_company_document_intake',
                    manifest=str(manifest_path),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )

    def test_command_accepts_output_under_local_evidence(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            output_path = Path(temp_dir) / 'audit' / 'document-intake-audit.json'
            manifest_path.write_text(json.dumps(_complete_manifest()), encoding='utf-8')

            call_command(
                'audit_company_document_intake',
                manifest=str(manifest_path),
                output=str(output_path),
                stdout=StringIO(),
            )

            result = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertTrue(result['ready_for_productive_document_review'])
