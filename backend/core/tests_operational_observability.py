import json
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from canales.models import CanalMensajeria, EstadoGateCanal
from cobranza.models import EstadoGateCobroExterno, GateCobroExterno
from core.models import OperationalRuntimeSignal, RuntimeSignalKey, RuntimeSignalStatus
from core.operational_observability import collect_operational_observability_audit
from patrimonio.models import Empresa
from sii.models import AmbienteSII, CapacidadSII, CapacidadTributariaSII, EstadoGateSII


def create_runtime_signals_ok():
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY,
        status=RuntimeSignalStatus.OK,
        value={'duration_ms': 120},
        evidence_ref='local-monthly-latency',
    )
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
        status=RuntimeSignalStatus.OK,
        value={'healthy': True},
        evidence_ref='local-queue-runtime',
    )
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.FAILED_WEBHOOKS,
        status=RuntimeSignalStatus.OK,
        value={'failed_count': 0},
        evidence_ref='local-webhooks',
    )
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.FAILED_CRONS,
        status=RuntimeSignalStatus.OK,
        value={'failed_count': 0},
        evidence_ref='local-crons',
    )


class OperationalObservabilityAuditTests(TestCase):
    def test_empty_database_reports_required_sections_without_external_access(self):
        result = collect_operational_observability_audit()

        self.assertEqual(result['source_kind'], 'local')
        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage7_observability'])
        self.assertIn('integration_gates', result['sections'])
        self.assertIn('operational_backlog', result['sections'])
        self.assertIn('runtime_signals', result['sections'])
        self.assertIn('observability.webhook_metric_missing', {issue['code'] for issue in result['issues']})
        self.assertNotIn('://', json.dumps(result))

    def test_operational_attention_counts_invalid_open_gates(self):
        CanalMensajeria.objects.create(
            canal='email',
            provider_key='smtp',
            estado_gate=EstadoGateCanal.OPEN,
            restricciones_operativas={},
            evidencia_ref='',
        )
        GateCobroExterno.objects.create(
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='',
        )
        empresa = Empresa.objects.create(
            razon_social='Empresa Observabilidad',
            rut='76123456-0',
            estado='borrador',
        )
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.DTE_EMISION,
            ambiente=AmbienteSII.CERTIFICATION,
            estado_gate=EstadoGateSII.OPEN,
        )

        result = collect_operational_observability_audit()
        issues = {issue['code']: issue for issue in result['issues']}

        self.assertEqual(result['sections']['integration_gates']['canales']['open_invalid_readiness'], 1)
        self.assertEqual(result['sections']['integration_gates']['webpay']['open_invalid_readiness'], 1)
        self.assertEqual(result['sections']['integration_gates']['sii']['open_invalid_readiness'], 1)
        self.assertEqual(issues['observability.channel_gate_invalid']['count'], 1)
        self.assertEqual(issues['observability.webpay_gate_invalid']['count'], 1)
        self.assertEqual(issues['observability.sii_capability_invalid']['count'], 1)

    def test_runtime_signals_clear_metric_missing_issues(self):
        create_runtime_signals_ok()

        result = collect_operational_observability_audit()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage7_observability'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('observability.monthly_latency_metric_missing', issue_codes)
        self.assertEqual(
            result['sections']['runtime_signals'][RuntimeSignalKey.QUEUE_RUNTIME]['status'],
            RuntimeSignalStatus.OK,
        )

    def test_runtime_signal_attention_blocks_observability_close(self):
        create_runtime_signals_ok()
        OperationalRuntimeSignal.objects.filter(signal_key=RuntimeSignalKey.FAILED_CRONS).update(
            status=RuntimeSignalStatus.ATTENTION,
            value={'failed_count': 2},
        )

        result = collect_operational_observability_audit()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_observability'])
        self.assertIn('observability.cron_metric_attention', issue_codes)

    def test_record_runtime_signal_command_validates_payload(self):
        call_command(
            'record_operational_runtime_signal',
            signal_key=RuntimeSignalKey.FAILED_WEBHOOKS,
            status=RuntimeSignalStatus.OK,
            evidence_ref='local-webhook-check',
            value_json='{"failed_count": 0}',
            stdout=StringIO(),
        )

        signal = OperationalRuntimeSignal.objects.get(signal_key=RuntimeSignalKey.FAILED_WEBHOOKS)
        self.assertEqual(signal.status, RuntimeSignalStatus.OK)
        self.assertEqual(signal.value['failed_count'], 0)

        with self.assertRaises(CommandError):
            call_command(
                'record_operational_runtime_signal',
                signal_key=RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY,
                status=RuntimeSignalStatus.OK,
                evidence_ref='bad-local-latency',
                value_json='{"duration_ms": -1}',
                stdout=StringIO(),
            )

    def test_command_writes_json_output_and_fail_on_attention_blocks_close(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'observability.json'
            call_command('audit_operational_observability', output=str(output_path))

            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertIn('runtime_signals', result['sections'])

        with self.assertRaises(CommandError):
            call_command('audit_operational_observability', fail_on_attention=True, stdout=StringIO())
