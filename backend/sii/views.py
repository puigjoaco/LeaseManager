from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import ControlModulePermission
from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference
from core.scope_access import ScopedQuerysetMixin, get_scope_access, scope_queryset_for_access, scope_queryset_for_user
from cobranza.models import PagoMensual
from patrimonio.models import Empresa

from .models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDDJJFormLayout,
    AnnualTaxF22ExportLayout,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxReviewChecklist,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadTributariaSII,
    DTEEmitido,
    F29PreparacionMensual,
    MonthlyTaxFact,
    TaxCodeMapping,
    TaxYearRuleSet,
    is_safe_public_sii_source_url,
)
from .serializers import (
    AnnualEnterpriseRegisterMovementSerializer,
    AnnualEnterpriseRegisterSetSerializer,
    AnnualRealEstateItemSerializer,
    AnnualRealEstateSectionSerializer,
    AnnualTaxArtifactMatrixItemSerializer,
    AnnualTaxArtifactMatrixSerializer,
    AnnualTaxDDJJFormLayoutSerializer,
    AnnualTaxF22ExportLayoutSerializer,
    AnnualTaxDossierSerializer,
    AnnualTaxExportSerializer,
    AnnualGenerateSerializer,
    AnnualTaxOfficialSourceSerializer,
    AnnualTaxReviewChecklistSerializer,
    AnnualStatusSerializer,
    AnnualTaxSourceBundleSerializer,
    AnnualTaxTrialBalanceLineSerializer,
    AnnualTaxTrialBalanceSerializer,
    AnnualTaxWorkbookLineSerializer,
    AnnualTaxWorkbookSerializer,
    CapacidadTributariaSIISerializer,
    DDJJPreparacionAnualSerializer,
    DTEEmitidoSerializer,
    DTEGenerateSerializer,
    DTEStatusSerializer,
    F22PreparacionAnualSerializer,
    F29GenerateSerializer,
    F29PreparacionMensualSerializer,
    F29StatusSerializer,
    MonthlyTaxFactSerializer,
    ProcesoRentaAnualSerializer,
    TaxCodeMappingSerializer,
    TaxYearRuleSetSerializer,
)
from .services import (
    generate_annual_preparation,
    generate_dte_draft,
    generate_f29_draft,
    register_annual_status,
    register_dte_status,
    register_f29_status,
)
from .models import DDJJPreparacionAnual, F22PreparacionAnual, ProcesoRentaAnual


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''
    audit_state_fields = ('estado_gate', 'estado_dte', 'estado_preparacion', 'estado')

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            self._create_audit_event(instance=instance, action='created')

    def perform_update(self, serializer):
        previous_state_field, previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            self._create_audit_event(instance=instance, action='updated')
            current_state_field, current_state = self._extract_state(instance)
            if previous_state != current_state:
                self._create_audit_event(
                    instance=instance,
                    action='state_changed',
                    summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
                    metadata=build_state_change_metadata(
                        previous_field=previous_state_field,
                        previous_state=previous_state,
                        current_field=current_state_field,
                        current_state=current_state,
                    ),
                )

    def _extract_state(self, instance):
        for field in self.audit_state_fields:
            if hasattr(instance, field):
                return field, getattr(instance, field)
        return None, None

    def _create_audit_event(self, *, instance, action, summary='', metadata=None):
        create_audit_event(
            event_type=f'sii.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            metadata=metadata,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


def build_state_change_metadata(*, previous_field, previous_state, current_field, current_state, extra=None):
    metadata = {
        'campo_estado': current_field or previous_field,
        'estado_anterior': previous_state,
        'estado_nuevo': current_state,
    }
    if extra:
        metadata.update(extra)
    return metadata


class SiiSnapshotView(APIView):
    permission_classes = [ControlModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)
        empresas = scope_queryset_for_access(
            Empresa.objects.order_by('razon_social', 'id'),
            access,
            company_paths=('id',),
        )
        pagos = scope_queryset_for_access(
            PagoMensual.objects.select_related('contrato').prefetch_related('distribuciones_cobro').order_by('-anio', '-mes', '-id'),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        capacidades = scope_queryset_for_access(
            CapacidadTributariaSII.objects.select_related('empresa').order_by('empresa_id', 'capacidad_key', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        dtes = scope_queryset_for_access(
            DTEEmitido.objects.select_related(
                'empresa',
                'capacidad_tributaria',
                'contrato',
                'pago_mensual',
                'distribucion_cobro_mensual',
                'arrendatario',
            ).order_by('-fecha_emision', '-id'),
            access,
            company_paths=('empresa_id',),
        )
        f29s = scope_queryset_for_access(
            F29PreparacionMensual.objects.select_related('empresa', 'capacidad_tributaria', 'cierre_mensual').order_by('-anio', '-mes', '-id'),
            access,
            company_paths=('empresa_id',),
        )
        procesos = scope_queryset_for_access(
            ProcesoRentaAnual.objects.select_related('empresa').order_by('-anio_tributario', '-id'),
            access,
            company_paths=('empresa_id',),
        )
        ddjjs = scope_queryset_for_access(
            DDJJPreparacionAnual.objects.select_related('empresa', 'capacidad_tributaria', 'proceso_renta_anual').order_by('-anio_tributario', '-id'),
            access,
            company_paths=('empresa_id',),
        )
        f22s = scope_queryset_for_access(
            F22PreparacionAnual.objects.select_related('empresa', 'capacidad_tributaria', 'proceso_renta_anual').order_by('-anio_tributario', '-id'),
            access,
            company_paths=('empresa_id',),
        )
        source_bundles = scope_queryset_for_access(
            AnnualTaxSourceBundle.objects.select_related('empresa').order_by('-anio_tributario', 'empresa_id', 'source_kind', 'source_label'),
            access,
            company_paths=('empresa_id',),
        )
        official_sources = AnnualTaxOfficialSource.objects.order_by('-anio_tributario', 'source_type', 'source_key')
        annual_tax_ddjj_layouts = AnnualTaxDDJJFormLayout.objects.select_related(
            'official_media_source',
            'official_form_source',
            'official_software_source',
        ).order_by('-anio_tributario', 'form_code')
        annual_tax_f22_export_layouts = AnnualTaxF22ExportLayout.objects.select_related(
            'official_certification_source',
            'official_instructions_source',
        ).order_by('-anio_tributario', 'form_code')
        monthly_tax_facts = scope_queryset_for_access(
            MonthlyTaxFact.objects.select_related(
                'empresa',
                'cierre_mensual',
                'f29_preparacion',
                'liquidacion_mensual',
            ).order_by('-anio', 'empresa_id', 'mes'),
            access,
            company_paths=('empresa_id',),
        )
        annual_tax_trial_balances = scope_queryset_for_access(
            AnnualTaxTrialBalance.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'source_bundle',
                'rule_set',
                'official_source',
                'source_balance',
            ).order_by('-anio_tributario', 'empresa_id', 'periodo_cierre', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        annual_tax_trial_balance_lines = scope_queryset_for_access(
            AnnualTaxTrialBalanceLine.objects.select_related(
                'trial_balance',
                'trial_balance__empresa',
                'cuenta_contable',
            ).order_by('trial_balance_id', 'codigo_cuenta', 'id'),
            access,
            company_paths=('trial_balance__empresa_id',),
        )
        annual_tax_workbooks = scope_queryset_for_access(
            AnnualTaxWorkbook.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'source_bundle',
                'rule_set',
            ).order_by('-anio_tributario', 'empresa_id', 'tipo'),
            access,
            company_paths=('empresa_id',),
        )
        annual_tax_workbook_lines = scope_queryset_for_access(
            AnnualTaxWorkbookLine.objects.select_related(
                'workbook',
                'workbook__empresa',
                'mapping',
            ).order_by('workbook_id', 'codigo_interno', 'codigo_destino'),
            access,
            company_paths=('workbook__empresa_id',),
        )
        annual_enterprise_registers = scope_queryset_for_access(
            AnnualEnterpriseRegisterSet.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'source_bundle',
                'rule_set',
            ).order_by('-anio_tributario', 'empresa_id', 'tipo_registro'),
            access,
            company_paths=('empresa_id',),
        )
        annual_enterprise_register_movements = scope_queryset_for_access(
            AnnualEnterpriseRegisterMovement.objects.select_related(
                'register_set',
                'register_set__empresa',
                'source_workbook_line',
            ).order_by('register_set_id', 'codigo_interno', 'origen'),
            access,
            company_paths=('register_set__empresa_id',),
        )
        annual_real_estate_sections = scope_queryset_for_access(
            AnnualRealEstateSection.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'source_bundle',
                'rule_set',
                'official_contribution_source',
            ).order_by('-anio_tributario', 'empresa_id', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        annual_real_estate_items = scope_queryset_for_access(
            AnnualRealEstateItem.objects.select_related(
                'section',
                'section__empresa',
                'propiedad',
            ).order_by('section_id', 'codigo_propiedad_snapshot', 'id'),
            access,
            company_paths=('section__empresa_id',),
        )
        annual_tax_artifact_matrices = scope_queryset_for_access(
            AnnualTaxArtifactMatrix.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'source_bundle',
                'rule_set',
            ).order_by('-anio_tributario', 'empresa_id', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        annual_tax_artifact_matrix_items = scope_queryset_for_access(
            AnnualTaxArtifactMatrixItem.objects.select_related(
                'matrix',
                'matrix__empresa',
            ).order_by('matrix_id', 'target_kind', 'target_code', 'source_kind', 'source_model', 'source_object_id'),
            access,
            company_paths=('matrix__empresa_id',),
        )
        annual_tax_dossiers = scope_queryset_for_access(
            AnnualTaxDossier.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'source_bundle',
                'rule_set',
                'artifact_matrix',
            ).order_by('-anio_tributario', 'empresa_id', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        annual_tax_exports = scope_queryset_for_access(
            AnnualTaxExport.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'dossier',
                'source_bundle',
                'rule_set',
                'artifact_matrix',
            ).order_by('-anio_tributario', 'empresa_id', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        annual_tax_review_checklists = scope_queryset_for_access(
            AnnualTaxReviewChecklist.objects.select_related(
                'empresa',
                'proceso_renta_anual',
                'dossier',
                'annual_export',
                'source_bundle',
                'rule_set',
                'artifact_matrix',
            ).order_by('-anio_tributario', 'empresa_id', 'id'),
            access,
            company_paths=('empresa_id',),
        )
        tax_year_rule_sets = TaxYearRuleSet.objects.select_related('regimen_tributario', 'official_source').order_by(
            '-anio_tributario',
            'regimen_tributario_id',
            'version',
        )
        tax_code_mappings = TaxCodeMapping.objects.select_related(
            'rule_set',
            'rule_set__regimen_tributario',
            'official_source',
        ).order_by('rule_set_id', 'destino', 'codigo_interno', 'codigo_destino')

        return Response(
            {
                'empresas': [
                    {
                        'id': item.id,
                        'razon_social': item.razon_social,
                    }
                    for item in empresas
                ],
                'pagos': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'mes': item.mes,
                        'anio': item.anio,
                        'estado_pago': item.estado_pago,
                        'tiene_distribucion_facturable': any(distribution.requiere_dte for distribution in item.distribuciones_cobro.all()),
                    }
                    for item in pagos
                ],
                'capacidades': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'capacidad_key': item.capacidad_key,
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'prueba_flujo_ref': redact_sensitive_reference(item.prueba_flujo_ref),
                        'autorizacion_ambiente_ref': redact_sensitive_reference(item.autorizacion_ambiente_ref),
                        'regla_fiscal_ref': redact_sensitive_reference(item.regla_fiscal_ref),
                        'ambiente': item.ambiente,
                        'estado_gate': item.estado_gate,
                    }
                    for item in capacidades
                ],
                'dtes': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'contrato': item.contrato_id,
                        'pago_mensual': item.pago_mensual_id,
                        'monto_neto_clp': item.monto_neto_clp,
                        'estado_dte': item.estado_dte,
                        'sii_track_id': redact_sensitive_reference(item.sii_track_id),
                        'observaciones': redact_sensitive_reference(item.observaciones),
                    }
                    for item in dtes
                ],
                'f29s': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'capacidad_tributaria': item.capacidad_tributaria_id,
                        'anio': item.anio,
                        'mes': item.mes,
                        'estado_preparacion': item.estado_preparacion,
                        'borrador_ref': redact_sensitive_reference(item.borrador_ref),
                        'responsable_revision_ref': redact_sensitive_reference(item.responsable_revision_ref),
                        'observaciones': redact_sensitive_reference(item.observaciones),
                    }
                    for item in f29s
                ],
                'procesos_anuales': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'anio_tributario': item.anio_tributario,
                        'estado': item.estado,
                        'source_bundle': item.source_bundle_id,
                        'fecha_preparacion': item.fecha_preparacion,
                        'responsable_revision_ref': redact_sensitive_reference(item.responsable_revision_ref),
                    }
                    for item in procesos
                ],
                'annual_tax_source_bundles': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'source_kind': item.source_kind,
                        'source_label': redact_sensitive_reference(item.source_label),
                        'authorization_ref': redact_sensitive_reference(item.authorization_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'hash_fuentes': item.hash_fuentes,
                        'resumen_fuentes': redact_sensitive_payload(item.resumen_fuentes),
                        'estado': item.estado,
                    }
                    for item in source_bundles
                ],
                'annual_tax_official_sources': [
                    {
                        'id': item.id,
                        'anio_tributario': item.anio_tributario,
                        'source_key': item.source_key,
                        'source_type': item.source_type,
                        'title': item.title,
                        'source_url': (
                            item.source_url
                            if is_safe_public_sii_source_url(item.source_url)
                            else redact_sensitive_reference(item.source_url)
                        ),
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'source_hash': item.source_hash,
                        'retrieved_on': item.retrieved_on.isoformat() if item.retrieved_on else None,
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'estado': item.estado,
                        'applies_to': item.applies_to,
                        'form_code': item.form_code,
                        'regime_code': item.regime_code,
                        'scope_note': redact_sensitive_reference(item.scope_note),
                        'metadata': redact_sensitive_payload(item.metadata),
                    }
                    for item in official_sources
                ],
                'annual_tax_ddjj_layouts': [
                    {
                        'id': item.id,
                        'anio_tributario': item.anio_tributario,
                        'form_code': item.form_code,
                        'title': item.title,
                        'periodicidad': item.periodicidad,
                        'allows_electronic_form': item.allows_electronic_form,
                        'allows_file_importer': item.allows_file_importer,
                        'allows_file_upload': item.allows_file_upload,
                        'allows_commercial_software': item.allows_commercial_software,
                        'allows_assistant': item.allows_assistant,
                        'medio_preferente': item.medio_preferente,
                        'due_date_label': item.due_date_label,
                        'certificate_code': item.certificate_code,
                        'certificate_due_label': item.certificate_due_label,
                        'resolution_ref': redact_sensitive_reference(item.resolution_ref),
                        'declaration_status': item.declaration_status,
                        'layout_ref': redact_sensitive_reference(item.layout_ref),
                        'instructions_ref': redact_sensitive_reference(item.instructions_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'official_media_source': item.official_media_source_id,
                        'official_form_source': item.official_form_source_id,
                        'official_software_source': item.official_software_source_id,
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_layout': item.hash_layout,
                        'estado': item.estado,
                    }
                    for item in annual_tax_ddjj_layouts
                ],
                'annual_tax_f22_export_layouts': [
                    {
                        'id': item.id,
                        'anio_tributario': item.anio_tributario,
                        'form_code': item.form_code,
                        'title': item.title,
                        'allows_local_preview': item.allows_local_preview,
                        'allows_certified_file': item.allows_certified_file,
                        'allows_supervised_portal': item.allows_supervised_portal,
                        'medio_preferente': item.medio_preferente,
                        'certification_ref': redact_sensitive_reference(item.certification_ref),
                        'format_ref': redact_sensitive_reference(item.format_ref),
                        'instructions_ref': redact_sensitive_reference(item.instructions_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'official_certification_source': item.official_certification_source_id,
                        'official_instructions_source': item.official_instructions_source_id,
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_layout': item.hash_layout,
                        'estado': item.estado,
                    }
                    for item in annual_tax_f22_export_layouts
                ],
                'monthly_tax_facts': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'anio': item.anio,
                        'mes': item.mes,
                        'cierre_mensual': item.cierre_mensual_id,
                        'f29_preparacion': item.f29_preparacion_id,
                        'liquidacion_mensual': item.liquidacion_mensual_id,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'resumen_hecho': redact_sensitive_payload(item.resumen_hecho),
                        'hash_hecho': item.hash_hecho,
                        'estado': item.estado,
                    }
                    for item in monthly_tax_facts
                ],
                'annual_tax_trial_balances': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'official_source': item.official_source_id,
                        'source_balance': item.source_balance_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'periodo_cierre': item.periodo_cierre,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'lines_total': item.lines_total,
                        'warnings_total': item.warnings_total,
                        'resumen_balance': redact_sensitive_payload(item.resumen_balance),
                        'hash_balance': item.hash_balance,
                        'estado': item.estado,
                    }
                    for item in annual_tax_trial_balances
                ],
                'annual_tax_trial_balance_lines': [
                    {
                        'id': item.id,
                        'trial_balance': item.trial_balance_id,
                        'cuenta_contable': item.cuenta_contable_id,
                        'codigo_cuenta': item.codigo_cuenta,
                        'nombre_cuenta': item.nombre_cuenta,
                        'clasificador_dj1847': item.clasificador_dj1847,
                        'sumas_debe_clp': item.sumas_debe_clp,
                        'sumas_haber_clp': item.sumas_haber_clp,
                        'saldo_deudor_clp': item.saldo_deudor_clp,
                        'saldo_acreedor_clp': item.saldo_acreedor_clp,
                        'inventario_activo_clp': item.inventario_activo_clp,
                        'inventario_pasivo_clp': item.inventario_pasivo_clp,
                        'resultado_perdida_clp': item.resultado_perdida_clp,
                        'resultado_ganancia_clp': item.resultado_ganancia_clp,
                        'formula_ref': redact_sensitive_reference(item.formula_ref),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_linea': item.hash_linea,
                        'estado': item.estado,
                    }
                    for item in annual_tax_trial_balance_lines
                ],
                'annual_tax_workbooks': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'tipo': item.tipo,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'resumen_workbook': redact_sensitive_payload(item.resumen_workbook),
                        'hash_workbook': item.hash_workbook,
                        'estado': item.estado,
                    }
                    for item in annual_tax_workbooks
                ],
                'annual_tax_workbook_lines': [
                    {
                        'id': item.id,
                        'workbook': item.workbook_id,
                        'mapping': item.mapping_id,
                        'codigo_interno': item.codigo_interno,
                        'codigo_destino': item.codigo_destino,
                        'origen': item.origen,
                        'signo': item.signo,
                        'monto_clp': item.monto_clp,
                        'formula_ref': redact_sensitive_reference(item.formula_ref),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'warning_review_ref': redact_sensitive_reference(item.warning_review_ref),
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_linea': item.hash_linea,
                        'estado': item.estado,
                    }
                    for item in annual_tax_workbook_lines
                ],
                'annual_enterprise_registers': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'tipo_registro': item.tipo_registro,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'saldo_inicial_clp': item.saldo_inicial_clp,
                        'movimientos_total_clp': item.movimientos_total_clp,
                        'saldo_final_clp': item.saldo_final_clp,
                        'resumen_registro': redact_sensitive_payload(item.resumen_registro),
                        'hash_registro': item.hash_registro,
                        'estado': item.estado,
                    }
                    for item in annual_enterprise_registers
                ],
                'annual_enterprise_register_movements': [
                    {
                        'id': item.id,
                        'register_set': item.register_set_id,
                        'source_workbook_line': item.source_workbook_line_id,
                        'codigo_interno': item.codigo_interno,
                        'origen': item.origen,
                        'signo': item.signo,
                        'monto_clp': item.monto_clp,
                        'formula_ref': redact_sensitive_reference(item.formula_ref),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'warning_review_ref': redact_sensitive_reference(item.warning_review_ref),
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_movimiento': item.hash_movimiento,
                        'estado': item.estado,
                    }
                    for item in annual_enterprise_register_movements
                ],
                'annual_real_estate_sections': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'official_contribution_source': item.official_contribution_source_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'propiedades_total': item.propiedades_total,
                        'arriendo_devengado_total_clp': item.arriendo_devengado_total_clp,
                        'arriendo_conciliado_total_clp': item.arriendo_conciliado_total_clp,
                        'arriendo_facturable_total_clp': item.arriendo_facturable_total_clp,
                        'contribuciones_total_clp': item.contribuciones_total_clp,
                        'resumen_seccion': redact_sensitive_payload(item.resumen_seccion),
                        'hash_seccion': item.hash_seccion,
                        'estado': item.estado,
                    }
                    for item in annual_real_estate_sections
                ],
                'annual_real_estate_items': [
                    {
                        'id': item.id,
                        'section': item.section_id,
                        'propiedad': item.propiedad_id,
                        'codigo_propiedad_snapshot': item.codigo_propiedad_snapshot,
                        'rol_avaluo_snapshot': redact_sensitive_reference(item.rol_avaluo_snapshot),
                        'direccion_snapshot': redact_sensitive_reference(item.direccion_snapshot),
                        'comuna_snapshot': item.comuna_snapshot,
                        'region_snapshot': item.region_snapshot,
                        'tipo_inmueble_snapshot': item.tipo_inmueble_snapshot,
                        'owner_tipo_snapshot': item.owner_tipo_snapshot,
                        'owner_id_snapshot': item.owner_id_snapshot,
                        'arriendo_devengado_clp': item.arriendo_devengado_clp,
                        'arriendo_conciliado_clp': item.arriendo_conciliado_clp,
                        'arriendo_facturable_clp': item.arriendo_facturable_clp,
                        'contribuciones_clp': item.contribuciones_clp,
                        'formula_ref': redact_sensitive_reference(item.formula_ref),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_item': item.hash_item,
                        'estado': item.estado,
                    }
                    for item in annual_real_estate_items
                ],
                'annual_tax_artifact_matrices': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'items_total': item.items_total,
                        'ddjj_items_total': item.ddjj_items_total,
                        'f22_items_total': item.f22_items_total,
                        'resumen_matriz': redact_sensitive_payload(item.resumen_matriz),
                        'hash_matriz': item.hash_matriz,
                        'estado': item.estado,
                    }
                    for item in annual_tax_artifact_matrices
                ],
                'annual_tax_artifact_matrix_items': [
                    {
                        'id': item.id,
                        'matrix': item.matrix_id,
                        'target_kind': item.target_kind,
                        'target_code': item.target_code,
                        'medio_sii': item.medio_sii,
                        'source_kind': item.source_kind,
                        'source_model': item.source_model,
                        'source_object_id': item.source_object_id,
                        'source_hash': item.source_hash,
                        'review_state': item.review_state,
                        'formula_ref': redact_sensitive_reference(item.formula_ref),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'warning_review_ref': redact_sensitive_reference(item.warning_review_ref),
                        'warnings': redact_sensitive_payload(item.warnings),
                        'source_payload': redact_sensitive_payload(item.source_payload),
                        'hash_item': item.hash_item,
                        'estado': item.estado,
                    }
                    for item in annual_tax_artifact_matrix_items
                ],
                'annual_tax_dossiers': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'artifact_matrix': item.artifact_matrix_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'dossier_ref': redact_sensitive_reference(item.dossier_ref),
                        'review_state': item.review_state,
                        'monthly_facts_total': item.monthly_facts_total,
                        'workbooks_total': item.workbooks_total,
                        'enterprise_registers_total': item.enterprise_registers_total,
                        'real_estate_sections_total': item.real_estate_sections_total,
                        'artifact_matrix_items_total': item.artifact_matrix_items_total,
                        'warnings_total': item.warnings_total,
                        'resumen_dossier': redact_sensitive_payload(item.resumen_dossier),
                        'hash_dossier': item.hash_dossier,
                        'estado': item.estado,
                    }
                    for item in annual_tax_dossiers
                ],
                'annual_tax_exports': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'dossier': item.dossier_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'artifact_matrix': item.artifact_matrix_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'export_kind': item.export_kind,
                        'source_ref': redact_sensitive_reference(item.source_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'export_ref': redact_sensitive_reference(item.export_ref),
                        'review_state': item.review_state,
                        'target_items_total': item.target_items_total,
                        'ddjj_items_total': item.ddjj_items_total,
                        'f22_items_total': item.f22_items_total,
                        'warnings_total': item.warnings_total,
                        'official_format': item.official_format,
                        'sii_submission': item.sii_submission,
                        'final_tax_calculation': item.final_tax_calculation,
                        'export_payload': redact_sensitive_payload(item.export_payload),
                        'hash_export': item.hash_export,
                        'estado': item.estado,
                    }
                    for item in annual_tax_exports
                ],
                'annual_tax_review_checklists': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'proceso_renta_anual': item.proceso_renta_anual_id,
                        'dossier': item.dossier_id,
                        'annual_export': item.annual_export_id,
                        'source_bundle': item.source_bundle_id,
                        'rule_set': item.rule_set_id,
                        'artifact_matrix': item.artifact_matrix_id,
                        'anio_tributario': item.anio_tributario,
                        'anio_comercial': item.anio_comercial,
                        'checklist_ref': redact_sensitive_reference(item.checklist_ref),
                        'responsible_ref': redact_sensitive_reference(item.responsible_ref),
                        'evidence_ref': redact_sensitive_reference(item.evidence_ref),
                        'items_total': item.items_total,
                        'completed_items_total': item.completed_items_total,
                        'blockers_total': item.blockers_total,
                        'warnings_total': item.warnings_total,
                        'review_payload': redact_sensitive_payload(item.review_payload),
                        'hash_checklist': item.hash_checklist,
                        'estado': item.estado,
                    }
                    for item in annual_tax_review_checklists
                ],
                'ddjjs': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'anio_tributario': item.anio_tributario,
                        'estado_preparacion': item.estado_preparacion,
                        'paquete_ref': redact_sensitive_reference(item.paquete_ref),
                        'responsable_revision_ref': redact_sensitive_reference(item.responsable_revision_ref),
                        'observaciones': redact_sensitive_reference(item.observaciones),
                    }
                    for item in ddjjs
                ],
                'f22s': [
                    {
                        'id': item.id,
                        'empresa': item.empresa_id,
                        'anio_tributario': item.anio_tributario,
                        'estado_preparacion': item.estado_preparacion,
                        'borrador_ref': redact_sensitive_reference(item.borrador_ref),
                        'responsable_revision_ref': redact_sensitive_reference(item.responsable_revision_ref),
                        'observaciones': redact_sensitive_reference(item.observaciones),
                    }
                    for item in f22s
                ],
                'tax_year_rule_sets': [
                    {
                        'id': item.id,
                        'anio_tributario': item.anio_tributario,
                        'regimen_tributario': item.regimen_tributario_id,
                        'regimen_codigo': item.regimen_tributario.codigo_regimen,
                        'version': item.version,
                        'estado': item.estado,
                        'fuente_ref': redact_sensitive_reference(item.fuente_ref),
                        'hash_normativo': item.hash_normativo,
                        'responsable_aprobacion_ref': redact_sensitive_reference(item.responsable_aprobacion_ref),
                        'official_source': item.official_source_id,
                        'official_source_key': item.official_source.source_key if item.official_source_id else '',
                        'metadata': redact_sensitive_payload(item.metadata),
                    }
                    for item in tax_year_rule_sets
                ],
                'tax_code_mappings': [
                    {
                        'id': item.id,
                        'rule_set': item.rule_set_id,
                        'destino': item.destino,
                        'codigo_interno': item.codigo_interno,
                        'codigo_destino': item.codigo_destino,
                        'formula_ref': redact_sensitive_reference(item.formula_ref),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                        'official_source': item.official_source_id,
                        'official_source_key': item.official_source.source_key if item.official_source_id else '',
                        'estado': item.estado,
                        'metadata': redact_sensitive_payload(item.metadata),
                    }
                    for item in tax_code_mappings
                ],
            }
        )


class CapacidadTributariaSIIListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CapacidadTributariaSIISerializer
    queryset = CapacidadTributariaSII.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'capacidad_sii'
    audit_entity_label = 'capacidad SII'


class CapacidadTributariaSIIDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CapacidadTributariaSIISerializer
    queryset = CapacidadTributariaSII.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'capacidad_sii'
    audit_entity_label = 'capacidad SII'


class TaxYearRuleSetListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = TaxYearRuleSetSerializer
    queryset = TaxYearRuleSet.objects.select_related('regimen_tributario', 'official_source').all()
    audit_entity_type = 'tax_year_ruleset'
    audit_entity_label = 'TaxYearRuleSet'


class TaxYearRuleSetDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = TaxYearRuleSetSerializer
    queryset = TaxYearRuleSet.objects.select_related('regimen_tributario', 'official_source').all()
    audit_entity_type = 'tax_year_ruleset'
    audit_entity_label = 'TaxYearRuleSet'


class TaxCodeMappingListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = TaxCodeMappingSerializer
    queryset = TaxCodeMapping.objects.select_related('rule_set', 'rule_set__regimen_tributario', 'official_source').all()
    audit_entity_type = 'tax_code_mapping'
    audit_entity_label = 'TaxCodeMapping'


class TaxCodeMappingDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = TaxCodeMappingSerializer
    queryset = TaxCodeMapping.objects.select_related('rule_set', 'rule_set__regimen_tributario', 'official_source').all()
    audit_entity_type = 'tax_code_mapping'
    audit_entity_label = 'TaxCodeMapping'


class AnnualTaxOfficialSourceListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxOfficialSourceSerializer
    queryset = AnnualTaxOfficialSource.objects.all()
    audit_entity_type = 'annual_tax_official_source'
    audit_entity_label = 'AnnualTaxOfficialSource'


class AnnualTaxOfficialSourceDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxOfficialSourceSerializer
    queryset = AnnualTaxOfficialSource.objects.all()
    audit_entity_type = 'annual_tax_official_source'
    audit_entity_label = 'AnnualTaxOfficialSource'


class AnnualTaxDDJJFormLayoutListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxDDJJFormLayoutSerializer
    queryset = AnnualTaxDDJJFormLayout.objects.select_related(
        'official_media_source',
        'official_form_source',
        'official_software_source',
    ).all()
    audit_entity_type = 'annual_tax_ddjj_form_layout'
    audit_entity_label = 'AnnualTaxDDJJFormLayout'


class AnnualTaxDDJJFormLayoutDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxDDJJFormLayoutSerializer
    queryset = AnnualTaxDDJJFormLayout.objects.select_related(
        'official_media_source',
        'official_form_source',
        'official_software_source',
    ).all()
    audit_entity_type = 'annual_tax_ddjj_form_layout'
    audit_entity_label = 'AnnualTaxDDJJFormLayout'


