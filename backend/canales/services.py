from django.db import transaction
from django.utils import timezone

from audit.models import ManualResolution
from contratos.models import Arrendatario, Contrato
from operacion.models import AsignacionCanalOperacion, CanalOperacion, EstadoIdentidadEnvio, EstadoMandatoOperacion

from .models import CanalMensajeria, EstadoGateCanal, EstadoMensajeSaliente, MensajeSaliente


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
    if arrendatario.whatsapp_bloqueado:
        return ''
    return arrendatario.telefono or ''


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
    elif not identidad or identidad.estado != EstadoIdentidadEnvio.ACTIVE:
        blocking_reason = f'No existe una identidad activa valida para el canal {canal}.'
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
        return message

    message.estado = EstadoMensajeSaliente.PREPARED
    message.save()
    return message


@transaction.atomic
def mark_message_as_sent(message, external_ref=''):
    if message.estado != EstadoMensajeSaliente.PREPARED:
        raise ValueError('Solo se puede registrar envio manual para mensajes preparados.')
    message.estado = EstadoMensajeSaliente.SENT
    message.external_ref = external_ref
    message.enviado_at = timezone.now()
    message.save(update_fields=['estado', 'external_ref', 'enviado_at', 'updated_at'])
    return message
