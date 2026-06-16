import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_ownership_candidate_review import review_annual_tax_ownership_candidates
from core.annual_tax_ownership_snapshot_template import build_annual_tax_ownership_snapshot_template
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxOwnershipSnapshotTemplateTests(SimpleTestCase):
    def _write(self, root: Path, relative_path: str, content: str = 'controlled-test-source') -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def _review(self, source_root: Path) -> dict:
        manifest = build_annual_tax_source_manifest(
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )
        return review_annual_tax_ownership_candidates(
            manifest=manifest,
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )

    def test_template_prepares_controlled_ownership_patch_without_sensitive_values(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/1.Escritura de Constitucion/Escritura.txt',
                'Inmobiliaria Puig SpA sociedad por acciones. Capital social. '
                'Accionistas con RUT 11.111.111-1 y participaciones.',
            )
            review = self._review(source_root)

            template = build_annual_tax_ownership_snapshot_template(
                review=review,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                responsible_ref='codex-controlled-review',
            )

        rendered = json.dumps(template, ensure_ascii=True)

        self.assertEqual(template['schema_version'], 'annual-tax-ownership-snapshot-template.v1')
        self.assertEqual(len(template['candidate_sources']), 1)
        self.assertTrue(template['candidate_sources'][0]['evidence_ref_suggestion'].startswith('ownership-evidence-'))
        self.assertEqual(template['ownership_patch_template']['as_of'], '2024-12-31')
        self.assertEqual(template['ownership_patch_template']['participants'], [])
        self.assertEqual(template['participant_template']['participant_type'], 'socio')
        self.assertFalse(template['safety']['ready_for_controlled_db_load'])
        self.assertFalse(template['safety']['auto_generates_socios_or_percentages'])
        self.assertTrue(template['decision']['can_patch_controlled_db_load_package_after_manual_completion'])
        self.assertFalse(template['decision']['ready_for_controlled_db_load'])
        self.assertNotIn('11.111.111-1', rendered)
        self.assertNotIn('Accionistas con RUT', rendered)

    def test_command_outputs_template_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/2.Extracto/Extracto.txt',
                'Inmobiliaria Puig SpA capital acciones 2024.',
            )
            review_path = Path(temp_dir) / 'review.json'
            review_path.write_text(json.dumps(self._review(source_root)), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'build_annual_tax_ownership_snapshot_template',
                review=str(review_path),
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['schema_version'], 'annual-tax-ownership-snapshot-template.v1')
            self.assertEqual(len(result['candidate_sources']), 1)
            self.assertFalse(result['decision']['ready_for_controlled_db_load'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'build_annual_tax_ownership_snapshot_template',
                    review=str(review_path),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    output='docs/ownership-snapshot-template.json',
                )
