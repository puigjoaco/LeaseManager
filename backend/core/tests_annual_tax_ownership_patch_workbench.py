import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

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
            output_dir = temp_root / 'workbench'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            checklist_path.write_text(json.dumps(self._checklist()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'materialize_annual_tax_ownership_patch_workbench',
                template=str(template_path),
                checklist=str(checklist_path),
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
            self.assertEqual(manifest['summary']['rendered_candidates_total'], 10)
            self.assertEqual(patch_draft['ownership']['participants'], [])
            self.assertNotIn('Socio Controlado Uno', rendered_summary)
            self.assertNotIn('11111111-1', rendered_summary)

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

    def test_checklist_context_must_match_template(self):
        checklist = self._checklist()
        checklist['tax_year'] = 2027

        with self.assertRaisesMessage(ValueError, 'tax_year'):
            build_annual_tax_ownership_patch_workbench(
                template=self._template(),
                checklist=checklist,
            )
