import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_template import CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION
from core.annual_tax_controlled_values_draft import (
    build_annual_tax_controlled_values_draft,
    parse_f29_text,
    parse_libro_diario_text,
    parse_libro_inventario_text,
    parse_libro_mayor_annual_trial_balance_lines,
    parse_libro_mayor_text,
    parse_payroll_text,
    parse_real_estate_contribution_history_json,
    parse_real_estate_registry_json,
)


class AnnualTaxControlledValuesDraftTests(SimpleTestCase):
    def _source_file(self, root: Path, relative_path: str, content: str) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def _manifest(self) -> dict:
        return {
            'schema_version': 'annual-tax-source-manifest.v1',
            'source_root_ref': 'source-root-sha256:test',
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'files': [
                {
                    'path_ref': 'libro-diario-ref',
                    'relative_path': '01_Libros_Anuales/Libro Diario 2024.txt',
                    'category': 'annual_ledger_input',
                    'artifact_key': 'libro_diario',
                    'months': [],
                },
                {
                    'path_ref': 'libro-mayor-ref',
                    'relative_path': '01_Libros_Anuales/Libro Mayor 2024.txt',
                    'category': 'annual_ledger_input',
                    'artifact_key': 'libro_mayor',
                    'months': [],
                },
                {
                    'path_ref': 'libro-inventario-ref',
                    'relative_path': '01_Libros_Anuales/Libro Inventario 2024.txt',
                    'category': 'annual_ledger_input',
                    'artifact_key': 'libro_inventario',
                    'months': [],
                },
                {
                    'path_ref': 'f29-enero-ref',
                    'relative_path': '06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-01 F29.txt',
                    'category': 'f29_support_input',
                    'artifact_key': 'f29_support_input',
                    'months': [1],
                },
                {
                    'path_ref': 'payroll-enero-ref',
                    'relative_path': '05_Libro_Remuneraciones/01 Enero.txt',
                    'category': 'payroll_support',
                    'artifact_key': 'payroll_support',
                    'months': [1],
                },
                {
                    'path_ref': 'f22-final-ref',
                    'relative_path': '08_F22_Renta_AT_2025/f22-final.txt',
                    'category': 'f22_expected_output',
                    'artifact_key': 'f22',
                    'months': [],
                },
            ],
        }

    def _template(self) -> dict:
        return {
            'schema_version': CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
            'comparison_targets': {
                'f22_expected_output': [{'path_ref': 'f22-final-ref', 'category': 'f22_expected_output'}],
            },
            'package_draft': {
                'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
                'company_ref': 'inmobiliaria-puig',
                'commercial_year': 2024,
                'tax_year': 2025,
                'source_manifest_hash': 'a' * 64,
                'responsible_ref': 'pending-responsible-ref',
                'approval_ref': 'pending-approval-ref',
                'expected_outputs_used_as_inputs': False,
                'annual_input_source_refs': {
                    'annual_ledger_input': [
                        {'path_ref': 'libro-diario-ref'},
                        {'path_ref': 'libro-mayor-ref'},
                        {'path_ref': 'libro-inventario-ref'},
                    ]
                },
                'labor_previsional': {
                    'required': True,
                    'required_by_ddjj_forms': ['1887'],
                    'source_ref': '',
                    'source_refs': [{'path_ref': 'payroll-enero-ref'}],
                    'monthly_support_months': [1],
                    'status': 'pending_source_review',
                    'final_tax_calculation': False,
                },
                'months': [
                    {
                        'month': 1,
                        'source_ref': 'month-01-controlled',
                        'input_source_refs': {
                            'f29_support_input': [{'path_ref': 'f29-enero-ref'}],
                            'payroll_support': [{'path_ref': 'payroll-enero-ref'}],
                        },
                        'ledger': {
                            'libro_diario_ref': '',
                            'libro_mayor_ref': '',
                            'asientos_count': None,
                            'cuentas_count': None,
                            'total_debe': '',
                            'total_haber': '',
                        },
                        'balance': {
                            'balance_ref': '',
                            'total_debe': '',
                            'total_haber': '',
                            'cuadrado': None,
                        },
                        'obligations': [],
                        'f29': {'estado_preparacion': 'preparado', 'borrador_ref': '', 'resumen': {}},
                        'payroll': {'source_ref': '', 'has_movements': None, 'resumen': {}},
                    }
                ],
            },
        }

    def test_text_parsers_extract_controlled_monthly_values(self):
        diario = parse_libro_diario_text(
            '\n'.join(
                [
                    'Comprobantes MES DE ENERO',
                    'TOTAL COMPROBANTE Nº 1 1.000 1.000',
                    'TOTAL COMPROBANTE Nº 2 2.500 2.500',
                    'Total ENERO 3.500 3.500',
                ]
            )
        )
        mayor = parse_libro_mayor_text(
            '\n'.join(
                [
                    '1101001 Caja',
                    'Total Mes de Enero . 1.000 500 500 DB',
                    '2101001 Proveedores',
                    'Total Mes de Enero . 2.500 3.000 500 CR',
                ]
            )
        )
        mayor_annual = parse_libro_mayor_annual_trial_balance_lines(
            '\n'.join(
                [
                    'Total 1101001 Caja 1.000 500 500 DB',
                    'Total 2101001 Proveedores 2.500 3.000 500 CR',
                ]
            )
        )
        f29 = parse_f29_text(
            'PERIODO [15] 202401\n'
            '563 BASE IMPONIBLE 3.500 062 PPM NETO DETERMINADO 378\n'
            '048 RET. IMP. UNICO TRAB. ART. 74 N 1 LIR 167.505'
        )
        payroll = parse_payroll_text('Total General : 4.000.000 0 3.166.637')
        inventario = parse_libro_inventario_text(
            '\n'.join(
                [
                    'DETALLE DE ACTIVOS',
                    '1101001 Caja',
                    'DESCRIPCION TOTAL',
                    'SALDO CONTABLE AL 31/12/2024 1.000',
                    'DETALLE DE PASIVOS',
                    '3101001 Capital',
                    'DESCRIPCION TOTAL',
                    'SALDO CONTABLE AL 31/12/2024 (700)',
                    'PERDIDA DEL EJERCICIO (300)',
                ]
            )
        )

        self.assertEqual(diario[1]['asientos_count'], 2)
        self.assertEqual(diario[1]['total_debe'], 3500)
        self.assertEqual(mayor[1]['cuentas_count'], 2)
        self.assertEqual(mayor[1]['total_haber'], 3500)
        self.assertEqual(mayor_annual['1101001']['saldo_deudor_clp'], '500.00')
        self.assertEqual(mayor_annual['2101001']['saldo_acreedor_clp'], '500.00')
        self.assertEqual(f29['periodo'], '202401')
        self.assertEqual(f29['codes']['062'], 378)
        self.assertTrue(payroll['has_movements'])
        self.assertEqual(len(inventario['lines']), 3)
        self.assertEqual(inventario['lines'][0]['clasificador_dj1847'], 'CPT-CASH-ASSET')
        self.assertEqual(inventario['lines'][1]['inventario_pasivo_clp'], '700.00')
        self.assertEqual(inventario['lines'][2]['resultado_perdida_clp'], '300.00')
        real_estate = parse_real_estate_registry_json(
            {
                'properties': [
                    [
                        '',
                        'Providencia',
                        '00031-00243',
                        'Nva Lyon 45 LC 41 B',
                        'COMERCIO',
                        '12345',
                        '67890',
                        '2026',
                        '50.00 %',
                        '$ 12.345.678',
                        'Ver',
                        '',
                    ]
                ]
            },
            registry_ref='real-estate-registry-ref',
        )
        contributions = parse_real_estate_contribution_history_json(
            {
                'response': {
                    'body': {
                        'data': [
                            {
                                'fechaPago': '02/05/2024',
                                'propiedad': [
                                    {
                                        'comuna': 15103,
                                        'manzana': 31,
                                        'predio': 243,
                                        'rol': None,
                                        'valorCuota': 12000,
                                    }
                                ],
                            }
                        ]
                    }
                }
            },
            commercial_year=2024,
            source_ref='real-estate-history-ref',
        )

        self.assertEqual(real_estate[0]['tipo_inmueble'], 'local')
        self.assertEqual(real_estate[0]['source_payload']['rol_tail_key'], '31-243')
        self.assertEqual(contributions['15103-31-243']['amount'], 12000)

    def test_values_draft_fills_permitted_inputs_without_using_expected_outputs(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Diario 2024.txt',
                'Comprobantes MES DE ENERO\n'
                'TOTAL COMPROBANTE Nº 1 1.000 1.000\n'
                'TOTAL COMPROBANTE Nº 2 2.500 2.500\n'
                'Total ENERO 3.500 3.500\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Mayor 2024.txt',
                '1101001 Caja\nTotal Mes de Enero . 1.000 500 500 DB\n'
                '2101001 Proveedores\nTotal Mes de Enero . 2.500 3.000 500 CR\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Inventario 2024.txt',
                'DETALLE DE ACTIVOS\n'
                '1101001 Caja\nDESCRIPCION TOTAL\nSALDO CONTABLE AL 31/12/2024 1.000\n'
                'DETALLE DE PASIVOS\n'
                '3101001 Capital\nDESCRIPCION TOTAL\nSALDO CONTABLE AL 31/12/2024 (700)\n'
                'PERDIDA DEL EJERCICIO (300)\n',
            )
            self._source_file(
                source_root,
                '06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-01 F29.txt',
                'PERIODO [15] 202401\n563 BASE IMPONIBLE 3.500 062 PPM NETO DETERMINADO 378\n',
            )
            self._source_file(
                source_root,
                '05_Libro_Remuneraciones/01 Enero.txt',
                'Total General : 4.000.000 0 3.166.637',
            )

            result = build_annual_tax_controlled_values_draft(
                manifest=self._manifest(),
                template=self._template(),
                source_root=source_root,
                responsible_ref='codex-local-review',
                approval_ref='user-authorized-local-source-review',
            )

        month = result['package_draft']['months'][0]
        self.assertEqual(result['values_draft_summary']['extraction_errors'], [])
        self.assertFalse(result['values_draft_summary']['uses_expected_outputs_as_inputs'])
        self.assertEqual(result['package_draft']['responsible_ref'], 'codex-local-review')
        self.assertEqual(month['ledger']['asientos_count'], 2)
        self.assertEqual(month['ledger']['cuentas_count'], 2)
        self.assertEqual(month['ledger']['total_debe'], '3500.00')
        self.assertTrue(month['balance']['cuadrado'])
        self.assertNotIn('lineas_balance_8_columnas', month['balance'])
        self.assertEqual(month['f29']['borrador_ref'], 'f29-enero-ref')
        self.assertEqual(month['obligations'][0]['tipo'], 'PPM')
        self.assertTrue(month['payroll']['has_movements'])
        labor = result['package_draft']['labor_previsional']
        self.assertTrue(labor['source_ref'].startswith('labor-previsional-reviewed-'))
        self.assertEqual(labor['status'], 'reviewed_source_ref_ready')
        self.assertEqual(labor['reviewed_source_refs_count'], 1)
        self.assertFalse(labor['final_tax_calculation'])
        self.assertTrue(result['values_draft_summary']['labor_previsional_source_ref_ready'])
        self.assertEqual(result['values_draft_summary']['labor_previsional_reviewed_source_refs_count'], 1)
        rendered_package = json.dumps(result['package_draft'], ensure_ascii=True)
        self.assertNotIn('f22_expected_output', rendered_package)

    def test_values_draft_materializes_real_estate_from_controlled_support(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._source_file(
                source_root,
                '06_Respaldos_Tributarios/03_Bienes_Raices_y_Contribuciones/00_REGISTRO_BIENES_RAICES.json',
                json.dumps(
                    {
                        'properties': [
                            [
                                '',
                                'Providencia',
                                '00031-00243',
                                'Nva Lyon 45 LC 41 B',
                                'COMERCIO',
                                '12345',
                                '67890',
                                '2026',
                                '50.00 %',
                                '$ 12.345.678',
                                'Ver',
                                '',
                            ],
                            [
                                '',
                                'Temuco',
                                '00090-00047',
                                'Bulnes 443 LC 19',
                                'COMERCIO',
                                '12345',
                                '67890',
                                '2026',
                                '100.00 %',
                                '$ 4.000.000',
                                'Ver',
                                '',
                            ],
                        ]
                    }
                ),
            )
            self._source_file(
                source_root,
                '06_Respaldos_Tributarios/03_Bienes_Raices_y_Contribuciones/Historial_Pagos/00031-00243.json',
                json.dumps(
                    {
                        'response': {
                            'body': {
                                'data': [
                                    {
                                        'fechaPago': '02/05/2024',
                                        'propiedad': [
                                            {
                                                'comuna': 15103,
                                                'manzana': 31,
                                                'predio': 243,
                                                'rol': None,
                                                'valorCuota': 12000,
                                            }
                                        ],
                                    },
                                    {
                                        'fechaPago': '15/09/2024',
                                        'propiedad': [
                                            {
                                                'comuna': 15103,
                                                'manzana': 31,
                                                'predio': 243,
                                                'rol': None,
                                                'valorCuota': 13000,
                                            }
                                        ],
                                    },
                                    {
                                        'fechaPago': '15/09/2023',
                                        'propiedad': [
                                            {
                                                'comuna': 15103,
                                                'manzana': 31,
                                                'predio': 243,
                                                'rol': None,
                                                'valorCuota': 99999,
                                            }
                                        ],
                                    },
                                ]
                            }
                        }
                    }
                ),
            )
            manifest = self._manifest()
            manifest['files'].extend(
                [
                    {
                        'path_ref': 'real-estate-registry-ref',
                        'relative_path': '06_Respaldos_Tributarios/03_Bienes_Raices_y_Contribuciones/00_REGISTRO_BIENES_RAICES.json',
                        'category': 'real_estate_support',
                        'artifact_key': 'real_estate_support',
                        'months': [],
                    },
                    {
                        'path_ref': 'real-estate-history-ref',
                        'relative_path': '06_Respaldos_Tributarios/03_Bienes_Raices_y_Contribuciones/Historial_Pagos/00031-00243.json',
                        'category': 'real_estate_support',
                        'artifact_key': 'real_estate_support',
                        'months': [],
                    },
                ]
            )

            result = build_annual_tax_controlled_values_draft(
                manifest=manifest,
                template=self._template(),
                source_root=source_root,
                responsible_ref='codex-local-review',
                approval_ref='user-authorized-local-source-review',
            )

        real_estate = result['package_draft']['real_estate']
        properties = real_estate['properties']
        self.assertTrue(real_estate['source_ref'].startswith('real-estate-reviewed-'))
        self.assertEqual(real_estate['as_of'], '2024-12-31')
        self.assertEqual(len(properties), 2)
        self.assertEqual(properties[0]['tipo_inmueble'], 'local')
        self.assertEqual(properties[0]['contribuciones_clp'], '25000.00')
        self.assertEqual(properties[0]['contribuciones_evidence_ref'], 'real-estate-history-ref')
        self.assertEqual(properties[0]['source_payload']['contribuciones_source'], 'historial_pagos_sii')
        self.assertEqual(properties[1]['contribuciones_clp'], '0.00')
        self.assertEqual(properties[1]['source_payload']['contribuciones_source'], 'not_found_for_commercial_year')
        self.assertFalse(real_estate['source_payload']['final_tax_calculation'])
        self.assertTrue(result['values_draft_summary']['real_estate_source_ref_ready'])
        self.assertEqual(result['values_draft_summary']['real_estate_properties_count'], 2)
        rendered_package = json.dumps(result['package_draft'], ensure_ascii=True)
        self.assertNotIn('f22_expected_output', rendered_package)

    def test_values_draft_keeps_labor_source_pending_when_expected_payroll_is_not_reviewed(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Diario 2024.txt',
                'Comprobantes MES DE ENERO\nTOTAL COMPROBANTE Nº 1 1.000 1.000\nTotal ENERO 1.000 1.000\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Mayor 2024.txt',
                '1101001 Caja\nTotal Mes de Enero . 1.000 1.000 0\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Inventario 2024.txt',
                'DETALLE DE ACTIVOS\n1101001 Caja\nSALDO CONTABLE AL 31/12/2024 1.000\n',
            )
            self._source_file(
                source_root,
                '06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-01 F29.txt',
                'PERIODO [15] 202401\n563 BASE IMPONIBLE 1.000 062 PPM NETO DETERMINADO 10\n',
            )
            template = self._template()
            template['package_draft']['months'][0]['input_source_refs'].pop('payroll_support')

            result = build_annual_tax_controlled_values_draft(
                manifest=self._manifest(),
                template=template,
                source_root=source_root,
                responsible_ref='codex-local-review',
                approval_ref='user-authorized-local-source-review',
            )

        labor = result['package_draft']['labor_previsional']
        self.assertEqual(labor['source_ref'], '')
        self.assertEqual(labor['status'], 'pending_source_review')
        self.assertFalse(result['values_draft_summary']['labor_previsional_source_ref_ready'])
        self.assertEqual(result['values_draft_summary']['labor_previsional_reviewed_source_refs_count'], 0)

    def test_values_draft_prefers_commercial_year_annual_books_over_later_candidates(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Diario 2024.txt',
                'Comprobantes MES DE ENERO\n'
                'TOTAL COMPROBANTE Nº 1 1.000 1.000\n'
                'TOTAL COMPROBANTE Nº 2 2.500 2.500\n'
                'Total ENERO 3.500 3.500\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Mayor 2024.txt',
                '1101001 Caja\nTotal Mes de Enero . 1.000 500 500 DB\n'
                '2101001 Proveedores\nTotal Mes de Enero . 2.500 3.000 500 CR\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Inventario 2024.txt',
                'DETALLE DE ACTIVOS\n'
                '1101001 Caja\nDESCRIPCION TOTAL\nSALDO CONTABLE AL 31/12/2024 1.000\n',
            )
            self._source_file(
                source_root,
                '06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-01 F29.txt',
                'PERIODO [15] 202401\n563 BASE IMPONIBLE 3.500 062 PPM NETO DETERMINADO 378\n',
            )
            self._source_file(
                source_root,
                '05_Libro_Remuneraciones/01 Enero.txt',
                'Total General : 4.000.000 0 3.166.637',
            )
            self._source_file(
                source_root,
                'Ano_2025/60_RESPALDOS_RECIBIDOS_PENDIENTES_AUDITORIA/Libro_Diario_2024_Gmail.txt',
                'Comprobantes MES DE ENERO\nTOTAL COMPROBANTE Nº 99 99.000 99.000\nTotal ENERO 99.000 99.000\n',
            )
            self._source_file(
                source_root,
                'Ano_2025/60_RESPALDOS_RECIBIDOS_PENDIENTES_AUDITORIA/Libro_Mayor_2024_Gmail.txt',
                '1101001 Caja\nTotal Mes de Enero . 99.000 99.000 0\n',
            )
            self._source_file(
                source_root,
                'Ano_HISTORICO/Lo que falto en el inventario.txt',
                'DETALLE DE ACTIVOS\n1101001 Caja\nSALDO CONTABLE AL 31/12/2024 99.000\n',
            )
            manifest = self._manifest()
            manifest['files'].extend(
                [
                    {
                        'path_ref': 'later-pending-diario-ref',
                        'relative_path': 'Ano_2025/60_RESPALDOS_RECIBIDOS_PENDIENTES_AUDITORIA/Libro_Diario_2024_Gmail.txt',
                        'category': 'annual_ledger_input',
                        'artifact_key': 'libro_diario',
                        'months': [],
                    },
                    {
                        'path_ref': 'later-pending-mayor-ref',
                        'relative_path': 'Ano_2025/60_RESPALDOS_RECIBIDOS_PENDIENTES_AUDITORIA/Libro_Mayor_2024_Gmail.txt',
                        'category': 'annual_ledger_input',
                        'artifact_key': 'libro_mayor',
                        'months': [],
                    },
                    {
                        'path_ref': 'historic-inventario-ref',
                        'relative_path': 'Ano_HISTORICO/Lo que falto en el inventario.txt',
                        'category': 'annual_ledger_input',
                        'artifact_key': 'libro_inventario',
                        'months': [],
                    },
                ]
            )

            result = build_annual_tax_controlled_values_draft(
                manifest=manifest,
                template=self._template(),
                source_root=source_root,
                responsible_ref='codex-local-review',
                approval_ref='user-authorized-local-source-review',
            )

        month = result['package_draft']['months'][0]
        self.assertEqual(result['values_draft_summary']['extraction_errors'], [])
        self.assertEqual(month['ledger']['libro_diario_ref'], 'libro-diario-ref#month=01')
        self.assertEqual(month['ledger']['libro_mayor_ref'], 'libro-mayor-ref#month=01')
        self.assertEqual(month['ledger']['asientos_count'], 2)
        self.assertEqual(month['ledger']['total_debe'], '3500.00')
        self.assertEqual(month['balance']['balance_ref'], 'libro-mayor-ref#month=01')

    def test_values_draft_attaches_inventory_lines_to_december_balance(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Diario 2024.txt',
                'Comprobantes MES DE DICIEMBRE\nTOTAL COMPROBANTE Nº 1 1.000 1.000\nTotal DICIEMBRE 1.000 1.000\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Mayor 2024.txt',
                '1101001 Caja\n'
                'Total Mes de Diciembre . 1.000 0 1.000 DB\n'
                'Total 1101001 Caja 1.500 500 1.000 DB\n'
                'Total 3101001 Capital 100 800 700 CR\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Inventario 2024.txt',
                'DETALLE DE ACTIVOS\n'
                '1101001 Caja\nDESCRIPCION TOTAL\nSALDO CONTABLE AL 31/12/2024 1.000\n'
                'DETALLE DE PASIVOS\n'
                '3101001 Capital\nDESCRIPCION TOTAL\nSALDO CONTABLE AL 31/12/2024 (700)\n',
            )
            template = self._template()
            month = template['package_draft']['months'][0]
            month['month'] = 12
            month['source_ref'] = 'month-12-controlled'
            month['input_source_refs'] = {}

            result = build_annual_tax_controlled_values_draft(
                manifest=self._manifest(),
                template=template,
                source_root=source_root,
                responsible_ref='codex-local-review',
                approval_ref='user-authorized-local-source-review',
            )

        december = result['package_draft']['months'][0]
        self.assertEqual(december['balance']['annual_inventory_ref'], 'libro-inventario-ref')
        self.assertEqual(december['balance']['lineas_balance_8_columnas_source'], 'libro_inventario')
        self.assertEqual(len(december['balance']['lineas_balance_8_columnas']), 2)
        first_line = december['balance']['lineas_balance_8_columnas'][0]
        second_line = december['balance']['lineas_balance_8_columnas'][1]
        self.assertEqual(first_line['inventario_activo_clp'], '1000.00')
        self.assertEqual(first_line['sumas_debe_clp'], '1500.00')
        self.assertEqual(first_line['sumas_haber_clp'], '500.00')
        self.assertEqual(first_line['saldo_deudor_clp'], '1000.00')
        self.assertEqual(first_line['source_payload']['source'], 'libro_inventario+libro_mayor')
        self.assertEqual(second_line['sumas_debe_clp'], '100.00')
        self.assertEqual(second_line['sumas_haber_clp'], '800.00')
        self.assertEqual(second_line['saldo_acreedor_clp'], '700.00')

    def test_command_outputs_values_draft_and_refuses_versioned_output_outside_local_evidence(self):
        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir) / 'source'
            source_root.mkdir()
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Diario 2024.txt',
                'Comprobantes MES DE ENERO\nTOTAL COMPROBANTE Nº 1 1.000 1.000\nTotal ENERO 1.000 1.000\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Mayor 2024.txt',
                '1101001 Caja\nTotal Mes de Enero . 1.000 1.000 0\n',
            )
            self._source_file(
                source_root,
                '01_Libros_Anuales/Libro Inventario 2024.txt',
                'DETALLE DE ACTIVOS\n1101001 Caja\nSALDO CONTABLE AL 31/12/2024 1.000\n',
            )
            self._source_file(source_root, '06_Respaldos_Tributarios/01_F29_y_Comprobantes/2024-01 F29.txt', '')
            self._source_file(source_root, '05_Libro_Remuneraciones/01 Enero.txt', 'Total General : 1.000')
            manifest_path = Path(temp_dir) / 'manifest.json'
            template_path = Path(temp_dir) / 'template.json'
            manifest_path.write_text(json.dumps(self._manifest()), encoding='utf-8')
            template_path.write_text(json.dumps(self._template()), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'build_annual_tax_controlled_values_draft',
                manifest=str(manifest_path),
                template=str(template_path),
                source_root=str(source_root),
                responsible_ref='codex-local-review',
                approval_ref='user-authorized-local-source-review',
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['values_draft_summary']['schema_version'], 'annual-tax-controlled-values-draft.v1')

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'build_annual_tax_controlled_values_draft',
                    manifest=str(manifest_path),
                    template=str(template_path),
                    source_root=str(source_root),
                    output='docs/ac2024-values-draft.json',
                    stdout=StringIO(),
                )
