import json
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from canales.models import CanalMensajeria, EstadoGateCanal, EstadoMensajeSaliente, MensajeSaliente
from cobranza.models import EstadoGateCobroExterno, GateCobroExterno, PagoMensual
from contratos.models import (
    Arrendatario,
    Contrato,
    ContratoPropiedad,
    EstadoContactoArrendatario,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RolContratoPropiedad,
    TipoArrendatario,
)
from core.stage2_cobranza_readiness import collect_stage2_cobranza_readiness
from operacion.models import (
    AsignacionCanalOperacion,
    CanalOperacion,
    CuentaRecaudadora,
    EstadoCuentaRecaudadora,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
)
from patrimonio.models import Empresa, Propiedad, Socio, TipoInmueble


class Stage2CobranzaReadinessTests(TestCase):
    def _create_payment_matrix(self):
        socio = Socio.objects.create(nombre='Socio Stage2', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(razon_social='Empresa Stage2 SpA', rut='88888888-8', estado='activa')
        propiedad = Propiedad.objects.create(
            direccion='Direccion Stage2 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='ST2-001',
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Stage2',
            numero_cuenta='ST2-ACC-001',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=False,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        identity = IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=CanalOperacion.EMAIL,
            remitente_visible='LeaseManager Stage2',
            direccion_o_numero='stage2@example.com',
            credencial_ref='cred-stage2-ref',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=mandato,
            canal=CanalOperacion.EMAIL,
            identidad_envio=identity,
            prioridad=1,
        )
        tenant = Arrendatario.objects.create(
            tipo_arrendatario=TipoArrendatario.NATURAL,
            nombre_razon_social='Arrendatario Stage2',
            rut='33333333-3',
            email='tenant@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio Stage2',
            estado_contacto=EstadoContactoArrendatario.ACTIVE,
        )
        contract = Contrato.objects.create(
            codigo_contrato='CON-ST2-001',
            mandato_operacion=mandato,
            arrendatario=tenant,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
        )
        ContratoPropiedad.objects.create(
            contrato=contract,
            propiedad=propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='001',
        )
        period = PeriodoContractual.objects.create(
            contrato=contract,
            numero_periodo=1,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        payment = PagoMensual.objects.create(
            contrato=contract,
            periodo_contractual=period,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('250000.00'),
            monto_calculado_clp=Decimal('250001.00'),
            monto_pagado_clp=Decimal('0.00'),
            fecha_vencimiento=date(2026, 1, 5),
            codigo_conciliacion_efectivo='001',
        )
        return {
            'socio': socio,
            'empresa': empresa,
            'mandato': mandato,
            'identity': identity,
            'tenant': tenant,
            'contract': contract,
            'payment': payment,
        }

    def _create_valid_email_gate(self):
        return CanalMensajeria.objects.create(
            canal=CanalOperacion.EMAIL,
            provider_key='gmail_api',
            estado_gate=EstadoGateCanal.OPEN,
            evidencia_ref='email-gate-evidence-v1',
            restricciones_operativas={
                'prueba_aislada_ref': 'email-proof-v1',
                'oauth_validado_ref': 'email-oauth-v1',
            },
        )

    def _create_valid_webpay_gate(self):
        return GateCobroExterno.objects.create(
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-gate-evidence-v1',
        )

    def _collect_with_final_refs(self):
        return collect_stage2_cobranza_readiness(
            source_kind='snapshot_controlado',
            source_label='stage2-controlled-v1',
            authorization_ref='stage2-authorization-v1',
            stage1_evidence_ref='stage1-snapshot-controlled-v1',
            email_proof_ref='email-proof-controlled-v1',
            webpay_proof_ref='webpay-proof-controlled-v1',
            responsible_ref='stage2-responsibles-v1',
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage2_cobranza_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.payments_missing', issue_codes)
        self.assertIn('stage2.email.open_gate_missing', issue_codes)
        self.assertIn('stage2.email.active_identity_missing', issue_codes)
        self.assertIn('stage2.email.active_assignment_missing', issue_codes)
        self.assertIn('stage2.webpay.open_gate_missing', issue_codes)
        self.assertIn('stage2.stage1_evidence_ref_missing', issue_codes)
        self.assertIn('stage2.source_kind_not_authorized', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage2_cobranza'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_matrix_and_refs_prepare_but_do_not_close_readiness(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()

        result = collect_stage2_cobranza_readiness(
            source_kind='local',
            stage1_evidence_ref='stage1-snapshot-controlled-v1',
            email_proof_ref='email-proof-controlled-v1',
            webpay_proof_ref='webpay-proof-controlled-v1',
            responsible_ref='stage2-responsibles-v1',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage2.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()

        result = collect_stage2_cobranza_readiness(
            source_kind='snapshot_controlado',
            stage1_evidence_ref='stage1-snapshot-controlled-v1',
            email_proof_ref='email-proof-controlled-v1',
            webpay_proof_ref='webpay-proof-controlled-v1',
            responsible_ref='stage2-responsibles-v1',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.source_label_missing', issue_codes)
        self.assertIn('stage2.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_email_gate_without_active_identity_or_assignment_is_blocking(self):
        self._create_payment_matrix()
        AsignacionCanalOperacion.objects.all().delete()
        IdentidadDeEnvio.objects.all().delete()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.email.active_identity_missing', issue_codes)
        self.assertIn('stage2.email.active_assignment_missing', issue_codes)
        self.assertIn('channel_identities', result['sections'])

    def test_open_whatsapp_gate_without_active_identity_or_assignment_is_blocking(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        CanalMensajeria.objects.create(
            canal=CanalOperacion.WHATSAPP,
            provider_key='twilio',
            estado_gate=EstadoGateCanal.OPEN,
            evidencia_ref='whatsapp-gate-v1',
            restricciones_operativas={'template_aprobado_ref': 'whatsapp-template-v1'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.whatsapp.active_identity_missing', issue_codes)
        self.assertIn('stage2.whatsapp.active_assignment_missing', issue_codes)

    def test_open_email_gate_without_required_refs_is_blocking(self):
        CanalMensajeria.objects.create(
            canal=CanalOperacion.EMAIL,
            provider_key='gmail_api',
            estado_gate=EstadoGateCanal.OPEN,
        )

        result = collect_stage2_cobranza_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.channel_gate_invalid', issue_codes)
        self.assertIn('stage2.email.open_gate_missing', issue_codes)

    def test_open_whatsapp_gate_without_template_is_blocking(self):
        CanalMensajeria.objects.create(
            canal=CanalOperacion.WHATSAPP,
            provider_key='twilio',
            estado_gate=EstadoGateCanal.OPEN,
            evidencia_ref='whatsapp-gate-v1',
        )

        result = collect_stage2_cobranza_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.whatsapp.template_missing', issue_codes)

    def test_sent_message_without_external_ref_is_blocking(self):
        fixture = self._create_payment_matrix()
        email_gate = self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        MensajeSaliente.objects.create(
            canal=CanalOperacion.EMAIL,
            canal_mensajeria=email_gate,
            identidad_envio=fixture['identity'],
            contrato=fixture['contract'],
            arrendatario=fixture['tenant'],
            destinatario=fixture['tenant'].email,
            asunto='Aviso',
            cuerpo='Cobranza controlada',
            estado=EstadoMensajeSaliente.SENT,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.message.sent_without_external_ref', issue_codes)

    def test_sensitive_final_refs_do_not_close_readiness(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()

        result = collect_stage2_cobranza_readiness(
            source_kind='snapshot_controlado',
            stage1_evidence_ref='https://example.com/stage1',
            email_proof_ref='email-proof-controlled-v1',
            webpay_proof_ref='webpay-proof-controlled-v1',
            responsible_ref='stage2-responsibles-v1',
        )

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.stage1_evidence_ref_missing', {issue['code'] for issue in result['issues']})

    def test_command_writes_json_and_rejects_versionable_repo_output(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage2_readiness.json'
            call_command('audit_stage2_cobranza_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertIn('channels', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage2-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage2_cobranza_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage2_cobranza_readiness', fail_on_attention=True, stdout=StringIO())
