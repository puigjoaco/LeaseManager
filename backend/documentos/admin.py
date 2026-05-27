from django.contrib import admin

from core.reference_validation import redact_sensitive_reference

from .models import DocumentoEmitido, ExpedienteDocumental, PoliticaFirmaYNotaria


@admin.register(ExpedienteDocumental)
class ExpedienteDocumentalAdmin(admin.ModelAdmin):
    list_display = ('entidad_tipo', 'entidad_id', 'owner_operativo', 'estado')
    list_filter = ('estado', 'entidad_tipo')
    search_fields = ('entidad_tipo', 'entidad_id', 'owner_operativo')


@admin.register(DocumentoEmitido)
class DocumentoEmitidoAdmin(admin.ModelAdmin):
    list_display = (
        'expediente',
        'tipo_documental',
        'version_plantilla',
        'estado',
        'origen',
        'fecha_carga',
        'documento_origen',
    )
    list_filter = ('tipo_documental', 'estado', 'origen')
    search_fields = ('checksum', 'version_plantilla')
    fields = (
        'expediente',
        'tipo_documental',
        'version_plantilla',
        'checksum',
        'fecha_carga',
        'usuario',
        'origen',
        'estado',
        'storage_ref_redacted',
        'firma_arrendador_registrada',
        'firma_arrendatario_registrada',
        'firma_codeudor_registrada',
        'recepcion_notarial_registrada',
        'evidencia_formalizacion_ref_redacted',
        'comprobante_notarial',
        'documento_origen',
        'correccion_ref_redacted',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'storage_ref_redacted',
        'evidencia_formalizacion_ref_redacted',
        'correccion_ref_redacted',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Storage ref redacted')
    def storage_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.storage_ref) or ''

    @admin.display(description='Evidencia formalizacion ref redacted')
    def evidencia_formalizacion_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.evidencia_formalizacion_ref) or ''

    @admin.display(description='Correccion ref redacted')
    def correccion_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.correccion_ref) or ''


@admin.register(PoliticaFirmaYNotaria)
class PoliticaFirmaYNotariaAdmin(admin.ModelAdmin):
    list_display = (
        'tipo_documental',
        'modo_firma_permitido',
        'requiere_notaria',
        'requiere_nacionalidad_arrendatario',
        'requiere_estado_civil_arrendatario',
        'requiere_profesion_arrendatario',
        'estado',
    )
    list_filter = (
        'estado',
        'requiere_notaria',
        'requiere_nacionalidad_arrendatario',
        'requiere_estado_civil_arrendatario',
        'requiere_profesion_arrendatario',
        'modo_firma_permitido',
    )
    search_fields = ('tipo_documental',)

