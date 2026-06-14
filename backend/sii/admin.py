from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import (
    AnnualTaxSourceBundle,
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
)


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


def _redacted_payload_attr(obj, field_name):
    return redact_sensitive_payload(getattr(obj, field_name, None))


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
    )
    list_filter = ('workbook__tipo', 'estado')
    search_fields = ('codigo_interno', 'codigo_destino', 'workbook__empresa__razon_social')

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
