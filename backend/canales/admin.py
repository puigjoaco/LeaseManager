from django.contrib import admin

from .models import CanalMensajeria, ConfiguracionNotificacionContrato, MensajeSaliente, NotificacionCobranzaProgramada


@admin.register(CanalMensajeria)
class CanalMensajeriaAdmin(admin.ModelAdmin):
    list_display = ('canal', 'provider_key', 'estado_gate')
    list_filter = ('estado_gate', 'canal')
    search_fields = ('provider_key',)


@admin.register(MensajeSaliente)
class MensajeSalienteAdmin(admin.ModelAdmin):
    list_display = ('canal', 'destinatario', 'estado', 'identidad_envio', 'usuario', 'enviado_at')
    list_filter = ('canal', 'estado')
    search_fields = ('destinatario', 'asunto', 'external_ref')


@admin.register(ConfiguracionNotificacionContrato)
class ConfiguracionNotificacionContratoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'canal', 'dias_notificacion', 'activa')
    list_filter = ('canal', 'activa')
    search_fields = ('contrato__codigo_contrato', 'evidencia_configuracion_ref')


@admin.register(NotificacionCobranzaProgramada)
class NotificacionCobranzaProgramadaAdmin(admin.ModelAdmin):
    list_display = ('pago_mensual', 'canal', 'dia_notificacion', 'fecha_programada', 'estado')
    list_filter = ('canal', 'estado')
    search_fields = ('pago_mensual__contrato__codigo_contrato',)

