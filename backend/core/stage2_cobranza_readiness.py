from __future__ import annotations

from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditEvent, ManualResolution
from canales.models import (
    CanalMensajeria,
    ConfiguracionNotificacionContrato,
    EstadoGateCanal,
    EstadoMensajeSaliente,
    MensajeSaliente,
    NotificacionCobranzaProgramada,
)
from canales.services import (
    COLLECTABLE_PAYMENT_STATES,
    WHATSAPP_FALLBACK_REQUIRED_CATEGORY,
    document_delivery_blocking_reason,
    email_readiness_blocking_reason,
    expected_payment_notification_schedule,
    whatsapp_gate_has_approved_template,
)
from cobranza.models import (
    CodigoCobroResidual,
    EstadoCuentaArrendatario,
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    EstadoPago,
    GateCobroExterno,
    IntentoPagoWebPay,
    PagoMensual,
    RepactacionDeuda,
)
from cobranza.services import build_account_state_summary
from contratos.models import (
    Arrendatario,
    Contrato,
    EstadoContrato,
    WHATSAPP_BLOCK_ALERT_CATEGORY,
    WHATSAPP_BLOCK_EVENT_TYPE,
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
    if not message.destinatario.strip():
        return 'Mensaje preparado/enviado sin destinatario trazable.'
    if message.contrato_id and message.contrato.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
        return 'Mensaje preparado/enviado sin mandato operativo activo.'
    if message.canal == CanalOperacion.WHATSAPP:
        return _whatsapp_contact_static_issue(message)
    return ''


def _message_context_matches(left: MensajeSaliente, right: MensajeSaliente) -> bool:
    if left.documento_emitido_id and left.documento_emitido_id == right.documento_emitido_id:
        return True
    if left.contrato_id and left.contrato_id == right.contrato_id:
        return True
    if left.arrendatario_id and left.arrendatario_id == right.arrendatario_id:
        return True
    return False


def _fallback_resolution_matches(message: MensajeSaliente, resolution: ManualResolution) -> bool:
    metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
    if resolution.scope_reference == str(message.pk):
        return True
    for key, value in [
        ('documento_emitido_id', message.documento_emitido_id),
        ('contrato_id', message.contrato_id),
        ('arrendatario_id', message.arrendatario_id),
    ]:
        if value and str(metadata.get(key, '')) == str(value):
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
        if any(_message_context_matches(message, fallback) for fallback in email_fallbacks):
            continue
        if any(_fallback_resolution_matches(message, resolution) for resolution in fallback_resolutions):
            continue
        counts['without_fallback_trace'] += 1

    return dict(sorted(counts.items()))


def _collect_whatsapp_block_issues(blocked_tenants) -> dict[str, int]:
    counts = Counter()
    block_alerts = list(
        ManualResolution.objects.filter(
            category=WHATSAPP_BLOCK_ALERT_CATEGORY,
            scope_type='arrendatario',
            status__in=[
                ManualResolution.Status.OPEN,
                ManualResolution.Status.IN_REVIEW,
                ManualResolution.Status.RESOLVED,
            ],
        ).values_list('scope_reference', flat=True)
    )
    block_alert_refs = {str(value) for value in block_alerts}

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
        if not AuditEvent.objects.filter(
            event_type=WHATSAPP_BLOCK_EVENT_TYPE,
            entity_type='arrendatario',
            entity_id=str(tenant.pk),
        ).exists():
            counts['whatsapp_block_event_missing'] += 1
        if str(tenant.pk) not in block_alert_refs:
            counts['whatsapp_block_alert_missing'] += 1

    return dict(sorted(counts.items()))


def _collect_message_issues(messages) -> dict[str, int]:
    counts = Counter()
    for message in messages:
        try:
            message.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if message.estado == EstadoMensajeSaliente.SENT:
            if not message.external_ref.strip():
                counts['sent_without_external_ref'] += 1
            elif not _non_sensitive_reference(message.external_ref):
                counts['sent_with_sensitive_external_ref'] += 1
        if _message_operational_issue(message):
            counts['prepared_or_sent_not_ready'] += 1
        if message.estado in {EstadoMensajeSaliente.PREPARED, EstadoMensajeSaliente.SENT}:
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
    return (
        bool(gate.evidencia_ref.strip() and not _non_sensitive_reference(gate.evidencia_ref))
        or contains_sensitive_reference(gate.restricciones_operativas)
    )


def _collect_webpay_intent_issues(intents) -> dict[str, int]:
    counts = Counter()
    for intent in intents:
        try:
            intent.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if contains_sensitive_reference(intent.provider_payload, include_sensitive_keys=True):
            counts['sensitive_provider_payload'] += 1
        if intent.return_url_ref.strip() and not _non_sensitive_reference(intent.return_url_ref):
            counts['sensitive_return_url_ref'] += 1
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


def _collect_account_state_issues(account_states, required_tenant_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    existing_tenant_ids: set[int] = set()
    for state in account_states:
        existing_tenant_ids.add(state.arrendatario_id)
        try:
            state.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        summary = state.resumen_operativo
        if not isinstance(summary, dict):
            counts['invalid_summary_shape'] += 1
            continue

        expected = build_account_state_summary(state.arrendatario)
        missing_keys = set(expected) - set(summary)
        if missing_keys:
            counts['missing_summary_keys'] += 1
            continue

        if any(str(summary.get(key)) != str(expected_value) for key, expected_value in expected.items()):
            counts['stale_summary'] += 1

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
    whatsapp_rehabilitation_sensitive_refs = sum(
        1
        for tenant in Arrendatario.objects.exclude(whatsapp_rehabilitacion_ref='')
        if not _non_sensitive_reference(tenant.whatsapp_rehabilitacion_ref)
    )

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

    payments = PagoMensual.objects.select_related('contrato__arrendatario')
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
    payments_total = payments.count()
    repayments = RepactacionDeuda.objects.select_related('arrendatario', 'contrato_origen')
    invalid_repayments = _count_invalid(repayments)
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
    account_state_issues = _collect_account_state_issues(account_states, account_state_required_tenant_ids)
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
    if invalid_repayments:
        issues.append(
            _issue(
                'stage2.repayment.invalid_model',
                'Existen repactaciones de deuda que no pasan validacion de dominio.',
                count=invalid_repayments,
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
    if whatsapp_block_issues.get('whatsapp_block_event_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_event_missing',
                'Existen bloqueos definitivos WhatsApp sin evento auditable asociado.',
                count=whatsapp_block_issues['whatsapp_block_event_missing'],
            )
        )
    if whatsapp_block_issues.get('whatsapp_block_alert_missing'):
        issues.append(
            _issue(
                'stage2.whatsapp.block_alert_missing',
                'Existen bloqueos definitivos WhatsApp sin alerta administrativa trazable.',
                count=whatsapp_block_issues['whatsapp_block_alert_missing'],
            )
        )
    if whatsapp_rehabilitation_sensitive_refs:
        issues.append(
            _issue(
                'stage2.whatsapp.rehabilitation_ref_sensitive',
                'Existen rehabilitaciones WhatsApp con referencia sensible.',
                count=whatsapp_rehabilitation_sensitive_refs,
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
    if message_issues.get('prepared_or_sent_not_ready'):
        issues.append(
            _issue(
                'stage2.message.prepared_or_sent_not_ready',
                'Existen mensajes preparados/enviados sin gate, identidad, destinatario o mandato operativo valido.',
                count=message_issues['prepared_or_sent_not_ready'],
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
                'invalid_model': invalid_repayments,
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
                'whatsapp_rehabilitation_sensitive_refs': whatsapp_rehabilitation_sensitive_refs,
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
