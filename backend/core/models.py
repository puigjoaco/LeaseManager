import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


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


class RuntimeSignalKey(models.TextChoices):
    MONTHLY_CALCULATION_LATENCY = 'monthly_calculation_latency', 'Latencia de calculo mensual'
    QUEUE_RUNTIME = 'queue_runtime', 'Colas y tareas'
    FAILED_WEBHOOKS = 'failed_webhooks', 'Webhooks fallidos'
    FAILED_CRONS = 'failed_crons', 'Crons fallidos'


class RuntimeSignalStatus(models.TextChoices):
    OK = 'ok', 'OK'
    ATTENTION = 'attention', 'Atencion'
    MISSING = 'missing', 'Faltante'


class RuntimeSignalSourceKind(models.TextChoices):
    LOCAL = 'local', 'Local'
    FIXTURE = 'fixture', 'Fixture'
    DEMO = 'demo', 'Demo'
    SNAPSHOT_CONTROLADO = 'snapshot_controlado', 'Snapshot controlado'
    REAL_AUTORIZADO = 'real_autorizado', 'Real autorizado'


def _numeric_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


SENSITIVE_EVIDENCE_REF_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
)


class OperationalRuntimeSignal(models.Model):
    signal_key = models.CharField(max_length=64, choices=RuntimeSignalKey.choices, unique=True)
    status = models.CharField(
        max_length=16,
        choices=RuntimeSignalStatus.choices,
        default=RuntimeSignalStatus.MISSING,
    )
    source_kind = models.CharField(
        max_length=32,
        choices=RuntimeSignalSourceKind.choices,
        default=RuntimeSignalSourceKind.LOCAL,
    )
    value = models.JSONField(default=dict, blank=True)
    evidence_ref = models.CharField(max_length=255, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['signal_key']

    def __str__(self):
        return f'{self.signal_key} - {self.status}'

    def clean(self):
        super().clean()
        if self.status == RuntimeSignalStatus.OK and not self.evidence_ref.strip():
            raise ValidationError({'evidence_ref': 'Una senal runtime OK requiere evidencia_ref trazable.'})
        if self.evidence_ref and SENSITIVE_EVIDENCE_REF_PATTERN.search(self.evidence_ref):
            raise ValidationError({'evidence_ref': 'evidence_ref debe ser una referencia no sensible, no una URL, token o credencial.'})

        payload = self.value if isinstance(self.value, dict) else {}
        errors = {}
        if self.signal_key == RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY:
            duration = _numeric_value(payload.get('duration_ms'))
            if self.status == RuntimeSignalStatus.OK and (duration is None or duration < 0):
                errors['value'] = 'monthly_calculation_latency OK requiere duration_ms numerico no negativo.'
        elif self.signal_key == RuntimeSignalKey.QUEUE_RUNTIME:
            if self.status == RuntimeSignalStatus.OK and payload.get('healthy') is not True:
                errors['value'] = 'queue_runtime OK requiere healthy=true.'
        elif self.signal_key in {RuntimeSignalKey.FAILED_WEBHOOKS, RuntimeSignalKey.FAILED_CRONS}:
            failed_count = payload.get('failed_count')
            if (
                self.status == RuntimeSignalStatus.OK
                and (not isinstance(failed_count, int) or isinstance(failed_count, bool) or failed_count < 0)
            ):
                errors['value'] = f'{self.signal_key} OK requiere failed_count entero no negativo.'

        if errors:
            raise ValidationError(errors)
