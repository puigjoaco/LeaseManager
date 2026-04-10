from django.contrib import admin

from .models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    Contrato,
    ContratoPropiedad,
    PeriodoContractual,
)


@admin.register(Arrendatario)
class ArrendatarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_razon_social', 'rut', 'tipo_arrendatario', 'estado_contacto', 'whatsapp_bloqueado')
    list_filter = ('tipo_arrendatario', 'estado_contacto', 'whatsapp_bloqueado')
    search_fields = ('nombre_razon_social', 'rut', 'email')


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('codigo_contrato', 'arrendatario', 'mandato_operacion', 'estado', 'fecha_inicio', 'fecha_fin_vigente')
    list_filter = ('estado', 'tiene_tramos', 'tiene_gastos_comunes')
    search_fields = ('codigo_contrato', 'arrendatario__nombre_razon_social')


@admin.register(ContratoPropiedad)
class ContratoPropiedadAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'propiedad', 'rol_en_contrato', 'codigo_conciliacion_efectivo_snapshot')
    list_filter = ('rol_en_contrato',)
    search_fields = ('contrato__codigo_contrato', 'propiedad__codigo_propiedad')


@admin.register(PeriodoContractual)
class PeriodoContractualAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'numero_periodo', 'fecha_inicio', 'fecha_fin', 'monto_base', 'moneda_base')
    list_filter = ('moneda_base',)
    search_fields = ('contrato__codigo_contrato',)


@admin.register(CodeudorSolidario)
class CodeudorSolidarioAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'fecha_inclusion', 'estado')
    list_filter = ('estado',)
    search_fields = ('contrato__codigo_contrato',)


@admin.register(AvisoTermino)
class AvisoTerminoAdmin(admin.ModelAdmin):
    list_display = ('contrato', 'fecha_efectiva', 'causal', 'estado', 'registrado_por')
    list_filter = ('estado',)
    search_fields = ('contrato__codigo_contrato', 'causal')

