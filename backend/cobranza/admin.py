from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import (
    AjusteContrato,
    CodigoCobroResidual,
    EstadoCuentaArrendatario,
    GateCobroExterno,
    GarantiaContractual,
    HistorialGarantia,
    IntentoPagoWebPay,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
)


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


def _redacted_payload_attr(obj, field_name):
    return redact_sensitive_payload(getattr(obj, field_name, None))


@admin.register(ValorUFDiario)
class ValorUFDiarioAdmin(admin.ModelAdmin):
    fields = (
        'fecha',
        'valor',
        'source_key',
        'evidencia_ref_redacted',
        'motivo_carga_redacted',
        'responsable_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'evidencia_ref_redacted',
        'motivo_carga_redacted',
        'responsable_ref_redacted',
        'created_at',
        'updated_at',
    )
    list_display = ('fecha', 'valor', 'source_key', 'responsable_ref_redacted')
    list_filter = ('source_key',)
    search_fields = ('source_key',)

    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    def motivo_carga_redacted(self, obj):
        return _redacted_attr(obj, 'motivo_carga')

    def responsable_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_ref')

    def has_add_permission(self, request):
        return False


@admin.register(AjusteContrato)
class AjusteContratoAdmin(admin.ModelAdmin):
    fields = (
        'contrato',
        'tipo_ajuste',
        'monto',
        'moneda',
        'mes_inicio',
        'mes_fin',
        'justificacion_redacted',
        'activo',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('justificacion_redacted', 'created_at', 'updated_at')
    list_display = (
        'contrato',
        'tipo_ajuste',
        'monto',
        'moneda',
        'mes_inicio',
        'mes_fin',
        'justificacion_redacted',
        'activo',
    )
    list_filter = ('moneda', 'activo')
    search_fields = ('contrato__codigo_contrato', 'tipo_ajuste')

    def justificacion_redacted(self, obj):
        return _redacted_attr(obj, 'justificacion')

    def has_add_permission(self, request):
        return False


@admin.register(PagoMensual)
class PagoMensualAdmin(admin.ModelAdmin):
    fields = (
        'contrato',
        'repactacion_deuda',
        'periodo_contractual',
        'mes',
        'anio',
        'monto_facturable_clp',
        'monto_calculado_clp',
        'monto_efecto_codigo_efectivo_clp',
        'moneda_calculo',
        'uf_fecha_usada',
        'uf_valor_usado',
        'uf_source_key',
        'monto_pagado_clp',
        'fecha_vencimiento',
        'fecha_deposito_banco',
        'fecha_pago_webpay',
        'fecha_deteccion_sistema',
        'estado_pago',
        'dias_mora',
        'codigo_conciliacion_efectivo',
        'resolucion_pago_excepcional_ref_redacted',
        'resolucion_pago_excepcional_motivo_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'resolucion_pago_excepcional_ref_redacted',
        'resolucion_pago_excepcional_motivo_redacted',
        'created_at',
        'updated_at',
    )
    list_display = (
        'contrato',
        'anio',
        'mes',
        'monto_calculado_clp',
        'moneda_calculo',
        'uf_fecha_usada',
        'estado_pago',
        'fecha_pago_webpay',
        'dias_mora',
    )
    list_filter = ('estado_pago', 'moneda_calculo', 'anio', 'mes')
    search_fields = ('contrato__codigo_contrato',)

    def resolucion_pago_excepcional_ref_redacted(self, obj):
        return _redacted_attr(obj, 'resolucion_pago_excepcional_ref')

    def resolucion_pago_excepcional_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'resolucion_pago_excepcional_motivo')

    def has_add_permission(self, request):
        return False


@admin.register(GateCobroExterno)
class GateCobroExternoAdmin(admin.ModelAdmin):
    fields = (
        'capacidad_key',
        'provider_key',
        'estado_gate',
        'evidencia_ref_redacted',
        'restricciones_operativas_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'evidencia_ref_redacted',
        'restricciones_operativas_redacted',
        'created_at',
        'updated_at',
    )
    list_display = ('capacidad_key', 'provider_key', 'estado_gate', 'evidencia_ref_redacted')
    list_filter = ('capacidad_key', 'estado_gate')
    search_fields = ('provider_key',)

    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    def restricciones_operativas_redacted(self, obj):
        return _redacted_payload_attr(obj, 'restricciones_operativas')

    def has_add_permission(self, request):
        return False


