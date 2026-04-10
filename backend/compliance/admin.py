from django.contrib import admin

from .models import ExportacionSensible, PoliticaRetencionDatos


@admin.register(PoliticaRetencionDatos)
class PoliticaRetencionDatosAdmin(admin.ModelAdmin):
    list_display = ('categoria_dato', 'plazo_minimo_anos', 'requiere_hold', 'estado')
    list_filter = ('estado', 'requiere_hold')
    search_fields = ('categoria_dato', 'evento_inicio')


@admin.register(ExportacionSensible)
class ExportacionSensibleAdmin(admin.ModelAdmin):
    list_display = ('export_kind', 'categoria_dato', 'estado', 'expires_at', 'hold_activo', 'created_by')
    list_filter = ('estado', 'categoria_dato', 'hold_activo')
    search_fields = ('export_kind', 'payload_hash', 'encrypted_ref')

