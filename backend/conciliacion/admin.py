from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import (
    CuadraturaBancaria,
    ConexionBancaria,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    TransferenciaIntercuenta,
)


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, ''))


def _redacted_payload_attr(obj, field_name):
    return redact_sensitive_payload(getattr(obj, field_name, None))


def _redacted_account_label(account):
    if not account:
        return '-'
    return f'Cuenta recaudadora #{account.pk}'


@admin.register(ConexionBancaria)
class ConexionBancariaAdmin(admin.ModelAdmin):
    fields = (
        'cuenta_recaudadora_redacted',
        'provider_key',
        'scope',
        'credencial_ref_redacted',
        'evidencia_gate_ref_redacted',
        'prueba_conectividad_ref_redacted',
        'prueba_movimientos_ref_redacted',
        'prueba_saldos_ref_redacted',
        'expira_en',
        'estado_conexion',
        'primaria_movimientos',
        'primaria_saldos',
        'primaria_conectividad',
        'ultimo_exito_at',
        'ultimo_error_at',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'cuenta_recaudadora_redacted',
        'credencial_ref_redacted',
        'evidencia_gate_ref_redacted',
        'prueba_conectividad_ref_redacted',
        'prueba_movimientos_ref_redacted',
        'prueba_saldos_ref_redacted',
        'created_at',
        'updated_at',
    )
    list_display = (
        'cuenta_recaudadora_redacted',
        'provider_key',
        'estado_conexion',
        'primaria_movimientos',
        'evidencia_gate_ref_redacted',
    )
    list_filter = ('estado_conexion', 'provider_key', 'primaria_movimientos', 'primaria_saldos', 'primaria_conectividad')
    search_fields = ('provider_key',)

    @admin.display(description='cuenta_recaudadora')
    def cuenta_recaudadora_redacted(self, obj):
        return _redacted_account_label(obj.cuenta_recaudadora)

    @admin.display(description='credencial_ref')
    def credencial_ref_redacted(self, obj):
        return _redacted_attr(obj, 'credencial_ref')

    @admin.display(description='evidencia_gate_ref')
    def evidencia_gate_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_gate_ref')

    @admin.display(description='prueba_conectividad_ref')
    def prueba_conectividad_ref_redacted(self, obj):
        return _redacted_attr(obj, 'prueba_conectividad_ref')

    @admin.display(description='prueba_movimientos_ref')
    def prueba_movimientos_ref_redacted(self, obj):
        return _redacted_attr(obj, 'prueba_movimientos_ref')

    @admin.display(description='prueba_saldos_ref')
    def prueba_saldos_ref_redacted(self, obj):
        return _redacted_attr(obj, 'prueba_saldos_ref')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimientoBancarioImportado)
class MovimientoBancarioImportadoAdmin(admin.ModelAdmin):
    fields = (
        'conexion_bancaria_redacted',
        'fecha_movimiento',
        'tipo_movimiento',
        'monto',
        'descripcion_origen',
        'origen_importacion',
        'evidencia_importacion_ref_redacted',
        'numero_documento',
        'saldo_reportado',
        'referencia_redacted',
        'transaction_id_banco_redacted',
        'estado_conciliacion',
        'pago_mensual',
        'codigo_cobro_residual',
        'notas_admin_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'conexion_bancaria_redacted',
        'fecha_movimiento',
        'tipo_movimiento',
        'monto',
        'origen_importacion',
        'estado_conciliacion',
        'referencia_redacted',
    )
    list_filter = ('tipo_movimiento', 'origen_importacion', 'estado_conciliacion')
    search_fields = ('descripcion_origen', 'numero_documento')

    @admin.display(description='conexion_bancaria')
    def conexion_bancaria_redacted(self, obj):
        connection = getattr(obj, 'conexion_bancaria', None)
        if not connection:
            return '-'
        return f'Conexion bancaria #{connection.pk}'

    @admin.display(description='evidencia_importacion_ref')
    def evidencia_importacion_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_importacion_ref')

    @admin.display(description='referencia')
    def referencia_redacted(self, obj):
        return _redacted_attr(obj, 'referencia')

    @admin.display(description='transaction_id_banco')
    def transaction_id_banco_redacted(self, obj):
        return _redacted_attr(obj, 'transaction_id_banco')

    @admin.display(description='notas_admin')
    def notas_admin_redacted(self, obj):
        return _redacted_attr(obj, 'notas_admin')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(IngresoDesconocido)
