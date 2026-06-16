import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_source_manifest import build_annual_tax_source_manifest, payload_hash


class AnnualTaxSourceManifestTests(SimpleTestCase):
    def _write(self, root: Path, relative_path: str, content: str = 'controlled-test-source') -> None:
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    def _build_complete_source_tree(self, root: Path) -> None:
        for month in range(1, 13):
            self._write(
                root,
                f'Ano_2024/06_Respaldos_Tributarios/02_RCV_SII/01_Resumenes/2024-{month:02d}_RCV_Resumen_Compra_Registro.csv',
                'Tipo Documento;Monto Total\nFactura;1000\n',
            )
            self._write(
                root,
                f'Ano_2024/06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-{month:02d}_F29_Comprobante.pdf',
            )
            self._write(
                root,
                f'Ano_2024/02_Libro_Compra/2024-{month:02d}_Libro_Compra.pdf',
            )
            self._write(
                root,
                f'Ano_2024/03_Libro_Venta/2024-{month:02d}_Libro_Venta.pdf',
            )

        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro_Diario_2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro_Mayor_2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Inventario_2024.pdf')
        self._write(root, 'Ano_2024/00_Estructura_Societaria/Participaciones_Socios_2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Balance_General_2024.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Capital Propio.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Determinacion RAI.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Razonabilidad CPT.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Renta Liquida.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Rentas Empresariales.pdf')
        for form in ('1835', '1837', '1847', '1887', '1926', '1948'):
            self._write(root, f'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_{form}_Aceptada.pdf')
        self._write(root, 'Ano_2024/08_F22_Renta_AT_2025/AT_2025_Formulario_22_Compacto.pdf')

    def test_manifest_classifies_sources_and_builds_bundle_draft_without_absolute_paths(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)

            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        rendered = json.dumps(manifest, ensure_ascii=True)
        bundle = manifest['annual_tax_source_bundle_draft']
        resumen = bundle['resumen_fuentes']
        mirror = manifest['mirror_proof_readiness']

        self.assertTrue(manifest['coverage']['ready_for_mirror_source_bundle'])
        self.assertTrue(mirror['source_documentation_confirmed_for_ac2024_at2025'])
        self.assertFalse(mirror['architecture_complete_for_mirror_run'])
        self.assertTrue(mirror['ready_to_start_controlled_processing'])
        self.assertEqual(
            mirror['missing_capabilities'],
            ['expected_output_value_equality_completion'],
        )
        self.assertFalse(mirror['input_policy']['expected_outputs_used_as_inputs'])
        self.assertEqual(manifest['coverage']['rcv_months'], list(range(1, 13)))
        self.assertEqual(manifest['coverage']['f29_months'], list(range(1, 13)))
        self.assertEqual(manifest['coverage']['missing_ddjj_forms'], [])
        self.assertEqual(manifest['coverage']['missing_annual_ledger_keys'], [])
        self.assertTrue(manifest['coverage']['ownership_source_present'])
        self.assertEqual(manifest['coverage']['ownership_source_files_count'], 1)
        self.assertEqual(manifest['coverage']['missing_annual_tax_register_keys'], [])
        self.assertEqual(manifest['summary']['category_counts']['annual_ledger_input'], 3)
        self.assertEqual(manifest['summary']['category_counts']['ownership_source_input'], 1)
        self.assertEqual(manifest['summary']['category_counts']['annual_balance_expected_output'], 1)
        self.assertEqual(manifest['summary']['category_counts']['annual_tax_register_expected_output'], 5)
        self.assertEqual(manifest['summary']['category_counts']['ddjj_expected_output'], 6)
        self.assertEqual(manifest['summary']['category_counts']['f22_expected_output'], 1)
        self.assertEqual(bundle['source_kind'], 'snapshot_controlado')
        self.assertEqual(bundle['estado_sugerido'], 'borrador')
        self.assertEqual(bundle['hash_fuentes'], payload_hash(resumen))
        self.assertEqual(resumen['approved_close_months'], [])
        self.assertFalse(resumen['expected_outputs_used_as_inputs'])
        self.assertIn('annual_ledger_input', resumen['calculation_input_categories'])
        self.assertIn('ownership_source_input', resumen['calculation_input_categories'])
        self.assertIn('annual_balance_expected_output', resumen['comparison_target_categories'])
        self.assertIn('annual_tax_register_expected_output', resumen['comparison_target_categories'])
        self.assertIn('internal_monthly_closes', resumen['manual_review_required'])
        self.assertNotIn(str(source_root), rendered)
        self.assertFalse(manifest['safety']['contains_absolute_source_paths'])
        self.assertFalse(manifest['safety']['copied_source_files'])
        self.assertFalse(manifest['safety']['uses_sii_real'])

    def test_manifest_requires_ownership_source_for_annual_mirror_source_bundle(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            (source_root / 'Ano_2024/00_Estructura_Societaria/Participaciones_Socios_2024.pdf').unlink()

            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        checks = {item['key']: item for item in manifest['coverage']['checks']}
        self.assertFalse(manifest['coverage']['ready_for_mirror_source_bundle'])
        self.assertFalse(manifest['mirror_proof_readiness']['source_documentation_confirmed_for_ac2024_at2025'])
        self.assertFalse(manifest['coverage']['ownership_source_present'])
        self.assertEqual(checks['ownership_source']['status'], 'missing')
        self.assertIn(
            'Completar fuentes AC2024/AT2025 minimas antes de iniciar procesamiento.',
            manifest['mirror_proof_readiness']['next_actions'],
        )

    def test_manifest_marks_legal_ownership_sources_as_candidates_without_unlocking_bundle(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            (source_root / 'Ano_2024/00_Estructura_Societaria/Participaciones_Socios_2024.pdf').unlink()
            self._write(
                source_root,
                'Ano_HISTORICO/08_Base_Legal_Patrimonial_Operativa/Inmobiliaria Puig SpA/'
                '1. Escrituras y Modificaciones/1.Constitucion/1.Escritura de Constitucion/Escritura.pdf',
            )
            self._write(
                source_root,
                'Ano_2024/00_Activos_Propiedades/Providencia/1.Constitucion/Escritura.pdf',
            )

            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        checks = {item['key']: item for item in manifest['coverage']['checks']}
        candidate_files = [
            item for item in manifest['files'] if item['category'] == 'ownership_source_candidate'
        ]
        property_files = [
            item
            for item in manifest['files']
            if item['artifact_key'] == 'unclassified_support'
            and item['relative_path'].endswith('00_Activos_Propiedades/Providencia/1.Constitucion/Escritura.pdf')
        ]

        self.assertFalse(manifest['coverage']['ready_for_mirror_source_bundle'])
        self.assertFalse(manifest['coverage']['ownership_source_present'])
        self.assertTrue(manifest['coverage']['ownership_source_candidate_present'])
        self.assertEqual(manifest['coverage']['ownership_source_candidate_files_count'], 1)
        self.assertEqual(checks['ownership_source']['status'], 'missing')
        self.assertEqual(checks['ownership_source_candidates']['status'], 'candidate_found')
        self.assertEqual(candidate_files[0]['artifact_key'], 'ownership_source_candidate')
        self.assertEqual(candidate_files[0]['role'], 'support')
        self.assertEqual(len(property_files), 1)
        self.assertIn(
            'Revisar candidatos legales de ownership y convertirlos, si son vigentes y suficientes, en snapshot controlado de socios/participaciones AC2024.',
            manifest['mirror_proof_readiness']['next_actions'],
        )

    def test_manifest_redacts_sensitive_relative_paths_but_keeps_path_ref_and_classification(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._write(
                source_root,
                'token-folder/Ano_2024/06_Respaldos_Tributarios/02_RCV_SII/2024-01_RCV_Resumen.csv',
            )

            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        file_payload = manifest['files'][0]
        self.assertEqual(file_payload['relative_path'], '<redacted-sensitive-reference>')
        self.assertTrue(file_payload['path_ref'].startswith('file-path-sha256:'))
        self.assertEqual(file_payload['category'], 'rcv_structured_input')
        self.assertEqual(file_payload['months'], [1])

    def test_manifest_treats_balance_and_tax_registers_as_comparison_targets_not_inputs(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._write(source_root, 'Ano_2024/01_Libros_Anuales/Balance General 2024.pdf')
            self._write(source_root, 'Ano_2024/01_Libros_Anuales/Libro Diario 2024.pdf')
            self._write(source_root, 'Ano_2024/01_Libros_Anuales/Libro Mayor 2024.pdf')
            self._write(source_root, 'Ano_2024/01_Libros_Anuales/Libro Inventario 2024.pdf')
            self._write(source_root, 'Ano_2024/00_Estructura_Societaria/Registro_Accionistas_2024.pdf')
            self._write(source_root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Renta Liquida.pdf')
            self._write(source_root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Capital Propio.pdf')
            self._write(source_root, 'Ano_2024/02_Libro_Compra/01 Enero - Libro Compra 2024.pdf')

            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        by_key = {item['artifact_key']: item for item in manifest['files']}
        self.assertEqual(by_key['balance_general']['category'], 'annual_balance_expected_output')
        self.assertEqual(by_key['balance_general']['role'], 'expected_output')
        self.assertEqual(by_key['renta_liquida']['category'], 'annual_tax_register_expected_output')
        self.assertEqual(by_key['renta_liquida']['role'], 'expected_output')
        self.assertEqual(by_key['libro_diario']['category'], 'annual_ledger_input')
        self.assertEqual(by_key['libro_diario']['role'], 'input')
        self.assertEqual(by_key['ownership_source_input']['category'], 'ownership_source_input')
        self.assertEqual(by_key['ownership_source_input']['role'], 'input')
        self.assertEqual(manifest['coverage']['purchase_sales_months'], [1])
        self.assertIn('annual_balance_expected_output', manifest['annual_tax_source_bundle_draft']['resumen_fuentes']['comparison_target_categories'])
        self.assertNotIn('annual_balance_expected_output', manifest['annual_tax_source_bundle_draft']['resumen_fuentes']['calculation_input_categories'])
        self.assertIn(
            'annual_balance_expected_output',
            manifest['mirror_proof_readiness']['input_policy']['comparison_only_outputs'],
        )
        self.assertNotIn(
            'annual_balance_expected_output',
            manifest['mirror_proof_readiness']['input_policy']['calculation_inputs'],
        )

    def test_rejected_or_annulled_ddjj_do_not_complete_expected_output_coverage(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            (source_root / 'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_1835_Aceptada.pdf').unlink()
            self._write(source_root, 'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_1835_RECHAZADA.pdf')
            self._write(source_root, 'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_1835_Anulada.pdf')

            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
            )

        self.assertIn('1835', manifest['coverage']['missing_ddjj_forms'])
        self.assertFalse(manifest['coverage']['ready_for_mirror_source_bundle'])
        statuses = {
            item['output_status']
            for item in manifest['files']
            if item['artifact_key'] == 'dj_1835'
        }
        self.assertEqual(statuses, {'annulled', 'rejected'})

    def test_command_outputs_manifest_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            stdout = StringIO()

            call_command(
                'build_annual_tax_source_manifest',
                source_root=str(source_root),
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                summary_only=True,
                fail_on_incomplete=True,
                stdout=stdout,
            )

        result = json.loads(stdout.getvalue())
        self.assertTrue(result['coverage']['ready_for_mirror_source_bundle'])
        self.assertNotIn('files', result)
        self.assertFalse(result['mirror_proof_readiness']['architecture_complete_for_mirror_run'])
        self.assertTrue(result['mirror_proof_readiness']['ready_to_start_controlled_processing'])
        self.assertEqual(
            result['mirror_proof_readiness']['missing_capabilities'],
            ['expected_output_value_equality_completion'],
        )

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'build_annual_tax_source_manifest',
                source_root='.',
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                output='docs/ac2024-source-manifest.json',
            )

    def test_command_can_fail_on_incomplete_required_mirror_inputs(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._write(source_root, 'Ano_2024/01_Libros_Anuales/Balance_General_2024.pdf')

            with self.assertRaisesMessage(CommandError, 'Manifiesto incompleto'):
                call_command(
                    'build_annual_tax_source_manifest',
                    source_root=str(source_root),
                    company_ref='inmobiliaria-puig',
                    commercial_year=2024,
                    tax_year=2025,
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )
