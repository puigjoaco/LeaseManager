import json

from django.contrib import admin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import OperationalRuntimeSignal, PlatformSetting, Role, RoleScope, Scope, UserScopeAssignment


def _redacted_attr(obj, field_name):
    return redact_sensitive_reference(getattr(obj, field_name, '')) or ''


def _redacted_payload_attr(obj, field_name):
    return json.dumps(
        redact_sensitive_payload(getattr(obj, field_name, None) or {}),
        ensure_ascii=True,
        sort_keys=True,
    )


@admin.register(Scope)
class ScopeAdmin(admin.ModelAdmin):
    fields = ('code', 'name', 'scope_type', 'external_reference_redacted', 'metadata_redacted', 'is_active', 'created_at')
    readonly_fields = ('external_reference_redacted', 'metadata_redacted', 'created_at')
    list_display = ('code', 'name', 'scope_type', 'external_reference_redacted', 'is_active')
    list_filter = ('scope_type', 'is_active')
    search_fields = ('code', 'name', 'scope_type')

    @admin.display(description='external_reference')
    def external_reference_redacted(self, obj):
        return _redacted_attr(obj, 'external_reference')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_system_role')
    list_filter = ('is_system_role',)
    search_fields = ('code', 'name')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RoleScope)
class RoleScopeAdmin(admin.ModelAdmin):
    fields = ('role', 'scope', 'permission_set_redacted')
    readonly_fields = ('permission_set_redacted',)
    list_display = ('role', 'scope', 'permission_set_redacted')
    search_fields = ('role__code', 'scope__code', 'scope__name')

    @admin.display(description='permission_set')
    def permission_set_redacted(self, obj):
        return _redacted_payload_attr(obj, 'permission_set')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UserScopeAssignment)
class UserScopeAssignmentAdmin(admin.ModelAdmin):
    fields = ('user', 'role', 'scope', 'is_primary', 'metadata_redacted', 'effective_from', 'effective_to')
    readonly_fields = ('metadata_redacted', 'effective_from')
    list_display = ('user', 'role', 'scope', 'is_primary', 'effective_from', 'effective_to')
    list_filter = ('is_primary', 'role')
    search_fields = ('user__username', 'user__email', 'role__code', 'scope__code', 'scope__name')

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return _redacted_payload_attr(obj, 'metadata')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    fields = ('key', 'value_redacted', 'description', 'is_secret_reference', 'is_active', 'updated_at')
    readonly_fields = ('value_redacted', 'updated_at')
    list_display = ('key', 'is_secret_reference', 'is_active', 'updated_at')
    list_filter = ('is_secret_reference', 'is_active')
    search_fields = ('key', 'description')

    @admin.display(description='value')
    def value_redacted(self, obj):
        return _redacted_payload_attr(obj, 'value')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OperationalRuntimeSignal)
class OperationalRuntimeSignalAdmin(admin.ModelAdmin):
    fields = (
        'signal_key',
        'status',
        'source_kind',
        'value_redacted',
        'evidence_ref_redacted',
        'source_label_redacted',
        'authorization_ref_redacted',
        'observed_at',
        'notes_redacted',
        'updated_at',
    )
    readonly_fields = (
        'value_redacted',
        'evidence_ref_redacted',
        'source_label_redacted',
        'authorization_ref_redacted',
        'notes_redacted',
        'updated_at',
    )
    list_display = ('signal_key', 'status', 'source_kind', 'evidence_ref_redacted', 'observed_at', 'updated_at')
    list_filter = ('status', 'source_kind', 'signal_key')
    search_fields = ('signal_key', 'status', 'source_kind')

    @admin.display(description='value')
    def value_redacted(self, obj):
        return _redacted_payload_attr(obj, 'value')

    @admin.display(description='evidence_ref')
    def evidence_ref_redacted(self, obj):
        return _redacted_attr(obj, 'evidence_ref')

    @admin.display(description='source_label')
    def source_label_redacted(self, obj):
        return _redacted_attr(obj, 'source_label')

    @admin.display(description='authorization_ref')
    def authorization_ref_redacted(self, obj):
        return _redacted_attr(obj, 'authorization_ref')

    @admin.display(description='notes')
    def notes_redacted(self, obj):
        return _redacted_attr(obj, 'notes')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
