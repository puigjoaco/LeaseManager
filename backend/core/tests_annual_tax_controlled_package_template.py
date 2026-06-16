import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_controlled_package_template import build_annual_tax_controlled_db_load_template
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxControlledPackageTemplateTests(SimpleTestCase):
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
            self._write(
                root,
                f'Ano_2024/05_Remuneraciones/2024-{month:02d}_Liquidaciones_Resumen.pdf',
            )

        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Diario 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Mayor 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Inventario 2024.pdf')
        self._write(root, 'Ano_2024/00_Estructura_Societaria/Participaciones_Socios_2024.pdf')
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

    def test_template_builds_writer_draft_without_using_expected_outputs_as_inputs(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            manifest = self._manifest(source_root)

        template = build_annual_tax_controlled_db_load_template(manifest=manifest)
        rendered = json.dumps(template, ensure_ascii=True)
        package = template['package_draft']

        self.assertEqual(template['schema_version'], 'annual-tax-controlled-db-load-template.v1')
        self.assertEqual(package['schema_version'], 'annual-tax-controlled-db-load.v1')
        self.assertFalse(template['safety']['writes_database'])
        self.assertFalse(template['safety']['expected_outputs_used_as_inputs'])
        self.assertTrue(template['safety']['comparison_targets_separated'])
        self.assertFalse(package['expected_outputs_used_as_inputs'])
        self.assertEqual(len(package['months']), 12)
        self.assertIn('annual_ledger_input', package['annual_input_source_refs'])
        self.assertIn('annual_balance_expected_output', template['comparison_targets'])
        self.assertIn('ddjj_expected_output', template['comparison_targets'])
        self.assertIn('f22_expected_output', template['comparison_targets'])
        self.assertNotIn('annual_balance_expected_output', package)
        self.assertNotIn('ddjj_expected_output', json.dumps(package, ensure_ascii=True))
        self.assertNotIn(str(source_root), rendered)
        self.assertEqual(
            template['summary']['missing_months_by_category']['rcv_structured_input'],
            [],
        )
        self.assertEqual(
            template['summary']['missing_months_by_category']['payroll_support'],
            [],
        )
        self.assertTrue(template['summary']['monthly_input_refs_complete'])
        self.assertTrue(template['summary']['annual_ledger_refs_complete'])

    def test_template_reports_missing_monthly_support_without_failing_source_inventory(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            for path in (source_root / 'Ano_2024/05_Remuneraciones').glob('2024-03_*'):
                path.unlink()
            manifest = self._manifest(source_root)

        template = build_annual_tax_controlled_db_load_template(manifest=manifest)

        self.assertEqual(template['summary']['missing_months_by_category']['payroll_support'], [3])
        self.assertFalse(template['summary']['monthly_input_refs_complete'])
        self.assertFalse(template['summary']['ready_for_writer'])

    def test_template_treats_controlled_no_declaration_f29_month_as_covered(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            for path in (source_root / 'Ano_2024/06_Respaldos_Tributarios/01_F29_y_Comprobantes').glob('2024-02_*'):
                path.unlink()
            manifest = build_annual_tax_source_manifest(
                source_root=source_root,
                company_ref='inmobiliaria-puig',
                commercial_year=2024,
                tax_year=2025,
                f29_no_declaration_months=[2],
            )

        template = build_annual_tax_controlled_db_load_template(manifest=manifest)
        february = template['package_draft']['months'][1]

        self.assertEqual(template['summary']['missing_months_by_category']['f29_support_input'], [])
        self.assertTrue(template['summary']['monthly_input_refs_complete'])
        self.assertEqual(february['month'], 2)
        self.assertEqual(february['f29']['estado_preparacion'], 'no_aplica')
        self.assertTrue(february['f29']['resumen']['no_declaration'])

    def test_command_outputs_template_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._build_complete_source_tree(source_root)
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(self._manifest(source_root)), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'build_annual_tax_controlled_db_load_template',
                manifest=str(manifest_path),
                fail_on_incomplete=True,
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['schema_version'], 'annual-tax-controlled-db-load-template.v1')
            self.assertFalse(result['safety']['writes_database'])
            self.assertFalse(result['package_draft']['expected_outputs_used_as_inputs'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'build_annual_tax_controlled_db_load_template',
                    manifest=str(manifest_path),
                    output='docs/ac2024-controlled-load-template.json',
                    stdout=StringIO(),
                )
