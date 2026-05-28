from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from cobranza.models import PagoMensual
from contratos.models import Arrendatario, Contrato, is_international_phone_number
from documentos.models import DocumentoEmitido, EstadoDocumento
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
CHANNEL_GATE_ALLOWED_SENSITIVE_REF_KEYS = (
    *EMAIL_READINESS_REF_KEYS,
    *EMAIL_CREDENTIAL_REF_KEYS,
    'template_aprobado_ref',
    'template_ref',
    'templates_aprobados',
)
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


def gate_restrictions_contain_sensitive_reference(restrictions):
    return contains_sensitive_reference(
        restrictions or {},
        include_sensitive_keys=True,
        allowed_sensitive_keys=CHANNEL_GATE_ALLOWED_SENSITIVE_REF_KEYS,
    )


def whatsapp_gate_has_approved_template(canal_mensajeria):
    restrictions = canal_mensajeria.restricciones_operativas or {}
    if gate_restrictions_contain_sensitive_reference(restrictions):
        return False
    return bool(restrictions.get('templates_aprobados')) or has_non_sensitive_operational_ref(
        restrictions,
        ('template_aprobado_ref', 'template_ref'),
    )


def document_delivery_blocking_reason(documento_emitido):
    if not documento_emitido:
        return ''
    policy = documento_emitido.get_active_policy()
    if not policy:
        return ''
    requires_formalization = (
        policy.requiere_firma_arrendador
        or policy.requiere_firma_arrendatario
        or policy.requiere_codeudor
        or policy.requiere_notaria
    )
    if requires_formalization and documento_emitido.estado != EstadoDocumento.FORMALIZED:
        return 'El documento requiere formalizacion antes de enviarse por canales.'
    return ''


def resolve_message_contract_context(contrato=None, documento_emitido=None):
    if contrato:
        return contrato
    if not documento_emitido:
        return None
    expediente = getattr(documento_emitido, 'expediente', None)
    if not expediente or expediente.entidad_tipo != 'contrato':
        return None
    try:
        contract_id = int(expediente.entidad_id)
    except (TypeError, ValueError):
        return None
    return Contrato.objects.filter(pk=contract_id).first()


def identity_is_contract_override(canal, contrato, identidad_envio):
    if not contrato or not identidad_envio:
        return False
    if contrato.identidad_envio_override_id != identidad_envio.pk:
        return False
    if identidad_envio.canal != canal or identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
        return False
    try:
        contrato.validate_identity_override()
    except ValidationError:
        return False
    return True


def identity_has_active_mandate_assignment(canal, contrato, identidad_envio):
    if not contrato or not contrato.mandato_operacion_id or not identidad_envio:
        return False
    return AsignacionCanalOperacion.objects.filter(
        mandato_operacion_id=contrato.mandato_operacion_id,
        mandato_operacion__estado=EstadoMandatoOperacion.ACTIVE,
        canal=canal,
        identidad_envio=identidad_envio,
        identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
        estado=EstadoAsignacionCanal.ACTIVE,
    ).exists()


def message_identity_authorization_issue(canal, contrato=None, documento_emitido=None, identidad_envio=None):
    contract_context = resolve_message_contract_context(contrato=contrato, documento_emitido=documento_emitido)
    if not contract_context or not identidad_envio:
        return ''
    if identidad_envio.canal != canal:
        return 'La identidad de envio debe pertenecer al mismo canal del mensaje.'
    if identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
        return 'Mensaje preparado/enviado requiere identidad activa.'
    if identity_is_contract_override(canal, contract_context, identidad_envio):
        return ''
    if identity_has_active_mandate_assignment(canal, contract_context, identidad_envio):
        return ''
    return (
        'La identidad de envio debe estar autorizada por override del contrato o asignacion activa '
        'del mandato para el mismo canal.'
    )


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


