from django.contrib import admin

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
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
    list_display = ('evento_tipo', 'empresa', 'fecha_operativa', 'monto_base', 'estado_contable')
    list_filter = ('estado_contable', 'evento_tipo', 'moneda')
    search_fields = ('idempotency_key', 'entidad_origen_tipo', 'entidad_origen_id')


@admin.register(AsientoContable)
class AsientoContableAdmin(admin.ModelAdmin):
    list_display = ('id', 'evento_contable', 'fecha_contable', 'periodo_contable', 'debe_total', 'haber_total', 'estado')
    list_filter = ('estado', 'periodo_contable')
    search_fields = ('evento_contable__idempotency_key',)


@admin.register(MovimientoAsiento)
class MovimientoAsientoAdmin(admin.ModelAdmin):
    list_display = ('asiento_contable', 'cuenta_contable', 'tipo_movimiento', 'monto')
    list_filter = ('tipo_movimiento',)
    search_fields = ('asiento_contable__id', 'cuenta_contable__codigo', 'glosa')


@admin.register(PoliticaReversoContable)
class PoliticaReversoContableAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tipo_ajuste', 'usa_reverso', 'usa_asiento_complementario', 'permite_reapertura', 'estado')
    list_filter = ('estado', 'usa_reverso', 'permite_reapertura')
    search_fields = ('empresa__razon_social', 'tipo_ajuste')


@admin.register(ObligacionTributariaMensual)
class ObligacionTributariaMensualAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'anio', 'mes', 'obligacion_tipo', 'monto_calculado', 'estado_preparacion')
    list_filter = ('obligacion_tipo', 'estado_preparacion')
    search_fields = ('empresa__razon_social',)


@admin.register(LibroDiario)
class LibroDiarioAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'periodo', 'estado_snapshot', 'storage_ref')
    list_filter = ('estado_snapshot',)
    search_fields = ('empresa__razon_social', 'periodo')


@admin.register(LibroMayor)
class LibroMayorAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'periodo', 'estado_snapshot', 'storage_ref')
    list_filter = ('estado_snapshot',)
    search_fields = ('empresa__razon_social', 'periodo')


@admin.register(BalanceComprobacion)
class BalanceComprobacionAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'periodo', 'estado_snapshot', 'storage_ref')
    list_filter = ('estado_snapshot',)
    search_fields = ('empresa__razon_social', 'periodo')


@admin.register(CierreMensualContable)
class CierreMensualContableAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'anio', 'mes', 'estado', 'fecha_preparacion', 'fecha_aprobacion')
    list_filter = ('estado', 'anio', 'mes')
    search_fields = ('empresa__razon_social',)
