from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .admin_security_control import ADMIN_SECURITY_SETTING_KEY, evaluate_admin_security_control
from .reference_validation import SENSITIVE_REFERENCE_PATTERN as SENSITIVE_EVIDENCE_REF_PATTERN
from .reference_validation import contains_sensitive_reference


ADMIN_SECURITY_TEXT_VALUE_FIELDS = {
    'mode',
    'mfa_evidence_ref',
    'risk_acceptance_ref',
    'authorization_ref',
    'responsible_ref',
    'valid_until',
    'risk_valid_until',
    'evidence_ref',
}


def _normalize_text_value(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_dict_text_fields(payload, field_names):
    if not isinstance(payload, dict):
        return payload
    normalized = dict(payload)
    for field_name in field_names:
        if field_name in normalized:
            normalized[field_name] = _normalize_text_value(normalized[field_name])
    return normalized


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

    def _normalize_operational_fields(self):
        if self.key == ADMIN_SECURITY_SETTING_KEY:
            self.description = _normalize_text_value(self.description)
            self.value = _normalize_dict_text_fields(self.value, ADMIN_SECURITY_TEXT_VALUE_FIELDS)

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        self._normalize_operational_fields()
        return super().full_clean(
            exclude=exclude,
            validate_unique=validate_unique,
            validate_constraints=validate_constraints,
        )

    def save(self, *args, **kwargs):
        self._normalize_operational_fields()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.key != ADMIN_SECURITY_SETTING_KEY:
            return

        if self.description and contains_sensitive_reference(self.description, include_sensitive_keys=True):
            raise ValidationError({'description': 'La descripcion del control administrativo debe ser no sensible.'})

        _payload, issues = evaluate_admin_security_control(
            self.value,
            setting_present=True,
        )
        if issues:
            raise ValidationError({'value': [issue['message'] for issue in issues]})


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


AUTHORIZED_RUNTIME_SIGNAL_MODEL_SOURCE_KINDS = {
    RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
    RuntimeSignalSourceKind.REAL_AUTORIZADO,
}


def _non_sensitive_reference(value):
    normalized = str(value or '').strip()
    return bool(normalized) and not SENSITIVE_EVIDENCE_REF_PATTERN.search(normalized)


def _contains_sensitive_reference(value):
    return contains_sensitive_reference(value, include_sensitive_keys=True)


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
    source_label = models.CharField(max_length=255, blank=True)
    authorization_ref = models.CharField(max_length=255, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['signal_key']

    def __str__(self):
        return f'{self.signal_key} - {self.status}'

    def _normalize_operational_fields(self):
        for field_name in ('evidence_ref', 'source_label', 'authorization_ref', 'notes'):
            setattr(self, field_name, _normalize_text_value(getattr(self, field_name)))

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        self._normalize_operational_fields()
        return super().full_clean(
            exclude=exclude,
            validate_unique=validate_unique,
            validate_constraints=validate_constraints,
        )

    def save(self, *args, **kwargs):
        self._normalize_operational_fields()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        if self.status == RuntimeSignalStatus.OK and not self.evidence_ref.strip():
            errors['evidence_ref'] = 'Una senal runtime OK requiere evidencia_ref trazable.'
        if self.evidence_ref and SENSITIVE_EVIDENCE_REF_PATTERN.search(self.evidence_ref):
            errors['evidence_ref'] = 'evidence_ref debe ser una referencia no sensible, no una URL, token o credencial.'
        if self.source_label and SENSITIVE_EVIDENCE_REF_PATTERN.search(self.source_label):
            errors['source_label'] = 'source_label debe ser una etiqueta no sensible.'
        if self.authorization_ref and SENSITIVE_EVIDENCE_REF_PATTERN.search(self.authorization_ref):
            errors['authorization_ref'] = 'authorization_ref debe ser una referencia no sensible.'
        if self.notes and SENSITIVE_EVIDENCE_REF_PATTERN.search(self.notes):
            errors['notes'] = 'notes debe ser una nota operativa no sensible.'
        if (
            self.status == RuntimeSignalStatus.OK
            and self.source_kind in AUTHORIZED_RUNTIME_SIGNAL_MODEL_SOURCE_KINDS
        ):
            if not _non_sensitive_reference(self.source_label):
                errors['source_label'] = 'Una senal runtime autorizada requiere source_label no sensible.'
            if not _non_sensitive_reference(self.authorization_ref):
                errors['authorization_ref'] = 'Una senal runtime autorizada requiere authorization_ref no sensible.'

        payload = self.value if isinstance(self.value, dict) else {}
        if _contains_sensitive_reference(payload):
            errors['value'] = 'value no debe contener URLs, tokens, credenciales ni referencias sensibles.'
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
