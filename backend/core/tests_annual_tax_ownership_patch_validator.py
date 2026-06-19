import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.annual_tax_ownership_patch_validator import (
    OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
    OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION,
    validate_annual_tax_ownership_patch,
)
from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION


class AnnualTaxOwnershipPatchValidatorTests(SimpleTestCase):
    def _template(self) -> dict:
        return {
            'schema_version': OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_review_hash': 'a' * 64,
            'responsible_ref': 'codex-controlled-review',
            'approval_ref': 'approval-controlled',
            'safety': {
                'stores_rut_values': False,
                'stores_person_names': False,
            },
            'candidate_sources': [
                {
                    'path_ref': 'file-path-sha256:' + 'b' * 64,
                    'sha256': 'c' * 64,
                    'document_kind': 'constitution_deed',
                    'review_status': 'manual_review_required_legal_candidate',
                    'path_context_tags': ['constitution'],
                    'evidence_ref_suggestion': 'ownership-evidence-' + 'c' * 12,
                    'requires_ocr_or_manual_read': True,
                }
            ],
            'ownership_patch_template': {
                'source_ref': 'ownership-review-2024-controlled',
                'as_of': '2024-12-31',
                'participants': [],
            },
            'decision': {
                'can_patch_controlled_db_load_package_after_manual_completion': True,
                'ready_for_controlled_db_load': False,
            },
        }

    def _valid_patch(self) -> dict:
        return {
            'schema_version': OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'responsible_ref': 'responsable-controlado',
            'approval_ref': 'aprobacion-controlada',
            'ownership': {
                'source_ref': 'ownership-structure-2024-controlled',
                'as_of': '2024-12-31',
                'participants': [
                    {
                        'participant_type': 'socio',
                        'participant_ref': 'socio-controlled-one',
                        'name': 'Socio Controlado Uno',
                        'rut': '11111111-1',
                        'percentage': '60.00',
                        'vigente_desde': '2024-01-01',
                        'vigente_hasta': None,
                        'evidence_ref': 'ownership-evidence-controlled-one',
                    },
                    {
                        'participant_type': 'socio',
                        'participant_ref': 'socio-controlled-two',
                        'name': 'Socio Controlado Dos',
                        'rut': '22222222-2',
                        'percentage': '40.00',
                        'vigente_desde': '2024-01-01',
                        'vigente_hasta': None,
                        'evidence_ref': 'ownership-evidence-controlled-two',
                    },
                ],
            },
        }

    def test_valid_patch_is_ready_without_exposing_names_or_ruts(self):
        result = validate_annual_tax_ownership_patch(
            template=self._template(),
            patch=self._valid_patch(),
        )
        rendered = json.dumps(result, ensure_ascii=True)

        self.assertEqual(result['schema_version'], OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION)
        self.assertTrue(result['ready_for_controlled_db_load'])
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['summary']['participants_count'], 2)
        self.assertEqual(result['summary']['valid_participants_count'], 2)
        self.assertEqual(result['summary']['percentage_total'], '100.00')
        self.assertTrue(result['summary']['percentage_total_is_100'])
        self.assertTrue(result['safety']['outputs_redacted'])
        self.assertFalse(result['safety']['stores_rut_values'])
        self.assertFalse(result['safety']['stores_person_names'])
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('Socio Controlado Dos', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('22222222-2', rendered)

    def test_invalid_patch_reports_safe_paths_without_hashing_sensitive_refs(self):
        patch = self._valid_patch()
        patch['ownership']['participants'][1]['percentage'] = '39.00'
        patch['ownership']['participants'][1]['rut'] = 'rut-malo'
        patch['ownership']['participants'][1]['evidence_ref'] = 'https://secret.example/evidence'

        result = validate_annual_tax_ownership_patch(template=self._template(), patch=patch)
        rendered = json.dumps(result, ensure_ascii=True)

        self.assertFalse(result['ready_for_controlled_db_load'])
        self.assertIn('ownership_patch_sensitive_reference', result['blockers'])
        self.assertIn('ownership_patch_invalid', result['blockers'])
        self.assertIn('$.ownership', result['invalid_paths'])
        self.assertIn('$.ownership.participants', result['invalid_paths'])
        self.assertIn('$.ownership.participants[1].rut', result['invalid_paths'])
        self.assertFalse(result['summary']['percentage_total_is_100'])
        self.assertNotIn('https://secret.example/evidence', rendered)
        self.assertEqual(result['summary']['redacted_participants'][1]['evidence_ref_hash'], '')

    def test_command_outputs_redacted_validation_and_refuses_versioned_patch(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            patch_path = temp_root / 'patch.json'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            patch_path.write_text(json.dumps(self._valid_patch()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'validate_annual_tax_ownership_patch',
                template=str(template_path),
                patch=str(patch_path),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            rendered = json.dumps(result, ensure_ascii=True)
            self.assertTrue(result['ready_for_controlled_db_load'])
            self.assertNotIn('Socio Controlado Uno', rendered)
            self.assertNotIn('11111111-1', rendered)

        with TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / 'repo'
            docs_dir = repo_root / 'docs'
            docs_dir.mkdir(parents=True)
            template_path = repo_root / 'template.json'
            patch_path = docs_dir / 'ownership-patch.json'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            patch_path.write_text(json.dumps(self._valid_patch()), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(repo_root)):
                with self.assertRaisesMessage(CommandError, 'local-evidence'):
                    call_command(
                        'validate_annual_tax_ownership_patch',
                        template=str(template_path),
                        patch=str(patch_path),
                        stdout=StringIO(),
                    )

    def test_command_missing_patch_error_does_not_echo_sensitive_path(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'template.json'
            patch_path = temp_root / 'Socio Controlado Uno 11111111-1.json'
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'validate_annual_tax_ownership_patch',
                    template=str(template_path),
                    patch=str(patch_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
