import json
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

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

    def test_visual_packet_rejects_control_sensitive_refs_without_echoing_values(self):
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

            cases = (
                (
                    'company_ref',
                    {'company_ref': 'inmobiliaria_11.111.111-1'},
                    '11.111.111-1',
                ),
                (
                    'review_path_ref',
                    {
                        'review': {
                            **review,
                            'review_items': [
                                {
                                    **review['review_items'][0],
                                    'path_ref': 'candidate_C:/Privado/accionistas.pdf',
                                }
                            ],
                        }
                    },
                    'C:/Privado',
                ),
                (
                    'manifest_path_ref',
                    {
                        'manifest': {
                            **manifest,
                            'files': [
                                {
                                    **manifest['files'][0],
                                    'path_ref': r'candidate_\\server\share\accionistas.pdf',
                                }
                            ],
                        }
                    },
                    r'\\server\share',
                ),
            )
            for label, overrides, sensitive_fragment in cases:
                with self.subTest(label=label):
                    kwargs = {
                        'manifest': overrides.get('manifest', manifest),
                        'review': overrides.get('review', review),
                        'source_root': source_root,
                        'output_dir': output_dir,
                        'company_ref': 'inmobiliaria-puig',
                        'commercial_year': 2024,
                        'tax_year': 2025,
                    }
                    kwargs.update({key: value for key, value in overrides.items() if key not in {'manifest', 'review'}})

                    with self.assertRaises(ValueError) as error:
                        build_annual_tax_ownership_visual_review_packet(**kwargs)

                    rendered_error = str(error.exception)
                    self.assertIn('referencia no sensible', rendered_error)
                    self.assertNotIn(sensitive_fragment, rendered_error)

    def test_visual_packet_requires_manifest_review_context_match(self):
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
            mismatched_review = {**review, 'commercial_year': 2023}

            with self.assertRaisesMessage(ValueError, 'review.commercial_year no coincide'):
                build_annual_tax_ownership_visual_review_packet(
                    manifest=manifest,
                    review=mismatched_review,
                    source_root=source_root,
                    output_dir=output_dir,
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    tax_year=2025,
                )

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

    def test_command_errors_do_not_echo_sensitive_paths_or_refs(self):
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / 'source'
            source_root.mkdir()
            sensitive_manifest = temp_root / 'Socio Controlado Uno 11.111.111-1.json'
            review_path = temp_root / 'review.json'
            review_path.write_text('{}', encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(temp_root)):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'build_annual_tax_ownership_visual_review_packet',
                        manifest=str(sensitive_manifest),
                        review=str(review_path),
                        source_root=str(source_root),
                        company_ref='inmobiliaria-puig',
                        commercial_year=2024,
                        output_dir=str(temp_root / 'local-evidence' / 'ownership-pages'),
                        output=str(temp_root / 'local-evidence' / 'ownership-pages' / 'index.json'),
                    )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11.111.111-1', rendered_error)

        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / 'source'
            self._write_bytes(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/4.Inscripcion/Inscripcion.pdf',
            )
            manifest, review = self._manifest_and_review(source_root)
            manifest_path = temp_root / 'manifest.json'
            review_path = temp_root / 'review.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            review_path.write_text(json.dumps(review), encoding='utf-8')
            sensitive_source_root = temp_root / 'Socio Controlado Uno 22.222.222-2'

            with override_settings(PROJECT_ROOT=str(temp_root)):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'build_annual_tax_ownership_visual_review_packet',
                        manifest=str(manifest_path),
                        review=str(review_path),
                        source_root=str(sensitive_source_root),
                        company_ref='inmobiliaria-puig',
                        commercial_year=2024,
                        output_dir=str(temp_root / 'local-evidence' / 'ownership-pages'),
                        output=str(temp_root / 'local-evidence' / 'ownership-pages' / 'index.json'),
                    )

            rendered_error = str(error.exception)
            self.assertIn('source_root no existe', rendered_error)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('22.222.222-2', rendered_error)

        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / 'source'
            self._write_bytes(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/4.Inscripcion/Inscripcion.pdf',
            )
            manifest, review = self._manifest_and_review(source_root)
            review = deepcopy(review)
            review['review_items'][0]['path_ref'] = 'candidate_33.333.333-3'
            manifest_path = temp_root / 'manifest.json'
            review_path = temp_root / 'review.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            review_path.write_text(json.dumps(review), encoding='utf-8')

            with override_settings(PROJECT_ROOT=str(temp_root)):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'build_annual_tax_ownership_visual_review_packet',
                        manifest=str(manifest_path),
                        review=str(review_path),
                        source_root=str(source_root),
                        company_ref='inmobiliaria-puig',
                        commercial_year=2024,
                        output_dir=str(temp_root / 'local-evidence' / 'ownership-pages'),
                        output=str(temp_root / 'local-evidence' / 'ownership-pages' / 'index.json'),
                    )

            rendered_error = str(error.exception)
            self.assertIn('Paquete visual ownership invalido', rendered_error)
            self.assertNotIn('33.333.333-3', rendered_error)
