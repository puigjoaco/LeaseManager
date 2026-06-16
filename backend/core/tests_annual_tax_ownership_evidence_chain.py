import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class AnnualTaxOwnershipEvidenceChainCommandTests(SimpleTestCase):
    def _write(self, root: Path, relative_path: str, content: str = 'controlled-test-source') -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def test_command_writes_safe_chain_under_local_evidence(self):
        local_evidence = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence.mkdir(exist_ok=True)
        with TemporaryDirectory() as temp_dir, TemporaryDirectory(dir=local_evidence) as output_dir:
            source_root = Path(temp_dir) / 'source'
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/2.Extracto/Extracto.txt',
                'Inmobiliaria Puig SpA sociedad por acciones. Capital social 1000. '
                'Accionistas con RUT 11.111.111-1 y participaciones al ano 2024.',
            )
            stdout = StringIO()

            call_command(
                'build_annual_tax_ownership_evidence_chain',
                source_root=str(source_root),
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                output_dir=output_dir,
                run_label='test',
                skip_visual_review_packet=True,
                stdout=stdout,
            )

            summary = json.loads(stdout.getvalue())
            rendered = json.dumps(summary, ensure_ascii=True)
            artifact_paths = {
                key: Path(settings.PROJECT_ROOT) / value
                for key, value in summary['artifacts'].items()
            }
            manifest = json.loads(artifact_paths['manifest'].read_text(encoding='utf-8'))
            review = json.loads(artifact_paths['ownership_candidate_review'].read_text(encoding='utf-8'))
            template = json.loads(artifact_paths['ownership_snapshot_template'].read_text(encoding='utf-8'))

        self.assertEqual(summary['schema_version'], 'annual-tax-ownership-evidence-chain.v1')
        self.assertEqual(manifest['schema_version'], 'annual-tax-source-manifest.v1')
        self.assertEqual(review['schema_version'], 'annual-tax-ownership-candidate-review.v1')
        self.assertEqual(template['schema_version'], 'annual-tax-ownership-snapshot-template.v1')
        self.assertTrue(summary['summary']['ownership_source_candidate_present'])
        self.assertEqual(summary['summary']['candidate_files_total'], 1)
        self.assertEqual(summary['summary']['reviewable_candidates_total'], 1)
        self.assertFalse(summary['summary']['ready_for_controlled_db_load'])
        self.assertFalse(summary['summary']['visual_packet_generated'])
        self.assertFalse(summary['safety']['writes_database'])
        self.assertFalse(summary['safety']['stores_raw_text'])
        self.assertNotIn('11.111.111-1', rendered)
        self.assertNotIn('Accionistas con RUT', rendered)

    def test_command_refuses_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'build_annual_tax_ownership_evidence_chain',
                    source_root=str(source_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    output_dir='docs/ownership-chain',
                    skip_visual_review_packet=True,
                )
