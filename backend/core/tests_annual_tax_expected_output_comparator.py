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
from core.annual_tax_expected_output_content import extract_expected_output_value_signals
from core.annual_tax_expected_output_comparator import compare_annual_tax_expected_outputs
from core.annual_tax_source_manifest import EXPECTED_ANNUAL_TAX_REGISTER_KEYS, EXPECTED_DDJJ_FORMS
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from patrimonio.models import Empresa
from sii.models import CapacidadSII, CapacidadTributariaSII, EstadoGateSII, ProcesoRentaAnual
from sii.services import mark_annual_tax_generated_warnings_reviewed


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
            elif item['artifact_key'] == 'balance_general':
                path.write_text('Balance AC2024 AT2025 total 1000 y 12000 controlado\n', encoding='utf-8')
            elif item['artifact_key'] in {'capital_propio', 'razonabilidad_cpt'}:
                path.write_text(f'{item["artifact_key"]} AC2024 AT2025 monto 1000 controlado\n', encoding='utf-8')
            elif item['artifact_key'] == 'rentas_empresariales':
                path.write_text(
                    f'{item["artifact_key"]} AC2024 AT2025 montos 1000 y 12000 controlado\n',
                    encoding='utf-8',
                )
            elif item['artifact_key'] in {'renta_liquida', 'determinacion_rai'}:
                path.write_text(f'{item["artifact_key"]} AC2024 AT2025 monto 12000 controlado\n', encoding='utf-8')
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

    def test_expected_value_extractor_does_not_merge_account_digits_with_amount_columns(self):
        manifest = {
            'schema_version': 'annual-tax-source-manifest.v1',
            'commercial_year': 2024,
            'tax_year': 2025,
            'files': [
                {
                    'category': 'annual_balance_expected_output',
                    'role': 'expected_output',
                    'path_ref': 'expected-output-balance-general-ref',
                    'artifact_key': 'balance_general',
                    'relative_path': 'expected/balance.txt',
                    'output_status': '',
                }
            ],
        }
        generated_targets = [
            {
                'target_key': 'trial_balance:12030101:sumas_debe_clp',
                'category': 'annual_balance_expected_output',
                'artifact_key': 'balance_general',
                'amount_token': '123456789',
            },
            {
                'target_key': 'trial_balance:12030101:inventario_activo_clp',
                'category': 'annual_balance_expected_output',
                'artifact_key': 'balance_general',
                'amount_token': '987654321',
            },
        ]

        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            expected_path = source_root / 'expected' / 'balance.txt'
            expected_path.parent.mkdir(parents=True)
            expected_path.write_text(
                '12030101 Local 19 123.456.789 987.654.321\n',
                encoding='utf-8',
            )

            result = extract_expected_output_value_signals(
                source_root=source_root,
                manifest=manifest,
                generated_targets=generated_targets,
            )

        self.assertTrue(result['summary']['target_value_presence_ready'])
        self.assertEqual(result['summary']['missing_targets_total'], 0)
        self.assertEqual(
            {item['target_key']: item['matched'] for item in result['comparisons']},
            {
                'trial_balance:12030101:sumas_debe_clp': True,
                'trial_balance:12030101:inventario_activo_clp': True,
            },
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
        self.assertTrue(result['summary']['document_semantic_extractors_ready'])
        self.assertTrue(result['summary']['value_equality_extractors_ready'])
        self.assertFalse(result['summary']['ready_for_mirror_conclusion'])
        self.assertNotIn('expected_output_value_extractors_partial', result['summary']['blockers'])
        self.assertNotIn('expected_output_document_semantic_mismatch', result['summary']['blockers'])
        self.assertIn('generated_artifacts_require_review', result['summary']['blockers'])
        self.assertNotIn('expected_output_value_mismatch', result['summary']['blockers'])
        self.assertNotIn('expected_output_identity_extractors_not_run', result['summary']['blockers'])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])
        self.assertTrue(result['safety']['expected_outputs_used_as_comparison_only'])
        self.assertFalse(result['safety']['stores_raw_expected_output_text'])
        self.assertTrue(result['comparison_scope']['content_identity_extraction_performed'])
        self.assertTrue(result['comparison_scope']['content_comparison_performed'])
        self.assertTrue(result['comparison_scope']['document_semantic_extraction_performed'])
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
        self.assertTrue(result['matches']['expected_output_document_semantics']['matched'])
        self.assertEqual(result['matches']['expected_output_document_semantics']['missing_documents_total'], 0)
        self.assertTrue(result['matches']['expected_output_value_presence']['matched'])
        self.assertTrue(result['matches']['expected_output_value_presence']['target_value_presence_ready'])
        self.assertTrue(result['expected_output_content_signals']['summary']['identity_signals_ready'])
        self.assertFalse(
            result['expected_output_content_signals']['summary']['value_equality_extractors_ready']
        )
        self.assertEqual(result['expected_output_content_signals']['summary']['extraction_errors_total'], 0)
        self.assertTrue(
            result['expected_output_document_semantic_signals']['summary']['document_semantic_ready']
        )
        self.assertEqual(
            result['expected_output_document_semantic_signals']['summary']['missing_documents_total'],
            0,
        )
        self.assertFalse(result['expected_output_document_semantic_signals']['safety']['stores_raw_text'])
        self.assertFalse(result['expected_output_document_semantic_signals']['safety']['stores_raw_folios'])
        self.assertTrue(result['expected_output_value_signals']['summary']['target_value_presence_ready'])
        self.assertTrue(result['expected_output_value_signals']['summary']['value_equality_extractors_ready'])
        self.assertEqual(result['expected_output_value_signals']['summary']['missing_targets_total'], 0)

    def test_reviewed_generated_artifact_chain_unlocks_mirror_conclusion_without_final_tax_claim(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)
        process = ProcesoRentaAnual.objects.get(empresa=empresa, anio_tributario=2025)

        acknowledgement = mark_annual_tax_generated_warnings_reviewed(
            process,
            warning_review_ref='stage6-generated-artifact-review-ac2024-at2025',
            apply=True,
        )

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

        self.assertTrue(acknowledgement['ready_for_generated_artifact_review'])
        self.assertTrue(acknowledgement['safety']['writes_database'])
        self.assertFalse(acknowledgement['safety']['uses_sii_real'])
        self.assertFalse(acknowledgement['safety']['sii_submission'])
        self.assertFalse(acknowledgement['safety']['final_tax_calculation'])
        self.assertEqual(acknowledgement['after']['pending_warnings_total'], 0)
        self.assertTrue(result['summary']['ready_for_mirror_conclusion'])
        self.assertNotIn('generated_artifacts_require_review', result['summary']['blockers'])
        self.assertFalse(result['safety']['uses_expected_outputs_as_inputs'])
        self.assertFalse(result['safety']['final_tax_calculation'])
        compared_target_keys = {
            item['target_key']
            for item in result['expected_output_value_signals']['comparisons']
        }
        self.assertNotIn('workbook:CPT:CPT-CASH-ASSET', compared_target_keys)
        self.assertNotIn('workbook:RLI:RLI-LEASE-REVENUE', compared_target_keys)
        self.assertEqual(
            result['expected_output_value_signals']['unsupported_expected_categories'],
            [],
        )
        self.assertEqual(
            result['expected_output_value_signals']['semantic_supported_categories'],
            ['ddjj_expected_output', 'f22_expected_output'],
        )
        self.assertFalse(result['expected_output_value_signals']['safety']['stores_raw_text'])
        self.assertFalse(result['expected_output_value_signals']['safety']['stores_raw_numeric_tokens'])
        self.assertFalse(result['expected_output_value_signals']['safety']['stores_raw_amounts'])
        evidence = result['generated_inventory']['generated_artifact_evidence']
        self.assertEqual(evidence['process']['process_id'], result['generated_inventory']['process_id'])
        self.assertEqual(len(evidence['process']['source_bundle_hash']), 64)
        self.assertEqual(len(evidence['trial_balances']), 1)
        self.assertGreater(evidence['trial_balances'][0]['lines_total'], 0)
        self.assertEqual(len(evidence['trial_balances'][0]['hash_balance']), 64)
        self.assertEqual(set(evidence['workbooks_by_type']), {'CPT', 'RLI'})
        for workbook in evidence['workbooks_by_type'].values():
            self.assertGreater(workbook['lines_total'], 0)
            self.assertEqual(len(workbook['hash_workbook']), 64)
        self.assertEqual(set(evidence['enterprise_registers_by_type']), {'DIVIDENDOS', 'RAI', 'RETIROS', 'SAC'})
        for register in evidence['enterprise_registers_by_type'].values():
            self.assertGreater(register['movements_total'], 0)
            self.assertEqual(len(register['hash_registro']), 64)
        self.assertIsNotNone(evidence['ddjj'])
        self.assertIsNotNone(evidence['f22'])
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

    def test_generated_artifact_evidence_redacts_sensitive_historical_refs(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)
        ProcesoRentaAnual.objects.filter(empresa=empresa, anio_tributario=2025).update(
            paquete_ddjj_ref='https://private.example.test/token',
        )

        result = compare_annual_tax_expected_outputs(
            empresa=empresa,
            commercial_year=2024,
            tax_year=2025,
            manifest=self._manifest(),
        )

        evidence = result['generated_inventory']['generated_artifact_evidence']
        self.assertEqual(evidence['process']['ddjj_package_ref'], REDACTED_SENSITIVE_REFERENCE)
        rendered_evidence = json.dumps(evidence, default=str)
        self.assertNotIn('https://private.example.test/token', rendered_evidence)

    def test_non_decisive_expected_output_extraction_errors_do_not_block_identity_or_semantics(self):
        empresa = self._create_empresa()
        self._load_and_generate_annual_layer(empresa)

        with TemporaryDirectory() as temp_dir:
            source_root = Path(temp_dir)
            manifest = self._manifest()
            manifest['files'].extend(
                [
                    {
                        'category': 'ddjj_expected_output',
                        'role': 'expected_output',
                        'path_ref': 'historical-ddjj-baseline-xls-ref',
                        'artifact_key': 'ddjj_metadata',
                        'relative_path': 'historical/ddjj_baseline.xls',
                        'ddjj_forms': ['1835'],
                        'output_status': 'baseline',
                    },
                    {
                        'category': 'f22_expected_output',
                        'role': 'expected_output',
                        'path_ref': 'historical-f22-rejected-xls-ref',
                        'artifact_key': 'f22',
                        'relative_path': 'historical/f22_rejected.xls',
                        'output_status': 'rejected',
                    },
                ]
            )
            self._write_expected_output_sources(source_root, manifest)

            result = compare_annual_tax_expected_outputs(
                empresa=empresa,
                commercial_year=2024,
                tax_year=2025,
                manifest=manifest,
                source_root=source_root,
            )

        content_summary = result['expected_output_content_signals']['summary']
        semantic_summary = result['expected_output_document_semantic_signals']['summary']

        self.assertGreater(content_summary['extraction_errors_total'], 0)
        self.assertEqual(content_summary['blocking_extraction_errors_total'], 0)
        self.assertTrue(content_summary['identity_signals_ready'])
        self.assertGreater(semantic_summary['extraction_errors_total'], 0)
        self.assertEqual(semantic_summary['blocking_extraction_errors_total'], 0)
        self.assertTrue(semantic_summary['document_semantic_ready'])
        self.assertNotIn('expected_output_identity_extraction_errors', result['summary']['blockers'])
        self.assertNotIn('expected_output_document_semantic_extraction_errors', result['summary']['blockers'])
        self.assertNotIn('expected_output_value_extractors_partial', result['summary']['blockers'])

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
        self.assertIn('expected_output_value_extractors_not_run', result['summary']['blockers'])
        self.assertEqual(result['generated_inventory']['generated_artifact_evidence'], {})

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
            self.assertTrue(result['summary']['document_semantic_extractors_ready'])
            self.assertTrue(result['summary']['value_equality_extractors_ready'])
            self.assertNotIn('expected_output_value_extractors_partial', result['summary']['blockers'])
            self.assertNotIn('expected_output_document_semantic_mismatch', result['summary']['blockers'])

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
