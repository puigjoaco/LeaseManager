from collections import Counter
from copy import deepcopy

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F
from django.db.models import Q
from django.utils import timezone

from canales.models import CanalMensajeria, EstadoGateCanal, EstadoMensajeSaliente, MensajeSaliente
from cobranza.models import (
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    GateCobroExterno,
    IntentoPagoWebPay,
)
from conciliacion.models import (
    ConexionBancaria,
    EstadoConciliacionMovimiento,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
)
from contabilidad.models import CierreMensualContable, EstadoCierreMensual
from documentos.models import DocumentoEmitido, EstadoDocumento
from sii.models import CapacidadTributariaSII, EstadoGateSII

from .models import (
    OperationalRuntimeSignal,
    RuntimeSignalKey,
    RuntimeSignalSourceKind,
    RuntimeSignalStatus,
    SENSITIVE_EVIDENCE_REF_PATTERN,
)


AUTHORIZED_RUNTIME_SIGNAL_SOURCE_KINDS = {
    RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
    RuntimeSignalSourceKind.REAL_AUTORIZADO,
}


REQUIRED_RUNTIME_SIGNALS = {
    RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY: {
        'missing_code': 'observability.monthly_latency_metric_missing',
        'attention_code': 'observability.monthly_latency_metric_attention',
        'evidence_code': 'observability.monthly_latency_metric_evidence_ref_missing',
        'source_code': 'observability.monthly_latency_metric_source_not_authorized',
        'trace_code': 'observability.monthly_latency_metric_source_trace_missing',
        'missing_message': 'No existe metrica persistida para latencia de calculo mensual.',
        'attention_message': 'La metrica de latencia de calculo mensual requiere atencion.',
        'evidence_message': 'La metrica de latencia de calculo mensual requiere evidencia_ref no sensible.',
        'source_message': 'La metrica de latencia de calculo mensual requiere fuente snapshot_controlado o real_autorizado para cierre.',
        'trace_message': 'La metrica de latencia de calculo mensual requiere source_label y authorization_ref no sensibles para cierre.',
    },
    RuntimeSignalKey.QUEUE_RUNTIME: {
        'missing_code': 'observability.queue_runtime_metric_missing',
        'attention_code': 'observability.queue_runtime_metric_attention',
        'evidence_code': 'observability.queue_runtime_metric_evidence_ref_missing',
        'source_code': 'observability.queue_runtime_metric_source_not_authorized',
        'trace_code': 'observability.queue_runtime_metric_source_trace_missing',
        'missing_message': 'La auditoria local solo verifica configuracion de broker; falta metrica runtime de colas/tareas.',
        'attention_message': 'La metrica runtime de colas/tareas requiere atencion.',
        'evidence_message': 'La metrica runtime de colas/tareas requiere evidencia_ref no sensible.',
        'source_message': 'La metrica runtime de colas/tareas requiere fuente snapshot_controlado o real_autorizado para cierre.',
        'trace_message': 'La metrica runtime de colas/tareas requiere source_label y authorization_ref no sensibles para cierre.',
    },
    RuntimeSignalKey.FAILED_WEBHOOKS: {
        'missing_code': 'observability.webhook_metric_missing',
        'attention_code': 'observability.webhook_metric_attention',
        'evidence_code': 'observability.webhook_metric_evidence_ref_missing',
        'source_code': 'observability.webhook_metric_source_not_authorized',
        'trace_code': 'observability.webhook_metric_source_trace_missing',
        'missing_message': 'No existe metrica persistida para webhooks fallidos.',
        'attention_message': 'La metrica de webhooks fallidos requiere atencion.',
        'evidence_message': 'La metrica de webhooks fallidos requiere evidencia_ref no sensible.',
        'source_message': 'La metrica de webhooks fallidos requiere fuente snapshot_controlado o real_autorizado para cierre.',
        'trace_message': 'La metrica de webhooks fallidos requiere source_label y authorization_ref no sensibles para cierre.',
    },
    RuntimeSignalKey.FAILED_CRONS: {
        'missing_code': 'observability.cron_metric_missing',
        'attention_code': 'observability.cron_metric_attention',
        'evidence_code': 'observability.cron_metric_evidence_ref_missing',
        'source_code': 'observability.cron_metric_source_not_authorized',
        'trace_code': 'observability.cron_metric_source_trace_missing',
        'missing_message': 'No existe metrica persistida para crons fallidos.',
        'attention_message': 'La metrica de crons fallidos requiere atencion.',
        'evidence_message': 'La metrica de crons fallidos requiere evidencia_ref no sensible.',
        'source_message': 'La metrica de crons fallidos requiere fuente snapshot_controlado o real_autorizado para cierre.',
        'trace_message': 'La metrica de crons fallidos requiere source_label y authorization_ref no sensibles para cierre.',
    },
}


