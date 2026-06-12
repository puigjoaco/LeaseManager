from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.reference_validation import contains_sensitive_reference


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoRegistro(models.TextChoices):
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class CategoriaDato(models.TextChoices):
    OPERATIONAL = 'operativo', 'Operativo'
    FINANCIAL = 'financiero', 'Financiero'
    TAX = 'tributario', 'Tributario'
    DOCUMENT = 'documental_sensible', 'Documental sensible'
    SECRET = 'secreto', 'Secreto'


class EstadoExportacionSensible(models.TextChoices):
    PREPARED = 'preparada', 'Preparada'
    EXPIRED = 'expirada', 'Expirada'
    REVOKED = 'revocada', 'Revocada'


RETENTION_HOLD_REQUIRED_CATEGORIES = {
    CategoriaDato.TAX.value,
    CategoriaDato.DOCUMENT.value,
}
RETENTION_NO_PHYSICAL_PURGE_CATEGORIES = {
    CategoriaDato.DOCUMENT.value,
    CategoriaDato.SECRET.value,
}
SECRET_EXPORT_ERROR = 'No se permite preparar exportaciones operativas sobre categoria secreto.'
EXPORT_MOTIVE_REQUIRED_ERROR = 'La exportacion sensible requiere un motivo operativo trazable.'
EXPORT_CREATED_BY_REQUIRED_ERROR = 'La exportacion sensible requiere actor creador trazable.'
EXPIRED_EXPORT_STATE_ERROR = 'La exportacion expirada debe representar una exportacion ya vencida sin hold activo.'
PAYLOAD_HASH_FORMAT_ERROR = 'payload_hash debe ser un digest SHA-256 hexadecimal de 64 caracteres.'
SENSITIVE_EXPORT_MAX_DAYS = 30
MAX_EXPORT_WINDOW_ERROR = 'Las exportaciones sensibles sin hold no pueden exceder 30 dias de vigencia.'
ENCRYPTED_REF_SENSITIVE_ERROR = 'encrypted_ref debe ser una referencia no sensible, no una URL, token o credencial.'


def _normalize_text_value(value):
    if isinstance(value, str):
        return value.strip()
    return value


def _normalize_payload_strings(value):
    if isinstance(value, dict):
        return {key: _normalize_payload_strings(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_payload_strings(item) for item in value]
    return _normalize_text_value(value)


class PoliticaRetencionDatos(TimestampedModel):
    categoria_dato = models.CharField(max_length=32, choices=CategoriaDato.choices, unique=True)
    evento_inicio = models.CharField(max_length=64)
    plazo_minimo_anos = models.PositiveSmallIntegerField()
    permite_borrado_logico = models.BooleanField(default=True)
    permite_purga_fisica = models.BooleanField(default=False)
    requiere_hold = models.BooleanField(default=False)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['categoria_dato']

    def __str__(self):
        return self.categoria_dato

    def _normalize_operational_fields(self):
        self.evento_inicio = _normalize_text_value(self.evento_inicio)

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
        if self.plazo_minimo_anos is not None and self.plazo_minimo_anos <= 0:
            errors['plazo_minimo_anos'] = 'La politica de retencion requiere un plazo minimo mayor a cero.'
        if contains_sensitive_reference(self.evento_inicio, include_sensitive_keys=True):
            errors['evento_inicio'] = (
                'El evento de inicio no puede contener URLs, correos, tokens, bearer, claves ni credenciales.'
            )
        if self.categoria_dato in RETENTION_HOLD_REQUIRED_CATEGORIES and not self.requiere_hold:
            errors['requiere_hold'] = 'Las categorias tributaria y documental sensible requieren hold operativo.'
        if self.categoria_dato in RETENTION_NO_PHYSICAL_PURGE_CATEGORIES and self.permite_purga_fisica:
            errors['permite_purga_fisica'] = 'Las categorias documental sensible y secreto no permiten purga fisica por defecto.'
        if errors:
            raise ValidationError(errors)


class ExportacionSensible(TimestampedModel):
    categoria_dato = models.CharField(max_length=32, choices=CategoriaDato.choices)
    export_kind = models.CharField(max_length=64)
    scope_resumen = models.JSONField(default=dict, blank=True)
    motivo = models.TextField()
    encrypted_payload = models.TextField()
    payload_hash = models.CharField(max_length=64)
    encrypted_ref = models.CharField(max_length=255, blank=True)
    expires_at = models.DateTimeField()
    hold_activo = models.BooleanField(default=False)
    estado = models.CharField(max_length=16, choices=EstadoExportacionSensible.choices, default=EstadoExportacionSensible.PREPARED)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='exports_sensibles_creados',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.export_kind} {self.created_at.isoformat()}'

    def _normalize_operational_fields(self, *, include_motivo=True):
        if include_motivo:
            self.motivo = _normalize_text_value(self.motivo)
        self.payload_hash = _normalize_text_value(self.payload_hash)
        if isinstance(self.payload_hash, str):
            self.payload_hash = self.payload_hash.lower()
        self.encrypted_ref = _normalize_text_value(self.encrypted_ref)
        self.scope_resumen = _normalize_payload_strings(self.scope_resumen)

    def full_clean(self, exclude=None, validate_unique=True, validate_constraints=True):
        self._normalize_operational_fields(include_motivo=False)
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
        self.motivo = _normalize_text_value(self.motivo)
        errors = {}
        reference_time = self.created_at or timezone.now()
        if not self.hold_activo and self.estado == EstadoExportacionSensible.PREPARED and self.expires_at <= reference_time:
            errors['expires_at'] = 'La exportacion preparada debe expirar en el futuro.'
        if (
            not self.hold_activo
            and self.estado == EstadoExportacionSensible.PREPARED
            and self.expires_at
            and self.expires_at - reference_time > timedelta(days=SENSITIVE_EXPORT_MAX_DAYS)
        ):
            errors['expires_at'] = MAX_EXPORT_WINDOW_ERROR
        if self.estado == EstadoExportacionSensible.EXPIRED:
            if self.hold_activo:
                errors['hold_activo'] = EXPIRED_EXPORT_STATE_ERROR
            if self.expires_at and self.expires_at > reference_time:
                errors['expires_at'] = EXPIRED_EXPORT_STATE_ERROR
        payload_hash = str(self.payload_hash or '').strip()
        if len(payload_hash) != 64 or any(char not in '0123456789abcdefABCDEF' for char in payload_hash):
            errors['payload_hash'] = PAYLOAD_HASH_FORMAT_ERROR
        if self.categoria_dato == CategoriaDato.SECRET:
            errors['categoria_dato'] = SECRET_EXPORT_ERROR
        if not str(self.motivo or '').strip():
            errors['motivo'] = EXPORT_MOTIVE_REQUIRED_ERROR
        if not self.created_by_id:
            errors['created_by'] = EXPORT_CREATED_BY_REQUIRED_ERROR
        if contains_sensitive_reference(self.motivo, include_sensitive_keys=True):
            errors['motivo'] = 'El motivo no puede contener URLs, correos, tokens, bearer, claves ni credenciales.'
        if contains_sensitive_reference(self.scope_resumen, include_sensitive_keys=True):
            errors['scope_resumen'] = 'El scope de exportacion no puede contener referencias sensibles.'
        if self.encrypted_ref and contains_sensitive_reference(self.encrypted_ref, include_sensitive_keys=True):
            errors['encrypted_ref'] = ENCRYPTED_REF_SENSITIVE_ERROR
        if errors:
            raise ValidationError(errors)
