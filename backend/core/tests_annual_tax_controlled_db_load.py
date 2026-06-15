import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    LibroDiario,
    LibroMayor,
    ObligacionTributariaMensual,
)
from contabilidad.services import ensure_default_regime
from core.annual_tax_controlled_db_load import (
    CONTROLLED_DB_LOAD_SCHEMA_VERSION,
    apply_annual_tax_controlled_db_load,
)
from patrimonio.models import Empresa
from sii.models import (
    CapacidadSII,
    CapacidadTributariaSII,
    EstadoGateSII,
    EstadoMonthlyTaxFact,
    F29PreparacionMensual,
    MonthlyTaxFact,
)


class AnnualTaxControlledDbLoadTests(TestCase):
    def _create_empresa(self):
        empresa = Empresa.objects.create(
            razon_social='Inmobiliaria Puig Controlada SpA',
            rut='77777777-7',
            estado='activa',
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=['1887'],
            inicio_ejercicio=date(2024, 1, 1),
            moneda_funcional='CLP',
            estado='activa',
        )
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.F29_PREPARACION,
            certificado_ref='f29-certificacion-controlada',
            evidencia_ref='f29-evidencia-controlada',
            prueba_flujo_ref='f29-flujo-controlado',
            autorizacion_ambiente_ref='f29-ambiente-controlado',
            regla_fiscal_ref='f29-regla-controlada',
            estado_gate=EstadoGateSII.OPEN,
        )
        return empresa

    def _package(self, *, months=range(1, 13)):
        return {
            'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_manifest_hash': 'a' * 64,
            'responsible_ref': 'codex-controlled-load',
            'approval_ref': 'joaquin-controlled-ac2024-proof',
            'expected_outputs_used_as_inputs': False,
            'months': [
                {
                    'month': month,
                    'source_ref': f'ac2024-month-{month:02d}-controlled',
                    'ledger': {
                        'libro_diario_ref': f'libro-diario-2024-{month:02d}-controlled',
                        'libro_mayor_ref': f'libro-mayor-2024-{month:02d}-controlled',
                        'asientos_count': month,
                        'cuentas_count': month + 10,
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
                            'estado_preparacion': EstadoPreparacionTributaria.PREPARED,
                            'source_ref': f'ppm-2024-{month:02d}-controlled',
                        }
                    ],
                    'f29': {
                        'estado_preparacion': EstadoPreparacionTributaria.PREPARED,
                        'borrador_ref': f'f29-2024-{month:02d}-controlled',
                        'resumen': {'declarado': True, 'month': month},
                    },
                    'payroll': {
                        'source_ref': f'payroll-2024-{month:02d}-controlled',
                        'has_movements': False,
                    },
                }
                for month in months
            ],
        }

    def test_apply_controlled_package_materializes_monthly_accounting_and_tax_facts(self):
        empresa = self._create_empresa()

        result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=self._package(),
            write_database=True,
        )

        self.assertTrue(result['writes_database'])
        self.assertTrue(result['ready_for_annual_generation'])
        self.assertEqual(result['months_loaded'], list(range(1, 13)))
        self.assertEqual(CierreMensualContable.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(LibroDiario.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(LibroMayor.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(BalanceComprobacion.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(ObligacionTributariaMensual.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(F29PreparacionMensual.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 12)
        self.assertFalse(
            MonthlyTaxFact.objects.filter(
                empresa=empresa,
            ).exclude(estado=EstadoMonthlyTaxFact.NORMALIZED).exists()
        )
        self.assertFalse(
            CierreMensualContable.objects.filter(
                empresa=empresa,
            ).exclude(estado=EstadoCierreMensual.APPROVED).exists()
        )
        fact = MonthlyTaxFact.objects.get(empresa=empresa, mes=1)
        self.assertFalse(fact.resumen_hecho['expected_outputs_used_as_inputs'])
        self.assertFalse(fact.resumen_hecho['final_tax_calculation'])

        second_result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=self._package(),
            write_database=True,
        )
        self.assertEqual(second_result['created_updated']['CierreMensualContable']['updated'], 12)
        self.assertEqual(CierreMensualContable.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 12)

    def test_apply_rejects_expected_outputs_as_inputs_without_writing(self):
        empresa = self._create_empresa()
        package = self._package(months=range(1, 2))
        package['months'][0]['ddjj_expected_output'] = {'form': '1887'}

        with self.assertRaisesMessage(ValueError, 'salidas esperadas'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(CierreMensualContable.objects.filter(empresa=empresa).count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_command_dry_run_validates_package_without_db_writes_and_restricts_output(self):
        empresa = self._create_empresa()
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'controlled-load.json'
            package_path.write_text(json.dumps(self._package(months=range(1, 3))), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'apply_annual_tax_controlled_db_load',
                package=str(package_path),
                empresa_id=empresa.id,
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertFalse(result['writes_database'])
            self.assertFalse(result['ready_for_annual_generation'])
            self.assertEqual(result['months_validated'], [1, 2])
            self.assertEqual(result['blockers'], ['controlled_package_incomplete_12_months'])
            self.assertEqual(CierreMensualContable.objects.filter(empresa=empresa).count(), 0)

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'apply_annual_tax_controlled_db_load',
                    package=str(package_path),
                    empresa_id=empresa.id,
                    output='docs/ac2024-controlled-db-load.json',
                    stdout=StringIO(),
                )

    def test_command_accepts_template_wrapper_package_draft(self):
        empresa = self._create_empresa()
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'controlled-load-wrapper.json'
            package_path.write_text(
                json.dumps(
                    {
                        'schema_version': 'annual-tax-controlled-values-draft.v1',
                        'package_draft': self._package(months=range(1, 2)),
                        'comparison_targets': {
                            'f22_expected_output': [
                                {'path_ref': 'f22-final-controlado', 'category': 'f22_expected_output'}
                            ],
                        },
                    }
                ),
                encoding='utf-8',
            )
            stdout = StringIO()

            call_command(
                'apply_annual_tax_controlled_db_load',
                package=str(package_path),
                empresa_id=empresa.id,
                stdout=stdout,
            )

        result = json.loads(stdout.getvalue())
        self.assertFalse(result['writes_database'])
        self.assertEqual(result['months_validated'], [1])
        self.assertEqual(CierreMensualContable.objects.filter(empresa=empresa).count(), 0)

    def test_apply_skips_f29_object_for_controlled_no_declaration_month(self):
        empresa = self._create_empresa()
        package = self._package()
        package['months'][1]['f29'] = {
            'estado_preparacion': EstadoPreparacionTributaria.NOT_APPLICABLE,
            'borrador_ref': '',
            'resumen': {
                'no_declaration': True,
                'source': 'manifest.f29_no_declaration_months',
            },
        }

        result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )

        self.assertTrue(result['ready_for_annual_generation'])
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 12)
        self.assertEqual(F29PreparacionMensual.objects.filter(empresa=empresa).count(), 11)
        february = MonthlyTaxFact.objects.get(empresa=empresa, mes=2)
        self.assertIsNone(february.f29_preparacion_id)
        self.assertTrue(february.resumen_hecho['f29']['resumen']['no_declaration'])

    def test_command_apply_writes_only_when_explicit_apply_flag_is_present(self):
        empresa = self._create_empresa()
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'controlled-load.json'
            package_path.write_text(json.dumps(self._package(months=range(1, 2))), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'apply_annual_tax_controlled_db_load',
                package=str(package_path),
                empresa_id=empresa.id,
                apply=True,
                stdout=stdout,
            )

        result = json.loads(stdout.getvalue())
        self.assertTrue(result['writes_database'])
        self.assertEqual(result['months_loaded'], [1])
        self.assertEqual(CierreMensualContable.objects.filter(empresa=empresa).count(), 1)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 1)
