import json
import hashlib
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent
from contabilidad.models import (
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    ObligacionTributariaMensual,
)
from contabilidad.services import ensure_default_regime
from core.stage6_renta_anual_readiness import collect_stage6_renta_anual_readiness
from documentos.models import (
    DocumentoEmitido,
    EstadoDocumento,
    ExpedienteDocumental,
    OrigenDocumento,
    PlantillaDocumental,
    PoliticaFirmaYNotaria,
    TipoDocumental,
)
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio
from patrimonio.models import Propiedad, TipoInmueble
from sii.models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxReviewChecklist,
    AmbienteSII,
    AnnualTaxSourceBundle,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DestinoMapeoTributarioAnual,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxOfficialSource,
    EstadoAnnualTaxSourceBundle,
    EstadoRegistro,
    EstadoReglaTributariaAnual,
    EstadoGateSII,
    F22PreparacionAnual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualTaxOfficialSource,
)
from sii.services import (
    summarize_annual_enterprise_registers,
    summarize_annual_real_estate_sections,
    summarize_annual_tax_artifact_matrices,
    summarize_annual_tax_dossiers,
    summarize_annual_tax_exports,
    summarize_annual_tax_review_checklists,
    summarize_annual_tax_workbooks,
    sync_annual_enterprise_registers,
    sync_annual_real_estate_section,
    sync_annual_tax_artifact_matrix,
    sync_annual_tax_dossier,
    sync_annual_tax_export,
    sync_annual_tax_review_checklist,
    sync_annual_tax_workbooks,
    sync_monthly_tax_facts,
)


VALID_DOCUMENT_SHA256 = 'd' * 64