def _count_by(queryset, field_name):
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _count_invalid(queryset):
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _issue(code, message, count=1, severity='attention'):
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _non_sensitive_reference(value):
    normalized = str(value or '').strip()
    return bool(normalized) and not SENSITIVE_EVIDENCE_REF_PATTERN.search(normalized)


def _runtime_signal_payload(signal):
    if signal is None:
        return {
            'status': RuntimeSignalStatus.MISSING,
            'observed_at': None,
            'source_kind': None,
            'evidence_ref': '',
            'source_trace': {
                'source_label': False,
                'authorization_ref': False,
            },
            'value': {},
        }
    safe_evidence_ref = signal.evidence_ref if _non_sensitive_reference(signal.evidence_ref) else ''
    return {
        'status': signal.status,
        'observed_at': signal.observed_at.isoformat() if signal.observed_at else None,
        'source_kind': signal.source_kind,
        'evidence_ref': safe_evidence_ref,
        'source_trace': {
            'source_label': _non_sensitive_reference(signal.source_label),
            'authorization_ref': _non_sensitive_reference(signal.authorization_ref),
        },
        'value': _public_runtime_value(signal.signal_key, {'value': signal.value if isinstance(signal.value, dict) else {}}),
    }


def _public_runtime_value(signal_key, payload):
    value = payload.get('value') if isinstance(payload, dict) else {}
    if not isinstance(value, dict):
        return {}
    if signal_key == RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY:
        duration = value.get('duration_ms')
        return {'duration_ms': duration} if _is_public_number(duration) else {}
    if signal_key == RuntimeSignalKey.QUEUE_RUNTIME:
        healthy = value.get('healthy')
        return {'healthy': healthy} if isinstance(healthy, bool) else {}
    if signal_key in {RuntimeSignalKey.FAILED_WEBHOOKS, RuntimeSignalKey.FAILED_CRONS}:
        failed_count = value.get('failed_count')
        return {'failed_count': failed_count} if isinstance(failed_count, int) and not isinstance(failed_count, bool) else {}
    return {}


def _is_public_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _public_runtime_signal_payload(signal_key, payload):
    if not isinstance(payload, dict):
        return {}
    return {
        'status': payload.get('status'),
        'observed_at': payload.get('observed_at'),
        'source_kind': payload.get('source_kind'),
        'has_evidence_ref': bool(payload.get('evidence_ref')),
        'source_trace': payload.get('source_trace') if isinstance(payload.get('source_trace'), dict) else {},
        'value': _public_runtime_value(signal_key, payload),
    }


def redact_operational_observability_for_api(result):
    public_result = deepcopy(result)
    sections = public_result.get('sections', {})
    if not isinstance(sections, dict):
        return public_result

    runtime_signals = sections.get('runtime_signals', {})
    if not isinstance(runtime_signals, dict):
        return public_result

    public_runtime_signals = {}
    celery_configured = runtime_signals.get('celery_broker_configured')
    if isinstance(celery_configured, bool):
        public_runtime_signals['celery_broker_configured'] = celery_configured
    authorized_for_close = runtime_signals.get('authorized_for_stage7_close')
    if isinstance(authorized_for_close, bool):
        public_runtime_signals['authorized_for_stage7_close'] = authorized_for_close

    for signal_key in REQUIRED_RUNTIME_SIGNALS:
        public_runtime_signals[signal_key] = _public_runtime_signal_payload(signal_key, runtime_signals.get(signal_key))

    sections['runtime_signals'] = public_runtime_signals
    return public_result


