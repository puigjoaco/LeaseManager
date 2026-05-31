import json

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference

from .models import User


@admin.register(User)
class LeaseManagerUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'display_name', 'default_role_code', 'is_staff', 'is_active')
    readonly_fields = UserAdmin.readonly_fields + ('legacy_reference_redacted', 'metadata_redacted')
    fieldsets = UserAdmin.fieldsets + (
        (
            'LeaseManager',
            {
                'fields': (
                    'display_name',
                    'default_role_code',
                    'legacy_reference_redacted',
                    'is_service_account',
                    'metadata_redacted',
                )
            },
        ),
    )

    @admin.display(description='legacy_reference')
    def legacy_reference_redacted(self, obj):
        return redact_sensitive_reference(obj.legacy_reference) or ''

    @admin.display(description='metadata')
    def metadata_redacted(self, obj):
        return json.dumps(redact_sensitive_payload(obj.metadata or {}), sort_keys=True, ensure_ascii=True)

    def has_delete_permission(self, request, obj=None):
        return False