class EstadoNotificacionCobranza(models.TextChoices):
    SCHEDULED = 'programada', 'Programada'
    PREPARED = 'preparada', 'Preparada'
    SKIPPED = 'omitida', 'Omitida'


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
        if gate_restrictions_contain_sensitive_reference(self.restricciones_operativas):
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
        errors = {}
        if self.identidad_envio_id and self.identidad_envio.canal != self.canal:
            errors['identidad_envio'] = 'La identidad de envio debe pertenecer al mismo canal del mensaje.'
        if self.canal_mensajeria.canal != self.canal:
            errors['canal_mensajeria'] = 'El gate configurado debe corresponder al mismo canal del mensaje.'
        if self.estado == EstadoMensajeSaliente.SENT:
            if not self.external_ref.strip():
                errors['external_ref'] = 'Mensaje enviado requiere external_ref trazable.'
            elif not is_non_sensitive_reference(self.external_ref):
                errors['external_ref'] = (
                    'external_ref debe ser una referencia no sensible, no una URL, token o credencial.'
                )
            if self.enviado_at is None:
                errors['enviado_at'] = 'Mensaje enviado requiere timestamp de envio.'
        if contains_sensitive_reference(self.provider_payload, include_sensitive_keys=True):
            errors['provider_payload'] = 'provider_payload no debe contener URLs, tokens, credenciales ni correos.'
        if self.motivo_bloqueo.strip() and contains_sensitive_reference(self.motivo_bloqueo):
            errors['motivo_bloqueo'] = 'motivo_bloqueo no debe contener URLs, tokens, credenciales ni correos.'
        if self.estado in {EstadoMensajeSaliente.PREPARED, EstadoMensajeSaliente.SENT}:
            if self.canal_mensajeria.estado_gate != EstadoGateCanal.OPEN:
                errors['canal_mensajeria'] = 'Mensaje preparado/enviado requiere gate de canal abierto.'
            elif self.canal == CanalOperacion.EMAIL:
                if not is_non_sensitive_reference(self.canal_mensajeria.evidencia_ref):
                    errors['canal_mensajeria'] = 'Email preparado/enviado requiere evidencia_ref no sensible.'
                elif not has_non_sensitive_operational_ref(
                    self.canal_mensajeria.restricciones_operativas,
                    EMAIL_READINESS_REF_KEYS,
                ):
                    errors['canal_mensajeria'] = 'Email preparado/enviado requiere prueba aislada trazable.'
                elif not has_non_sensitive_operational_ref(
                    self.canal_mensajeria.restricciones_operativas,
                    EMAIL_CREDENTIAL_REF_KEYS,
                ):
                    errors['canal_mensajeria'] = 'Email preparado/enviado requiere credencial u OAuth validado.'
            if not self.identidad_envio_id or self.identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
                errors['identidad_envio'] = 'Mensaje preparado/enviado requiere identidad activa.'
            elif reason := message_identity_authorization_issue(
                self.canal,
                contrato=self.contrato,
                documento_emitido=self.documento_emitido,
                identidad_envio=self.identidad_envio,
            ):
                errors['identidad_envio'] = reason
            if not self.destinatario.strip():
                errors['destinatario'] = 'Mensaje preparado/enviado requiere destinatario trazable.'
            if self.contrato_id and self.contrato.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
                errors['contrato'] = 'Mensaje preparado/enviado requiere mandato operativo activo.'
            if self.canal == CanalOperacion.WHATSAPP:
                tenant = self.arrendatario
                if not tenant:
                    errors['arrendatario'] = 'WhatsApp preparado/enviado requiere arrendatario trazable.'
                elif tenant.whatsapp_bloqueado:
                    errors['arrendatario'] = 'WhatsApp preparado/enviado no acepta contacto bloqueado.'
                elif not tenant.whatsapp_opt_in:
                    errors['arrendatario'] = 'WhatsApp preparado/enviado requiere opt-in operativo.'
                elif not tenant.whatsapp_opt_in_evidencia_ref.strip():
                    errors['arrendatario'] = 'WhatsApp preparado/enviado requiere evidencia de opt-in.'
                elif not is_non_sensitive_reference(tenant.whatsapp_opt_in_evidencia_ref):
                    errors['arrendatario'] = 'WhatsApp preparado/enviado requiere evidencia de opt-in no sensible.'
                elif not is_international_phone_number(tenant.telefono):
                    errors['arrendatario'] = 'WhatsApp preparado/enviado requiere telefono internacional.'
                elif not whatsapp_gate_has_approved_template(self.canal_mensajeria):
                    errors['canal_mensajeria'] = 'WhatsApp preparado/enviado requiere template aprobado.'
            if reason := document_delivery_blocking_reason(self.documento_emitido):
                errors['documento_emitido'] = reason
        if errors:
            raise ValidationError(errors)


