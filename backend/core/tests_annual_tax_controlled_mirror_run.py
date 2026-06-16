import json
from datetime import date
from decimal import Decimal
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
from core.company_accounting_progress import collect_company_accounting_progress
from core.stage6_renta_anual_readiness import collect_stage6_renta_anual_readiness
from documentos.models import DocumentoEmitido, EstadoDocumento, TipoDocumental
from patrimonio.models import Empresa, TipoInmueble
from sii.models import (
    AnnualEnterpriseRegisterMovement,
    AnnualRealEstateItem,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbookLine,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    EstadoGateSII,
    F22PreparacionAnual,
    ProcesoRentaAnual,
    MonthlyTaxFact,
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

    def _with_ownership(self, package):
        package['ownership'] = {
            'source_ref': 'ownership-structure-2024-controlled',
            'as_of': '2024-12-31',
            'participants': [
                {
                    'participant_type': 'socio',
                    'participant_ref': 'socio-controlled-one',
                    'name': 'Socio Controlado Uno',
                    'rut': '11111111-1',
                    'percentage': '60.00',
                    'vigente_desde': '2024-01-01',
                    'vigente_hasta': None,
                    'evidence_ref': 'ownership-evidence-controlled-one',
                },
                {
                    'participant_type': 'socio',
                    'participant_ref': 'socio-controlled-two',
                    'name': 'Socio Controlado Dos',
                    'rut': '22222222-2',
                    'percentage': '40.00',
                    'vigente_desde': '2024-01-01',
                    'vigente_hasta': None,
                    'evidence_ref': 'ownership-evidence-controlled-two',
                },
            ],
        }
        return package

    def _with_real_estate(self, package):
        package['real_estate'] = {
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
                },
            ],
        }
        return package

    def _load_monthly_package(self, empresa, package=None):
        return apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package or self._package(),
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
        february = MonthlyTaxFact.objects.get(empresa=empresa, anio=2024, mes=2)
        self.assertIsNone(february.f29_preparacion)
        self.assertEqual(
            february.resumen_hecho['f29']['estado_preparacion'],
            EstadoPreparacionTributaria.NOT_APPLICABLE,
        )
        self.assertTrue(february.resumen_hecho['f29']['resumen']['no_declaration'])
        progress = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2024)
        self.assertEqual(progress['phases']['f29_monthly']['completed'], 12)
        self.assertEqual(progress['phases']['f29_monthly']['missing'], [])

    def test_controlled_mirror_emits_valid_tax_support_document(self):
        empresa = self._create_empresa()
        self._load_monthly_package(empresa, package=self._with_ownership(self._package()))

        result = run_annual_tax_controlled_mirror(
            **self._mirror_kwargs(empresa),
            write_database=True,
        )

        document = DocumentoEmitido.objects.get(tipo_documental=TipoDocumental.TAX_SUPPORT)
        self.assertEqual(document.estado, EstadoDocumento.ISSUED)
        self.assertEqual(document.origen, 'generado_sistema')
        self.assertEqual(document.version_plantilla, 'stage6-v1')
        self.assertEqual(document.expediente.entidad_tipo, 'proceso_renta_anual')
        self.assertEqual(document.expediente.entidad_id, str(result['process_id']))
        self.assertRegex(document.checksum, r'^[0-9a-f]{64}$')
        self.assertTrue(
            document.storage_ref.startswith('storage/generated-documents/respaldo_tributario/stage6-v1-')
        )
        self.assertTrue(document.storage_ref.endswith('.pdf'))
        document.full_clean()

        gate = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='ac2024-tax-rule-review-pending',
            certificates_proof_ref='ac2024-certificates-proof-pending',
            responsible_ref='stage6-responsibles-v1',
            source_label='inmobiliaria-puig-ac2024-controlled-writer',
            authorization_ref='user-authorized-local-source-review',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in gate['issues']}
        self.assertNotIn('stage6.tax_support_document_missing', issue_codes)
        self.assertIn('stage6.real_estate_item_missing', issue_codes)

    def test_controlled_mirror_uses_real_estate_snapshot_for_stage6_gate(self):
        empresa = self._create_empresa()
        package = self._with_real_estate(self._with_ownership(self._package()))
        self._load_monthly_package(empresa, package=package)

        run_annual_tax_controlled_mirror(
            **self._mirror_kwargs(empresa),
            write_database=True,
        )

        item = AnnualRealEstateItem.objects.get()
        self.assertEqual(item.codigo_propiedad_snapshot, 'RE-001')
        self.assertEqual(item.contribuciones_clp, Decimal('345000.00'))
        self.assertEqual(item.source_payload['contribuciones_loaded'], True)
        self.assertEqual(item.source_payload['contribuciones_source'], 'official_or_expert_review')
        self.assertFalse(item.source_payload['final_tax_calculation'])

        gate = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='ac2024-tax-rule-review-pending',
            certificates_proof_ref='ac2024-certificates-proof-pending',
            responsible_ref='stage6-responsibles-v1',
            source_label='inmobiliaria-puig-ac2024-controlled-writer',
            authorization_ref='user-authorized-local-source-review',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in gate['issues']}
        self.assertNotIn('stage6.real_estate_item_missing', issue_codes)
        self.assertNotIn('stage6.real_estate_contribution_value_missing', issue_codes)
        self.assertNotIn('stage6.tax_support_document_missing', issue_codes)

    def test_controlled_mirror_uses_ownership_snapshot_for_participation_registers(self):
        empresa = self._create_empresa()
        self._load_monthly_package(empresa, package=self._with_ownership(self._package()))

        run_annual_tax_controlled_mirror(
            **self._mirror_kwargs(empresa),
            write_database=True,
        )

        missing_movements = AnnualEnterpriseRegisterMovement.objects.filter(
            origen='participacion_patrimonial_missing',
        )
        self.assertFalse(missing_movements.exists())
        participation_movements = AnnualEnterpriseRegisterMovement.objects.filter(
            origen='participacion_patrimonial',
        )
        self.assertEqual(participation_movements.count(), 4)
        for movement in participation_movements:
            self.assertNotIn('participation_source_missing', movement.warnings)
            self.assertEqual(movement.source_payload['source'], 'participacion_patrimonial')
            self.assertFalse(movement.source_payload['final_tax_calculation'])

    def test_controlled_mirror_generates_valid_enterprise_register_movement_hashes(self):
        empresa = self._create_empresa()
        self._load_monthly_package(empresa, package=self._with_ownership(self._package()))

        run_annual_tax_controlled_mirror(
            **self._mirror_kwargs(empresa),
            write_database=True,
        )

        workbook_movements = AnnualEnterpriseRegisterMovement.objects.filter(
            origen__startswith='annual_tax_workbook:',
        )
        self.assertGreater(workbook_movements.count(), 0)
        for movement in workbook_movements:
            movement.full_clean()

        gate = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='ac2024-tax-rule-review-pending',
            certificates_proof_ref='ac2024-certificates-proof-pending',
            responsible_ref='stage6-responsibles-v1',
            source_label='inmobiliaria-puig-ac2024-controlled-writer',
            authorization_ref='user-authorized-local-source-review',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in gate['issues']}
        self.assertNotIn('stage6.enterprise_register_movement_invalid', issue_codes)

    def test_controlled_mirror_uses_december_inventory_lines_for_trial_balance(self):
        empresa = self._create_empresa()
        package = self._package()
        package['months'][11]['balance']['annual_inventory_ref'] = 'libro-inventario-ref'
        package['months'][11]['balance']['lineas_balance_8_columnas_source'] = 'libro_inventario'
        package['months'][11]['balance']['lineas_balance_8_columnas'] = [
            {
                'codigo_cuenta': '1101001',
                'nombre_cuenta': 'Caja',
                'clasificador_dj1847': 'CPT-CASH-ASSET',
                'sumas_debe_clp': '1000.00',
                'saldo_deudor_clp': '1000.00',
                'inventario_activo_clp': '1000.00',
                'formula_ref': 'libro-inventario-saldo-contable',
                'evidencia_ref': 'libro-inventario-2024-controlled',
            },
            {
                'codigo_cuenta': '3101001',
                'nombre_cuenta': 'Capital',
                'clasificador_dj1847': 'CPT-EQUITY',
                'sumas_haber_clp': '700.00',
                'saldo_acreedor_clp': '700.00',
                'inventario_pasivo_clp': '700.00',
                'formula_ref': 'libro-inventario-saldo-contable',
                'evidencia_ref': 'libro-inventario-2024-controlled',
            },
        ]
        self._load_monthly_package(empresa, package=package)

        run_annual_tax_controlled_mirror(
            **self._mirror_kwargs(empresa),
            write_database=True,
        )

        trial_lines = AnnualTaxTrialBalanceLine.objects.order_by('codigo_cuenta')
        self.assertGreaterEqual(trial_lines.count(), 3)
        self.assertTrue(trial_lines.filter(codigo_cuenta='1101001', clasificador_dj1847='CPT-CASH-ASSET').exists())
        self.assertTrue(trial_lines.filter(codigo_cuenta='3101001', clasificador_dj1847='CPT-EQUITY').exists())
        self.assertTrue(trial_lines.filter(clasificador_dj1847='RLI-LEASE-REVENUE').exists())
        workbook_lines = AnnualTaxWorkbookLine.objects.filter(
            workbook__proceso_renta_anual__empresa=empresa,
        )
        self.assertTrue(workbook_lines.filter(codigo_destino='CPT-ASSETS-SUPPORT').exists())
        equity_line = workbook_lines.get(codigo_destino='CPT-EQUITY')
        self.assertEqual(equity_line.monto_clp, Decimal('700.00'))
        self.assertEqual(equity_line.source_payload['expected_output_artifacts'], [])
        self.assertEqual(equity_line.source_payload['expected_enterprise_register_artifacts'], [])
        support_line = workbook_lines.get(codigo_destino='CPT-ASSETS-SUPPORT')
        self.assertEqual(support_line.source_payload['trial_balance_classifiers'], ['CPT-CASH-ASSET', 'CPT-ASSET'])
        self.assertEqual(support_line.source_payload['expected_output_artifacts'], ['capital_propio'])

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
