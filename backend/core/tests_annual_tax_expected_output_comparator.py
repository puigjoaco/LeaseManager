import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoPreparacionTributaria
from contabilidad.services import ensure_default_regime
from core.annual_tax_controlled_db_load import (
    CONTROLLED_DB_LOAD_SCHEMA_VERSION,
    apply_annual_tax_controlled_db_load,
)
from core.annual_tax_controlled_mirror_run import run_annual_tax_controlled_mirror
from core.annual_tax_expected_output_comparator import compare_annual_tax_expected_outputs
from core.annual_tax_source_manifest import EXPECTED_ANNUAL_TAX_REGISTER_KEYS, EXPECTED_DDJJ_FORMS
from patrimonio.models import Empresa
from sii.models import CapacidadSII, CapacidadTributariaSII, EstadoGateSII


class AnnualTaxExpectedOutputComparatorTests(TestCase):
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
            ddjj_habilitadas=list(EXPECTED_DDJJ_FORMS),
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
            no_declaration = month in {2, 12}
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

    def _manifest(self):
        files = [
            {
                'category': 'annual_balance_expected_output',
                'role': 'expected_output',
                'path_ref': 'expected-output-balance-general-ref',
                'artifact_key': 'balance_general',
                'output_status': '',
            },
            {
                'category': 'f22_expected_output',
                'role': 'expected_output',
                'path_ref': 'expected-output-f22-ref',
                'artifact_key': 'f22',
                'output_status': '',
            },
        ]
        for key in EXPECTED_ANNUAL_TAX_REGISTER_KEYS:
            files.append(
                {
                    'category': 'annual_tax_register_expected_output',
                    'role': 'expected_output',
                    'path_ref': f'expected-output-{key}-ref',
                    'artifact_key': key,
                    'output_status': '',
                }
            )
        for form in EXPECTED_DDJJ_FORMS:
            files.append(
                {
                    'category': 'ddjj_expected_output',
                    'role': 'expected_output',
                    'path_ref': f'expected-output-dj-{form}-ref',
                    'artifact_key': f'dj_{form}',
                    'ddjj_forms': [form],
                    'output_status': 'accepted',
                }
            )
        return {
            'schema_version': 'annual-tax-source-manifest.v1',
            'hash_manifest': 'b' * 64,
            'company_ref': 'inmobiliaria-puig',
            'commercial_year': 2024,
            'tax_year': 2025,
            'files': files,
        }

    def _load_and_generate_annual_layer(self, empresa):
        apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=self._package(),
            write_database=True,
        )
        return run_annual_tax_controlled_mirror(
            empresa=empresa,
            commercial_year=2024,
            tax_year=2025,
            source_label='inmobiliaria-puig-ac2024-controlled-writer',
            authorization_ref='user-authorized-local-source-review',
            responsible_ref='codex-local-review',
            fiscal_rule_ref='ac2024-tax-rule-review-pending',
            certificates_proof_ref='ac2024-certificates-proof-pending',
            ddjj_codes=EXPECTED_DDJJ_FORMS,
            write_database=True,
        )

    def test_comparator_matches_generated_coverage_without_using_expected_outputs_as_inputs(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        result = compare_annual_tax_expected_outputs(
            empresa=empresa,
            commercial_year=2024,
            tax_year=2025,
            manifest=self._manifest(),
        )

        self.assertTrue(result['summary']['coverage_ready_for_content_comparison'])
        self.assertFalse(result['summary']['ready_for_mirror_conclusion'])
        self.assertIn('expected_output_content_extractors_missing', result['summary']['blockers'])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])
        self.assertTrue(result['safety']['expected_outputs_used_as_comparison_only'])
        self.assertFalse(result['comparison_scope']['content_comparison_performed'])
        self.assertTrue(result['matches']['annual_balance_expected_output']['matched'])
        self.assertEqual(result['matches']['annual_tax_register_expected_output']['missing_artifact_keys'], [])
        self.assertEqual(result['matches']['ddjj_expected_output']['missing_forms'], [])
        self.assertTrue(result['matches']['f22_expected_output']['matched'])

    def test_comparator_reports_missing_annual_process_as_blocker(self):
        empresa = self._create_empresa()

        result = compare_annual_tax_expected_outputs(
            empresa=empresa,
            commercial_year=2024,
            tax_year=2025,
            manifest=self._manifest(),
        )

        self.assertFalse(result['summary']['coverage_ready_for_content_comparison'])
        self.assertIn('annual_process_missing', result['summary']['blockers'])
        self.assertIn('expected_output_coverage_mismatch', result['summary']['blockers'])

    def test_command_writes_comparison_and_refuses_versioned_output_outside_local_evidence(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            manifest_path = temp_path / 'manifest.json'
            output_path = temp_path / 'comparison.json'
            manifest_path.write_text(json.dumps(self._manifest(), ensure_ascii=True), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'compare_annual_tax_expected_outputs',
                empresa_id=empresa.id,
                commercial_year=2024,
                tax_year=2025,
                manifest=str(manifest_path),
                output=str(output_path),
                stdout=stdout,
            )
            result = json.loads(output_path.read_text(encoding='utf-8'))

            self.assertEqual(stdout.getvalue(), '')
            self.assertTrue(result['summary']['coverage_ready_for_content_comparison'])

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'compare_annual_tax_expected_outputs',
                    empresa_id=empresa.id,
                    commercial_year=2024,
                    tax_year=2025,
                    manifest=str(manifest_path),
                    output='docs/ac2024-expected-output-comparison.json',
                    stdout=StringIO(),
                )
