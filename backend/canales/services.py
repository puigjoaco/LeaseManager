from django.db import transaction
from django.utils import timezone

from audit.models import ManualResolution
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from contratos.models import Arrendatario, Contrato, is_international_phone_number
from documentos.models import EstadoDocumento
from operacion.models import AsignacionCanalOperacion, CanalOperacion, EstadoIdentidadEnvio, EstadoMandatoOperacion

from .models import (
    EMAIL_CREDENTIAL_REF_KEYS,
    EMAIL_READINESS_REF_KEYS,
    CanalMensajeria,
    EstadoGateCanal,
    EstadoMensajeSaliente,
    MensajeSaliente,
    has_non_sensitive_operational_ref,
)


WHATSAPP_WINDOW_START_HOUR = 8
WHATSAPP_WINDOW_END_HOUR = 21
WHATSAPP_FALLBACK_REQUIRED_CATEGORY = 'canales.whatsapp.fallback_requerido'


def ensure_manual_resolution(category, message, payload=None):
    existing = ManualResolution.objects.filter(
        category=category,
        scope_type='canales',
        scope_reference=payload.get('scope_reference', '') if payload else '',
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).first()
    if existing:
        return existing
    return ManualResolution.objects.create(
        category=category,
        scope_type='canales',
        scope_reference=payload.get('scope_reference', '') if payload else '',
        summary=message,
        metadata=payload or {},
    )


def ensure_whatsapp_fallback_resolution(message, blocking_reason):
    return ensure_manual_resolution(
        WHATSAPP_FALLBACK_REQUIRED_CATEGORY,
        'WhatsApp bloqueado requiere fallback por Email o alerta critica trazable.',
        payload={
            'scope_reference': str(message.pk),
            'canal': CanalOperacion.WHATSAPP,
            'fallback_canal_base': CanalOperacion.EMAIL,
            'blocking_reason': blocking_reason,
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


def whatsapp_gate_has_approved_template(canal_mensajeria):
    restrictions = canal_mensajeria.restricciones_operativas or {}
    if contains_sensitive_reference(restrictions):
        return False
    return bool(restrictions.get('templates_aprobados')) or has_non_sensitive_operational_ref(
        restrictions,
        ('template_aprobado_ref', 'template_ref'),
    )


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


@transaction.atomic
def prepare_message(*, canal, canal_mensajeria, contrato=None, arrendatario=None, documento_emitido=None, explicit_identity=None, asunto='', cuerpo='', usuario=None):
    arrendatario = resolve_arrendatario(contrato=contrato, arrendatario=arrendatario, documento_emitido=documento_emitido)
    identidad = resolve_identity(canal, contrato=contrato, explicit_identity=explicit_identity)
    destinatario = resolve_recipient(canal, arrendatario)

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
        message.save()
        ensure_manual_resolution(
            f'canales.{canal}.bloqueado',
            blocking_reason,
            payload={'scope_reference': str(message.pk), 'canal': canal},
        )
        if canal == CanalOperacion.WHATSAPP:
            ensure_whatsapp_fallback_resolution(message, blocking_reason)
        return message

    message.estado = EstadoMensajeSaliente.PREPARED
    message.save()
    return message


@transaction.atomic
def mark_message_as_sent(message, external_ref=''):
    if message.estado != EstadoMensajeSaliente.PREPARED:
        raise ValueError('Solo se puede registrar envio manual para mensajes preparados.')
    external_ref = external_ref.strip()
    if not external_ref:
        raise ValueError('El envio manual requiere una referencia externa trazable.')
    if not is_non_sensitive_reference(external_ref):
        raise ValueError(
            'El envio manual requiere external_ref no sensible; no use URLs, tokens, credenciales ni correos.'
        )
    if message.canal_mensajeria.estado_gate != EstadoGateCanal.OPEN:
        raise ValueError('No se puede registrar envio manual si el gate del canal no esta abierto.')
    if message.canal == CanalOperacion.EMAIL and (reason := email_readiness_blocking_reason(message.canal_mensajeria)):
        raise ValueError(f'No se puede registrar envio manual de Email: {reason}')
    if not message.identidad_envio or message.identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
        raise ValueError('No se puede registrar envio manual sin identidad de envio activa.')
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
    message.save(update_fields=['estado', 'external_ref', 'enviado_at', 'updated_at'])
    return message
