from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

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
    DDJJPreparacionAnual,
    DTEEmitido,
    F22PreparacionAnual,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    is_safe_public_sii_source_url,
)


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


def _redacted_payload_attr(obj, field_name):
    return redact_sensitive_payload(getattr(obj, field_name, None))


def _public_sii_url_attr(obj, field_name):
    value = getattr(obj, field_name, '') or ''
    if is_safe_public_sii_source_url(value):
        return value
    return redact_sensitive_reference(value)


@admin.register(CapacidadTributariaSII)
class CapacidadTributariaSIIAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'capacidad_key',
        'certificado_ref_redacted',
        'evidencia_ref_redacted',
        'prueba_flujo_ref_redacted',
        'autorizacion_ambiente_ref_redacted',
        'regla_fiscal_ref_redacted',
        'ambiente',
        'estado_gate',
        'ultimo_resultado_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('empresa', 'capacidad_key', 'ambiente', 'estado_gate', 'evidencia_ref_redacted')
    list_filter = ('capacidad_key', 'ambiente', 'estado_gate')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='certificado_ref')
    def certificado_ref_redacted(self, obj):
        return _redacted_attr(obj, 'certificado_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='prueba_flujo_ref')
    def prueba_flujo_ref_redacted(self, obj):
        return _redacted_attr(obj, 'prueba_flujo_ref')

    @admin.display(description='autorizacion_ambiente_ref')
    def autorizacion_ambiente_ref_redacted(self, obj):
        return _redacted_attr(obj, 'autorizacion_ambiente_ref')

    @admin.display(description='regla_fiscal_ref')
    def regla_fiscal_ref_redacted(self, obj):
        return _redacted_attr(obj, 'regla_fiscal_ref')

    @admin.display(description='ultimo_resultado')
    def ultimo_resultado_redacted(self, obj):
        return _redacted_payload_attr(obj, 'ultimo_resultado')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TaxYearRuleSet)
class TaxYearRuleSetAdmin(admin.ModelAdmin):
    fields = (
        'anio_tributario',
        'regimen_tributario',
        'version',
        'estado',
        'fuente_ref_redacted',
        'hash_normativo',
        'responsable_aprobacion_ref_redacted',
        'official_source',
        'descripcion',
        'metadata_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'anio_tributario',
        'regimen_tributario',
        'version',
        'estado',
        'fuente_ref_redacted',
        'responsable_aprobacion_ref_redacted',
        'official_source',
    )
    list_filter = ('anio_tributario', 'estado', 'regimen_tributario')
    search_fields = ('version', 'regimen_tributario__codigo_regimen')

    @admin.display(description='fuente_ref')
    def fuente_ref_redacted(self, obj):
        return _redacted_attr(obj, 'fuente_ref')

    @admin.display(description='responsable_aprobacion_ref')
    def responsable_aprobacion_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_aprobacion_ref')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TaxCodeMapping)
class TaxCodeMappingAdmin(admin.ModelAdmin):
    fields = (
        'rule_set',
        'destino',
        'codigo_interno',
        'codigo_destino',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'official_source',
        'estado',
        'metadata_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'rule_set',
        'destino',
        'codigo_interno',
        'codigo_destino',
        'estado',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'official_source',
    )
    list_filter = ('destino', 'estado', 'rule_set__anio_tributario')
    search_fields = ('codigo_interno', 'codigo_destino', 'rule_set__version')

    @admin.display(description='formula_ref')
    def formula_ref_redacted(self, obj):
        return _redacted_attr(obj, 'formula_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxOfficialSource)
class AnnualTaxOfficialSourceAdmin(admin.ModelAdmin):
    fields = (
        'anio_tributario',
        'source_key',
        'source_type',
        'title',
        'source_url_safe',
        'source_ref_redacted',
        'source_hash',
        'retrieved_on',
        'responsible_ref_redacted',
        'estado',
        'applies_to',
        'form_code',
        'regime_code',
        'scope_note_redacted',
        'metadata_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'anio_tributario',
        'source_key',
        'source_type',
        'estado',
        'applies_to',
        'form_code',
        'responsible_ref_redacted',
    )
    list_filter = ('anio_tributario', 'source_type', 'estado', 'applies_to')
    search_fields = ('source_key', 'title', 'form_code', 'regime_code')

    @admin.display(description='source_url')
    def source_url_safe(self, obj):
        return _public_sii_url_attr(obj, 'source_url')

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='scope_note')
    def scope_note_redacted(self, obj):
        return _redacted_attr(obj, 'scope_note')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxDDJJFormLayout)
