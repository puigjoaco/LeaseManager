from django.contrib import admin

from .models import ConexionBancaria, IngresoDesconocido, MovimientoBancarioImportado


@admin.register(ConexionBancaria)
class ConexionBancariaAdmin(admin.ModelAdmin):
    list_display = ('cuenta_recaudadora', 'provider_key', 'estado_conexion', 'primaria_movimientos')
    list_filter = ('estado_conexion', 'provider_key', 'primaria_movimientos')
    search_fields = ('cuenta_recaudadora__numero_cuenta', 'provider_key')


@admin.register(MovimientoBancarioImportado)
class MovimientoBancarioImportadoAdmin(admin.ModelAdmin):
    list_display = ('conexion_bancaria', 'fecha_movimiento', 'tipo_movimiento', 'monto', 'estado_conciliacion')
    list_filter = ('tipo_movimiento', 'estado_conciliacion')
    search_fields = ('descripcion_origen', 'referencia', 'transaction_id_banco')


@admin.register(IngresoDesconocido)
class IngresoDesconocidoAdmin(admin.ModelAdmin):
    list_display = ('cuenta_recaudadora', 'fecha_movimiento', 'monto', 'estado')
    list_filter = ('estado',)
    search_fields = ('descripcion_origen',)

