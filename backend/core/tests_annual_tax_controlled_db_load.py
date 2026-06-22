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
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from sii.models import (
    AnnualTaxOfficialSource,
    CapacidadSII,
    CapacidadTributariaSII,
    DestinoMapeoTributarioAnual,
    EstadoGateSII,
    EstadoMonthlyTaxFact,
    TipoAnnualTaxOfficialSource,
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

    def _with_ready_ownership_review(self, package):
        package['ownership_review'] = {
            'schema_version': 'annual-tax-ownership-review-handoff.v1',
            'source_checklist_hash': 'b' * 64,
            'redacted_patch_hash': 'c' * 64,
            'reviewable_candidates_total': 10,
            'rendered_candidates_total': 10,
            'validation_present': True,
            'participants_count': 2,
            'percentage_total': '100.00',
            'blocking_items_total': 0,
            'blocking_item_keys': [],
            'validation_blockers': [],
            'ready_for_manual_review': True,
            'ready_for_controlled_db_load': True,
            'can_inject_ownership_into_controlled_package': True,
            'next_action': 'package_ownership_injected_reaudit_readiness',
            'writes_database': False,
            'stores_source_paths': False,
            'stores_person_names': False,
            'stores_rut_values': False,
            'auto_generates_ownership': False,
        }
        return package

    def _with_ownership_review_sources(self, package):
        package['ownership_review']['readiness_sources_total'] = 1
        package['ownership_review']['question_source_summaries'] = [
            {
                'label': 'D:/Privado/Socio Controlado Uno 11111111-1/banco',
                'schema_version': 'company-bank-support-coverage-manifest.v1',
                'classification': 'blocking',
                'ready_flags': {
                    'ready_for_formal_bank_support_review': False,
                    'document_intake_ready_for_productive_review': False,
                    'document_intake_ready_for_formal_bank_support_manifest': True,
                    'D:/Privado/Socio Controlado Uno 11111111-1': True,
                },
                'issues_total': 2,
                'safe_issue_codes': [
                    {
                        'code': 'company_accounting.responsible_review_missing',
                        'severity': 'blocking',
                    },
                    {
                        'code': 'redacted-issue-code',
                        'severity': 'blocking',
                    },
                ],
                'source_hash': 'd' * 64,
            }
        ]
        return package

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

    def test_apply_controlled_package_materializes_ownership_snapshot(self):
        empresa = self._create_empresa()
        package = self._with_ownership(self._package())

        result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )

        self.assertTrue(result['ready_for_annual_generation'])
        self.assertTrue(result['ownership_snapshot']['present'])
        self.assertEqual(result['ownership_snapshot']['participants_loaded'], 2)
        self.assertFalse(result['ownership_snapshot']['final_tax_calculation'])
        self.assertEqual(Socio.objects.filter(rut__in=['11111111-1', '22222222-2']).count(), 2)
        participations = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).order_by('porcentaje')
        self.assertEqual(participations.count(), 2)
        self.assertEqual(sum(item.porcentaje for item in participations), 100)

        second_result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )
        self.assertEqual(second_result['created_updated']['Socio']['updated'], 2)
        self.assertEqual(second_result['created_updated']['ParticipacionPatrimonial']['updated'], 2)
        self.assertEqual(ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).count(), 2)

    def test_apply_controlled_package_accepts_consistent_ownership_review_handoff(self):
        empresa = self._create_empresa()
        package = self._with_ready_ownership_review(self._with_ownership(self._package()))

        result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )

        self.assertTrue(result['ready_for_annual_generation'])
        self.assertEqual(result['ownership_snapshot']['participants_loaded'], 2)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 12)

    def test_apply_exposes_sanitized_ownership_review_handoff_sources(self):
        empresa = self._create_empresa()
        package = self._with_ownership_review_sources(
            self._with_ready_ownership_review(self._with_ownership(self._package()))
        )

        result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )
        handoff = result['ownership_review_handoff']
        source_summary = handoff['question_source_summaries'][0]
        rendered_result = json.dumps(result, ensure_ascii=True, default=str)

        self.assertTrue(result['ready_for_annual_generation'])
        self.assertTrue(handoff['present'])
        self.assertTrue(handoff['ready_for_controlled_db_load'])
        self.assertFalse(handoff['replaces_ownership_snapshot'])
        self.assertEqual(handoff['readiness_sources_total'], 1)
        self.assertEqual(source_summary['label'], 'source')
        self.assertFalse(source_summary['ready_flags']['ready_for_formal_bank_support_review'])
        self.assertFalse(source_summary['ready_flags']['document_intake_ready_for_productive_review'])
        self.assertTrue(source_summary['ready_flags']['document_intake_ready_for_formal_bank_support_manifest'])
        self.assertIn(
            {'code': 'company_accounting.responsible_review_missing', 'severity': 'blocking'},
            source_summary['safe_issue_codes'],
        )
        self.assertIn({'code': 'redacted-issue-code', 'severity': 'blocking'}, source_summary['safe_issue_codes'])
        self.assertNotIn('D:/Privado/Socio Controlado Uno 11111111-1', source_summary['ready_flags'])
        self.assertNotIn('Socio Controlado Uno', rendered_result)
        self.assertNotIn('11111111-1', rendered_result)
        self.assertNotIn('D:/Privado', rendered_result)

    def test_apply_rejects_ready_ownership_handoff_without_patch_hash_before_writing(self):
        empresa = self._create_empresa()
        package = self._with_ready_ownership_review(self._with_ownership(self._package()))
        package['ownership_review']['redacted_patch_hash'] = ''

        with self.assertRaisesMessage(ValueError, 'redacted_patch_hash'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(Socio.objects.count(), 0)
        self.assertEqual(ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_apply_rejects_ownership_handoff_mismatch_before_writing(self):
        empresa = self._create_empresa()
        package = self._with_ready_ownership_review(self._with_ownership(self._package()))
        package['ownership_review']['participants_count'] = 1

        with self.assertRaisesMessage(ValueError, 'participants_count'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(Socio.objects.count(), 0)
        self.assertEqual(ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_apply_rejects_incomplete_ownership_snapshot_without_writing(self):
        empresa = self._create_empresa()
        package = self._with_ownership(self._package())
        package['ownership']['participants'][1]['percentage'] = '39.00'

        with self.assertRaisesMessage(ValueError, '100.00%'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(Socio.objects.count(), 0)
        self.assertEqual(ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_apply_rejects_ownership_snapshot_not_at_year_end_without_writing(self):
        empresa = self._create_empresa()
        package = self._with_ownership(self._package())
        package['ownership']['as_of'] = '2024-06-30'

        with self.assertRaisesMessage(ValueError, '31-12'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(Socio.objects.count(), 0)
        self.assertEqual(ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_apply_rejects_ownership_participant_not_active_at_year_end_without_writing(self):
        empresa = self._create_empresa()
        package = self._with_ownership(self._package())
        package['ownership']['participants'][1]['vigente_hasta'] = '2024-09-30'

        with self.assertRaisesMessage(ValueError, 'vigente al 31-12'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(Socio.objects.count(), 0)
        self.assertEqual(ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_apply_controlled_package_materializes_real_estate_snapshot(self):
        empresa = self._create_empresa()
        package = self._with_real_estate(self._with_ownership(self._package()))

        result = apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )

        self.assertTrue(result['ready_for_annual_generation'])
        self.assertTrue(result['real_estate_snapshot']['present'])
        self.assertEqual(result['real_estate_snapshot']['properties_loaded'], 1)
        self.assertFalse(result['real_estate_snapshot']['final_tax_calculation'])
        propiedad = Propiedad.objects.get(empresa_owner=empresa, codigo_propiedad='RE-001')
        self.assertEqual(propiedad.estado, 'activa')
        self.assertEqual(propiedad.tipo_inmueble, TipoInmueble.APARTMENT)
        source = AnnualTaxOfficialSource.objects.get(
            anio_tributario=2025,
            source_key__startswith='controlled-load-real-estate-contributions-at2025-',
        )
        self.assertEqual(source.source_type, TipoAnnualTaxOfficialSource.EXPERT_REVIEW)
        self.assertEqual(source.applies_to, DestinoMapeoTributarioAnual.F22)
        self.assertTrue(source.metadata['real_estate_contributions'])
        self.assertEqual(
            source.metadata['values_by_property_id'][str(propiedad.id)]['contribuciones_clp'],
            '345000.00',
        )

    def test_apply_rejects_incomplete_real_estate_snapshot_without_writing(self):
        empresa = self._create_empresa()
        package = self._with_real_estate(self._with_ownership(self._package()))
        package['real_estate']['properties'][0]['contribuciones_evidence_ref'] = ''

        with self.assertRaisesMessage(ValueError, 'contribuciones_evidence_ref'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(Propiedad.objects.filter(empresa_owner=empresa).count(), 0)
        self.assertEqual(AnnualTaxOfficialSource.objects.count(), 0)
        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

    def test_apply_rejects_required_labor_previsional_without_source(self):
        empresa = self._create_empresa()
        package = self._with_ownership(self._package())
        package['labor_previsional'] = {
            'required': True,
            'required_by_ddjj_forms': ['1887'],
            'source_ref': '',
        }

        with self.assertRaisesMessage(ValueError, 'labor_previsional.source_ref'):
            apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=True,
            )

        self.assertEqual(MonthlyTaxFact.objects.filter(empresa=empresa).count(), 0)

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

    def test_command_missing_package_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'apply_annual_tax_controlled_db_load',
                    package=str(package_path),
                    empresa_id=empresa.id,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_command_output_write_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_path = temp_root / 'controlled-load.json'
            output_path = temp_root / 'Socio Controlado Uno 11111111-1.json'
            output_path.mkdir()
            package_path.write_text(json.dumps(self._package(months=range(1, 2))), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'apply_annual_tax_controlled_db_load',
                    package=str(package_path),
                    empresa_id=empresa.id,
                    output=str(output_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

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

    def test_command_exposes_sanitized_ownership_review_handoff_sources(self):
        empresa = self._create_empresa()
        with TemporaryDirectory() as temp_dir:
            package_path = Path(temp_dir) / 'controlled-load.json'
            package_path.write_text(
                json.dumps(
                    self._with_ownership_review_sources(
                        self._with_ready_ownership_review(self._with_ownership(self._package()))
                    )
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

        rendered_stdout = stdout.getvalue()
        result = json.loads(rendered_stdout)
        handoff = result['ownership_review_handoff']

        self.assertFalse(result['writes_database'])
        self.assertTrue(handoff['present'])
        self.assertEqual(handoff['readiness_sources_total'], 1)
        self.assertEqual(handoff['question_source_summaries'][0]['label'], 'source')
        self.assertNotIn('Socio Controlado Uno', rendered_stdout)
        self.assertNotIn('11111111-1', rendered_stdout)
        self.assertNotIn('D:/Privado', rendered_stdout)

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

    def test_apply_preserves_december_inventory_lines_for_annual_trial_balance(self):
        empresa = self._create_empresa()
        package = self._package()
        package['months'][11]['balance']['annual_inventory_ref'] = 'libro-inventario-ref'
        package['months'][11]['balance']['lineas_balance_8_columnas_source'] = 'libro_inventario'
        package['months'][11]['balance']['annual_inventory_totals'] = {'activos': 1000, 'pasivos': 700}
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
            }
        ]

        apply_annual_tax_controlled_db_load(
            empresa=empresa,
            package=package,
            write_database=True,
        )

        december_balance = BalanceComprobacion.objects.get(empresa=empresa, periodo='2024-12')
        self.assertEqual(december_balance.resumen['annual_inventory_ref'], 'libro-inventario-ref')
        self.assertEqual(december_balance.resumen['lineas_balance_8_columnas_source'], 'libro_inventario')
        self.assertEqual(len(december_balance.resumen['lineas_balance_8_columnas']), 1)

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