class AnnualTaxDDJJFormLayoutAdmin(admin.ModelAdmin):
    fields = (
        'anio_tributario',
        'form_code',
        'title',
        'periodicidad',
        'allows_electronic_form',
        'allows_file_importer',
        'allows_file_upload',
        'allows_commercial_software',
        'allows_assistant',
        'medio_preferente',
        'due_date_label',
        'certificate_code',
        'certificate_due_label',
        'resolution_ref_redacted',
        'declaration_status',
        'layout_ref_redacted',
        'instructions_ref_redacted',
        'responsible_ref_redacted',
        'official_media_source',
        'official_form_source',
        'official_software_source',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_layout',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'anio_tributario',
        'form_code',
        'title',
        'medio_preferente',
        'estado',
        'responsible_ref_redacted',
    )
    list_filter = ('anio_tributario', 'medio_preferente', 'estado')
    search_fields = ('form_code', 'title')

    @admin.display(description='resolution_ref')
    def resolution_ref_redacted(self, obj):
        return _redacted_attr(obj, 'resolution_ref')

    @admin.display(description='layout_ref')
    def layout_ref_redacted(self, obj):
        return _redacted_attr(obj, 'layout_ref')

    @admin.display(description='instructions_ref')
    def instructions_ref_redacted(self, obj):
        return _redacted_attr(obj, 'instructions_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxF22ExportLayout)
class AnnualTaxF22ExportLayoutAdmin(admin.ModelAdmin):
    fields = (
        'anio_tributario',
        'form_code',
        'title',
        'allows_local_preview',
        'allows_certified_file',
        'allows_supervised_portal',
        'medio_preferente',
        'certification_ref_redacted',
        'format_ref_redacted',
        'instructions_ref_redacted',
        'responsible_ref_redacted',
        'official_certification_source',
        'official_instructions_source',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_layout',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'anio_tributario',
        'form_code',
        'title',
        'medio_preferente',
        'estado',
        'responsible_ref_redacted',
    )
    list_filter = ('anio_tributario', 'medio_preferente', 'estado')
    search_fields = ('form_code', 'title')

    @admin.display(description='certification_ref')
    def certification_ref_redacted(self, obj):
        return _redacted_attr(obj, 'certification_ref')

    @admin.display(description='format_ref')
    def format_ref_redacted(self, obj):
        return _redacted_attr(obj, 'format_ref')

    @admin.display(description='instructions_ref')
    def instructions_ref_redacted(self, obj):
        return _redacted_attr(obj, 'instructions_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxSourceBundle)
class AnnualTaxSourceBundleAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'anio_tributario',
        'anio_comercial',
        'source_kind',
        'source_label_redacted',
        'authorization_ref_redacted',
        'responsible_ref_redacted',
        'hash_fuentes',
        'resumen_fuentes_redacted',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'anio_comercial',
        'source_kind',
        'estado',
        'source_label_redacted',
        'responsible_ref_redacted',
    )
    list_filter = ('anio_tributario', 'source_kind', 'estado')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_label')
    def source_label_redacted(self, obj):
        return _redacted_attr(obj, 'source_label')

    @admin.display(description='authorization_ref')
    def authorization_ref_redacted(self, obj):
        return _redacted_attr(obj, 'authorization_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_fuentes')
    def resumen_fuentes_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_fuentes')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MonthlyTaxFact)
class MonthlyTaxFactAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'anio',
        'mes',
        'cierre_mensual',
        'f29_preparacion',
        'liquidacion_mensual',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'resumen_hecho_redacted',
        'hash_hecho',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio',
        'mes',
        'cierre_mensual',
        'f29_preparacion',
        'liquidacion_mensual',
        'estado',
    )
    list_filter = ('anio', 'mes', 'estado')
    search_fields = ('empresa__razon_social', 'source_ref', 'responsible_ref')

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_hecho')
    def resumen_hecho_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_hecho')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxTrialBalance)
class AnnualTaxTrialBalanceAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'official_source',
        'source_balance',
        'anio_tributario',
        'anio_comercial',
        'periodo_cierre',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'lines_total',
        'warnings_total',
        'resumen_balance_redacted',
        'hash_balance',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'periodo_cierre',
        'estado',
        'lines_total',
        'warnings_total',
        'source_ref_redacted',
    )
    list_filter = ('anio_tributario', 'periodo_cierre', 'estado')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_balance')
    def resumen_balance_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_balance')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxTrialBalanceLine)
class AnnualTaxTrialBalanceLineAdmin(admin.ModelAdmin):
    fields = (
        'trial_balance',
        'cuenta_contable',
        'codigo_cuenta',
        'nombre_cuenta',
        'clasificador_dj1847',
        'sumas_debe_clp',
        'sumas_haber_clp',
        'saldo_deudor_clp',
        'saldo_acreedor_clp',
        'inventario_activo_clp',
        'inventario_pasivo_clp',
        'resultado_perdida_clp',
        'resultado_ganancia_clp',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_linea',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'trial_balance',
        'codigo_cuenta',
        'clasificador_dj1847',
        'saldo_deudor_clp',
        'saldo_acreedor_clp',
        'estado',
        'formula_ref_redacted',
    )
    list_filter = ('trial_balance__anio_tributario', 'clasificador_dj1847', 'estado')
    search_fields = ('codigo_cuenta', 'nombre_cuenta', 'trial_balance__empresa__razon_social')

    @admin.display(description='formula_ref')
    def formula_ref_redacted(self, obj):
        return _redacted_attr(obj, 'formula_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxWorkbook)
class AnnualTaxWorkbookAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'anio_tributario',
        'anio_comercial',
        'tipo',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'resumen_workbook_redacted',
        'hash_workbook',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'tipo',
        'estado',
        'source_ref_redacted',
        'responsible_ref_redacted',
    )
    list_filter = ('anio_tributario', 'tipo', 'estado')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_workbook')
    def resumen_workbook_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_workbook')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxWorkbookLine)
