from django.contrib import admin

from .models import CuadraturaBancaria, ConexionBancaria, IngresoDesconocido, MovimientoBancarioImportado


@admin.register(ConexionBancaria)
class ConexionBancariaAdmin(admin.ModelAdmin):
    list_display = ('cuenta_recaudadora', 'provider_key', 'estado_conexion', 'primaria_movimientos', 'evidencia_gate_ref')
    list_filter = ('estado_conexion', 'provider_key', 'primaria_movimientos', 'primaria_saldos', 'primaria_conectividad')
    search_fields = ('cuenta_recaudadora__numero_cuenta', 'provider_key', 'evidencia_gate_ref')


@admin.register(MovimientoBancarioImportado)
class MovimientoBancarioImportadoAdmin(admin.ModelAdmin):
    list_display = (
        'conexion_bancaria',
        'fecha_movimiento',
        'tipo_movimiento',
        'monto',
        'origen_importacion',
        'estado_conciliacion',
    )
    list_filter = ('tipo_movimiento', 'origen_importacion', 'estado_conciliacion')
    search_fields = ('descripcion_origen', 'referencia', 'transaction_id_banco', 'evidencia_importacion_ref')


@admin.register(IngresoDesconocido)
class IngresoDesconocidoAdmin(admin.ModelAdmin):
    list_display = ('cuenta_recaudadora', 'fecha_movimiento', 'monto', 'estado')
    list_filter = ('estado',)
    search_fields = ('descripcion_origen',)


@admin.register(CuadraturaBancaria)
class CuadraturaBancariaAdmin(admin.ModelAdmin):
    list_display = (
        'cuenta_recaudadora',
        'periodo_economico',
        'fecha_cuadratura',
        'saldo_sistema_clp',
        'saldo_banco_clp',
        'diferencia_clp',
        'estado',
    )
    list_filter = ('estado', 'periodo_economico')
    search_fields = ('cuenta_recaudadora__numero_cuenta', 'evidencia_cuadratura_ref', 'responsable_ref')

