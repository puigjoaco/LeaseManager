import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
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
)
from contabilidad.services import ensure_default_regime
from core.annual_tax_source_manifest import payload_hash
from core.company_accounting_review_package import (
    build_company_accounting_review_package,
    canonical_company_review_ref,
    verify_company_accounting_review_package,
)
from core.company_document_intake import write_company_document_intake_package
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
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
    TipoAnnualTaxWorkbook,
    TipoAnnualTaxOfficialSource,
    TipoAnnualTaxArtifactTarget,
)
from sii.services import summarize_annual_tax_exports


def _complete_bank_manifest(*, empresa=None, fiscal_year=2025, tax_year=2026, statement_strength='verified_complete'):
    operations = [
        {'operation_ref': f'leasing-op-{index:02d}', 'label_ref': f'bank-leasing-{index:02d}'}
        for index in range(1, 4)
    ]
    attachments = []
    for operation in operations:
        operation_ref = operation['operation_ref']
        attachments.extend(
            [
                {
                    'attachment_ref': f'{operation_ref}-contract-schedule',
                    'operation_refs': [operation_ref],
                    'category': 'contract_or_schedule',
                    'source_ref': 'gmail-thread-redacted',
                },
                {
                    'attachment_ref': f'{operation_ref}-payment-history',
                    'operation_refs': [operation_ref],
                    'category': 'payment_history',
                    'source_ref': 'gmail-thread-redacted',
                },
            ]
        )
    attachments.append(
        {
            'attachment_ref': 'invoice-bundle-redacted',
            'operation_refs': ['*'],
            'category': 'invoice_or_tax_document_bundle',
            'source_ref': 'gmail-thread-redacted',
        }
    )
    return {
        'schema_version': 'company-bank-support-coverage-manifest.v1',
        'company_ref': canonical_company_review_ref(empresa.id) if empresa is not None else 'company-1',
        'fiscal_year': fiscal_year,
        'tax_year': tax_year,
        'required_operations': operations,
        'attachments': attachments,
        'confirmations': [
            {
                'confirmation_ref': 'bank-confirmation-redacted',
                'source_ref': 'gmail-thread-redacted',
                'statement_strength': statement_strength,
            }
        ],
    }


def _complete_document_intake_manifest(
    *,
    empresa,
    fiscal_year=2025,
    tax_year=2026,
    statement_strength='verified_complete',
    source_kind='manual_review_packet',
):
    company_ref = canonical_company_review_ref(empresa.id)
    operations = [
        {'operation_ref': f'leasing-op-{index:02d}', 'label_ref': f'bank-leasing-{index:02d}'}
        for index in range(1, 4)
    ]
    documents = []
    for operation in operations:
        operation_ref = operation['operation_ref']
        documents.extend(
            [
                {
                    'document_ref': f'{operation_ref}-contract-schedule',
                    'batch_ref': 'gmail-thread-redacted',
                    'category': 'bank_contract_or_schedule',
                    'operation_refs': [operation_ref],
                },
                {
                    'document_ref': f'{operation_ref}-payment-history',
                    'batch_ref': 'gmail-thread-redacted',
                    'category': 'bank_payment_history',
                    'operation_refs': [operation_ref],
                },
            ]
        )
    documents.extend(
        [
            {
                'document_ref': 'invoice-bundle-redacted',
                'batch_ref': 'gmail-thread-redacted',
                'category': 'bank_invoice_or_tax_document_bundle',
                'operation_refs': ['*'],
            },
            {
                'document_ref': 'bank-confirmation-redacted',
                'batch_ref': 'gmail-thread-redacted',
                'category': 'bank_confirmation',
                'statement_strength': statement_strength,
            },
        ]
    )
    return {
        'schema_version': 'company-document-intake-manifest.v1',
        'company_ref': company_ref,
        'fiscal_year': fiscal_year,
        'tax_year': tax_year,
        'source_batches': [
            {
                'batch_ref': 'gmail-thread-redacted',
                'source_kind': source_kind,
                'source_ref': 'manual-review-packet-redacted',
                'declared_complete': True,
                'statement_strength': statement_strength,
            }
        ],
        'required_bank_operations': operations,
        'documents': documents,
    }


