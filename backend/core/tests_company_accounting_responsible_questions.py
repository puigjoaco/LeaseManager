import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.company_accounting_responsible_questions import (
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION,
    build_company_accounting_responsible_questions,
)


class CompanyAccountingResponsibleQuestionsTests(SimpleTestCase):
    def _ownership_validation(self) -> dict:
        return {
            'schema_version': 'annual-tax-ownership-patch-validation.v1',
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2025,
            'tax_year': 2026,
            'ready_for_controlled_db_load': False,
            'blockers': ['ownership_patch_missing'],
            'missing_paths': ['$.ownership.participants'],
            'summary': {
                'participants_count': 0,
                'percentage_total': '0.00',
            },
        }

    def _bank_support_coverage(self) -> dict:
        return {
            'schema_version': 'company-bank-support-coverage-manifest.v1',
            'company_ref': 'company-1',
            'fiscal_year': 2025,
            'tax_year': 2026,
            'classification': 'parcial',
            'ready_for_accounting_document_review': False,
            'issues': [
                {
                    'code': 'company_bank_support.bank_confirmation_missing',
                    'severity': 'blocking',
                    'message': 'No copiar: D:/Privado/Socio Controlado Uno 11111111-1/cartola.pdf',
                }
            ],
        }

    def _company_review_package(self) -> dict:
        return {
            'schema_version': 'company-accounting-review-package.v1',
            'company_ref': 'company-1',
            'fiscal_year': 2025,
            'tax_year': 2026,
            'classification': 'parcial',
            'ready_for_productive_accounting_review': False,
            'summary': {
                'expected_company_ref': 'company-1',
                'accounting_progress_classification': 'parcial',
            },
            'issues': [
                {
                    'code': 'company_accounting_review.accounting_progress_incomplete',
                    'severity': 'blocking',
                    'message': 'Socio Controlado Uno 11111111-1 aparece solo en fixture de prueba.',
                }
            ],
        }

    def test_build_questions_from_redacted_artifacts_without_leaking_messages(self):
        packet = build_company_accounting_responsible_questions(
            source_payloads={
                'ownership_validation': self._ownership_validation(),
                'bank_support_coverage': self._bank_support_coverage(),
                'company_review_package': self._company_review_package(),
            },
            company_ref='company-1',
            fiscal_year=2025,
            tax_year=2026,
        )
        rendered = json.dumps(packet, ensure_ascii=True)
        categories = {question['category'] for question in packet['questions']}

        self.assertEqual(packet['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION)
        self.assertTrue(packet['summary']['ready_for_responsible_review'])
        self.assertIn('ownership', categories)
        self.assertIn('bank_leasing', categories)
        self.assertIn('accounting_progress', categories)
        self.assertFalse(packet['boundary']['autonomous_accounting'])
        self.assertFalse(packet['boundary']['final_tax_calculation'])
        self.assertFalse(packet['boundary']['sii_submission'])
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)

        changed_bank_payload = self._bank_support_coverage()
        changed_bank_payload['issues'][0]['message'] = 'No copiar: D:/Privado/Otro Socio 22222222-2/cartola.pdf'
        changed_packet = build_company_accounting_responsible_questions(
            source_payloads={
                'ownership_validation': self._ownership_validation(),
                'bank_support_coverage': changed_bank_payload,
                'company_review_package': self._company_review_package(),
            },
            company_ref='company-1',
            fiscal_year=2025,
            tax_year=2026,
        )
        self.assertEqual(packet['package_hash'], changed_packet['package_hash'])
        self.assertEqual(
            [source['source_hash'] for source in packet['source_summaries']],
            [source['source_hash'] for source in changed_packet['source_summaries']],
        )

    def test_command_materializes_questions_packet_with_redacted_stdout(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ownership_path = temp_root / 'ownership-validation.json'
            bank_path = temp_root / 'bank-support.json'
            output_dir = temp_root / 'questions'
            ownership_path.write_text(json.dumps(self._ownership_validation()), encoding='utf-8')
            bank_path.write_text(json.dumps(self._bank_support_coverage()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_responsible_questions',
                ownership_validation=str(ownership_path),
                bank_support_coverage=str(bank_path),
                company_ref='company-1',
                fiscal_year=2025,
                tax_year=2026,
                output_dir=str(output_dir),
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            rendered_summary = json.dumps(summary, ensure_ascii=True)
            manifest = json.loads((output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).read_text())
            self.assertEqual(summary['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_SCHEMA_VERSION)
            self.assertEqual(summary['questions_total'], 2)
            self.assertEqual(manifest['summary']['questions_total'], 2)
            self.assertIn('ownership', summary['categories'])
            self.assertIn('bank_leasing', summary['categories'])
            self.assertNotIn('Socio Controlado Uno', rendered_summary)
            self.assertNotIn('11111111-1', rendered_summary)

    def test_noncanonical_issue_codes_are_redacted(self):
        packet = build_company_accounting_responsible_questions(
            source_payloads={
                'Socio Controlado Uno': {
                    'schema_version': 'bad-source.v1',
                    'blockers': ['Socio Controlado Uno 11111111-1 pendiente'],
                }
            },
        )
        rendered = json.dumps(packet, ensure_ascii=True)

        self.assertEqual(packet['questions'][0]['source_issue_code'], 'noncanonical-issue-code')
        self.assertEqual(packet['questions'][0]['source_label'], 'source-redacted')
        self.assertIn('noncanonical-issue-code', packet['questions'][0]['question'])
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)

    def test_command_rejects_repo_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)
            ownership_path = repo_root / 'ownership-validation.json'
            ownership_path.write_text(json.dumps(self._ownership_validation()), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'materialize_company_accounting_responsible_questions',
                        ownership_validation=str(ownership_path),
                        output_dir=str(docs_dir / 'questions'),
                        stdout=StringIO(),
                    )

    def test_command_rejects_non_empty_output_dir(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            ownership_path = temp_root / 'ownership-validation.json'
            output_dir = temp_root / 'questions'
            output_dir.mkdir()
            (output_dir / 'old.json').write_text('{}', encoding='utf-8')
            ownership_path.write_text(json.dumps(self._ownership_validation()), encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'vacio'):
                call_command(
                    'materialize_company_accounting_responsible_questions',
                    ownership_validation=str(ownership_path),
                    output_dir=str(output_dir),
                    stdout=StringIO(),
                )

    def test_command_missing_source_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_responsible_questions',
                    ownership_validation=str(missing_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
