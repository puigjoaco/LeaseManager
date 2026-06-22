import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.company_document_intake import (
    audit_company_document_intake,
    verify_company_document_intake_package,
    verify_company_document_intake_package_from_disk,
)
from core.management.commands.materialize_company_document_intake import _safe_path_component
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE


def _complete_manifest(*, statement_strength='verified_complete'):
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
                'statement_strength': statement_strength,
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
        self.assertTrue(result['ready_for_formal_bank_support_manifest'])
        self.assertTrue(result['ready_for_source_manifest_reconciliation'])
        self.assertTrue(result['ready_for_productive_document_review'])
        self.assertTrue(result['summary']['ready_for_formal_bank_support_manifest'])
        self.assertEqual(result['summary']['company_ref'], 'company-1')
        self.assertEqual(result['bank_support_coverage']['classification'], 'preparado')
        self.assertEqual(result['bank_support_coverage']['coverage_percent'], 100)
        self.assertTrue(result['bank_support_coverage']['ready_for_formal_bank_support_review'])
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

    def test_expected_complete_bank_confirmation_does_not_enable_productive_review(self):
        result = audit_company_document_intake(
            payload=_complete_manifest(statement_strength='expected_complete')
        )

        warning_codes = {
            warning['code']
            for warning in result['warnings']
        }

        self.assertEqual(result['classification'], 'preparado')
        self.assertTrue(result['ready_for_document_intake_review'])
        self.assertTrue(result['ready_for_bank_support_manifest'])
        self.assertFalse(result['ready_for_formal_bank_support_manifest'])
        self.assertTrue(result['ready_for_source_manifest_reconciliation'])
        self.assertFalse(result['ready_for_productive_document_review'])
        self.assertTrue(result['bank_support_coverage']['ready_for_accounting_document_review'])
        self.assertFalse(result['bank_support_coverage']['ready_for_formal_bank_support_review'])
        self.assertIn(
            'company_document_intake.company_bank_support.bank_confirmation_not_file_by_file_verified',
            warning_codes,
        )

    def test_sensitive_intake_blocks_without_leaking_values(self):
        manifest = _complete_manifest()
        manifest['company_ref'] = 'company_76.123.456-7'
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

    def test_materialize_company_document_intake_command_writes_verified_package(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)
        manifest = _complete_manifest()

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            output_dir = Path(temp_dir) / 'company-document-intake-package'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_document_intake',
                manifest=str(manifest_path),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            verification = verify_company_document_intake_package(
                payload=manifest,
                package_dir=output_dir,
            )
            disk_verification = verify_company_document_intake_package_from_disk(package_dir=output_dir)

            self.assertTrue(result['materialized'])
            self.assertEqual(result['package_hash'], verification['package_hash'])
            self.assertEqual(result['package_hash'], disk_verification['package_hash'])
            self.assertEqual(result['classification'], 'preparado')
            self.assertEqual(disk_verification['bank_support_manifest']['schema_version'], 'company-bank-support-coverage-manifest.v1')
            self.assertEqual(disk_verification['annual_source_bridge']['schema_version'], 'annual-tax-source-intake-bridge.v1')
            self.assertTrue(result['ready_for_document_intake_review'])
            self.assertTrue(result['ready_for_bank_support_manifest'])
            self.assertTrue(result['ready_for_formal_bank_support_manifest'])
            self.assertTrue(result['ready_for_source_manifest_reconciliation'])
            self.assertTrue(result['ready_for_productive_document_review'])
            self.assertTrue(verification['ready_for_formal_bank_support_manifest'])
            self.assertTrue(disk_verification['ready_for_formal_bank_support_manifest'])
            self.assertEqual(result['company_ref'], 'company-1')
            self.assertEqual(result['fiscal_year'], 2025)
            self.assertEqual(result['tax_year'], 2026)
            self.assertGreater(result['documents_total'], 0)
            self.assertFalse(result['reads_real_documents'])
            self.assertFalse(result['stores_real_attachments'])
            self.assertFalse(result['uses_email_connector'])
            self.assertFalse(result['opens_bank_gate'])
            self.assertFalse(result['opens_sii_gate'])
            self.assertFalse(result['autonomous_accounting'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertFalse(result['sii_submission'])
            self.assertTrue(result['requires_responsible_review'])

            for file_key in (
                'package_manifest_file',
                'audit_file',
                'bank_support_manifest_file',
                'annual_source_bridge_file',
            ):
                self.assertTrue((output_dir / result[file_key]).is_file())

            rendered = stdout.getvalue()
            for file_path in output_dir.iterdir():
                rendered += file_path.read_text(encoding='utf-8')
            self.assertNotIn('://', rendered)
            self.assertNotIn('@', rendered)

    def test_verify_company_document_intake_package_from_disk_rejects_tampered_file(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)
        manifest = _complete_manifest()

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            output_dir = Path(temp_dir) / 'company-document-intake-package'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            call_command(
                'materialize_company_document_intake',
                manifest=str(manifest_path),
                output_dir=str(output_dir),
                stdout=StringIO(),
            )

            bank_manifest_path = output_dir / 'company-bank-support-coverage-manifest.json'
            bank_manifest = json.loads(bank_manifest_path.read_text(encoding='utf-8'))
            bank_manifest['attachments'] = bank_manifest['attachments'][1:]
            bank_manifest_path.write_text(
                json.dumps(bank_manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=True),
                encoding='utf-8',
            )

            with self.assertRaisesMessage(ValueError, 'no coincide con la auditoria incluida'):
                verify_company_document_intake_package_from_disk(package_dir=output_dir)

    def test_materialize_company_document_intake_rejects_nonempty_output_dir(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            manifest_path.write_text(json.dumps(_complete_manifest()), encoding='utf-8')
            output_dir = Path(temp_dir) / 'company-document-intake-package'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous document intake residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_company_document_intake',
                    manifest=str(manifest_path),
                    output_dir=str(output_dir),
                    stdout=StringIO(),
                )

            self.assertTrue(stale_file.exists())

    def test_materialize_company_document_intake_rejects_versioned_repo_output(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            manifest_path.write_text(json.dumps(_complete_manifest()), encoding='utf-8')
            blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'company-document-intake-package'

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'materialize_company_document_intake',
                    manifest=str(manifest_path),
                    output_dir=str(blocked_output),
                    stdout=StringIO(),
                )

            self.assertFalse(blocked_output.exists())

    def test_materialize_company_document_intake_redacts_sensitive_manifest_values(self):
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)
        manifest = _complete_manifest()
        manifest['company_ref'] = '76.123.456-7'
        manifest['source_batches'][0]['source_ref'] = 'https://mail.example.test/thread?token=secret'
        manifest['documents'][0]['local_path'] = 'C:\\Users\\owner\\Downloads\\factura.pdf'
        manifest['documents'][1]['password'] = 'last-six-rut-digits'

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'document-intake.json'
            output_dir = Path(temp_dir) / 'company-document-intake-package'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_document_intake',
                manifest=str(manifest_path),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['classification'], 'parcial')
            self.assertFalse(result['ready_for_productive_document_review'])
            rendered = stdout.getvalue()
            for file_path in output_dir.iterdir():
                rendered += file_path.read_text(encoding='utf-8')
            for sensitive_value in (
                'https://mail.example.test',
                'last-six-rut-digits',
                '76.123.456-7',
                'C:\\Users\\owner\\Downloads',
            ):
                self.assertNotIn(sensitive_value, rendered)
            self.assertIn(REDACTED_SENSITIVE_REFERENCE, rendered)

    def test_materialize_company_document_intake_default_path_component_redacts_sensitive_ref(self):
        self.assertEqual(_safe_path_component('76.123.456-7'), 'sensitive-ref')
        self.assertEqual(_safe_path_component('https://mail.example.test/thread'), 'sensitive-ref')
        self.assertEqual(_safe_path_component('owner@example.test'), 'sensitive-ref')
        self.assertEqual(_safe_path_component('Company 1'), 'company-1')