class IngresoDesconocidoAdmin(admin.ModelAdmin):
    fields = (
        'movimiento_bancario',
        'cuenta_recaudadora_redacted',
        'monto',
        'fecha_movimiento',
        'descripcion_origen',
        'estado',
        'sugerencia_asistida_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('cuenta_recaudadora_redacted', 'fecha_movimiento', 'monto', 'estado')
    list_filter = ('estado',)
    search_fields = ('descripcion_origen',)

    @admin.display(description='cuenta_recaudadora')
    def cuenta_recaudadora_redacted(self, obj):
        return _redacted_account_label(obj.cuenta_recaudadora)

    @admin.display(description='sugerencia_asistida')
    def sugerencia_asistida_redacted(self, obj):
        return _redacted_payload_attr(obj, 'sugerencia_asistida')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CuadraturaBancaria)
class CuadraturaBancariaAdmin(admin.ModelAdmin):
    fields = (
        'cuenta_recaudadora_redacted',
        'periodo_economico',
        'fecha_cuadratura',
        'saldo_sistema_clp',
        'saldo_banco_clp',
        'diferencia_clp',
        'estado',
        'evidencia_cuadratura_ref_redacted',
        'responsable_ref_redacted',
        'rationale_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'cuenta_recaudadora_redacted',
        'periodo_economico',
        'fecha_cuadratura',
        'saldo_sistema_clp',
        'saldo_banco_clp',
        'diferencia_clp',
        'estado',
    )
    list_filter = ('estado', 'periodo_economico')
    search_fields = ('periodo_economico',)

    @admin.display(description='cuenta_recaudadora')
    def cuenta_recaudadora_redacted(self, obj):
        return _redacted_account_label(obj.cuenta_recaudadora)

    @admin.display(description='evidencia_cuadratura_ref')
    def evidencia_cuadratura_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_cuadratura_ref')

    @admin.display(description='responsable_ref')
    def responsable_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_ref')

    @admin.display(description='rationale')
    def rationale_redacted(self, obj):
        return _redacted_attr(obj, 'rationale')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TransferenciaIntercuenta)
class TransferenciaIntercuentaAdmin(admin.ModelAdmin):
    fields = (
        'periodo_economico',
        'movimiento_origen',
        'movimiento_destino',
        'entidad_origen_tipo',
        'entidad_origen_id',
        'entidad_destino_tipo',
        'entidad_destino_id',
        'criterio_conciliacion_redacted',
        'evidencia_transferencia_ref_redacted',
        'responsable_ref_redacted',
        'rationale_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = (
        'periodo_economico',
        'movimiento_origen',
        'movimiento_destino',
        'entidad_origen_tipo',
        'entidad_destino_tipo',
    )
    list_filter = ('periodo_economico', 'entidad_origen_tipo', 'entidad_destino_tipo')
    search_fields = ('periodo_economico',)

    @admin.display(description='criterio_conciliacion')
    def criterio_conciliacion_redacted(self, obj):
        return _redacted_attr(obj, 'criterio_conciliacion')

    @admin.display(description='evidencia_transferencia_ref')
    def evidencia_transferencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_transferencia_ref')

    @admin.display(description='responsable_ref')
    def responsable_ref_redacted(self, obj):
        return _redacted_attr(obj, 'responsable_ref')

    @admin.display(description='rationale')
    def rationale_redacted(self, obj):
        return _redacted_attr(obj, 'rationale')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

