import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_readiness import audit_annual_tax_controlled_package_readiness
from core.annual_tax_controlled_package_template import build_annual_tax_controlled_db_load_template
from core.annual_tax_source_manifest import build_annual_tax_source_manifest


class AnnualTaxControlledPackageReadinessTests(SimpleTestCase):
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
            self._write(root, f'Ano_2024/02_Libro_Compra/{month:02d} Libro Compra 2024.pdf')
            self._write(root, f'Ano_2024/05_Remuneraciones/2024-{month:02d}_Liquidaciones_Resumen.pdf')

        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Diario 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Libro Mayor 2024.pdf')
        self._write(root, 'Ano_2024/01_Libros_Anuales/Balance General 2024.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Renta Liquida.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Capital Propio.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Determinacion RAI.pdf')
        self._write(root, 'Ano_2024/06_Registros_Empresariales_AT/2025/Rentas Empresariales.pdf')
        self._write(root, 'Ano_2024/07_DDJJ_AT_2025/AT_2025_DJ_1887_Aceptada.pdf')
        self._write(root, 'Ano_2024/08_F22_Renta_AT_2025/AT_2025_Formulario_22_Compacto.pdf')

    def _manifest(self, source_root: Path) -> dict:
        return build_annual_tax_source_manifest(
            source_root=source_root,
            company_ref='inmobiliaria-puig',
            commercial_year=2024,
            tax_year=2025,
        )

    def _complete_package(self, *, f29_no_aplica_months=()):
        return {
            'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_manifest_hash': 'a' * 64,
            'responsible_ref': 'responsable-controlado',
            'approval_ref': 'aprobacion-controlada',
            'expected_outputs_used_as_inputs': False,
            'annual_input_source_refs': {
                'annual_ledger_input': [
                    {
                        'path_ref': 'libro-diario-mayor-anual-controlado',
                        'category': 'annual_ledger_input',
                        'artifact_key': 'annual_ledger',
                    }
                ],
            },
            'months': [
                {
                    'month': month,
                    'source_ref': f'ac2024-month-{month:02d}-controlled',
                    'ledger': {
                        'libro_diario_ref': f'libro-diario-2024-{month:02d}-controlled',
                        'libro_mayor_ref': f'libro-mayor-2024-{month:02d}-controlled',
                        'asientos_count': 10,
                        'cuentas_count': 25,
                        'total_debe': '1000.00',
                        'total_haber': '1000.00',
                    },
                    'balance': {
                        'balance_ref': f'balance-comprobacion-2024-{month:02d}-controlled',
                        'total_debe': '1000.00',
                        'total_haber': '1000.00',
                        'cuadrado': True,
                    },
                    'obligations': [
                        {
                            'tipo': 'PPM',
                            'base_imponible': '1000.00',
                            'monto_calculado': '10.00',
                        }
                    ],
                    'f29': {
                        'estado_preparacion': 'no_aplica',
                        'borrador_ref': '',
                        'resumen': {
                            'no_declaration': True,
                            'source': 'manifest.f29_no_declaration_months',
                        },
                    }
                    if month in f29_no_aplica_months
                    else {
                        'estado_preparacion': 'preparado',
                        'borrador_ref': f'f29-2024-{month:02d}-controlled',
                        'resumen': {'declarado': True},
                    },
                    'payroll': {
                        'source_ref': '',
                        'has_movements': False,
                        'resumen': {'reviewed': True},
                    },
                }
                for month in range(1, 13)
            ],
        }

    def test_template_draft_is_not_ready_until_manual_values_are_completed(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._build_complete_source_tree(source_root)
            template = build_annual_tax_controlled_db_load_template(manifest=self._manifest(source_root))

        result = audit_annual_tax_controlled_package_readiness(payload=template)

        self.assertFalse(result['ready_for_db_writer'])
        self.assertIn('monthly_value_placeholders', result['blockers'])
        self.assertIn('missing_control_refs', result['blockers'])
        self.assertIn('$.responsible_ref', result['missing_value_paths'])
        self.assertIn('$.months[0].ledger.libro_diario_ref', result['missing_value_paths'])
        self.assertIn('$.months[0].f29.borrador_ref', result['missing_value_paths'])
        self.assertTrue(result['summary']['complete_12_months'])
        self.assertTrue(result['summary']['comparison_targets_present'])

    def test_complete_package_is_ready_for_db_writer_without_using_expected_outputs(self):
        result = audit_annual_tax_controlled_package_readiness(payload=self._complete_package())

        self.assertTrue(result['ready_for_db_writer'])
        self.assertTrue(result['ready_for_annual_generation'])
        self.assertFalse(result['ready_for_mirror_comparison'])
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['missing_value_paths'], [])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])

    def test_no_declaration_f29_month_is_valid_without_borrador_ref(self):
        result = audit_annual_tax_controlled_package_readiness(
            payload=self._complete_package(f29_no_aplica_months={2, 12}),
        )

        self.assertTrue(result['ready_for_db_writer'])
        self.assertNotIn('$.months[1].f29.borrador_ref', result['missing_value_paths'])
        self.assertNotIn('f29_status_missing', result['blockers'])

    def test_expected_outputs_inside_package_block_readiness(self):
        package = self._complete_package()
        package['ddjj_expected_output'] = {'form': '1887'}

        result = audit_annual_tax_controlled_package_readiness(payload=package)

        self.assertFalse(result['ready_for_db_writer'])
        self.assertIn('expected_outputs_present', result['blockers'])
        self.assertIn('$.ddjj_expected_output', result['invalid_paths'])

    def test_command_outputs_readiness_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'package.json'
            package_path.write_text(json.dumps(self._complete_package()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'audit_annual_tax_controlled_package_readiness',
                package=str(package_path),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertTrue(result['ready_for_db_writer'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_annual_tax_controlled_package_readiness',
                    package=str(package_path),
                    output='docs/ac2024-controlled-package-readiness.json',
                    stdout=StringIO(),
                )
