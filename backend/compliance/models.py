from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


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
        if not self.hold_activo and self.estado == EstadoExportacionSensible.PREPARED and self.expires_at <= self.created_at:
            raise ValidationError({'expires_at': 'La exportacion preparada debe expirar en el futuro.'})