@admin.register(IntentoPagoWebPay)
class IntentoPagoWebPayAdmin(admin.ModelAdmin):
    fields = (
        'pago_mensual',
        'gate_cobro',
        'provider_key',
        'monto_clp_snapshot',
        'buy_order',
        'session_id',
        'return_url_ref_redacted',
        'estado',
        'motivo_bloqueo_redacted',
        'external_ref_redacted',
        'fecha_pago_webpay',
        'confirmado_at',
        'usuario',
        'provider_payload_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'return_url_ref_redacted',
        'motivo_bloqueo_redacted',
        'external_ref_redacted',
        'provider_payload_redacted',
        'created_at',
        'updated_at',
    )
    list_display = (
        'pago_mensual',
        'provider_key',
        'monto_clp_snapshot',
        'estado',
        'external_ref_redacted',
        'fecha_pago_webpay',
    )
    list_filter = ('estado', 'provider_key')
    search_fields = ('pago_mensual__contrato__codigo_contrato', 'buy_order')

    def return_url_ref_redacted(self, obj):
        return _redacted_attr(obj, 'return_url_ref')

    def motivo_bloqueo_redacted(self, obj):
        return _redacted_attr(obj, 'motivo_bloqueo')

    def external_ref_redacted(self, obj):
        return _redacted_attr(obj, 'external_ref')

    def provider_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'provider_payload')

    def has_add_permission(self, request):
        return False


@admin.register(GarantiaContractual)
class GarantiaContractualAdmin(admin.ModelAdmin):
    fields = (
        'contrato',
        'monto_pactado',
        'monto_recibido',
        'monto_devuelto',
        'monto_aplicado',
        'estado_garantia',
        'fecha_recepcion',
        'fecha_cierre',
        'aceptacion_parcial_ref_redacted',
        'resolucion_exceso_garantia',
        'resolucion_exceso_garantia_ref_redacted',
        'resolucion_exceso_garantia_motivo_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'aceptacion_parcial_ref_redacted',
        'resolucion_exceso_garantia_ref_redacted',
        'resolucion_exceso_garantia_motivo_redacted',
        'created_at',
        'updated_at',
    )
    list_display = (
        'contrato',
        'monto_pactado',
        'monto_recibido',
        'monto_devuelto',
        'monto_aplicado',
        'estado_garantia',
    )
    list_filter = ('estado_garantia',)
    search_fields = ('contrato__codigo_contrato',)

    def aceptacion_parcial_ref_redacted(self, obj):
        return _redacted_attr(obj, 'aceptacion_parcial_ref')

    def resolucion_exceso_garantia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'resolucion_exceso_garantia_ref')

    def resolucion_exceso_garantia_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'resolucion_exceso_garantia_motivo')

    def has_add_permission(self, request):
        return False


@admin.register(HistorialGarantia)
class HistorialGarantiaAdmin(admin.ModelAdmin):
    fields = (
        'garantia_contractual',
        'tipo_movimiento',
        'monto_clp',
        'fecha',
        'justificacion_redacted',
        'movimiento_origen',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('justificacion_redacted', 'created_at', 'updated_at')
    list_display = ('garantia_contractual', 'tipo_movimiento', 'monto_clp', 'fecha')
    list_filter = ('tipo_movimiento',)
    search_fields = ('garantia_contractual__contrato__codigo_contrato',)

    def justificacion_redacted(self, obj):
        return _redacted_attr(obj, 'justificacion')

    def has_add_permission(self, request):
        return False


@admin.register(RepactacionDeuda)
class RepactacionDeudaAdmin(admin.ModelAdmin):
    fields = (
        'arrendatario',
        'contrato_origen',
        'deuda_total_original',
        'cantidad_cuotas',
        'monto_cuota',
        'saldo_pendiente',
        'estado',
        'excepcion_parcial_ref_redacted',
        'excepcion_parcial_motivo_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'excepcion_parcial_ref_redacted',
        'excepcion_parcial_motivo_redacted',
        'created_at',
        'updated_at',
    )
    list_display = ('arrendatario', 'contrato_origen', 'deuda_total_original', 'saldo_pendiente', 'estado')
    list_filter = ('estado',)
    search_fields = ('arrendatario__nombre_razon_social', 'contrato_origen__codigo_contrato')

    def excepcion_parcial_ref_redacted(self, obj):
        return _redacted_attr(obj, 'excepcion_parcial_ref')

    def excepcion_parcial_motivo_redacted(self, obj):
        return _redacted_attr(obj, 'excepcion_parcial_motivo')

    def has_add_permission(self, request):
        return False


@admin.register(CodigoCobroResidual)
class CodigoCobroResidualAdmin(admin.ModelAdmin):
    list_display = ('referencia_visible', 'arrendatario', 'contrato_origen', 'saldo_actual', 'estado')
    list_filter = ('estado',)
    search_fields = ('referencia_visible', 'arrendatario__nombre_razon_social', 'contrato_origen__codigo_contrato')


@admin.register(EstadoCuentaArrendatario)
class EstadoCuentaArrendatarioAdmin(admin.ModelAdmin):
    fields = (
        'arrendatario',
        'resumen_operativo',
        'score_pago',
        'observaciones_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = ('observaciones_redacted', 'created_at', 'updated_at')
    list_display = ('arrendatario', 'score_pago', 'observaciones_redacted', 'updated_at')
    search_fields = ('arrendatario__nombre_razon_social', 'arrendatario__rut')

    def observaciones_redacted(self, obj):
        return _redacted_attr(obj, 'observaciones')