class CompanyAccountingReviewPackageTests(TestCase):
    def _create_empresa(self):
        socio = Socio.objects.create(nombre='Socio Review', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(
            razon_social='Empresa Review SpA',
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
            resumen_obligaciones={'source': 'company-accounting-review-package-test', 'month': month},
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
            source_label='company-accounting-review-package-controlled',
            authorization_ref='company-accounting-review-package-authorization',
            responsible_ref='company-accounting-review-package-owner',
            hash_fuentes='1' * 64,
            resumen_fuentes={'source': 'company-accounting-review-package-test'},
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

    def _process_summary(self, source_bundle):
        return {
            'fiscal_year': source_bundle.anio_comercial,
            'annual_tax_source_bundle': {
                'id': source_bundle.id,
                'source_kind': source_bundle.source_kind,
                'source_label': source_bundle.source_label,
                'hash_fuentes': source_bundle.hash_fuentes,
                'anio_comercial': source_bundle.anio_comercial,
                'approved_closes_total': 12,
                'obligations_total': 12,
                'f29_preparations_total': 12,
                'real_estate_properties_total': 1,
            },
            'annual_tax_monthly_facts': {
                'total': 12,
                'months': list(range(1, 13)),
                'obligations_total': 12,
                'rent_distributions_total': 1,
                'liquidation_lines_total': 12,
            },
        }

    def _create_rule_set(self, config):
        source = AnnualTaxOfficialSource.objects.create(
            anio_tributario=2026,
            source_key='company-accounting-review-package-source',
            source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            title='Fuente experta controlada',
            source_ref='company-accounting-review-package-source-ref',
            source_hash='2' * 64,
            retrieved_on=date(2026, 6, 18),
            responsible_ref='company-accounting-review-package-source-owner',
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            metadata={'source': 'company-accounting-review-package-test'},
        )
        rule_set = TaxYearRuleSet.objects.create(
            anio_tributario=2026,
            regimen_tributario=config.regimen_tributario,
            version='AT2026-review-package-test',
            estado=EstadoReglaTributariaAnual.APPROVED,
            fuente_ref='company-accounting-review-package-rules',
            hash_normativo='3' * 64,
            responsable_aprobacion_ref='company-accounting-review-package-rule-owner',
            official_source=source,
            metadata={'source': 'company-accounting-review-package-test'},
        )
        return rule_set, source

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
            'source': 'company-accounting-review-package-test',
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

    def _create_trial_balance_line(self, trial_balance):
        account, _ = CuentaContable.objects.get_or_create(
            empresa=trial_balance.empresa,
            plan_cuentas_version='company-review-package-test',
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
            source_payload={'source': 'company-accounting-review-package-test', 'trial_balance_id': trial_balance.id},
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
                'metadata': {'source': 'company-accounting-review-package-test'},
            },
        )
        return AnnualTaxWorkbookLine.objects.create(
            workbook=workbook,
            mapping=mapping,
            codigo_interno=mapping.codigo_interno,
            codigo_destino=mapping.codigo_destino,
            origen='company-accounting-review-package-test',
            monto_clp='1000.00',
            formula_ref=f'{workbook.tipo.lower()}-line-formula-controlled',
            evidencia_ref=f'{workbook.tipo.lower()}-line-evidence-controlled',
            source_payload={'source': 'company-accounting-review-package-test', 'workbook_id': workbook.id},
            hash_linea='e' * 64,
            estado=EstadoRegistro.ACTIVE,
        )

    def _prepare_reviewable_dossier(self, *, process, source_bundle, rule_set, matrix, dossier):
        summary = {
            'source': 'company-accounting-review-package-test',
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

    def _prepare_reviewable_export(self, *, process, export):
        export.refresh_from_db()
        process_summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        process_summary = {**process_summary, 'annual_tax_exports': summarize_annual_tax_exports(process)}
        ProcesoRentaAnual.objects.filter(pk=process.pk).update(resumen_anual=process_summary)
        process.resumen_anual = process_summary

    def _prepare_complete_accounting_layers(self, empresa):
        config = self._activate_fiscal_config(empresa)
        f29_capability = self._create_f29_capability(empresa)
        december_balance = None
        for month in range(1, 13):
            close = self._create_close(empresa, month)
            balance = BalanceComprobacion.objects.create(
                empresa=empresa,
                periodo=f'2025-{month:02d}',
                estado_snapshot=EstadoCierreMensual.APPROVED,
                storage_ref=f'balance-review-package-{month}',
                resumen={'cuadrado': True, 'source': 'company-accounting-review-package-test'},
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
                resumen_formulario={'source': 'company-accounting-review-package-test'},
                borrador_ref=f'f29-review-package-draft-{month}',
                responsable_revision_ref='f29-review-package-owner',
            )
            resumen = {
                'empresa_id': empresa.id,
                'anio': 2025,
                'mes': month,
                'source': 'company-accounting-review-package-test',
            }
            MonthlyTaxFact.objects.create(
                empresa=empresa,
                anio=2025,
                mes=month,
                cierre_mensual=close,
                source_ref=f'monthly-tax-fact-review-package-{month}',
                responsible_ref='company-accounting-review-package-owner',
                resumen_hecho=resumen,
                hash_hecho=payload_hash(resumen),
                estado=EstadoMonthlyTaxFact.NORMALIZED,
            )

        source_bundle = self._create_source_bundle(empresa)
        rule_set, official_source = self._create_rule_set(config)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
            source_bundle=source_bundle,
            fecha_preparacion=timezone.now(),
            resumen_anual=self._process_summary(source_bundle),
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
            source_ref='trial-balance-review-package-source',
            responsible_ref='trial-balance-review-package-owner',
            lines_total=1,
            resumen_balance={'source': 'company-accounting-review-package-test'},
            hash_balance='4' * 64,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        )
        self._create_trial_balance_line(trial_balance)
        for kind in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
            workbook = AnnualTaxWorkbook.objects.create(
                empresa=empresa,
                proceso_renta_anual=process,
                source_bundle=source_bundle,
                rule_set=rule_set,
                anio_tributario=2026,
                anio_comercial=2025,
                tipo=kind,
                source_ref=f'{kind.lower()}-review-package-source',
                responsible_ref='workbook-review-package-owner',
                resumen_workbook={'source': 'company-accounting-review-package-test', 'tipo': kind},
                hash_workbook='5' * 64,
                estado=EstadoAnnualTaxWorkbook.PREPARED,
            )
            self._create_workbook_line(workbook)
        matrix = AnnualTaxArtifactMatrix.objects.create(
            empresa=empresa,
            proceso_renta_anual=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            anio_tributario=2026,
            anio_comercial=2025,
            source_ref='matrix-review-package-source',
            responsible_ref='matrix-review-package-owner',
            items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            resumen_matriz={'source': 'company-accounting-review-package-test'},
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
            source_ref='dossier-review-package-source',
            responsible_ref='dossier-review-package-owner',
            dossier_ref='dossier-review-package-ref',
            monthly_facts_total=12,
            workbooks_total=2,
            artifact_matrix_items_total=2,
            resumen_dossier={'source': 'company-accounting-review-package-test'},
            hash_dossier='7' * 64,
            estado=EstadoAnnualTaxDossier.PREPARED,
        )
        self._prepare_reviewable_dossier(
            process=process,
            source_bundle=source_bundle,
            rule_set=rule_set,
            matrix=matrix,
            dossier=dossier,
        )
        export_payload = self._export_package_payload()
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
            source_ref='export-review-package-source',
            responsible_ref='export-review-package-owner',
            export_ref='export-review-package-ref',
            target_items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            export_payload=export_payload,
            hash_export=payload_hash(export_payload),
            estado=EstadoAnnualTaxExport.PREPARED,
        )
        self._prepare_reviewable_export(process=process, export=export)

    def test_complete_accounting_and_bank_support_are_ready_for_responsible_review_only(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)

        result = build_company_accounting_review_package(
            empresa_id=empresa.id,
            fiscal_year=2025,
            bank_support_payload=_complete_bank_manifest(empresa=empresa),
        )

        self.assertEqual(result['schema_version'], 'company-accounting-review-package.v1')
        self.assertEqual(result['classification'], 'preparado')
        self.assertTrue(result['ready_for_productive_accounting_review'])
        self.assertEqual(result['summary']['accounting_progress_percent'], 100)
        self.assertEqual(result['summary']['expected_company_ref'], canonical_company_review_ref(empresa.id))
        self.assertEqual(result['summary']['bank_support_company_ref'], canonical_company_review_ref(empresa.id))
        self.assertEqual(result['summary']['bank_support_coverage_percent'], 100)
        self.assertEqual(result['summary']['document_intake_source_kind'], 'bank_support_manifest')
        self.assertEqual(result['summary']['document_intake_package_hash'], '')
        self.assertIsNone(result['summary']['document_intake_ready_for_productive_review'])
        self.assertTrue(result['summary']['ready_for_formal_bank_support_review'])
        self.assertTrue(result['summary']['bank_support_strong_confirmation_present'])
        self.assertEqual(result['summary']['accounting_responsible_review_gate_state'], 'responsible_review_required')
        self.assertEqual(
            result['summary']['accounting_responsible_review_next_action_ref'],
            'audit_or_materialize_responsible_answers',
        )
        self.assertEqual(
            result['summary']['accounting_responsible_review_blocking_issue_code'],
            'company_accounting.responsible_review_missing',
        )
        self.assertTrue(result['summary']['accounting_local_layers_ready_for_review'])
        self.assertTrue(result['summary']['accounting_review_manifest_required'])
        self.assertFalse(result['summary']['accounting_ready_for_responsible_decision_handoff'])
        self.assertFalse(result['summary']['accounting_ready_for_final_tax_calculation'])
        self.assertFalse(result['summary']['accounting_ready_for_sii_submission'])
        self.assertEqual(result['summary']['blocking_issues_total'], 0)
        self.assertEqual(result['issues'], [])
        self.assertIn('package_hash', result)
        self.assertIn('accounting_progress_hash', result['evidence'])
        self.assertIn('bank_support_hash', result['evidence'])
        self.assertFalse(result['boundary']['autonomous_accounting'])
        self.assertFalse(result['boundary']['final_tax_calculation'])
        self.assertFalse(result['boundary']['sii_submission'])
        self.assertTrue(result['boundary']['requires_responsible_review'])
        self.assertEqual(result['warnings'], [])
        rendered = json.dumps(result)
        self.assertNotIn(empresa.rut, rendered)
        self.assertNotIn('://', rendered)
        self.assertNotIn('@', rendered)

    def test_expected_bank_confirmation_keeps_package_partial_until_formal_confirmation(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)

        result = build_company_accounting_review_package(
            empresa_id=empresa.id,
            fiscal_year=2025,
            bank_support_payload=_complete_bank_manifest(
                empresa=empresa,
                statement_strength='expected_complete',
            ),
        )

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_productive_accounting_review'])
        self.assertTrue(result['summary']['ready_for_accounting_document_review'])
        self.assertFalse(result['summary']['ready_for_formal_bank_support_review'])
        self.assertFalse(result['summary']['bank_support_strong_confirmation_present'])
        self.assertIn(
            'company_accounting_review.bank_support_formal_confirmation_missing',
            {issue['code'] for issue in result['issues']},
        )
        self.assertIn(
            'company_accounting_review.company_bank_support.bank_confirmation_not_file_by_file_verified',
            {warning['code'] for warning in result['warnings']},
        )

    def test_bank_support_year_mismatch_blocks_productive_review_even_when_inputs_are_ready(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)

        result = build_company_accounting_review_package(
            empresa_id=empresa.id,
            fiscal_year=2025,
            bank_support_payload=_complete_bank_manifest(empresa=empresa, fiscal_year=2024, tax_year=2026),
        )

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_productive_accounting_review'])
        self.assertIn(
            'company_accounting_review.bank_support_fiscal_year_mismatch',
            {issue['code'] for issue in result['issues']},
        )

    def test_bank_support_company_ref_mismatch_blocks_productive_review_even_when_inputs_are_ready(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        manifest = _complete_bank_manifest(empresa=empresa)
        manifest['company_ref'] = 'company-999999'

        result = build_company_accounting_review_package(
            empresa_id=empresa.id,
            fiscal_year=2025,
            bank_support_payload=manifest,
        )

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_productive_accounting_review'])
        self.assertEqual(result['summary']['expected_company_ref'], canonical_company_review_ref(empresa.id))
        self.assertEqual(result['summary']['bank_support_company_ref'], 'company-999999')
        self.assertIn(
            'company_accounting_review.bank_support_company_ref_mismatch',
            {issue['code'] for issue in result['issues']},
        )

    def test_bank_support_company_ref_missing_blocks_productive_review_even_when_inputs_are_ready(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        manifest = _complete_bank_manifest(empresa=empresa)
        manifest['company_ref'] = ''

        result = build_company_accounting_review_package(
            empresa_id=empresa.id,
            fiscal_year=2025,
            bank_support_payload=manifest,
        )

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_productive_accounting_review'])
        self.assertIn(
            'company_accounting_review.bank_support_company_ref_missing',
            {issue['code'] for issue in result['issues']},
        )

    def test_command_outputs_redacted_package_and_can_fail_on_incomplete(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'audit_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                bank_support_manifest=str(manifest_path),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['classification'], 'parcial')
            self.assertFalse(result['ready_for_productive_accounting_review'])
            self.assertEqual(result['summary']['accounting_responsible_review_gate_state'], 'local_layers_incomplete')
            self.assertEqual(
                result['summary']['accounting_responsible_review_next_action_ref'],
                'complete_local_phase:fiscal_config',
            )
            self.assertIn(
                'company_accounting_review.accounting_progress_incomplete',
                {issue['code'] for issue in result['issues']},
            )
            self.assertNotIn(empresa.rut, stdout.getvalue())

            with self.assertRaises(CommandError) as error:
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )
            self.assertIn('Paquete de revision contable/renta incompleto', str(error.exception))
            self.assertIn('review_gate=local_layers_incomplete', str(error.exception))
            self.assertIn('next_action=complete_local_phase:fiscal_config', str(error.exception))

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    output='docs/company-accounting-review-package.json',
                    stdout=StringIO(),
                )

    def test_audit_fail_on_incomplete_reports_formal_bank_support_readiness(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        manifest = _complete_bank_manifest(
            empresa=empresa,
            statement_strength='expected_complete',
        )

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('formal_bank_support_ready=False', rendered_error)
            self.assertIn('document_intake_ready=None', rendered_error)

    def test_audit_command_accepts_verified_document_intake_package(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            intake_dir = Path(temp_dir) / 'company-document-intake-package'
            intake_manifest = _complete_document_intake_manifest(empresa=empresa)
            intake_package = write_company_document_intake_package(
                payload=intake_manifest,
                output_dir=intake_dir,
            )
            stdout = StringIO()

            call_command(
                'audit_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                document_intake_package_dir=str(intake_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())

            self.assertEqual(result['classification'], 'preparado')
            self.assertTrue(result['ready_for_productive_accounting_review'])
            self.assertEqual(result['summary']['document_intake_source_kind'], 'document_intake_package')
            self.assertEqual(result['summary']['document_intake_package_hash'], intake_package['package_hash'])
            self.assertTrue(result['summary']['document_intake_ready_for_productive_review'])
            self.assertTrue(result['summary']['document_intake_ready_for_formal_bank_support_manifest'])

    def test_audit_command_document_intake_not_ready_blocks_review_package(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            intake_dir = Path(temp_dir) / 'company-document-intake-package'
            intake_manifest = _complete_document_intake_manifest(
                empresa=empresa,
                source_kind='unsupported_source_kind',
            )
            intake_package = write_company_document_intake_package(
                payload=intake_manifest,
                output_dir=intake_dir,
            )
            stdout = StringIO()

            call_command(
                'audit_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                document_intake_package_dir=str(intake_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())

            self.assertEqual(result['classification'], 'parcial')
            self.assertFalse(result['ready_for_productive_accounting_review'])
            self.assertEqual(result['summary']['document_intake_source_kind'], 'document_intake_package')
            self.assertEqual(result['summary']['document_intake_package_hash'], intake_package['package_hash'])
            self.assertFalse(result['summary']['document_intake_ready_for_productive_review'])
            self.assertIn(
                'company_accounting_review.document_intake_not_productive_ready',
                {issue['code'] for issue in result['issues']},
            )

            with self.assertRaisesMessage(CommandError, 'document_intake_ready=False'):
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    document_intake_package_dir=str(intake_dir),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )

    def test_audit_command_requires_exactly_one_review_source(self):
        empresa = self._create_empresa()

        with self.assertRaisesMessage(CommandError, 'exactamente una fuente'):
            call_command(
                'audit_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                stdout=StringIO(),
            )

    def test_command_redacts_sensitive_bank_manifest_values(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)
        manifest['company_ref'] = '76.123.456-7'
        manifest['attachments'][0]['source_ref'] = 'https://bank.example.test/file?token=secret'
        manifest['attachments'][1]['local_path'] = 'C:\\Users\\owner\\Downloads\\factura.pdf'
        manifest['confirmations'][0]['password'] = 'last-six-rut-digits'

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            stdout = StringIO()

            call_command(
                'audit_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                bank_support_manifest=str(manifest_path),
                stdout=stdout,
            )

            rendered = stdout.getvalue()
            self.assertNotIn('https://bank.example.test', rendered)
            self.assertNotIn('last-six-rut-digits', rendered)
            self.assertNotIn('76.123.456-7', rendered)
            self.assertNotIn('C:\\Users\\owner\\Downloads', rendered)
            self.assertIn(REDACTED_SENSITIVE_REFERENCE, rendered)
            self.assertIn('company_accounting_review.bank_support_company_ref_mismatch', rendered)
            self.assertIn('company_bank_support.sensitive_reference', rendered)

    def test_audit_command_missing_manifest_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()

        with TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(missing_path),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No existe manifest JSON o no es un archivo legible.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_audit_command_read_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)

        with TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with patch.object(
                Path,
                'read_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/bank-support.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'audit_company_accounting_review_package',
                        empresa_id=empresa.id,
                        fiscal_year=2025,
                        bank_support_manifest=str(manifest_path),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo leer manifest JSON.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_audit_command_write_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)

        with TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            manifest_path = temp_root / 'bank-support-manifest.json'
            output_path = temp_root / 'Socio Controlado Uno 11111111-1' / 'review-package.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with patch.object(
                Path,
                'write_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/review-package.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'audit_company_accounting_review_package',
                        empresa_id=empresa.id,
                        fiscal_year=2025,
                        bank_support_manifest=str(manifest_path),
                        output=str(output_path),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo escribir paquete de revision contable/renta.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_materialize_company_accounting_review_package_command_writes_verified_package(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        manifest = _complete_bank_manifest(empresa=empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            output_dir = Path(temp_dir) / 'company-accounting-review-package'
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                bank_support_manifest=str(manifest_path),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            verification = verify_company_accounting_review_package(
                empresa_id=empresa.id,
                fiscal_year=2025,
                bank_support_payload=manifest,
                package_dir=output_dir,
            )

            self.assertTrue(result['materialized'])
            self.assertEqual(result['package_hash'], verification['package_hash'])
            self.assertEqual(result['classification'], 'preparado')
            self.assertTrue(result['ready_for_productive_accounting_review'])
            self.assertEqual(result['expected_company_ref'], canonical_company_review_ref(empresa.id))
            self.assertEqual(result['bank_support_company_ref'], canonical_company_review_ref(empresa.id))
            self.assertEqual(result['accounting_progress_percent'], 100)
            self.assertEqual(result['accounting_responsible_review_gate_state'], 'responsible_review_required')
            self.assertEqual(
                result['accounting_responsible_review_next_action_ref'],
                'audit_or_materialize_responsible_answers',
            )
            self.assertEqual(
                result['accounting_responsible_review_blocking_issue_code'],
                'company_accounting.responsible_review_missing',
            )
            self.assertTrue(result['accounting_local_layers_ready_for_review'])
            self.assertTrue(result['accounting_review_manifest_required'])
            self.assertFalse(result['accounting_ready_for_responsible_decision_handoff'])
            self.assertEqual(result['bank_support_coverage_percent'], 100)
            self.assertFalse(result['autonomous_accounting'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertFalse(result['sii_submission'])
            self.assertTrue(result['requires_responsible_review'])
            self.assertTrue((output_dir / result['manifest_file']).is_file())

            rendered = stdout.getvalue()
            manifest_rendered = (output_dir / result['manifest_file']).read_text(encoding='utf-8')
            self.assertNotIn(empresa.rut, rendered)
            self.assertNotIn(empresa.rut, manifest_rendered)
            self.assertNotIn('://', rendered)
            self.assertNotIn('://', manifest_rendered)
            self.assertNotIn('@', rendered)
            self.assertNotIn('@', manifest_rendered)

    def test_materialize_company_accounting_review_package_accepts_verified_document_intake_package(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            intake_dir = Path(temp_dir) / 'company-document-intake-package'
            output_dir = Path(temp_dir) / 'company-accounting-review-package'
            intake_manifest = _complete_document_intake_manifest(empresa=empresa)
            intake_package = write_company_document_intake_package(
                payload=intake_manifest,
                output_dir=intake_dir,
            )
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                document_intake_package_dir=str(intake_dir),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())

            self.assertTrue(result['materialized'])
            self.assertEqual(result['source_kind'], 'document_intake_package')
            self.assertEqual(result['document_intake_package_hash'], intake_package['package_hash'])
            self.assertTrue(result['document_intake_ready_for_productive_review'])
            self.assertTrue(result['document_intake_ready_for_formal_bank_support_manifest'])
            self.assertEqual(result['classification'], 'preparado')
            self.assertTrue(result['ready_for_productive_accounting_review'])
            self.assertEqual(result['bank_support_company_ref'], canonical_company_review_ref(empresa.id))
            self.assertEqual(result['bank_support_coverage_percent'], 100)
            self.assertFalse(result['autonomous_accounting'])
            self.assertFalse(result['final_tax_calculation'])
            self.assertFalse(result['sii_submission'])
            self.assertTrue((output_dir / result['manifest_file']).is_file())

    def test_document_intake_package_not_ready_blocks_accounting_review_package(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            intake_dir = Path(temp_dir) / 'company-document-intake-package'
            output_dir = Path(temp_dir) / 'company-accounting-review-package'
            intake_manifest = _complete_document_intake_manifest(
                empresa=empresa,
                source_kind='unsupported_source_kind',
            )
            intake_package = write_company_document_intake_package(
                payload=intake_manifest,
                output_dir=intake_dir,
            )
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                document_intake_package_dir=str(intake_dir),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            manifest = json.loads((output_dir / result['manifest_file']).read_text(encoding='utf-8'))
            issue_codes = {issue['code'] for issue in manifest['issues']}

            self.assertEqual(result['source_kind'], 'document_intake_package')
            self.assertEqual(result['document_intake_package_hash'], intake_package['package_hash'])
            self.assertFalse(result['document_intake_ready_for_productive_review'])
            self.assertTrue(result['document_intake_ready_for_formal_bank_support_manifest'])
            self.assertEqual(result['classification'], 'parcial')
            self.assertFalse(result['ready_for_productive_accounting_review'])
            self.assertEqual(manifest['summary']['document_intake_source_kind'], 'document_intake_package')
            self.assertEqual(manifest['summary']['document_intake_package_hash'], intake_package['package_hash'])
            self.assertFalse(manifest['summary']['document_intake_ready_for_productive_review'])
            self.assertIn(
                'company_accounting_review.document_intake_not_productive_ready',
                issue_codes,
            )

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    document_intake_package_dir=str(intake_dir),
                    output_dir=str(Path(temp_dir) / 'company-accounting-review-package-fail'),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('review_gate=responsible_review_required', rendered_error)
            self.assertIn('next_action=audit_or_materialize_responsible_answers', rendered_error)
            self.assertIn('formal_bank_support_ready=True', rendered_error)
            self.assertIn('document_intake_ready=False', rendered_error)

    def test_materialize_fail_on_incomplete_reports_formal_bank_support_readiness(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        manifest = _complete_bank_manifest(
            empresa=empresa,
            statement_strength='expected_complete',
        )
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    output_dir=str(Path(temp_dir) / 'company-accounting-review-package'),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertIn('formal_bank_support_ready=False', rendered_error)
            self.assertIn('document_intake_ready=None', rendered_error)

    def test_materialize_company_accounting_review_package_rejects_nonempty_output_dir(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            output_dir = Path(temp_dir) / 'company-accounting-review-package'
            output_dir.mkdir()
            stale_file = output_dir / 'stale.txt'
            stale_file.write_text('previous company review package residue', encoding='utf-8')

            with self.assertRaisesMessage(CommandError, 'debe estar vacio'):
                call_command(
                    'materialize_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    output_dir=str(output_dir),
                    stdout=StringIO(),
                )

            self.assertTrue(stale_file.exists())

    def test_materialize_company_accounting_review_package_rejects_versioned_repo_output(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'company-accounting-review-package'

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'materialize_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    output_dir=str(blocked_output),
                    stdout=StringIO(),
                )

            self.assertFalse(blocked_output.exists())

    def test_materialize_company_accounting_review_package_redacts_sensitive_manifest_values(self):
        empresa = self._create_empresa()
        self._prepare_complete_accounting_layers(empresa)
        manifest = _complete_bank_manifest(empresa=empresa)
        manifest['company_ref'] = '76.123.456-7'
        manifest['attachments'][0]['source_ref'] = 'https://bank.example.test/file?token=secret'
        manifest['attachments'][1]['local_path'] = 'C:\\Users\\owner\\Downloads\\factura.pdf'
        manifest['confirmations'][0]['password'] = 'last-six-rut-digits'
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            manifest_path = Path(temp_dir) / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            output_dir = Path(temp_dir) / 'company-accounting-review-package'
            stdout = StringIO()

            call_command(
                'materialize_company_accounting_review_package',
                empresa_id=empresa.id,
                fiscal_year=2025,
                bank_support_manifest=str(manifest_path),
                output_dir=str(output_dir),
                stdout=stdout,
            )

            result = json.loads(stdout.getvalue())
            self.assertEqual(result['classification'], 'parcial')
            self.assertFalse(result['ready_for_productive_accounting_review'])
            manifest_rendered = (output_dir / result['manifest_file']).read_text(encoding='utf-8')
            for sensitive_value in (
                'https://bank.example.test',
                'last-six-rut-digits',
                '76.123.456-7',
                'C:\\Users\\owner\\Downloads',
                empresa.rut,
            ):
                self.assertNotIn(sensitive_value, stdout.getvalue())
                self.assertNotIn(sensitive_value, manifest_rendered)
            self.assertIn(REDACTED_SENSITIVE_REFERENCE, manifest_rendered)

    def test_materialize_command_missing_manifest_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            missing_path = Path(temp_dir) / 'Socio Controlado Uno 11111111-1.json'

            with self.assertRaises(CommandError) as error:
                call_command(
                    'materialize_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(missing_path),
                    output_dir=str(Path(temp_dir) / 'company-accounting-review-package'),
                    stdout=StringIO(),
                )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No existe manifest JSON o no es un archivo legible.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)

    def test_materialize_command_read_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            temp_root = Path(temp_dir)
            manifest_path = temp_root / 'Socio Controlado Uno 11111111-1.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with patch.object(
                Path,
                'read_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/bank-support.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_company_accounting_review_package',
                        empresa_id=empresa.id,
                        fiscal_year=2025,
                        bank_support_manifest=str(manifest_path),
                        output_dir=str(temp_root / 'company-accounting-review-package'),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo leer manifest JSON.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)

    def test_materialize_command_write_error_does_not_echo_sensitive_path(self):
        empresa = self._create_empresa()
        manifest = _complete_bank_manifest(empresa=empresa)
        local_evidence_root = Path(settings.PROJECT_ROOT) / 'local-evidence'
        local_evidence_root.mkdir(exist_ok=True)

        with TemporaryDirectory(dir=local_evidence_root) as temp_dir:
            temp_root = Path(temp_dir)
            manifest_path = temp_root / 'bank-support-manifest.json'
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')

            with patch.object(
                Path,
                'write_text',
                side_effect=OSError('D:/Privado/Socio Controlado Uno 11111111-1/review-package.json'),
            ):
                with self.assertRaises(CommandError) as error:
                    call_command(
                        'materialize_company_accounting_review_package',
                        empresa_id=empresa.id,
                        fiscal_year=2025,
                        bank_support_manifest=str(manifest_path),
                        output_dir=str(temp_root / 'Socio Controlado Uno 11111111-1'),
                        stdout=StringIO(),
                    )

            rendered_error = str(error.exception)
            self.assertEqual(rendered_error, 'No se pudo escribir/verificar paquete contable/renta.')
            self.assertNotIn('Socio Controlado Uno', rendered_error)
            self.assertNotIn('11111111-1', rendered_error)
            self.assertNotIn('D:/Privado', rendered_error)