class Stage6RentaAnualReadinessTests(TestCase):
    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='Empresa Stage6 SpA', rut='66666666-6'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', f'{rut[:7]}1-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', f'{rut[:7]}2-2')
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde=date(2025, 1, 1),
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde=date(2025, 1, 1),
            activo=True,
        )
        return empresa

    def _sii_readiness_fields(self, prefix):
        return {
            'certificado_ref': f'certificado-{prefix}-ref',
            'evidencia_ref': f'evidencia-{prefix}-gate',
            'prueba_flujo_ref': f'prueba-{prefix}-flujo',
            'autorizacion_ambiente_ref': f'ambiente-{prefix}-certificacion',
            'regla_fiscal_ref': f'regla-{prefix}-validada',
        }

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

    def _open_capability(self, empresa, capability_key, prefix=None, **overrides):
        payload = {
            'empresa': empresa,
            'capacidad_key': capability_key,
            **self._sii_readiness_fields(prefix or capability_key.lower()),
            'ambiente': AmbienteSII.CERTIFICATION,
            'estado_gate': EstadoGateSII.OPEN,
            'ultimo_resultado': {},
        }
        payload.update(overrides)
        return CapacidadTributariaSII.objects.create(**payload)

    def _create_twelve_approved_closes(self, empresa, fiscal_year=2025):
        for month in range(1, 13):
            CierreMensualContable.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                estado=EstadoCierreMensual.APPROVED,
                fecha_preparacion=timezone.now(),
                fecha_aprobacion=timezone.now(),
                resumen_obligaciones={'month': month, 'source': 'stage6-controlled'},
            )
            ObligacionTributariaMensual.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                obligacion_tipo='PPM',
                base_imponible=Decimal('100000.00'),
                monto_calculado=Decimal('10000.00'),
                estado_preparacion=EstadoPreparacionTributaria.APPROVED,
                detalle_calculo={'source': 'stage6-controlled'},
            )

    def _annual_summary(self, fiscal_year=2025):
        return {
            'fiscal_year': fiscal_year,
            'obligaciones': [
                {
                    'anio': fiscal_year,
                    'mes': month,
                    'tipo': 'PPM',
                    'monto_calculado': '10000.00',
                    'estado_preparacion': EstadoPreparacionTributaria.APPROVED,
                }
                for month in range(1, 13)
            ],
            'total_obligaciones': 12,
            'total_monto_calculado': '120000.00',
        }

    def _create_tax_support_document(self, process):
        PoliticaFirmaYNotaria.objects.get_or_create(
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            defaults={
                'requiere_firma_arrendador': False,
                'requiere_firma_arrendatario': False,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
        )
        PlantillaDocumental.objects.get_or_create(
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            version_plantilla='stage6-v1',
            defaults={
                'plantilla_ref': 'templates/respaldo_tributario/stage6-v1',
                'checksum_plantilla': VALID_DOCUMENT_SHA256,
                'descripcion': 'Plantilla controlada para respaldo tributario anual.',
                'estado': 'activa',
            },
        )
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='proceso_renta_anual',
            entidad_id=str(process.pk),
            owner_operativo='tributario-stage6',
        )
        user = get_user_model().objects.create_user(
            username=f'stage6-docs-{process.pk}',
            password='secret123',
        )
        return DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            version_plantilla='stage6-v1',
            checksum=VALID_DOCUMENT_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen=OrigenDocumento.GENERATED,
            estado=EstadoDocumento.ISSUED,
            storage_ref='local-evidence/stage6/certificado-renta-anual.pdf',
        )

    def _create_official_source(self, *, anio_tributario=2026, applies_to='', regime_code=''):
        target_key = applies_to.lower() if applies_to else 'ruleset'
        return AnnualTaxOfficialSource.objects.create(
            anio_tributario=anio_tributario,
            source_key=f'expert-{target_key}-at{anio_tributario}',
            source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            title=f'Revision experta {target_key} AT{anio_tributario}',
            source_ref=f'expert-{target_key}-source-ref-at{anio_tributario}',
            source_hash='f' * 64,
            retrieved_on=date(2026, 6, 14),
            responsible_ref='tax-source-reviewer-controlled',
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            applies_to=applies_to,
            regime_code=regime_code,
            scope_note='Fuente experta controlada para pruebas locales Stage 6.',
            metadata={'source': 'stage6-controlled'},
        )

    def _create_approved_tax_year_ruleset(self, config, anio_tributario=2026):
        rule_source = self._create_official_source(
            anio_tributario=anio_tributario,
            regime_code=config.regimen_tributario.codigo_regimen,
        )
        rule_set = TaxYearRuleSet.objects.create(
            anio_tributario=anio_tributario,
            regimen_tributario=config.regimen_tributario,
            version='AT2026-controlled-v1',
            estado=EstadoReglaTributariaAnual.APPROVED,
            fuente_ref='tax-rule-source-at2026-controlled',
            hash_normativo='a' * 64,
            responsable_aprobacion_ref='tax-rule-reviewer-controlled',
            official_source=rule_source,
            metadata={'source': 'stage6-controlled'},
        )
        for destino, codigo_interno, codigo_destino, source_metric in (
            (
                DestinoMapeoTributarioAnual.RLI,
                'lease.revenue.net',
                'RLI-ING-001',
                'monthly_tax_facts.rent_distributions_total_devengado',
            ),
            (
                DestinoMapeoTributarioAnual.CPT,
                'lease.capital.taxable',
                'CPT-CAP-001',
                'monthly_tax_facts.obligations_total_amount',
            ),
            (
                DestinoMapeoTributarioAnual.RAI,
                'lease.register.rai',
                'RAI-REG-001',
                '',
            ),
            (
                DestinoMapeoTributarioAnual.SAC,
                'lease.register.sac',
                'SAC-REG-001',
                '',
            ),
        ):
            metadata = {'source': 'stage6-controlled'}
            if source_metric:
                metadata['source_metric'] = source_metric
            mapping_source = self._create_official_source(
                anio_tributario=anio_tributario,
                applies_to=destino,
                regime_code=config.regimen_tributario.codigo_regimen,
            )
            TaxCodeMapping.objects.create(
                rule_set=rule_set,
                destino=destino,
                codigo_interno=codigo_interno,
                codigo_destino=codigo_destino,
                formula_ref=f'formula-ref-{codigo_destino.lower()}-controlled',
                evidencia_ref=f'evidence-ref-{codigo_destino.lower()}-controlled',
                official_source=mapping_source,
                metadata=metadata,
            )
        return rule_set

    def _create_annual_source_bundle(self, empresa, *, anio_tributario=2026, fiscal_year=2025):
        source_summary = {
            'empresa_id': empresa.id,
            'anio_comercial': fiscal_year,
            'approved_close_months': list(range(1, 13)),
            'approved_closes_total': 12,
            'obligation_months': list(range(1, 13)),
            'obligations_total': 12,
            'obligations_total_amount': '120000.00',
            'f29_preparations_total': 0,
            'source_scope': 'stage6-controlled',
        }
        source_hash = hashlib.sha256(
            json.dumps(source_summary, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)
            .encode('utf-8')
        ).hexdigest()
        return AnnualTaxSourceBundle.objects.create(
            empresa=empresa,
            anio_tributario=anio_tributario,
            anio_comercial=fiscal_year,
            source_kind='snapshot_controlado',
            source_label='stage6-controlled-v1',
            authorization_ref='stage6-authorization-v1',
            responsible_ref='stage6-source-owner-v1',
            hash_fuentes=source_hash,
            resumen_fuentes=source_summary,
            estado=EstadoAnnualTaxSourceBundle.FROZEN,
        )

    def _create_valid_local_matrix(self):
        empresa = self._create_active_empresa()
        config = self._activate_fiscal_config(empresa)
        rule_set = self._create_approved_tax_year_ruleset(config)
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        self._create_twelve_approved_closes(empresa)
        Propiedad.objects.create(
            rol_avaluo='ROL-STAGE6-001',
            direccion='Propiedad Stage 6',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='STG6-001',
            estado='activa',
            empresa_owner=empresa,
        )
        source_bundle = self._create_annual_source_bundle(empresa)
        monthly_facts = sync_monthly_tax_facts(empresa, 2025)
        summary = self._annual_summary()
        summary['annual_tax_source_bundle'] = {
            'id': source_bundle.id,
            'source_kind': source_bundle.source_kind,
            'source_label': source_bundle.source_label,
            'hash_fuentes': source_bundle.hash_fuentes,
            'anio_comercial': source_bundle.anio_comercial,
            'approved_closes_total': source_bundle.resumen_fuentes['approved_closes_total'],
            'obligations_total': source_bundle.resumen_fuentes['obligations_total'],
            'f29_preparations_total': source_bundle.resumen_fuentes['f29_preparations_total'],
        }
        summary['annual_tax_monthly_facts'] = {
            'total': len(monthly_facts),
            'months': sorted(fact.mes for fact in monthly_facts),
            'obligations_total': sum(
                int((fact.resumen_hecho or {}).get('obligations_total') or 0)
                for fact in monthly_facts
            ),
            'rent_distributions_total': sum(
                int((fact.resumen_hecho or {}).get('rent_distributions_total') or 0)
                for fact in monthly_facts
            ),
            'liquidation_lines_total': sum(
                int((fact.resumen_hecho or {}).get('liquidation_lines_total') or 0)
                for fact in monthly_facts
            ),
        }
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.APPROVED,
            source_bundle=source_bundle,
            fecha_preparacion=timezone.now(),
            resumen_anual=summary,
            paquete_ddjj_ref='ddjj-package-stage6-controlled',
            borrador_f22_ref='f22-draft-stage6-controlled',
            responsable_revision_ref='stage6-review-owner-controlled',
        )
        sync_annual_tax_workbooks(process, rule_set, source_bundle)
        sync_annual_enterprise_registers(process, rule_set, source_bundle)
        sync_annual_real_estate_section(process, rule_set, source_bundle)
        summary['annual_tax_workbooks'] = summarize_annual_tax_workbooks(process)
        summary['annual_enterprise_registers'] = summarize_annual_enterprise_registers(process)
        summary['annual_real_estate_sections'] = summarize_annual_real_estate_sections(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_artifact_matrix(process, rule_set, source_bundle, config)
        summary['annual_tax_artifact_matrices'] = summarize_annual_tax_artifact_matrices(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_dossier(process, rule_set, source_bundle)
        summary['annual_tax_dossiers'] = summarize_annual_tax_dossiers(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary},
            paquete_ref='ddjj-package-stage6-controlled',
            responsable_revision_ref='stage6-review-owner-ddjj',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1'},
            borrador_ref='f22-draft-stage6-controlled',
            responsable_revision_ref='stage6-review-owner-f22',
        )
        sync_annual_tax_export(process, rule_set, source_bundle)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        sync_annual_tax_review_checklist(process, rule_set, source_bundle)
        summary['annual_tax_review_checklists'] = summarize_annual_tax_review_checklists(process)
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])
        self._create_tax_support_document(process)
        return empresa

    def _collect_with_final_refs(self):
        return collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_label='stage6-controlled-v1',
            authorization_ref='stage6-authorization-v1',
            source_kind='snapshot_controlado',
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_kind_not_authorized', issue_codes)
        self.assertIn('stage6.fiscal_config_missing', issue_codes)
        self.assertIn('stage6.ddjj.open_capability_missing', issue_codes)
        self.assertIn('stage6.annual_process_missing', issue_codes)
        self.assertIn('stage6.tax_support_document_missing', issue_codes)
        self.assertIn('stage6.fiscal_rule_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_annual_status_updated_event_without_transition_metadata_is_blocking(self):
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada sin metadata de transicion.',
            metadata={'estado_nuevo': EstadoPreparacionTributaria.APPROVED},
        )

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage6.audit.annual_status_transition_metadata_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['annual_status_transition_metadata_missing'], 1)

    def test_annual_status_updated_event_without_review_responsible_is_blocking(self):
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada sin responsable auditado.',
            metadata={
                'campo_estado': 'estado_preparacion',
                'estado_anterior': EstadoPreparacionTributaria.PREPARED,
                'estado_nuevo': EstadoPreparacionTributaria.APPROVED,
            },
        )

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage6.audit.annual_status_responsible_ref_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['annual_status_responsible_ref_missing'], 1)

    def test_annual_status_updated_event_with_sensitive_review_responsible_is_blocking_without_leak(self):
        AuditEvent.objects.create(
            event_type='sii.f22_preparacion.status_updated',
            entity_type='f22_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada con responsable sensible.',
            metadata={
                'campo_estado': 'estado_preparacion',
                'estado_anterior': EstadoPreparacionTributaria.PREPARED,
                'estado_nuevo': EstadoPreparacionTributaria.APPROVED,
                'responsable_revision_ref': 'https://sii.example.test/reviewer?token=secret',
            },
        )

        result = collect_stage6_renta_anual_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertIn('stage6.audit.annual_status_responsible_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['audit']['annual_status_responsible_ref_sensitive'], 1)
        self.assertNotIn('sii.example.test', serialized_result)
        self.assertNotIn('token=secret', serialized_result)

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_valid_local_matrix()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertTrue(result['sections']['source_trace']['source_label'])
        self.assertTrue(result['sections']['source_trace']['authorization_ref'])
        self.assertEqual(result['issues'], [])

    def test_annual_process_without_tax_workbooks_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()
        AnnualTaxWorkbook.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbooks_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_workbooks']['workbooks_total'], 0)

    def test_annual_tax_workbook_without_active_lines_is_blocking(self):
        self._create_valid_local_matrix()
        workbook = AnnualTaxWorkbook.objects.get(tipo='RLI')
        AnnualTaxWorkbookLine.objects.filter(workbook=workbook).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_line_missing', issue_codes)

    def test_annual_tax_workbook_line_warning_is_blocking(self):
        self._create_valid_local_matrix()
        line = AnnualTaxWorkbookLine.objects.select_related('workbook', 'mapping').get(workbook__tipo='RLI')
        line.warnings = ['source_metric_missing_or_unsupported']
        line.hash_linea = hashlib.sha256(
            json.dumps(
                {
                    'workbook_id': line.workbook_id,
                    'mapping_id': line.mapping_id,
                    'codigo_interno': line.codigo_interno,
                    'codigo_destino': line.codigo_destino,
                    'origen': line.origen,
                    'signo': line.signo,
                    'monto_clp': str(line.monto_clp),
                    'formula_ref': line.formula_ref,
                    'evidencia_ref': line.evidencia_ref,
                    'warnings': line.warnings,
                    'source_payload': line.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        line.save(update_fields=['warnings', 'hash_linea', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_line_warning_review_required', issue_codes)

    def test_annual_tax_workbook_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        workbook_summary = dict(summary['annual_tax_workbooks'])
        by_type = dict(workbook_summary['by_type'])
        rli_summary = dict(by_type['RLI'])
        rli_summary['hash_workbook'] = 'f' * 64
        by_type['RLI'] = rli_summary
        workbook_summary['by_type'] = by_type
        summary['annual_tax_workbooks'] = workbook_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)

    def test_invalid_annual_tax_workbook_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        workbook = AnnualTaxWorkbook.objects.get(tipo='RLI')
        line = AnnualTaxWorkbookLine.objects.get(workbook=workbook)
        AnnualTaxWorkbook.objects.filter(pk=workbook.pk).update(
            source_ref='https://sii.example.test/rli?token=secret',
            resumen_workbook={'api_key': 'secret'},
            hash_workbook='not-a-sha',
        )
        AnnualTaxWorkbookLine.objects.filter(pk=line.pk).update(
            evidencia_ref='https://sii.example.test/evidence?token=secret',
            source_payload={'access_token': 'secret'},
            hash_linea='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_invalid', issue_codes)
        self.assertIn('stage6.tax_workbook_line_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_enterprise_registers_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_enterprise_registers_missing', issue_codes)
        self.assertEqual(result['sections']['annual_enterprise_registers']['registers_total'], 0)

    def test_enterprise_register_without_active_movements_is_blocking(self):
        self._create_valid_local_matrix()
        register = AnnualEnterpriseRegisterSet.objects.get(tipo_registro='RAI')
        AnnualEnterpriseRegisterMovement.objects.filter(register_set=register).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.enterprise_register_movement_missing', issue_codes)

    def test_enterprise_register_movement_warning_is_blocking(self):
        self._create_valid_local_matrix()
        movement = AnnualEnterpriseRegisterMovement.objects.select_related('register_set').get(register_set__tipo_registro='RAI')
        movement.warnings = ['opening_balance_requires_expert_review']
        movement.hash_movimiento = hashlib.sha256(
            json.dumps(
                {
                    'register_set_id': movement.register_set_id,
                    'source_workbook_line_id': movement.source_workbook_line_id,
                    'codigo_interno': movement.codigo_interno,
                    'origen': movement.origen,
                    'signo': movement.signo,
                    'monto_clp': str(movement.monto_clp),
                    'formula_ref': movement.formula_ref,
                    'evidencia_ref': movement.evidencia_ref,
                    'warnings': movement.warnings,
                    'source_payload': movement.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        movement.save(update_fields=['warnings', 'hash_movimiento', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.enterprise_register_movement_warning_review_required', issue_codes)

    def test_enterprise_register_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        register_summary = dict(summary['annual_enterprise_registers'])
        by_type = dict(register_summary['by_type'])
        rai_summary = dict(by_type['RAI'])
        rai_summary['hash_registro'] = 'f' * 64
        by_type['RAI'] = rai_summary
        register_summary['by_type'] = by_type
        summary['annual_enterprise_registers'] = register_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_enterprise_register_summary_mismatch', issue_codes)

    def test_invalid_enterprise_register_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        register = AnnualEnterpriseRegisterSet.objects.get(tipo_registro='RAI')
        movement = AnnualEnterpriseRegisterMovement.objects.get(register_set=register)
        AnnualEnterpriseRegisterSet.objects.filter(pk=register.pk).update(
            source_ref='https://sii.example.test/rai?token=secret',
            resumen_registro={'api_key': 'secret'},
            hash_registro='not-a-sha',
        )
        AnnualEnterpriseRegisterMovement.objects.filter(pk=movement.pk).update(
            evidencia_ref='https://sii.example.test/movement?token=secret',
            source_payload={'access_token': 'secret-register-value'},
            hash_movimiento='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.enterprise_register_invalid', issue_codes)
        self.assertIn('stage6.enterprise_register_movement_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_real_estate_section_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualRealEstateSection.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_real_estate_section_missing', issue_codes)
        self.assertEqual(result['sections']['annual_real_estate_sections']['sections_total'], 0)

    def test_real_estate_section_without_active_items_is_blocking(self):
        self._create_valid_local_matrix()
        section = AnnualRealEstateSection.objects.get()
        AnnualRealEstateItem.objects.filter(section=section).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_item_missing', issue_codes)

    def test_real_estate_item_warning_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualRealEstateItem.objects.select_related('section').get()
        item.warnings = ['contribuciones_requires_expert_review']
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'section_id': item.section_id,
                    'propiedad_id': item.propiedad_id,
                    'codigo_propiedad_snapshot': item.codigo_propiedad_snapshot,
                    'rol_avaluo_snapshot': item.rol_avaluo_snapshot,
                    'direccion_snapshot': item.direccion_snapshot,
                    'comuna_snapshot': item.comuna_snapshot,
                    'region_snapshot': item.region_snapshot,
                    'tipo_inmueble_snapshot': item.tipo_inmueble_snapshot,
                    'owner_tipo_snapshot': item.owner_tipo_snapshot,
                    'owner_id_snapshot': item.owner_id_snapshot,
                    'arriendo_devengado_clp': str(item.arriendo_devengado_clp),
                    'arriendo_conciliado_clp': str(item.arriendo_conciliado_clp),
                    'arriendo_facturable_clp': str(item.arriendo_facturable_clp),
                    'contribuciones_clp': str(item.contribuciones_clp),
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'hash_item', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_item_warning_review_required', issue_codes)

    def test_real_estate_section_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        real_estate_summary = dict(summary['annual_real_estate_sections'])
        by_id = dict(real_estate_summary['by_id'])
        section_id = next(iter(by_id.keys()))
        section_summary = dict(by_id[section_id])
        section_summary['hash_seccion'] = 'f' * 64
        by_id[section_id] = section_summary
        real_estate_summary['by_id'] = by_id
        summary['annual_real_estate_sections'] = real_estate_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_real_estate_section_summary_mismatch', issue_codes)

    def test_invalid_real_estate_section_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        section = AnnualRealEstateSection.objects.get()
        item = AnnualRealEstateItem.objects.get(section=section)
        AnnualRealEstateSection.objects.filter(pk=section.pk).update(
            source_ref='https://sii.example.test/real-estate?token=secret',
            resumen_seccion={'api_key': 'secret-real-estate'},
            hash_seccion='not-a-sha',
        )
        AnnualRealEstateItem.objects.filter(pk=item.pk).update(
            evidencia_ref='https://sii.example.test/property?token=secret',
            source_payload={'access_token': 'secret-real-estate-item'},
            hash_item='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.real_estate_section_invalid', issue_codes)
        self.assertIn('stage6.real_estate_item_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_artifact_matrix_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()
        AnnualTaxExport.objects.all().delete()
        AnnualTaxDossier.objects.all().delete()
        AnnualTaxArtifactMatrix.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_artifact_matrix_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_artifact_matrices']['matrices_total'], 0)

    def test_artifact_matrix_without_active_items_is_blocking(self):
        self._create_valid_local_matrix()
        matrix = AnnualTaxArtifactMatrix.objects.get()
        AnnualTaxArtifactMatrixItem.objects.filter(matrix=matrix).update(estado=EstadoRegistro.INACTIVE)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.artifact_matrix_item_missing', issue_codes)
        self.assertIn('stage6.artifact_matrix_f22_item_missing', issue_codes)
        self.assertIn('stage6.artifact_matrix_ddjj_item_missing', issue_codes)

    def test_artifact_matrix_item_warning_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(target_kind='F22', target_code='F22-PREVIEW')
        item.warnings = ['artifact_requires_expert_review']
        item.review_state = EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'matrix_id': item.matrix_id,
                    'target_kind': item.target_kind,
                    'target_code': item.target_code,
                    'medio_sii': item.medio_sii,
                    'source_kind': item.source_kind,
                    'source_model': item.source_model,
                    'source_object_id': item.source_object_id,
                    'source_hash': item.source_hash,
                    'review_state': item.review_state,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'responsible_ref': item.responsible_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'review_state', 'hash_item', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.artifact_matrix_item_warning_review_required', issue_codes)

    def test_artifact_matrix_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        artifact_summary = dict(summary['annual_tax_artifact_matrices'])
        by_id = dict(artifact_summary['by_id'])
        matrix_id = next(iter(by_id.keys()))
        matrix_summary = dict(by_id[matrix_id])
        matrix_summary['hash_matriz'] = 'f' * 64
        by_id[matrix_id] = matrix_summary
        artifact_summary['by_id'] = by_id
        summary['annual_tax_artifact_matrices'] = artifact_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_artifact_matrix_summary_mismatch', issue_codes)

    def test_invalid_artifact_matrix_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        matrix = AnnualTaxArtifactMatrix.objects.get()
        item = AnnualTaxArtifactMatrixItem.objects.get(matrix=matrix, target_kind='F22', target_code='F22-PREVIEW')
        AnnualTaxArtifactMatrix.objects.filter(pk=matrix.pk).update(
            source_ref='https://sii.example.test/artifact-matrix?token=secret',
            resumen_matriz={'api_key': 'secret-artifact-matrix'},
            hash_matriz='not-a-sha',
        )
        AnnualTaxArtifactMatrixItem.objects.filter(pk=item.pk).update(
            evidencia_ref='https://sii.example.test/artifact-item?token=secret',
            source_payload={'access_token': 'secret-artifact-item'},
            hash_item='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.artifact_matrix_invalid', issue_codes)
        self.assertIn('stage6.artifact_matrix_item_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('access_token', serialized_result)

    def test_annual_process_without_tax_dossier_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()
        AnnualTaxExport.objects.all().delete()
        AnnualTaxDossier.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_dossier_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_dossiers']['dossiers_total'], 0)

    def test_tax_dossier_review_required_is_blocking(self):
        self._create_valid_local_matrix()
        item = AnnualTaxArtifactMatrixItem.objects.select_related('matrix').get(target_kind='F22', target_code='F22-PREVIEW')
        item.warnings = ['dossier_requires_expert_review']
        item.review_state = EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        item.hash_item = hashlib.sha256(
            json.dumps(
                {
                    'matrix_id': item.matrix_id,
                    'target_kind': item.target_kind,
                    'target_code': item.target_code,
                    'medio_sii': item.medio_sii,
                    'source_kind': item.source_kind,
                    'source_model': item.source_model,
                    'source_object_id': item.source_object_id,
                    'source_hash': item.source_hash,
                    'review_state': item.review_state,
                    'formula_ref': item.formula_ref,
                    'evidencia_ref': item.evidencia_ref,
                    'responsible_ref': item.responsible_ref,
                    'warnings': item.warnings,
                    'source_payload': item.source_payload,
                },
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        item.save(update_fields=['warnings', 'review_state', 'hash_item', 'updated_at'])
        process = ProcesoRentaAnual.objects.get()
        source_bundle = AnnualTaxSourceBundle.objects.get()
        rule_set = TaxYearRuleSet.objects.get()
        sync_annual_tax_dossier(process, rule_set, source_bundle)
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_dossiers': summarize_annual_tax_dossiers(process),
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_dossier_review_required', issue_codes)

    def test_tax_dossier_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        dossier_summary = dict(summary['annual_tax_dossiers'])
        by_id = dict(dossier_summary['by_id'])
        dossier_id = next(iter(by_id.keys()))
        item_summary = dict(by_id[dossier_id])
        item_summary['hash_dossier'] = 'f' * 64
        by_id[dossier_id] = item_summary
        dossier_summary['by_id'] = by_id
        summary['annual_tax_dossiers'] = dossier_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_dossier_summary_mismatch', issue_codes)

    def test_invalid_tax_dossier_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxDossier.objects.update(
            source_ref='https://sii.example.test/dossier?token=secret',
            responsible_ref='Bearer tax-dossier-secret',
            dossier_ref='https://sii.example.test/dossier-file?token=secret',
            resumen_dossier={'api_key': 'secret-tax-dossier'},
            hash_dossier='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_dossier_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('tax-dossier-secret', serialized_result)

    def test_tax_dossier_boundary_flags_are_blocking(self):
        self._create_valid_local_matrix()
        dossier = AnnualTaxDossier.objects.get()
        process = dossier.proceso_renta_anual
        dossier_summary = dict(dossier.resumen_dossier)
        dossier_summary.update(
            {
                'official_format': True,
                'sii_submission': True,
                'sii_submission_attempted': True,
                'final_tax_calculation': True,
            }
        )
        hash_dossier = hashlib.sha256(
            json.dumps(
                dossier_summary,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxDossier.objects.filter(pk=dossier.pk).update(
            resumen_dossier=dossier_summary,
            hash_dossier=hash_dossier,
        )
        process_summary = dict(process.resumen_anual)
        dossier_process_summary = dict(process_summary['annual_tax_dossiers'])
        by_id = dict(dossier_process_summary['by_id'])
        item_summary = dict(by_id[str(dossier.id)])
        item_summary['hash_dossier'] = hash_dossier
        by_id[str(dossier.id)] = item_summary
        dossier_process_summary['by_id'] = by_id
        process_summary['annual_tax_dossiers'] = dossier_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_dossier_invalid', issue_codes)
        self.assertIn('stage6.tax_dossier_official_format_boundary', issue_codes)
        self.assertIn('stage6.tax_dossier_sii_submission_boundary', issue_codes)
        self.assertIn('stage6.tax_dossier_final_calculation_boundary', issue_codes)

    def test_annual_process_without_tax_export_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()
        AnnualTaxExport.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_export_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_exports']['exports_total'], 0)

    def test_tax_export_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        export_summary = dict(summary['annual_tax_exports'])
        by_id = dict(export_summary['by_id'])
        export_id = next(iter(by_id.keys()))
        item_summary = dict(by_id[export_id])
        item_summary['hash_export'] = 'f' * 64
        by_id[export_id] = item_summary
        export_summary['by_id'] = by_id
        summary['annual_tax_exports'] = export_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_export_summary_mismatch', issue_codes)

    def test_invalid_tax_export_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxExport.objects.update(
            source_ref='https://sii.example.test/export?token=secret',
            responsible_ref='Bearer tax-export-secret',
            export_ref='https://sii.example.test/export-file?token=secret',
            export_payload={'api_key': 'secret-tax-export'},
            hash_export='not-a-sha',
            official_format=True,
            sii_submission=True,
            final_tax_calculation=True,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_export_invalid', issue_codes)
        self.assertIn('stage6.tax_export_official_format_boundary', issue_codes)
        self.assertIn('stage6.tax_export_sii_submission_boundary', issue_codes)
        self.assertIn('stage6.tax_export_final_calculation_boundary', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('tax-export-secret', serialized_result)

    def test_annual_process_without_tax_review_checklist_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_review_checklist_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax_review_checklists']['checklists_total'], 0)

    def test_tax_review_checklist_summary_hash_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        summary = dict(process.resumen_anual)
        checklist_summary = dict(summary['annual_tax_review_checklists'])
        by_id = dict(checklist_summary['by_id'])
        checklist_id = next(iter(by_id.keys()))
        item_summary = dict(by_id[checklist_id])
        item_summary['hash_checklist'] = 'e' * 64
        by_id[checklist_id] = item_summary
        checklist_summary['by_id'] = by_id
        summary['annual_tax_review_checklists'] = checklist_summary
        process.resumen_anual = summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_review_checklist_summary_mismatch', issue_codes)

    def test_invalid_tax_review_checklist_is_blocking_without_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxReviewChecklist.objects.update(
            checklist_ref='https://sii.example.test/checklist?token=secret',
            responsible_ref='Bearer tax-checklist-secret',
            evidence_ref='https://sii.example.test/evidence?token=secret',
            review_payload={'api_key': 'secret-tax-checklist'},
            hash_checklist='not-a-sha',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('api_key', serialized_result)
        self.assertNotIn('tax-checklist-secret', serialized_result)

    def test_tax_review_checklist_boundary_flags_are_blocking(self):
        self._create_valid_local_matrix()
        checklist = AnnualTaxReviewChecklist.objects.get()
        process = checklist.proceso_renta_anual
        review_payload = dict(checklist.review_payload)
        review_payload.update(
            {
                'official_format': True,
                'sii_submission': True,
                'sii_submission_attempted': True,
                'final_tax_calculation': True,
            }
        )
        hash_checklist = hashlib.sha256(
            json.dumps(
                review_payload,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=True,
                default=str,
            ).encode('utf-8')
        ).hexdigest()
        AnnualTaxReviewChecklist.objects.filter(pk=checklist.pk).update(
            review_payload=review_payload,
            hash_checklist=hash_checklist,
        )
        process_summary = dict(process.resumen_anual)
        checklist_process_summary = dict(process_summary['annual_tax_review_checklists'])
        by_id = dict(checklist_process_summary['by_id'])
        item_summary = dict(by_id[str(checklist.id)])
        item_summary['hash_checklist'] = hash_checklist
        by_id[str(checklist.id)] = item_summary
        checklist_process_summary['by_id'] = by_id
        process_summary['annual_tax_review_checklists'] = checklist_process_summary
        process.resumen_anual = process_summary
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_review_checklist_invalid', issue_codes)
        self.assertIn('stage6.tax_review_checklist_official_format_boundary', issue_codes)
        self.assertIn('stage6.tax_review_checklist_sii_submission_boundary', issue_codes)
        self.assertIn('stage6.tax_review_checklist_final_calculation_boundary', issue_codes)

    def test_valid_local_matrix_and_non_sensitive_refs_cannot_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_kind_not_authorized', issue_codes)

    def test_annual_process_without_source_bundle_is_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(source_bundle=None)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_source_bundle_missing', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_source_bundle_missing'], 1)

    def test_invalid_annual_source_bundle_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxSourceBundle.objects.update(
            source_label='https://sii.example.test/source?token=secret',
            hash_fuentes='bad-hash',
            resumen_fuentes={'api_key': 'secret'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.source_bundle_invalid', issue_codes)
        self.assertNotIn('sii.example.test', serialized_result)
        self.assertNotIn('token=secret', serialized_result)

    def test_annual_process_source_bundle_summary_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_source_bundle': {
                **process.resumen_anual['annual_tax_source_bundle'],
                'hash_fuentes': 'f' * 64,
            },
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_source_bundle_summary_mismatch', issue_codes)

    def test_annual_process_without_monthly_tax_facts_is_blocking(self):
        self._create_valid_local_matrix()
        MonthlyTaxFact.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.monthly_tax_fact_missing', issue_codes)
        self.assertIn('stage6.process_monthly_tax_facts_missing', issue_codes)
        self.assertEqual(result['sections']['monthly_tax_facts']['process_monthly_tax_facts_missing'], 1)

    def test_invalid_monthly_tax_fact_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        MonthlyTaxFact.objects.filter(mes=1).update(
            source_ref='https://sii.example.test/monthly?token=secret',
            hash_hecho='bad-hash',
            resumen_hecho={'api_key': 'secret-monthly-value'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.monthly_tax_fact_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('secret-monthly-value', serialized_result)

    def test_monthly_tax_fact_summary_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_monthly_facts': {
                **process.resumen_anual['annual_tax_monthly_facts'],
                'months': list(range(1, 12)),
            },
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_monthly_tax_fact_summary_mismatch', issue_codes)

    def test_annual_process_without_rli_cpt_workbooks_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()
        AnnualTaxWorkbookLine.objects.all().delete()
        AnnualTaxWorkbook.objects.all().delete()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': {'total': 2, 'types': ['CPT', 'RLI'], 'by_type': {}},
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbooks_missing', issue_codes)
        self.assertIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)
        self.assertEqual(result['sections']['annual_tax_workbooks']['process_tax_workbooks_missing'], 1)

    def test_invalid_annual_tax_workbook_line_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxWorkbookLine.objects.filter(codigo_destino='RLI-ING-001').update(
            origen='',
            formula_ref='https://sii.example.test/formula?token=secret',
            evidencia_ref='Bearer annual-line-secret',
            source_payload={'api_key': 'secret-line-value'},
            hash_linea='bad-hash',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_workbook_line_invalid', issue_codes)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('secret-line-value', serialized_result)

    def test_annual_tax_workbook_summary_mismatch_is_blocking(self):
        self._create_valid_local_matrix()
        process = ProcesoRentaAnual.objects.get()
        process.resumen_anual = {
            **process.resumen_anual,
            'annual_tax_workbooks': {
                **summarize_annual_tax_workbooks(process),
                'by_type': {
                    **summarize_annual_tax_workbooks(process)['by_type'],
                    'RLI': {
                        **summarize_annual_tax_workbooks(process)['by_type']['RLI'],
                        'hash_workbook': 'f' * 64,
                    },
                },
            },
        }
        process.save(update_fields=['resumen_anual', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_tax_workbook_summary_mismatch', issue_codes)

    def test_annual_process_without_approved_tax_year_ruleset_is_blocking(self):
        self._create_valid_local_matrix()
        TaxYearRuleSet.objects.update(estado=EstadoReglaTributariaAnual.DRAFT)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_year_ruleset_missing', issue_codes)
        self.assertEqual(result['sections']['tax_year_rules']['tax_year_ruleset_missing'], 1)

    def test_approved_tax_year_ruleset_without_mapping_is_blocking(self):
        self._create_valid_local_matrix()
        AnnualEnterpriseRegisterSet.objects.all().delete()
        AnnualTaxWorkbookLine.objects.all().delete()
        AnnualTaxWorkbook.objects.all().delete()
        TaxCodeMapping.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_code_mapping_missing', issue_codes)
        self.assertEqual(result['sections']['tax_year_rules']['tax_code_mapping_missing'], 1)

    def test_approved_tax_rules_without_official_source_are_blocking(self):
        self._create_valid_local_matrix()
        TaxYearRuleSet.objects.update(official_source=None)
        TaxCodeMapping.objects.update(official_source=None)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_year_ruleset_official_source_missing', issue_codes)
        self.assertIn('stage6.tax_code_mapping_official_source_missing', issue_codes)
        self.assertEqual(result['sections']['tax_year_rules']['tax_year_ruleset_official_source_missing'], 1)
        self.assertEqual(result['sections']['tax_year_rules']['tax_code_mapping_official_source_missing'], 4)

    def test_invalid_tax_year_rules_are_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        TaxYearRuleSet.objects.update(
            fuente_ref='https://sii.example.test/rule?token=secret',
            hash_normativo='bad-hash',
        )
        TaxCodeMapping.objects.update(
            formula_ref='https://sii.example.test/formula?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_year_ruleset_invalid', issue_codes)
        self.assertIn('stage6.tax_code_mapping_invalid', issue_codes)
        self.assertNotIn('sii.example.test', serialized_result)
        self.assertNotIn('token=secret', serialized_result)

    def test_invalid_annual_tax_official_source_is_blocking_without_sensitive_leak(self):
        self._create_valid_local_matrix()
        AnnualTaxOfficialSource.objects.create(
            anio_tributario=2026,
            source_key='sii-f22-invalid-at2026',
            source_type=TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION,
            title='Certificacion F22 AT2026',
            source_url='https://www.sii.cl/noticias/2026/060226noti02pcr.htm?token=secret',
            source_ref='Bearer source-secret',
            source_hash='bad-hash',
            retrieved_on=date(2026, 6, 14),
            responsible_ref='https://sii.example.test/reviewer?token=secret',
            metadata={'credential': 'secret'},
            estado=EstadoAnnualTaxOfficialSource.APPROVED,
            applies_to=DestinoMapeoTributarioAnual.F22,
            form_code='F22',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        serialized_result = json.dumps(result)

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.official_source_invalid', issue_codes)
        self.assertEqual(result['sections']['annual_tax_official_sources']['official_source_invalid'], 1)
        self.assertEqual(result['sections']['annual_tax_official_sources']['sources_total'], 6)
        self.assertNotIn('token=secret', serialized_result)
        self.assertNotIn('source-secret', serialized_result)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_label_missing', issue_codes)
        self.assertIn('stage6.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_authorized_source_sensitive_trace_refs_are_classified(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='annual-tax-rule-expert-v1',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_kind='snapshot_controlado',
            source_label='https://example.test/stage6?signed_token=secret',
            authorization_ref='Bearer stage6-secret-token',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_label_sensitive', issue_codes)
        self.assertIn('stage6.authorization_ref_sensitive', issue_codes)
        self.assertNotIn('stage6.source_label_missing', issue_codes)
        self.assertNotIn('stage6.authorization_ref_missing', issue_codes)
        self.assertTrue(result['sections']['source_trace_sensitive']['source_label'])
        self.assertTrue(result['sections']['source_trace_sensitive']['authorization_ref'])
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_authorized_source_sensitive_final_refs_are_classified(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            source_kind='snapshot_controlado',
            source_label='stage6-controlled-source-v1',
            authorization_ref='stage6-authorization-v1',
            stage5_evidence_ref='https://example.test/stage5?signed_token=secret',
            stage4_sii_evidence_ref='https://example.test/stage4?signed_token=secret',
            fiscal_rule_ref='https://example.test/fiscal-rule?signed_token=secret',
            certificates_proof_ref='https://example.test/certificates?signed_token=secret',
            responsible_ref='Bearer stage6-responsible-secret',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        expected_sensitive_codes = {
            'stage6.stage5_evidence_ref_sensitive',
            'stage6.stage4_sii_evidence_ref_sensitive',
            'stage6.fiscal_rule_ref_sensitive',
            'stage6.certificates_proof_ref_sensitive',
            'stage6.responsible_ref_sensitive',
        }
        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertTrue(expected_sensitive_codes.issubset(issue_codes))
        self.assertNotIn('stage6.stage5_evidence_ref_missing', issue_codes)
        self.assertNotIn('stage6.stage4_sii_evidence_ref_missing', issue_codes)
        self.assertNotIn('stage6.fiscal_rule_ref_missing', issue_codes)
        self.assertNotIn('stage6.certificates_proof_ref_missing', issue_codes)
        self.assertNotIn('stage6.responsible_ref_missing', issue_codes)
        for key in (
            'stage5_evidence_ref',
            'stage4_sii_evidence_ref',
            'fiscal_rule_ref',
            'certificates_proof_ref',
            'responsible_ref',
        ):
            self.assertTrue(result['sections']['final_evidence_sensitive'][key])
            self.assertFalse(result['sections']['final_evidence'][key])

    def test_process_without_twelve_approved_closes_is_blocking(self):
        self._create_valid_local_matrix()
        CierreMensualContable.objects.filter(mes=12).update(estado=EstadoCierreMensual.PREPARED)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_twelve_closes_missing', issue_codes)

    def test_open_annual_capability_without_readiness_refs_is_blocking(self):
        empresa = self._create_active_empresa(nombre='AnnualCapabilityCo', rut='67676767-6')
        self._activate_fiscal_config(empresa)
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.DDJJ_PREPARACION,
            certificado_ref='cert-stage6',
            ambiente=AmbienteSII.CERTIFICATION,
            estado_gate=EstadoGateSII.OPEN,
        )

        result = collect_stage6_renta_anual_readiness()

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_capability_invalid', {issue['code'] for issue in result['issues']})

    def test_annual_capabilities_process_ddjj_and_f22_require_same_company_fiscal_config(self):
        empresa_con_config = self._create_active_empresa(nombre='FiscalConfiguredStage6Co', rut='65656565-6')
        self._activate_fiscal_config(empresa_con_config)
        empresa_sin_config = self._create_active_empresa(nombre='AnnualNoFiscalCo', rut='75757575-7')
        ddjj_capability = self._open_capability(
            empresa_sin_config,
            CapacidadSII.DDJJ_PREPARACION,
            'ddjj-no-fiscal',
        )
        f22_capability = self._open_capability(
            empresa_sin_config,
            CapacidadSII.F22_PREPARACION,
            'f22-no-fiscal',
        )
        self._create_twelve_approved_closes(empresa_sin_config)
        summary = self._annual_summary()
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa_sin_config,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.APPROVED,
            fecha_preparacion=timezone.now(),
            resumen_anual=summary,
            paquete_ddjj_ref='ddjj-package-stage6-no-fiscal',
            borrador_f22_ref='f22-draft-stage6-no-fiscal',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa_sin_config,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary},
            paquete_ref='ddjj-package-stage6-no-fiscal',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa_sin_config,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2026,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1'},
            borrador_ref='f22-draft-stage6-no-fiscal',
        )
        self._create_tax_support_document(process)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_capability_fiscal_config_missing', issue_codes)
        self.assertIn('stage6.annual_process_fiscal_config_missing', issue_codes)
        self.assertIn('stage6.ddjj_fiscal_config_missing', issue_codes)
        self.assertIn('stage6.f22_fiscal_config_missing', issue_codes)
        self.assertEqual(result['sections']['annual_capabilities']['open_without_active_fiscal_config'], 2)
        self.assertEqual(result['sections']['annual_process']['without_active_fiscal_config'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_without_active_fiscal_config'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_without_active_fiscal_config'], 1)

    def test_process_without_summary_or_annual_documents_is_blocking(self):
        empresa = self._create_active_empresa(nombre='ProcessNoDocsCo', rut='68686868-6')
        self._activate_fiscal_config(empresa)
        self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj-no-docs')
        self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22-no-docs')
        self._create_twelve_approved_closes(empresa)
        ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2026,
            estado=EstadoPreparacionTributaria.PREPARED,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_process_summary_missing', issue_codes)
        self.assertIn('stage6.ddjj_missing_for_process', issue_codes)
        self.assertIn('stage6.f22_missing_for_process', issue_codes)

    def test_annual_payloads_with_wrong_fiscal_year_are_blocking(self):
        self._create_valid_local_matrix()
        wrong_summary = self._annual_summary(fiscal_year=2024)
        ProcesoRentaAnual.objects.update(resumen_anual=wrong_summary)
        DDJJPreparacionAnual.objects.update(
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': wrong_summary}
        )
        F22PreparacionAnual.objects.update(
            resumen_f22={'resumen_anual': wrong_summary, 'regimen_tributario': 'propyme-general-v1'}
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_process_fiscal_year_mismatch', issue_codes)
        self.assertIn('stage6.ddjj_summary_fiscal_year_mismatch', issue_codes)
        self.assertIn('stage6.f22_summary_fiscal_year_mismatch', issue_codes)

    def test_sensitive_annual_payload_keys_are_blocking(self):
        self._create_valid_local_matrix()
        summary = self._annual_summary()
        ProcesoRentaAnual.objects.update(resumen_anual={**summary, 'api_key': None})
        DDJJPreparacionAnual.objects.update(
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary, 'access_token': None}
        )
        F22PreparacionAnual.objects.update(
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1', 'credential': None}
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.annual_process_sensitive_payload', issue_codes)
        self.assertIn('stage6.ddjj_sensitive_payload', issue_codes)
        self.assertIn('stage6.f22_sensitive_payload', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_sensitive_payload'], 1)
        self.assertNotIn('api_key', json.dumps(result))

    def test_ddjj_and_f22_approved_without_refs_or_presented_are_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(paquete_ddjj_ref='', borrador_f22_ref='')
        DDJJPreparacionAnual.objects.update(paquete_ref='')
        F22PreparacionAnual.objects.update(borrador_ref='')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_ref_missing', issue_codes)
        self.assertIn('stage6.process_f22_ref_missing', issue_codes)
        self.assertIn('stage6.ddjj_ref_missing', issue_codes)
        self.assertIn('stage6.f22_ref_missing', issue_codes)

        DDJJPreparacionAnual.objects.update(estado_preparacion=EstadoPreparacionTributaria.PRESENTED, paquete_ref='ddjj-presented')
        F22PreparacionAnual.objects.update(estado_preparacion=EstadoPreparacionTributaria.PRESENTED, borrador_ref='f22-presented')
        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertIn('stage6.ddjj_presented_boundary', issue_codes)
        self.assertIn('stage6.f22_presented_boundary', issue_codes)

    def test_approved_annual_artifacts_without_review_responsible_are_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(responsable_revision_ref='')
        DDJJPreparacionAnual.objects.update(responsable_revision_ref='')
        F22PreparacionAnual.objects.update(responsable_revision_ref='')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_responsible_ref_missing', issue_codes)
        self.assertIn('stage6.ddjj_responsible_ref_missing', issue_codes)
        self.assertIn('stage6.f22_responsible_ref_missing', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_responsible_ref_missing'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_responsible_ref_missing'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_responsible_ref_missing'], 1)

    def test_sensitive_annual_final_refs_are_classified_explicitly(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
            responsable_revision_ref='https://sii.example.test/user?token=secret',
        )
        DDJJPreparacionAnual.objects.update(
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            responsable_revision_ref='https://sii.example.test/user?token=secret',
        )
        F22PreparacionAnual.objects.update(
            borrador_ref='https://sii.example.test/f22?token=secret',
            responsable_revision_ref='https://sii.example.test/user?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.process_ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage6.process_f22_ref_sensitive', issue_codes)
        self.assertIn('stage6.process_responsible_ref_sensitive', issue_codes)
        self.assertIn('stage6.ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage6.f22_ref_sensitive', issue_codes)
        self.assertIn('stage6.ddjj_responsible_ref_sensitive', issue_codes)
        self.assertIn('stage6.f22_responsible_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['annual_process']['process_ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_process']['process_f22_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_process']['process_responsible_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['ddjj_responsible_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_documents']['f22_responsible_ref_sensitive'], 1)
        self.assertNotIn('token=secret', json.dumps(result))

    def test_tax_support_document_must_be_valid_pdf(self):
        self._create_valid_local_matrix()
        DocumentoEmitido.objects.update(storage_ref='local-evidence/stage6/certificado.txt')

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_stage6_renta_anual'])
        self.assertIn('stage6.tax_support_document_invalid', {issue['code'] for issue in result['issues']})

    def test_sensitive_final_refs_and_command_behaviour(self):
        self._create_valid_local_matrix()

        result = collect_stage6_renta_anual_readiness(
            stage5_evidence_ref='stage5-ledger-year-controlled-v1',
            stage4_sii_evidence_ref='stage4-sii-annual-controlled-v1',
            fiscal_rule_ref='https://sii.example/rule',
            certificates_proof_ref='annual-certificates-controlled-v1',
            responsible_ref='stage6-responsibles-v1',
            source_label='stage6-controlled-v1',
            authorization_ref='stage6-authorization-v1',
            source_kind='snapshot_controlado',
        )
        self.assertFalse(result['ready_for_stage6_renta_anual'])
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertIn('stage6.fiscal_rule_ref_sensitive', issue_codes)
        self.assertNotIn('stage6.fiscal_rule_ref_missing', issue_codes)
        self.assertTrue(result['sections']['final_evidence_sensitive']['fiscal_rule_ref'])

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage6_readiness.json'
            call_command('audit_stage6_renta_anual_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage6.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('annual_process', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage6-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage6_renta_anual_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage6_renta_anual_readiness', fail_on_attention=True, stdout=StringIO())
