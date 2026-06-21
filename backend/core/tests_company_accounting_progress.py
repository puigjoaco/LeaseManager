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
    CuentaContable,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    NaturalezaCuenta,
    RegimenTributarioEmpresa,
)
from contabilidad.services import ensure_default_regime
from core.annual_tax_source_manifest import payload_hash
from core.company_accounting_progress import collect_company_accounting_candidates, collect_company_accounting_progress
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio
from sii.models import (
    AnnualTaxArtifactMatrix,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadSII,
    CapacidadTributariaSII,
    DestinoMapeoTributarioAnual,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxArtifactMatrix,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxOfficialSource,
    EstadoAnnualTaxSourceBundle,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    EstadoGateSII,
    EstadoMonthlyTaxFact,
    EstadoReglaTributariaAnual,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualTaxArtifactTarget,
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

    def _create_no_declaration_monthly_tax_fact(self, empresa, month, *, fiscal_year=2025):
        close = self._create_close(empresa, month, fiscal_year=fiscal_year)
        resumen = {
            'empresa_id': empresa.id,
            'anio': fiscal_year,
            'mes': month,
            'f29': {
                'estado_preparacion': EstadoPreparacionTributaria.NOT_APPLICABLE,
                'resumen': {'no_declaration': True},
            },
        }
        return MonthlyTaxFact.objects.create(
            empresa=empresa,
            anio=fiscal_year,
            mes=month,
            cierre_mensual=close,
            source_ref=f'f29-no-declaration-{fiscal_year}-{month:02d}',
            responsible_ref='company-accounting-progress-owner',
            resumen_hecho=resumen,
            hash_hecho=payload_hash(resumen),
            estado=EstadoMonthlyTaxFact.NORMALIZED,
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

    def _create_mismatched_source_bundle(self, empresa):
        return AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            anio_comercial=2025,
            source_label='company-accounting-progress-mismatched-source',
            responsible_ref='company-accounting-progress-mismatched-owner',
            resumen_fuentes={'source': 'company-accounting-progress-mismatch'},
            estado=EstadoAnnualTaxSourceBundle.DRAFT,
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

    def _create_trial_balance_line(self, trial_balance):
        account, _ = CuentaContable.objects.get_or_create(
            empresa=trial_balance.empresa,
            plan_cuentas_version='company-progress-test',
            codigo=f'4100-{trial_balance.id}',
            defaults={
                'nombre': f'Ingresos {trial_balance.id}',
                'naturaleza': NaturalezaCuenta.CREDIT,
                'nivel': 1,
                'estado': EstadoRegistro.ACTIVE,
            },
        )
        return AnnualTaxTrialBalanceLine.objects.create(
            trial_balance=trial_balance,
            cuenta_contable=account,
            codigo_cuenta=account.codigo,
            nombre_cuenta=account.nombre,
            clasificador_dj1847='RLI-LEASE-REVENUE',
            sumas_haber_clp='1000.00',
            saldo_acreedor_clp='1000.00',
            resultado_ganancia_clp='1000.00',
            formula_ref='trial-balance-line-formula-controlled',
            evidencia_ref='trial-balance-line-evidence-controlled',
            source_payload={'source': 'company-accounting-progress-test', 'trial_balance_id': trial_balance.id},
            hash_linea='d' * 64,
            estado=EstadoRegistro.ACTIVE,
        )

    def _create_workbook_line(self, workbook):
        destino = (
            DestinoMapeoTributarioAnual.RLI
            if workbook.tipo == TipoAnnualTaxWorkbook.RLI
            else DestinoMapeoTributarioAnual.CPT
        )
        mapping, _ = TaxCodeMapping.objects.get_or_create(
            rule_set=workbook.rule_set,
            destino=destino,
            codigo_interno=f'{workbook.tipo.lower()}.lease.controlled',
            codigo_destino=f'{workbook.tipo}-CONTROLLED-001',
            defaults={
                'formula_ref': f'{workbook.tipo.lower()}-formula-controlled',
                'evidencia_ref': f'{workbook.tipo.lower()}-evidence-controlled',
                'official_source': workbook.rule_set.official_source,
                'metadata': {'source': 'company-accounting-progress-test'},
            },
        )
        return AnnualTaxWorkbookLine.objects.create(
            workbook=workbook,
            mapping=mapping,
            codigo_interno=mapping.codigo_interno,
            codigo_destino=mapping.codigo_destino,
            origen='company-accounting-progress-test',
            monto_clp='1000.00',
            formula_ref=f'{workbook.tipo.lower()}-line-formula-controlled',
            evidencia_ref=f'{workbook.tipo.lower()}-line-evidence-controlled',
            source_payload={'source': 'company-accounting-progress-test', 'workbook_id': workbook.id},
            hash_linea='e' * 64,
            estado=EstadoRegistro.ACTIVE,
        )

    def _export_package_payload(self):
        package_manifest = [
            {
                'package_entry_version': 'annual-tax-export-file-package-manifest-v1',
                'artifact_matrix_item_id': '1',
                'target_kind': TipoAnnualTaxArtifactTarget.DDJJ,
                'target_code': '1887',
                'file_name': 'ddjj-1887.json',
                'content_type': 'application/json',
                'encoding': 'utf-8',
                'schema_ref': 'annual-tax-export-file-payload-v1',
                'delivery_kind': 'local_controlled_export_package',
                'materialized_from': 'annual-tax-export-file-payload-v1',
                'canonical_json': 'sort_keys_ascii_compact',
                'payload_hash': 'a' * 64,
                'manifest_payload_hash': 'a' * 64,
                'payload_size_bytes': 10,
                'manifest_payload_size_bytes': 10,
                'requires_official_format_gate': True,
                'requires_explicit_submission_authorization': True,
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
            },
            {
                'package_entry_version': 'annual-tax-export-file-package-manifest-v1',
                'artifact_matrix_item_id': '2',
                'target_kind': TipoAnnualTaxArtifactTarget.F22,
                'target_code': 'F22',
                'file_name': 'f22.json',
                'content_type': 'application/json',
                'encoding': 'utf-8',
                'schema_ref': 'annual-tax-export-file-payload-v1',
                'delivery_kind': 'local_controlled_export_package',
                'materialized_from': 'annual-tax-export-file-payload-v1',
                'canonical_json': 'sort_keys_ascii_compact',
                'payload_hash': 'b' * 64,
                'manifest_payload_hash': 'b' * 64,
                'payload_size_bytes': 20,
                'manifest_payload_size_bytes': 20,
                'requires_official_format_gate': True,
                'requires_explicit_submission_authorization': True,
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
            },
        ]
        return {
            'source': 'company-accounting-progress-test',
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'export_file_package_manifest': package_manifest,
            'export_file_package_version': 'annual-tax-export-file-package-v1',
            'export_file_package_files_total': 2,
            'ddjj_export_package_files_total': 1,
            'f22_export_package_files_total': 1,
            'export_file_package_hash': payload_hash(package_manifest),
        }

    def _prepare_reviewable_dossier(self, *, process, source_bundle, rule_set, matrix, dossier):
        summary = {
            'source': 'company-accounting-progress-test',
            'empresa_id': process.empresa_id,
            'proceso_renta_anual_id': process.id,
            'source_bundle_id': source_bundle.id,
            'rule_set_id': rule_set.id,
            'artifact_matrix_id': matrix.id,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': process.anio_tributario - 1,
            'source_bundle_hash': source_bundle.hash_fuentes,
            'rule_set_hash': rule_set.hash_normativo,
            'artifact_matrix_hash': matrix.hash_matriz,
            'monthly_facts_total': dossier.monthly_facts_total,
            'workbooks_total': dossier.workbooks_total,
            'enterprise_registers_total': dossier.enterprise_registers_total,
            'real_estate_sections_total': dossier.real_estate_sections_total,
            'artifact_matrix_items_total': dossier.artifact_matrix_items_total,
            'matrix_items_total': dossier.artifact_matrix_items_total,
            'ddjj_items_total': matrix.ddjj_items_total,
            'f22_items_total': matrix.f22_items_total,
            'warnings_total': dossier.warnings_total,
            'warnings_reviewed_total': 0,
            'warnings_pending_review_total': 0,
            'review_state': EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW,
            'review_state_counts': {
                EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW: dossier.artifact_matrix_items_total,
            },
            'item_refs': [],
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
        }
        dossier_hash = payload_hash(summary)
        AnnualTaxDossier.objects.filter(pk=dossier.pk).update(
            review_state=EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW,
            resumen_dossier=summary,
            hash_dossier=dossier_hash,
        )
        dossier.review_state = EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
        dossier.resumen_dossier = summary
        dossier.hash_dossier = dossier_hash
        annual_tax_dossiers = {
            'total': 1,
            'ids': [str(dossier.id)],
            'by_id': {
                str(dossier.id): {
                    'id': dossier.id,
                    'hash_dossier': dossier_hash,
                    'artifact_matrix_id': matrix.id,
                    'artifact_matrix_hash': matrix.hash_matriz,
                    'review_state': EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW,
                    'monthly_facts_total': dossier.monthly_facts_total,
                    'workbooks_total': dossier.workbooks_total,
                    'enterprise_registers_total': dossier.enterprise_registers_total,
                    'real_estate_sections_total': dossier.real_estate_sections_total,
                    'artifact_matrix_items_total': dossier.artifact_matrix_items_total,
                    'warnings_total': dossier.warnings_total,
                    'source_bundle_id': source_bundle.id,
                    'rule_set_id': rule_set.id,
                },
            },
        }
        process_summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        process_summary = {**process_summary, 'annual_tax_dossiers': annual_tax_dossiers}
        ProcesoRentaAnual.objects.filter(pk=process.pk).update(resumen_anual=process_summary)
        process.resumen_anual = process_summary

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
        self.assertEqual(result['responsible_review_gate']['state'], 'local_layers_incomplete')
        self.assertFalse(result['responsible_review_gate']['local_layers_ready_for_review'])
        self.assertFalse(result['responsible_review_gate']['review_manifest_required'])
        self.assertFalse(result['responsible_review_gate']['ready_for_responsible_decision_handoff'])
        self.assertFalse(result['responsible_review_gate']['ready_for_final_tax_calculation'])
        self.assertFalse(result['responsible_review_gate']['ready_for_sii_submission'])
        self.assertEqual(result['responsible_review_gate']['blocking_issue_code'], 'company_accounting.monthly_closes_missing')
        self.assertEqual(result['responsible_review_gate']['next_action_ref'], 'complete_local_phase:monthly_closes')
        self.assertFalse(result['responsible_review_gate']['raw_paths_returned'])
        self.assertNotIn('://', json.dumps(result))

    def test_progress_counts_controlled_f29_no_declaration_month(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)

        close = self._create_close(empresa, 1)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2025,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'company-accounting-progress-test'},
            borrador_ref='f29-progress-draft',
            responsable_revision_ref='f29-progress-owner',
        )
        self._create_no_declaration_monthly_tax_fact(empresa, 2)

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertEqual(result['phases']['f29_monthly']['completed'], 2)
        self.assertEqual(result['phases']['f29_monthly']['missing'], [3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_progress_ignores_f29_preparation_without_reviewable_payload(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)

        incomplete_close = self._create_close(empresa, 1)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=incomplete_close,
            anio=2025,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'company-accounting-progress-test'},
            borrador_ref='',
            responsable_revision_ref='',
        )
        sensitive_close = self._create_close(empresa, 2)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=sensitive_close,
            anio=2025,
            mes=2,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'https://sii.example.test/f29?token=secret'},
            borrador_ref='f29-progress-sensitive-draft',
            responsable_revision_ref='f29-progress-owner',
        )
        reviewable_close = self._create_close(empresa, 3)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=reviewable_close,
            anio=2025,
            mes=3,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'company-accounting-progress-test'},
            borrador_ref='f29-progress-reviewable-draft',
            responsable_revision_ref='f29-progress-owner',
        )
        self._create_no_declaration_monthly_tax_fact(empresa, 4)

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertEqual(result['phases']['f29_monthly']['completed'], 2)
        self.assertEqual(result['phases']['f29_monthly']['missing'], [1, 2, 5, 6, 7, 8, 9, 10, 11, 12])
        self.assertNotIn('token=secret', json.dumps(result))

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
        trial_balance = AnnualTaxTrialBalance.objects.create(
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
        workbooks = []
        for kind in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
            workbooks.append(AnnualTaxWorkbook.objects.create(
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
            ))
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
        export = AnnualTaxExport.objects.create(
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

        missing_package_result = collect_company_accounting_candidates(empresa_ids=[empresa.id, empresa_sin_senales.id])
        self.assertEqual(missing_package_result['candidates'][0]['years'][0]['signals']['annual_trial_balance'], 0)
        self.assertEqual(missing_package_result['candidates'][0]['years'][0]['signals']['rli_cpt_workbooks'], 0)
        self.assertEqual(missing_package_result['candidates'][0]['years'][0]['signals']['annual_dossier'], 0)
        self.assertEqual(missing_package_result['candidates'][0]['years'][0]['signals']['annual_export'], 0)

        self._create_trial_balance_line(trial_balance)
        for workbook in workbooks:
            self._create_workbook_line(workbook)
        missing_dossier_result = collect_company_accounting_candidates(empresa_ids=[empresa.id, empresa_sin_senales.id])
        self.assertEqual(missing_dossier_result['candidates'][0]['years'][0]['signals']['annual_trial_balance'], 1)
        self.assertEqual(missing_dossier_result['candidates'][0]['years'][0]['signals']['rli_cpt_workbooks'], 2)
        self.assertEqual(missing_dossier_result['candidates'][0]['years'][0]['signals']['annual_dossier'], 0)
        self.assertEqual(missing_dossier_result['candidates'][0]['years'][0]['signals']['annual_export'], 0)

        self._prepare_reviewable_dossier(
            process=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            matrix=matrix,
            dossier=dossier,
        )
        export_payload = self._export_package_payload()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=export_payload,
            hash_export=payload_hash(export_payload),
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

    def test_candidates_count_controlled_f29_no_declaration_month(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        self._create_no_declaration_monthly_tax_fact(empresa, 2)

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id])

        self.assertEqual(result['summary']['candidate_companies'], 1)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['f29_monthly'], 1)
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_candidates_ignore_f29_preparation_without_reviewable_payload(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)

        incomplete_close = self._create_close(empresa, 1)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=incomplete_close,
            anio=2025,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'candidate-f29-test'},
            borrador_ref='',
            responsable_revision_ref='',
        )
        sensitive_close = self._create_close(empresa, 2)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=sensitive_close,
            anio=2025,
            mes=2,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'https://sii.example.test/f29?token=secret'},
            borrador_ref='candidate-f29-sensitive-draft',
            responsable_revision_ref='candidate-reviewer',
        )
        reviewable_close = self._create_close(empresa, 3)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=reviewable_close,
            anio=2025,
            mes=3,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'candidate-f29-test'},
            borrador_ref='candidate-f29-reviewable-draft',
            responsable_revision_ref='candidate-reviewer',
        )
        self._create_no_declaration_monthly_tax_fact(empresa, 4)

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id])

        self.assertEqual(result['summary']['candidate_companies'], 1)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['f29_monthly'], 2)
        self.assertNotIn('token=secret', json.dumps(result))
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_candidates_ignore_annual_process_without_frozen_source_bundle(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        self._create_close(empresa, 1)
        ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
            resumen_anual={'source': 'company-accounting-progress-test'},
        )

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id])

        self.assertEqual(result['candidates'][0]['years'][0]['signals']['monthly_closes'], 1)
        self.assertEqual(result['candidates'][0]['years'][0]['signals']['annual_processes'], 0)
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_candidates_ignore_downstream_annual_artifacts_without_valid_process(self):
        empresa = self._create_empresa()
        config = self._activate_fiscal_config(empresa)
        self._create_close(empresa, 1, fiscal_year=2025)
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
            storage_ref='candidate-invalid-process-balance',
            resumen={'cuadrado': True, 'source': 'candidate-invalid-process-test'},
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
            source_ref='candidate-invalid-process-trial-balance',
            responsible_ref='candidate-reviewer',
            lines_total=1,
            resumen_balance={'source': 'candidate-invalid-process-test'},
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
                source_ref=f'candidate-invalid-process-{kind.lower()}',
                responsible_ref='candidate-reviewer',
                resumen_workbook={'source': 'candidate-invalid-process-test', 'tipo': kind},
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
            source_ref='candidate-invalid-process-matrix',
            responsible_ref='candidate-reviewer',
            items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            resumen_matriz={'source': 'candidate-invalid-process-test'},
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
            source_ref='candidate-invalid-process-dossier',
            responsible_ref='candidate-reviewer',
            dossier_ref='candidate-invalid-process-dossier-ref',
            monthly_facts_total=1,
            workbooks_total=2,
            artifact_matrix_items_total=2,
            resumen_dossier={'source': 'candidate-invalid-process-test'},
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
            source_ref='candidate-invalid-process-export',
            responsible_ref='candidate-reviewer',
            export_ref='candidate-invalid-process-export-ref',
            target_items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            export_payload={'source': 'candidate-invalid-process-test'},
            hash_export='8' * 64,
            estado=EstadoAnnualTaxExport.PREPARED,
        )

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id])
        signals = result['candidates'][0]['years'][0]['signals']

        self.assertEqual(signals['monthly_closes'], 1)
        self.assertEqual(signals['monthly_balances'], 1)
        self.assertEqual(signals['monthly_balances_squared'], 1)
        self.assertEqual(signals['annual_processes'], 0)
        self.assertEqual(signals['annual_trial_balance'], 0)
        self.assertEqual(signals['rli_cpt_workbooks'], 0)
        self.assertEqual(signals['annual_dossier'], 0)
        self.assertEqual(signals['annual_export'], 0)
        self.assertNotIn(empresa.rut, json.dumps(result))

    def test_candidates_ignore_downstream_annual_artifacts_with_mismatched_source_bundle(self):
        empresa = self._create_empresa()
        config = self._activate_fiscal_config(empresa)
        self._create_close(empresa, 1, fiscal_year=2025)
        source_bundle = self._create_source_bundle(empresa)
        mismatched_source_bundle = self._create_mismatched_source_bundle(empresa)
        rule_set, official_source = self._create_rule_set(config)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
            source_bundle=source_bundle,
            resumen_anual={'source': 'company-accounting-progress-test'},
        )
        source_balance = BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2025-12',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            storage_ref='candidate-mismatched-process-balance',
            resumen={'cuadrado': True, 'source': 'candidate-mismatched-source-test'},
        )
        AnnualTaxTrialBalance.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=mismatched_source_bundle,
            rule_set=rule_set,
            official_source=official_source,
            source_balance=source_balance,
            anio_tributario=2026,
            anio_comercial=2025,
            periodo_cierre='2025-12',
            source_ref='candidate-mismatched-trial-balance',
            responsible_ref='candidate-reviewer',
            lines_total=1,
            resumen_balance={'source': 'candidate-mismatched-source-test'},
            hash_balance='4' * 64,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )
        for kind in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
            AnnualTaxWorkbook.objects.create(
                empresa=empresa,
                proceso_renta_anual=process,
                source_bundle=mismatched_source_bundle,
                rule_set=rule_set,
                anio_tributario=2026,
                anio_comercial=2025,
                tipo=kind,
                source_ref=f'candidate-mismatched-{kind.lower()}',
                responsible_ref='candidate-reviewer',
                resumen_workbook={'source': 'candidate-mismatched-source-test', 'tipo': kind},
                hash_workbook='5' * 64,
                estado=EstadoAnnualTaxWorkbook.PREPARED,
            )
        matrix = AnnualTaxArtifactMatrix.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=mismatched_source_bundle,
            rule_set=rule_set,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='candidate-mismatched-matrix',
            responsible_ref='candidate-reviewer',
            items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            resumen_matriz={'source': 'candidate-mismatched-source-test'},
            hash_matriz='6' * 64,
            estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
        )
        dossier = AnnualTaxDossier.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=mismatched_source_bundle,
            rule_set=rule_set,
            artifact_matrix=matrix,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='candidate-mismatched-dossier',
            responsible_ref='candidate-reviewer',
            dossier_ref='candidate-mismatched-dossier-ref',
            monthly_facts_total=1,
            workbooks_total=2,
            artifact_matrix_items_total=2,
            resumen_dossier={'source': 'candidate-mismatched-source-test'},
            hash_dossier='7' * 64,
            estado=EstadoAnnualTaxDossier.PREPARED,
        )
        AnnualTaxExport.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            dossier=dossier,
            source_bundle=mismatched_source_bundle,
            rule_set=rule_set,
            artifact_matrix=matrix,
            official_format_source=official_source,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='candidate-mismatched-export',
            responsible_ref='candidate-reviewer',
            export_ref='candidate-mismatched-export-ref',
            target_items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            export_payload={'source': 'candidate-mismatched-source-test'},
            hash_export='8' * 64,
            estado=EstadoAnnualTaxExport.PREPARED,
        )

        result = collect_company_accounting_candidates(empresa_ids=[empresa.id])
        signals = result['candidates'][0]['years'][0]['signals']

        self.assertEqual(signals['monthly_closes'], 1)
        self.assertEqual(signals['annual_processes'], 1)
        self.assertEqual(signals['annual_trial_balance'], 0)
        self.assertEqual(signals['rli_cpt_workbooks'], 0)
        self.assertEqual(signals['annual_dossier'], 0)
        self.assertEqual(signals['annual_export'], 0)
        self.assertNotIn(empresa.rut, json.dumps(result))

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

    def test_progress_requires_annual_process_frozen_source_bundle(self):
        empresa = self._create_empresa()
        self._activate_fiscal_config(empresa)
        ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
            resumen_anual={'source': 'company-accounting-progress-test'},
        )

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertFalse(result['phases']['annual_process']['ready'])
        self.assertEqual(result['phases']['annual_process']['missing'], ['source_bundle_congelado'])
        self.assertIn(
            'company_accounting.annual_process_source_bundle_missing',
            {issue['code'] for issue in result['issues']},
        )
        self.assertNotIn(empresa.rut, json.dumps(result))

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
        trial_balance = AnnualTaxTrialBalance.objects.create(
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
        workbooks = []
        for kind in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
            workbooks.append(AnnualTaxWorkbook.objects.create(
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
            ))
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
        export = AnnualTaxExport.objects.create(
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

        missing_lines_result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)
        self.assertEqual(missing_lines_result['classification'], 'parcial')
        self.assertFalse(missing_lines_result['ready_for_company_accounting_review'])
        self.assertFalse(missing_lines_result['phases']['annual_trial_balance']['ready'])
        self.assertEqual(missing_lines_result['next_blocking_phase'], 'annual_trial_balance')
        self.assertIn(
            'company_accounting.annual_trial_balance_missing',
            {issue['code'] for issue in missing_lines_result['issues']},
        )

        self._create_trial_balance_line(trial_balance)
        missing_workbook_lines_result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)
        self.assertEqual(missing_workbook_lines_result['classification'], 'parcial')
        self.assertFalse(missing_workbook_lines_result['ready_for_company_accounting_review'])
        self.assertTrue(missing_workbook_lines_result['phases']['annual_trial_balance']['ready'])
        self.assertFalse(missing_workbook_lines_result['phases']['rli_cpt_workbooks']['ready'])
        self.assertEqual(missing_workbook_lines_result['next_blocking_phase'], 'rli_cpt_workbooks')
        self.assertIn(
            'company_accounting.rli_cpt_workbooks_missing',
            {issue['code'] for issue in missing_workbook_lines_result['issues']},
        )

        for workbook in workbooks:
            self._create_workbook_line(workbook)
        missing_package_result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)
        self.assertEqual(missing_package_result['classification'], 'parcial')
        self.assertFalse(missing_package_result['ready_for_company_accounting_review'])
        self.assertTrue(missing_package_result['phases']['annual_trial_balance']['ready'])
        self.assertTrue(missing_package_result['phases']['rli_cpt_workbooks']['ready'])
        self.assertFalse(missing_package_result['phases']['annual_dossier']['ready'])
        self.assertFalse(missing_package_result['phases']['annual_export']['ready'])
        self.assertEqual(missing_package_result['next_blocking_phase'], 'annual_dossier')
        self.assertIn(
            'company_accounting.annual_dossier_missing',
            {issue['code'] for issue in missing_package_result['issues']},
        )

        self._prepare_reviewable_dossier(
            process=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            matrix=matrix,
            dossier=dossier,
        )
        missing_export_result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)
        self.assertEqual(missing_export_result['classification'], 'parcial')
        self.assertFalse(missing_export_result['ready_for_company_accounting_review'])
        self.assertTrue(missing_export_result['phases']['annual_dossier']['ready'])
        self.assertFalse(missing_export_result['phases']['annual_export']['ready'])
        self.assertEqual(missing_export_result['next_blocking_phase'], 'annual_export')
        self.assertIn(
            'company_accounting.annual_export_missing',
            {issue['code'] for issue in missing_export_result['issues']},
        )

        malformed_export_payload = self._export_package_payload()
        malformed_export_payload['export_file_package_files_total'] = 'not-a-number'
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=malformed_export_payload,
            hash_export=payload_hash(malformed_export_payload),
        )
        malformed_package_result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)
        self.assertEqual(malformed_package_result['classification'], 'parcial')
        self.assertFalse(malformed_package_result['phases']['annual_export']['ready'])

        export_payload = self._export_package_payload()
        AnnualTaxExport.objects.filter(pk=export.pk).update(
            export_payload=export_payload,
            hash_export=payload_hash(export_payload),
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
        self.assertEqual(result['responsible_review_gate']['state'], 'responsible_review_required')
        self.assertTrue(result['responsible_review_gate']['local_layers_ready_for_review'])
        self.assertTrue(result['responsible_review_gate']['review_manifest_required'])
        self.assertFalse(result['responsible_review_gate']['ready_for_responsible_decision_handoff'])
        self.assertFalse(result['responsible_review_gate']['ready_for_productive_accounting_review'])
        self.assertFalse(result['responsible_review_gate']['ready_for_final_tax_calculation'])
        self.assertFalse(result['responsible_review_gate']['ready_for_sii_submission'])
        self.assertTrue(result['responsible_review_gate']['requires_responsible_review'])
        self.assertTrue(result['responsible_review_gate']['requires_external_or_controlled_review_artifact'])
        self.assertEqual(
            result['responsible_review_gate']['blocking_issue_code'],
            'company_accounting.responsible_review_missing',
        )
        self.assertEqual(
            result['responsible_review_gate']['next_action_ref'],
            'audit_or_materialize_responsible_answers',
        )
        self.assertFalse(result['responsible_review_gate']['raw_paths_returned'])

    def test_progress_rejects_annual_artifact_with_mismatched_source_bundle(self):
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
                storage_ref=f'balance-progress-mismatched-{month}',
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
                borrador_ref=f'f29-progress-mismatched-{month}',
                responsable_revision_ref='f29-progress-owner',
            )

        source_bundle = self._create_source_bundle(empresa)
        mismatched_source_bundle = self._create_mismatched_source_bundle(empresa)
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
            source_bundle=mismatched_source_bundle,
            rule_set=rule_set,
            official_source=official_source,
            source_balance=december_balance,
            anio_tributario=2026,
            anio_comercial=2025,
            periodo_cierre='2025-12',
            source_ref='trial-balance-progress-mismatched-source',
            responsible_ref='trial-balance-progress-owner',
            lines_total=1,
            resumen_balance={'source': 'company-accounting-progress-test'},
            hash_balance='4' * 64,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )

        result = collect_company_accounting_progress(empresa_id=empresa.id, fiscal_year=2025)

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_company_accounting_review'])
        self.assertTrue(result['phases']['annual_process']['ready'])
        self.assertFalse(result['phases']['annual_trial_balance']['ready'])
        self.assertEqual(result['phases']['annual_trial_balance']['completed'], 0)
        self.assertEqual(result['next_blocking_phase'], 'annual_trial_balance')
        self.assertIn('company_accounting.annual_trial_balance_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['responsible_review_gate']['state'], 'local_layers_incomplete')
        self.assertEqual(
            result['responsible_review_gate']['next_action_ref'],
            'complete_local_phase:annual_trial_balance',
        )
        self.assertNotIn(empresa.rut, json.dumps(result))

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
