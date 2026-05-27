from django.contrib import admin

from core.reference_validation import redact_sensitive_reference

from .models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    ContactoPagoArrendatario,
    Contrato,
    ContratoPropiedad,
    PeriodoContractual,
)


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


@admin.register(Arrendatario)
class ArrendatarioAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_razon_social',
        'rut',
        'tipo_arrendatario',
        'estado_contacto',
        'whatsapp_bloqueado',
        'whatsapp_bloqueado_at',
        'whatsapp_rehabilitado_at',
    )
    list_filter = ('tipo_arrendatario', 'estado_contacto', 'whatsapp_bloqueado')
    search_fields = ('nombre_razon_social', 'rut', 'email')


@admin.register(ContactoPagoArrendatario)
class ContactoPagoArrendatarioAdmin(admin.ModelAdmin):
    list_display = ('arrendatario', 'nombre', 'rol_operativo', 'estado', 'es_principal')
    list_filter = ('estado', 'es_principal')
    search_fields = ('arrendatario__nombre_razon_social', 'nombre', 'email', 'telefono')


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    fields = (
        'codigo_contrato',
        'mandato_operacion',
        'arrendatario',
        'fecha_inicio',
        'fecha_fin_vigente',
        'fecha_entrega',
        'fecha_registro_operativo',
        'entrega_llaves_autorizacion_ref_redacted',
        'entrega_llaves_autorizacion_motivo_redacted',
        'terminacion_anticipada_prorrata_ref_redacted',
        'terminacion_anticipada_prorrata_motivo_redacted',
        'dia_pago_mensual',
        'plazo_notificacion_termino_dias',
        'dias_prealerta_admin',
        'estado',
        'identidad_envio_override',
        'politica_documental',
        'tiene_tramos',
        'tiene_gastos_comunes',
        'snapshot_representante_legal',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'entrega_llaves_autorizacion_ref_redacted',
        'entrega_llaves_autorizacion_motivo_redacted',
        'terminacion_anticipada_prorrata_ref_redacted',
        'terminacion_anticipada_prorrata_motivo_redacted',
        'created_at',
        'updated_at',
    )
    list_display = (
        'codigo_contrato',
        'arrendatario',
        'mandato_operacion',
        'estado',
        'politica_documental',
        'fecha_inicio',
        'fecha_fin_vigente',
    )
    list_filter = ('estado', 'politica_documental', 'tiene_tramos', 'tiene_gastos_comunes')
    search_fields = ('codigo_contrato', 'arrendatario__nombre_razon_social')

    def entrega_llaves_autorizacion_ref_redacted(self, obj):
        return _redacted_attr(obj, 'entrega_llaves_autorizacion_ref')

    def entrega_llaves_autorizacion_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'entrega_llaves_autorizacion_motivo')

    def terminacion_anticipada_prorrata_ref_redacted(self, obj):
        return _redacted_attr(obj, 'terminacion_anticipada_prorrata_ref')

    def terminacion_anticipada_prorrata_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'terminacion_anticipada_prorrata_motivo')

    def has_add_permission(self, request):
        return False


@admin.register(ContratoPropiedad)
class ContratoPropiedadAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'propiedad', 'rol_en_contrato', 'codigo_conciliacion_efectivo_snapshot')
    list_filter = ('rol_en_contrato',)
    search_fields = ('contrato__codigo_contrato', 'propiedad__codigo_propiedad')


@admin.register(PeriodoContractual)
class PeriodoContractualAdmin(admin.ModelAdmin):
    fields = (
        'contrato',
        'numero_periodo',
        'fecha_inicio',
        'fecha_fin',
        'monto_base',
        'moneda_base',
        'tipo_periodo',
        'origen_periodo',
        'politica_base_renovacion_ref_redacted',
        'politica_base_renovacion_motivo_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'politica_base_renovacion_ref_redacted',
        'politica_base_renovacion_motivo_redacted',
        'created_at',
        'updated_at',
    )
    list_display = ('contrato', 'numero_periodo', 'fecha_inicio', 'fecha_fin', 'monto_base', 'moneda_base')
    list_filter = ('moneda_base',)
    search_fields = ('contrato__codigo_contrato',)

    def politica_base_renovacion_ref_redacted(self, obj):
        return _redacted_attr(obj, 'politica_base_renovacion_ref')

    def politica_base_renovacion_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'politica_base_renovacion_motivo')

    def has_add_permission(self, request):
        return False


@admin.register(CodeudorSolidario)
class CodeudorSolidarioAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'fecha_inclusion', 'estado')
    list_filter = ('estado',)
    search_fields = ('contrato__codigo_contrato',)


@admin.register(AvisoTermino)
class AvisoTerminoAdmin(admin.ModelAdmin):
    fields = (
        'contrato',
        'fecha_efectiva',
        'causal',
        'estado',
        'resolucion_conflicto_renovacion_ref_redacted',
        'resolucion_conflicto_renovacion_motivo_redacted',
        'registrado_por',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'resolucion_conflicto_renovacion_ref_redacted',
        'resolucion_conflicto_renovacion_motivo_redacted',
        'created_at',
        'updated_at',
    )
    list_display = ('contrato', 'fecha_efectiva', 'causal', 'estado', 'registrado_por')
    list_filter = ('estado',)
    search_fields = ('contrato__codigo_contrato', 'causal')

    def resolucion_conflicto_renovacion_ref_redacted(self, obj):
        return _redacted_attr(obj, 'resolucion_conflicto_renovacion_ref')

    def resolucion_conflicto_renovacion_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'resolucion_conflicto_renovacion_motivo')

    def has_add_permission(self, request):
        return False