def _collect_runtime_signals():
    signals_by_key = {signal.signal_key: signal for signal in OperationalRuntimeSignal.objects.all()}
    runtime_payload = {
        'celery_broker_configured': bool(str(settings.CELERY_BROKER_URL or '').strip()),
        'authorized_source_kinds': sorted(AUTHORIZED_RUNTIME_SIGNAL_SOURCE_KINDS),
        'authorized_for_stage7_close': False,
    }
    runtime_issues = []
    authorized_ok_signal_count = 0

    for signal_key, definition in REQUIRED_RUNTIME_SIGNALS.items():
        signal = signals_by_key.get(signal_key)
        runtime_payload[signal_key] = _runtime_signal_payload(signal)
        if signal is None:
            runtime_issues.append(_issue(definition['missing_code'], definition['missing_message']))
        elif signal.status != RuntimeSignalStatus.OK:
            runtime_issues.append(_issue(definition['attention_code'], definition['attention_message']))
        elif not _non_sensitive_reference(signal.evidence_ref):
            runtime_issues.append(_issue(definition['evidence_code'], definition['evidence_message']))
        elif signal.source_kind not in AUTHORIZED_RUNTIME_SIGNAL_SOURCE_KINDS:
            runtime_issues.append(_issue(definition['source_code'], definition['source_message']))
        elif not (
            _non_sensitive_reference(signal.source_label)
            and _non_sensitive_reference(signal.authorization_ref)
        ):
            runtime_issues.append(_issue(definition['trace_code'], definition['trace_message']))
        else:
            authorized_ok_signal_count += 1

    runtime_payload['authorized_for_stage7_close'] = authorized_ok_signal_count == len(REQUIRED_RUNTIME_SIGNALS)

    return runtime_payload, runtime_issues


