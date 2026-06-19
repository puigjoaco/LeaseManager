import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_ownership_patch_validator import (
    OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
    validate_annual_tax_ownership_patch,
)
from core.annual_tax_ownership_review_checklist import (
    OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION,
    OWNERSHIP_VISUAL_INDEX_SCHEMA_VERSION,
    build_annual_tax_ownership_review_checklist,
)
from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION
from core.annual_tax_ownership_visual_review_packet import OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION


class AnnualTaxOwnershipReviewChecklistTests(SimpleTestCase):
    def _template(self) -> dict:
        return {
            'schema_version': OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
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
                'source_ref': 'ownership-review-2024-controlled',
                'as_of': '2024-12-31',
                'participants': [],
            },
        }

    def _visual_packet(self) -> dict:
        return {
            'schema_version': OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION,
            'items': [
                {
                    'path_ref': 'legal/Socio Controlado Uno/constitucion.pdf',
                    'rendered_pages': [
                        {
                            'page': 1,
                            'file_name': 'candidate-page-01.png',
                            'sha256': 'c' * 64,
                        }
                    ],
                }
            ],
        }

    def _visual_index(self) -> dict:
        return {
            'schema_version': OWNERSHIP_VISUAL_INDEX_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'records': [
                {
                    'path_ref': 'legal/Socio Controlado Uno/constitucion.pdf',
                    'relative_path_tail_redacted': 'socios/constitucion-sensible.pdf',
                    'rendered_pages': [
                        'candidate_01_page-01.png',
                        'candidate_01_page-02.png',
                    ],
                }
            ],
        }

    def _valid_patch(self) -> dict:
        return {
            'schema_version': OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
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

    def test_pending_checklist_tracks_missing_participants_without_source_paths(self):
        validation = validate_annual_tax_ownership_patch(
            template=self._template(),
            patch={
                'schema_version': OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
                'company_ref': 'inmobiliaria-puig',
                'commercial_year': 2024,
                'tax_year': 2025,
                'ownership': {
                    'source_ref': 'ownership-structure-2024-controlled',
                    'as_of': '2024-12-31',
                    'participants': [],
                },
            },
        )
        result = build_annual_tax_ownership_review_checklist(
            template=self._template(),
            validation=validation,
            visual_packet=self._visual_packet(),
        )
        rendered = json.dumps(result, ensure_ascii=True)
        item_by_key = {item['key']: item for item in result['checklist_items']}

        self.assertEqual(result['schema_version'], OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION)
        self.assertFalse(result['summary']['ready_for_controlled_db_load'])
        self.assertEqual(result['summary']['reviewable_candidates_total'], 1)
        self.assertEqual(result['summary']['rendered_candidates_total'], 1)
        self.assertEqual(item_by_key['participants_completed_from_legal_review']['status'], 'pending')
        self.assertIn('$.ownership.participants', item_by_key['participants_completed_from_legal_review']['blocking_paths'])
        self.assertTrue(result['safety']['stores_source_paths'] is False)
        self.assertNotIn('legal/Socio Controlado Uno/constitucion.pdf', rendered)
        self.assertNotIn('Socio Controlado Uno', rendered)

    def test_checklist_counts_existing_visual_index_without_leaking_paths(self):
        result = build_annual_tax_ownership_review_checklist(
            template=self._template(),
            visual_packet=self._visual_index(),
        )
        rendered = json.dumps(result, ensure_ascii=True)

        self.assertEqual(result['summary']['reviewable_candidates_total'], 1)
        self.assertEqual(result['summary']['rendered_candidates_total'], 1)
        self.assertEqual(result['candidate_review_queue'][0]['rendered_pages_count'], 2)
        self.assertFalse(result['summary']['ready_for_controlled_db_load'])
        self.assertNotIn('legal/Socio Controlado Uno/constitucion.pdf', rendered)
        self.assertNotIn('socios/constitucion-sensible.pdf', rendered)
        self.assertNotIn('candidate_01_page-01.png', rendered)

    def test_ready_checklist_uses_redacted_validation_without_names_or_ruts(self):
        validation = validate_annual_tax_ownership_patch(
            template=self._template(),
            patch=self._valid_patch(),
        )
        result = build_annual_tax_ownership_review_checklist(
            template=self._template(),
            validation=validation,
            visual_packet=self._visual_packet(),
        )
        rendered = json.dumps(result, ensure_ascii=True)

        self.assertTrue(result['summary']['ready_for_controlled_db_load'])
        self.assertEqual(result['summary']['participants_count'], 2)
        self.assertEqual(result['summary']['percentage_total'], '100.00')
        self.assertEqual(result['summary']['blocking_items_total'], 0)
        self.assertNotIn('Socio Controlado Uno', rendered)
        self.assertNotIn('Socio Controlado Dos', rendered)
        self.assertNotIn('11111111-1', rendered)
        self.assertNotIn('22222222-2', rendered)

    def test_command_outputs_checklist_and_rejects_versioned_output(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            template_path = temp_root / 'ownership-template.json'
            validation_path = temp_root / 'ownership-validation.json'
            visual_path = temp_root / 'ownership-visual-index.json'
            output_path = temp_root / 'ownership-checklist.json'
            template = self._template()
            validation = validate_annual_tax_ownership_patch(
                template=template,
                patch=self._valid_patch(),
            )
            template_path.write_text(json.dumps(template), encoding='utf-8')
            validation_path.write_text(json.dumps(validation), encoding='utf-8')
            visual_path.write_text(json.dumps(self._visual_index()), encoding='utf-8')

            stdout = StringIO()
            call_command(
                'build_annual_tax_ownership_review_checklist',
                template=str(template_path),
                validation=str(validation_path),
                visual_packet=str(visual_path),
                output=str(output_path),
                stdout=stdout,
            )

            result = json.loads(output_path.read_text(encoding='utf-8'))
            self.assertEqual(result['schema_version'], OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION)
            self.assertTrue(result['summary']['ready_for_controlled_db_load'])
            self.assertEqual(result['summary']['rendered_candidates_total'], 1)
            self.assertEqual(result['candidate_review_queue'][0]['rendered_pages_count'], 2)

            blocked_output = Path.cwd() / 'docs' / 'ownership-review-checklist.json'
            with self.assertRaises(CommandError):
                call_command(
                    'build_annual_tax_ownership_review_checklist',
                    template=str(template_path),
                    output=str(blocked_output),
                    stdout=StringIO(),
                )
