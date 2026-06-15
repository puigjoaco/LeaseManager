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

    def _expected_relative_path(self, category: str, artifact_key: str) -> str:
        return f'expected/{category}/{artifact_key}.txt'

    def _write_expected_output_sources(self, source_root: Path, manifest: dict):
        for item in manifest['files']:
            relative_path = item['relative_path']
            path = source_root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if item['category'] == 'ddjj_expected_output':
                form = item['ddjj_forms'][0]
                path.write_text(
                    f'Declaracion Jurada {form} Aceptada Folio 88{form} controlada\n',
                    encoding='utf-8',
                )
            elif item['category'] == 'f22_expected_output':
                path.write_text('Formulario 22 Folio 348868325 controlado\n', encoding='utf-8')
            else:
                path.write_text(
                    f'{item["artifact_key"]} AC2024 AT2025 total 1000 1000 controlado\n',
                    encoding='utf-8',
                )

    def _manifest(self):
        files = [
            {
                'category': 'annual_balance_expected_output',
                'role': 'expected_output',
                'path_ref': 'expected-output-balance-general-ref',
                'artifact_key': 'balance_general',
                'relative_path': self._expected_relative_path(
                    'annual_balance_expected_output',
                    'balance_general',
                ),
                'output_status': '',
            },
            {
                'category': 'f22_expected_output',
                'role': 'expected_output',
                'path_ref': 'expected-output-f22-ref',
                'artifact_key': 'f22',
                'relative_path': self._expected_relative_path('f22_expected_output', 'f22'),
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
                    'relative_path': self._expected_relative_path(
                        'annual_tax_register_expected_output',
                        key,
                    ),
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
                    'relative_path': self._expected_relative_path(
                        'ddjj_expected_output',
                        f'dj_{form}',
                    ),
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

    def test_comparator_matches_generated_coverage_and_identity_without_using_expected_outputs_as_inputs(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            manifest = self._manifest()
            self._write_expected_output_sources(source_root, manifest)

            result = compare_annual_tax_expected_outputs(
                empresa=empresa,
                commercial_year=2024,
                tax_year=2025,
                manifest=manifest,
                source_root=source_root,
            )

        self.assertTrue(result['summary']['coverage_ready_for_content_comparison'])
        self.assertTrue(result['summary']['content_identity_extractors_ready'])
        self.assertFalse(result['summary']['value_equality_extractors_ready'])
        self.assertFalse(result['summary']['ready_for_mirror_conclusion'])
        self.assertIn('expected_output_value_extractors_missing', result['summary']['blockers'])
        self.assertNotIn('expected_output_identity_extractors_not_run', result['summary']['blockers'])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])
        self.assertTrue(result['safety']['expected_outputs_used_as_comparison_only'])
        self.assertFalse(result['safety']['stores_raw_expected_output_text'])
        self.assertTrue(result['comparison_scope']['content_identity_extraction_performed'])
        self.assertTrue(result['comparison_scope']['content_comparison_performed'])
        self.assertFalse(result['comparison_scope']['numeric_equality_performed'])
        self.assertEqual(result['comparison_scope']['level'], 'coverage_traceability_and_identity')
        self.assertTrue(result['matches']['annual_balance_expected_output']['matched'])
        self.assertEqual(result['matches']['annual_tax_register_expected_output']['missing_artifact_keys'], [])
        self.assertEqual(result['matches']['ddjj_expected_output']['missing_forms'], [])
        self.assertTrue(result['matches']['f22_expected_output']['matched'])
        self.assertTrue(result['matches']['ddjj_content_identity']['matched'])
        self.assertTrue(result['matches']['f22_content_identity']['matched'])
        self.assertTrue(result['matches']['annual_balance_content_identity']['matched'])
        self.assertTrue(result['matches']['annual_tax_register_content_identity']['matched'])
        self.assertTrue(result['expected_output_content_signals']['summary']['identity_signals_ready'])
        self.assertFalse(
            result['expected_output_content_signals']['summary']['value_equality_extractors_ready']
        )
        self.assertEqual(result['expected_output_content_signals']['summary']['extraction_errors_total'], 0)

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
        self.assertIn('expected_output_identity_extractors_not_run', result['summary']['blockers'])
        self.assertIn('expected_output_value_extractors_missing', result['summary']['blockers'])

    def test_command_writes_comparison_and_refuses_versioned_output_outside_local_evidence(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_root = temp_path / 'source'
            source_root.mkdir()
            manifest = self._manifest()
            self._write_expected_output_sources(source_root, manifest)
            manifest_path = temp_path / 'manifest.json'
            output_path = temp_path / 'comparison.json'
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=True), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'compare_annual_tax_expected_outputs',
                empresa_id=empresa.id,
                commercial_year=2024,
                tax_year=2025,
                manifest=str(manifest_path),
                source_root=str(source_root),
                output=str(output_path),
                stdout=stdout,
            )
            result = json.loads(output_path.read_text(encoding='utf-8'))

            self.assertEqual(stdout.getvalue(), '')
            self.assertTrue(result['summary']['coverage_ready_for_content_comparison'])
            self.assertTrue(result['summary']['content_identity_extractors_ready'])
            self.assertFalse(result['summary']['value_equality_extractors_ready'])

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
