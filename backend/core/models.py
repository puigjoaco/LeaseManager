from django.conf import settings
from django.db import models


class Scope(models.Model):
    class ScopeType(models.TextChoices):
        GLOBAL = 'global', 'Global'
        COMPANY = 'company', 'Company'
        PROPERTY = 'property', 'Property'
        BANK_ACCOUNT = 'bank_account', 'Bank Account'

    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    scope_type = models.CharField(max_length=40, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    external_reference = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} ({self.code})'


class Role(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=True)
    scopes = models.ManyToManyField(Scope, through='RoleScope', related_name='roles')

    def __str__(self):
        return self.name


class RoleScope(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE)
    permission_set = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('role', 'scope')


class UserScopeAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scope_assignments')
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name='user_assignments')
    scope = models.ForeignKey(Scope, on_delete=models.PROTECT, null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    effective_from = models.DateTimeField(auto_now_add=True)
    effective_to = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'role', 'scope')


class PlatformSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    is_secret_reference = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key
