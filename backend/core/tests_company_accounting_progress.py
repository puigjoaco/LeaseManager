import json
from datetime import date
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    RegimenTributarioEmpresa,
)
from contabilidad.services import ensure_default_regime
from core.company_accounting_progress import collect_company_accounting_candidates, collect_company_accounting_progress
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio
from sii.models import (
    AnnualTaxArtifactMatrix,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalance,
    AnnualTaxWorkbook,
    CapacidadSII,
    CapacidadTributariaSII,
    EstadoAnnualTaxArtifactMatrix,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxOfficialSource,
    EstadoAnnualTaxSourceBundle,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    EstadoGateSII,
    EstadoReglaTributariaAnual,
    F29PreparacionMensual,
    ProcesoRentaAnual,
    TaxYearRuleSet,
    TipoAnnualTaxWorkbook,
    TipoAnnualTaxOfficialSource,
)


class CompanyAccountingProgressTests(TestCase):
    def _create_empresa(self):
        socio = Socio.objects.create(nombre='Socio Progress', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(
            razon_social='Empresa Progress SpA',
            rut='77777777-7',
            estado='activa',
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=empresa,
            porcentaje='100.00',
            vigente_desde=date(2025, 1, 1),
            activo=True,
        )
        return empresa

    def _activate_fiscal_config(self, empresa):
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=['1887'],
            inicio_ejercicio=date(2025, 1, 1),
            moneda_funcional='CLP',
            estado='activa',
        )

    def _activate_unsupported_fiscal_config(self, empresa):
        regime = RegimenTributarioEmpresa.objects.create(
            codigo_regimen='RegimenManualNoAutomatizableV1',
            descripcion='Regimen manual no automatizable en v1',
            estado='activa',
        )
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regime,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=['1887'],
            inicio_ejercicio=date(2025, 1, 1),
            moneda_funcional='CLP',
            estado='activa',
        )

    def _create_close(self, empresa, month, *, fiscal_year=2025):
        return CierreMensualContable.objects.create(
            empresa=empresa,
            anio=fiscal_year,
            mes=month,
            estado=EstadoCierreMensual.APPROVED,
            fecha_preparacion=timezone.now(),
            fecha_aprobacion=timezone.now(),
            resumen_obligaciones={'source': 'company-accounting-progress-test', 'month': month},
        )

    def _create_f29_capability(self, empresa):
        return CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.F29_PREPARACION,
            certificado_ref='f29-cert-controlled',
            evidencia_ref='f29-evidence-controlled',
            prueba_flujo_ref='f29-flow-controlled',
            autorizacion_ambiente_ref='f29-certification-env-controlled',
            regla_fiscal_ref='f29-tax-rule-controlled',
            estado_gate=EstadoGateSII.OPEN,
        )

    def _create_source_bundle(self, empresa):
        return AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            anio_comercial=2025,
            source_kind='snapshot_controlado',
            source_label='company-accounting-progress-controlled',
            authorization_ref='company-accounting-progress-authorization',
            responsible_ref='company-accounting-progress-owner',
            hash_fuentes='1' * 64,
            resumen_fuentes={'source': 'company-accounting-progress-test'},
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

    def _create_rule_set(self, config):
        source = AnnualTaxOfficialSource.objects.create(
            anio_tributario=2026,
            source_key='company-accounting-progress-source',
            source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            title='Fuente experta controlada',
            source_ref='company-accounting-progress-source-ref',
            source_hash='2' * 64,
            retrieved_on=date(2026, 6, 14),
            responsible_ref='company-accounting-progress-source-owner',
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            metadata={'source': 'company-accounting-progress-test'},
        )
        rule_set = TaxYearRuleSet.objects.create(
            anio_tributario=2026,
            regimen_tributario=config.regimen_tributario,
            version='AT2026-progress-test',
            estado=EstadoReglaTributariaAnual.APPROVED,
            fuente_ref='company-accounting-progress-rules',
            hash_normativo='3' * 64,
            responsable_aprobacion_ref='company-accounting-progress-rule-owner',
            official_source=source,
            metadata={'source': 'company-accounting-progress-test'},
        )
        return rule_set, source

    def test_partial_progress_reports_next_missing_phase_without_external_sources(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)

        for month in (1, 2, 3):
            close = self._create_close(empresa, month)
            BalanceComprobacion.objects.create(
                empresa=empresa,
                periodo=f'2025-{month:02d}',
                estado_snapshot=EstadoCierreMensual.APPROVED,
                storage_ref=f'balance-progress-{month}',
                resumen={'cuadrado': month in (1, 2), 'source': 'company-accounting-progress-test'},
            )
            if month == 1:
                F29PreparacionMensual.objects.create(
                    empresa=empresa,
                    capacidad_tributaria=f29_capability,
                    cierre_mensual=close,
                    anio=2025,
                    mes=month,
                    estado_preparacion=EstadoPreparacionTributaria.PREPARED,
                    resumen_formulario={'source': 'company-accounting-progress-test'},
                    borrador_ref='f29-progress-draft',
                    responsable_revision_ref='f29-progress-owner',
                )

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_company_accounting_review'])
        self.assertEqual(result['next_blocking_phase'], 'monthly_closes')
        self.assertEqual(result['phases']['monthly_closes']['completed'], 3)
        self.assertEqual(result['phases']['monthly_closes']['missing'], [4, 5, 6, 7, 8, 9, 10, 11, 12])
        self.assertEqual(result['phases']['monthly_balances_squared']['completed'], 2)
        self.assertEqual(result['phases']['f29_monthly']['completed'], 1)
        self.assertIn('company_accounting.monthly_closes_missing', {issue['code'] for issue in result['issues']})
        self.assertNotIn('://', json.dumps(result))

    def test_unsupported_fiscal_regime_blocks_company_progress_review(self):
        empresa = self._create_empresa()
        config = self._activate_unsupported_fiscal_config(empresa)
        self._create_close(empresa, 1, fiscal_year=2025)

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_company_accounting_review'])
        self.assertEqual(result['next_blocking_phase'], 'fiscal_config')
        self.assertFalse(result['phases']['fiscal_config']['ready'])
        self.assertEqual(result['phases']['fiscal_config']['missing'], [config.regimen_tributario.codigo_regimen])
        self.assertTrue(result['fiscal_config']['active'])
        self.assertFalse(result['fiscal_config']['supported'])
        self.assertEqual(result['fiscal_config']['regime_code'], config.regimen_tributario.codigo_regimen)
        self.assertIn('company_accounting.fiscal_config_unsupported_regime', issue_codes)
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_candidates_rank_company_years_without_exposing_rut(self):
        empresa = self._create_empresa()
        empresa_sin_senales = Empresa.objects.create(
            razon_social='Empresa Sin Senales SpA',
            rut='76666666-6',
            estado='activa',
        )
        self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)

        for month in (1, 2):
            close = self._create_close(empresa, month, fiscal_year=2025)
            BalanceComprobacion.objects.create(
                empresa=empresa,
                periodo=f'2025-{month:02d}',
                estado_snapshot=EstadoCierreMensual.APPROVED,
                storage_ref=f'candidate-balance-{month}',
                resumen={'cuadrado': month == 1},
            )
            F29PreparacionMensual.objects.create(
                empresa=empresa,
                capacidad_tributaria=f29_capability,
                cierre_mensual=close,
                anio=2025,
                mes=month,
                estado_preparacion=EstadoPreparacionTributaria.PREPARED,
                resumen_formulario={'source': 'candidate-test'},
                borrador_ref=f'candidate-f29-{month}',
                responsable_revision_ref='candidate-reviewer',
            )
        self._create_close(empresa, 1, fiscal_year=2024)
        december_balance = BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2025-12',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            storage_ref='candidate-balance-december',
            resumen={'cuadrado': True},
        )
        source_bundle = self._create_source_bundle(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        rule_set, official_source = self._create_rule_set(config)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
            source_bundle=source_bundle,
            fecha_preparacion=timezone.now(),
            resumen_anual={'source': 'candidate-test'},
        )
        AnnualTaxTrialBalance.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            official_source=official_source,
            source_balance=december_balance,
            anio_tributario=2026,
            anio_comercial=2025,
            periodo_cierre='2025-12',
            source_ref='candidate-trial-balance',
            responsible_ref='candidate-reviewer',
            lines_total=1,
            resumen_balance={'source': 'candidate-test'},
            hash_balance='9' * 64,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )
        for kind in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
            AnnualTaxWorkbook.objects.create(
                empresa=empresa,
                proceso_renta_anual=process,
                source_bundle=source_bundle,
                rule_set=rule_set,
                anio_tributario=2026,
                anio_comercial=2025,
                tipo=kind,
                source_ref=f'candidate-{kind.lower()}',
                responsible_ref='candidate-reviewer',
                resumen_workbook={'source': 'candidate-test', 'tipo': kind},
                hash_workbook='a' * 64,
                estado=EstadoAnnualTaxWorkbook.PREPARED,
            )
        matrix = AnnualTaxArtifactMatrix.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='candidate-matrix',
            responsible_ref='candidate-reviewer',
            items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            resumen_matriz={'source': 'candidate-test'},
            hash_matriz='b' * 64,
            estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
        )
        dossier = AnnualTaxDossier.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            artifact_matrix=matrix,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='candidate-dossier',
            responsible_ref='candidate-reviewer',
            dossier_ref='candidate-dossier-ref',
            monthly_facts_total=2,
            workbooks_total=2,
            artifact_matrix_items_total=2,
            resumen_dossier={'source': 'candidate-test'},
            hash_dossier='c' * 64,
            estado=EstadoAnnualTaxDossier.PREPARED,
        )
        AnnualTaxExport.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            dossier=dossier,
            source_bundle=source_bundle,
            rule_set=rule_set,
            artifact_matrix=matrix,
            official_format_source=official_source,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='candidate-export',
            responsible_ref='candidate-reviewer',
            export_ref='candidate-export-ref',
            target_items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            export_payload={'source': 'candidate-test'},
            hash_export='d' * 64,
            estado=EstadoAnnualTaxExport.PREPARED,
        )

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id, empresa_sin_senales.id])

        self.assertEqual(result['summary']['companies_total'], 2)
        self.assertEqual(result['summary']['candidate_companies'], 1)
        self.assertEqual(result['summary']['candidate_years'], 2)
        self.assertTrue(result['selection_boundary']['purpose'])
        self.assertFalse(result['selection_boundary']['uses_external_sources'])
        self.assertFalse(result['selection_boundary']['autonomous_accounting'])
        self.assertFalse(result['selection_boundary']['final_tax_calculation'])
        self.assertFalse(result['selection_boundary']['sii_submission'])
        self.assertEqual(result['candidates'][0]['empresa']['id'], empresa.id)
        self.assertEqual(result['candidates'][0]['recommended_fiscal_year'], 2025)
        self.assertTrue(result['candidates'][0]['years'][0]['recommended'])
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['monthly_closes'], 2)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['monthly_balances_squared'], 2)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['f29_monthly'], 2)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['annual_processes'], 1)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['annual_trial_balance'], 1)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['rli_cpt_workbooks'], 2)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['annual_dossier'], 1)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['annual_export'], 1)
        self.assertEqual(result['candidates'][0]['years'][1]['fiscal_year'], 2024)
        self.assertNotIn(empresa.rut, json.dumps(result))
        self.assertNotIn(empresa_sin_senales.rut, json.dumps(result))

    def test_candidates_surface_unsupported_fiscal_regime_without_hiding_signals(self):
        empresa = self._create_empresa()
        config = self._activate_unsupported_fiscal_config(empresa)
        self._create_close(empresa, 1, fiscal_year=2025)

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id])
        candidate = result['candidates'][0]

        self.assertEqual(result['summary']['candidate_companies'], 1)
        self.assertEqual(result['summary']['unsupported_fiscal_regime_companies'], 1)
        self.assertTrue(candidate['fiscal_config_active'])
        self.assertFalse(candidate['fiscal_regime_supported'])
        self.assertEqual(candidate['fiscal_regime_code'], config.regimen_tributario.codigo_regimen)
        self.assertEqual(candidate['recommended_fiscal_year'], 2025)
        self.assertEqual(candidate['years'][0]['signals']['monthly_closes'], 1)
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_candidates_command_outputs_empty_and_can_fail_on_empty(self):
        stdout = StringIO()

        call_command('audit_company_accounting_candidates', stdout=stdout)

        result = json.loads(stdout.getvalue())
        self.assertEqual(result['summary']['companies_total'], 0)
        self.assertEqual(result['summary']['candidate_companies'], 0)
        self.assertEqual(result['candidates'], [])

        with self.assertRaisesMessage(CommandError, 'No hay candidatos'):
            call_command(
                'audit_company_accounting_candidates',
                fail_on_empty=True,
                stdout=StringIO(),
            )

    def test_candidates_command_refuses_versioned_output_outside_local_evidence(self):
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_company_accounting_candidates',
                output='docs/company-accounting-candidates.json',
            )

    def test_downstream_annual_artifacts_do_not_count_without_prepared_process(self):
        empresa = self._create_empresa()
        config = self._activate_fiscal_config(empresa)
        source_bundle = self._create_source_bundle(empresa)
        rule_set, official_source = self._create_rule_set(config)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PENDING_DATA,
            source_bundle=source_bundle,
            resumen_anual={'source': 'company-accounting-progress-test'},
        )
        source_balance = BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2025-12',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            storage_ref='balance-progress-annual',
            resumen={'cuadrado': True, 'source': 'company-accounting-progress-test'},
        )
        AnnualTaxTrialBalance.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            official_source=official_source,
            source_balance=source_balance,
            anio_tributario=2026,
            anio_comercial=2025,
            periodo_cierre='2025-12',
            source_ref='trial-balance-progress-source',
            responsible_ref='trial-balance-progress-owner',
            lines_total=1,
            resumen_balance={'source': 'company-accounting-progress-test'},
            hash_balance='4' * 64,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertFalse(result['phases']['annual_process']['ready'])
        self.assertFalse(result['phases']['annual_trial_balance']['ready'])
        self.assertEqual(result['phases']['annual_trial_balance']['completed'], 0)
        self.assertIn('company_accounting.annual_process_missing', {issue['code'] for issue in result['issues']})
        self.assertIn('company_accounting.annual_trial_balance_missing', {issue['code'] for issue in result['issues']})

    def test_complete_local_layers_are_ready_for_review_not_close(self):
        empresa = self._create_empresa()
        config = self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)

        december_balance = None
        for month in range(1, 13):
            close = self._create_close(empresa, month)
            balance = BalanceComprobacion.objects.create(
                empresa=empresa,
                periodo=f'2025-{month:02d}',
                estado_snapshot=EstadoCierreMensual.APPROVED,
                storage_ref=f'balance-progress-ready-{month}',
                resumen={'cuadrado': True, 'source': 'company-accounting-progress-test'},
            )
            if month == 12:
                december_balance = balance
            F29PreparacionMensual.objects.create(
                empresa=empresa,
                capacidad_tributaria=f29_capability,
                cierre_mensual=close,
                anio=2025,
                mes=month,
                estado_preparacion=EstadoPreparacionTributaria.PREPARED,
                resumen_formulario={'source': 'company-accounting-progress-test'},
                borrador_ref=f'f29-progress-ready-{month}',
                responsable_revision_ref='f29-progress-owner',
            )

        source_bundle = self._create_source_bundle(empresa)
        rule_set, official_source = self._create_rule_set(config)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
            source_bundle=source_bundle,
            fecha_preparacion=timezone.now(),
            resumen_anual={'source': 'company-accounting-progress-test'},
        )
        AnnualTaxTrialBalance.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            official_source=official_source,
            source_balance=december_balance,
            anio_tributario=2026,
            anio_comercial=2025,
            periodo_cierre='2025-12',
            source_ref='trial-balance-progress-source',
            responsible_ref='trial-balance-progress-owner',
            lines_total=1,
            resumen_balance={'source': 'company-accounting-progress-test'},
            hash_balance='4' * 64,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )
        for kind in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
            AnnualTaxWorkbook.objects.create(
                empresa=empresa,
                proceso_renta_anual=process,
                source_bundle=source_bundle,
                rule_set=rule_set,
                anio_tributario=2026,
                anio_comercial=2025,
                tipo=kind,
                source_ref=f'{kind.lower()}-progress-source',
                responsible_ref='workbook-progress-owner',
                resumen_workbook={'source': 'company-accounting-progress-test', 'tipo': kind},
                hash_workbook='5' * 64,
                estado=EstadoAnnualTaxWorkbook.PREPARED,
            )
        matrix = AnnualTaxArtifactMatrix.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='matrix-progress-source',
            responsible_ref='matrix-progress-owner',
            items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            resumen_matriz={'source': 'company-accounting-progress-test'},
            hash_matriz='6' * 64,
            estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
        )
        dossier = AnnualTaxDossier.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            artifact_matrix=matrix,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='dossier-progress-source',
            responsible_ref='dossier-progress-owner',
            dossier_ref='dossier-progress-ref',
            monthly_facts_total=12,
            workbooks_total=2,
            artifact_matrix_items_total=2,
            resumen_dossier={'source': 'company-accounting-progress-test'},
            hash_dossier='7' * 64,
            estado=EstadoAnnualTaxDossier.PREPARED,
        )
        AnnualTaxExport.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            dossier=dossier,
            source_bundle=source_bundle,
            rule_set=rule_set,
            artifact_matrix=matrix,
            official_format_source=official_source,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='export-progress-source',
            responsible_ref='export-progress-owner',
            export_ref='export-progress-ref',
            target_items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            export_payload={'source': 'company-accounting-progress-test'},
            hash_export='8' * 64,
            estado=EstadoAnnualTaxExport.PREPARED,
        )

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertEqual(result['classification'], 'preparado')
        self.assertEqual(result['progress_percent'], 100)
        self.assertTrue(result['ready_for_company_accounting_review'])
        self.assertEqual(
            result['review_boundary']['meaning_when_ready'],
            'paquete_local_preparado_para_revision_responsable',
        )
        self.assertFalse(result['review_boundary']['autonomous_accounting'])
        self.assertFalse(result['review_boundary']['final_tax_calculation'])
        self.assertFalse(result['review_boundary']['sii_submission'])
        self.assertTrue(result['review_boundary']['requires_responsible_review'])
        self.assertTrue(result['review_boundary']['requires_expert_or_official_validation'])
        self.assertIn('presentacion_sii_automatica', result['review_boundary']['not_allowed_actions'])
        self.assertEqual(result['issue_counts']['blocking'], 0)
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['next_blocking_phase'], '')
        self.assertEqual(result['phases']['rli_cpt_workbooks']['completed'], 2)

    def test_command_refuses_versioned_output_outside_local_evidence(self):
        empresa = self._create_empresa()

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_company_accounting_progress',
                empresa_id=empresa.id,
                fiscal_year=2025,
                output='docs/company-accounting-progress.json',
            )

    def test_command_outputs_progress_and_can_fail_on_incomplete(self):
        empresa = self._create_empresa()
        stdout = StringIO()

        call_command(
            'audit_company_accounting_progress',
            empresa_id=empresa.id,
            fiscal_year=2025,
            stdout=stdout,
        )

        result = json.loads(stdout.getvalue())
        self.assertEqual(result['tax_year'], 2026)
        self.assertEqual(result['classification'], 'sin_datos')
        self.assertFalse(result['ready_for_company_accounting_review'])

        with self.assertRaisesMessage(CommandError, 'Avance contable/renta incompleto'):
            call_command(
                'audit_company_accounting_progress',
                empresa_id=empresa.id,
                fiscal_year=2025,
                fail_on_incomplete=True,
                stdout=StringIO(),
            )

    def test_candidates_command_outputs_candidates_without_rut(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        self._create_close(empresa, 1, fiscal_year=2025)
        stdout = StringIO()

        call_command(
            'audit_company_accounting_candidates',
            stdout=stdout,
        )

        result = json.loads(stdout.getvalue())
        self.assertEqual(result['summary']['companies_total'], 1)
        self.assertEqual(result['summary']['candidate_companies'], 1)
        self.assertEqual(result['candidates'][0]['empresa']['id'], empresa.id)
        self.assertEqual(result['candidates'][0]['recommended_fiscal_year'], 2025)
        self.assertNotIn(empresa.rut, stdout.getvalue())
