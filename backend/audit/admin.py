import json

from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import AuditEvent, ManualResolution


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


def _redacted_payload_attr(obj, field_name):
    return json.dumps(
        redact_sensitive_payload(getattr(obj, field_name, None) or {}),
        ensure_ascii=True,
        sort_keys=True,
    )


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    fields = (
        'actor_user',
        'actor_identifier_redacted',
        'event_type',
        'severity',
        'entity_type',
        'entity_id_redacted',
        'summary_redacted',
        'metadata_redacted',
        'request_id_redacted',
        'ip_address_redacted',
        'created_at',
    )
    readonly_fields = fields
    list_display = (
        'event_type',
        'severity',
        'entity_type',
        'entity_id_redacted',
        'summary_redacted',
        'actor_user',
        'created_at',
    )
    list_filter = ('severity', 'entity_type', 'event_type')
    search_fields = ('event_type', 'entity_type')

    @admin.display(description='actor_identifier')
    def actor_identifier_redacted(self, obj):
        return _redacted_attr(obj, 'actor_identifier')

    @admin.display(description='entity_id')
    def entity_id_redacted(self, obj):
        return _redacted_attr(obj, 'entity_id')

    @admin.display(description='summary')
    def summary_redacted(self, obj):
        return _redacted_attr(obj, 'summary')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    @admin.display(description='request_id')
    def request_id_redacted(self, obj):
        return _redacted_attr(obj, 'request_id')

    @admin.display(description='ip_address')
    def ip_address_redacted(self, obj):
        return _redacted_attr(obj, 'ip_address')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ManualResolution)
class ManualResolutionAdmin(admin.ModelAdmin):
    fields = (
        'id',
        'category',
        'status',
        'scope_type',
        'scope_reference_redacted',
        'summary_redacted',
        'rationale_redacted',
        'requested_by',
        'resolved_by',
        'metadata_redacted',
        'created_at',
        'resolved_at',
    )
    readonly_fields = fields
    list_display = (
        'category',
        'status',
        'scope_type',
        'scope_reference_redacted',
        'summary_redacted',
        'created_at',
    )
    list_filter = ('status', 'category', 'scope_type')
    search_fields = ('category', 'scope_type')

    @admin.display(description='scope_reference')
    def scope_reference_redacted(self, obj):
        return _redacted_attr(obj, 'scope_reference')

    @admin.display(description='summary')
    def summary_redacted(self, obj):
        return _redacted_attr(obj, 'summary')

    @admin.display(description='rationale')
    def rationale_redacted(self, obj):
        return _redacted_attr(obj, 'rationale')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
