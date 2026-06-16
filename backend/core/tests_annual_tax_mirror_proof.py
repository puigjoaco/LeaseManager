import json
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
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
from core.annual_tax_mirror_proof import audit_annual_tax_mirror_proof
from core.annual_tax_source_manifest import EXPECTED_ANNUAL_TAX_REGISTER_KEYS, EXPECTED_DDJJ_FORMS
from patrimonio.models import Empresa, TipoInmueble
from sii.models import CapacidadSII, CapacidadTributariaSII, EstadoGateSII


class AnnualTaxMirrorProofTests(TestCase):
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
            'ownership': {
                'source_ref': 'ownership-ac2024-controlled',
                'as_of': '2024-12-31',
                'participants': [
                    {
                        'participant_ref': 'participant-controlled-one',
                        'rut': '11111111-1',
                        'name': 'Participante controlado',
                        'percentage': '100.00',
                        'vigente_desde': '2024-01-01',
                        'vigente_hasta': '',
                        'evidence_ref': 'ownership-evidence-controlled-one',
                    }
                ],
            },
            'real_estate': {
                'source_ref': 'real-estate-ac2024-controlled',
                'as_of': '2024-12-31',
                'properties': [
                    {
                        'property_ref': 'property-controlled-one',
                        'codigo_propiedad': 'RE-001',
                        'rol_avaluo': 'ROL-CONTROLADO-001',
                        'direccion': 'Propiedad controlada uno',
                        'comuna': 'Santiago',
                        'region': 'RM',
                        'tipo_inmueble': TipoInmueble.APARTMENT,
                        'evidence_ref': 'property-evidence-controlled-one',
                        'contribuciones_clp': '345000.00',
                        'contribuciones_evidence_ref': 'property-tax-evidence-controlled-one',
                        'codigo_f22': 'F22-BIENES-RAICES',
                    }
                ],
            },
        }

    def _expected_relative_path(self, category: str, artifact_key: str) -> str:
        return f'expected/{category}/{artifact_key}.txt'

    def _manifest(self, *, ready=True):
        files = [
            {
                'category': 'annual_balance_expected_output',
                'role': 'expected_output',
                'path_ref': 'expected-output-balance-general-ref',
                'artifact_key': 'balance_general',
                'relative_path': self._expected_relative_path('annual_balance_expected_output', 'balance_general'),
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
                    'relative_path': self._expected_relative_path('annual_tax_register_expected_output', key),
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
                    'relative_path': self._expected_relative_path('ddjj_expected_output', f'dj_{form}'),
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
            'safety': {
                'expected_outputs_used_as_inputs': False,
                'uses_sii_real': False,
                'uses_credentials': False,
            },
            'coverage': {'ready_for_mirror_source_bundle': ready},
            'mirror_proof_readiness': {
                'source_documentation_confirmed_for_ac2024_at2025': ready,
                'architecture_complete_for_mirror_run': ready,
            },
            'files': files,
        }

    def _write_expected_output_sources(self, source_root: Path, manifest: dict):
        for item in manifest['files']:
            path = source_root / item['relative_path']
            path.parent.mkdir(parents=True, exist_ok=True)
            if item['category'] == 'ddjj_expected_output':
                form = item['ddjj_forms'][0]
                path.write_text(f'Declaracion Jurada {form} Aceptada Folio 88{form} controlada\n', encoding='utf-8')
            elif item['category'] == 'f22_expected_output':
                path.write_text('Formulario 22 Folio 348868325 controlado\n', encoding='utf-8')
            elif item['artifact_key'] == 'balance_general':
                path.write_text('Balance AC2024 AT2025 total 1000 y 12000 controlado\n', encoding='utf-8')
            elif item['artifact_key'] in {'capital_propio', 'razonabilidad_cpt'}:
                path.write_text(f'{item["artifact_key"]} AC2024 AT2025 monto 1000 controlado\n', encoding='utf-8')
            elif item['artifact_key'] == 'rentas_empresariales':
                path.write_text(f'{item["artifact_key"]} AC2024 AT2025 montos 1000 y 12000 controlado\n', encoding='utf-8')
            elif item['artifact_key'] in {'renta_liquida', 'determinacion_rai'}:
                path.write_text(f'{item["artifact_key"]} AC2024 AT2025 monto 12000 controlado\n', encoding='utf-8')
            else:
                path.write_text(f'{item["artifact_key"]} AC2024 AT2025 total 1000 1000 controlado\n', encoding='utf-8')

    def _load_and_generate_annual_layer(self, empresa):
        apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=self._package(),
            write_database=True,
        )
        run_annual_tax_controlled_mirror(
            empresa=empresa,
            commercial_year=2024,
            tax_year=2025,
            source_label='inmobiliaria-puig-ac2024-controlled-writer',
            authorization_ref='user-authorized-local-source-review',
            responsible_ref='stage6-responsibles-v1',
            fiscal_rule_ref='ac2024-tax-rule-review-pending',
            certificates_proof_ref='ac2024-certificates-proof-pending',
            ddjj_codes=EXPECTED_DDJJ_FORMS,
            write_database=True,
        )

    def _proof_kwargs(self, empresa, manifest, source_root):
        return {
            'empresa': empresa,
            'commercial_year': 2024,
            'tax_year': 2025,
            'manifest': manifest,
            'source_root': source_root,
            'stage5_evidence_ref': 'stage5-ledger-year-controlled-v1',
            'stage4_sii_evidence_ref': 'stage4-sii-annual-controlled-v1',
            'fiscal_rule_ref': 'ac2024-tax-rule-review-pending',
            'certificates_proof_ref': 'ac2024-certificates-proof-pending',
            'responsible_ref': 'stage6-responsibles-v1',
            'source_label': 'inmobiliaria-puig-ac2024-controlled-writer',
            'authorization_ref': 'user-authorized-local-source-review',
            'source_kind': 'snapshot_controlado',
        }

    def test_mirror_proof_combines_source_comparison_stage6_and_safety_without_false_completion(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            manifest = self._manifest()
            self._write_expected_output_sources(source_root, manifest)
            result = audit_annual_tax_mirror_proof(**self._proof_kwargs(empresa, manifest, source_root))

        self.assertEqual(result['summary']['classification'], 'parcial')
        self.assertFalse(result['summary']['ready_for_architecture_proof'])
        self.assertFalse(result['summary']['ready_for_objective_completion'])
        self.assertTrue(result['checks']['source_documentation_confirmed'])
        self.assertFalse(result['checks']['comparison_ready_for_mirror_conclusion'])
        self.assertFalse(result['checks']['stage6_ready_for_renta_anual'])
        self.assertTrue(result['checks']['safety_boundary_ok'])
        self.assertIn('comparison.generated_artifacts_require_review', result['summary']['blockers'])
        self.assertIn('stage6.tax_review_checklist_incomplete', result['summary']['blockers'])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])
        self.assertTrue(result['safety']['expected_outputs_used_as_comparison_only'])
        self.assertFalse(result['safety']['final_tax_calculation'])
        evidence = result['comparison_generated_artifact_evidence']
        self.assertGreater(evidence['process']['process_id'], 0)
        self.assertGreater(evidence['process']['source_bundle_id'], 0)
        self.assertEqual(len(evidence['process']['source_bundle_hash']), 64)
        self.assertEqual(len(evidence['artifact_matrix']['hash_matriz']), 64)
        self.assertEqual(len(evidence['dossier']['hash_dossier']), 64)
        self.assertEqual(len(evidence['annual_export']['hash_export']), 64)
        self.assertEqual(len(evidence['review_checklist']['hash_checklist']), 64)
        self.assertFalse(evidence['annual_export']['official_format'])
        self.assertFalse(evidence['annual_export']['sii_submission'])
        self.assertFalse(evidence['annual_export']['final_tax_calculation'])
        rendered_evidence = json.dumps(evidence, default=str).lower()
        for forbidden in ('source_payload', 'export_payload', 'review_payload', 'resumen_', 'password', 'secret', 'token'):
            self.assertNotIn(forbidden, rendered_evidence)

    def test_mirror_proof_reports_source_gap_without_masking_artifact_review(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            manifest = self._manifest(ready=False)
            self._write_expected_output_sources(source_root, manifest)
            result = audit_annual_tax_mirror_proof(**self._proof_kwargs(empresa, manifest, source_root))

        self.assertEqual(result['summary']['classification'], 'parcial')
        self.assertFalse(result['summary']['ready_for_architecture_proof'])
        self.assertFalse(result['summary']['ready_for_objective_completion'])
        self.assertIn('source_documentation_not_confirmed', result['summary']['blockers'])
        self.assertIn('comparison.generated_artifacts_require_review', result['summary']['blockers'])

    def test_command_writes_proof_and_refuses_versioned_output(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_root = temp_path / 'source'
            source_root.mkdir()
            manifest = self._manifest()
            self._write_expected_output_sources(source_root, manifest)
            manifest_path = temp_path / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            output_path = Path(settings.PROJECT_ROOT) / 'local-evidence' / 'stage6' / 'mirror-proof-test.json'
            stdout = StringIO()
            call_command(
                'audit_annual_tax_mirror_proof',
                '--empresa-id',
                str(empresa.id),
                '--commercial-year',
                '2024',
                '--tax-year',
                '2025',
                '--manifest',
                str(manifest_path),
                '--source-root',
                str(source_root),
                '--source-label',
                'inmobiliaria-puig-ac2024-controlled-writer',
                '--authorization-ref',
                'user-authorized-local-source-review',
                '--stage5-evidence-ref',
                'stage5-ledger-year-controlled-v1',
                '--stage4-sii-evidence-ref',
                'stage4-sii-annual-controlled-v1',
                '--fiscal-rule-ref',
                'ac2024-tax-rule-review-pending',
                '--certificates-proof-ref',
                'ac2024-certificates-proof-pending',
                '--responsible-ref',
                'stage6-responsibles-v1',
                '--source-kind',
                'snapshot_controlado',
                '--output',
                str(output_path),
                stdout=stdout,
            )
            written = json.loads(output_path.read_text(encoding='utf-8'))
            with self.assertRaises(CommandError):
                call_command(
                    'audit_annual_tax_mirror_proof',
                    '--empresa-id',
                    str(empresa.id),
                    '--commercial-year',
                    '2024',
                    '--tax-year',
                    '2025',
                    '--manifest',
                    str(manifest_path),
                    '--source-root',
                    str(source_root),
                    '--source-label',
                    'inmobiliaria-puig-ac2024-controlled-writer',
                    '--authorization-ref',
                    'user-authorized-local-source-review',
                    '--stage5-evidence-ref',
                    'stage5-ledger-year-controlled-v1',
                    '--stage4-sii-evidence-ref',
                    'stage4-sii-annual-controlled-v1',
                    '--fiscal-rule-ref',
                    'ac2024-tax-rule-review-pending',
                    '--certificates-proof-ref',
                    'ac2024-certificates-proof-pending',
                    '--responsible-ref',
                    'stage6-responsibles-v1',
                    '--source-kind',
                    'snapshot_controlado',
                    '--fail-on-incomplete',
                )
            with self.assertRaises(CommandError):
                call_command(
                    'audit_annual_tax_mirror_proof',
                    '--empresa-id',
                    str(empresa.id),
                    '--commercial-year',
                    '2024',
                    '--tax-year',
                    '2025',
                    '--manifest',
                    str(manifest_path),
                    '--source-root',
                    str(source_root),
                    '--source-label',
                    'inmobiliaria-puig-ac2024-controlled-writer',
                    '--authorization-ref',
                    'user-authorized-local-source-review',
                    '--stage5-evidence-ref',
                    'stage5-ledger-year-controlled-v1',
                    '--stage4-sii-evidence-ref',
                    'stage4-sii-annual-controlled-v1',
                    '--fiscal-rule-ref',
                    'ac2024-tax-rule-review-pending',
                    '--certificates-proof-ref',
                    'ac2024-certificates-proof-pending',
                    '--responsible-ref',
                    'stage6-responsibles-v1',
                    '--source-kind',
                    'snapshot_controlado',
                    '--output',
                    'mirror-proof.json',
                )

        self.assertFalse(written['summary']['ready_for_objective_completion'])
        self.assertIn('comparison.generated_artifacts_require_review', written['summary']['blockers'])
