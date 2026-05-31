from calendar import monthrange
from datetime import date

from django.db import transaction
from django.utils import timezone

from audit.models import ManualResolution
from audit.services import create_audit_event
from core.reference_validation import is_non_sensitive_reference
from cobranza.models import EstadoPago
from contratos.models import Arrendatario, Contrato, is_international_phone_number
from operacion.models import AsignacionCanalOperacion, CanalOperacion, EstadoIdentidadEnvio, EstadoMandatoOperacion

from .models import (
    EMAIL_CREDENTIAL_REF_KEYS,
    EMAIL_READINESS_REF_KEYS,
    CanalMensajeria,
    ConfiguracionNotificacionContrato,
    EstadoGateCanal,
    EstadoMensajeSaliente,
    EstadoNotificacionCobranza,
    MensajeSaliente,
    NotificacionCobranzaProgramada,
    document_delivery_blocking_reason,
    has_non_sensitive_operational_ref,
    message_identity_authorization_issue,
    whatsapp_gate_has_approved_template,
)


WHATSAPP_WINDOW_START_HOUR = 8
WHATSAPP_WINDOW_END_HOUR = 21
MESSAGE_PREPARED_EVENT_TYPE = 'canales.mensaje_saliente.prepared'
WHATSAPP_FALLBACK_REQUIRED_CATEGORY = 'canales.whatsapp.fallback_requerido'
WHATSAPP_FALLBACK_REQUIRED_EVENT_TYPE = 'canales.whatsapp.fallback_required'
COLLECTABLE_PAYMENT_STATES = {EstadoPago.PENDING, EstadoPago.OVERDUE}


