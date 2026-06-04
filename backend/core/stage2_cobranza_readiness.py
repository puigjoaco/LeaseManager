from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from audit.models import AuditEvent, ManualResolution
from canales.models import (
    CanalMensajeria,
    ConfiguracionNotificacionContrato,
    EstadoGateCanal,
    EstadoMensajeSaliente,
    MensajeSaliente,
    NotificacionCobranzaProgramada,
    gate_restrictions_contain_sensitive_reference,
    is_within_whatsapp_operational_window,
    message_identity_authorization_issue,
    whatsapp_message_window_timestamp,
)
from canales.services import (
    COLLECTABLE_PAYMENT_STATES,
    WHATSAPP_FALLBACK_REQUIRED_CATEGORY,
    WHATSAPP_FALLBACK_REQUIRED_EVENT_TYPE,
    document_delivery_blocking_reason,
    email_readiness_blocking_reason,
    expected_payment_notification_schedule,
    whatsapp_gate_has_approved_template,
)
from cobranza.models import (
    AjusteContrato,
    CANONICAL_UF_SOURCE_KEYS,
    CodigoCobroResidual,
    EstadoCuentaArrendatario,
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    EstadoPago,
    EFFECTIVE_CODE_APPLIED_EVENT_TYPE,
    EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
    GateCobroExterno,
    IntentoPagoWebPay,
    MANUAL_UF_LOAD_EVENT_TYPE,
    PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
    WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
    WEBPAY_PREPARE_EVENT_TYPE,
)
from cobranza.services import build_account_state_summary
from contratos.models import (
    Arrendatario,
    Contrato,
    EstadoContrato,
    MonedaBaseContrato,
    WHATSAPP_BLOCK_ALERT_CATEGORY,
    WHATSAPP_BLOCK_EVENT_TYPE,
    WHATSAPP_REHABILITATION_EVENT_TYPE,
    is_international_phone_number,
)
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from operacion.models import (
    AsignacionCanalOperacion,
    CanalOperacion,
    EstadoAsignacionCanal,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
)


AUTHORIZED_STAGE2_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
SENT_MESSAGE_EVENT_TYPE = 'canales.mensaje_saliente.sent_manually'


def _non_sensitive_reference(value: str) -> bool:
    return is_non_sensitive_reference(value)


