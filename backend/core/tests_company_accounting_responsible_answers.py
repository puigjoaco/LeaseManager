import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_DISCOVERY_SCHEMA_VERSION,
    COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PREFLIGHT_SCHEMA_VERSION,
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION,
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION,
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
    COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
    COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_SCHEMA_VERSION,
    build_company_accounting_responsible_answers_template,
    build_company_accounting_responsible_handoff_packet,
    validate_company_accounting_responsible_answers,
    verify_company_accounting_responsible_handoff_packet,
    write_company_accounting_responsible_handoff_packet,
)
from core.company_accounting_responsible_questions import (
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
    build_company_accounting_responsible_questions,
)


class CompanyAccountingResponsibleAnswersTests(SimpleTestCase):
    def _questions_packet(self) -> dict:
        return build_company_accounting_responsible_questions(
            source_payloads={
                'ownership_validation': {
                    'schema_version': 'annual-tax-ownership-patch-validation.v1',
                    'company_ref': 'company-1',
                    'commercial_year': 2025,
                    'tax_year': 2026,
                    'blockers': ['ownership_patch_missing'],
                },
                'bank_support_coverage': {
                    'schema_version': 'company-bank-support-coverage-manifest.v1',
                    'company_ref': 'company-1',
                    'fiscal_year': 2025,
                    'tax_year': 2026,
                    'issues': [{'code': 'company_bank_support.bank_confirmation_missing', 'severity': 'blocking'}],
                },
            },
            company_ref='company-1',
            fiscal_year=2025,
            tax_year=2026,
        )

    def _questions_packet_with_readiness_source(self) -> dict:
        packet = self._questions_packet()
        packet['source_summaries'] = [
            {
                'label': 'company_review_package',
                'schema_version': 'company-accounting-review-package.v1',
                'classification': 'parcial',
                'ready_flags': {
                    'ready_for_formal_bank_support_review': False,
                    'document_intake_ready_for_productive_review': False,
                    'document_intake_ready_for_formal_bank_support_manifest': True,
                    'source_11.111.111-1': True,
                },
                'issues_total': 2,
                'safe_issue_codes': [
                    {
                        'code': 'company_accounting.responsible_review_missing',
                        'severity': 'blocking',
                    },
                    {
                        'code': 'ownership_11.111.111-1_pending',
                        'severity': 'severity_22.222.222-2',
                    },
                ],
                'source_hash': 'a' * 64,
            }
        ]
        return packet

    def _answers_payload(self, packet: dict) -> dict:
        return {
            'schema_version': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION,
            'company_ref': packet['company_ref'],
            'fiscal_year': packet['fiscal_year'],
            'tax_year': packet['tax_year'],
            'responsible_ref': 'responsible-review-ac2025-at2026',
            'decision_ref': 'responsible-decisions-ac2025-at2026-v1',
            'evidence_ref': 'responsible-evidence-ac2025-at2026-v1',
            'answers': [
                {
                    'question_key': question['key'],
                    'decision_state': 'respondido',
                    'evidence_ref': f'evidence-{index}',
                    'next_action_ref': f'next-action-{index}',
                }
                for index, question in enumerate(packet['questions'], start=1)
            ],
        }

    def test_validates_complete_answers_without_storing_raw_text(self):
        packet = self._questions_packet()
        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=self._answers_payload(packet),
        )
        rendered = json.dumps(review, ensure_ascii=True)

        self.assertEqual(review['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION)
        self.assertTrue(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertFalse(review['summary']['ready_for_productive_accounting_review'])
        self.assertFalse(review['summary']['final_tax_calculation'])
        self.assertFalse(review['summary']['sii_submission'])
        self.assertEqual(review['summary']['questions_total'], len(packet['questions']))
        self.assertEqual(review['summary']['answers_total'], len(packet['questions']))
        self.assertEqual(review['summary']['blocking_issues_total'], 0)
        self.assertTrue(all(not answer['raw_text_stored'] for answer in review['answers']))
        self.assertNotIn('answer_text', rendered)

    def test_validates_complete_answers_preserving_question_readiness_sources(self):
        packet = self._questions_packet_with_readiness_source()
        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=self._answers_payload(packet),
        )
        rendered = json.dumps(review, ensure_ascii=True)
        source_summary = review['question_source_summaries'][0]
        ready_flags = source_summary['ready_flags']
        safe_issue_codes = source_summary['safe_issue_codes']

        self.assertTrue(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(review['summary']['readiness_sources_total'], 1)
        self.assertFalse(ready_flags['ready_for_formal_bank_support_review'])
        self.assertFalse(ready_flags['document_intake_ready_for_productive_review'])
        self.assertTrue(ready_flags['document_intake_ready_for_formal_bank_support_manifest'])
        self.assertIn(
            {'code': 'company_accounting.responsible_review_missing', 'severity': 'blocking'},
            safe_issue_codes,
        )
        self.assertIn({'code': 'redacted-issue-code', 'severity': 'blocking'}, safe_issue_codes)
        self.assertNotIn('source_11.111.111-1', ready_flags)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11.111.111-1', rendered)
        self.assertNotIn('22.222.222-2', rendered)
        self.assertNotIn('D:/Privado', rendered)

    def test_missing_answers_are_blocking_when_complete_required(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['answers'] = answers['answers'][:1]

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(review['summary']['missing_questions_total'], len(packet['questions']) - 1)
        self.assertIn('responsible_answers.questions_unanswered', issue_codes)

    def test_missing_answers_are_blocking_even_when_incomplete_allowed(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['answers'] = answers['answers'][:1]

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
            require_complete=False,
        )
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(review['summary']['missing_questions_total'], len(packet['questions']) - 1)
        self.assertIn('responsible_answers.questions_unanswered', issue_codes)
        self.assertEqual(review['summary']['blocking_issues_total'], len(packet['questions']) - 1)

    def test_pending_decisions_are_blocking(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['answers'][0]['decision_state'] = 'pendiente'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertIn('responsible_answers.decision_pending', issue_codes)

    def test_top_level_next_action_ref_can_safely_apply_to_all_answers(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['next_action_ref'] = 'shared-next-action-ac2025-at2026'
        for answer in answers['answers']:
            answer.pop('next_action_ref', None)

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )

        self.assertTrue(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(review['summary']['blocking_issues_total'], 0)
        self.assertTrue(
            all(answer['next_action_ref'] == 'shared-next-action-ac2025-at2026' for answer in review['answers'])
        )

    def test_builds_pending_answers_template_without_raw_text_or_sensitive_values(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            responsible_ref='responsable 11111111-1',
            decision_ref='decision-ref-ac2025-at2026',
            evidence_ref='D:/Privado/Socio Controlado Uno.pdf',
            next_action_ref='complete-responsible-review',
        )
        rendered = json.dumps(template, ensure_ascii=True)
        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=template,
        )
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertEqual(template['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION)
        self.assertEqual(template['template_schema_version'], 'company-accounting-responsible-answers-template.v1')
        self.assertEqual(template['template_summary']['answers_total'], len(packet['questions']))
        self.assertFalse(template['template_summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(template['next_action_ref'], 'complete-responsible-review')
        self.assertTrue(all(answer['decision_state'] == 'pendiente' for answer in template['answers']))
        self.assertTrue(all(answer['responsible_ref'] == 'responsible-ref-pending' for answer in template['answers']))
        self.assertTrue(all(answer['evidence_ref'] == 'evidence-ref-pending' for answer in template['answers']))
        self.assertTrue(all(answer['next_action_ref'] == 'complete-responsible-review' for answer in template['answers']))
        self.assertIn('responsible_answers.decision_pending', issue_codes)
        self.assertEqual(review['summary']['blocking_issues_total'], len(packet['questions']))
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)
        self.assertNotIn('answer_text', rendered)

    def test_unknown_or_sensitive_references_are_blocking_without_leaking_values(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['responsible_ref'] = 'responsable 11111111-1'
        answers['answers'][0]['question_key'] = 'ownership.unknown'
        answers['answers'][1]['evidence_ref'] = 'D:/Privado/Socio Controlado Uno 11111111-1.pdf'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
            require_complete=False,
        )
        rendered = json.dumps(review, ensure_ascii=True)
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertIn('responsible_answers.responsible_ref_invalid', issue_codes)
        self.assertIn('responsible_answers.question_key_unknown', issue_codes)
        self.assertIn('responsible_answers.evidence_ref_invalid', issue_codes)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)

    def test_sensitive_answers_company_ref_is_blocking_without_leaking_value(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['company_ref'] = 'D:/Privado/Socio Controlado Uno 11111111-1'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        rendered = json.dumps(review, ensure_ascii=True)
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(review['company_ref'], packet['company_ref'])
        self.assertIn('responsible_answers.company_ref_invalid', issue_codes)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)

    def test_sensitive_questions_company_ref_is_blocking_without_leaking_value(self):
        packet = self._questions_packet()
        safe_packet = self._questions_packet()
        answers = self._answers_payload(safe_packet)
        packet['company_ref'] = 'D:/Privado/Socio Controlado Uno 11111111-1'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        rendered = json.dumps(review, ensure_ascii=True)
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertEqual(review['company_ref'], safe_packet['company_ref'])
        self.assertIn('responsible_answers.questions_company_ref_invalid', issue_codes)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)

    def test_sensitive_top_level_evidence_ref_is_blocking_without_leaking_value(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['evidence_ref'] = 'D:/Privado/Socio Controlado Uno 11111111-1/evidence.pdf'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        rendered = json.dumps(review, ensure_ascii=True)
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertIn('responsible_answers.evidence_ref_invalid', issue_codes)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)

    def test_sensitive_top_level_next_action_ref_is_blocking_without_leaking_value(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['next_action_ref'] = 'https://privado.example/accion/Socio-Controlado-Uno-11111111-1'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        rendered = json.dumps(review, ensure_ascii=True)
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertIn('responsible_answers.next_action_ref_invalid', issue_codes)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('privado.example', rendered)

    def test_raw_answer_text_fields_are_blocking_and_not_persisted(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['notes'] = 'No copiar decision privada con RUT 11111111-1'
        answers['answers'][0]['answer_text'] = 'No copiar Socio Controlado Uno 11111111-1'

        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=answers,
        )
        rendered = json.dumps(review, ensure_ascii=True)
        issue_codes = {issue['code'] for issue in review['issues']}

        self.assertFalse(review['summary']['ready_for_responsible_decision_handoff'])
        self.assertIn('responsible_answers.raw_text_field_not_allowed', issue_codes)
        self.assertEqual(review['summary']['blocking_issues_total'], 2)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)

    def test_command_materializes_answers_review_with_safe_stdout(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            output_dir = temp_root / 'answers-review'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_responsible_answers',
                questions_packet=str(questions_path),
                answers=str(answers_path),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            manifest = json.loads((output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).read_text())
            self.assertEqual(summary['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_REVIEW_SCHEMA_VERSION)
            self.assertEqual(summary['answers_total'], len(packet['questions']))
            self.assertTrue(summary['ready_for_responsible_decision_handoff'])
            self.assertEqual(manifest['summary']['answers_total'], len(packet['questions']))

    def test_command_materializes_answers_review_from_verified_handoff_packet(self):
        packet = self._questions_packet_with_readiness_source()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            handoff_dir = temp_root / 'handoff-packet'
            answers_path = temp_root / 'answers.json'
            output_dir = temp_root / 'answers-review'
            write_company_accounting_responsible_handoff_packet(
                questions_packet=packet,
                answers_template=template,
                output_dir=handoff_dir,
            )
            answers_path.write_text(json.dumps(answers), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_responsible_answers',
                handoff_packet_dir=str(handoff_dir),
                answers=str(answers_path),
                output_dir=str(output_dir),
                fail_on_blocking=True,
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            manifest = json.loads((output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).read_text())
            rendered = json.dumps(manifest, ensure_ascii=True)
            self.assertEqual(summary['source_kind'], 'handoff_packet')
            self.assertTrue(summary['handoff_packet_verified'])
            self.assertTrue(summary['ready_for_responsible_decision_handoff'])
            self.assertEqual(summary['readiness_sources_total'], 1)
            self.assertEqual(manifest['questions_packet_hash'], template['questions_packet_hash'])
            self.assertEqual(manifest['summary']['answers_total'], len(packet['questions']))
            self.assertEqual(manifest['summary']['readiness_sources_total'], 1)
            self.assertFalse(
                manifest['question_source_summaries'][0]['ready_flags']['ready_for_formal_bank_support_review']
            )
            self.assertNotIn('Socio Controlado Uno', rendered)
            self.assertNotIn('11111111-1', rendered)
            self.assertNotIn('D:/Privado', rendered)

    def test_audit_answers_draft_from_verified_handoff_packet_does_not_write_review(self):
        packet = self._questions_packet_with_readiness_source()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            handoff_dir = temp_root / 'handoff-packet'
            answers_path = temp_root / 'answers.json'
            write_company_accounting_responsible_handoff_packet(
                questions_packet=packet,
                answers_template=template,
                output_dir=handoff_dir,
            )
            answers_path.write_text(json.dumps(answers), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'audit_company_accounting_responsible_answers_draft',
                handoff_packet_dir=str(handoff_dir),
                answers=str(answers_path),
                require_ready=True,
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary['schema_version'], 'company-accounting-responsible-answers-draft-audit.v1')
            self.assertEqual(summary['source_kind'], 'handoff_packet')
            self.assertTrue(summary['handoff_packet_verified'])
            self.assertTrue(summary['ready_for_responsible_decision_handoff'])
            self.assertEqual(summary['readiness_sources_total'], 1)
            self.assertFalse(summary['writes_review_manifest'])
            self.assertFalse((temp_root / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).exists())

    def test_audit_answers_draft_require_ready_reports_blockers_without_writing_review(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['answers'] = answers['answers'][:1]
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')
            stdout = StringIO()

            with self.assertRaises(CommandError) as error:
                call_command(
                    'audit_company_accounting_responsible_answers_draft',
                    questions_packet=str(questions_path),
                    answers=str(answers_path),
                    allow_incomplete=True,
                    require_ready=True,
                    stdout=stdout,
                )

            summary = json.loads(stdout.getvalue())
            self.assertEqual(str(error.exception), 'El borrador de respuestas responsables no esta listo para handoff.')
            self.assertFalse(summary['ready_for_responsible_decision_handoff'])
            self.assertFalse(summary['writes_review_manifest'])
            self.assertIn('responsible_answers.questions_unanswered', summary['issue_codes'])
            self.assertFalse((temp_root / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).exists())

    def test_audit_answers_draft_requires_exactly_one_questions_source(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            handoff_dir = temp_root / 'handoff-packet'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')

            with self.assertRaises(CommandError) as missing_error:
                call_command(
                    'audit_company_accounting_responsible_answers_draft',
                    answers=str(answers_path),
                    stdout=StringIO(),
                )
            self.assertEqual(
                str(missing_error.exception),
                'Debe informar exactamente una fuente de preguntas: --questions-packet o --handoff-packet-dir.',
            )

            with self.assertRaises(CommandError) as duplicated_error:
                call_command(
                    'audit_company_accounting_responsible_answers_draft',
                    questions_packet=str(questions_path),
                    handoff_packet_dir=str(handoff_dir),
                    answers=str(answers_path),
                    stdout=StringIO(),
                )
            self.assertEqual(str(duplicated_error.exception), str(missing_error.exception))

    def test_command_requires_exactly_one_questions_source(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            handoff_dir = temp_root / 'handoff-packet'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')

            with self.assertRaises(CommandError) as missing_error:
                call_command(
                    'materialize_company_accounting_responsible_answers',
                    answers=str(answers_path),
                    output_dir=str(temp_root / 'answers-review-missing'),
                    stdout=StringIO(),
                )
            self.assertEqual(
                str(missing_error.exception),
                'Debe informar exactamente una fuente de preguntas: --questions-packet o --handoff-packet-dir.',
            )

            with self.assertRaises(CommandError) as duplicated_error:
                call_command(
                    'materialize_company_accounting_responsible_answers',
                    questions_packet=str(questions_path),
                    handoff_packet_dir=str(handoff_dir),
                    answers=str(answers_path),
                    output_dir=str(temp_root / 'answers-review-duplicated'),
                    stdout=StringIO(),
                )
            self.assertEqual(str(duplicated_error.exception), str(missing_error.exception))

    def test_command_allow_incomplete_keeps_missing_questions_blocking(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['answers'] = answers['answers'][:1]
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            output_dir = temp_root / 'answers-review'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_responsible_answers',
                questions_packet=str(questions_path),
                answers=str(answers_path),
                output_dir=str(output_dir),
                allow_incomplete=True,
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            manifest = json.loads((output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).read_text())
            issue_codes = {issue['code'] for issue in manifest['issues']}
            self.assertFalse(summary['ready_for_responsible_decision_handoff'])
            self.assertEqual(summary['missing_questions_total'], len(packet['questions']) - 1)
            self.assertEqual(summary['blocking_issues_total'], len(packet['questions']) - 1)
            self.assertFalse(manifest['summary']['ready_for_responsible_decision_handoff'])
            self.assertIn('responsible_answers.questions_unanswered', issue_codes)

    def test_command_fail_on_blocking_rejects_before_writing_review(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        answers['answers'] = answers['answers'][:1]
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            output_dir = temp_root / 'answers-review'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_responsible_answers',
                    questions_packet=str(questions_path),
                    answers=str(answers_path),
                    output_dir=str(output_dir),
                    allow_incomplete=True,
                    fail_on_blocking=True,
                    stdout=StringIO(),
                )

            self.assertEqual(
                str(error.exception),
                'La revision de respuestas responsables conserva issues bloqueantes.',
            )
            self.assertFalse(output_dir.exists())

    def test_command_materializes_answers_template_with_safe_stdout(self):
        packet = self._questions_packet()
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            output_dir = temp_root / 'answers-template'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_responsible_answers_template',
                questions_packet=str(questions_path),
                output_dir=str(output_dir),
                responsible_ref='responsable 11111111-1',
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            manifest = json.loads((output_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).read_text())
            rendered = json.dumps(manifest, ensure_ascii=True)
            self.assertEqual(summary['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_SCHEMA_VERSION)
            self.assertEqual(summary['template_schema_version'], 'company-accounting-responsible-answers-template.v1')
            self.assertEqual(summary['answers_total'], len(packet['questions']))
            self.assertFalse(summary['ready_for_responsible_decision_handoff'])
            self.assertEqual(manifest['template_summary']['answers_total'], len(packet['questions']))
            self.assertNotIn('11111111-1', rendered)

    def test_command_rejects_repo_output_outside_local_evidence(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)
            questions_path = repo_root / 'questions.json'
            answers_path = repo_root / 'answers.json'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'materialize_company_accounting_responsible_answers',
                        questions_packet=str(questions_path),
                        answers=str(answers_path),
                        output_dir=str(docs_dir / 'answers-review'),
                        stdout=StringIO(),
                    )

    def test_command_write_error_does_not_echo_sensitive_path(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            answers_path = temp_root / 'answers.json'
            output_dir = temp_root / 'Socio Controlado Uno 11111111-1'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')

            with patch.object(
                Path,
                'write_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/answers-review.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_company_accounting_responsible_answers',
                        questions_packet=str(questions_path),
                        answers=str(answers_path),
                        output_dir=str(output_dir),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo escribir revision de respuestas responsables.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_command_missing_questions_path_does_not_echo_sensitive_path(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            sensitive_dir = temp_root / 'Socio Controlado Uno 11111111-1'
            sensitive_dir.mkdir()
            questions_path = sensitive_dir / 'missing-questions.json'
            answers_path = temp_root / 'answers.json'
            answers_path.write_text(json.dumps(answers), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_responsible_answers',
                    questions_packet=str(questions_path),
                    answers=str(answers_path),
                    output_dir=str(temp_root / 'answers-review'),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No existe questions_packet JSON o no es un archivo legible.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn(str(sensitive_dir), rendered_error)

    def test_command_read_error_does_not_echo_sensitive_answer_path(self):
        packet = self._questions_packet()
        answers = self._answers_payload(packet)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            sensitive_dir = temp_root / 'Socio Controlado Uno 11111111-1'
            sensitive_dir.mkdir()
            questions_path = temp_root / 'questions.json'
            answers_path = sensitive_dir / 'answers.json'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')
            answers_path.write_text(json.dumps(answers), encoding='utf-8')
            original_read_text = Path.read_text

            def read_text_side_effect(self, *args, **kwargs):
                if self == answers_path:
                    raise OSError('D:/Privado/Socio Controlado Uno 11111111-1/answers.json')
                return original_read_text(self, *args, **kwargs)

            with patch.object(Path, 'read_text', autospec=True, side_effect=read_text_side_effect):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_company_accounting_responsible_answers',
                        questions_packet=str(questions_path),
                        answers=str(answers_path),
                        output_dir=str(temp_root / 'answers-review'),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo leer answers JSON.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_template_command_rejects_repo_output_outside_local_evidence(self):
        packet = self._questions_packet()
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)
            questions_path = repo_root / 'questions.json'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'materialize_company_accounting_responsible_answers_template',
                        questions_packet=str(questions_path),
                        output_dir=str(docs_dir / 'answers-template'),
                        stdout=StringIO(),
                    )

    def test_template_command_write_error_does_not_echo_sensitive_path(self):
        packet = self._questions_packet()
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            questions_path = temp_root / 'questions.json'
            output_dir = temp_root / 'Socio Controlado Uno 11111111-1'
            questions_path.write_text(json.dumps(packet), encoding='utf-8')

            with patch.object(
                Path,
                'write_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/answers-template.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_company_accounting_responsible_answers_template',
                        questions_packet=str(questions_path),
                        output_dir=str(output_dir),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo escribir template de respuestas responsables.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_template_command_missing_questions_path_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            sensitive_dir = temp_root / 'Socio Controlado Uno 11111111-1'
            sensitive_dir.mkdir()
            questions_path = sensitive_dir / 'missing-questions.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_responsible_answers_template',
                    questions_packet=str(questions_path),
                    output_dir=str(temp_root / 'answers-template'),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No existe questions_packet JSON o no es un archivo legible.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn(str(sensitive_dir), rendered_error)

    def test_review_presence_audit_reports_missing_review_without_manual_path(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            (repo_root / 'local-evidence').mkdir(parents=True)
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command('audit_company_accounting_responsible_answers_review_presence', stdout=stdout)

            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_DISCOVERY_SCHEMA_VERSION)
            self.assertEqual(summary['summary']['candidates_total'], 0)
            self.assertFalse(summary['summary']['ready_for_responsible_decision_handoff'])
            self.assertIn('responsible_answers.review_missing', summary['issue_codes'])
            self.assertFalse(summary['search']['raw_paths_returned'])

    def test_review_presence_audit_finds_ready_review_without_returning_path(self):
        packet = self._questions_packet_with_readiness_source()
        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=self._answers_payload(packet),
        )
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            sensitive_dir = repo_root / 'local-evidence' / 'Socio Controlado Uno 11111111-1'
            sensitive_dir.mkdir(parents=True)
            (sensitive_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).write_text(
                json.dumps(review),
                encoding='utf-8',
            )
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command('audit_company_accounting_responsible_answers_review_presence', stdout=stdout)

            audit = json.loads(stdout.getvalue())
            rendered = json.dumps(audit, ensure_ascii=True)
            self.assertEqual(audit['summary']['candidates_total'], 1)
            self.assertEqual(audit['summary']['ready_candidates_total'], 1)
            self.assertTrue(audit['summary']['ready_for_responsible_decision_handoff'])
            self.assertTrue(audit['candidates'][0]['ready_for_responsible_decision_handoff'])
            self.assertTrue(audit['candidates'][0]['path_hash'])
            self.assertEqual(audit['candidates'][0]['readiness_sources_total'], 1)
            self.assertFalse(
                audit['candidates'][0]['question_source_summaries'][0]['ready_flags'][
                    'ready_for_formal_bank_support_review'
                ]
            )
            self.assertNotIn('Socio Controlado Uno', rendered)
            self.assertNotIn('11111111-1', rendered)
            self.assertNotIn(str(sensitive_dir), rendered)

    def test_review_presence_audit_derives_not_ready_from_forged_review_summary(self):
        packet = self._questions_packet()
        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=self._answers_payload(packet),
        )
        review['summary']['ready_for_responsible_decision_handoff'] = True
        review['summary']['missing_questions_total'] = 1
        review['summary']['blocking_issues_total'] = 0
        review['missing_question_keys'] = ['ownership.source-ref']
        review['issues'] = []
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            output_path = repo_root / 'local-evidence' / 'audit' / 'responsible-review-discovery.json'
            review_dir = repo_root / 'local-evidence' / 'responsible-review'
            review_dir.mkdir(parents=True)
            (review_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).write_text(
                json.dumps(review),
                encoding='utf-8',
            )
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command(
                    'audit_company_accounting_responsible_answers_review_presence',
                    output=str(output_path),
                    stdout=stdout,
                )

            audit = json.loads(stdout.getvalue())
            written = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertFalse(audit['summary']['ready_for_responsible_decision_handoff'])
            self.assertEqual(audit['candidates'][0]['missing_questions_total'], 1)
            self.assertIn('responsible_answers.questions_unanswered', audit['candidates'][0]['issue_codes'])
            self.assertEqual(written['summary'], audit['summary'])

    def test_review_presence_command_rejects_search_root_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'audit_company_accounting_responsible_answers_review_presence',
                        search_root=str(docs_dir),
                        stdout=StringIO(),
                    )

    def test_handoff_preflight_reports_missing_artifacts_without_manual_path(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            (repo_root / 'local-evidence').mkdir(parents=True)
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command('audit_company_accounting_responsible_handoff_preflight', stdout=stdout)

            audit = json.loads(stdout.getvalue())
            self.assertEqual(audit['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PREFLIGHT_SCHEMA_VERSION)
            self.assertEqual(audit['summary']['questions_candidates_total'], 0)
            self.assertEqual(audit['summary']['template_candidates_total'], 0)
            self.assertEqual(audit['summary']['review_candidates_total'], 0)
            self.assertFalse(audit['summary']['ready_for_responsible_answer_completion'])
            self.assertFalse(audit['summary']['ready_for_responsible_decision_handoff'])
            self.assertIn('responsible_handoff.questions_missing', audit['issue_codes'])
            self.assertIn('responsible_handoff.template_missing', audit['issue_codes'])
            self.assertIn('responsible_answers.review_missing', audit['issue_codes'])
            self.assertFalse(audit['search']['raw_paths_returned'])

    def test_builds_handoff_packet_from_questions_and_template(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )

        manifest = build_company_accounting_responsible_handoff_packet(
            questions_packet=packet,
            answers_template=template,
        )
        rendered = json.dumps(manifest, ensure_ascii=True)

        self.assertEqual(manifest['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_SCHEMA_VERSION)
        self.assertEqual(manifest['manifest_files']['handoff_packet'], COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST)
        self.assertEqual(manifest['manifest_files']['questions_packet'], COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST)
        self.assertEqual(
            manifest['manifest_files']['answers_template'],
            COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
        )
        self.assertEqual(manifest['summary']['questions_total'], len(packet['questions']))
        self.assertEqual(manifest['summary']['answers_total'], len(packet['questions']))
        self.assertEqual(manifest['summary']['pending_answers_total'], len(packet['questions']))
        self.assertTrue(manifest['summary']['ready_for_responsible_answer_completion'])
        self.assertFalse(manifest['summary']['ready_for_responsible_decision_handoff'])
        self.assertFalse(manifest['summary']['ready_for_productive_accounting_review'])
        self.assertFalse(manifest['summary']['final_tax_calculation'])
        self.assertFalse(manifest['summary']['sii_submission'])
        self.assertEqual(manifest['issue_codes'], ['responsible_handoff.review_pending'])
        self.assertTrue(manifest['package_hash'])
        self.assertNotIn('answer_text', rendered)
        self.assertNotIn('D:\\', rendered)

    def test_handoff_packet_preserves_question_readiness_source_summaries(self):
        packet = self._questions_packet()
        packet['source_summaries'] = [
            {
                'label': 'company_review_package',
                'schema_version': 'company-accounting-review-package.v1',
                'classification': 'parcial',
                'ready_flags': {
                    'ready_for_formal_bank_support_review': False,
                    'document_intake_ready_for_productive_review': False,
                    'document_intake_ready_for_formal_bank_support_manifest': True,
                    'D:/Privado/Socio Controlado Uno 11111111-1': True,
                },
                'issues_total': 2,
                'safe_issue_codes': [
                    {
                        'code': 'company_accounting.responsible_review_missing',
                        'severity': 'blocking',
                    },
                    {
                        'code': 'D:/Privado/Socio Controlado Uno 11111111-1',
                        'severity': 'https://review.example.test/token=secret',
                    },
                ],
                'source_hash': 'a' * 64,
            }
        ]
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )

        manifest = build_company_accounting_responsible_handoff_packet(
            questions_packet=packet,
            answers_template=template,
        )
        rendered = json.dumps(manifest, ensure_ascii=True)
        source_summary = manifest['artifacts']['questions_packet']['source_summaries'][0]
        ready_flags = source_summary['ready_flags']
        safe_issue_codes = source_summary['safe_issue_codes']

        self.assertEqual(manifest['summary']['readiness_sources_total'], 1)
        self.assertEqual(manifest['artifacts']['questions_packet']['readiness_sources_total'], 1)
        self.assertFalse(ready_flags['ready_for_formal_bank_support_review'])
        self.assertFalse(ready_flags['document_intake_ready_for_productive_review'])
        self.assertTrue(ready_flags['document_intake_ready_for_formal_bank_support_manifest'])
        self.assertIn(
            {'code': 'company_accounting.responsible_review_missing', 'severity': 'blocking'},
            safe_issue_codes,
        )
        self.assertIn({'code': 'redacted-issue-code', 'severity': 'blocking'}, safe_issue_codes)
        self.assertNotIn('D:/Privado/Socio Controlado Uno 11111111-1', ready_flags)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('D:/Privado', rendered)

    def test_handoff_packet_rejects_inconsistent_template(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(questions_packet=packet)
        template['answers'] = template['answers'][:-1]

        with self.assertRaises(ValueError):
            build_company_accounting_responsible_handoff_packet(
                questions_packet=packet,
                answers_template=template,
            )

    def test_handoff_packet_command_materializes_and_verifies_without_paths(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            sensitive_dir = repo_root / 'local-evidence' / 'Socio Controlado Uno 11111111-1'
            input_dir = sensitive_dir / 'inputs'
            output_dir = repo_root / 'local-evidence' / 'stage6' / 'responsible-handoff-packets' / 'packet-1'
            input_dir.mkdir(parents=True)
            (input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).write_text(
                json.dumps(packet),
                encoding='utf-8',
            )
            (input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).write_text(
                json.dumps(template),
                encoding='utf-8',
            )
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command(
                    'materialize_company_accounting_responsible_handoff_packet',
                    questions_packet=str(input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST),
                    answers_template=str(input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST),
                    output_dir=str(output_dir),
                    stdout=stdout,
                )

            summary = json.loads(stdout.getvalue())
            rendered = json.dumps(summary, ensure_ascii=True)
            written_files = sorted(path.name for path in output_dir.iterdir())
            verification = verify_company_accounting_responsible_handoff_packet(package_dir=output_dir)

            self.assertEqual(summary['schema_version'], COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_SCHEMA_VERSION)
            self.assertTrue(summary['materialized'])
            self.assertTrue(summary['verified'])
            self.assertEqual(summary['manifest_file'], COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST)
            self.assertEqual(summary['questions_file'], COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST)
            self.assertEqual(summary['answers_template_file'], COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST)
            self.assertTrue(summary['ready_for_responsible_answer_completion'])
            self.assertFalse(summary['ready_for_responsible_decision_handoff'])
            self.assertFalse(summary['raw_paths_returned'])
            self.assertEqual(verification['summary']['questions_total'], len(packet['questions']))
            self.assertEqual(summary['readiness_sources_total'], len(packet['source_summaries']))
            self.assertEqual(
                len(verification['question_source_summaries']),
                len(packet['source_summaries']),
            )
            self.assertEqual(
                written_files,
                sorted(
                    [
                        COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
                        COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
                        COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
                    ]
                ),
            )
            self.assertNotIn('Socio Controlado Uno', rendered)
            self.assertNotIn('11111111-1', rendered)
            self.assertNotIn(str(input_dir), rendered)

    def test_handoff_packet_command_rejects_repo_output_outside_local_evidence(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(questions_packet=packet)
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            input_dir = repo_root / 'local-evidence' / 'inputs'
            input_dir.mkdir(parents=True)
            (input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).write_text(
                json.dumps(packet),
                encoding='utf-8',
            )
            (input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).write_text(
                json.dumps(template),
                encoding='utf-8',
            )
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'materialize_company_accounting_responsible_handoff_packet',
                        questions_packet=str(input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST),
                        answers_template=str(input_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST),
                        output_dir=str(docs_dir / 'packet'),
                        stdout=StringIO(),
                    )

    def test_handoff_preflight_finds_questions_and_template_without_returning_paths(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            sensitive_dir = repo_root / 'local-evidence' / 'Socio Controlado Uno 11111111-1'
            questions_dir = sensitive_dir / 'questions'
            template_dir = sensitive_dir / 'template'
            questions_dir.mkdir(parents=True)
            template_dir.mkdir(parents=True)
            (questions_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).write_text(
                json.dumps(packet),
                encoding='utf-8',
            )
            (template_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).write_text(
                json.dumps(template),
                encoding='utf-8',
            )
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command(
                    'audit_company_accounting_responsible_handoff_preflight',
                    require_answer_template_ready=True,
                    stdout=stdout,
                )

            audit = json.loads(stdout.getvalue())
            rendered = json.dumps(audit, ensure_ascii=True)
            self.assertEqual(audit['summary']['questions_candidates_total'], 1)
            self.assertEqual(audit['summary']['ready_question_packets_total'], 1)
            self.assertEqual(audit['summary']['template_candidates_total'], 1)
            self.assertEqual(audit['summary']['ready_answer_templates_total'], 1)
            self.assertTrue(audit['summary']['ready_for_responsible_answer_completion'])
            self.assertFalse(audit['summary']['ready_for_responsible_decision_handoff'])
            self.assertIn('responsible_handoff.review_pending', audit['issue_codes'])
            self.assertIn('responsible_answers.review_missing', audit['issue_codes'])
            self.assertTrue(audit['questions']['candidates'][0]['path_hash'])
            self.assertTrue(audit['answer_templates']['candidates'][0]['path_hash'])
            self.assertEqual(
                audit['questions']['candidates'][0]['readiness_sources_total'],
                len(packet['source_summaries']),
            )
            self.assertEqual(
                len(audit['questions']['candidates'][0]['source_summaries']),
                len(packet['source_summaries']),
            )
            preflight_issue_codes = {
                issue['code']
                for source_summary in audit['questions']['candidates'][0]['source_summaries']
                for issue in source_summary['safe_issue_codes']
            }
            self.assertIn(
                'company_bank_support.bank_confirmation_missing',
                preflight_issue_codes,
            )
            self.assertNotIn('Socio Controlado Uno', rendered)
            self.assertNotIn('11111111-1', rendered)
            self.assertNotIn(str(sensitive_dir), rendered)

    def test_handoff_preflight_dedupes_materialized_packet_copies(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(
            questions_packet=packet,
            next_action_ref='complete-ac2025-at2026-responsible-review',
        )
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            sensitive_dir = repo_root / 'local-evidence' / 'Socio Controlado Uno 11111111-1'
            questions_dir = sensitive_dir / 'questions'
            template_dir = sensitive_dir / 'template'
            packet_dir = sensitive_dir / 'handoff-packet'
            questions_dir.mkdir(parents=True)
            template_dir.mkdir(parents=True)
            (questions_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).write_text(
                json.dumps(packet),
                encoding='utf-8',
            )
            (template_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).write_text(
                json.dumps(template),
                encoding='utf-8',
            )
            write_company_accounting_responsible_handoff_packet(
                questions_packet=packet,
                answers_template=template,
                output_dir=packet_dir,
            )
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command(
                    'audit_company_accounting_responsible_handoff_preflight',
                    require_answer_template_ready=True,
                    stdout=stdout,
                )

            audit = json.loads(stdout.getvalue())
            rendered = json.dumps(audit, ensure_ascii=True)
            self.assertEqual(audit['summary']['questions_candidates_total'], 2)
            self.assertEqual(audit['summary']['template_candidates_total'], 2)
            self.assertEqual(audit['summary']['ready_question_packets_total'], 1)
            self.assertEqual(audit['summary']['ready_answer_templates_total'], 1)
            self.assertEqual(audit['summary']['duplicate_ready_question_packets_total'], 1)
            self.assertEqual(audit['summary']['duplicate_ready_answer_templates_total'], 1)
            self.assertTrue(audit['summary']['ready_for_responsible_answer_completion'])
            self.assertNotIn('responsible_handoff.multiple_ready_question_packets', audit['issue_codes'])
            self.assertNotIn('responsible_handoff.multiple_ready_answer_templates', audit['issue_codes'])
            self.assertIn('responsible_handoff.review_pending', audit['issue_codes'])
            self.assertNotIn('Socio Controlado Uno', rendered)
            self.assertNotIn('11111111-1', rendered)
            self.assertNotIn(str(sensitive_dir), rendered)

    def test_handoff_preflight_reports_ready_review_without_answer_completion(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(questions_packet=packet)
        review = validate_company_accounting_responsible_answers(
            questions_packet=packet,
            answers_payload=self._answers_payload(packet),
        )
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            local_root = repo_root / 'local-evidence' / 'responsible'
            questions_dir = local_root / 'questions'
            template_dir = local_root / 'template'
            review_dir = local_root / 'review'
            questions_dir.mkdir(parents=True)
            template_dir.mkdir(parents=True)
            review_dir.mkdir(parents=True)
            (questions_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).write_text(
                json.dumps(packet),
                encoding='utf-8',
            )
            (template_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).write_text(
                json.dumps(template),
                encoding='utf-8',
            )
            (review_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST).write_text(
                json.dumps(review),
                encoding='utf-8',
            )
            output_path = repo_root / 'local-evidence' / 'audit' / 'responsible-handoff-preflight.json'
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command(
                    'audit_company_accounting_responsible_handoff_preflight',
                    output=str(output_path),
                    require_review_ready=True,
                    stdout=stdout,
                )

            audit = json.loads(stdout.getvalue())
            written = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertTrue(audit['summary']['ready_for_responsible_decision_handoff'])
            self.assertFalse(audit['summary']['ready_for_responsible_answer_completion'])
            self.assertEqual(audit['summary']['ready_review_candidates_total'], 1)
            self.assertEqual(written['summary'], audit['summary'])

    def test_handoff_preflight_rejects_forged_template_counts(self):
        packet = self._questions_packet()
        template = build_company_accounting_responsible_answers_template(questions_packet=packet)
        template['answers'] = []
        template['template_summary']['answers_total'] = len(packet['questions'])
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            local_root = repo_root / 'local-evidence' / 'responsible'
            questions_dir = local_root / 'questions'
            template_dir = local_root / 'template'
            questions_dir.mkdir(parents=True)
            template_dir.mkdir(parents=True)
            (questions_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST).write_text(
                json.dumps(packet),
                encoding='utf-8',
            )
            (template_dir / COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST).write_text(
                json.dumps(template),
                encoding='utf-8',
            )
            stdout = StringIO()

            with override_settings(PROJECT_ROOT=str(repo_root)):
                call_command('audit_company_accounting_responsible_handoff_preflight', stdout=stdout)

            audit = json.loads(stdout.getvalue())
            self.assertFalse(audit['summary']['ready_for_responsible_answer_completion'])
            self.assertEqual(audit['summary']['ready_answer_templates_total'], 0)
            self.assertIn(
                'responsible_handoff.template_answer_count_mismatch',
                audit['answer_templates']['candidates'][0]['issue_codes'],
            )

    def test_handoff_preflight_command_rejects_search_root_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'audit_company_accounting_responsible_handoff_preflight',
                        search_root=str(docs_dir),
                        stdout=StringIO(),
                    )
