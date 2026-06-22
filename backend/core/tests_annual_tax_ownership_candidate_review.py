import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_ownership_candidate_review import review_annual_tax_ownership_candidates
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxOwnershipCandidateReviewTests(SimpleTestCase):
    def _write(self, root: Path, relative_path: str, content: str = 'controlled-test-source') -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def _manifest(self, source_root: Path) -> dict:
        return build_annual_tax_source_manifest(
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )

    def test_review_extracts_only_redacted_structural_signals(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/1.Escritura de Constitucion/Escritura.txt',
                'Inmobiliaria Puig SpA sociedad por acciones. Capital social 1000. '
                'Accionistas con RUT 11.111.111-1 y participaciones al ano 2024.',
            )
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/2.NULA - Primera Modificacion/2.Extracto/Extracto.txt',
                'Modificacion nula y sin efecto.',
            )
            manifest = self._manifest(source_root)

            review = review_annual_tax_ownership_candidates(
                manifest=manifest,
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        rendered = json.dumps(review, ensure_ascii=True)
        by_kind = {item['document_kind']: item for item in review['review_items']}

        self.assertEqual(review['summary']['candidate_files_total'], 2)
        self.assertEqual(review['summary']['candidate_for_controlled_snapshot_review_count'], 1)
        self.assertFalse(review['summary']['controlled_snapshot_ready'])
        self.assertFalse(review['summary']['auto_generates_socios_or_percentages'])
        self.assertTrue(review['summary']['requires_manual_controlled_extraction'])
        self.assertEqual(
            by_kind['constitution_deed']['review_status'],
            'candidate_for_controlled_snapshot_review',
        )
        self.assertTrue(by_kind['constitution_deed']['signals']['capital_mentioned'])
        self.assertEqual(by_kind['constitution_deed']['signals']['rut_like_tokens_count'], 1)
        self.assertEqual(
            by_kind['void_modification_support']['review_status'],
            'excluded_void_or_superseded',
        )
        self.assertNotIn('11.111.111-1', rendered)
        self.assertNotIn('Accionistas con RUT', rendered)
        self.assertFalse(review['safety']['stores_raw_text'])
        self.assertFalse(review['safety']['stores_rut_values'])
        self.assertFalse(review['safety']['can_generate_controlled_snapshot_without_review'])

    def test_review_counts_prefixed_rut_like_tokens_without_leaking_values(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/1.Escritura de Constitucion/Escritura.txt',
                'Inmobiliaria Puig SpA sociedad por acciones. Capital social 1000. '
                'Accionistas source_11.111.111-1 y participant_22.222.222-2 con participaciones al ano 2024.',
            )
            manifest = self._manifest(source_root)

            review = review_annual_tax_ownership_candidates(
                manifest=manifest,
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2025,
                tax_year=2026,
            )

        rendered = json.dumps(review, ensure_ascii=True)
        item = review['review_items'][0]

        self.assertEqual(item['signals']['rut_like_tokens_count'], 2)
        self.assertEqual(item['review_status'], 'candidate_for_controlled_snapshot_review')
        self.assertIn('AC2025', review['decision']['reason'])
        self.assertNotIn('source_11.111.111-1', rendered)
        self.assertNotIn('participant_22.222.222-2', rendered)
        self.assertNotIn('11.111.111-1', rendered)
        self.assertNotIn('22.222.222-2', rendered)
        self.assertNotIn('Accionistas', rendered)
        self.assertFalse(review['safety']['stores_raw_text'])
        self.assertFalse(review['safety']['stores_rut_values'])

    def test_review_keeps_unextractable_legal_pdf_as_manual_candidate(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            target = (
                source_root
                / 'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/4.Inscripcion/Inscripcion.pdf'
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'%PDF-unextractable-controlled-test')
            manifest = self._manifest(source_root)

            review = review_annual_tax_ownership_candidates(
                manifest=manifest,
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        self.assertEqual(review['summary']['candidate_files_total'], 1)
        self.assertEqual(review['summary']['candidate_for_controlled_snapshot_review_count'], 0)
        self.assertEqual(review['summary']['manual_review_legal_candidate_count'], 1)
        self.assertTrue(review['summary']['requires_manual_controlled_extraction'])
        self.assertTrue(review['decision']['architecture_can_continue_to_controlled_snapshot'])
        self.assertFalse(review['decision']['architecture_can_close_ownership_source'])
        self.assertEqual(
            review['review_items'][0]['review_status'],
            'manual_review_required_legal_candidate',
        )

    def test_command_outputs_review_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/2.Extracto/Extracto.txt',
                'Inmobiliaria Puig SpA capital acciones 2024.',
            )
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(self._manifest(source_root)), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'review_annual_tax_ownership_candidates',
                manifest=str(manifest_path),
                source_root=str(source_root),
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())

            self.assertEqual(result['schema_version'], 'annual-tax-ownership-candidate-review.v1')
            self.assertEqual(result['summary']['candidate_for_controlled_snapshot_review_count'], 1)
            self.assertFalse(result['decision']['architecture_can_close_ownership_source'])
            self.assertTrue(result['decision']['architecture_can_continue_to_controlled_snapshot'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'review_annual_tax_ownership_candidates',
                    manifest=str(manifest_path),
                    source_root=str(source_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    output='docs/ownership-review.json',
                )

    def test_command_rejects_sensitive_control_refs_without_echoing_values(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/2.Extracto/Extracto.txt',
                'Inmobiliaria Puig SpA capital acciones 2024.',
            )
            manifest = self._manifest(source_root)
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            sensitive_path_ref_manifest = dict(manifest)
            sensitive_path_ref_manifest['files'] = [dict(item) for item in manifest['files']]
            sensitive_path_ref_manifest['files'][0]['path_ref'] = 'file_C:/Privado/ownership.txt'
            sensitive_manifest_path = Path(temp_dir) / 'sensitive-manifest.json'
            sensitive_manifest_path.write_text(json.dumps(sensitive_path_ref_manifest), encoding='utf-8')
            cases = (
                (
                    'company_ref',
                    {'manifest': str(manifest_path), 'company_ref': 'inmobiliaria_11.111.111-1'},
                    '11.111.111-1',
                ),
                (
                    'path_ref',
                    {'manifest': str(sensitive_manifest_path), 'company_ref': 'inmobiliaria-puig'},
                    'C:/Privado',
                ),
            )
            for label, overrides, sensitive_fragment in cases:
                with self.subTest(label=label):
                    kwargs = {
                        'source_root': str(source_root),
                        'commercial_year': 2024,
                        'tax_year': 2025,
                        'stdout': StringIO(),
                    }
                    kwargs.update(overrides)

                    with self.assertRaises(CommandError) as error:
                        call_command('review_annual_tax_ownership_candidates', **kwargs)

                    rendered_error = str(error.exception)
                    self.assertIn('Revision ownership invalida', rendered_error)
                    self.assertNotIn(sensitive_fragment, rendered_error)

    def test_command_redacts_sensitive_manifest_source_and_output_paths_in_errors(self):
        local_evidence = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence.mkdir(exist_ok=True)
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            sensitive_manifest_path = temp_root / 'Socio Controlado Manifest 11.111.111-1.json'
            with self.assertRaises(CommandError) as error:
                call_command(
                    'review_annual_tax_ownership_candidates',
                    manifest=str(sensitive_manifest_path),
                    source_root=str(temp_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('No existe manifest JSON controlado', rendered_error)
            self.assertNotIn('Socio Controlado Manifest', rendered_error)
            self.assertNotIn('11.111.111-1', rendered_error)

        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / 'source'
            source_root.mkdir()
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/2.Extracto/Extracto.txt',
                'Inmobiliaria Puig SpA capital acciones 2024.',
            )
            manifest_path = temp_root / 'manifest.json'
            manifest_path.write_text(json.dumps(self._manifest(source_root)), encoding='utf-8')
            sensitive_source_root = temp_root / 'Socio Controlado Source 22.222.222-2'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'review_annual_tax_ownership_candidates',
                    manifest=str(manifest_path),
                    source_root=str(sensitive_source_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('Revision ownership invalida', rendered_error)
            self.assertNotIn('Socio Controlado Source', rendered_error)
            self.assertNotIn('22.222.222-2', rendered_error)

        with TemporaryDirectory(dir=local_evidence) as temp_dir:
            temp_root = Path(temp_dir)
            source_root = temp_root / 'source'
            source_root.mkdir()
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/2.Extracto/Extracto.txt',
                'Inmobiliaria Puig SpA capital acciones 2024.',
            )
            manifest_path = temp_root / 'manifest.json'
            manifest_path.write_text(json.dumps(self._manifest(source_root)), encoding='utf-8')
            sensitive_output = local_evidence / 'Socio Controlado Output 33.333.333-3' / 'review.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'review_annual_tax_ownership_candidates',
                    manifest=str(manifest_path),
                    source_root=str(source_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    output=str(sensitive_output),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('ruta relativa no sensible', rendered_error)
            self.assertNotIn('Socio Controlado Output', rendered_error)
            self.assertNotIn('33.333.333-3', rendered_error)