def _issue(code: str, message: str, *, count: int = 1, severity: str = 'blocking') -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _count_invalid(queryset) -> int:
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _partial_repayment_exception_event_is_complete(repayment: RepactacionDeuda) -> bool:
    if not repayment.es_repactacion_parcial:
        return True
    events = AuditEvent.objects.filter(
        event_type=PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
        entity_type='repactacion_deuda',
        entity_id=str(repayment.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        expected_reason = repayment.excepcion_parcial_motivo.strip()
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if str(metadata.get('excepcion_parcial_ref') or '').strip() != repayment.excepcion_parcial_ref.strip():
            continue
        if str(metadata.get('excepcion_parcial_motivo') or '').strip() != expected_reason:
            continue
        if not _non_sensitive_reference(metadata.get('excepcion_parcial_ref') or ''):
            continue
        return True
    return False


def _manual_uf_load_event_is_complete(uf_value: ValorUFDiario) -> bool:
    if not uf_value.requiere_auditoria_manual:
        return True
    events = AuditEvent.objects.filter(
        event_type=MANUAL_UF_LOAD_EVENT_TYPE,
        entity_type='valor_uf_diario',
        entity_id=str(uf_value.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if str(metadata.get('evidencia_ref') or '').strip() != uf_value.evidencia_ref.strip():
            continue
        if str(metadata.get('motivo_carga') or '').strip() != uf_value.motivo_carga.strip():
            continue
        if str(metadata.get('responsable_ref') or '').strip() != uf_value.responsable_ref.strip():
            continue
        if not _non_sensitive_reference(metadata.get('evidencia_ref') or ''):
            continue
        if not _non_sensitive_reference(metadata.get('responsable_ref') or ''):
            continue
        return True
    return False


def _collect_uf_value_issues(uf_values) -> dict[str, int]:
    counts = Counter()
    for uf_value in uf_values:
        if not uf_value.source_key_is_canonical:
            counts['source_not_canonical'] += 1
        try:
            uf_value.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if uf_value.requiere_auditoria_manual:
            counts['manual_values'] += 1
            if not _manual_uf_load_event_is_complete(uf_value):
                counts['manual_without_audit_event'] += 1
    return dict(sorted(counts.items()))


def _collect_repayment_issues(repayments) -> dict[str, int]:
    counts = Counter()
    for repayment in repayments:
        try:
            repayment.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if repayment.es_repactacion_parcial:
            if not repayment.tiene_excepcion_parcial:
                counts['partial_without_exception'] += 1
            elif not _partial_repayment_exception_event_is_complete(repayment):
                counts['partial_without_audit_event'] += 1
    return dict(sorted(counts.items()))


def _count_by(queryset, field_name: str) -> dict[str, int]:
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _whatsapp_contact_static_issue(message: MensajeSaliente) -> str:
    tenant = message.arrendatario
    if not tenant:
        return 'WhatsApp requiere arrendatario trazable.'
    if tenant.whatsapp_bloqueado:
        return 'WhatsApp no puede operar con contacto bloqueado.'
    if not tenant.whatsapp_opt_in:
        return 'WhatsApp requiere opt-in operativo.'
    if not tenant.whatsapp_opt_in_evidencia_ref.strip():
        return 'WhatsApp requiere evidencia de opt-in.'
    if not _non_sensitive_reference(tenant.whatsapp_opt_in_evidencia_ref):
        return 'WhatsApp requiere evidencia de opt-in no sensible.'
    if not is_international_phone_number(tenant.telefono):
        return 'WhatsApp requiere telefono en formato internacional.'
    if not whatsapp_gate_has_approved_template(message.canal_mensajeria):
        return 'WhatsApp requiere template aprobado en el gate.'
    return ''


def _message_operational_issue(message: MensajeSaliente) -> str:
    if message.estado not in {EstadoMensajeSaliente.PREPARED, EstadoMensajeSaliente.SENT}:
        return ''
    if message.canal_mensajeria.estado_gate != EstadoGateCanal.OPEN:
        return 'Mensaje preparado/enviado con gate de canal no abierto.'
    if message.canal == CanalOperacion.EMAIL and email_readiness_blocking_reason(message.canal_mensajeria):
        return 'Mensaje Email preparado/enviado con readiness de gate incompleta.'
    if not message.identidad_envio_id or message.identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
        return 'Mensaje preparado/enviado sin identidad activa.'
    if message_identity_authorization_issue(
        message.canal,
        contrato=message.contrato,
        documento_emitido=message.documento_emitido,
        identidad_envio=message.identidad_envio,
    ):
        return 'Mensaje preparado/enviado con identidad no autorizada para el contrato.'
    if not message.destinatario.strip():
        return 'Mensaje preparado/enviado sin destinatario trazable.'
    if message.contrato_id and message.contrato.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
        return 'Mensaje preparado/enviado sin mandato operativo activo.'
    if message.canal == CanalOperacion.WHATSAPP:
        if issue := _whatsapp_contact_static_issue(message):
            return issue
        window_timestamp = whatsapp_message_window_timestamp(message)
        if window_timestamp and not is_within_whatsapp_operational_window(window_timestamp):
            return 'Mensaje WhatsApp preparado/enviado fuera de ventana operativa.'
    return ''


def _message_context_matches(left: MensajeSaliente, right: MensajeSaliente) -> bool:
    if left.documento_emitido_id and left.documento_emitido_id == right.documento_emitido_id:
        return True
    if left.contrato_id and left.contrato_id == right.contrato_id:
        return True
    if left.arrendatario_id and left.arrendatario_id == right.arrendatario_id:
        return True
    return False


def _fallback_email_matches(message: MensajeSaliente, fallback: MensajeSaliente) -> bool:
    if not _message_context_matches(message, fallback):
        return False
    message_state_at = message.updated_at or message.created_at
    fallback_ready_at = fallback.created_at
    if fallback.estado == EstadoMensajeSaliente.SENT and fallback.enviado_at:
        fallback_ready_at = fallback.enviado_at
    if message_state_at and fallback_ready_at and fallback_ready_at < message_state_at:
        return False
    return True


def _fallback_resolution_matches(message: MensajeSaliente, resolution: ManualResolution) -> bool:
    metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
    if not resolution.requested_by_id and not str(metadata.get('actor_identifier') or '').strip():
        return False
    if str(metadata.get('canal') or '').strip() != CanalOperacion.WHATSAPP:
        return False
    if str(metadata.get('fallback_canal_base') or '').strip() != CanalOperacion.EMAIL:
        return False
    if str(metadata.get('blocking_reason') or '').strip() != message.motivo_bloqueo.strip():
        return False
    if resolution.scope_reference == str(message.pk) or str(metadata.get('message_id') or '') == str(message.pk):
        return True
    for key, value in [
        ('documento_emitido_id', message.documento_emitido_id),
        ('contrato_id', message.contrato_id),
        ('arrendatario_id', message.arrendatario_id),
    ]:
        if value and str(metadata.get(key, '')) == str(value):
            return True
    return False


def _fallback_event_matches(message: MensajeSaliente) -> bool:
    events = AuditEvent.objects.filter(
        event_type=WHATSAPP_FALLBACK_REQUIRED_EVENT_TYPE,
        entity_type='mensaje_saliente',
        entity_id=str(message.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if str(metadata.get('canal') or '').strip() != CanalOperacion.WHATSAPP:
            continue
        if str(metadata.get('fallback_canal_base') or '').strip() != CanalOperacion.EMAIL:
            continue
        if str(metadata.get('blocking_reason') or '').strip() != message.motivo_bloqueo.strip():
            continue
        return True
    return False


def _collect_whatsapp_fallback_issues(messages) -> dict[str, int]:
    counts = Counter()
    message_list = list(messages)
    email_fallbacks = [
        message
        for message in message_list
        if message.canal == CanalOperacion.EMAIL
        and message.estado in {EstadoMensajeSaliente.PREPARED, EstadoMensajeSaliente.SENT}
    ]
    fallback_resolutions = list(
        ManualResolution.objects.filter(
            category=WHATSAPP_FALLBACK_REQUIRED_CATEGORY,
            status__in=[
                ManualResolution.Status.OPEN,
                ManualResolution.Status.IN_REVIEW,
                ManualResolution.Status.RESOLVED,
            ],
        )
    )

    for message in message_list:
        if message.canal != CanalOperacion.WHATSAPP:
            continue
        if message.estado not in {EstadoMensajeSaliente.BLOCKED, EstadoMensajeSaliente.FAILED}:
            continue
        if any(_fallback_email_matches(message, fallback) for fallback in email_fallbacks):
            continue
        if any(_fallback_resolution_matches(message, resolution) for resolution in fallback_resolutions) and (
            _fallback_event_matches(message)
        ):
            continue
        counts['without_fallback_trace'] += 1

    return dict(sorted(counts.items()))


def _collect_whatsapp_block_issues(blocked_tenants) -> dict[str, int]:
    counts = Counter()

    for tenant in blocked_tenants:
        if (
            not tenant.whatsapp_bloqueo_motivo.strip()
            or not tenant.whatsapp_bloqueo_evidencia_ref.strip()
            or tenant.whatsapp_bloqueado_at is None
        ):
            counts['whatsapp_block_trace_missing'] += 1
        if tenant.whatsapp_bloqueo_evidencia_ref.strip() and not _non_sensitive_reference(
            tenant.whatsapp_bloqueo_evidencia_ref
        ):
            counts['whatsapp_block_evidence_sensitive'] += 1
        if tenant.whatsapp_bloqueo_motivo.strip() and contains_sensitive_reference(
            tenant.whatsapp_bloqueo_motivo
        ):
            counts['whatsapp_block_motive_sensitive'] += 1
        if not _whatsapp_block_event_is_complete(tenant):
            counts['whatsapp_block_event_missing'] += 1
        if not _whatsapp_block_alert_is_complete(tenant):
            counts['whatsapp_block_alert_missing'] += 1

    return dict(sorted(counts.items()))


def _whatsapp_block_event_is_complete(tenant: Arrendatario) -> bool:
    events = AuditEvent.objects.filter(
        event_type=WHATSAPP_BLOCK_EVENT_TYPE,
        entity_type='arrendatario',
        entity_id=str(tenant.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if str(metadata.get('evidencia_ref') or '').strip() != tenant.whatsapp_bloqueo_evidencia_ref.strip():
            continue
        if str(metadata.get('motivo') or '').strip() != tenant.whatsapp_bloqueo_motivo.strip():
            continue
        if not _non_sensitive_reference(metadata.get('evidencia_ref') or ''):
            continue
        return True
    return False


def _whatsapp_block_alert_is_complete(tenant: Arrendatario) -> bool:
    alerts = ManualResolution.objects.filter(
        category=WHATSAPP_BLOCK_ALERT_CATEGORY,
        scope_type='arrendatario',
        scope_reference=str(tenant.pk),
        status__in=[
            ManualResolution.Status.OPEN,
            ManualResolution.Status.IN_REVIEW,
            ManualResolution.Status.RESOLVED,
        ],
    )
    for alert in alerts:
        metadata = alert.metadata if isinstance(alert.metadata, dict) else {}
        if not alert.requested_by_id and not str(metadata.get('actor_identifier') or '').strip():
            continue
        if str(alert.rationale or '').strip() != tenant.whatsapp_bloqueo_motivo.strip():
            continue
        if str(metadata.get('evidencia_ref') or '').strip() != tenant.whatsapp_bloqueo_evidencia_ref.strip():
            continue
        if not _non_sensitive_reference(metadata.get('evidencia_ref') or ''):
            continue
        return True
    return False


def _collect_whatsapp_rehabilitation_issues(rehabilitated_tenants) -> dict[str, int]:
    counts = Counter()

    for tenant in rehabilitated_tenants:
        if not tenant.whatsapp_rehabilitacion_ref.strip() or tenant.whatsapp_rehabilitado_at is None:
            counts['whatsapp_rehabilitation_trace_missing'] += 1
        if tenant.whatsapp_rehabilitacion_ref.strip() and not _non_sensitive_reference(
            tenant.whatsapp_rehabilitacion_ref
        ):
            counts['whatsapp_rehabilitation_sensitive_refs'] += 1
        if (
            not tenant.whatsapp_bloqueo_motivo.strip()
            or not tenant.whatsapp_bloqueo_evidencia_ref.strip()
            or tenant.whatsapp_bloqueado_at is None
        ):
            counts['whatsapp_rehabilitation_block_trace_missing'] += 1
        if not _whatsapp_block_event_is_complete(tenant):
            counts['whatsapp_rehabilitation_block_event_missing'] += 1
        if not _whatsapp_block_alert_is_complete(tenant):
            counts['whatsapp_rehabilitation_block_alert_missing'] += 1
        if not _whatsapp_rehabilitation_event_is_complete(tenant):
            counts['whatsapp_rehabilitation_event_missing'] += 1
        if _whatsapp_rehabilitation_has_open_block_alert(tenant):
            counts['whatsapp_rehabilitation_open_alerts'] += 1

    return dict(sorted(counts.items()))


def _whatsapp_rehabilitation_event_is_complete(tenant: Arrendatario) -> bool:
    if not tenant.whatsapp_rehabilitacion_ref.strip() or tenant.whatsapp_rehabilitado_at is None:
        return False
    expected_rehabilitated_at = tenant.whatsapp_rehabilitado_at.isoformat()
    events = AuditEvent.objects.filter(
        event_type=WHATSAPP_REHABILITATION_EVENT_TYPE,
        entity_type='arrendatario',
        entity_id=str(tenant.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if str(metadata.get('rehabilitacion_ref') or '').strip() != tenant.whatsapp_rehabilitacion_ref.strip():
            continue
        if str(metadata.get('whatsapp_rehabilitado_at') or '').strip() != expected_rehabilitated_at:
            continue
        if not _non_sensitive_reference(metadata.get('rehabilitacion_ref') or ''):
            continue
        return True
    return False


def _whatsapp_rehabilitation_has_open_block_alert(tenant: Arrendatario) -> bool:
    return ManualResolution.objects.filter(
        category=WHATSAPP_BLOCK_ALERT_CATEGORY,
        scope_type='arrendatario',
        scope_reference=str(tenant.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).exists()


def _sent_message_event_is_complete(event: AuditEvent, message: MensajeSaliente) -> bool:
    event_external_ref = str((event.metadata or {}).get('external_ref') or '').strip()
    if not event.actor_user_id and not event.actor_identifier.strip():
        return False
    if not event_external_ref or not _non_sensitive_reference(event_external_ref):
        return False
    return event_external_ref == message.external_ref.strip()


def _collect_message_issues(messages) -> dict[str, int]:
    counts = Counter()
    sent_message_ids = [
        str(message.pk)
        for message in messages
        if message.pk is not None and message.estado == EstadoMensajeSaliente.SENT
    ]
    sent_message_events = defaultdict(list)
    for event in AuditEvent.objects.filter(
        event_type=SENT_MESSAGE_EVENT_TYPE,
        entity_type='mensaje_saliente',
        entity_id__in=sent_message_ids,
    ):
        sent_message_events[event.entity_id].append(event)
    for message in messages:
        try:
            message.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if message.motivo_bloqueo.strip() and contains_sensitive_reference(message.motivo_bloqueo):
            counts['block_reason_sensitive'] += 1
        if message.estado == EstadoMensajeSaliente.SENT:
            if not message.external_ref.strip():
                counts['sent_without_external_ref'] += 1
            elif not _non_sensitive_reference(message.external_ref):
                counts['sent_with_sensitive_external_ref'] += 1
            if message.enviado_at is None:
                counts['sent_without_timestamp'] += 1
            message_events = sent_message_events.get(str(message.pk), [])
            if not message_events:
                counts['sent_without_audit_event'] += 1
            elif not any(_sent_message_event_is_complete(event, message) for event in message_events):
                counts['sent_audit_event_incomplete'] += 1
        if _message_operational_issue(message):
            counts['prepared_or_sent_not_ready'] += 1
        if message.estado in {EstadoMensajeSaliente.PREPARED, EstadoMensajeSaliente.SENT}:
            if (
                message.canal == CanalOperacion.WHATSAPP
                and (window_timestamp := whatsapp_message_window_timestamp(message))
                and not is_within_whatsapp_operational_window(window_timestamp)
            ):
                counts['whatsapp_window_violation'] += 1
            if document_delivery_blocking_reason(message.documento_emitido):
                counts['document_not_formalized'] += 1
    return dict(sorted(counts.items()))


def _collect_notification_config_issues(configs) -> dict[str, int]:
    counts = Counter()
    for config in configs:
        try:
            config.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if config.evidencia_configuracion_ref.strip() and not _non_sensitive_reference(
            config.evidencia_configuracion_ref
        ):
            counts['sensitive_reference'] += 1
    return dict(sorted(counts.items()))


def _collect_notification_schedule_issues(payments, active_notification_configs, notification_schedules) -> dict[str, int]:
    counts = Counter()
    configs_by_contract: dict[int, list[ConfiguracionNotificacionContrato]] = {}
    for config in active_notification_configs:
        configs_by_contract.setdefault(config.contrato_id, []).append(config)

    expected_keys = set()
    for payment in payments:
        if payment.estado_pago not in COLLECTABLE_PAYMENT_STATES:
            continue
        for config in configs_by_contract.get(payment.contrato_id, []):
            for day, _scheduled_date in expected_payment_notification_schedule(payment, config):
                expected_keys.add((payment.id, config.canal, day))

    actual_keys = set()
    for notification in notification_schedules:
        try:
            notification.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if notification.pago_mensual.estado_pago not in COLLECTABLE_PAYMENT_STATES:
            continue
        actual_keys.add((notification.pago_mensual_id, notification.canal, notification.dia_notificacion))
        if notification.estado == 'preparada' and not notification.mensaje_saliente_id:
            counts['prepared_without_message'] += 1

    counts['expected_for_collectable_payments'] = len(expected_keys)
    counts['missing_for_collectable_payments'] = len(expected_keys - actual_keys)
    return dict(sorted(counts.items()))


def _gate_contains_sensitive_reference(gate) -> bool:
    if isinstance(gate, CanalMensajeria):
        restrictions_sensitive = gate_restrictions_contain_sensitive_reference(gate.restricciones_operativas)
    else:
        restrictions_sensitive = contains_sensitive_reference(gate.restricciones_operativas, include_sensitive_keys=True)
    return (
        bool(gate.evidencia_ref.strip() and not _non_sensitive_reference(gate.evidencia_ref))
        or restrictions_sensitive
    )


def _webpay_manual_confirmation_event_is_complete(intent: IntentoPagoWebPay) -> bool:
    events = AuditEvent.objects.filter(
        event_type=WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
        entity_type='webpay_intento',
        entity_id=str(intent.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if str(metadata.get('external_ref') or '').strip() != intent.external_ref.strip():
            continue
        if str(metadata.get('pago_mensual_id') or '').strip() != str(intent.pago_mensual_id):
            continue
        if str(metadata.get('fecha_pago_webpay') or '').strip() != str(intent.fecha_pago_webpay):
            continue
        return True
    return False


def _webpay_prepare_event_is_complete(intent: IntentoPagoWebPay) -> bool:
    events = AuditEvent.objects.filter(
        event_type=WEBPAY_PREPARE_EVENT_TYPE,
        entity_type='webpay_intento',
        entity_id=str(intent.pk),
    )
    expected_metadata = {
        'estado': intent.estado,
        'pago_mensual_id': intent.pago_mensual_id,
        'gate_cobro_id': intent.gate_cobro_id,
        'provider_key': intent.provider_key,
        'return_url_ref': intent.return_url_ref,
    }
    if intent.motivo_bloqueo.strip():
        expected_metadata['motivo_bloqueo'] = intent.motivo_bloqueo
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if not event.actor_user_id and not event.actor_identifier.strip():
            continue
        if all(str(metadata.get(key, '')) == str(value) for key, value in expected_metadata.items()):
            return True
    return False


def _collect_webpay_intent_issues(intents) -> dict[str, int]:
    counts = Counter()
    for intent in intents:
        try:
            intent.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if contains_sensitive_reference(intent.provider_payload, include_sensitive_keys=True):
            counts['sensitive_provider_payload'] += 1
        if intent.motivo_bloqueo.strip() and contains_sensitive_reference(intent.motivo_bloqueo):
            counts['sensitive_block_reason'] += 1
        if intent.return_url_ref.strip() and not _non_sensitive_reference(intent.return_url_ref):
            counts['sensitive_return_url_ref'] += 1
        if intent.estado in {EstadoIntentoPagoWebPay.PREPARED, EstadoIntentoPagoWebPay.BLOCKED}:
            if not _webpay_prepare_event_is_complete(intent):
                counts['prepared_event_missing'] += 1
        if intent.estado == EstadoIntentoPagoWebPay.CONFIRMED_MANUAL:
            if not intent.external_ref.strip():
                counts['confirmed_without_external_ref'] += 1
            elif not _non_sensitive_reference(intent.external_ref):
                counts['confirmed_with_sensitive_external_ref'] += 1
            if intent.pago_mensual.estado_pago != EstadoPago.PAID:
                counts['confirmed_payment_not_paid'] += 1
            if not intent.pago_mensual.fecha_pago_webpay:
                counts['confirmed_payment_without_webpay_date'] += 1
            elif intent.fecha_pago_webpay and intent.pago_mensual.fecha_pago_webpay != intent.fecha_pago_webpay:
                counts['confirmed_payment_date_mismatch'] += 1
            if not _webpay_manual_confirmation_event_is_complete(intent):
                counts['confirmed_manual_event_missing'] += 1
    return dict(sorted(counts.items()))


def _collect_payment_overdue_issues(payments, reference_date) -> dict[str, int]:
    counts = Counter()
    for payment in payments:
        expected_days_late = max(0, (reference_date - payment.fecha_vencimiento).days)
        if payment.estado_pago == EstadoPago.PENDING and expected_days_late > 0:
            counts['pending_past_due'] += 1
        if payment.estado_pago == EstadoPago.OVERDUE and payment.dias_mora != expected_days_late:
            counts['overdue_days_stale'] += 1
    return dict(sorted(counts.items()))


def _expected_effective_code_effect(payment: PagoMensual) -> Decimal:
    return Decimal(payment.monto_calculado_clp or Decimal('0.00')) - Decimal(
        payment.monto_facturable_clp or Decimal('0.00')
    )


def _safe_decimal(value) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _effective_code_event_is_complete(payment: PagoMensual, expected_effect: Decimal) -> bool:
    if not expected_effect:
        return True
    events = AuditEvent.objects.filter(
        event_type=EFFECTIVE_CODE_APPLIED_EVENT_TYPE,
        entity_type='pago_mensual',
        entity_id=str(payment.pk),
    )
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        actor_identifier = (event.actor_identifier or '').strip()
        if not event.actor_user_id and not actor_identifier:
            continue
        if str(metadata.get('codigo_conciliacion_efectivo') or '').strip() != payment.codigo_conciliacion_efectivo:
            continue
        metadata_effect = _safe_decimal(metadata.get('monto_efecto_codigo_efectivo_clp') or '0.00')
        if metadata_effect != expected_effect:
            continue
        metadata_billable = _safe_decimal(metadata.get('monto_facturable_clp') or '0.00')
        if metadata_billable != Decimal(payment.monto_facturable_clp or Decimal('0.00')):
            continue
        metadata_calculated = _safe_decimal(metadata.get('monto_calculado_clp') or '0.00')
        if metadata_calculated != Decimal(payment.monto_calculado_clp or Decimal('0.00')):
            continue
        return True
    return False


def _collect_payment_effective_code_issues(payments) -> dict[str, int]:
    counts = Counter()
    for payment in payments:
        expected_effect = _expected_effective_code_effect(payment)
        if Decimal(payment.monto_efecto_codigo_efectivo_clp or Decimal('0.00')) != expected_effect:
            counts['effective_code_effect_mismatch'] += 1
        if expected_effect and not _effective_code_event_is_complete(payment, expected_effect):
            counts['effective_code_event_missing'] += 1
    return dict(sorted(counts.items()))


def _exceptional_payment_event_is_complete(payment: PagoMensual) -> bool:
    events = AuditEvent.objects.filter(
        event_type=EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
        entity_type='pago_mensual',
        entity_id=str(payment.pk),
    )
    expected_ref = str(payment.resolucion_pago_excepcional_ref or '').strip()
    expected_reason = str(payment.resolucion_pago_excepcional_motivo or '').strip()
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        actor_identifier = (event.actor_identifier or '').strip()
        if not event.actor_user_id and not actor_identifier:
            continue
        if str(metadata.get('estado_pago') or '').strip() != payment.estado_pago:
            continue
        if str(metadata.get('resolucion_pago_excepcional_ref') or '').strip() != expected_ref:
            continue
        if str(metadata.get('resolucion_pago_excepcional_motivo') or '').strip() != expected_reason:
            continue
        return True
    return False


def _collect_payment_exceptional_resolution_issues(payments) -> dict[str, int]:
    counts = Counter()
    exceptional_states = {EstadoPago.PAID_BY_TERMINATION, EstadoPago.FORGIVEN}
    for payment in payments:
        if payment.estado_pago not in exceptional_states:
            continue
        resolution_ref = str(payment.resolucion_pago_excepcional_ref or '').strip()
        resolution_reason = str(payment.resolucion_pago_excepcional_motivo or '').strip()
        if (
            not resolution_ref
            or not resolution_reason
            or not _non_sensitive_reference(resolution_ref)
            or contains_sensitive_reference(resolution_reason)
        ):
            counts['exceptional_resolution_missing'] += 1
            continue
        if not _exceptional_payment_event_is_complete(payment):
            counts['exceptional_resolution_event_missing'] += 1
    return dict(sorted(counts.items()))


def _collect_payment_repayment_trace_issues(payments) -> dict[str, int]:
    counts = Counter()
    repayment_states = {EstadoPago.IN_REPAYMENT, EstadoPago.PAID_VIA_REPAYMENT}
    for payment in payments:
        has_repayment = bool(payment.repactacion_deuda_id)
        if payment.estado_pago in repayment_states and not has_repayment:
            counts['repayment_state_without_plan'] += 1
            continue
        if payment.estado_pago not in repayment_states and has_repayment:
            counts['repayment_link_on_non_repayment_state'] += 1
            continue
        if not has_repayment:
            continue

        repayment = payment.repactacion_deuda
        if repayment.contrato_origen_id != payment.contrato_id:
            counts['repayment_plan_contract_mismatch'] += 1
            continue
        if repayment.arrendatario_id != payment.contrato.arrendatario_id:
            counts['repayment_plan_tenant_mismatch'] += 1
            continue
        if payment.estado_pago == EstadoPago.IN_REPAYMENT and repayment.estado != 'activa':
            counts['in_repayment_plan_not_active'] += 1
        if payment.estado_pago == EstadoPago.PAID_VIA_REPAYMENT and repayment.estado != 'cumplida':
            counts['paid_via_repayment_plan_not_completed'] += 1
    return dict(sorted(counts.items()))


def _payment_requires_uf_trace(payment: PagoMensual) -> bool:
    if payment.periodo_contractual.moneda_base == MonedaBaseContrato.UF:
        return True
    month_start = date(int(payment.anio), int(payment.mes), 1)
    return AjusteContrato.objects.filter(
        contrato=payment.contrato,
        activo=True,
        moneda=MonedaBaseContrato.UF,
        mes_inicio__lte=month_start,
        mes_fin__gte=month_start,
    ).exists()


def _collect_payment_uf_trace_issues(payments) -> dict[str, int]:
    counts = Counter()
    for payment in payments:
        if not _payment_requires_uf_trace(payment):
            if payment.moneda_calculo == MonedaBaseContrato.UF or payment.uf_fecha_usada or payment.uf_valor_usado is not None or payment.uf_source_key:
                counts['uf_trace_on_non_uf_payment'] += 1
            continue

        if (
            payment.moneda_calculo != MonedaBaseContrato.UF
            or not payment.uf_fecha_usada
            or payment.uf_valor_usado is None
            or not str(payment.uf_source_key or '').strip()
        ):
            counts['uf_trace_missing'] += 1
            continue

        if payment.uf_fecha_usada != payment.fecha_vencimiento:
            counts['uf_date_mismatch'] += 1
        uf_record = ValorUFDiario.objects.filter(fecha=payment.fecha_vencimiento).first()
        if not uf_record:
            counts['uf_value_missing_for_effective_date'] += 1
            continue
        if payment.uf_valor_usado != uf_record.valor:
            counts['uf_value_mismatch'] += 1
        if payment.uf_source_key not in CANONICAL_UF_SOURCE_KEYS:
            counts['uf_source_not_canonical'] += 1
        elif payment.uf_source_key != uf_record.source_key:
            counts['uf_source_mismatch'] += 1
    return dict(sorted(counts.items()))


def _collect_account_state_issues(account_states, required_tenant_ids: set[int], reference_date) -> dict[str, int]:
    counts = Counter()
    existing_tenant_ids: set[int] = set()
    for state in account_states:
        existing_tenant_ids.add(state.arrendatario_id)
        if contains_sensitive_reference(state.observaciones, include_sensitive_keys=True):
            counts['sensitive_observations'] += 1
        try:
            state.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        summary = state.resumen_operativo
        if not isinstance(summary, dict):
            counts['invalid_summary_shape'] += 1
            continue

        expected = build_account_state_summary(state.arrendatario, reference_date=reference_date)
        missing_keys = set(expected) - set(summary)
        if missing_keys:
            counts['missing_summary_keys'] += 1
            continue

        if any(str(summary.get(key)) != str(expected_value) for key, expected_value in expected.items()):
            counts['stale_summary'] += 1

        expected_score = expected.get('score_pago_porcentaje')
        if expected_score is not None and state.score_pago is None:
            counts['missing_score'] += 1
        elif state.score_pago != expected_score:
            counts['stale_score'] += 1

    counts['missing_for_active_tenant'] = len(required_tenant_ids - existing_tenant_ids)
    return dict(sorted(counts.items()))


def collect_stage2_cobranza_readiness(
    *,
    stage1_evidence_ref: str = '',
    email_proof_ref: str = '',
    webpay_proof_ref: str = '',
    responsible_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
    reference_date=None,
) -> dict[str, Any]:
    reference_date = reference_date or timezone.localdate()
    identities = IdentidadDeEnvio.objects.select_related('empresa_owner', 'socio_owner')
    channel_assignments = AsignacionCanalOperacion.objects.select_related(
        'mandato_operacion',
        'identidad_envio',
        'identidad_envio__empresa_owner',
        'identidad_envio__socio_owner',
    )
    invalid_identities = _count_invalid(identities)
    invalid_assignments = _count_invalid(channel_assignments)

    email_active_identities = identities.filter(
        canal=CanalOperacion.EMAIL,
        estado=EstadoIdentidadEnvio.ACTIVE,
    )
    whatsapp_active_identities = identities.filter(
        canal=CanalOperacion.WHATSAPP,
        estado=EstadoIdentidadEnvio.ACTIVE,
    )
    email_active_assignments = channel_assignments.filter(
        canal=CanalOperacion.EMAIL,
        estado=EstadoAsignacionCanal.ACTIVE,
        identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
        mandato_operacion__estado=EstadoMandatoOperacion.ACTIVE,
    )
    whatsapp_active_assignments = channel_assignments.filter(
        canal=CanalOperacion.WHATSAPP,
        estado=EstadoAsignacionCanal.ACTIVE,
        identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
        mandato_operacion__estado=EstadoMandatoOperacion.ACTIVE,
    )
    whatsapp_opt_in_tenants = Arrendatario.objects.filter(whatsapp_opt_in=True)
    invalid_whatsapp_opt_in_tenants = _count_invalid(whatsapp_opt_in_tenants)
    whatsapp_opt_in_invalid_phone = sum(
        1
        for tenant in whatsapp_opt_in_tenants
        if not is_international_phone_number(tenant.telefono)
    )
    whatsapp_opt_in_sensitive_refs = sum(
        1
        for tenant in whatsapp_opt_in_tenants
        if tenant.whatsapp_opt_in_evidencia_ref.strip()
        and not _non_sensitive_reference(tenant.whatsapp_opt_in_evidencia_ref)
    )
    whatsapp_blocked_tenants = Arrendatario.objects.filter(whatsapp_bloqueado=True)
    whatsapp_block_issues = _collect_whatsapp_block_issues(whatsapp_blocked_tenants)
    whatsapp_rehabilitated_tenants = Arrendatario.objects.filter(
        Q(whatsapp_rehabilitacion_ref__gt='') | Q(whatsapp_rehabilitado_at__isnull=False)
    )
    whatsapp_rehabilitation_issues = _collect_whatsapp_rehabilitation_issues(whatsapp_rehabilitated_tenants)

    channel_gates = CanalMensajeria.objects.all()
    email_open_gates = channel_gates.filter(canal=CanalOperacion.EMAIL, estado_gate=EstadoGateCanal.OPEN)
    whatsapp_open_gates = channel_gates.filter(canal=CanalOperacion.WHATSAPP, estado_gate=EstadoGateCanal.OPEN)
    invalid_channel_gates = _count_invalid(channel_gates)
    valid_email_open_gates = email_open_gates.count() - _count_invalid(email_open_gates)
    whatsapp_open_without_template = sum(
        1 for gate in whatsapp_open_gates if not whatsapp_gate_has_approved_template(gate)
    )
    sensitive_channel_gate_refs = sum(1 for gate in channel_gates if _gate_contains_sensitive_reference(gate))

    active_contracts = Contrato.objects.select_related('mandato_operacion').filter(
        estado__in=(EstadoContrato.ACTIVE, EstadoContrato.FUTURE),
    )
    active_assignment_pairs = set(
        channel_assignments.filter(
            estado=EstadoAsignacionCanal.ACTIVE,
            identidad_envio__estado=EstadoIdentidadEnvio.ACTIVE,
            mandato_operacion__estado=EstadoMandatoOperacion.ACTIVE,
        ).values_list('mandato_operacion_id', 'canal')
    )
    required_notification_pairs = {
        (contract.id, canal)
        for contract in active_contracts
        for mandato_id, canal in active_assignment_pairs
        if mandato_id == contract.mandato_operacion_id
    }
    notification_configs = ConfiguracionNotificacionContrato.objects.select_related(
        'contrato',
        'contrato__mandato_operacion',
    )
    active_notification_configs = notification_configs.filter(activa=True)
    active_notification_pairs = set(active_notification_configs.values_list('contrato_id', 'canal'))
    notification_config_issues = _collect_notification_config_issues(notification_configs)
    notification_configs_missing_for_enabled_channel = len(required_notification_pairs - active_notification_pairs)

    messages = MensajeSaliente.objects.select_related(
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'contrato__mandato_operacion',
        'arrendatario',
        'documento_emitido',
    )
    message_issues = _collect_message_issues(messages)
    whatsapp_fallback_issues = _collect_whatsapp_fallback_issues(messages)

    webpay_gates = GateCobroExterno.objects.all()
    webpay_open_gates = webpay_gates.filter(estado_gate=EstadoGateCobroExterno.OPEN)
    invalid_webpay_gates = _count_invalid(webpay_gates)
    valid_webpay_open_gates = webpay_open_gates.count() - _count_invalid(webpay_open_gates)
    sensitive_webpay_gate_refs = sum(1 for gate in webpay_gates if _gate_contains_sensitive_reference(gate))
    webpay_intents = IntentoPagoWebPay.objects.select_related('pago_mensual', 'gate_cobro')
    webpay_intent_issues = _collect_webpay_intent_issues(webpay_intents)
    invalid_webpay_intents = webpay_intent_issues.get('invalid_model', 0)

    payments = PagoMensual.objects.select_related('contrato__arrendatario', 'repactacion_deuda')
    notification_schedules = NotificacionCobranzaProgramada.objects.select_related(
        'pago_mensual',
        'pago_mensual__contrato',
        'configuracion',
        'mensaje_saliente',
    )
    notification_schedule_issues = _collect_notification_schedule_issues(
        payments,
        active_notification_configs,
        notification_schedules,
    )
    payment_overdue_issues = _collect_payment_overdue_issues(payments, reference_date)
    payment_effective_code_issues = _collect_payment_effective_code_issues(payments)
    payment_exceptional_resolution_issues = _collect_payment_exceptional_resolution_issues(payments)
    payment_repayment_issues = _collect_payment_repayment_trace_issues(payments)
    payment_uf_trace_issues = _collect_payment_uf_trace_issues(payments)
    payments_total = payments.count()
    uf_values = ValorUFDiario.objects.all()
    uf_value_issues = _collect_uf_value_issues(uf_values)
    repayments = RepactacionDeuda.objects.select_related('arrendatario', 'contrato_origen')
    repayment_issues = _collect_repayment_issues(repayments)
    invalid_repayments = repayment_issues.get('invalid_model', 0)
    residual_codes = CodigoCobroResidual.objects.select_related('arrendatario', 'contrato_origen')
    invalid_residual_codes = _count_invalid(residual_codes)
    account_state_required_tenant_ids = {
        tenant_id
        for tenant_id in [
            *payments.values_list('contrato__arrendatario_id', flat=True),
            *repayments.values_list('arrendatario_id', flat=True),
            *residual_codes.values_list('arrendatario_id', flat=True),
        ]
        if tenant_id
    }
    account_states = EstadoCuentaArrendatario.objects.select_related('arrendatario')
    account_state_issues = _collect_account_state_issues(account_states, account_state_required_tenant_ids, reference_date)
    final_evidence = {
        'stage1_evidence_ref': _non_sensitive_reference(stage1_evidence_ref),
        'email_proof_ref': _non_sensitive_reference(email_proof_ref),
        'webpay_proof_ref': _non_sensitive_reference(webpay_proof_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE2_SOURCE_KINDS

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage2.source_kind_not_authorized',
                'La readiness local de Etapa 2 no puede cerrar Cobranza sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, code, message in [
            (
                'source_label',
                'stage2.source_label_missing',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 2.',
            ),
            (
                'authorization_ref',
                'stage2.authorization_ref_missing',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 2.',
            ),
        ]:
            if not source_trace[key]:
                issues.append(_issue(code, message))
    if payments_total == 0:
        issues.append(
            _issue(
                'stage2.payments_missing',
                'No existen pagos mensuales locales para validar cobranza activa.',
            )
        )
    if payment_overdue_issues.get('pending_past_due'):
        issues.append(
            _issue(
                'stage2.payment.pending_past_due',
                'Existen pagos pendientes ya vencidos que deben refrescarse como atrasados antes de cerrar cobranza.',
                count=payment_overdue_issues['pending_past_due'],
            )
        )
    if payment_overdue_issues.get('overdue_days_stale'):
        issues.append(
            _issue(
                'stage2.payment.overdue_days_stale',
                'Existen pagos atrasados cuyo dias_mora no coincide con la fecha de corte auditada.',
                count=payment_overdue_issues['overdue_days_stale'],
            )
        )
    if payment_effective_code_issues.get('effective_code_effect_mismatch'):
        issues.append(
            _issue(
                'stage2.payment.effective_code_effect_mismatch',
                'Existen pagos cuyo efecto de codigo efectivo no cuadra con monto calculado menos monto facturable.',
                count=payment_effective_code_issues['effective_code_effect_mismatch'],
            )
        )
    if payment_effective_code_issues.get('effective_code_event_missing'):
        issues.append(
            _issue(
                'stage2.payment.effective_code_event_missing',
                'Existen pagos con efecto de codigo efectivo sin evento auditable con actor y montos alineados.',
                count=payment_effective_code_issues['effective_code_event_missing'],
            )
        )
    if payment_exceptional_resolution_issues.get('exceptional_resolution_missing'):
        issues.append(
            _issue(
                'stage2.payment.exceptional_resolution_missing',
                'Existen pagos por acuerdo de termino o condonados sin referencia/motivo trazable no sensible.',
                count=payment_exceptional_resolution_issues['exceptional_resolution_missing'],
            )
        )
    if payment_exceptional_resolution_issues.get('exceptional_resolution_event_missing'):
        issues.append(
            _issue(
                'stage2.payment.exceptional_resolution_event_missing',
                'Existen pagos por acuerdo de termino o condonados sin evento auditable con actor y resolucion alineada.',
                count=payment_exceptional_resolution_issues['exceptional_resolution_event_missing'],
            )
        )
    if payment_repayment_issues.get('repayment_state_without_plan'):
        issues.append(
            _issue(
                'stage2.payment.repayment_state_without_plan',
                'Existen pagos en estado de repactacion sin una repactacion trazable enlazada.',
                count=payment_repayment_issues['repayment_state_without_plan'],
            )
        )
    if payment_repayment_issues.get('repayment_link_on_non_repayment_state'):
        issues.append(
            _issue(
                'stage2.payment.repayment_link_on_non_repayment_state',
                'Existen pagos que enlazan repactacion sin estar en estado de repactacion.',
                count=payment_repayment_issues['repayment_link_on_non_repayment_state'],
            )
        )
    if payment_repayment_issues.get('repayment_plan_contract_mismatch'):
        issues.append(
            _issue(
                'stage2.payment.repayment_plan_contract_mismatch',
                'Existen pagos enlazados a repactaciones de otro contrato.',
                count=payment_repayment_issues['repayment_plan_contract_mismatch'],
            )
        )
    if payment_repayment_issues.get('repayment_plan_tenant_mismatch'):
        issues.append(
            _issue(
                'stage2.payment.repayment_plan_tenant_mismatch',
                'Existen pagos enlazados a repactaciones de otro arrendatario.',
                count=payment_repayment_issues['repayment_plan_tenant_mismatch'],
            )
        )
    if payment_repayment_issues.get('in_repayment_plan_not_active'):
        issues.append(
            _issue(
                'stage2.payment.in_repayment_plan_not_active',
                'Existen pagos en repactacion cuyo plan no esta activo.',
                count=payment_repayment_issues['in_repayment_plan_not_active'],
            )
        )
    if payment_repayment_issues.get('paid_via_repayment_plan_not_completed'):
        issues.append(
            _issue(
                'stage2.payment.paid_via_repayment_plan_not_completed',
                'Existen pagos pagados via repactacion cuyo plan no esta cumplido.',
                count=payment_repayment_issues['paid_via_repayment_plan_not_completed'],
            )
        )
    if payment_uf_trace_issues.get('uf_trace_missing'):
        issues.append(
            _issue(
                'stage2.payment.uf_trace_missing',
                'Existen pagos calculados en UF sin moneda, fecha, valor o fuente UF persistidos.',
                count=payment_uf_trace_issues['uf_trace_missing'],
            )
        )
    if payment_uf_trace_issues.get('uf_date_mismatch'):
        issues.append(
            _issue(
                'stage2.payment.uf_date_mismatch',
                'Existen pagos con fecha UF usada distinta a la fecha de vencimiento del cobro.',
                count=payment_uf_trace_issues['uf_date_mismatch'],
            )
        )
    if payment_uf_trace_issues.get('uf_value_missing_for_effective_date'):
        issues.append(
            _issue(
                'stage2.payment.uf_value_missing_for_effective_date',
                'Existen pagos en UF sin ValorUFDiario para la fecha efectiva del cobro.',
                count=payment_uf_trace_issues['uf_value_missing_for_effective_date'],
            )
        )
    if payment_uf_trace_issues.get('uf_value_mismatch'):
        issues.append(
            _issue(
                'stage2.payment.uf_value_mismatch',
                'Existen pagos con valor UF persistido distinto al ValorUFDiario de la fecha efectiva.',
                count=payment_uf_trace_issues['uf_value_mismatch'],
            )
        )
    if payment_uf_trace_issues.get('uf_source_not_canonical') or payment_uf_trace_issues.get('uf_source_mismatch'):
        issues.append(
            _issue(
                'stage2.payment.uf_source_invalid',
                'Existen pagos con fuente UF no canonica o distinta al ValorUFDiario de la fecha efectiva.',
                count=payment_uf_trace_issues.get('uf_source_not_canonical', 0)
                + payment_uf_trace_issues.get('uf_source_mismatch', 0),
            )
        )
    if payment_uf_trace_issues.get('uf_trace_on_non_uf_payment'):
        issues.append(
            _issue(
                'stage2.payment.uf_trace_on_non_uf_payment',
                'Existen pagos que conservan traza UF sin depender de UF en periodo ni ajustes.',
                count=payment_uf_trace_issues['uf_trace_on_non_uf_payment'],
            )
        )
    if uf_value_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage2.uf_value.invalid_model',
                'Existen valores UF que no pasan validacion de dominio/procedencia.',
                count=uf_value_issues['invalid_model'],
            )
        )
    if uf_value_issues.get('source_not_canonical'):
        issues.append(
            _issue(
                'stage2.uf_value.source_not_canonical',
                'Existen valores UF con fuente fuera de la cadena canonica BancoCentral/CMF/MiIndicador/manual auditada.',
                count=uf_value_issues['source_not_canonical'],
            )
        )
    if uf_value_issues.get('manual_without_audit_event'):
        issues.append(
            _issue(
                'stage2.uf_value.manual_audit_missing',
                'Existen valores UF cargados manualmente sin evento auditable con actor y refs trazables.',
                count=uf_value_issues['manual_without_audit_event'],
            )
        )
    if invalid_repayments:
        issues.append(
            _issue(
                'stage2.repayment.invalid_model',
                'Existen repactaciones de deuda que no pasan validacion de dominio.',
                count=invalid_repayments,
            )
        )
    if repayment_issues.get('partial_without_exception'):
        issues.append(
            _issue(
                'stage2.repayment.partial_without_exception',
                'Existen repactaciones parciales sin excepcion formal y motivo auditable.',
                count=repayment_issues['partial_without_exception'],
            )
        )
    if repayment_issues.get('partial_without_audit_event'):
        issues.append(
            _issue(
                'stage2.repayment.partial_without_audit_event',
                'Existen repactaciones parciales cuya excepcion formal no tiene evento auditable con actor.',
                count=repayment_issues['partial_without_audit_event'],
            )
        )
    if invalid_residual_codes:
        issues.append(
            _issue(
                'stage2.residual_code.invalid_model',
                'Existen codigos de cobro residual que no pasan validacion de dominio.',
                count=invalid_residual_codes,
            )
        )
    if account_state_issues.get('missing_for_active_tenant'):
        issues.append(
            _issue(
                'stage2.account_state.missing',
                'Existen arrendatarios con cobranza activa sin estado de cuenta recalculado.',
                count=account_state_issues['missing_for_active_tenant'],
            )
        )
    if account_state_issues.get('stale_summary'):
        issues.append(
            _issue(
                'stage2.account_state.stale_summary',
                'Existen estados de cuenta cuyo resumen no coincide con pagos, repactaciones y codigos residuales.',
                count=account_state_issues['stale_summary'],
            )
        )
    if account_state_issues.get('missing_score'):
        issues.append(
            _issue(
                'stage2.account_state.missing_score',
                'Existen estados de cuenta con pagos evaluables sin score de pago calculado.',
                count=account_state_issues['missing_score'],
            )
        )
    if account_state_issues.get('stale_score'):
        issues.append(
            _issue(
                'stage2.account_state.stale_score',
                'Existen estados de cuenta cuyo score de pago no coincide con los pagos operativos.',
                count=account_state_issues['stale_score'],
            )
        )
    if account_state_issues.get('missing_summary_keys'):
        issues.append(
            _issue(
                'stage2.account_state.missing_summary_keys',
                'Existen estados de cuenta con resumen operativo incompleto.',
                count=account_state_issues['missing_summary_keys'],
            )
        )
    if account_state_issues.get('invalid_summary_shape'):
        issues.append(
            _issue(
                'stage2.account_state.invalid_summary_shape',
                'Existen estados de cuenta con resumen operativo no estructurado.',
                count=account_state_issues['invalid_summary_shape'],
            )
        )
    if account_state_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage2.account_state.invalid_model',
                'Existen estados de cuenta que no pasan validacion de dominio.',
                count=account_state_issues['invalid_model'],
            )
        )
    if account_state_issues.get('sensitive_observations'):
        issues.append(
            _issue(
                'stage2.account_state.sensitive_observations',
                'Existen estados de cuenta con observaciones que parecen contener referencias sensibles.',
                count=account_state_issues['sensitive_observations'],
            )
        )
    if valid_email_open_gates <= 0:
        issues.append(
            _issue(
                'stage2.email.open_gate_missing',
                'Etapa 2 requiere al menos un gate Email abierto y valido para cierre.',
            )
        )
    if email_active_identities.count() <= 0:
        issues.append(
            _issue(
                'stage2.email.active_identity_missing',
                'Etapa 2 requiere al menos una IdentidadDeEnvio Email activa para no inventar remitente.',
            )
        )
    if email_active_assignments.count() <= 0:
        issues.append(
            _issue(
                'stage2.email.active_assignment_missing',
                'Etapa 2 requiere al menos una asignacion Email activa sobre mandato operativo activo.',
            )
        )
    if invalid_identities:
        issues.append(
            _issue(
                'stage2.channel_identity_invalid',
                'Existen identidades de envio que no pasan validacion de dominio.',
                count=invalid_identities,
            )
        )
    if invalid_assignments:
        issues.append(
            _issue(
                'stage2.channel_assignment_invalid',
                'Existen asignaciones de canal que no pasan validacion de dominio.',
                count=invalid_assignments,
            )
        )
    if invalid_channel_gates:
        issues.append(
            _issue(
                'stage2.channel_gate_invalid',
                'Existen gates de canales que no pasan validacion de dominio.',
                count=invalid_channel_gates,
            )
        )
    if sensitive_channel_gate_refs:
        issues.append(
            _issue(
                'stage2.channel_gate_sensitive_reference',
                'Existen gates de canales con evidencia_ref o restricciones_operativas sensibles.',
                count=sensitive_channel_gate_refs,
            )
        )
    if notification_configs_missing_for_enabled_channel:
        issues.append(
            _issue(
                'stage2.notification_config.missing_for_enabled_channel',
                'Existen contratos vigentes/futuros con canal habilitado sin cadencia de notificaciones activa.',
                count=notification_configs_missing_for_enabled_channel,
            )
        )
    if notification_config_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage2.notification_config.invalid_model',
                'Existen configuraciones de notificacion por contrato/canal que no pasan validacion de dominio.',
                count=notification_config_issues['invalid_model'],
            )
        )
    if notification_config_issues.get('sensitive_reference'):
        issues.append(
            _issue(
                'stage2.notification_config.sensitive_reference',
                'Existen configuraciones de notificacion con evidencia_configuracion_ref sensible.',
                count=notification_config_issues['sensitive_reference'],
            )
        )
    if notification_schedule_issues.get('missing_for_collectable_payments'):
        issues.append(
            _issue(
                'stage2.notification_schedule.missing_for_collectable_payment',
                'Existen pagos pendientes/atrasados sin programacion local de recordatorios segun su cadencia activa.',
                count=notification_schedule_issues['missing_for_collectable_payments'],
            )
        )
    if notification_schedule_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage2.notification_schedule.invalid_model',
                'Existen recordatorios de cobranza programados que no pasan validacion de dominio.',
                count=notification_schedule_issues['invalid_model'],
            )
        )
    if notification_schedule_issues.get('prepared_without_message'):
        issues.append(
            _issue(
                'stage2.notification_schedule.prepared_without_message',
                'Existen recordatorios marcados preparados sin mensaje saliente trazable.',
                count=notification_schedule_issues['prepared_without_message'],
            )
        )
    if whatsapp_open_without_template:
        issues.append(
            _issue(
                'stage2.whatsapp.template_missing',
                'WhatsApp abierto requiere template aprobado registrado en el gate.',
                count=whatsapp_open_without_template,
            )
        )
    if invalid_whatsapp_opt_in_tenants:
        issues.append(
            _issue(
                'stage2.whatsapp.opt_in_invalid',
                'Existen opt-in WhatsApp que no pasan validacion de dominio.',
                count=invalid_whatsapp_opt_in_tenants,
            )
        )
    if whatsapp_opt_in_invalid_phone:
        issues.append(
            _issue(
                'stage2.whatsapp.phone_invalid',
                'Existen opt-in WhatsApp con telefono fuera de formato internacional.',
                count=whatsapp_opt_in_invalid_phone,
            )
        )
    if whatsapp_opt_in_sensitive_refs:
        issues.append(
            _issue(
                'stage2.whatsapp.opt_in_evidence_sensitive',
                'Existen opt-in WhatsApp con evidencia_ref sensible.',
                count=whatsapp_opt_in_sensitive_refs,
            )
        )
    if whatsapp_block_issues.get('whatsapp_block_trace_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_trace_missing',
                'Existen bloqueos definitivos WhatsApp sin motivo, evidencia o fecha trazable.',
                count=whatsapp_block_issues['whatsapp_block_trace_missing'],
            )
        )
    if whatsapp_block_issues.get('whatsapp_block_evidence_sensitive'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_evidence_sensitive',
                'Existen bloqueos definitivos WhatsApp con evidencia_ref sensible.',
                count=whatsapp_block_issues['whatsapp_block_evidence_sensitive'],
            )
        )
    if whatsapp_block_issues.get('whatsapp_block_motive_sensitive'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_motive_sensitive',
                'Existen bloqueos definitivos WhatsApp con motivo sensible heredado.',
                count=whatsapp_block_issues['whatsapp_block_motive_sensitive'],
            )
        )
    if whatsapp_block_issues.get('whatsapp_block_event_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_event_missing',
                'Existen bloqueos definitivos WhatsApp sin evento auditable con actor y evidencia alineada.',
                count=whatsapp_block_issues['whatsapp_block_event_missing'],
            )
        )
    if whatsapp_block_issues.get('whatsapp_block_alert_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_alert_missing',
                'Existen bloqueos definitivos WhatsApp sin alerta administrativa trazable y alineada.',
                count=whatsapp_block_issues['whatsapp_block_alert_missing'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_trace_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_trace_missing',
                'Existen rehabilitaciones WhatsApp sin referencia o fecha trazable.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_trace_missing'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_sensitive_refs'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_ref_sensitive',
                'Existen rehabilitaciones WhatsApp con referencia sensible.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_sensitive_refs'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_block_trace_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_block_trace_missing',
                'Existen rehabilitaciones WhatsApp sin conservar motivo, evidencia o fecha del bloqueo original.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_block_trace_missing'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_block_event_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_block_event_missing',
                'Existen rehabilitaciones WhatsApp sin evento de bloqueo original completo.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_block_event_missing'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_block_alert_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_block_alert_missing',
                'Existen rehabilitaciones WhatsApp sin alerta administrativa original resuelta y alineada.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_block_alert_missing'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_event_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_event_missing',
                'Existen rehabilitaciones WhatsApp sin evento auditable dedicado con actor y referencia alineada.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_event_missing'],
            )
        )
    if whatsapp_rehabilitation_issues.get('whatsapp_rehabilitation_open_alerts'):
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_alert_open',
                'Existen rehabilitaciones WhatsApp que dejaron alertas administrativas abiertas.',
                count=whatsapp_rehabilitation_issues['whatsapp_rehabilitation_open_alerts'],
            )
        )
    if whatsapp_open_gates.count() > 0 and whatsapp_active_identities.count() <= 0:
        issues.append(
            _issue(
                'stage2.whatsapp.active_identity_missing',
                'WhatsApp abierto requiere una IdentidadDeEnvio WhatsApp activa.',
            )
        )
    if whatsapp_open_gates.count() > 0 and whatsapp_active_assignments.count() <= 0:
        issues.append(
            _issue(
                'stage2.whatsapp.active_assignment_missing',
                'WhatsApp abierto requiere asignacion activa sobre mandato operativo activo.',
            )
        )
    if message_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage2.message.invalid_model',
                'Existen mensajes salientes que no pasan validacion de dominio.',
                count=message_issues['invalid_model'],
            )
        )
    if message_issues.get('sent_without_external_ref'):
        issues.append(
            _issue(
                'stage2.message.sent_without_external_ref',
                'Existen mensajes marcados enviados sin external_ref trazable.',
                count=message_issues['sent_without_external_ref'],
            )
        )
    if message_issues.get('sent_with_sensitive_external_ref'):
        issues.append(
            _issue(
                'stage2.message.sent_with_sensitive_external_ref',
                'Existen mensajes marcados enviados con external_ref sensible.',
                count=message_issues['sent_with_sensitive_external_ref'],
            )
        )
    if message_issues.get('sent_without_timestamp'):
        issues.append(
            _issue(
                'stage2.message.sent_without_timestamp',
                'Existen mensajes marcados enviados sin timestamp de envio.',
                count=message_issues['sent_without_timestamp'],
            )
        )
    if message_issues.get('sent_without_audit_event'):
        issues.append(
            _issue(
                'stage2.message.sent_without_audit_event',
                'Existen mensajes marcados enviados sin evento auditable de envio manual.',
                count=message_issues['sent_without_audit_event'],
            )
        )
    if message_issues.get('sent_audit_event_incomplete'):
        issues.append(
            _issue(
                'stage2.message.sent_audit_event_incomplete',
                'Existen mensajes enviados cuyo evento auditable no conserva actor y external_ref trazable alineado.',
                count=message_issues['sent_audit_event_incomplete'],
            )
        )
    if message_issues.get('block_reason_sensitive'):
        issues.append(
            _issue(
                'stage2.message.block_reason_sensitive',
                'Existen mensajes salientes con motivo de bloqueo sensible heredado.',
                count=message_issues['block_reason_sensitive'],
            )
        )
    if message_issues.get('prepared_or_sent_not_ready'):
        issues.append(
            _issue(
                'stage2.message.prepared_or_sent_not_ready',
                'Existen mensajes preparados/enviados sin gate, identidad, destinatario o mandato operativo valido.',
                count=message_issues['prepared_or_sent_not_ready'],
            )
        )
    if message_issues.get('whatsapp_window_violation'):
        issues.append(
            _issue(
                'stage2.message.whatsapp_window_violation',
                'Existen mensajes WhatsApp preparados/enviados fuera de 08:00-21:00 America/Santiago.',
                count=message_issues['whatsapp_window_violation'],
            )
        )
    if message_issues.get('document_not_formalized'):
        issues.append(
            _issue(
                'stage2.message.document_not_formalized',
                'Existen mensajes preparados/enviados con documentos que requieren formalizacion previa.',
                count=message_issues['document_not_formalized'],
            )
        )
    if whatsapp_fallback_issues.get('without_fallback_trace'):
        issues.append(
            _issue(
                'stage2.whatsapp.fallback_trace_missing',
                'Existen mensajes WhatsApp bloqueados/fallidos sin Email alternativo ni alerta critica trazable.',
                count=whatsapp_fallback_issues['without_fallback_trace'],
            )
        )
    if valid_webpay_open_gates <= 0:
        issues.append(
            _issue(
                'stage2.webpay.open_gate_missing',
                'Etapa 2 requiere al menos un gate WebPay abierto y valido para cierre.',
            )
        )
    if invalid_webpay_gates:
        issues.append(
            _issue(
                'stage2.webpay_gate_invalid',
                'Existen gates WebPay que no pasan validacion de dominio.',
                count=invalid_webpay_gates,
            )
        )
    if sensitive_webpay_gate_refs:
        issues.append(
            _issue(
                'stage2.webpay_gate_sensitive_reference',
                'Existen gates WebPay con evidencia_ref o restricciones_operativas sensibles.',
                count=sensitive_webpay_gate_refs,
            )
        )
    if invalid_webpay_intents:
        issues.append(
            _issue(
                'stage2.webpay_intent_invalid',
                'Existen intentos WebPay que no pasan validacion de dominio.',
                count=invalid_webpay_intents,
            )
        )
    if webpay_intent_issues.get('sensitive_return_url_ref'):
        issues.append(
            _issue(
                'stage2.webpay_intent.sensitive_return_url_ref',
                'Existen intentos WebPay con return_url_ref sensible.',
                count=webpay_intent_issues['sensitive_return_url_ref'],
            )
        )
    if webpay_intent_issues.get('sensitive_provider_payload'):
        issues.append(
            _issue(
                'stage2.webpay_intent.sensitive_provider_payload',
                'Existen intentos WebPay con provider_payload sensible.',
                count=webpay_intent_issues['sensitive_provider_payload'],
            )
        )
    if webpay_intent_issues.get('sensitive_block_reason'):
        issues.append(
            _issue(
                'stage2.webpay_intent.sensitive_block_reason',
                'Existen intentos WebPay con motivo de bloqueo sensible heredado.',
                count=webpay_intent_issues['sensitive_block_reason'],
            )
        )
    if webpay_intent_issues.get('confirmed_without_external_ref'):
        issues.append(
            _issue(
                'stage2.webpay_intent.confirmed_without_external_ref',
                'Existen intentos WebPay confirmados sin external_ref trazable.',
                count=webpay_intent_issues['confirmed_without_external_ref'],
            )
        )
    if webpay_intent_issues.get('confirmed_with_sensitive_external_ref'):
        issues.append(
            _issue(
                'stage2.webpay_intent.confirmed_with_sensitive_external_ref',
                'Existen intentos WebPay confirmados con external_ref sensible.',
                count=webpay_intent_issues['confirmed_with_sensitive_external_ref'],
            )
        )
    if webpay_intent_issues.get('confirmed_payment_not_paid'):
        issues.append(
            _issue(
                'stage2.webpay_intent.confirmed_payment_not_paid',
                'Existen intentos WebPay confirmados cuyo pago mensual no esta pagado.',
                count=webpay_intent_issues['confirmed_payment_not_paid'],
            )
        )
    if webpay_intent_issues.get('confirmed_payment_without_webpay_date'):
        issues.append(
            _issue(
                'stage2.webpay_intent.confirmed_payment_without_webpay_date',
                'Existen intentos WebPay confirmados cuyo pago mensual no conserva fecha WebPay.',
                count=webpay_intent_issues['confirmed_payment_without_webpay_date'],
            )
        )
    if webpay_intent_issues.get('confirmed_payment_date_mismatch'):
        issues.append(
            _issue(
                'stage2.webpay_intent.confirmed_payment_date_mismatch',
                'Existen intentos WebPay confirmados con fecha distinta a la del pago mensual.',
                count=webpay_intent_issues['confirmed_payment_date_mismatch'],
            )
        )
    if webpay_intent_issues.get('confirmed_manual_event_missing'):
        issues.append(
            _issue(
                'stage2.webpay_intent.confirmed_manual_event_missing',
                'Existen intentos WebPay confirmados sin auditoria manual completa y alineada.',
                count=webpay_intent_issues['confirmed_manual_event_missing'],
            )
        )
    if webpay_intent_issues.get('prepared_event_missing'):
        issues.append(
            _issue(
                'stage2.webpay_intent.prepared_event_missing',
                'Existen intentos WebPay preparados o bloqueados sin auditoria prepared completa y alineada.',
                count=webpay_intent_issues['prepared_event_missing'],
            )
        )

    for key, code, message in [
        (
            'stage1_evidence_ref',
            'stage2.stage1_evidence_ref_missing',
            'Falta referencia no sensible a cierre/evidencia Etapa 1.',
        ),
        (
            'email_proof_ref',
            'stage2.email_proof_ref_missing',
            'Falta referencia no sensible a prueba aislada/controlada de Email.',
        ),
        (
            'webpay_proof_ref',
            'stage2.webpay_proof_ref_missing',
            'Falta referencia no sensible a prueba aislada/controlada de WebPay.',
        ),
        (
            'responsible_ref',
            'stage2.responsible_ref_missing',
            'Falta referencia no sensible a responsables de cobranza/canales.',
        ),
    ]:
        if not final_evidence[key]:
            issues.append(_issue(code, message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 2 - Cobranza y canales',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_STAGE2_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage2_cobranza': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'payments': {
                'total': payments_total,
                'by_state': _count_by(payments, 'estado_pago'),
                'reference_date': reference_date.isoformat(),
                **payment_overdue_issues,
                **payment_effective_code_issues,
                **payment_exceptional_resolution_issues,
                **payment_repayment_issues,
                **payment_uf_trace_issues,
            },
            'uf_values': {
                'total': uf_values.count(),
                'canonical_source_keys': sorted(CANONICAL_UF_SOURCE_KEYS),
                'by_source_key': _count_by(uf_values, 'source_key'),
                **uf_value_issues,
            },
            'account_states': {
                'total': account_states.count(),
                'required_tenants': len(account_state_required_tenant_ids),
                **account_state_issues,
            },
            'repayments': {
                'total': repayments.count(),
                'active': repayments.filter(estado='activa').count(),
                'completed': repayments.filter(estado='cumplida').count(),
                'by_state': _count_by(repayments, 'estado'),
                **repayment_issues,
            },
            'residual_codes': {
                'total': residual_codes.count(),
                'active': residual_codes.filter(estado='activa').count(),
                'by_state': _count_by(residual_codes, 'estado'),
                'invalid_model': invalid_residual_codes,
            },
            'channels': {
                'gates_total': channel_gates.count(),
                'by_channel': _count_by(channel_gates, 'canal'),
                'by_gate_state': _count_by(channel_gates, 'estado_gate'),
                'email_open_valid': max(valid_email_open_gates, 0),
                'invalid_channel_gates': invalid_channel_gates,
                'sensitive_channel_gate_refs': sensitive_channel_gate_refs,
                'whatsapp_open_without_template': whatsapp_open_without_template,
            },
            'notification_configs': {
                'total': notification_configs.count(),
                'active': active_notification_configs.count(),
                'base_suggested_days': [1, 3, 5, 10, 15, 20, 25],
                'required_enabled_contract_channels': len(required_notification_pairs),
                'missing_for_enabled_channel': notification_configs_missing_for_enabled_channel,
                **notification_config_issues,
            },
            'notification_schedules': {
                'total': notification_schedules.count(),
                'by_state': _count_by(notification_schedules, 'estado'),
                **notification_schedule_issues,
            },
            'channel_identities': {
                'identities_total': identities.count(),
                'identities_by_channel': _count_by(identities, 'canal'),
                'identities_by_state': _count_by(identities, 'estado'),
                'email_active_identities': email_active_identities.count(),
                'whatsapp_active_identities': whatsapp_active_identities.count(),
                'whatsapp_opt_in_tenants': whatsapp_opt_in_tenants.count(),
                'invalid_whatsapp_opt_in_tenants': invalid_whatsapp_opt_in_tenants,
                'whatsapp_opt_in_invalid_phone': whatsapp_opt_in_invalid_phone,
                'whatsapp_opt_in_sensitive_refs': whatsapp_opt_in_sensitive_refs,
                'whatsapp_blocked_tenants': whatsapp_blocked_tenants.count(),
                **whatsapp_block_issues,
                'whatsapp_rehabilitated_tenants': whatsapp_rehabilitated_tenants.count(),
                **whatsapp_rehabilitation_issues,
                'invalid_identities': invalid_identities,
                'assignments_total': channel_assignments.count(),
                'assignments_by_channel': _count_by(channel_assignments, 'canal'),
                'assignments_by_state': _count_by(channel_assignments, 'estado'),
                'email_active_assignments': email_active_assignments.count(),
                'whatsapp_active_assignments': whatsapp_active_assignments.count(),
                'invalid_assignments': invalid_assignments,
            },
            'messages': {
                'total': messages.count(),
                'by_channel': _count_by(messages, 'canal'),
                'by_state': _count_by(messages, 'estado'),
                **message_issues,
                **whatsapp_fallback_issues,
            },
            'webpay': {
                'gates_total': webpay_gates.count(),
                'by_gate_state': _count_by(webpay_gates, 'estado_gate'),
                'open_valid': max(valid_webpay_open_gates, 0),
                'invalid_gates': invalid_webpay_gates,
                'sensitive_gate_refs': sensitive_webpay_gate_refs,
                'intents_total': webpay_intents.count(),
                'intents_by_state': _count_by(webpay_intents, 'estado'),
                'invalid_intents': invalid_webpay_intents,
                **webpay_intent_issues,
            },
            'final_evidence': final_evidence,
            'source_trace': source_trace,
        },
        'limitations': [
            'Auditoria local de solo lectura; no envia Email, WhatsApp ni WebPay.',
            'No usa secretos, .env, datos reales ni integraciones externas.',
            'No cierra Etapa 2 sin identidades/asignaciones activas, evidencia Etapa 1 y pruebas aisladas/controladas de Email y WebPay.',
        ],
    }
