import json

from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import ExportacionSensible, PoliticaRetencionDatos


@admin.register(PoliticaRetencionDatos)
class PoliticaRetencionDatosAdmin(admin.ModelAdmin):
    list_display = ('categoria_dato', 'evento_inicio_redacted', 'plazo_minimo_anos', 'requiere_hold', 'estado')
    list_filter = ('estado', 'requiere_hold')
    search_fields = ('categoria_dato',)
    fields = (
        'categoria_dato',
        'evento_inicio_redacted',
        'plazo_minimo_anos',
        'permite_borrado_logico',
        'permite_purga_fisica',
        'requiere_hold',
        'estado',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'categoria_dato',
        'evento_inicio_redacted',
        'plazo_minimo_anos',
        'permite_borrado_logico',
        'permite_purga_fisica',
        'requiere_hold',
        'estado',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Evento inicio redacted')
    def evento_inicio_redacted(self, obj):
        return redact_sensitive_reference(obj.evento_inicio) or ''


@admin.register(ExportacionSensible)
class ExportacionSensibleAdmin(admin.ModelAdmin):
    list_display = ('export_kind', 'categoria_dato', 'estado', 'expires_at', 'hold_activo', 'created_by')
    list_filter = ('estado', 'categoria_dato', 'hold_activo')
    search_fields = ('export_kind', 'payload_hash')
    fields = (
        'categoria_dato',
        'export_kind',
        'scope_resumen_redacted',
        'motivo_redacted',
        'payload_hash',
        'encrypted_ref_redacted',
        'expires_at',
        'hold_activo',
        'estado',
        'created_by',
        'created_at',
        'updated_at',
    )
    readonly_fields = (
        'categoria_dato',
        'export_kind',
        'scope_resumen_redacted',
        'motivo_redacted',
        'payload_hash',
        'encrypted_ref_redacted',
        'expires_at',
        'hold_activo',
        'estado',
        'created_by',
        'created_at',
        'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Scope redacted')
    def scope_resumen_redacted(self, obj):
        return json.dumps(redact_sensitive_payload(obj.scope_resumen or {}), ensure_ascii=True, sort_keys=True)

    @admin.display(description='Motivo redacted')
    def motivo_redacted(self, obj):
        return redact_sensitive_reference(obj.motivo) or ''

    @admin.display(description='Encrypted ref redacted')
    def encrypted_ref_redacted(self, obj):
        return redact_sensitive_reference(obj.encrypted_ref) or ''

