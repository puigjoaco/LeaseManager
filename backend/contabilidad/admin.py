from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EfectoReaperturaCierreMensual,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
)


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, ''))


def _redacted_payload_attr(obj, field_name):
    return redact_sensitive_payload(getattr(obj, field_name, None))


@admin.register(RegimenTributarioEmpresa)
class RegimenTributarioEmpresaAdmin(admin.ModelAdmin):
    list_display = ('codigo_regimen', 'descripcion', 'estado')
    list_filter = ('estado',)
    search_fields = ('codigo_regimen', 'descripcion')


@admin.register(ConfiguracionFiscalEmpresa)
class ConfiguracionFiscalEmpresaAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'regimen_tributario', 'moneda_funcional', 'estado')
    list_filter = ('estado', 'moneda_funcional', 'aplica_ppm')
    search_fields = ('empresa__razon_social',)


@admin.register(CuentaContable)
class CuentaContableAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'plan_cuentas_version', 'codigo', 'nombre', 'naturaleza', 'estado')
    list_filter = ('estado', 'naturaleza', 'plan_cuentas_version')
    search_fields = ('codigo', 'nombre', 'empresa__razon_social')


@admin.register(ReglaContable)
class ReglaContableAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'evento_tipo', 'plan_cuentas_version', 'vigencia_desde', 'estado')
    list_filter = ('estado', 'plan_cuentas_version')
    search_fields = ('evento_tipo', 'empresa__razon_social')


@admin.register(MatrizReglasContables)
class MatrizReglasContablesAdmin(admin.ModelAdmin):
    list_display = ('regla_contable', 'cuenta_debe', 'cuenta_haber', 'estado')
    list_filter = ('estado',)
    search_fields = ('regla_contable__evento_tipo', 'cuenta_debe__codigo', 'cuenta_haber__codigo')


@admin.register(EventoContable)
class EventoContableAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'evento_tipo',
        'entidad_origen_tipo',
        'entidad_origen_id',
        'fecha_operativa',
        'moneda',
        'monto_base',
        'payload_resumen_redacted',
        'idempotency_key',
        'estado_contable',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('evento_tipo', 'empresa', 'fecha_operativa', 'monto_base', 'estado_contable')
    list_filter = ('estado_contable', 'evento_tipo', 'moneda')
    search_fields = ('idempotency_key', 'entidad_origen_tipo', 'entidad_origen_id')

    @admin.display(description='payload_resumen')
    def payload_resumen_redacted(self, obj):
        return _redacted_payload_attr(obj, 'payload_resumen')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    fields = (
        'evento_contable',
        'fecha_contable',
        'periodo_contable',
        'estado',
        'debe_total',
        'haber_total',
        'moneda_funcional',
        'hash_integridad',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('id', 'evento_contable', 'fecha_contable', 'periodo_contable', 'debe_total', 'haber_total', 'estado')
    list_filter = ('estado', 'periodo_contable')
    search_fields = ('evento_contable__idempotency_key',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimientoAsiento)
class MovimientoAsientoAdmin(admin.ModelAdmin):
    fields = (
        'asiento_contable',
        'cuenta_contable',
        'tipo_movimiento',
        'monto',
        'glosa',
        'centro_resultado_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('asiento_contable', 'cuenta_contable', 'tipo_movimiento', 'monto', 'centro_resultado_ref_redacted')
    list_filter = ('tipo_movimiento',)
    search_fields = ('asiento_contable__id', 'cuenta_contable__codigo', 'glosa')

    @admin.display(description='centro_resultado_ref')
    def centro_resultado_ref_redacted(self, obj):
        return _redacted_attr(obj, 'centro_resultado_ref')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PoliticaReversoContable)
class PoliticaReversoContableAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tipo_ajuste', 'usa_reverso', 'usa_asiento_complementario', 'permite_reapertura', 'estado')
    list_filter = ('estado', 'usa_reverso', 'permite_reapertura')
    search_fields = ('empresa__razon_social', 'tipo_ajuste')


@admin.register(EfectoReaperturaCierreMensual)
class EfectoReaperturaCierreMensualAdmin(admin.ModelAdmin):
    fields = (
        'cierre',
        'politica_reverso',
        'evento_contable',
        'tipo_efecto',
        'monto_efecto',
        'motivo_redacted',
        'efecto_esperado_redacted',
        'evidencia_ref_redacted',
        'fecha_aplicacion',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('cierre', 'tipo_efecto', 'monto_efecto', 'evento_contable', 'fecha_aplicacion')
    list_filter = ('tipo_efecto',)
    search_fields = ('cierre__empresa__razon_social', 'evento_contable__idempotency_key')

    @admin.display(description='motivo')
    def motivo_redacted(self, obj):
        return _redacted_attr(obj, 'motivo')

    @admin.display(description='efecto_esperado')
    def efecto_esperado_redacted(self, obj):
        return _redacted_attr(obj, 'efecto_esperado')

    @admin.display(description='evidencia_ref')
    def evidencia_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidencia_ref')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ObligacionTributariaMensual)
class ObligacionTributariaMensualAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'anio',
        'mes',
        'obligacion_tipo',
        'base_imponible',
        'monto_calculado',
        'estado_preparacion',
        'detalle_calculo_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('empresa', 'anio', 'mes', 'obligacion_tipo', 'monto_calculado', 'estado_preparacion')
    list_filter = ('obligacion_tipo', 'estado_preparacion')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='detalle_calculo')
    def detalle_calculo_redacted(self, obj):
        return _redacted_payload_attr(obj, 'detalle_calculo')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LedgerSnapshotAdminMixin(admin.ModelAdmin):
    fields = (
        'empresa',
        'periodo',
        'estado_snapshot',
        'storage_ref_redacted',
        'resumen_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('empresa', 'periodo', 'estado_snapshot', 'storage_ref_redacted')
    list_filter = ('estado_snapshot',)
    search_fields = ('empresa__razon_social', 'periodo')

    @admin.display(description='storage_ref')
    def storage_ref_redacted(self, obj):
        return _redacted_attr(obj, 'storage_ref')

    @admin.display(description='resumen')
    def resumen_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LibroDiario)
class LibroDiarioAdmin(LedgerSnapshotAdminMixin):
    pass


@admin.register(LibroMayor)
class LibroMayorAdmin(LedgerSnapshotAdminMixin):
    pass


@admin.register(BalanceComprobacion)
class BalanceComprobacionAdmin(LedgerSnapshotAdminMixin):
    pass


@admin.register(CierreMensualContable)
class CierreMensualContableAdmin(admin.ModelAdmin):
    fields = (
        'empresa',
        'anio',
        'mes',
        'estado',
        'fecha_preparacion',
        'fecha_aprobacion',
        'resumen_obligaciones_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = fields
    list_display = ('empresa', 'anio', 'mes', 'estado', 'fecha_preparacion', 'fecha_aprobacion')
    list_filter = ('estado', 'anio', 'mes')
    search_fields = ('empresa__razon_social',)

    @admin.display(description='resumen_obligaciones')
    def resumen_obligaciones_redacted(self, obj):
        return _redacted_payload_attr(obj, 'resumen_obligaciones')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