def _service_actor_identifier(actor_user=None, actor_identifier='', default='system:canales.prepare_message'):
    actor_identifier = (actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        return default
    return actor_identifier


def _with_actor_metadata(payload=None, *, actor_user=None, actor_identifier=''):
    metadata = dict(payload or {})
    actor_identifier = _service_actor_identifier(actor_user=actor_user, actor_identifier=actor_identifier)
    if actor_user is None and actor_identifier:
        metadata['actor_identifier'] = actor_identifier
    elif actor_identifier:
        metadata['actor_identifier'] = actor_identifier
    return metadata, actor_identifier


def ensure_manual_resolution(
    category,
    message,
    payload=None,
    *,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
    audit_event_type='',
):
    metadata, actor_identifier = _with_actor_metadata(
        payload,
        actor_user=actor_user,
        actor_identifier=actor_identifier,
    )
    existing = ManualResolution.objects.filter(
        category=category,
        scope_type=metadata.get('scope_type', 'canales'),
        scope_reference=metadata.get('scope_reference', ''),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).first()
    if existing:
        updates = []
        existing_metadata = dict(existing.metadata or {})
        if actor_user is not None and existing.requested_by_id is None:
            existing.requested_by = actor_user
            updates.append('requested_by')
        if actor_identifier and not existing_metadata.get('actor_identifier'):
            existing_metadata['actor_identifier'] = actor_identifier
            existing.metadata = existing_metadata
            updates.append('metadata')
        if updates:
            existing.save(update_fields=updates)
        return existing
    resolution = ManualResolution.objects.create(
        category=category,
        scope_type=metadata.get('scope_type', 'canales'),
        scope_reference=metadata.get('scope_reference', ''),
        summary=message,
        requested_by=actor_user,
        metadata=metadata,
    )
    if audit_event_type:
        entity_id = str(metadata.get('message_id') or metadata.get('scope_reference', ''))
        create_audit_event(
            event_type=audit_event_type,
            entity_type='mensaje_saliente',
            entity_id=entity_id,
            summary=message,
            severity='warning',
            actor_user=actor_user,
            actor_identifier=actor_identifier,
            ip_address=ip_address,
            metadata=metadata,
        )
    return resolution


def ensure_whatsapp_fallback_resolution(
    message,
    blocking_reason,
    *,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    return ensure_manual_resolution(
        WHATSAPP_FALLBACK_REQUIRED_CATEGORY,
        'WhatsApp bloqueado o fallido requiere fallback por Email o alerta critica trazable.',
        payload={
            'scope_reference': str(message.pk),
            'message_id': message.pk,
            'canal': CanalOperacion.WHATSAPP,
            'fallback_canal_base': CanalOperacion.EMAIL,
            'blocking_reason': blocking_reason,
            'contrato_id': message.contrato_id,
            'arrendatario_id': message.arrendatario_id,
            'documento_emitido_id': message.documento_emitido_id,
        },
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        audit_event_type=WHATSAPP_FALLBACK_REQUIRED_EVENT_TYPE,
    )


def create_message_prepared_audit_event(message, *, actor_user=None, actor_identifier='', ip_address=None):
    create_audit_event(
        event_type=MESSAGE_PREPARED_EVENT_TYPE,
        entity_type='mensaje_saliente',
        entity_id=str(message.pk),
        summary='Mensaje preparado o bloqueado segun gate/identidad',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={
            'estado': message.estado,
            'canal': message.canal,
            'contrato_id': message.contrato_id,
            'arrendatario_id': message.arrendatario_id,
            'documento_emitido_id': message.documento_emitido_id,
        },
    )


def resolve_document_contract(documento_emitido=None):
    if not documento_emitido or documento_emitido.expediente.entidad_tipo != 'contrato':
        return None
    try:
        contract_id = int(documento_emitido.expediente.entidad_id)
    except (TypeError, ValueError):
        return None
    return Contrato.objects.select_related('arrendatario').filter(pk=contract_id).first()


def resolve_arrendatario(contrato=None, arrendatario=None, documento_emitido=None):
    if arrendatario:
        return arrendatario
    if contrato:
        return contrato.arrendatario
    contract = resolve_document_contract(documento_emitido)
    if contract:
        return contract.arrendatario
    return None


def resolve_identity(canal, contrato=None, explicit_identity=None):
    if explicit_identity:
        return explicit_identity
    if not contrato:
        return None
    if (
        contrato.identidad_envio_override_id
        and contrato.identidad_envio_override.estado == EstadoIdentidadEnvio.ACTIVE
        and contrato.identidad_envio_override.canal == canal
    ):
        return contrato.identidad_envio_override
    assignment = (
        AsignacionCanalOperacion.objects.filter(
            mandato_operacion=contrato.mandato_operacion,
            canal=canal,
            estado='activa',
            identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
        )
        .select_related('identidad_envio')
        .order_by('prioridad')
        .first()
    )
    return assignment.identidad_envio if assignment else None


def resolve_recipient(canal, arrendatario):
    if not arrendatario:
        return ''
    if canal == CanalOperacion.EMAIL:
        return arrendatario.email or ''
    if (
        arrendatario.whatsapp_bloqueado
        or not arrendatario.whatsapp_opt_in
        or not arrendatario.whatsapp_opt_in_evidencia_ref.strip()
        or not is_international_phone_number(arrendatario.telefono)
    ):
        return ''
    return arrendatario.telefono or ''


def is_within_whatsapp_window(now=None):
    current_time = timezone.localtime(now).time() if now else timezone.localtime().time()
    return WHATSAPP_WINDOW_START_HOUR <= current_time.hour < WHATSAPP_WINDOW_END_HOUR


def whatsapp_blocking_reason(arrendatario, canal_mensajeria):
    if not arrendatario:
        return ''
    if arrendatario.whatsapp_bloqueado:
        return 'El arrendatario tiene WhatsApp bloqueado.'
    if not arrendatario.whatsapp_opt_in:
        return 'WhatsApp requiere opt-in operativo del arrendatario.'
    if not arrendatario.whatsapp_opt_in_evidencia_ref.strip():
        return 'WhatsApp requiere evidencia trazable del opt-in.'
    if not is_non_sensitive_reference(arrendatario.whatsapp_opt_in_evidencia_ref):
        return 'WhatsApp requiere evidencia de opt-in no sensible.'
    if not is_international_phone_number(arrendatario.telefono):
        return 'WhatsApp requiere telefono operativo en formato internacional.'
    if not whatsapp_gate_has_approved_template(canal_mensajeria):
        return 'WhatsApp requiere template aprobado registrado en el gate del canal.'
    if not is_within_whatsapp_window():
        return 'WhatsApp solo opera dentro de la ventana permitida 08:00-21:00 America/Santiago.'
    return ''


def email_readiness_blocking_reason(canal_mensajeria):
    if canal_mensajeria.canal != CanalOperacion.EMAIL:
        return ''
    if not is_non_sensitive_reference(canal_mensajeria.evidencia_ref):
        return 'Email requiere evidencia_ref no sensible del gate antes de preparar envios.'
    if not has_non_sensitive_operational_ref(canal_mensajeria.restricciones_operativas, EMAIL_READINESS_REF_KEYS):
        return 'Email requiere prueba aislada de envio no sensible registrada en el gate.'
    if not has_non_sensitive_operational_ref(canal_mensajeria.restricciones_operativas, EMAIL_CREDENTIAL_REF_KEYS):
        return 'Email requiere referencia OAuth o credencial validada no sensible en el gate.'
    return ''


def expected_payment_notification_schedule(payment, configuration):
    try:
        last_day = monthrange(int(payment.anio), int(payment.mes))[1]
    except (TypeError, ValueError):
        return []

    schedule = []
    for day in configuration.dias_notificacion or []:
        if int(day) > last_day:
            continue
        schedule.append((int(day), date(int(payment.anio), int(payment.mes), int(day))))
    return schedule


@transaction.atomic
def materialize_payment_notification_schedule(payment):
    if payment.estado_pago not in COLLECTABLE_PAYMENT_STATES:
        return {'rows': [], 'created_count': 0}

    configurations = ConfiguracionNotificacionContrato.objects.filter(
        contrato=payment.contrato,
        activa=True,
    ).order_by('canal', 'id')
    rows = []
    created_count = 0
    for configuration in configurations:
        for day, scheduled_date in expected_payment_notification_schedule(payment, configuration):
            notification, created = NotificacionCobranzaProgramada.objects.get_or_create(
                pago_mensual=payment,
                canal=configuration.canal,
                dia_notificacion=day,
                defaults={
                    'configuracion': configuration,
                    'fecha_programada': scheduled_date,
                    'estado': EstadoNotificacionCobranza.SCHEDULED,
                },
            )
            if not created:
                updates = []
                if notification.configuracion_id != configuration.id:
                    notification.configuracion = configuration
                    updates.append('configuracion')
                if notification.fecha_programada != scheduled_date:
                    notification.fecha_programada = scheduled_date
                    updates.append('fecha_programada')
                if updates:
                    notification.full_clean()
                    notification.save(update_fields=[*updates, 'updated_at'])
            else:
                created_count += 1
            rows.append(notification)
    return {'rows': rows, 'created_count': created_count}


@transaction.atomic
def prepare_message(
    *,
    canal,
    canal_mensajeria,
    contrato=None,
    arrendatario=None,
    documento_emitido=None,
    explicit_identity=None,
    asunto='',
    cuerpo='',
    usuario=None,
    actor_identifier='',
    ip_address=None,
):
    arrendatario = resolve_arrendatario(contrato=contrato, arrendatario=arrendatario, documento_emitido=documento_emitido)
    identidad = resolve_identity(canal, contrato=contrato, explicit_identity=explicit_identity)
    destinatario = resolve_recipient(canal, arrendatario)
    actor_identifier = _service_actor_identifier(actor_user=usuario, actor_identifier=actor_identifier)

    message = MensajeSaliente(
        canal=canal,
        canal_mensajeria=canal_mensajeria,
        identidad_envio=identidad,
        contrato=contrato,
        arrendatario=arrendatario,
        documento_emitido=documento_emitido,
        destinatario=destinatario,
        asunto=asunto,
        cuerpo=cuerpo,
        usuario=usuario,
    )

    blocking_reason = ''
    if canal_mensajeria.estado_gate != EstadoGateCanal.OPEN:
        blocking_reason = f'El gate del canal {canal} no permite envio automatico.'
    elif canal == CanalOperacion.EMAIL and (reason := email_readiness_blocking_reason(canal_mensajeria)):
        blocking_reason = reason
    elif not identidad or identidad.estado != EstadoIdentidadEnvio.ACTIVE:
        blocking_reason = f'No existe una identidad activa valida para el canal {canal}.'
    elif reason := message_identity_authorization_issue(
        canal,
        contrato=contrato,
        documento_emitido=documento_emitido,
        identidad_envio=identidad,
    ):
        blocking_reason = reason
    elif canal == CanalOperacion.WHATSAPP and (
        reason := whatsapp_blocking_reason(arrendatario, canal_mensajeria)
    ):
        blocking_reason = reason
    elif reason := document_delivery_blocking_reason(documento_emitido):
        blocking_reason = reason
    elif not destinatario:
        blocking_reason = f'No existe un destinatario valido para el canal {canal}.'
    elif contrato and contrato.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
        blocking_reason = 'El contrato no tiene un mandato operativo activo para envio.'

    if blocking_reason:
        message.estado = EstadoMensajeSaliente.BLOCKED
        message.motivo_bloqueo = blocking_reason
        message.full_clean()
        message.save()
        ensure_manual_resolution(
            f'canales.{canal}.bloqueado',
            blocking_reason,
            payload={'scope_reference': str(message.pk), 'canal': canal},
            actor_user=usuario,
            actor_identifier=actor_identifier,
            ip_address=ip_address,
        )
        if canal == CanalOperacion.WHATSAPP:
            ensure_whatsapp_fallback_resolution(
                message,
                blocking_reason,
                actor_user=usuario,
                actor_identifier=actor_identifier,
                ip_address=ip_address,
            )
        create_message_prepared_audit_event(
            message,
            actor_user=usuario,
            actor_identifier=actor_identifier,
            ip_address=ip_address,
        )
        return message

    message.estado = EstadoMensajeSaliente.PREPARED
    message.full_clean()
    message.save()
    create_message_prepared_audit_event(
        message,
        actor_user=usuario,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
    )
    return message


@transaction.atomic
def mark_whatsapp_message_as_failed(
    message,
    failure_reason='',
    *,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    if message.canal != CanalOperacion.WHATSAPP:
        raise ValueError('Solo se puede registrar fallo controlado para mensajes WhatsApp.')
    if message.estado != EstadoMensajeSaliente.PREPARED:
        raise ValueError('Solo se puede registrar fallo controlado para mensajes WhatsApp preparados.')
    failure_reason = failure_reason.strip()
    if not failure_reason:
        raise ValueError('El fallo WhatsApp requiere un motivo trazable.')
    if not is_non_sensitive_reference(failure_reason):
        raise ValueError(
            'El fallo WhatsApp requiere un motivo no sensible; no use URLs, tokens, credenciales ni correos.'
        )
    actor_identifier = (actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        raise ValueError('El fallo WhatsApp requiere un actor trazable para auditoria.')

    message.estado = EstadoMensajeSaliente.FAILED
    message.motivo_bloqueo = failure_reason
    message.full_clean()
    message.save(update_fields=['estado', 'motivo_bloqueo', 'updated_at'])
    ensure_whatsapp_fallback_resolution(
        message,
        failure_reason,
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
    )
    return message


@transaction.atomic
def mark_message_as_sent(message, external_ref='', *, actor_user=None, actor_identifier='', ip_address=None):
    if message.estado != EstadoMensajeSaliente.PREPARED:
        raise ValueError('Solo se puede registrar envio manual para mensajes preparados.')
    external_ref = external_ref.strip()
    if not external_ref:
        raise ValueError('El envio manual requiere una referencia externa trazable.')
    if not is_non_sensitive_reference(external_ref):
        raise ValueError(
            'El envio manual requiere external_ref no sensible; no use URLs, tokens, credenciales ni correos.'
        )
    actor_identifier = (actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        raise ValueError('El envio manual requiere un actor trazable para auditoria.')
    if message.canal_mensajeria.estado_gate != EstadoGateCanal.OPEN:
        raise ValueError('No se puede registrar envio manual si el gate del canal no esta abierto.')
    if message.canal == CanalOperacion.EMAIL and (reason := email_readiness_blocking_reason(message.canal_mensajeria)):
        raise ValueError(f'No se puede registrar envio manual de Email: {reason}')
    if not message.identidad_envio or message.identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
        raise ValueError('No se puede registrar envio manual sin identidad de envio activa.')
    if reason := message_identity_authorization_issue(
        message.canal,
        contrato=message.contrato,
        documento_emitido=message.documento_emitido,
        identidad_envio=message.identidad_envio,
    ):
        raise ValueError(f'No se puede registrar envio manual: {reason}')
    if not message.destinatario:
        raise ValueError('No se puede registrar envio manual sin destinatario trazable.')
    if message.contrato and message.contrato.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
        raise ValueError('No se puede registrar envio manual sin mandato operativo activo.')
    if message.canal == CanalOperacion.WHATSAPP and (
        reason := whatsapp_blocking_reason(message.arrendatario, message.canal_mensajeria)
    ):
        raise ValueError(f'No se puede registrar envio manual de WhatsApp: {reason}')
    if reason := document_delivery_blocking_reason(message.documento_emitido):
        raise ValueError(f'No se puede registrar envio manual: {reason}')

    message.estado = EstadoMensajeSaliente.SENT
    message.external_ref = external_ref
    message.enviado_at = timezone.now()
    message.full_clean()
    message.save(update_fields=['estado', 'external_ref', 'enviado_at', 'updated_at'])
    create_audit_event(
        event_type='canales.mensaje_saliente.sent_manually',
        entity_type='mensaje_saliente',
        entity_id=str(message.pk),
        summary='Envio manual registrado',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={'external_ref': external_ref},
    )
    return message
