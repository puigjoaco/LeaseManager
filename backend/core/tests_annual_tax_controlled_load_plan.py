import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_controlled_load_plan import build_annual_tax_controlled_load_plan
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxControlledLoadPlanTests(SimpleTestCase):
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
                f'Ano_2024/02_Libro_Compra/{month:02d} Enero - Libro Compra 2024.pdf',
            )

        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Diario 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Mayor 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Inventario 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Balance General 2024.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Capital Propio.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Determinacion RAI.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Razonabilidad CPT.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Renta Liquida.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Rentas Empresariales.pdf')
        for form in ('1835', '1837', '1847', '1887', '1926', '1948'):
            self._write(root, f'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_{form}_Aceptada.pdf')
        self._write(root, 'Ano_2024/08_F22_Renta_AT_2025/AT_2025_Formulario_22_Compacto.pdf')

    def _manifest(self, source_root: Path) -> dict:
        return build_annual_tax_source_manifest(
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )

    def test_load_plan_maps_inputs_to_architecture_without_using_expected_outputs_as_inputs(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            manifest = self._manifest(source_root)

        plan = build_annual_tax_controlled_load_plan(manifest=manifest)
        by_category = {item['category']: item for item in plan['load_items']}

        self.assertTrue(plan['source_confirmation']['source_documentation_confirmed_for_ac2024_at2025'])
        self.assertFalse(plan['summary']['ready_for_db_load'])
        self.assertFalse(plan['summary']['ready_for_mirror_generation'])
        self.assertFalse(plan['summary']['expected_outputs_used_as_inputs'])
        self.assertIn('calculation_input_parsers_or_manual_load_required', plan['blockers'])
        self.assertEqual(by_category['annual_balance_expected_output']['role'], 'comparison_only')
        self.assertEqual(by_category['annual_balance_expected_output']['status'], 'comparison_target_only')
        self.assertFalse(by_category['annual_balance_expected_output']['used_as_calculation_input'])
        self.assertEqual(by_category['ddjj_expected_output']['role'], 'comparison_only')
        self.assertFalse(by_category['ddjj_expected_output']['used_as_calculation_input'])
        self.assertEqual(by_category['rcv_structured_input']['status'], 'ready_for_loader')
        self.assertIn('sii.MonthlyTaxFact', by_category['rcv_structured_input']['target_models'])
        self.assertEqual(by_category['annual_ledger_input']['status'], 'blocked')
        self.assertIn('contabilidad.LibroDiario', by_category['annual_ledger_input']['target_models'])
        self.assertIn('sii.AnnualTaxTrialBalanceLine', by_category['annual_ledger_input']['target_models'])
        self.assertIn(
            'normalized_controlled_source_package_required',
            plan['summary']['missing_capabilities_after_plan'],
        )
        self.assertNotIn('controlled_accounting_db_writer', plan['summary']['missing_capabilities_after_plan'])
        self.assertIn('expected_output_comparator', plan['summary']['missing_capabilities_after_plan'])

    def test_load_plan_blocks_manifest_without_file_list(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                include_file_list=False,
            )

        plan = build_annual_tax_controlled_load_plan(manifest=manifest)

        self.assertFalse(plan['summary']['ready_for_db_load'])
        self.assertIn('manifest_file_list_missing', plan['blockers'])
        self.assertIn('required_source_categories_missing', plan['blockers'])

    def test_command_outputs_plan_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._build_complete_source_tree(source_root)
            manifest = self._manifest(source_root)
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'build_annual_tax_controlled_load_plan',
                manifest=str(manifest_path),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['schema_version'], 'annual-tax-controlled-load-plan.v1')
            self.assertFalse(result['safety']['writes_database'])
            self.assertFalse(result['safety']['expected_outputs_used_as_inputs'])
            self.assertIn('calculation_input_parsers_or_manual_load_required', result['blockers'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'build_annual_tax_controlled_load_plan',
                    manifest=str(manifest_path),
                    output='docs/ac2024-load-plan.json',
                )

    def test_command_can_fail_on_blocking_plan(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._build_complete_source_tree(source_root)
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(self._manifest(source_root)), encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'Plan de carga controlada no listo para DB'):
                call_command(
                    'build_annual_tax_controlled_load_plan',
                    manifest=str(manifest_path),
                    fail_on_blocking=True,
                    stdout=StringIO(),
                )
