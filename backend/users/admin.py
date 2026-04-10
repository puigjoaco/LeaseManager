from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class LeaseManagerUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'display_name', 'default_role_code', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        (
            'LeaseManager',
            {
                'fields': (
                    'display_name',
                    'default_role_code',
                    'legacy_reference',
                    'is_service_account',
                    'metadata',
                )
            },
        ),
    )

