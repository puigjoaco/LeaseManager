from django.contrib import admin

from .models import DocumentoEmitido, ExpedienteDocumental, PoliticaFirmaYNotaria


@admin.register(ExpedienteDocumental)
class ExpedienteDocumentalAdmin(admin.ModelAdmin):
    list_display = ('entidad_tipo', 'entidad_id', 'owner_operativo', 'estado')
    list_filter = ('estado', 'entidad_tipo')
    search_fields = ('entidad_tipo', 'entidad_id', 'owner_operativo')


@admin.register(DocumentoEmitido)
class DocumentoEmitidoAdmin(admin.ModelAdmin):
    list_display = ('expediente', 'tipo_documental', 'version_plantilla', 'estado', 'origen', 'fecha_carga')
    list_filter = ('tipo_documental', 'estado', 'origen')
    search_fields = ('checksum', 'storage_ref', 'version_plantilla')


@admin.register(PoliticaFirmaYNotaria)
class PoliticaFirmaYNotariaAdmin(admin.ModelAdmin):
    list_display = ('tipo_documental', 'modo_firma_permitido', 'requiere_notaria', 'estado')
    list_filter = ('estado', 'requiere_notaria', 'modo_firma_permitido')
    search_fields = ('tipo_documental',)

