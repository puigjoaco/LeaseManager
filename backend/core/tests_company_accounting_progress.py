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
)
from contabilidad.services import ensure_default_regime
from core.company_accounting_progress import collect_company_accounting_progress
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