class AnnualTaxWorkbookLineAdmin(admin.ModelAdmin):
    fields = (
        'workbook',
        'mapping',
        'codigo_interno',
        'codigo_destino',
        'origen',
        'signo',
        'monto_clp',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'warning_review_ref_redacted',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_linea',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'workbook',
        'codigo_interno',
        'codigo_destino',
        'monto_clp',
        'estado',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'warning_review_ref_redacted',
    )
    list_filter = ('workbook__tipo', 'estado')
    search_fields = ('codigo_interno', 'codigo_destino', 'workbook__empresa__razon_social')

    @admin.display(description='formula_ref')
    def formula_ref_redacted(self, obj):
        return _redacted_attr(obj, 'formula_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='warning_review_ref')
    def warning_review_ref_redacted(self, obj):
        return _redacted_attr(obj, 'warning_review_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualEnterpriseRegisterSet)
class AnnualEnterpriseRegisterSetAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'anio_tributario',
        'anio_comercial',
        'tipo_registro',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'saldo_inicial_clp',
        'movimientos_total_clp',
        'saldo_final_clp',
        'resumen_registro_redacted',
        'hash_registro',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'tipo_registro',
        'estado',
        'saldo_final_clp',
        'source_ref_redacted',
        'responsible_ref_redacted',
    )
    list_filter = ('anio_tributario', 'tipo_registro', 'estado')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_registro')
    def resumen_registro_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_registro')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualEnterpriseRegisterMovement)
class AnnualEnterpriseRegisterMovementAdmin(admin.ModelAdmin):
    fields = (
        'register_set',
        'source_workbook_line',
        'codigo_interno',
        'origen',
        'signo',
        'monto_clp',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'warning_review_ref_redacted',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_movimiento',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'register_set',
        'codigo_interno',
        'origen',
        'monto_clp',
        'estado',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'warning_review_ref_redacted',
    )
    list_filter = ('register_set__tipo_registro', 'estado')
    search_fields = ('codigo_interno', 'register_set__empresa__razon_social')

    @admin.display(description='formula_ref')
    def formula_ref_redacted(self, obj):
        return _redacted_attr(obj, 'formula_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='warning_review_ref')
    def warning_review_ref_redacted(self, obj):
        return _redacted_attr(obj, 'warning_review_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualRealEstateSection)
class AnnualRealEstateSectionAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'official_contribution_source',
        'anio_tributario',
        'anio_comercial',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'propiedades_total',
        'arriendo_devengado_total_clp',
        'arriendo_conciliado_total_clp',
        'arriendo_facturable_total_clp',
        'contribuciones_total_clp',
        'resumen_seccion_redacted',
        'hash_seccion',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado',
        'propiedades_total',
        'arriendo_devengado_total_clp',
        'contribuciones_total_clp',
        'official_contribution_source',
        'source_ref_redacted',
    )
    list_filter = ('anio_tributario', 'estado', 'official_contribution_source__source_type')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_seccion')
    def resumen_seccion_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_seccion')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualRealEstateItem)
class AnnualRealEstateItemAdmin(admin.ModelAdmin):
    fields = (
        'section',
        'propiedad',
        'codigo_propiedad_snapshot',
        'rol_avaluo_snapshot',
        'direccion_snapshot',
        'comuna_snapshot',
        'region_snapshot',
        'tipo_inmueble_snapshot',
        'owner_tipo_snapshot',
        'owner_id_snapshot',
        'arriendo_devengado_clp',
        'arriendo_conciliado_clp',
        'arriendo_facturable_clp',
        'contribuciones_clp',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_item',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'section',
        'codigo_propiedad_snapshot',
        'arriendo_devengado_clp',
        'contribuciones_clp',
        'estado',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
    )
    list_filter = ('estado', 'section__anio_tributario')
    search_fields = ('codigo_propiedad_snapshot', 'section__empresa__razon_social')

    @admin.display(description='formula_ref')
    def formula_ref_redacted(self, obj):
        return _redacted_attr(obj, 'formula_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxArtifactMatrix)
class AnnualTaxArtifactMatrixAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'anio_tributario',
        'anio_comercial',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'items_total',
        'ddjj_items_total',
        'f22_items_total',
        'resumen_matriz_redacted',
        'hash_matriz',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado',
        'items_total',
        'ddjj_items_total',
        'f22_items_total',
        'source_ref_redacted',
    )
    list_filter = ('anio_tributario', 'estado')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='resumen_matriz')
    def resumen_matriz_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_matriz')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxArtifactMatrixItem)
class AnnualTaxArtifactMatrixItemAdmin(admin.ModelAdmin):
    fields = (
        'matrix',
        'target_kind',
        'target_code',
        'medio_sii',
        'source_kind',
        'source_model',
        'source_object_id',
        'source_hash',
        'review_state',
        'formula_ref_redacted',
        'evidencia_ref_redacted',
        'responsible_ref_redacted',
        'warning_review_ref_redacted',
        'warnings_redacted',
        'source_payload_redacted',
        'hash_item',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'matrix',
        'target_kind',
        'target_code',
        'source_kind',
        'review_state',
        'estado',
        'formula_ref_redacted',
        'warning_review_ref_redacted',
    )
    list_filter = ('target_kind', 'source_kind', 'review_state', 'estado', 'matrix__anio_tributario')
    search_fields = ('target_code', 'source_model', 'matrix__empresa__razon_social')

    @admin.display(description='formula_ref')
    def formula_ref_redacted(self, obj):
        return _redacted_attr(obj, 'formula_ref')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='warning_review_ref')
    def warning_review_ref_redacted(self, obj):
        return _redacted_attr(obj, 'warning_review_ref')

    @admin.display(description='warnings')
    def warnings_redacted(self, obj):
        return _redacted_payload_attr(obj, 'warnings')

    @admin.display(description='source_payload')
    def source_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'source_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxDossier)
class AnnualTaxDossierAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
        'anio_tributario',
        'anio_comercial',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'dossier_ref_redacted',
        'review_state',
        'monthly_facts_total',
        'workbooks_total',
        'enterprise_registers_total',
        'real_estate_sections_total',
        'artifact_matrix_items_total',
        'warnings_total',
        'resumen_dossier_redacted',
        'hash_dossier',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado',
        'review_state',
        'warnings_total',
        'artifact_matrix',
        'dossier_ref_redacted',
    )
    list_filter = ('anio_tributario', 'estado', 'review_state')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='dossier_ref')
    def dossier_ref_redacted(self, obj):
        return _redacted_attr(obj, 'dossier_ref')

    @admin.display(description='resumen_dossier')
    def resumen_dossier_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_dossier')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxExport)
class AnnualTaxExportAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'dossier',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
        'official_format_source',
        'anio_tributario',
        'anio_comercial',
        'export_kind',
        'source_ref_redacted',
        'responsible_ref_redacted',
        'export_ref_redacted',
        'review_state',
        'target_items_total',
        'ddjj_items_total',
        'f22_items_total',
        'warnings_total',
        'official_format',
        'sii_submission',
        'final_tax_calculation',
        'export_payload_redacted',
        'hash_export',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'export_kind',
        'estado',
        'review_state',
        'target_items_total',
        'official_format_source',
        'export_ref_redacted',
    )
    list_filter = ('anio_tributario', 'export_kind', 'estado', 'review_state', 'official_format_source')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='source_ref')
    def source_ref_redacted(self, obj):
        return _redacted_attr(obj, 'source_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='export_ref')
    def export_ref_redacted(self, obj):
        return _redacted_attr(obj, 'export_ref')

    @admin.display(description='export_payload')
    def export_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'export_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AnnualTaxReviewChecklist)
class AnnualTaxReviewChecklistAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'proceso_renta_anual',
        'dossier',
        'annual_export',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
        'anio_tributario',
        'anio_comercial',
        'checklist_ref_redacted',
        'responsible_ref_redacted',
        'evidence_ref_redacted',
        'items_total',
        'completed_items_total',
        'blockers_total',
        'warnings_total',
        'review_decision_state',
        'review_decision_ref_redacted',
        'review_decision_evidence_ref_redacted',
        'review_payload_redacted',
        'hash_checklist',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado',
        'review_decision_state',
        'items_total',
        'completed_items_total',
        'blockers_total',
        'warnings_total',
        'checklist_ref_redacted',
    )
    list_filter = ('anio_tributario', 'estado', 'review_decision_state')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='checklist_ref')
    def checklist_ref_redacted(self, obj):
        return _redacted_attr(obj, 'checklist_ref')

    @admin.display(description='responsible_ref')
    def responsible_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsible_ref')

    @admin.display(description='evidence_ref')
    def evidence_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidence_ref')

    @admin.display(description='review_decision_ref')
    def review_decision_ref_redacted(self, obj):
        return _redacted_attr(obj, 'review_decision_ref')

    @admin.display(description='review_decision_evidence_ref')
    def review_decision_evidence_ref_redacted(self, obj):
        return _redacted_attr(obj, 'review_decision_evidence_ref')

    @admin.display(description='review_payload')
    def review_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'review_payload')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DTEEmitido)
class DTEEmitidoAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'capacidad_tributaria',
        'contrato',
        'pago_mensual',
        'distribucion_cobro_mensual',
        'arrendatario',
        'tipo_dte',
        'monto_neto_clp',
        'fecha_emision',
        'estado_dte',
        'sii_track_id_redacted',
        'ultimo_estado_sii',
        'observaciones_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('empresa', 'tipo_dte', 'pago_mensual', 'monto_neto_clp', 'estado_dte', 'fecha_emision')
    list_filter = ('tipo_dte', 'estado_dte')
    search_fields = ('empresa__razon_social', 'ultimo_estado_sii')

    @admin.display(description='sii_track_id')
    def sii_track_id_redacted(self, obj):
        return _redacted_attr(obj, 'sii_track_id')

    @admin.display(description='observaciones')
    def observaciones_redacted(self, obj):
        return _redacted_attr(obj, 'observaciones')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(F29PreparacionMensual)
