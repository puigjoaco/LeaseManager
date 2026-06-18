import json
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

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
from core.annual_tax_source_manifest import payload_hash
from core.company_accounting_review_package import build_company_accounting_review_package, canonical_company_review_ref
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
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
    EstadoMonthlyTaxFact,
    EstadoReglaTributariaAnual,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxYearRuleSet,
    TipoAnnualTaxWorkbook,
    TipoAnnualTaxOfficialSource,
)


def _complete_bank_manifest(*, empresa=None, fiscal_year=2025, tax_year=2026):
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
                'statement_strength': 'expected_complete',
            }
        ],
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
            resumen_anual={'source': 'company-accounting-review-package-test'},
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
            source_ref='trial-balance-review-package-source',
            responsible_ref='trial-balance-review-package-owner',
            lines_total=1,
            resumen_balance={'source': 'company-accounting-review-package-test'},
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
                source_ref=f'{kind.lower()}-review-package-source',
                responsible_ref='workbook-review-package-owner',
                resumen_workbook={'source': 'company-accounting-review-package-test', 'tipo': kind},
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
            source_ref='export-review-package-source',
            responsible_ref='export-review-package-owner',
            export_ref='export-review-package-ref',
            target_items_total=2,
            ddjj_items_total=1,
            f22_items_total=1,
            export_payload={'source': 'company-accounting-review-package-test'},
            hash_export='8' * 64,
            estado=EstadoAnnualTaxExport.PREPARED,
        )

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
        self.assertEqual(result['summary']['blocking_issues_total'], 0)
        self.assertEqual(result['issues'], [])
        self.assertIn('package_hash', result)
        self.assertIn('accounting_progress_hash', result['evidence'])
        self.assertIn('bank_support_hash', result['evidence'])
        self.assertFalse(result['boundary']['autonomous_accounting'])
        self.assertFalse(result['boundary']['final_tax_calculation'])
        self.assertFalse(result['boundary']['sii_submission'])
        self.assertTrue(result['boundary']['requires_responsible_review'])
        self.assertIn(
            'company_accounting_review.company_bank_support.bank_confirmation_not_file_by_file_verified',
            {warning['code'] for warning in result['warnings']},
        )
        rendered = json.dumps(result)
        self.assertNotIn(empresa.rut, rendered)
        self.assertNotIn('://', rendered)
        self.assertNotIn('@', rendered)

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
            self.assertIn(
                'company_accounting_review.accounting_progress_incomplete',
                {issue['code'] for issue in result['issues']},
            )
            self.assertNotIn(empresa.rut, stdout.getvalue())

            with self.assertRaisesMessage(CommandError, 'Paquete de revision contable/renta incompleto'):
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    fail_on_incomplete=True,
                    stdout=StringIO(),
                )

            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_company_accounting_review_package',
                    empresa_id=empresa.id,
                    fiscal_year=2025,
                    bank_support_manifest=str(manifest_path),
                    output='docs/company-accounting-review-package.json',
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
