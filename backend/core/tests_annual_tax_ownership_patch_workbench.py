import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.annual_tax_ownership_patch_validator import OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION
from core.annual_tax_ownership_patch_workbench import (
    OWNERSHIP_PATCH_DRAFT_PRIVATE_FILENAME,
    OWNERSHIP_PATCH_WORKBENCH_MANIFEST_FILENAME,
    OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION,
    build_annual_tax_ownership_patch_workbench,
    write_annual_tax_ownership_patch_workbench,
)
from core.annual_tax_ownership_review_checklist import OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION
from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION
from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION,
    validate_company_accounting_responsible_answers,
)
from core.company_accounting_responsible_questions import build_company_accounting_responsible_questions


class AnnualTaxOwnershipPatchWorkbenchTests(SimpleTestCase):
    def _template(self) -> dict:
        return {
            'schema_version': OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2025,
            'tax_year': 2026,
            'source_review_hash': 'a' * 64,
            'candidate_sources': [
                {
                    'path_ref': 'legal/Socio Controlado Uno/constitucion.pdf',
                    'sha256': 'b' * 64,
                    'document_kind': 'constitution_deed',
                    'review_status': 'manual_review_required_legal_candidate',
                    'path_context_tags': ['constitution'],
                    'evidence_ref_suggestion': 'ownership-evidence-' + 'b' * 12,
                    'requires_ocr_or_manual_read': True,
                }
            ],
            'ownership_patch_template': {
                'source_ref': 'ownership-review-2025-controlled',
                'as_of': '2025-12-31',
                'participants': [],
            },
        }

    def _checklist(self) -> dict:
        return {
            'schema_version': OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2025,
            'tax_year': 2026,
            'source_template_hash': 'c' * 64,
            'summary': {
                'reviewable_candidates_total': 10,
                'rendered_candidates_total': 10,
                'validation_present': False,
                'participants_count': 0,
                'percentage_total': '0.00',
                'blocking_items_total': 3,
                'ready_for_manual_review': True,
                'ready_for_controlled_db_load': False,
            },
            'validation_summary': {
                'blockers': ['ownership_patch_validation_missing'],
            },
            'checklist_items': [
                {'key': 'participants_completed_from_legal_review', 'status': 'pending'},
                {'key': 'participants_total_percentage_100', 'status': 'pending'},
                {'key': 'validation_output_redacted', 'status': 'pending'},
            ],
        }

    def _responsible_answers_review(self, *, pending: bool = False) -> dict:
        questions_packet = build_company_accounting_responsible_questions(
            source_payloads={
                'ownership_validation': {
                    'schema_version': 'annual-tax-ownership-patch-validation.v1',
                    'company_ref': 'inmobiliaria-puig',
                    'commercial_year': 2025,
                    'tax_year': 2026,
                    'blockers': ['ownership_patch_missing'],
                },
                'bank_support_coverage': {
                    'schema_version': 'company-bank-support-coverage-manifest.v1',
                    'company_ref': 'inmobiliaria-puig',
                    'fiscal_year': 2025,
                    'tax_year': 2026,
                    'issues': [{'code': 'company_bank_support.bank_confirmation_missing', 'severity': 'blocking'}],
                },
            },
            company_ref='inmobiliaria-puig',
            fiscal_year=2025,
            tax_year=2026,
        )
        answers = {
            'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'fiscal_year': 2025,
            'tax_year': 2026,
            'responsible_ref': 'responsible-review-ac2025-at2026',
            'decision_ref': 'responsible-decisions-ac2025-at2026-v1',
            'evidence_ref': 'responsible-evidence-ac2025-at2026-v1',
            'answers': [
                {
                    'question_key': question['key'],
                    'decision_state': 'pendiente' if pending and index == 1 else 'respondido',
                    'evidence_ref': f'evidence-{index}',
                    'next_action_ref': f'next-action-{index}',
                }
                for index, question in enumerate(questions_packet['questions'], start=1)
            ],
        }
        return validate_company_accounting_responsible_answers(
            questions_packet=questions_packet,
            answers_payload=answers,
        )

    def test_workbench_creates_private_patch_draft_without_leaking_candidate_paths(self):
        result = build_annual_tax_ownership_patch_workbench(
            template=self._template(),
            checklist=self._checklist(),
        )
        rendered_manifest = json.dumps(result['manifest'], ensure_ascii=True)
        patch_draft = result['patch_draft']

        self.assertEqual(result['manifest']['schema_version'], OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION)
        self.assertEqual(patch_draft['schema_version'], OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION)
        self.assertEqual(patch_draft['commercial_year'], 2025)
        self.assertEqual(patch_draft['tax_year'], 2026)
        self.assertEqual(patch_draft['ownership']['as_of'], '2025-12-31')
        self.assertEqual(patch_draft['ownership']['participants'], [])
        self.assertEqual(result['manifest']['summary']['reviewable_candidates_total'], 10)
        self.assertTrue(result['manifest']['safety']['private_patch_may_store_person_names'])
        self.assertFalse(result['manifest']['safety']['stores_person_names'])
        self.assertNotIn('legal/Socio Controlado Uno/constitucion.pdf', rendered_manifest)
        self.assertNotIn('Socio Controlado Uno', rendered_manifest)

    def test_workbench_rejects_sensitive_responsible_or_approval_refs(self):
        with self.assertRaisesMessage(ValueError, 'responsible_ref'):
            build_annual_tax_ownership_patch_workbench(
                template=self._template(),
                responsible_ref='responsable 11111111-1',
                approval_ref='approval-ac2025-at2026',
            )
        with self.assertRaisesMessage(ValueError, 'approval_ref'):
            build_annual_tax_ownership_patch_workbench(
                template=self._template(),
                responsible_ref='responsible-ac2025-at2026',
                approval_ref='D:/Privado/Socio Controlado Uno.pdf',
            )

    def test_workbench_summarizes_responsible_answers_review_without_copying_answer_refs(self):
        result = build_annual_tax_ownership_patch_workbench(
            template=self._template(),
            checklist=self._checklist(),
            responsible_answers_review=self._responsible_answers_review(),
        )
        rendered_manifest = json.dumps(result['manifest'], ensure_ascii=True)
        responsible_summary = result['manifest']['responsible_answers_summary']

        self.assertTrue(result['manifest']['summary']['responsible_answers_present'])
        self.assertTrue(result['manifest']['summary']['responsible_answers_ready'])
        self.assertEqual(result['manifest']['summary']['responsible_answers_blocking_issues_total'], 0)
        self.assertTrue(responsible_summary['present'])
        self.assertEqual(responsible_summary['questions_total'], 2)
        self.assertEqual(responsible_summary['answers_total'], 2)
        self.assertEqual(responsible_summary['decision_states'], {'respondido': 2})
        self.assertIn('ownership', responsible_summary['categories'])
        self.assertIn('bank_leasing', responsible_summary['categories'])
        self.assertNotIn('evidence-1', rendered_manifest)
        self.assertNotIn('responsible-decisions-ac2025-at2026-v1', rendered_manifest)

    def test_workbench_derives_not_ready_from_inconsistent_responsible_answers_review(self):
        review = self._responsible_answers_review()
        review['summary']['ready_for_responsible_decision_handoff'] = True
        review['summary']['missing_questions_total'] = 1
        review['summary']['blocking_issues_total'] = 0
        review['missing_question_keys'] = ['ownership.source-ref']
        review['issues'] = []

        result = build_annual_tax_ownership_patch_workbench(
            template=self._template(),
            responsible_answers_review=review,
        )
        responsible_summary = result['manifest']['responsible_answers_summary']

        self.assertTrue(responsible_summary['reported_ready_for_responsible_decision_handoff'])
        self.assertFalse(responsible_summary['ready_for_responsible_decision_handoff'])
        self.assertEqual(responsible_summary['missing_questions_total'], 1)
        self.assertGreaterEqual(responsible_summary['blocking_issues_total'], 1)
        self.assertIn('responsible_answers.questions_unanswered', responsible_summary['issue_codes'])
        self.assertFalse(result['manifest']['summary']['responsible_answers_ready'])
        self.assertFalse(result['manifest']['decision']['responsible_answers_ready_for_patch_completion'])

    def test_workbench_marks_pending_responsible_answers_as_not_ready(self):
        result = build_annual_tax_ownership_patch_workbench(
            template=self._template(),
            responsible_answers_review=self._responsible_answers_review(pending=True),
        )

        self.assertTrue(result['manifest']['summary']['responsible_answers_present'])
        self.assertFalse(result['manifest']['summary']['responsible_answers_ready'])
        self.assertEqual(result['manifest']['summary']['responsible_answers_blocking_issues_total'], 1)
        self.assertIn(
            'responsible_answers.decision_pending',
            result['manifest']['responsible_answers_summary']['issue_codes'],
        )
        self.assertFalse(result['manifest']['decision']['responsible_answers_ready_for_patch_completion'])

    def test_workbench_redacts_sensitive_summary_keys_from_review_inputs(self):
        checklist = self._checklist()
        checklist['checklist_items'][0]['key'] = 'D:/Privado/Socio Controlado Uno 11111111-1/checklist'
        checklist['validation_summary']['blockers'] = ['D:/Privado/Socio Controlado Uno 11111111-1/blocker']
        review = self._responsible_answers_review()
        review['summary']['decision_states'] = {
            'respondido': 2,
            'D:/Privado/Socio Controlado Uno 11111111-1/decision': 1,
        }
        review['summary']['categories'] = {
            'ownership': 1,
            'D:/Privado/Socio Controlado Uno 11111111-1/category': 1,
        }
        review['issues'] = [
            {
                'code': 'D:/Privado/Socio Controlado Uno 11111111-1/issue',
                'severity': 'blocking',
                'count': 1,
            }
        ]

        result = build_annual_tax_ownership_patch_workbench(
            template=self._template(),
            checklist=checklist,
            responsible_answers_review=review,
        )
        manifest = result['manifest']
        rendered_manifest = json.dumps(manifest, ensure_ascii=True)

        self.assertIn('redacted-checklist-item', manifest['checklist_summary']['blocking_item_keys'])
        self.assertIn('redacted-validation-blocker', manifest['checklist_summary']['validation_blockers'])
        self.assertEqual(manifest['responsible_answers_summary']['decision_states']['redacted-decision-state'], 1)
        self.assertEqual(manifest['responsible_answers_summary']['categories']['redacted-category'], 1)
        self.assertIn('redacted-issue-code', manifest['responsible_answers_summary']['issue_codes'])
        self.assertNotIn('Socio Controlado Uno', rendered_manifest)
        self.assertNotIn('11111111-1', rendered_manifest)
        self.assertNotIn('D:/Privado', rendered_manifest)

    def test_responsible_answers_review_context_must_match_template(self):
        review = self._responsible_answers_review()
        review['tax_year'] = 2027

        with self.assertRaisesMessage(ValueError, 'tax_year'):
            build_annual_tax_ownership_patch_workbench(
                template=self._template(),
                responsible_answers_review=review,
            )

    def test_write_workbench_refuses_non_empty_output_dir(self):
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'workbench'
            output_dir.mkdir()
            (output_dir / 'old.json').write_text('{}', encoding='utf-8')
            result = build_annual_tax_ownership_patch_workbench(template=self._template())

            with self.assertRaisesMessage(ValueError, 'vacio'):
                write_annual_tax_ownership_patch_workbench(workbench=result, output_dir=output_dir)

    def test_command_materializes_manifest_and_private_patch_with_redacted_stdout(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            checklist_path = temp_root / 'checklist.json'
            responsible_answers_path = temp_root / 'responsible-answers-review.json'
            output_dir = temp_root / 'workbench'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            checklist_path.write_text(json.dumps(self._checklist()), encoding='utf-8')
            responsible_answers_path.write_text(json.dumps(self._responsible_answers_review()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_ownership_patch_workbench',
                template=str(template_path),
                checklist=str(checklist_path),
                responsible_answers_review=str(responsible_answers_path),
                require_responsible_answers_ready=True,
                output_dir=str(output_dir),
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            rendered_summary = json.dumps(summary, ensure_ascii=True)
            manifest = json.loads((output_dir / OWNERSHIP_PATCH_WORKBENCH_MANIFEST_FILENAME).read_text(encoding='utf-8'))
            patch_draft = json.loads((output_dir / OWNERSHIP_PATCH_DRAFT_PRIVATE_FILENAME).read_text(encoding='utf-8'))
            self.assertEqual(summary['schema_version'], OWNERSHIP_PATCH_WORKBENCH_SCHEMA_VERSION)
            self.assertEqual(summary['manifest_file'], OWNERSHIP_PATCH_WORKBENCH_MANIFEST_FILENAME)
            self.assertEqual(summary['private_patch_draft_file'], OWNERSHIP_PATCH_DRAFT_PRIVATE_FILENAME)
            self.assertTrue(summary['responsible_answers_present'])
            self.assertTrue(summary['responsible_answers_ready'])
            self.assertEqual(manifest['summary']['rendered_candidates_total'], 10)
            self.assertTrue(manifest['responsible_answers_summary']['ready_for_responsible_decision_handoff'])
            self.assertEqual(patch_draft['ownership']['participants'], [])
            self.assertNotIn('Socio Controlado Uno', rendered_summary)
            self.assertNotIn('11111111-1', rendered_summary)

    def test_command_rejects_inconsistent_responsible_answers_review_when_ready_required(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            responsible_answers_path = temp_root / 'responsible-answers-review.json'
            output_dir = temp_root / 'workbench'
            review = self._responsible_answers_review()
            review['summary']['ready_for_responsible_decision_handoff'] = True
            review['summary']['missing_questions_total'] = 1
            review['summary']['blocking_issues_total'] = 0
            review['missing_question_keys'] = ['ownership.source-ref']
            review['issues'] = []
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            responsible_answers_path.write_text(json.dumps(review), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_annual_tax_ownership_patch_workbench',
                    template=str(template_path),
                    responsible_answers_review=str(responsible_answers_path),
                    output_dir=str(output_dir),
                    require_responsible_answers_ready=True,
                    stdout=StringIO(),
                )

            self.assertEqual(
                str(error.exception),
                'Respuestas responsables listas requeridas para materializar ownership patch workbench.',
            )
            self.assertFalse(output_dir.exists())

    def test_command_rejects_sensitive_responsible_ref_before_writing(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            output_dir = temp_root / 'workbench'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_annual_tax_ownership_patch_workbench',
                    template=str(template_path),
                    output_dir=str(output_dir),
                    responsible_ref='responsable 11111111-1',
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('responsible_ref debe ser una referencia no sensible', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertFalse(output_dir.exists())

    def test_command_requires_ready_responsible_answers_before_writing_when_requested(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            output_dir = temp_root / 'workbench'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_annual_tax_ownership_patch_workbench',
                    template=str(template_path),
                    output_dir=str(output_dir),
                    require_responsible_answers_ready=True,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(
                rendered_error,
                'Respuestas responsables listas requeridas para materializar ownership patch workbench.',
            )
            self.assertFalse(output_dir.exists())

    def test_command_rejects_pending_responsible_answers_before_writing_when_requested(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            responsible_answers_path = temp_root / 'responsible-answers-review.json'
            output_dir = temp_root / 'workbench'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            responsible_answers_path.write_text(
                json.dumps(self._responsible_answers_review(pending=True)),
                encoding='utf-8',
            )

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_annual_tax_ownership_patch_workbench',
                    template=str(template_path),
                    responsible_answers_review=str(responsible_answers_path),
                    output_dir=str(output_dir),
                    require_responsible_answers_ready=True,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(
                rendered_error,
                'Respuestas responsables listas requeridas para materializar ownership patch workbench.',
            )
            self.assertFalse(output_dir.exists())

    def test_command_refuses_repo_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)
            template_path = repo_root / 'template.json'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'materialize_annual_tax_ownership_patch_workbench',
                        template=str(template_path),
                        output_dir=str(docs_dir / 'ownership-workbench'),
                        stdout=StringIO(),
                    )

    def test_command_missing_input_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_annual_tax_ownership_patch_workbench',
                    template=str(missing_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_command_read_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'
            template_path.write_text('{}', encoding='utf-8')

            with patch.object(
                Path,
                'read_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_annual_tax_ownership_patch_workbench',
                        template=str(template_path),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertIn('No se pudo leer template JSON', rendered_error)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_command_invalid_json_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'
            template_path.write_text('{', encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_annual_tax_ownership_patch_workbench',
                    template=str(template_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('template JSON invalido: line 1, column 2', rendered_error)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_command_write_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            output_dir = temp_root / 'Socio Controlado Uno 11111111-1'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')

            with patch.object(
                Path,
                'write_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/workbench.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_annual_tax_ownership_patch_workbench',
                        template=str(template_path),
                        output_dir=str(output_dir),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo escribir ownership patch workbench.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_checklist_context_must_match_template(self):
        checklist = self._checklist()
        checklist['tax_year'] = 2027

        with self.assertRaisesMessage(ValueError, 'tax_year'):
            build_annual_tax_ownership_patch_workbench(
                template=self._template(),
                checklist=checklist,
            )