class F29PreparacionMensualAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'capacidad_tributaria',
        'cierre_mensual',
        'anio',
        'mes',
        'estado_preparacion',
        'resumen_formulario_redacted',
        'borrador_ref_redacted',
        'responsable_revision_ref_redacted',
        'observaciones_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('empresa', 'anio', 'mes', 'estado_preparacion', 'borrador_ref_redacted', 'responsable_revision_ref_redacted')
    list_filter = ('estado_preparacion', 'anio', 'mes')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='resumen_formulario')
    def resumen_formulario_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_formulario')

    @admin.display(description='borrador_ref')
    def borrador_ref_redacted(self, obj):
        return _redacted_attr(obj, 'borrador_ref')

    @admin.display(description='responsable_revision_ref')
    def responsable_revision_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_revision_ref')

    @admin.display(description='observaciones')
    def observaciones_redacted(self, obj):
        return _redacted_attr(obj, 'observaciones')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class AnnualTaxArtifactAdminMixin(admin.ModelAdmin):
    list_filter = ('estado_preparacion', 'anio_tributario')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='observaciones')
    def observaciones_redacted(self, obj):
        return _redacted_attr(obj, 'observaciones')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProcesoRentaAnual)
class ProcesoRentaAnualAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'anio_tributario',
        'estado',
        'source_bundle',
        'fecha_preparacion',
        'resumen_anual_redacted',
        'paquete_ddjj_ref_redacted',
        'borrador_f22_ref_redacted',
        'responsable_revision_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado',
        'paquete_ddjj_ref_redacted',
        'borrador_f22_ref_redacted',
        'responsable_revision_ref_redacted',
    )
    list_filter = ('estado', 'anio_tributario')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='resumen_anual')
    def resumen_anual_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_anual')

    @admin.display(description='paquete_ddjj_ref')
    def paquete_ddjj_ref_redacted(self, obj):
        return _redacted_attr(obj, 'paquete_ddjj_ref')

    @admin.display(description='borrador_f22_ref')
    def borrador_f22_ref_redacted(self, obj):
        return _redacted_attr(obj, 'borrador_f22_ref')

    @admin.display(description='responsable_revision_ref')
    def responsable_revision_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_revision_ref')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DDJJPreparacionAnual)
class DDJJPreparacionAnualAdmin(AnnualTaxArtifactAdminMixin):
    fields = (
        'empresa',
        'capacidad_tributaria',
        'proceso_renta_anual',
        'anio_tributario',
        'estado_preparacion',
        'resumen_paquete_redacted',
        'paquete_ref_redacted',
        'responsable_revision_ref_redacted',
        'observaciones_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado_preparacion',
        'paquete_ref_redacted',
        'responsable_revision_ref_redacted',
    )

    @admin.display(description='resumen_paquete')
    def resumen_paquete_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_paquete')

    @admin.display(description='paquete_ref')
    def paquete_ref_redacted(self, obj):
        return _redacted_attr(obj, 'paquete_ref')

    @admin.display(description='responsable_revision_ref')
    def responsable_revision_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_revision_ref')


@admin.register(F22PreparacionAnual)
class F22PreparacionAnualAdmin(AnnualTaxArtifactAdminMixin):
    fields = (
        'empresa',
        'capacidad_tributaria',
        'proceso_renta_anual',
        'anio_tributario',
        'estado_preparacion',
        'resumen_f22_redacted',
        'borrador_ref_redacted',
        'responsable_revision_ref_redacted',
        'observaciones_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'empresa',
        'anio_tributario',
        'estado_preparacion',
        'borrador_ref_redacted',
        'responsable_revision_ref_redacted',
    )

    @admin.display(description='resumen_f22')
    def resumen_f22_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_f22')

    @admin.display(description='borrador_ref')
    def borrador_ref_redacted(self, obj):
        return _redacted_attr(obj, 'borrador_ref')

    @admin.display(description='responsable_revision_ref')
    def responsable_revision_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_revision_ref')
