from collections import Counter

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

from .models import OperationalRuntimeSignal, RuntimeSignalKey, RuntimeSignalStatus


REQUIRED_RUNTIME_SIGNALS = {
    RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY: {
        'missing_code': 'observability.monthly_latency_metric_missing',
        'attention_code': 'observability.monthly_latency_metric_attention',
        'missing_message': 'No existe metrica persistida para latencia de calculo mensual.',
        'attention_message': 'La metrica de latencia de calculo mensual requiere atencion.',
    },
    RuntimeSignalKey.QUEUE_RUNTIME: {
        'missing_code': 'observability.queue_runtime_metric_missing',
        'attention_code': 'observability.queue_runtime_metric_attention',
        'missing_message': 'La auditoria local solo verifica configuracion de broker; falta metrica runtime de colas/tareas.',
        'attention_message': 'La metrica runtime de colas/tareas requiere atencion.',
    },
    RuntimeSignalKey.FAILED_WEBHOOKS: {
        'missing_code': 'observability.webhook_metric_missing',
        'attention_code': 'observability.webhook_metric_attention',
        'missing_message': 'No existe metrica persistida para webhooks fallidos.',
        'attention_message': 'La metrica de webhooks fallidos requiere atencion.',
    },
    RuntimeSignalKey.FAILED_CRONS: {
        'missing_code': 'observability.cron_metric_missing',
        'attention_code': 'observability.cron_metric_attention',
        'missing_message': 'No existe metrica persistida para crons fallidos.',
        'attention_message': 'La metrica de crons fallidos requiere atencion.',
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


def _runtime_signal_payload(signal):
    if signal is None:
        return {'status': RuntimeSignalStatus.MISSING, 'observed_at': None, 'source_kind': None, 'evidence_ref': ''}
    return {
        'status': signal.status,
        'observed_at': signal.observed_at.isoformat() if signal.observed_at else None,
        'source_kind': signal.source_kind,
        'evidence_ref': signal.evidence_ref,
        'value': signal.value if isinstance(signal.value, dict) else {},
    }


def _collect_runtime_signals():
    signals_by_key = {signal.signal_key: signal for signal in OperationalRuntimeSignal.objects.all()}
    runtime_payload = {
        'celery_broker_configured': bool(str(settings.CELERY_BROKER_URL or '').strip()),
    }
    runtime_issues = []

    for signal_key, definition in REQUIRED_RUNTIME_SIGNALS.items():
        signal = signals_by_key.get(signal_key)
        runtime_payload[signal_key] = _runtime_signal_payload(signal)
        if signal is None:
            runtime_issues.append(_issue(definition['missing_code'], definition['missing_message']))
        elif signal.status != RuntimeSignalStatus.OK:
            runtime_issues.append(_issue(definition['attention_code'], definition['attention_message']))

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