class NotificacionCobranzaProgramada(TimestampedModel):
    pago_mensual = models.ForeignKey(
        PagoMensual,
        on_delete=models.CASCADE,
        related_name='notificaciones_cobranza',
    )
    configuracion = models.ForeignKey(
        ConfiguracionNotificacionContrato,
        on_delete=models.CASCADE,
        related_name='notificaciones_programadas',
    )
    canal = models.CharField(max_length=16, choices=CanalOperacion.choices)
    dia_notificacion = models.PositiveSmallIntegerField()
    fecha_programada = models.DateField()
    estado = models.CharField(
        max_length=16,
        choices=EstadoNotificacionCobranza.choices,
        default=EstadoNotificacionCobranza.SCHEDULED,
    )
    mensaje_saliente = models.ForeignKey(
        MensajeSaliente,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='notificaciones_cobranza',
    )
    motivo_estado = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_programada', 'pago_mensual_id', 'canal', 'dia_notificacion']
        constraints = [
            models.UniqueConstraint(
                fields=['pago_mensual', 'canal', 'dia_notificacion'],
                name='uniq_notificacion_cobranza_por_pago_canal_dia',
            ),
        ]

    def __str__(self):
        return f'{self.pago_mensual_id} - {self.canal} - {self.fecha_programada}'

    def clean(self):
        super().clean()
        errors = {}
        if self.configuracion_id:
            if self.canal != self.configuracion.canal:
                errors['canal'] = 'El canal debe coincidir con la configuracion de notificacion.'
            if not self.configuracion.activa:
                errors['configuracion'] = 'La notificacion requiere una configuracion activa.'
            if self.pago_mensual_id and self.configuracion.contrato_id != self.pago_mensual.contrato_id:
                errors['configuracion'] = (
                    'La configuracion debe pertenecer al contrato del pago mensual.'
                )
            if self.dia_notificacion not in (self.configuracion.dias_notificacion or []):
                errors['dia_notificacion'] = (
                    'El dia programado debe existir en la cadencia configurada.'
                )
        if self.pago_mensual_id:
            try:
                expected_date = date(
                    int(self.pago_mensual.anio),
                    int(self.pago_mensual.mes),
                    int(self.dia_notificacion),
                )
            except (TypeError, ValueError):
                expected_date = None
            if expected_date and self.fecha_programada != expected_date:
                errors['fecha_programada'] = (
                    'La fecha programada debe corresponder al dia de cadencia dentro del mes operativo.'
                )
        if self.estado == EstadoNotificacionCobranza.PREPARED and not self.mensaje_saliente_id:
            errors['mensaje_saliente'] = 'Una notificacion preparada requiere mensaje saliente asociado.'
        if self.motivo_estado.strip() and contains_sensitive_reference(self.motivo_estado):
            errors['motivo_estado'] = 'El motivo de la notificacion debe ser texto no sensible.'
        if self.estado == EstadoNotificacionCobranza.SKIPPED and not self.motivo_estado.strip():
            errors['motivo_estado'] = 'Una notificacion omitida requiere motivo operativo.'
        if self.mensaje_saliente_id:
            if self.mensaje_saliente.canal != self.canal:
                errors['mensaje_saliente'] = 'El mensaje asociado debe usar el mismo canal.'
            if self.pago_mensual_id:
                message_contract = resolve_message_contract_context(
                    contrato=self.mensaje_saliente.contrato,
                    documento_emitido=self.mensaje_saliente.documento_emitido,
                )
                if not message_contract or message_contract.pk != self.pago_mensual.contrato_id:
                    errors['mensaje_saliente'] = 'El mensaje asociado debe pertenecer al contrato del pago mensual.'
                expected_tenant_id = self.pago_mensual.contrato.arrendatario_id
                if (
                    self.mensaje_saliente.arrendatario_id
                    and self.mensaje_saliente.arrendatario_id != expected_tenant_id
                ):
                    errors['mensaje_saliente'] = 'El mensaje asociado debe pertenecer al arrendatario del pago mensual.'
            if self.estado == EstadoNotificacionCobranza.PREPARED and (
                self.mensaje_saliente.estado not in {EstadoMensajeSaliente.PREPARED, EstadoMensajeSaliente.BLOCKED}
            ):
                errors['estado'] = 'Una notificacion preparada requiere mensaje preparado o bloqueado.'
        if errors:
            raise ValidationError(errors)

