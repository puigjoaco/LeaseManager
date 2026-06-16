import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_ownership_candidate_review import review_annual_tax_ownership_candidates
from core.annual_tax_ownership_visual_review_packet import build_annual_tax_ownership_visual_review_packet
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxOwnershipVisualReviewPacketTests(SimpleTestCase):
    def _write_bytes(self, root: Path, relative_path: str, content: bytes = b'%PDF-test') -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def _manifest_and_review(self, source_root: Path) -> tuple[dict, dict]:
        manifest = build_annual_tax_source_manifest(
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )
        review = review_annual_tax_ownership_candidates(
            manifest=manifest,
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )
        return manifest, review

    def test_visual_packet_indexes_rendered_pages_without_raw_text_or_paths(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / 'source'
            output_dir = temp_root / 'local-evidence' / 'ownership-pages'
            self._write_bytes(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/4.Inscripcion/Inscripcion.pdf',
            )
            manifest, review = self._manifest_and_review(source_root)

            with patch(
                'core.annual_tax_ownership_visual_review_packet._render_pdf_pages',
                return_value=[{'page': 1, 'file_name': 'candidate-01-page-01.png', 'sha256': 'a' * 64, 'size_bytes': 123}],
            ):
                packet = build_annual_tax_ownership_visual_review_packet(
                    manifest=manifest,
                    review=review,
                    source_root=source_root,
                    output_dir=output_dir,
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    tax_year=2025,
                    max_pages_per_candidate=1,
                    resolution=120,
                )

        rendered = json.dumps(packet, ensure_ascii=True)

        self.assertEqual(packet['schema_version'], 'annual-tax-ownership-visual-review-packet.v1')
        self.assertEqual(packet['summary']['reviewable_candidates_total'], 1)
        self.assertEqual(packet['summary']['rendered_pages_total'], 1)
        self.assertTrue(packet['summary']['ready_for_manual_visual_review'])
        self.assertFalse(packet['summary']['ready_for_controlled_db_load'])
        self.assertTrue(packet['safety']['rendered_images_may_contain_sensitive_data'])
        self.assertFalse(packet['safety']['stores_raw_text'])
        self.assertNotIn(str(source_root), rendered)
        self.assertNotIn('Inmobiliaria Puig SpA', rendered)

    def test_command_refuses_visual_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._write_bytes(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/4.Inscripcion/Inscripcion.pdf',
            )
            manifest, review = self._manifest_and_review(source_root)
            manifest_path = Path(temp_dir) / 'manifest.json'
            review_path = Path(temp_dir) / 'review.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            review_path.write_text(json.dumps(review), encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'build_annual_tax_ownership_visual_review_packet',
                    manifest=str(manifest_path),
                    review=str(review_path),
                    source_root=str(source_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    output_dir='docs/ownership-pages',
                    output='docs/ownership-pages/index.json',
                )
