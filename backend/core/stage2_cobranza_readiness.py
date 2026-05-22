from __future__ import annotations

from collections import Counter
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from canales.models import (
    CanalMensajeria,
    EstadoGateCanal,
    EstadoMensajeSaliente,
    MensajeSaliente,
)
from canales.services import (
    email_readiness_blocking_reason,
    whatsapp_gate_has_approved_template,
)
from cobranza.models import (
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    GateCobroExterno,
    IntentoPagoWebPay,
    PagoMensual,
)
from operacion.models import CanalOperacion, EstadoIdentidadEnvio, EstadoMandatoOperacion


SENSITIVE_REFERENCE_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
)


def _non_sensitive_reference(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and not SENSITIVE_REFERENCE_PATTERN.search(normalized)


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


def _collect_message_issues(messages) -> dict[str, int]:
    counts = Counter()
    for message in messages:
        try:
            message.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if message.estado == EstadoMensajeSaliente.SENT and not message.external_ref.strip():
            counts['sent_without_external_ref'] += 1
        if _message_operational_issue(message):
            counts['prepared_or_sent_not_ready'] += 1
    return dict(sorted(counts.items()))


def collect_stage2_cobranza_readiness(
    *,
    stage1_evidence_ref: str = '',
    email_proof_ref: str = '',
    webpay_proof_ref: str = '',
    responsible_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
    channel_gates = CanalMensajeria.objects.all()
    email_open_gates = channel_gates.filter(canal=CanalOperacion.EMAIL, estado_gate=EstadoGateCanal.OPEN)
    whatsapp_open_gates = channel_gates.filter(canal=CanalOperacion.WHATSAPP, estado_gate=EstadoGateCanal.OPEN)
    invalid_channel_gates = _count_invalid(channel_gates)
    valid_email_open_gates = email_open_gates.count() - _count_invalid(email_open_gates)
    whatsapp_open_without_template = sum(
        1 for gate in whatsapp_open_gates if not whatsapp_gate_has_approved_template(gate)
    )

    messages = MensajeSaliente.objects.select_related(
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'contrato__mandato_operacion',
        'arrendatario',
        'documento_emitido',
    )
    message_issues = _collect_message_issues(messages)

    webpay_gates = GateCobroExterno.objects.all()
    webpay_open_gates = webpay_gates.filter(estado_gate=EstadoGateCobroExterno.OPEN)
    invalid_webpay_gates = _count_invalid(webpay_gates)
    valid_webpay_open_gates = webpay_open_gates.count() - _count_invalid(webpay_open_gates)
    webpay_intents = IntentoPagoWebPay.objects.select_related('pago_mensual', 'gate_cobro')
    invalid_webpay_intents = _count_invalid(webpay_intents)

    payments_total = PagoMensual.objects.count()
    final_evidence = {
        'stage1_evidence_ref': _non_sensitive_reference(stage1_evidence_ref),
        'email_proof_ref': _non_sensitive_reference(email_proof_ref),
        'webpay_proof_ref': _non_sensitive_reference(webpay_proof_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }

    issues: list[dict[str, Any]] = []
    if payments_total == 0:
        issues.append(
            _issue(
                'stage2.payments_missing',
                'No existen pagos mensuales locales para validar cobranza activa.',
            )
        )
    if valid_email_open_gates <= 0:
        issues.append(
            _issue(
                'stage2.email.open_gate_missing',
                'Etapa 2 requiere al menos un gate Email abierto y valido para cierre.',
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
    if whatsapp_open_without_template:
        issues.append(
            _issue(
                'stage2.whatsapp.template_missing',
                'WhatsApp abierto requiere template aprobado registrado en el gate.',
                count=whatsapp_open_without_template,
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
    if message_issues.get('prepared_or_sent_not_ready'):
        issues.append(
            _issue(
                'stage2.message.prepared_or_sent_not_ready',
                'Existen mensajes preparados/enviados sin gate, identidad, destinatario o mandato operativo valido.',
                count=message_issues['prepared_or_sent_not_ready'],
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
    if invalid_webpay_intents:
        issues.append(
            _issue(
                'stage2.webpay_intent_invalid',
                'Existen intentos WebPay que no pasan validacion de dominio.',
                count=invalid_webpay_intents,
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
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage2_cobranza': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'payments': {
                'total': payments_total,
            },
            'channels': {
                'gates_total': channel_gates.count(),
                'by_channel': _count_by(channel_gates, 'canal'),
                'by_gate_state': _count_by(channel_gates, 'estado_gate'),
                'email_open_valid': max(valid_email_open_gates, 0),
                'invalid_channel_gates': invalid_channel_gates,
                'whatsapp_open_without_template': whatsapp_open_without_template,
            },
            'messages': {
                'total': messages.count(),
                'by_channel': _count_by(messages, 'canal'),
                'by_state': _count_by(messages, 'estado'),
                **message_issues,
            },
            'webpay': {
                'gates_total': webpay_gates.count(),
                'by_gate_state': _count_by(webpay_gates, 'estado_gate'),
                'open_valid': max(valid_webpay_open_gates, 0),
                'invalid_gates': invalid_webpay_gates,
                'intents_total': webpay_intents.count(),
                'intents_by_state': _count_by(webpay_intents, 'estado'),
                'invalid_intents': invalid_webpay_intents,
            },
            'final_evidence': final_evidence,
        },
        'limitations': [
            'Auditoria local de solo lectura; no envia Email, WhatsApp ni WebPay.',
            'No usa secretos, .env, datos reales ni integraciones externas.',
            'No cierra Etapa 2 sin evidencia Etapa 1 y pruebas aisladas/controladas de Email y WebPay.',
        ],
    }
