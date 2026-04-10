from django.contrib import admin

from .models import AsignacionCanalOperacion, CuentaRecaudadora, IdentidadDeEnvio, MandatoOperacion


@admin.register(CuentaRecaudadora)
class CuentaRecaudadoraAdmin(admin.ModelAdmin):
    list_display = ('institucion', 'numero_cuenta', 'owner_tipo', 'owner_display', 'estado_operativo')
    list_filter = ('estado_operativo', 'moneda_operativa', 'institucion')
    search_fields = ('institucion', 'numero_cuenta', 'titular_nombre', 'titular_rut')


@admin.register(IdentidadDeEnvio)
class IdentidadDeEnvioAdmin(admin.ModelAdmin):
    list_display = ('canal', 'remitente_visible', 'direccion_o_numero', 'owner_tipo', 'owner_display', 'estado')
    list_filter = ('canal', 'estado')
    search_fields = ('remitente_visible', 'direccion_o_numero', 'credencial_ref')


@admin.register(MandatoOperacion)
class MandatoOperacionAdmin(admin.ModelAdmin):
    list_display = (
        'propiedad',
        'propietario_tipo',
        'administrador_operativo_tipo',
        'recaudador_tipo',
        'cuenta_recaudadora',
        'estado',
        'vigencia_desde',
    )
    list_filter = ('estado', 'tipo_relacion_operativa')
    search_fields = ('propiedad__codigo_propiedad', 'propiedad__direccion', 'tipo_relacion_operativa')


@admin.register(AsignacionCanalOperacion)
class AsignacionCanalOperacionAdmin(admin.ModelAdmin):
    list_display = ('mandato_operacion', 'canal', 'identidad_envio', 'prioridad', 'estado')
    list_filter = ('canal', 'estado')
    search_fields = ('mandato_operacion__propiedad__codigo_propiedad', 'identidad_envio__direccion_o_numero')
