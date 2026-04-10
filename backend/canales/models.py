from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from contratos.models import Arrendatario, Contrato
from documentos.models import DocumentoEmitido
from operacion.models import CanalOperacion, IdentidadDeEnvio


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoGateCanal(models.TextChoices):
    OPEN = 'abierto', 'Abierto'
    CONDITIONED = 'condicionado', 'Condicionado'
    CLOSED = 'cerrado', 'Cerrado'
    SUSPENDED = 'suspendido', 'Suspendido'


class EstadoMensajeSaliente(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    BLOCKED = 'bloqueado', 'Bloqueado'
    SENT = 'enviado', 'Enviado'
    FAILED = 'fallido', 'Fallido'


class CanalMensajeria(TimestampedModel):
    canal = models.CharField(max_length=16, choices=CanalOperacion.choices, unique=True)
    provider_key = models.CharField(max_length=64)
    estado_gate = models.CharField(max_length=16, choices=EstadoGateCanal.choices, default=EstadoGateCanal.CONDITIONED)
    restricciones_operativas = models.JSONField(default=dict, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['canal']

    def __str__(self):
        return self.canal


class MensajeSaliente(TimestampedModel):
    canal = models.CharField(max_length=16, choices=CanalOperacion.choices)
    canal_mensajeria = models.ForeignKey(
        CanalMensajeria,
        on_delete=models.PROTECT,
        related_name='mensajes_salientes',
    )
    identidad_envio = models.ForeignKey(
        IdentidadDeEnvio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mensajes_salientes',
    )
    contrato = models.ForeignKey(
        Contrato,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mensajes_salientes',
    )
    arrendatario = models.ForeignKey(
        Arrendatario,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mensajes_salientes',
    )
    documento_emitido = models.ForeignKey(
        DocumentoEmitido,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mensajes_salientes',
    )
    destinatario = models.CharField(max_length=255, blank=True)
    asunto = models.CharField(max_length=255, blank=True)
    cuerpo = models.TextField(blank=True)
    estado = models.CharField(max_length=16, choices=EstadoMensajeSaliente.choices, default=EstadoMensajeSaliente.DRAFT)
    motivo_bloqueo = models.TextField(blank=True)
    external_ref = models.CharField(max_length=255, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='mensajes_salientes',
    )
    provider_payload = models.JSONField(default=dict, blank=True)
    enviado_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(contrato__isnull=False)
                    | Q(arrendatario__isnull=False)
                    | Q(documento_emitido__isnull=False)
                ),
                name='mensaje_requiere_contexto',
            ),
        ]

    def __str__(self):
        return f'{self.canal} - {self.destinatario}'

    def clean(self):
        super().clean()
        if self.identidad_envio_id and self.identidad_envio.canal != self.canal:
            raise ValidationError({'identidad_envio': 'La identidad de envio debe pertenecer al mismo canal del mensaje.'})
        if self.canal_mensajeria.canal != self.canal:
            raise ValidationError({'canal_mensajeria': 'El gate configurado debe corresponder al mismo canal del mensaje.'})

