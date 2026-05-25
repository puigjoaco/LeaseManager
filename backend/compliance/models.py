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

    def clean(self):
        super().clean()
        errors = {}
        reference_time = self.created_at or timezone.now()
        if not self.hold_activo and self.estado == EstadoExportacionSensible.PREPARED and self.expires_at <= reference_time:
            errors['expires_at'] = 'La exportacion preparada debe expirar en el futuro.'
        if contains_sensitive_reference(self.motivo, include_sensitive_keys=True):
            errors['motivo'] = 'El motivo no puede contener URLs, correos, tokens, bearer, claves ni credenciales.'
        if contains_sensitive_reference(self.scope_resumen, include_sensitive_keys=True):
            errors['scope_resumen'] = 'El scope de exportacion no puede contener referencias sensibles.'
        if errors:
            raise ValidationError(errors)