def collect_operational_observability_audit():
    channel_gates = CanalMensajeria.objects.all()
    webpay_gates = GateCobroExterno.objects.all()
    bank_connections = ConexionBancaria.objects.all()
    sii_capabilities = CapacidadTributariaSII.objects.all()

    blocked_messages = MensajeSaliente.objects.filter(estado=EstadoMensajeSaliente.BLOCKED).count()
    failed_messages = MensajeSaliente.objects.filter(estado=EstadoMensajeSaliente.FAILED).count()
    blocked_webpay = IntentoPagoWebPay.objects.filter(estado=EstadoIntentoPagoWebPay.BLOCKED).count()
    failed_webpay = IntentoPagoWebPay.objects.filter(estado=EstadoIntentoPagoWebPay.FAILED).count()
    unmatched_bank_movements = MovimientoBancarioImportado.objects.filter(
        estado_conciliacion__in=[
            EstadoConciliacionMovimiento.PENDING,
            EstadoConciliacionMovimiento.UNKNOWN_INCOME,
            EstadoConciliacionMovimiento.MANUAL_REQUIRED,
        ]
    ).count()
    open_unknown_income = IngresoDesconocido.objects.filter(estado=EstadoIngresoDesconocido.OPEN).count()
    reopened_closes = CierreMensualContable.objects.filter(estado=EstadoCierreMensual.REOPENED).count()
    canceled_documents = DocumentoEmitido.objects.filter(estado=EstadoDocumento.CANCELED).count()

    invalid_channel_gates = _count_invalid(channel_gates.filter(estado_gate=EstadoGateCanal.OPEN))
    invalid_webpay_gates = _count_invalid(webpay_gates.filter(estado_gate=EstadoGateCobroExterno.OPEN))
    invalid_bank_connections = _count_invalid(
        bank_connections.filter(
            Q(primaria_movimientos=True)
            | Q(primaria_saldos=True)
            | Q(primaria_conectividad=True)
            | Q(estado_conexion='activa')
        )
    )
    invalid_sii_capabilities = _count_invalid(sii_capabilities.filter(estado_gate=EstadoGateSII.OPEN))
    bank_recent_errors = bank_connections.filter(ultimo_error_at__isnull=False).filter(
        Q(ultimo_exito_at__isnull=True) | Q(ultimo_error_at__gt=F('ultimo_exito_at'))
    ).count()

    runtime_signals, issues = _collect_runtime_signals()

    for code, count, message in [
        (
            'observability.channel_gate_invalid',
            invalid_channel_gates,
            'Existen gates de mensajeria abiertos sin readiness trazable.',
        ),
        (
            'observability.webpay_gate_invalid',
            invalid_webpay_gates,
            'Existen gates WebPay abiertos sin readiness trazable.',
        ),
        (
            'observability.bank_connection_invalid',
            invalid_bank_connections,
            'Existen conexiones bancarias operativas sin readiness trazable.',
        ),
        (
            'observability.sii_capability_invalid',
            invalid_sii_capabilities,
            'Existen capacidades SII abiertas sin readiness trazable.',
        ),
        (
            'observability.bank_recent_error',
            bank_recent_errors,
            'Existen conexiones bancarias con error posterior al ultimo exito conocido.',
        ),
        (
            'observability.messages_blocked',
            blocked_messages,
            'Existen mensajes salientes bloqueados que requieren seguimiento operativo.',
        ),
        (
            'observability.messages_failed',
            failed_messages,
            'Existen mensajes salientes fallidos que requieren seguimiento operativo.',
        ),
        (
            'observability.webpay_blocked',
            blocked_webpay,
            'Existen intentos WebPay bloqueados por gate.',
        ),
        (
            'observability.webpay_failed',
            failed_webpay,
            'Existen intentos WebPay fallidos.',
        ),
        (
            'observability.bank_unmatched_movements',
            unmatched_bank_movements,
            'Existen movimientos bancarios pendientes, desconocidos o manuales.',
        ),
        (
            'observability.unknown_income_open',
            open_unknown_income,
            'Existen ingresos desconocidos abiertos.',
        ),
        (
            'observability.monthly_close_reopened',
            reopened_closes,
            'Existen cierres mensuales reabiertos.',
        ),
        (
            'observability.documents_canceled',
            canceled_documents,
            'Existen documentos cancelados que deben mantenerse visibles en monitoreo.',
        ),
    ]:
        if count:
            issues.append(_issue(code, message, count=count))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('attention', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'source_kind': 'local',
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage7_observability': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'integration_gates': {
                'canales': {
                    'total': channel_gates.count(),
                    'by_state': _count_by(channel_gates, 'estado_gate'),
                    'open_invalid_readiness': invalid_channel_gates,
                },
                'webpay': {
                    'total': webpay_gates.count(),
                    'by_state': _count_by(webpay_gates, 'estado_gate'),
                    'open_invalid_readiness': invalid_webpay_gates,
                },
                'banco': {
                    'total': bank_connections.count(),
                    'by_state': _count_by(bank_connections, 'estado_conexion'),
                    'operational_invalid_readiness': invalid_bank_connections,
                    'recent_error_after_success': bank_recent_errors,
                },
                'sii': {
                    'total': sii_capabilities.count(),
                    'by_state': _count_by(sii_capabilities, 'estado_gate'),
                    'open_invalid_readiness': invalid_sii_capabilities,
                },
            },
            'operational_backlog': {
                'mensajes_bloqueados': blocked_messages,
                'mensajes_fallidos': failed_messages,
                'webpay_bloqueados': blocked_webpay,
                'webpay_fallidos': failed_webpay,
                'movimientos_bancarios_sin_match': unmatched_bank_movements,
                'ingresos_desconocidos_abiertos': open_unknown_income,
                'cierres_mensuales_reabiertos': reopened_closes,
                'documentos_cancelados': canceled_documents,
            },
            'runtime_signals': runtime_signals,
        },
        'limitations': [
            'Auditoria local de solo lectura; no conecta proveedores externos.',
            'No usa secretos, .env, datos reales ni snapshots externos.',
            'No reemplaza monitoreo runtime productivo ni cierra Operacion productiva.',
        ],
    }
