from django.contrib import admin

from .models import (
    AjusteContrato,
    CodigoCobroResidual,
    EstadoCuentaArrendatario,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
)


@admin.register(ValorUFDiario)
class ValorUFDiarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'valor', 'source_key')
    list_filter = ('source_key',)
    search_fields = ('source_key',)


@admin.register(AjusteContrato)
class AjusteContratoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'tipo_ajuste', 'monto', 'moneda', 'mes_inicio', 'mes_fin', 'activo')
    list_filter = ('moneda', 'activo')
    search_fields = ('contrato__codigo_contrato', 'tipo_ajuste')


@admin.register(PagoMensual)
class PagoMensualAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'anio', 'mes', 'monto_calculado_clp', 'estado_pago', 'dias_mora')
    list_filter = ('estado_pago', 'anio', 'mes')
    search_fields = ('contrato__codigo_contrato',)


@admin.register(GarantiaContractual)
class GarantiaContractualAdmin(admin.ModelAdmin):
    list_display = (
        'contrato',
        'monto_pactado',
        'monto_recibido',
        'monto_devuelto',
        'monto_aplicado',
        'estado_garantia',
    )
    list_filter = ('estado_garantia',)
    search_fields = ('contrato__codigo_contrato',)


@admin.register(HistorialGarantia)
class HistorialGarantiaAdmin(admin.ModelAdmin):
    list_display = ('garantia_contractual', 'tipo_movimiento', 'monto_clp', 'fecha')
    list_filter = ('tipo_movimiento',)
    search_fields = ('garantia_contractual__contrato__codigo_contrato',)


@admin.register(RepactacionDeuda)
class RepactacionDeudaAdmin(admin.ModelAdmin):
    list_display = ('arrendatario', 'contrato_origen', 'deuda_total_original', 'saldo_pendiente', 'estado')
    list_filter = ('estado',)
    search_fields = ('arrendatario__nombre_razon_social', 'contrato_origen__codigo_contrato')


@admin.register(CodigoCobroResidual)
class CodigoCobroResidualAdmin(admin.ModelAdmin):
    list_display = ('referencia_visible', 'arrendatario', 'contrato_origen', 'saldo_actual', 'estado')
    list_filter = ('estado',)
    search_fields = ('referencia_visible', 'arrendatario__nombre_razon_social', 'contrato_origen__codigo_contrato')


@admin.register(EstadoCuentaArrendatario)
class EstadoCuentaArrendatarioAdmin(admin.ModelAdmin):
    list_display = ('arrendatario', 'score_pago', 'updated_at')
    search_fields = ('arrendatario__nombre_razon_social', 'arrendatario__rut')
