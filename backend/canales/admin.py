from django.contrib import admin

from .models import CanalMensajeria, MensajeSaliente


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

