from django.contrib import admin

from .models import CapacidadTributariaSII, DTEEmitido


@admin.register(CapacidadTributariaSII)
class CapacidadTributariaSIIAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'capacidad_key', 'ambiente', 'estado_gate')
    list_filter = ('capacidad_key', 'ambiente', 'estado_gate')
    search_fields = ('empresa__razon_social', 'certificado_ref')


@admin.register(DTEEmitido)
class DTEEmitidoAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tipo_dte', 'pago_mensual', 'monto_neto_clp', 'estado_dte', 'fecha_emision')
    list_filter = ('tipo_dte', 'estado_dte')
    search_fields = ('empresa__razon_social', 'sii_track_id', 'ultimo_estado_sii')

