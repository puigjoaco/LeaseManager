from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import (
    CanalMensajeria,
    ConfiguracionNotificacionContrato,
    MensajeSaliente,
    NotificacionCobranzaProgramada,
)
from .redaction import redact_channel_gate_restrictions


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


def _redacted_payload_attr(obj, field_name):
    return redact_sensitive_payload(getattr(obj, field_name, None))


@admin.register(CanalMensajeria)
class CanalMensajeriaAdmin(admin.ModelAdmin):
    fields = (
        'canal',
        'provider_key',
        'estado_gate',
        'restricciones_operativas_redacted',
        'evidencia_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('canal', 'provider_key', 'estado_gate', 'evidencia_ref_redacted')
    list_filter = ('estado_gate', 'canal')
    search_fields = ('provider_key',)

    @admin.display(description='restricciones_operativas')
    def restricciones_operativas_redacted(self, obj):
        return redact_channel_gate_restrictions(obj.restricciones_operativas or {})

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MensajeSaliente)
class MensajeSalienteAdmin(admin.ModelAdmin):
    fields = (
        'canal',
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'arrendatario',
        'documento_emitido',
        'destinatario',
        'asunto',
        'cuerpo',
        'estado',
        'motivo_bloqueo_redacted',
        'external_ref_redacted',
        'usuario',
        'provider_payload_redacted',
        'enviado_at',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'canal',
        'destinatario',
        'estado',
        'identidad_envio',
        'usuario',
        'external_ref_redacted',
        'enviado_at',
    )
    list_filter = ('canal', 'estado')
    search_fields = ('destinatario', 'asunto')

    @admin.display(description='motivo_bloqueo')
    def motivo_bloqueo_redacted(self, obj):
        return _redacted_attr(obj, 'motivo_bloqueo')

    @admin.display(description='external_ref')
    def external_ref_redacted(self, obj):
        return _redacted_attr(obj, 'external_ref')

    @admin.display(description='provider_payload')
    def provider_payload_redacted(self, obj):
        return _redacted_payload_attr(obj, 'provider_payload')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracionNotificacionContrato)
class ConfiguracionNotificacionContratoAdmin(admin.ModelAdmin):
    fields = (
        'contrato',
        'canal',
        'dias_notificacion',
        'activa',
        'evidencia_configuracion_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('contrato', 'canal', 'dias_notificacion', 'activa', 'evidencia_configuracion_ref_redacted')
    list_filter = ('canal', 'activa')
    search_fields = ('contrato__codigo_contrato',)

    @admin.display(description='evidencia_configuracion_ref')
    def evidencia_configuracion_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_configuracion_ref')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(NotificacionCobranzaProgramada)
class NotificacionCobranzaProgramadaAdmin(admin.ModelAdmin):
    fields = (
        'pago_mensual',
        'configuracion',
        'canal',
        'dia_notificacion',
        'fecha_programada',
        'estado',
        'mensaje_saliente',
        'motivo_estado_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('pago_mensual', 'canal', 'dia_notificacion', 'fecha_programada', 'estado')
    list_filter = ('canal', 'estado')
    search_fields = ('pago_mensual__contrato__codigo_contrato',)

    @admin.display(description='motivo_estado')
    def motivo_estado_redacted(self, obj):
        return _redacted_attr(obj, 'motivo_estado')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

