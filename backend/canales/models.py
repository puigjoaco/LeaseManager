from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from contratos.models import Arrendatario, Contrato
from documentos.models import DocumentoEmitido
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from operacion.models import (
    AsignacionCanalOperacion,
    CanalOperacion,
    EstadoAsignacionCanal,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
)


EMAIL_READINESS_REF_KEYS = ('prueba_aislada_ref', 'prueba_envio_ref')
EMAIL_CREDENTIAL_REF_KEYS = ('oauth_validado_ref', 'credencial_validada_ref')
NOTIFICATION_BASE_SUGGESTED_DAYS = (1, 3, 5, 10, 15, 20, 25)


def normalize_notification_days(value):
    if value in (None, ''):
        return []
    if not isinstance(value, (list, tuple)):
        raise ValueError('dias_notificacion debe ser una lista de dias.')

    normalized = []
    seen = set()
    for raw_day in value:
        if isinstance(raw_day, bool):
            raise ValueError('dias_notificacion debe contener enteros entre 1 y 31.')
        if isinstance(raw_day, int):
            day = raw_day
        elif isinstance(raw_day, str) and raw_day.strip().isdigit():
            day = int(raw_day.strip())
        else:
            raise ValueError('dias_notificacion debe contener enteros entre 1 y 31.')
        if day < 1 or day > 31:
            raise ValueError('dias_notificacion debe contener enteros entre 1 y 31.')
        if day in seen:
            raise ValueError('dias_notificacion no debe contener dias duplicados.')
        seen.add(day)
        normalized.append(day)
    return sorted(normalized)


def has_non_sensitive_operational_ref(restrictions, keys):
    restrictions = restrictions or {}
    return any(is_non_sensitive_reference(restrictions.get(key, '')) for key in keys)


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

    def clean(self):
        super().clean()
        if self.evidencia_ref.strip() and not is_non_sensitive_reference(self.evidencia_ref):
            raise ValidationError({'evidencia_ref': 'evidencia_ref debe ser una referencia no sensible.'})
        if contains_sensitive_reference(self.restricciones_operativas):
            raise ValidationError(
                {
                    'restricciones_operativas': (
                        'restricciones_operativas no debe contener URLs, tokens, credenciales ni correos.'
                    )
                }
            )
        if self.canal == CanalOperacion.EMAIL and self.estado_gate == EstadoGateCanal.OPEN:
            if not self.evidencia_ref.strip():
                raise ValidationError({'evidencia_ref': 'Email abierto requiere evidencia_ref del gate.'})
            if not has_non_sensitive_operational_ref(self.restricciones_operativas, EMAIL_READINESS_REF_KEYS):
                raise ValidationError(
                    {
                        'restricciones_operativas': (
                            'Email abierto requiere prueba_aislada_ref o prueba_envio_ref trazable no sensible.'
                        )
                    }
                )
            if not has_non_sensitive_operational_ref(self.restricciones_operativas, EMAIL_CREDENTIAL_REF_KEYS):
                raise ValidationError(
                    {
                        'restricciones_operativas': (
                            'Email abierto requiere oauth_validado_ref o credencial_validada_ref trazable no sensible.'
                        )
                    }
                )


class ConfiguracionNotificacionContrato(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='configuraciones_notificacion',
    )
    canal = models.CharField(max_length=16, choices=CanalOperacion.choices)
    dias_notificacion = models.JSONField(default=list, blank=True)
    activa = models.BooleanField(default=True)
    evidencia_configuracion_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['contrato_id', 'canal', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'canal'],
                condition=Q(activa=True),
                name='uniq_config_notificacion_activa_por_contrato_canal',
            ),
        ]

    def __str__(self):
        return f'{self.contrato_id} - {self.canal} - {self.dias_notificacion}'

    @property
    def uses_base_suggested_days(self):
        return tuple(self.dias_notificacion or []) == NOTIFICATION_BASE_SUGGESTED_DAYS

    def has_enabled_channel_assignment(self):
        if not self.contrato_id:
            return False
        return AsignacionCanalOperacion.objects.filter(
            mandato_operacion=self.contrato.mandato_operacion,
            canal=self.canal,
            estado=EstadoAsignacionCanal.ACTIVE,
            identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
            mandato_operacion__estado=EstadoMandatoOperacion.ACTIVE,
        ).exists()

    def clean(self):
        super().clean()
        try:
            self.dias_notificacion = normalize_notification_days(self.dias_notificacion)
        except ValueError as error:
            raise ValidationError({'dias_notificacion': str(error)})

        if self.activa and not self.dias_notificacion:
            raise ValidationError({'dias_notificacion': 'La configuracion activa requiere al menos un dia.'})

        if (
            self.evidencia_configuracion_ref.strip()
            and not is_non_sensitive_reference(self.evidencia_configuracion_ref)
        ):
            raise ValidationError(
                {'evidencia_configuracion_ref': 'evidencia_configuracion_ref debe ser una referencia no sensible.'}
            )

        if self.activa and tuple(self.dias_notificacion) != NOTIFICATION_BASE_SUGGESTED_DAYS:
            if not self.evidencia_configuracion_ref.strip():
                raise ValidationError(
                    {
                        'evidencia_configuracion_ref': (
                            'Una cadencia distinta de la base 1/3/5/10/15/20/25 requiere referencia no sensible.'
                        )
                    }
                )

        if self.activa and self.contrato_id and not self.has_enabled_channel_assignment():
            raise ValidationError(
                {'canal': 'La configuracion activa requiere canal habilitado en el mandato del contrato.'}
            )

    def save(self, *args, **kwargs):
        self.dias_notificacion = normalize_notification_days(self.dias_notificacion)
        super().save(*args, **kwargs)


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
        if (
            self.estado == EstadoMensajeSaliente.SENT
            and self.external_ref.strip()
            and not is_non_sensitive_reference(self.external_ref)
        ):
            raise ValidationError(
                {'external_ref': 'external_ref debe ser una referencia no sensible, no una URL, token o credencial.'}
            )

