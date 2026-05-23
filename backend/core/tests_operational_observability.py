import json
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from canales.models import CanalMensajeria, EstadoGateCanal
from cobranza.models import EstadoGateCobroExterno, GateCobroExterno
from core.models import OperationalRuntimeSignal, RuntimeSignalKey, RuntimeSignalSourceKind, RuntimeSignalStatus
from core.operational_observability import collect_operational_observability_audit
from patrimonio.models import Empresa
from sii.models import AmbienteSII, CapacidadSII, CapacidadTributariaSII, EstadoGateSII


AUTHORIZED_RUNTIME_TEST_SOURCE_KINDS = {
    RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
    RuntimeSignalSourceKind.REAL_AUTORIZADO,
}


def _runtime_source_trace(signal_key, source_kind, include_source_trace):
    if source_kind not in AUTHORIZED_RUNTIME_TEST_SOURCE_KINDS or not include_source_trace:
        return {}
    return {
        'source_label': f'{signal_key}-runtime-controlled-v1',
        'authorization_ref': 'stage7-runtime-authorization-v1',
    }


def create_runtime_signals_ok(source_kind=RuntimeSignalSourceKind.LOCAL, *, include_source_trace=True):
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY,
        status=RuntimeSignalStatus.OK,
        source_kind=source_kind,
        value={'duration_ms': 120},
        evidence_ref='local-monthly-latency',
        **_runtime_source_trace(RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY, source_kind, include_source_trace),
    )
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
        status=RuntimeSignalStatus.OK,
        source_kind=source_kind,
        value={'healthy': True},
        evidence_ref='local-queue-runtime',
        **_runtime_source_trace(RuntimeSignalKey.QUEUE_RUNTIME, source_kind, include_source_trace),
    )
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.FAILED_WEBHOOKS,
        status=RuntimeSignalStatus.OK,
        source_kind=source_kind,
        value={'failed_count': 0},
        evidence_ref='local-webhooks',
        **_runtime_source_trace(RuntimeSignalKey.FAILED_WEBHOOKS, source_kind, include_source_trace),
    )
    OperationalRuntimeSignal.objects.create(
        signal_key=RuntimeSignalKey.FAILED_CRONS,
        status=RuntimeSignalStatus.OK,
        source_kind=source_kind,
        value={'failed_count': 0},
        evidence_ref='local-crons',
        **_runtime_source_trace(RuntimeSignalKey.FAILED_CRONS, source_kind, include_source_trace),
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

    def test_local_runtime_signals_clear_missing_but_do_not_close_productive_observability(self):
        create_runtime_signals_ok()

        result = collect_operational_observability_audit()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_observability'])
        self.assertEqual(result['classification'], 'parcial')
        self.assertNotIn('observability.monthly_latency_metric_missing', issue_codes)
        self.assertIn('observability.monthly_latency_metric_source_not_authorized', issue_codes)
        self.assertFalse(result['sections']['runtime_signals']['authorized_for_stage7_close'])
        self.assertEqual(
            result['sections']['runtime_signals'][RuntimeSignalKey.QUEUE_RUNTIME]['status'],
            RuntimeSignalStatus.OK,
        )

    def test_authorized_runtime_signals_can_pass_observability_close(self):
        create_runtime_signals_ok(source_kind=RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO)

        result = collect_operational_observability_audit()

        self.assertTrue(result['ready_for_stage7_observability'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['sections']['runtime_signals']['authorized_for_stage7_close'])
        self.assertEqual(result['issues'], [])

    def test_authorized_runtime_signals_require_source_trace_refs(self):
        create_runtime_signals_ok(
            source_kind=RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
            include_source_trace=False,
        )

        result = collect_operational_observability_audit()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_observability'])
        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['sections']['runtime_signals']['authorized_for_stage7_close'])
        self.assertIn('observability.monthly_latency_metric_source_trace_missing', issue_codes)
        self.assertFalse(
            result['sections']['runtime_signals'][RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY]['source_trace'][
                'source_label'
            ]
        )

    def test_runtime_signal_attention_blocks_observability_close(self):
        create_runtime_signals_ok(source_kind=RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO)
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
                signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
                status=RuntimeSignalStatus.OK,
                source_kind=RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
                evidence_ref='queue-runtime-controlled-v1',
                value_json='{"healthy": true}',
                stdout=StringIO(),
            )

        call_command(
            'record_operational_runtime_signal',
            signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
            status=RuntimeSignalStatus.OK,
            source_kind=RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
            evidence_ref='queue-runtime-controlled-v1',
            source_label='queue-runtime-controlled-source-v1',
            authorization_ref='stage7-runtime-authorization-v1',
            value_json='{"healthy": true}',
            stdout=StringIO(),
        )
        signal = OperationalRuntimeSignal.objects.get(signal_key=RuntimeSignalKey.QUEUE_RUNTIME)
        self.assertEqual(signal.source_label, 'queue-runtime-controlled-source-v1')
        self.assertEqual(signal.authorization_ref, 'stage7-runtime-authorization-v1')

        with self.assertRaises(CommandError):
            call_command(
                'record_operational_runtime_signal',
                signal_key=RuntimeSignalKey.MONTHLY_CALCULATION_LATENCY,
                status=RuntimeSignalStatus.OK,
                evidence_ref='bad-local-latency',
                value_json='{"duration_ms": -1}',
                stdout=StringIO(),
            )

        with self.assertRaises(CommandError):
            call_command(
                'record_operational_runtime_signal',
                signal_key=RuntimeSignalKey.FAILED_CRONS,
                status=RuntimeSignalStatus.OK,
                source_kind=RuntimeSignalSourceKind.SNAPSHOT_CONTROLADO,
                evidence_ref='cron-runtime-controlled-v1',
                source_label='https://runtime.example/source',
                authorization_ref='stage7-runtime-authorization-v1',
                value_json='{"failed_count": 0}',
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

    def test_command_rejects_repo_output_before_collecting_audit(self):
        blocked_output = (
            Path(settings.PROJECT_ROOT)
            / 'docs'
            / 'operational-observability-should-not-be-versioned.json'
        )
        with patch(
            'core.management.commands.audit_operational_observability.collect_operational_observability_audit'
        ) as collect:
            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_operational_observability',
                    output=str(blocked_output),
                    stdout=StringIO(),
                )

        collect.assert_not_called()
        self.assertFalse(blocked_output.exists())

    def test_record_runtime_signal_rejects_sensitive_evidence_reference(self):
        with self.assertRaises(CommandError):
            call_command(
                'record_operational_runtime_signal',
                signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
                status=RuntimeSignalStatus.OK,
                evidence_ref='postgres://user:super-secret@example.com/db',
                value_json='{"healthy": true}',
                stdout=StringIO(),
            )

    def test_record_runtime_signal_rejects_sensitive_payload_keys(self):
        with self.assertRaises(CommandError):
            call_command(
                'record_operational_runtime_signal',
                signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
                status=RuntimeSignalStatus.OK,
                evidence_ref='queue-runtime-controlled-v1',
                value_json='{"healthy": true, "access_token": "opaque-runtime-value"}',
                stdout=StringIO(),
            )


