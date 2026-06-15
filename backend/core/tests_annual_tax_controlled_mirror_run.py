import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase

from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoPreparacionTributaria
from contabilidad.services import ensure_default_regime
from core.annual_tax_controlled_db_load import (
    CONTROLLED_DB_LOAD_SCHEMA_VERSION,
    apply_annual_tax_controlled_db_load,
)
from core.annual_tax_controlled_mirror_run import run_annual_tax_controlled_mirror
from patrimonio.models import Empresa
from sii.models import (
    AnnualTaxSourceBundle,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    EstadoGateSII,
    F22PreparacionAnual,
    ProcesoRentaAnual,
)


class AnnualTaxControlledMirrorRunTests(TestCase):
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

    def _package(self):
        months = []
        for month in range(1, 13):
            no_declaration = month == 2
            months.append(
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
                    'obligations': []
                    if no_declaration
                    else [
                        {
                            'tipo': 'PPM',
                            'base_imponible': '1000.00',
                            'monto_calculado': '10.00',
                            'estado_preparacion': EstadoPreparacionTributaria.PREPARED,
                            'source_ref': f'ppm-2024-{month:02d}-controlled',
                        }
                    ],
                    'f29': {
                        'estado_preparacion': EstadoPreparacionTributaria.NOT_APPLICABLE,
                        'borrador_ref': '',
                        'resumen': {'no_declaration': True, 'source': 'manifest.f29_no_declaration_months'},
                    }
                    if no_declaration
                    else {
                        'estado_preparacion': EstadoPreparacionTributaria.PREPARED,
                        'borrador_ref': f'f29-2024-{month:02d}-controlled',
                        'resumen': {'declarado': True, 'month': month},
                    },
                    'payroll': {
                        'source_ref': f'payroll-2024-{month:02d}-controlled',
                        'has_movements': False,
                    },
                }
            )
        return {
            'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_manifest_hash': 'a' * 64,
            'responsible_ref': 'codex-controlled-load',
            'approval_ref': 'joaquin-controlled-ac2024-proof',
            'expected_outputs_used_as_inputs': False,
            'months': months,
        }

    def _load_monthly_package(self, empresa):
        return apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=self._package(),
            write_database=True,
        )

    def _mirror_kwargs(self, empresa):
        return {
            'empresa': empresa,
            'commercial_year': 2024,
            'tax_year': 2025,
            'source_label': 'inmobiliaria-puig-ac2024-controlled-writer',
            'authorization_ref': 'user-authorized-local-source-review',
            'responsible_ref': 'codex-local-review',
            'fiscal_rule_ref': 'ac2024-tax-rule-review-pending',
            'certificates_proof_ref': 'ac2024-certificates-proof-pending',
        }

    def test_controlled_mirror_dry_run_does_not_generate_annual_records(self):
        empresa = self._create_empresa()
        self._load_monthly_package(empresa)

        result = run_annual_tax_controlled_mirror(**self._mirror_kwargs(empresa))

        self.assertFalse(result['writes_database'])
        self.assertTrue(result['ready_for_generation'])
        self.assertFalse(result['generated'])
        self.assertEqual(result['monthly_tax_fact_months'], list(range(1, 13)))
        self.assertEqual(ProcesoRentaAnual.objects.count(), 0)

    def test_controlled_mirror_generates_annual_layer_with_no_declaration_month(self):
        empresa = self._create_empresa()
        self._load_monthly_package(empresa)

        result = run_annual_tax_controlled_mirror(
            **self._mirror_kwargs(empresa),
            write_database=True,
        )

        self.assertTrue(result['writes_database'])
        self.assertTrue(result['generated'])
        self.assertEqual(result['blockers'], [])
        self.assertEqual(ProcesoRentaAnual.objects.count(), 1)
        self.assertEqual(DDJJPreparacionAnual.objects.count(), 1)
        self.assertEqual(F22PreparacionAnual.objects.count(), 1)
        bundle = AnnualTaxSourceBundle.objects.get()
        self.assertEqual(bundle.source_label, 'inmobiliaria-puig-ac2024-controlled-writer')
        self.assertEqual(bundle.resumen_fuentes['monthly_tax_fact_months'], list(range(1, 13)))
        self.assertEqual(bundle.resumen_fuentes['obligation_months'], [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

    def test_command_dry_run_writes_output_only_under_local_evidence(self):
        empresa = self._create_empresa()
        self._load_monthly_package(empresa)
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'mirror-run.json'
            stdout = StringIO()
            call_command(
                'run_annual_tax_controlled_mirror',
                empresa_id=empresa.id,
                commercial_year=2024,
                tax_year=2025,
                source_label='inmobiliaria-puig-ac2024-controlled-writer',
                authorization_ref='user-authorized-local-source-review',
                responsible_ref='codex-local-review',
                fiscal_rule_ref='ac2024-tax-rule-review-pending',
                certificates_proof_ref='ac2024-certificates-proof-pending',
                output=str(output_path),
                stdout=stdout,
            )

            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertFalse(result['writes_database'])
        self.assertTrue(result['ready_for_generation'])
        self.assertEqual(stdout.getvalue(), '')