class AnnualTaxF22ExportLayoutListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxF22ExportLayoutSerializer
    queryset = AnnualTaxF22ExportLayout.objects.select_related(
        'official_certification_source',
        'official_instructions_source',
    ).all()
    audit_entity_type = 'annual_tax_f22_export_layout'
    audit_entity_label = 'AnnualTaxF22ExportLayout'


class AnnualTaxF22ExportLayoutDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxF22ExportLayoutSerializer
    queryset = AnnualTaxF22ExportLayout.objects.select_related(
        'official_certification_source',
        'official_instructions_source',
    ).all()
    audit_entity_type = 'annual_tax_f22_export_layout'
    audit_entity_label = 'AnnualTaxF22ExportLayout'


class AnnualTaxSourceBundleListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxSourceBundleSerializer
    queryset = AnnualTaxSourceBundle.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'annual_tax_source_bundle'
    audit_entity_label = 'AnnualTaxSourceBundle'


class AnnualTaxSourceBundleDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxSourceBundleSerializer
    queryset = AnnualTaxSourceBundle.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'annual_tax_source_bundle'
    audit_entity_label = 'AnnualTaxSourceBundle'


class MonthlyTaxFactListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = MonthlyTaxFactSerializer
    queryset = MonthlyTaxFact.objects.select_related(
        'empresa',
        'cierre_mensual',
        'f29_preparacion',
        'liquidacion_mensual',
    ).all()
    company_scope_paths = ('empresa_id',)


class MonthlyTaxFactDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = MonthlyTaxFactSerializer
    queryset = MonthlyTaxFact.objects.select_related(
        'empresa',
        'cierre_mensual',
        'f29_preparacion',
        'liquidacion_mensual',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxTrialBalanceListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxTrialBalanceSerializer
    queryset = AnnualTaxTrialBalance.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'official_source',
        'source_balance',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxTrialBalanceDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxTrialBalanceSerializer
    queryset = AnnualTaxTrialBalance.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'official_source',
        'source_balance',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxTrialBalanceLineListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxTrialBalanceLineSerializer
    queryset = AnnualTaxTrialBalanceLine.objects.select_related(
        'trial_balance',
        'trial_balance__empresa',
        'cuenta_contable',
    ).all()
    company_scope_paths = ('trial_balance__empresa_id',)


class AnnualTaxTrialBalanceLineDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxTrialBalanceLineSerializer
    queryset = AnnualTaxTrialBalanceLine.objects.select_related(
        'trial_balance',
        'trial_balance__empresa',
        'cuenta_contable',
    ).all()
    company_scope_paths = ('trial_balance__empresa_id',)


class AnnualTaxWorkbookListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxWorkbookSerializer
    queryset = AnnualTaxWorkbook.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxWorkbookDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxWorkbookSerializer
    queryset = AnnualTaxWorkbook.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxWorkbookLineListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxWorkbookLineSerializer
    queryset = AnnualTaxWorkbookLine.objects.select_related(
        'workbook',
        'workbook__empresa',
        'mapping',
    ).all()
    company_scope_paths = ('workbook__empresa_id',)


class AnnualTaxWorkbookLineDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxWorkbookLineSerializer
    queryset = AnnualTaxWorkbookLine.objects.select_related(
        'workbook',
        'workbook__empresa',
        'mapping',
    ).all()
    company_scope_paths = ('workbook__empresa_id',)


class AnnualEnterpriseRegisterSetListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualEnterpriseRegisterSetSerializer
    queryset = AnnualEnterpriseRegisterSet.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualEnterpriseRegisterSetDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualEnterpriseRegisterSetSerializer
    queryset = AnnualEnterpriseRegisterSet.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualEnterpriseRegisterMovementListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualEnterpriseRegisterMovementSerializer
    queryset = AnnualEnterpriseRegisterMovement.objects.select_related(
        'register_set',
        'register_set__empresa',
        'source_workbook_line',
    ).all()
    company_scope_paths = ('register_set__empresa_id',)


class AnnualEnterpriseRegisterMovementDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualEnterpriseRegisterMovementSerializer
    queryset = AnnualEnterpriseRegisterMovement.objects.select_related(
        'register_set',
        'register_set__empresa',
        'source_workbook_line',
    ).all()
    company_scope_paths = ('register_set__empresa_id',)


class AnnualRealEstateSectionListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualRealEstateSectionSerializer
    queryset = AnnualRealEstateSection.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'official_contribution_source',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualRealEstateSectionDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualRealEstateSectionSerializer
    queryset = AnnualRealEstateSection.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'official_contribution_source',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualRealEstateItemListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualRealEstateItemSerializer
    queryset = AnnualRealEstateItem.objects.select_related(
        'section',
        'section__empresa',
        'propiedad',
    ).all()
    company_scope_paths = ('section__empresa_id',)


class AnnualRealEstateItemDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualRealEstateItemSerializer
    queryset = AnnualRealEstateItem.objects.select_related(
        'section',
        'section__empresa',
        'propiedad',
    ).all()
    company_scope_paths = ('section__empresa_id',)


class AnnualTaxArtifactMatrixListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxArtifactMatrixSerializer
    queryset = AnnualTaxArtifactMatrix.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxArtifactMatrixDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxArtifactMatrixSerializer
    queryset = AnnualTaxArtifactMatrix.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxArtifactMatrixItemListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxArtifactMatrixItemSerializer
    queryset = AnnualTaxArtifactMatrixItem.objects.select_related(
        'matrix',
        'matrix__empresa',
    ).all()
    company_scope_paths = ('matrix__empresa_id',)


class AnnualTaxArtifactMatrixItemDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxArtifactMatrixItemSerializer
    queryset = AnnualTaxArtifactMatrixItem.objects.select_related(
        'matrix',
        'matrix__empresa',
    ).all()
    company_scope_paths = ('matrix__empresa_id',)


class AnnualTaxDossierListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxDossierSerializer
    queryset = AnnualTaxDossier.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxDossierDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxDossierSerializer
    queryset = AnnualTaxDossier.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxExportListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxExportSerializer
    queryset = AnnualTaxExport.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'dossier',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
        'official_format_source',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxExportDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxExportSerializer
    queryset = AnnualTaxExport.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'dossier',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
        'official_format_source',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxReviewChecklistListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxReviewChecklistSerializer
    queryset = AnnualTaxReviewChecklist.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'dossier',
        'annual_export',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
    ).all()
    company_scope_paths = ('empresa_id',)


class AnnualTaxReviewChecklistDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AnnualTaxReviewChecklistSerializer
    queryset = AnnualTaxReviewChecklist.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'dossier',
        'annual_export',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
    ).all()
    company_scope_paths = ('empresa_id',)


class DTEEmitidoListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = DTEEmitidoSerializer
    queryset = DTEEmitido.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'contrato',
        'pago_mensual',
        'distribucion_cobro_mensual',
        'arrendatario',
    ).all()
    company_scope_paths = ('empresa_id',)


class DTEEmitidoDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = DTEEmitidoSerializer
    queryset = DTEEmitido.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'contrato',
        'pago_mensual',
        'distribucion_cobro_mensual',
        'arrendatario',
    ).all()
    company_scope_paths = ('empresa_id',)


class DTEGenerateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = DTEGenerateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                dte, created = generate_dte_draft(
                    serializer.validated_data['pago_mensual'],
                    tipo_dte=serializer.validated_data['tipo_dte'],
                )
                create_audit_event(
                    event_type='sii.dte_emitido.draft_generated',
                    entity_type='dte_emitido',
                    entity_id=str(dte.pk),
                    summary='Borrador DTE generado',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'created': created},
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(DTEEmitidoSerializer(dte).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DTEStatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        dte = generics.get_object_or_404(
            scope_queryset_for_user(
                DTEEmitido.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        serializer = DTEStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_state = dte.estado_dte
        try:
            with transaction.atomic():
                dte = register_dte_status(dte, **serializer.validated_data)
                create_audit_event(
                    event_type='sii.dte_emitido.status_updated',
                    entity_type='dte_emitido',
                    entity_id=str(dte.pk),
                    summary='Estado DTE actualizado manualmente',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata=build_state_change_metadata(
                        previous_field='estado_dte',
                        previous_state=previous_state,
                        current_field='estado_dte',
                        current_state=dte.estado_dte,
                        extra={'sii_track_id': redact_sensitive_reference(dte.sii_track_id)},
                    ),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DTEEmitidoSerializer(dte).data, status=status.HTTP_200_OK)


class F29PreparacionListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = F29PreparacionMensualSerializer
    queryset = F29PreparacionMensual.objects.select_related('empresa', 'capacidad_tributaria', 'cierre_mensual').all()
    company_scope_paths = ('empresa_id',)


class F29PreparacionDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = F29PreparacionMensualSerializer
    queryset = F29PreparacionMensual.objects.select_related('empresa', 'capacidad_tributaria', 'cierre_mensual').all()
    company_scope_paths = ('empresa_id',)


class F29GenerateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = F29GenerateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                draft, created = generate_f29_draft(
                    serializer.validated_data['empresa'],
                    serializer.validated_data['anio'],
                    serializer.validated_data['mes'],
                )
                create_audit_event(
                    event_type='sii.f29_preparacion.generated',
                    entity_type='f29_preparacion',
                    entity_id=str(draft.pk),
                    summary='Borrador F29 generado',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'created': created},
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            F29PreparacionMensualSerializer(draft).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class F29StatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        draft = generics.get_object_or_404(
            scope_queryset_for_user(
                F29PreparacionMensual.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        serializer = F29StatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_state = draft.estado_preparacion
        try:
            with transaction.atomic():
                draft = register_f29_status(draft, **serializer.validated_data)
                create_audit_event(
                    event_type='sii.f29_preparacion.status_updated',
                    entity_type='f29_preparacion',
                    entity_id=str(draft.pk),
                    summary='Estado de F29 actualizado manualmente',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata=build_state_change_metadata(
                        previous_field='estado_preparacion',
                        previous_state=previous_state,
                        current_field='estado_preparacion',
                        current_state=draft.estado_preparacion,
                        extra={'responsable_revision_ref': redact_sensitive_reference(draft.responsable_revision_ref)},
                    ),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(F29PreparacionMensualSerializer(draft).data, status=status.HTTP_200_OK)


class ProcesoRentaAnualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ProcesoRentaAnualSerializer
    queryset = ProcesoRentaAnual.objects.select_related('empresa', 'source_bundle').all()
    company_scope_paths = ('empresa_id',)


class DDJJPreparacionAnualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = DDJJPreparacionAnualSerializer
    queryset = DDJJPreparacionAnual.objects.select_related('empresa', 'capacidad_tributaria', 'proceso_renta_anual').all()
    company_scope_paths = ('empresa_id',)


class F22PreparacionAnualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = F22PreparacionAnualSerializer
    queryset = F22PreparacionAnual.objects.select_related('empresa', 'capacidad_tributaria', 'proceso_renta_anual').all()
    company_scope_paths = ('empresa_id',)


class AnnualGenerateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = AnnualGenerateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                process, ddjj, f22 = generate_annual_preparation(
                    serializer.validated_data['empresa'],
                    serializer.validated_data['anio_tributario'],
                )
                create_audit_event(
                    event_type='sii.preparacion_anual.generated',
                    entity_type='proceso_renta_anual',
                    entity_id=str(process.pk),
                    summary='Proceso anual preparado',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={'ddjj_id': ddjj.pk, 'f22_id': f22.pk},
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'proceso_renta_anual': ProcesoRentaAnualSerializer(process).data,
                'ddjj_preparacion': DDJJPreparacionAnualSerializer(ddjj).data,
                'f22_preparacion': F22PreparacionAnualSerializer(f22).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DDJJStatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        document = generics.get_object_or_404(
            scope_queryset_for_user(
                DDJJPreparacionAnual.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        serializer = AnnualStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_state = document.estado_preparacion
        try:
            with transaction.atomic():
                document = register_annual_status(document, **serializer.validated_data)
                create_audit_event(
                    event_type='sii.ddjj_preparacion.status_updated',
                    entity_type='ddjj_preparacion',
                    entity_id=str(document.pk),
                    summary='Estado de DDJJ actualizado manualmente',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata=build_state_change_metadata(
                        previous_field='estado_preparacion',
                        previous_state=previous_state,
                        current_field='estado_preparacion',
                        current_state=document.estado_preparacion,
                        extra={'responsable_revision_ref': redact_sensitive_reference(document.responsable_revision_ref)},
                    ),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(DDJJPreparacionAnualSerializer(document).data, status=status.HTTP_200_OK)


class F22StatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        document = generics.get_object_or_404(
            scope_queryset_for_user(
                F22PreparacionAnual.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        serializer = AnnualStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_state = document.estado_preparacion
        try:
            with transaction.atomic():
                document = register_annual_status(document, **serializer.validated_data)
                create_audit_event(
                    event_type='sii.f22_preparacion.status_updated',
                    entity_type='f22_preparacion',
                    entity_id=str(document.pk),
                    summary='Estado de F22 actualizado manualmente',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata=build_state_change_metadata(
                        previous_field='estado_preparacion',
                        previous_state=previous_state,
                        current_field='estado_preparacion',
                        current_state=document.estado_preparacion,
                        extra={'responsable_revision_ref': redact_sensitive_reference(document.responsable_revision_ref)},
                    ),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(F22PreparacionAnualSerializer(document).data, status=status.HTTP_200_OK)