class OperationalObservabilityAPITests(APITestCase):
    def test_api_requires_operational_role(self):
        reviewer = get_user_model().objects.create_user(
            username='observability-reviewer',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        self.client.force_authenticate(reviewer)

        response = self.client.get(reverse('platform-operational-observability'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_returns_redacted_observability_for_admin(self):
        admin = get_user_model().objects.create_user(
            username='observability-admin',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        OperationalRuntimeSignal.objects.create(
            signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
            status=RuntimeSignalStatus.OK,
            value={'healthy': True, 'debug_url': 'postgres://user:super-secret@example.com/db'},
            evidence_ref='postgres://user:super-secret@example.com/db',
        )
        self.client.force_authenticate(admin)

        response = self.client.get(reverse('platform-operational-observability'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queue_signal = response.data['sections']['runtime_signals'][RuntimeSignalKey.QUEUE_RUNTIME]
        self.assertEqual(queue_signal['status'], RuntimeSignalStatus.OK)
        self.assertFalse(queue_signal['has_evidence_ref'])
        self.assertEqual(queue_signal['source_trace'], {'source_label': False, 'authorization_ref': False})
        self.assertEqual(queue_signal['value'], {'healthy': True})
        self.assertNotIn('evidence_ref', queue_signal)

        rendered = json.dumps(response.data, default=str)
        self.assertNotIn('postgres://', rendered)
        self.assertNotIn('super-secret', rendered)
