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
from django.utils import timezone

from canales.models import CanalMensajeria, EstadoGateCanal, EstadoMensajeSaliente, MensajeSaliente
from cobranza.models import (
    CodigoCobroResidual,
    EstadoCuentaArrendatario,
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    GateCobroExterno,
    IntentoPagoWebPay,
    PagoMensual,
    RepactacionDeuda,
)
from cobranza.services import rebuild_account_state
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
from documentos.models import (
    DocumentoEmitido,
    EstadoDocumento,
    ExpedienteDocumental,
    PoliticaFirmaYNotaria,
    TipoDocumental,
)
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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
        account_state = rebuild_account_state(tenant)
        return {
            'socio': socio,
            'empresa': empresa,
            'mandato': mandato,
            'identity': identity,
            'tenant': tenant,
            'contract': contract,
            'payment': payment,
            'account_state': account_state,
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

    def test_missing_account_state_for_active_billing_tenant_is_blocking(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        EstadoCuentaArrendatario.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.account_state.missing', issue_codes)
        self.assertEqual(result['sections']['account_states']['required_tenants'], 1)
        self.assertEqual(result['sections']['account_states']['missing_for_active_tenant'], 1)

    def test_stale_account_state_summary_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        stale_summary = dict(fixture['account_state'].resumen_operativo)
        stale_summary['saldo_total_clp'] = '0.00'
        EstadoCuentaArrendatario.objects.filter(pk=fixture['account_state'].pk).update(
            resumen_operativo=stale_summary,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.account_state.stale_summary', issue_codes)
        self.assertEqual(result['sections']['account_states']['stale_summary'], 1)

    def test_residual_code_with_non_canonical_reference_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        CodigoCobroResidual.objects.create(
            referencia_visible='BAD-00001',
            arrendatario=fixture['tenant'],
            contrato_origen=fixture['contract'],
            saldo_actual=Decimal('25000.00'),
            estado='activa',
            fecha_activacion=date(2027, 1, 10),
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.residual_code.invalid_model', issue_codes)
        self.assertEqual(result['sections']['residual_codes']['total'], 1)
        self.assertEqual(result['sections']['residual_codes']['active'], 1)
        self.assertEqual(result['sections']['residual_codes']['invalid_model'], 1)

    def test_repayment_with_inconsistent_state_balance_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        RepactacionDeuda.objects.create(
            arrendatario=fixture['tenant'],
            contrato_origen=fixture['contract'],
            deuda_total_original=Decimal('30000.00'),
            cantidad_cuotas=3,
            monto_cuota=Decimal('10000.00'),
            saldo_pendiente=Decimal('0.00'),
            estado='activa',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.repayment.invalid_model', issue_codes)
        self.assertEqual(result['sections']['repayments']['total'], 1)
        self.assertEqual(result['sections']['repayments']['active'], 1)
        self.assertEqual(result['sections']['repayments']['invalid_model'], 1)

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

    def test_sent_message_with_sensitive_external_ref_is_blocking(self):
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
            external_ref='https://provider.example.test/token/secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.message.sent_with_sensitive_external_ref', issue_codes)
        self.assertNotIn('provider.example.test', json.dumps(result))

    def test_prepared_message_with_unformalized_required_document_is_blocking(self):
        fixture = self._create_payment_matrix()
        email_gate = self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        PoliticaFirmaYNotaria.objects.create(
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            requiere_codeudor=False,
            requiere_notaria=False,
            modo_firma_permitido='firma_simple',
            estado='activa',
        )
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='contrato',
            entidad_id=str(fixture['contract'].id),
            estado='abierto',
            owner_operativo=f"mandato:{fixture['mandato'].id}",
        )
        document = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum='d' * 64,
            fecha_carga=timezone.now(),
            origen='generado_sistema',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/stage2-unformalized.pdf',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        MensajeSaliente.objects.create(
            canal=CanalOperacion.EMAIL,
            canal_mensajeria=email_gate,
            identidad_envio=fixture['identity'],
            contrato=fixture['contract'],
            arrendatario=fixture['tenant'],
            documento_emitido=document,
            destinatario=fixture['tenant'].email,
            asunto='Documento sin formalizar',
            cuerpo='No debe estar preparado para envio.',
            estado=EstadoMensajeSaliente.PREPARED,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.message.document_not_formalized', issue_codes)
        self.assertEqual(result['sections']['messages']['document_not_formalized'], 1)

    def test_confirmed_webpay_with_sensitive_external_ref_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        webpay_gate = self._create_valid_webpay_gate()
        IntentoPagoWebPay.objects.create(
            pago_mensual=fixture['payment'],
            gate_cobro=webpay_gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=fixture['payment'].monto_calculado_clp,
            buy_order='LM-PM-STAGE2-SENSITIVE',
            session_id='LM-WP-STAGE2-SENSITIVE',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.CONFIRMED_MANUAL,
            external_ref='https://transbank.example.test/token/secret',
            fecha_pago_webpay=date(2026, 1, 6),
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.webpay_intent.confirmed_with_sensitive_external_ref', issue_codes)
        self.assertNotIn('transbank.example.test', json.dumps(result))

    def test_webpay_intent_with_sensitive_return_ref_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        webpay_gate = self._create_valid_webpay_gate()
        IntentoPagoWebPay.objects.create(
            pago_mensual=fixture['payment'],
            gate_cobro=webpay_gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=fixture['payment'].monto_calculado_clp,
            buy_order='LM-PM-STAGE2-RETURN',
            session_id='LM-WP-STAGE2-RETURN',
            return_url_ref='https://front.example.test/webpay?token=secret',
            estado=EstadoIntentoPagoWebPay.PREPARED,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.webpay_intent.sensitive_return_url_ref', issue_codes)
        self.assertNotIn('front.example.test', json.dumps(result))

    def test_webpay_intent_with_sensitive_provider_payload_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        webpay_gate = self._create_valid_webpay_gate()
        IntentoPagoWebPay.objects.create(
            pago_mensual=fixture['payment'],
            gate_cobro=webpay_gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=fixture['payment'].monto_calculado_clp,
            buy_order='LM-PM-STAGE2-PAYLOAD',
            session_id='LM-WP-STAGE2-PAYLOAD',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.PREPARED,
            provider_payload={'token': 'secret-token', 'status_ref': 'webpay-status-v1'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.webpay_intent.sensitive_provider_payload', issue_codes)
        self.assertEqual(result['sections']['webpay']['sensitive_provider_payload'], 1)
        self.assertNotIn('secret-token', json.dumps(result))

    def test_channel_gate_with_sensitive_reference_is_blocking(self):
        self._create_payment_matrix()
        email_gate = self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        CanalMensajeria.objects.filter(pk=email_gate.pk).update(
            restricciones_operativas={
                'prueba_aislada_ref': 'https://mail.example.test/proof?token=secret',
                'oauth_validado_ref': 'email-oauth-v1',
            }
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.channel_gate_sensitive_reference', issue_codes)
        self.assertNotIn('mail.example.test', json.dumps(result))

    def test_whatsapp_opt_in_with_sensitive_evidence_ref_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        Arrendatario.objects.filter(pk=fixture['tenant'].pk).update(
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='https://wa.example.test/optin?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.whatsapp.opt_in_evidence_sensitive', issue_codes)
        self.assertEqual(result['sections']['channel_identities']['whatsapp_opt_in_sensitive_refs'], 1)
        self.assertNotIn('wa.example.test', json.dumps(result))
        self.assertNotIn('token=secret', json.dumps(result))

    def test_whatsapp_opt_in_with_non_international_phone_is_blocking(self):
        fixture = self._create_payment_matrix()
        self._create_valid_email_gate()
        self._create_valid_webpay_gate()
        Arrendatario.objects.filter(pk=fixture['tenant'].pk).update(
            telefono='912345678',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='optin-phone-controlled',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.whatsapp.phone_invalid', issue_codes)
        self.assertIn('stage2.whatsapp.opt_in_invalid', issue_codes)
        self.assertEqual(result['sections']['channel_identities']['whatsapp_opt_in_invalid_phone'], 1)

    def test_webpay_gate_with_sensitive_reference_is_blocking(self):
        self._create_payment_matrix()
        self._create_valid_email_gate()
        webpay_gate = self._create_valid_webpay_gate()
        GateCobroExterno.objects.filter(pk=webpay_gate.pk).update(
            evidencia_ref='https://transbank.example.test/token/secret'
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage2_cobranza'])
        self.assertIn('stage2.webpay_gate_sensitive_reference', issue_codes)
        self.assertNotIn('transbank.example.test', json.dumps(result))

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
