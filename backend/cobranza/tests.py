from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent, ManualResolution
from canales.models import ConfiguracionNotificacionContrato, NotificacionCobranzaProgramada
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
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
from patrimonio.models import ComunidadPatrimonial, Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import (
    AjusteContrato,
    DistribucionCobroMensual,
    CodigoCobroResidual,
    EstadoCobroResidual,
    EstadoCuentaArrendatario,
    EstadoGarantia,
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    EstadoPago,
    EFFECTIVE_CODE_APPLIED_EVENT_TYPE,
    EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
    GateCobroExterno,
    GarantiaContractual,
    HistorialGarantia,
    IntentoPagoWebPay,
    MANUAL_UF_LOAD_EVENT_TYPE,
    PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
    WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
    WEBPAY_PREPARE_EVENT_TYPE,
)
from .admin import (
    AjusteContratoAdmin,
    CodigoCobroResidualAdmin,
    EstadoCuentaArrendatarioAdmin,
    GateCobroExternoAdmin,
    GarantiaContractualAdmin,
    HistorialGarantiaAdmin,
    IntentoPagoWebPayAdmin,
    PagoMensualAdmin,
    RepactacionDeudaAdmin,
    ValorUFDiarioAdmin,
)
from .services import (
    confirm_webpay_intent_manually,
    prepare_webpay_intent,
    rebuild_account_state,
    save_repayment_plan,
    save_uf_value,
    sync_payment_distribution,
    update_payment_operational_fields,
)


class CobranzaAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='billing', password='secret123')
        self.client.force_authenticate(self.user)

    def _make_rut(self, number):
        reversed_digits = map(int, reversed(str(number)))
        factors = [2, 3, 4, 5, 6, 7]
        total = sum(digit * factors[index % len(factors)] for index, digit in enumerate(reversed_digits))
        remainder = 11 - (total % 11)
        if remainder == 11:
            dv = '0'
        elif remainder == 10:
            dv = 'K'
        else:
            dv = str(remainder)
        return f'{number}-{dv}'

    def _rut_for_code(self, code, offset=0):
        seed = sum((index + 1) * ord(char) for index, char in enumerate(code)) + offset
        return self._make_rut(10_000_000 + seed)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre, rut, socio_1_rut, socio_2_rut):
        socio_1 = self._create_socio(f'{nombre} Socio 1', socio_1_rut)
        socio_2 = self._create_socio(f'{nombre} Socio 2', socio_2_rut)
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        return empresa

    def _create_active_contract(self, *, codigo='CON-001', moneda='CLP', monto_base='523456.00', code='042'):
        propietario = self._create_socio(f'Prop {codigo}', self._rut_for_code(codigo, 0))
        admin_company = self._create_active_empresa(
            f'Admin {codigo}',
            self._rut_for_code(codigo, 100),
            self._rut_for_code(codigo, 200),
            self._rut_for_code(codigo, 300),
        )
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo}',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=f'PROP-{codigo}'[:16],
            estado='activa',
            socio_owner=propietario,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=admin_company,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=admin_company.razon_social,
            titular_rut=admin_company.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_socio_owner=propietario,
            administrador_empresa_owner=admin_company,
            recaudador_empresa_owner=admin_company,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut=self._rut_for_code(codigo, 400),
            email='tenant@example.com',
            telefono='999',
            domicilio_notificaciones='Notificaciones 123',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot=code,
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base=monto_base,
            moneda_base=moneda,
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        return contrato

    def _generate_monthly_payment(self, *, codigo='CON-WEBPAY', monto_base='100000.00', code='111'):
        contrato = self._create_active_contract(codigo=codigo, monto_base=monto_base, code=code)
        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return PagoMensual.objects.get(pk=response.data['id'])

    def test_cobranza_admin_redacts_sensitive_refs(self):
        payment = self._generate_monthly_payment(codigo='CON-ADM-COB')
        PagoMensual.objects.filter(pk=payment.pk).update(
            estado_pago=EstadoPago.FORGIVEN,
            resolucion_pago_excepcional_ref='https://billing.example.test/payment?token=secret',
            resolucion_pago_excepcional_motivo='Resolucion en https://billing.example.test/payment?token=secret',
        )
        payment.refresh_from_db()
        uf_value = ValorUFDiario.objects.create(
            fecha=date(2026, 1, 1),
            valor=Decimal('35000.0000'),
            source_key='UF.CargaManualExtraordinaria',
            evidencia_ref='https://billing.example.test/uf?token=secret',
            motivo_carga='Carga desde https://billing.example.test/uf?token=secret',
            responsable_ref='mailto:ops@example.test',
        )
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='https://billing.example.test/gate?token=secret',
            restricciones_operativas={
                'api_key': 'secret-value',
                'safe_ref': 'webpay-controlled-ref',
            },
        )
        intent = IntentoPagoWebPay.objects.create(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=Decimal('100000.00'),
            buy_order='BO-ADMIN-COB',
            session_id='SESSION-ADMIN-COB',
            return_url_ref='https://billing.example.test/return?token=secret',
            estado=EstadoIntentoPagoWebPay.CONFIRMED_MANUAL,
            motivo_bloqueo='Bloqueo en https://billing.example.test/block?token=secret',
            external_ref='https://billing.example.test/external?token=secret',
            fecha_pago_webpay=date(2026, 1, 6),
            provider_payload={
                'access_token': 'secret-value',
                'callback': 'https://billing.example.test/callback?token=secret',
                'result_ref': 'webpay-controlled-result',
            },
        )
        guarantee = GarantiaContractual.objects.create(
            contrato=payment.contrato,
            monto_pactado=Decimal('100000.00'),
            monto_recibido=Decimal('50000.00'),
            monto_devuelto=Decimal('0.00'),
            monto_aplicado=Decimal('0.00'),
            estado_garantia=EstadoGarantia.HELD,
            fecha_recepcion=date(2026, 1, 1),
            aceptacion_parcial_ref='https://billing.example.test/guarantee?token=secret',
            resolucion_exceso_garantia='clasificar',
            resolucion_exceso_garantia_ref='https://billing.example.test/excess?token=secret',
            resolucion_exceso_garantia_motivo='Exceso en https://billing.example.test/excess?token=secret',
        )
        history = HistorialGarantia.objects.create(
            garantia_contractual=guarantee,
            tipo_movimiento='deposito',
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 1),
            justificacion='Deposito en https://billing.example.test/history?token=secret',
        )
        repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original=Decimal('50000.00'),
            cantidad_cuotas=4,
            monto_cuota=Decimal('10000.00'),
            saldo_pendiente=Decimal('40000.00'),
            estado='activa',
            excepcion_parcial_ref='https://billing.example.test/repayment?token=secret',
            excepcion_parcial_motivo='Excepcion en https://billing.example.test/repayment?token=secret',
        )

        site = AdminSite()
        uf_admin = ValorUFDiarioAdmin(ValorUFDiario, site)
        payment_admin = PagoMensualAdmin(PagoMensual, site)
        gate_admin = GateCobroExternoAdmin(GateCobroExterno, site)
        intent_admin = IntentoPagoWebPayAdmin(IntentoPagoWebPay, site)
        guarantee_admin = GarantiaContractualAdmin(GarantiaContractual, site)
        history_admin = HistorialGarantiaAdmin(HistorialGarantia, site)
        repayment_admin = RepactacionDeudaAdmin(RepactacionDeuda, site)
        residual_admin = CodigoCobroResidualAdmin(CodigoCobroResidual, site)
        account_state_admin = EstadoCuentaArrendatarioAdmin(EstadoCuentaArrendatario, site)

        self.assertNotIn('evidencia_ref', uf_admin.fields)
        self.assertNotIn('responsable_ref', uf_admin.search_fields)
        self.assertEqual(uf_admin.evidencia_ref_redacted(uf_value), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(uf_admin.motivo_carga_redacted(uf_value), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(uf_admin.responsable_ref_redacted(uf_value), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resolucion_pago_excepcional_ref', payment_admin.fields)
        self.assertEqual(
            payment_admin.resolucion_pago_excepcional_ref_redacted(payment),
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            payment_admin.resolucion_pago_excepcional_motivo_redacted(payment),
            REDACTED_SENSITIVE_REFERENCE,
        )

        self.assertNotIn('evidencia_ref', gate_admin.fields)
        self.assertNotIn('restricciones_operativas', gate_admin.fields)
        self.assertNotIn('evidencia_ref', gate_admin.search_fields)
        self.assertEqual(gate_admin.evidencia_ref_redacted(gate), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            gate_admin.restricciones_operativas_redacted(gate)['api_key'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(gate_admin.restricciones_operativas_redacted(gate)['safe_ref'], 'webpay-controlled-ref')

        self.assertNotIn('external_ref', intent_admin.fields)
        self.assertNotIn('external_ref', intent_admin.search_fields)
        self.assertEqual(intent_admin.return_url_ref_redacted(intent), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intent_admin.motivo_bloqueo_redacted(intent), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intent_admin.external_ref_redacted(intent), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intent_admin.provider_payload_redacted(intent)['access_token'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intent_admin.provider_payload_redacted(intent)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intent_admin.provider_payload_redacted(intent)['result_ref'], 'webpay-controlled-result')

        self.assertNotIn('aceptacion_parcial_ref', guarantee_admin.fields)
        self.assertEqual(guarantee_admin.aceptacion_parcial_ref_redacted(guarantee), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            guarantee_admin.resolucion_exceso_garantia_ref_redacted(guarantee),
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            guarantee_admin.resolucion_exceso_garantia_motivo_redacted(guarantee),
            REDACTED_SENSITIVE_REFERENCE,
        )

        self.assertNotIn('justificacion', history_admin.fields)
        self.assertNotIn('justificacion', history_admin.search_fields)
        self.assertEqual(history_admin.justificacion_redacted(history), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('excepcion_parcial_ref', repayment_admin.fields)
        self.assertEqual(repayment_admin.excepcion_parcial_ref_redacted(repayment), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(repayment_admin.excepcion_parcial_motivo_redacted(repayment), REDACTED_SENSITIVE_REFERENCE)
        self.assertIn('saldo_actual', residual_admin.fields)
        self.assertIn('estado', residual_admin.fields)
        self.assertIn('saldo_actual', residual_admin.readonly_fields)
        self.assertIn('estado', residual_admin.readonly_fields)
        self.assertFalse(residual_admin.has_delete_permission(None))
        for admin_instance in (
            uf_admin,
            payment_admin,
            gate_admin,
            intent_admin,
            guarantee_admin,
            history_admin,
            repayment_admin,
            residual_admin,
            account_state_admin,
        ):
            self.assertFalse(admin_instance.has_add_permission(None))
            self.assertFalse(admin_instance.has_change_permission(None, object()))
            self.assertFalse(admin_instance.has_delete_permission(None))

    def test_adjustment_admin_redacts_sensitive_justification(self):
        contrato = self._create_active_contract(codigo='CON-ADM-AJUS', monto_base='100000.00', code='111')
        adjustment = AjusteContrato.objects.create(
            contrato=contrato,
            tipo_ajuste='cargo_controlado',
            monto=Decimal('1000.00'),
            moneda='CLP',
            mes_inicio=date(2026, 1, 1),
            mes_fin=date(2026, 1, 1),
            justificacion='Cargo operativo controlado',
        )
        AjusteContrato.objects.filter(pk=adjustment.pk).update(
            justificacion='Cargo respaldado en https://billing.example.test/adjustment?token=secret'
        )
        adjustment.refresh_from_db()

        adjustment_admin = AjusteContratoAdmin(AjusteContrato, AdminSite())

        self.assertNotIn('justificacion', adjustment_admin.fields)
        self.assertNotIn('justificacion', adjustment_admin.search_fields)
        self.assertEqual(adjustment_admin.justificacion_redacted(adjustment), REDACTED_SENSITIVE_REFERENCE)
        self.assertFalse(adjustment_admin.has_add_permission(None))
        self.assertFalse(adjustment_admin.has_change_permission(None, adjustment))
        self.assertFalse(adjustment_admin.has_delete_permission(None))

    def test_refresh_mora_marks_pending_payment_overdue_and_updates_account_state(self):
        payment = self._generate_monthly_payment(codigo='CON-MORA-REFRESH')
        rebuild_account_state(payment.contrato.arrendatario)

        response = self.client.post(
            reverse('cobranza-pago-refresh-mora'),
            {'fecha_corte': '2026-01-10'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['reference_date'], '2026-01-10')
        self.assertEqual(response.data['updated_count'], 1)
        self.assertEqual(response.data['tenant_count'], 1)
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.OVERDUE)
        self.assertEqual(payment.dias_mora, 5)
        account_state = payment.contrato.arrendatario.estado_cuenta
        account_state.refresh_from_db()
        self.assertEqual(account_state.resumen_operativo['pagos_abiertos'], 1)
        self.assertEqual(account_state.resumen_operativo['pagos_atrasados'], 1)
        self.assertTrue(AuditEvent.objects.filter(event_type='cobranza.pago_mensual.overdue_refreshed').exists())

    def test_refresh_overdue_payments_rolls_back_when_view_audit_fails(self):
        payment = self._generate_monthly_payment(codigo='CON-MORA-AUDIT-ROLLBACK')

        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.post(
                    reverse('cobranza-pago-refresh-mora'),
                    {'fecha_corte': '2026-01-10'},
                    format='json',
                )

        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertEqual(payment.dias_mora, 0)
        self.assertFalse(
            AuditEvent.objects.filter(event_type='cobranza.pago_mensual.overdue_refreshed').exists()
        )

    def test_account_state_rebuild_rolls_back_when_view_audit_fails(self):
        payment = self._generate_monthly_payment(codigo='CON-STATE-AUDIT-ROLLBACK')

        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.post(
                    reverse('cobranza-estado-cuenta-rebuild'),
                    {'arrendatario_id': payment.contrato.arrendatario_id},
                    format='json',
                )

        self.assertFalse(EstadoCuentaArrendatario.objects.filter(arrendatario=payment.contrato.arrendatario).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='cobranza.estado_cuenta_arrendatario.rebuilt').exists())

    def test_account_state_observations_reject_and_redact_sensitive_values(self):
        payment = self._generate_monthly_payment(codigo='CON-STATE-OBS')
        account_state = rebuild_account_state(payment.contrato.arrendatario)
        EstadoCuentaArrendatario.objects.filter(pk=account_state.pk).update(
            observaciones='Revision en https://billing.example.test/account?token=secret',
        )
        account_state.refresh_from_db()

        detail_response = self.client.get(reverse('cobranza-estado-cuenta-detail', args=[account_state.pk]))
        list_response = self.client.get(reverse('cobranza-estado-cuenta-list'))
        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(list_response.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['estados_cuenta'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)

        account_state_admin = EstadoCuentaArrendatarioAdmin(EstadoCuentaArrendatario, AdminSite())
        self.assertNotIn('observaciones', account_state_admin.fields)
        self.assertEqual(account_state_admin.observaciones_redacted(account_state), REDACTED_SENSITIVE_REFERENCE)
        self.assertFalse(account_state_admin.has_add_permission(None))

        update_response = self.client.patch(
            reverse('cobranza-estado-cuenta-detail', args=[account_state.pk]),
            {'observaciones': 'Seguimiento en https://billing.example.test/account?token=secret'},
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', update_response.data)

    def test_account_state_score_cannot_be_patched_directly(self):
        payment = self._generate_monthly_payment(codigo='CON-STATE-SCORE-PATCH')
        account_state = rebuild_account_state(payment.contrato.arrendatario)

        response = self.client.patch(
            reverse('cobranza-estado-cuenta-detail', args=[account_state.pk]),
            {'score_pago': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('score_pago', response.data)
        account_state.refresh_from_db()
        self.assertEqual(account_state.score_pago, 0)

    def test_account_state_admin_rebuild_fields_are_read_only(self):
        account_state_admin = EstadoCuentaArrendatarioAdmin(EstadoCuentaArrendatario, AdminSite())

        self.assertIn('resumen_operativo', account_state_admin.fields)
        self.assertIn('score_pago', account_state_admin.fields)
        self.assertIn('resumen_operativo', account_state_admin.readonly_fields)
        self.assertIn('score_pago', account_state_admin.readonly_fields)
        self.assertNotIn('observaciones', account_state_admin.fields)
        self.assertIn('observaciones_redacted', account_state_admin.readonly_fields)

    def _create_contract_for_company_and_arrendatario(self, *, empresa, arrendatario, codigo='CON-SHARED', owner_kind='empresa', comunidad=None):
        propietario_socio = None
        empresa_owner = empresa if owner_kind == 'empresa' else None
        comunidad_owner = comunidad if owner_kind == 'comunidad' else None
        if owner_kind == 'socio':
            propietario_socio = self._create_socio(f'Prop {codigo}', self._rut_for_code(codigo, 999))

        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo}',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=f'PROP-{codigo}'[:16],
            estado='activa',
            empresa_owner=empresa_owner,
            comunidad_owner=comunidad_owner,
            socio_owner=propietario_socio,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa if owner_kind == 'empresa' else None,
            propietario_comunidad_owner=comunidad if owner_kind == 'comunidad' else None,
            propietario_socio_owner=propietario_socio if owner_kind == 'socio' else None,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa if owner_kind == 'empresa' else None,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=owner_kind == 'empresa',
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        periodo = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        return contrato, periodo

    def test_auth_is_required_for_cobranza_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('cobranza-valor-uf-list'),
            reverse('cobranza-ajuste-list'),
            reverse('cobranza-pago-list'),
            reverse('cobranza-pago-generate'),
            reverse('cobranza-webpay-gate-list'),
            reverse('cobranza-webpay-intent-list'),
            reverse('cobranza-garantia-list'),
            reverse('cobranza-historial-list'),
            reverse('cobranza-repactacion-list'),
            reverse('cobranza-residual-list'),
            reverse('cobranza-estado-cuenta-list'),
            reverse('cobranza-estado-cuenta-rebuild'),
        ]

        for url in urls:
            response = client.get(url) if ('generar' not in url and 'recalcular' not in url) else client.post(url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manual_uf_requires_traceable_provenance(self):
        response = self.client.post(
            reverse('cobranza-valor-uf-list'),
            {
                'fecha': '2026-01-01',
                'valor': '35000.0000',
                'source_key': 'UF.CargaManualExtraordinaria',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_ref', response.data)
        self.assertIn('motivo_carga', response.data)
        self.assertIn('responsable_ref', response.data)

    def test_uf_rejects_non_canonical_source_key(self):
        response = self.client.post(
            reverse('cobranza-valor-uf-list'),
            {
                'fecha': '2026-01-01',
                'valor': '35000.0000',
                'source_key': 'spreadsheet_snapshot',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('source_key', response.data)

    def test_uf_create_rolls_back_when_view_audit_fails(self):
        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.post(
                    reverse('cobranza-valor-uf-list'),
                    {
                        'fecha': '2026-01-01',
                        'valor': '35000.0000',
                        'source_key': 'UF.BancoCentral',
                    },
                    format='json',
                )

        self.assertFalse(ValorUFDiario.objects.filter(fecha=date(2026, 1, 1)).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='cobranza.valor_uf.created').exists())

    def test_manual_uf_records_auditable_trace(self):
        response = self.client.post(
            reverse('cobranza-valor-uf-list'),
            {
                'fecha': '2026-01-01',
                'valor': '35000.0000',
                'source_key': 'UF.CargaManualExtraordinaria',
                'evidencia_ref': '  uf-manual-evidence-2026-01-01  ',
                'motivo_carga': '  Falla total de fuentes automaticas registrada para demo controlada.  ',
                'responsable_ref': '  ops-uf-responsible-001  ',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['evidencia_ref'], 'uf-manual-evidence-2026-01-01')
        self.assertEqual(response.data['motivo_carga'], 'Falla total de fuentes automaticas registrada para demo controlada.')
        self.assertEqual(response.data['responsable_ref'], 'ops-uf-responsible-001')
        uf_value = ValorUFDiario.objects.get(pk=response.data['id'])
        self.assertEqual(uf_value.evidencia_ref, 'uf-manual-evidence-2026-01-01')
        self.assertEqual(uf_value.motivo_carga, 'Falla total de fuentes automaticas registrada para demo controlada.')
        self.assertEqual(uf_value.responsable_ref, 'ops-uf-responsible-001')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=MANUAL_UF_LOAD_EVENT_TYPE,
                entity_type='valor_uf_diario',
                entity_id=str(response.data['id']),
                actor_user=self.user,
                metadata__evidencia_ref='uf-manual-evidence-2026-01-01',
                metadata__motivo_carga='Falla total de fuentes automaticas registrada para demo controlada.',
                metadata__responsable_ref='ops-uf-responsible-001',
            ).exists()
        )

    def test_manual_uf_service_creates_audit_event(self):
        uf_value, event = save_uf_value(
            validated_data={
                'fecha': date(2026, 1, 1),
                'valor': Decimal('35000.0000'),
                'source_key': 'UF.CargaManualExtraordinaria',
                'evidencia_ref': '  uf-manual-service-2026-01-01  ',
                'motivo_carga': '  Carga manual controlada desde servicio de dominio.  ',
                'responsable_ref': '  ops-uf-responsible-001  ',
            },
            actor_user=self.user,
            ip_address='127.0.0.1',
        )

        self.assertIsNotNone(event)
        self.assertEqual(uf_value.evidencia_ref, 'uf-manual-service-2026-01-01')
        self.assertEqual(uf_value.motivo_carga, 'Carga manual controlada desde servicio de dominio.')
        self.assertEqual(uf_value.responsable_ref, 'ops-uf-responsible-001')
        self.assertEqual(event.event_type, MANUAL_UF_LOAD_EVENT_TYPE)
        self.assertEqual(event.entity_type, 'valor_uf_diario')
        self.assertEqual(event.entity_id, str(uf_value.pk))
        self.assertEqual(event.actor_user, self.user)
        self.assertEqual(event.ip_address, '127.0.0.1')
        self.assertEqual(event.metadata['fecha'], '2026-01-01')
        self.assertEqual(event.metadata['valor'], '35000.0000')
        self.assertEqual(event.metadata['source_key'], 'UF.CargaManualExtraordinaria')
        self.assertEqual(event.metadata['evidencia_ref'], 'uf-manual-service-2026-01-01')
        self.assertEqual(event.metadata['motivo_carga'], 'Carga manual controlada desde servicio de dominio.')
        self.assertEqual(event.metadata['responsable_ref'], 'ops-uf-responsible-001')

    def test_manual_uf_service_requires_actor(self):
        with self.assertRaisesMessage(ValueError, 'actor trazable'):
            save_uf_value(
                validated_data={
                    'fecha': date(2026, 1, 1),
                    'valor': Decimal('35000.0000'),
                    'source_key': 'UF.CargaManualExtraordinaria',
                    'evidencia_ref': 'uf-manual-service-2026-01-01',
                    'motivo_carga': 'Carga manual controlada desde servicio de dominio.',
                    'responsable_ref': 'ops-uf-responsible-001',
                },
            )

        self.assertFalse(ValorUFDiario.objects.filter(fecha=date(2026, 1, 1)).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type=MANUAL_UF_LOAD_EVENT_TYPE).exists())

    def test_generate_clp_payment_applies_effective_code(self):
        contrato = self._create_active_contract(codigo='CON-CLP', monto_base='523456.00', code='042')

        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['monto_facturable_clp'], '523456.00')
        self.assertEqual(response.data['monto_calculado_clp'], '523042.00')
        self.assertEqual(response.data['monto_efecto_codigo_efectivo_clp'], '-414.00')
        self.assertEqual(response.data['codigo_conciliacion_efectivo'], '042')
        self.assertEqual(len(response.data['distribuciones_detail']), 1)
        self.assertEqual(response.data['distribuciones_detail'][0]['beneficiario_tipo'], 'socio')
        self.assertEqual(response.data['distribuciones_detail'][0]['monto_devengado_clp'], '523456.00')
        self.assertEqual(response.data['distribuciones_detail'][0]['monto_facturable_clp'], '0.00')
        self.assertTrue(AuditEvent.objects.filter(event_type='cobranza.pago_mensual.generated').exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EFFECTIVE_CODE_APPLIED_EVENT_TYPE,
                entity_type='pago_mensual',
                entity_id=str(response.data['id']),
                actor_user=self.user,
                metadata__monto_efecto_codigo_efectivo_clp='-414.00',
            ).exists()
        )

    def test_generate_payment_materializes_collection_notification_schedule(self):
        contrato = self._create_active_contract(codigo='CON-NOTIFY', monto_base='523456.00', code='042')
        empresa = contrato.mandato_operacion.administrador_empresa_owner
        identity = IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=CanalOperacion.EMAIL,
            remitente_visible='LeaseManager Cobranza',
            direccion_o_numero='cobranza@example.com',
            credencial_ref='cred-cobranza-ref',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal=CanalOperacion.EMAIL,
            identidad_envio=identity,
            prioridad=1,
        )
        ConfiguracionNotificacionContrato.objects.create(
            contrato=contrato,
            canal=CanalOperacion.EMAIL,
            dias_notificacion=[1, 3, 5, 10, 15, 20, 25],
            activa=True,
        )

        first = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        second = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        payment = PagoMensual.objects.get(pk=first.data['id'])
        self.assertEqual(NotificacionCobranzaProgramada.objects.filter(pago_mensual=payment).count(), 7)
        self.assertEqual(
            list(
                NotificacionCobranzaProgramada.objects.filter(pago_mensual=payment)
                .order_by('dia_notificacion')
                .values_list('dia_notificacion', flat=True)
            ),
            [1, 3, 5, 10, 15, 20, 25],
        )
        self.assertTrue(
            AuditEvent.objects.filter(event_type='canales.notificacion_cobranza.materialized').exists()
        )

    def test_payment_full_clean_rejects_zero_effective_code(self):
        contrato = self._create_active_contract(codigo='CON-PAY-ZERO', monto_base='100000.00', code='111')
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        payment = PagoMensual(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('100000.00'),
            monto_calculado_clp=Decimal('100000.00'),
            fecha_vencimiento='2026-01-05',
            codigo_conciliacion_efectivo='000',
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_full_clean_rejects_untraced_effective_code_effect(self):
        contrato = self._create_active_contract(codigo='CON-PAY-EFFECT', monto_base='100000.00', code='111')
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        payment = PagoMensual(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('100000.00'),
            monto_calculado_clp=Decimal('100111.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('0.00'),
            fecha_vencimiento='2026-01-05',
            codigo_conciliacion_efectivo='111',
        )

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()

        self.assertIn('monto_efecto_codigo_efectivo_clp', error.exception.message_dict)

    def test_payment_full_clean_rejects_month_outside_period(self):
        contrato = self._create_active_contract(codigo='CON-PAY-PERIOD', monto_base='100000.00', code='111')
        first_period = contrato.periodos_contractuales.get(numero_periodo=1)
        first_period.fecha_fin = date(2026, 6, 30)
        first_period.save(update_fields=['fecha_fin', 'updated_at'])
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base=Decimal('120000.00'),
            moneda_base='CLP',
            tipo_periodo='renovacion',
            origen_periodo='manual',
        )
        payment = PagoMensual(
            contrato=contrato,
            periodo_contractual=first_period,
            mes=7,
            anio=2026,
            monto_facturable_clp=Decimal('100000.00'),
            monto_calculado_clp=Decimal('100111.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('111.00'),
            fecha_vencimiento=date(2026, 7, 5),
            codigo_conciliacion_efectivo='111',
        )

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()
        self.assertIn('periodo_contractual', error.exception.message_dict)

    def test_payment_full_clean_rejects_due_date_outside_operational_month(self):
        contrato = self._create_active_contract(codigo='CON-PAY-DUE', monto_base='100000.00', code='111')
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        payment = PagoMensual(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('100000.00'),
            monto_calculado_clp=Decimal('100111.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('111.00'),
            fecha_vencimiento=date(2026, 2, 5),
            codigo_conciliacion_efectivo='111',
        )

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()
        self.assertIn('fecha_vencimiento', error.exception.message_dict)

    def test_payment_full_clean_requires_uf_trace_for_uf_period(self):
        contrato = self._create_active_contract(codigo='CON-PAY-UF-TRACE', moneda='UF', monto_base='10.00', code='111')
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        payment = PagoMensual(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('350000.00'),
            monto_calculado_clp=Decimal('350111.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('111.00'),
            fecha_vencimiento=date(2026, 1, 5),
            codigo_conciliacion_efectivo='111',
        )

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()
        self.assertIn('moneda_calculo', error.exception.message_dict)
        self.assertIn('uf_fecha_usada', error.exception.message_dict)
        self.assertIn('uf_valor_usado', error.exception.message_dict)
        self.assertIn('uf_source_key', error.exception.message_dict)

    def test_payment_full_clean_rejects_paid_state_without_traceable_payment(self):
        contrato = self._create_active_contract(codigo='CON-PAY-CLOSE', monto_base='100000.00', code='111')
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        payment = PagoMensual(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('100000.00'),
            monto_calculado_clp=Decimal('100111.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('111.00'),
            monto_pagado_clp=Decimal('0.00'),
            fecha_vencimiento=date(2026, 1, 5),
            estado_pago=EstadoPago.PAID,
            codigo_conciliacion_efectivo='111',
        )

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()
        self.assertIn('monto_pagado_clp', error.exception.message_dict)
        self.assertIn('fecha_deposito_banco', error.exception.message_dict)

    def test_generate_uf_payment_requires_existing_uf_value(self):
        contrato = self._create_active_contract(codigo='CON-UF-MISS', moneda='UF', monto_base='10.00', code='123')

        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('2026-01-05', response.data['detail'])

    def test_generate_uf_payment_applies_adjustments_before_effective_code(self):
        contrato = self._create_active_contract(codigo='CON-UF-OK', moneda='UF', monto_base='10.00', code='123')
        ValorUFDiario.objects.create(
            fecha=date(2026, 1, 5),
            valor='35000.0000',
            source_key='UF.CargaManualExtraordinaria',
            evidencia_ref='uf-manual-evidence-2026-01-05',
            motivo_carga='Carga manual controlada para prueba local.',
            responsable_ref='ops-uf-responsible-001',
        )
        AjusteContrato.objects.create(
            contrato=contrato,
            tipo_ajuste='cargo_extra',
            monto='5000.00',
            moneda='CLP',
            mes_inicio='2026-01-01',
            mes_fin='2026-01-01',
            justificacion='Cargo enero',
        )

        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['monto_facturable_clp'], '355000.00')
        self.assertEqual(response.data['monto_calculado_clp'], '355123.00')
        self.assertEqual(response.data['moneda_calculo'], 'UF')
        self.assertEqual(response.data['uf_fecha_usada'], '2026-01-05')
        self.assertEqual(response.data['uf_valor_usado'], '35000.0000')
        self.assertEqual(response.data['uf_source_key'], 'UF.CargaManualExtraordinaria')

        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        snapshot_pago = snapshot_response.data['pagos'][0]
        self.assertEqual(snapshot_pago['id'], response.data['id'])
        self.assertEqual(snapshot_pago['periodo_contractual'], response.data['periodo_contractual'])
        self.assertEqual(snapshot_pago['moneda_calculo'], 'UF')
        self.assertEqual(snapshot_pago['uf_fecha_usada'], date(2026, 1, 5))
        self.assertEqual(snapshot_pago['uf_valor_usado'], Decimal('35000.0000'))
        self.assertEqual(snapshot_pago['uf_source_key'], 'UF.CargaManualExtraordinaria')
        self.assertEqual(snapshot_pago['codigo_conciliacion_efectivo'], '123')
        self.assertIsNone(snapshot_pago['fecha_deposito_banco'])
        self.assertIsNone(snapshot_pago['fecha_deteccion_sistema'])

    def test_generate_payment_is_idempotent_for_same_contract_and_month(self):
        contrato = self._create_active_contract(codigo='CON-IDEM', monto_base='100000.00', code='111')

        first = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        second = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(PagoMensual.objects.filter(contrato=contrato, anio=2026, mes=1).count(), 1)

    def test_generate_payment_rejects_automatic_past_billing_for_retroactive_contract(self):
        contrato = self._create_active_contract(codigo='CON-RETRO', monto_base='100000.00', code='111')
        contrato.fecha_registro_operativo = date(2026, 2, 10)
        contrato.save(update_fields=['fecha_registro_operativo', 'updated_at'])

        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Contrato retroactivo', response.data['detail'])
        self.assertFalse(PagoMensual.objects.filter(contrato=contrato, anio=2026, mes=1).exists())

    def test_payment_update_rejects_manual_paid_transition_without_reconciliation_artifact(self):
        contrato = self._create_active_contract(codigo='CON-LATE', monto_base='100000.00', code='111')
        generate = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generate.status_code, status.HTTP_201_CREATED)

        update = self.client.patch(
            reverse('cobranza-pago-detail', args=[generate.data['id']]),
            {
                'estado_pago': EstadoPago.PAID,
                'monto_pagado_clp': '100111.00',
                'fecha_deposito_banco': '2026-01-08',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        pago = PagoMensual.objects.get(pk=generate.data['id'])
        self.assertEqual(pago.estado_pago, EstadoPago.PENDING)
        self.assertEqual(str(pago.monto_pagado_clp), '0.00')
        self.assertFalse(pago.movimientos_bancarios.exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='cobranza.pago_mensual.state_changed').exists())

    def test_payment_update_allows_open_state_transition(self):
        contrato = self._create_active_contract(codigo='CON-OPEN-STATE', monto_base='100000.00', code='111')
        generate = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generate.status_code, status.HTTP_201_CREATED)

        update = self.client.patch(
            reverse('cobranza-pago-detail', args=[generate.data['id']]),
            {'estado_pago': EstadoPago.OVERDUE},
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_pago'], EstadoPago.OVERDUE)
        state_event = AuditEvent.objects.get(
            event_type='cobranza.pago_mensual.state_changed',
            entity_type='pago_mensual',
            entity_id=str(generate.data['id']),
        )
        self.assertEqual(
            state_event.metadata,
            {
                'campo_estado': 'estado_pago',
                'estado_anterior': EstadoPago.PENDING,
                'estado_nuevo': EstadoPago.OVERDUE,
            },
        )

    def test_payment_update_rolls_back_when_view_audit_fails(self):
        payment = self._generate_monthly_payment(codigo='CON-PAY-AUDIT-ROLLBACK')

        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.patch(
                    reverse('cobranza-pago-detail', args=[payment.pk]),
                    {'estado_pago': EstadoPago.OVERDUE},
                    format='json',
                )

        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type__in=['cobranza.pago_mensual.updated', 'cobranza.pago_mensual.state_changed'],
                entity_type='pago_mensual',
                entity_id=str(payment.pk),
            ).exists()
        )

    def test_payment_update_rejects_forgiven_without_trace(self):
        payment = self._generate_monthly_payment(codigo='CON-FORGIVE-NOTRACE')

        response = self.client.patch(
            reverse('cobranza-pago-detail', args=[payment.pk]),
            {'estado_pago': EstadoPago.FORGIVEN},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resolucion_pago_excepcional_ref', response.data)
        self.assertIn('resolucion_pago_excepcional_motivo', response.data)
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)

    def test_payment_update_allows_forgiven_with_trace_and_audit(self):
        payment = self._generate_monthly_payment(codigo='CON-FORGIVE-TRACE')

        response = self.client.patch(
            reverse('cobranza-pago-detail', args=[payment.pk]),
            {
                'estado_pago': EstadoPago.FORGIVEN,
                'resolucion_pago_excepcional_ref': 'payment-forgiven-resolution-2026-01',
                'resolucion_pago_excepcional_motivo': 'Condonacion aprobada por acuerdo operativo controlado.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado_pago'], EstadoPago.FORGIVEN)
        self.assertEqual(response.data['resolucion_pago_excepcional_ref'], 'payment-forgiven-resolution-2026-01')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
                entity_type='pago_mensual',
                entity_id=str(payment.pk),
                actor_user=self.user,
                metadata__estado_pago=EstadoPago.FORGIVEN,
                metadata__resolucion_pago_excepcional_ref='payment-forgiven-resolution-2026-01',
            ).exists()
        )

    def test_payment_exceptional_state_service_creates_audit_event(self):
        payment = self._generate_monthly_payment(codigo='CON-FORGIVE-SERVICE')

        updated, previous_state, audit_event = update_payment_operational_fields(
            payment=payment,
            validated_data={
                'estado_pago': EstadoPago.FORGIVEN,
                'resolucion_pago_excepcional_ref': 'payment-forgiven-service-2026-01',
                'resolucion_pago_excepcional_motivo': 'Condonacion aprobada por acuerdo operativo controlado.',
            },
            actor_user=self.user,
            ip_address='127.0.0.1',
        )

        self.assertEqual(previous_state, EstadoPago.PENDING)
        self.assertEqual(updated.estado_pago, EstadoPago.FORGIVEN)
        self.assertIsNotNone(audit_event)
        self.assertEqual(audit_event.event_type, EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE)
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.ip_address, '127.0.0.1')
        self.assertEqual(audit_event.metadata['previous_state'], EstadoPago.PENDING)
        self.assertEqual(audit_event.metadata['estado_pago'], EstadoPago.FORGIVEN)
        self.assertEqual(
            audit_event.metadata['resolucion_pago_excepcional_ref'],
            'payment-forgiven-service-2026-01',
        )

    def test_payment_exceptional_state_service_requires_actor(self):
        payment = self._generate_monthly_payment(codigo='CON-FORGIVE-NO-ACTOR')

        with self.assertRaisesMessage(ValueError, 'actor trazable'):
            update_payment_operational_fields(
                payment=payment,
                validated_data={
                    'estado_pago': EstadoPago.FORGIVEN,
                    'resolucion_pago_excepcional_ref': 'payment-forgiven-service-2026-01',
                    'resolucion_pago_excepcional_motivo': 'Condonacion aprobada por acuerdo operativo controlado.',
                },
            )

        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
                entity_type='pago_mensual',
                entity_id=str(payment.pk),
            ).exists()
        )

    def test_payment_operational_service_rejects_invalid_state_transition(self):
        payment = self._generate_monthly_payment(codigo='CON-SVC-STATE-GUARD')
        repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='30000.00',
            estado='activa',
        )

        with self.assertRaisesMessage(ValueError, 'Transicion invalida desde pendiente hacia en_repactacion'):
            update_payment_operational_fields(
                payment=payment,
                validated_data={
                    'estado_pago': EstadoPago.IN_REPAYMENT,
                    'repactacion_deuda': repayment,
                },
                actor_user=self.user,
                ip_address='127.0.0.1',
            )

        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertIsNone(payment.repactacion_deuda_id)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
                entity_type='pago_mensual',
                entity_id=str(payment.pk),
            ).exists()
        )

    def test_payment_model_rejects_invalid_state_transition(self):
        payment = self._generate_monthly_payment(codigo='CON-MODEL-STATE-GUARD')
        repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='30000.00',
            estado='activa',
        )
        payment.estado_pago = EstadoPago.IN_REPAYMENT
        payment.repactacion_deuda = repayment

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()

        self.assertIn('estado_pago', error.exception.message_dict)
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertIsNone(payment.repactacion_deuda_id)

    def test_payment_model_allows_overdue_to_repayment_transition(self):
        payment = self._generate_monthly_payment(codigo='CON-MODEL-STATE-OK')
        payment.estado_pago = EstadoPago.OVERDUE
        payment.dias_mora = 5
        payment.save(update_fields=['estado_pago', 'dias_mora', 'updated_at'])
        repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='30000.00',
            estado='activa',
        )

        payment.estado_pago = EstadoPago.IN_REPAYMENT
        payment.repactacion_deuda = repayment

        payment.full_clean()

    def test_payment_update_allows_paid_by_termination_with_trace(self):
        payment = self._generate_monthly_payment(codigo='CON-TERM-TRACE')

        response = self.client.patch(
            reverse('cobranza-pago-detail', args=[payment.pk]),
            {
                'estado_pago': EstadoPago.PAID_BY_TERMINATION,
                'monto_pagado_clp': str(payment.monto_calculado_clp),
                'fecha_deteccion_sistema': '2026-01-08',
                'resolucion_pago_excepcional_ref': 'termination-payment-resolution-2026-01',
                'resolucion_pago_excepcional_motivo': 'Cierre por acuerdo de termino controlado.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado_pago'], EstadoPago.PAID_BY_TERMINATION)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
                entity_type='pago_mensual',
                entity_id=str(payment.pk),
                metadata__estado_pago=EstadoPago.PAID_BY_TERMINATION,
            ).exists()
        )

    def test_payment_exceptional_resolution_rejects_sensitive_reference(self):
        payment = self._generate_monthly_payment(codigo='CON-FORGIVE-SENSITIVE')

        response = self.client.patch(
            reverse('cobranza-pago-detail', args=[payment.pk]),
            {
                'estado_pago': EstadoPago.FORGIVEN,
                'resolucion_pago_excepcional_ref': 'https://example.test/resolution?token=secret',
                'resolucion_pago_excepcional_motivo': 'Condonacion aprobada.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resolucion_pago_excepcional_ref', response.data)

    def test_webpay_prepare_blocks_when_gate_is_not_open(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-BLOCK')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.CONDITIONED,
        )

        response = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'webpay-return-controlled-v1'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoIntentoPagoWebPay.BLOCKED)
        self.assertIn('gate WebPay no esta abierto', response.data['motivo_bloqueo'])
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertEqual(str(payment.monto_pagado_clp), '0.00')
        resolution = ManualResolution.objects.get(
            category='cobranza.webpay.bloqueado',
            scope_type='cobranza.webpay',
            scope_reference=str(response.data['id']),
        )
        self.assertEqual(resolution.requested_by, self.user)
        self.assertEqual(resolution.metadata['intent_id'], response.data['id'])
        audit_event = AuditEvent.objects.get(
            event_type=WEBPAY_PREPARE_EVENT_TYPE,
            entity_type='webpay_intento',
            entity_id=str(response.data['id']),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.metadata['estado'], EstadoIntentoPagoWebPay.BLOCKED)
        self.assertEqual(audit_event.metadata['motivo_bloqueo'], response.data['motivo_bloqueo'])

    def test_webpay_prepare_blocks_open_gate_without_evidence(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-NO-EVID')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='',
        )

        response = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'webpay-return-controlled-v1'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoIntentoPagoWebPay.BLOCKED)
        self.assertIn('requiere evidencia_ref', response.data['motivo_bloqueo'])
        self.assertEqual(IntentoPagoWebPay.objects.count(), 1)

    def test_webpay_gate_normalizes_evidence_ref_before_persisting(self):
        self.user.default_role_code = 'AdministradorGlobal'
        self.user.save(update_fields=['default_role_code'])

        response = self.client.post(
            reverse('cobranza-webpay-gate-list'),
            {
                'capacidad_key': 'WebPay.IntentoPago',
                'provider_key': 'transbank_webpay_normalized',
                'estado_gate': EstadoGateCobroExterno.OPEN,
                'restricciones_operativas': {'proof_ref': 'webpay-proof-controlled'},
                'evidencia_ref': '  webpay-gate-evidence-normalized  ',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['evidencia_ref'], 'webpay-gate-evidence-normalized')
        gate = GateCobroExterno.objects.get(pk=response.data['id'])
        self.assertEqual(gate.evidencia_ref, 'webpay-gate-evidence-normalized')

    def test_webpay_gate_rejects_sensitive_references(self):
        sensitive_evidence_gate = GateCobroExterno(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='https://transbank.example.test/token/secret',
        )
        with self.assertRaises(ValidationError) as evidence_error:
            sensitive_evidence_gate.full_clean()
        self.assertIn('evidencia_ref', evidence_error.exception.message_dict)

        sensitive_restriction_gate = GateCobroExterno(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.CONDITIONED,
            evidencia_ref='webpay-gate-evidence-controlled',
            restricciones_operativas={'proof_ref': 'https://transbank.example.test/proof?token=secret'},
        )
        with self.assertRaises(ValidationError) as restriction_error:
            sensitive_restriction_gate.full_clean()
        self.assertIn('restricciones_operativas', restriction_error.exception.message_dict)

        sensitive_key_gate = GateCobroExterno(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.CONDITIONED,
            evidencia_ref='webpay-gate-evidence-controlled',
            restricciones_operativas={'api_key': 'webpay-api-key-controlled'},
        )
        with self.assertRaises(ValidationError) as key_error:
            sensitive_key_gate.full_clean()
        self.assertIn('restricciones_operativas', key_error.exception.message_dict)

    def test_webpay_intent_full_clean_rejects_sensitive_provider_payload(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-PAYLOAD-SECRET')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-gate-evidence-controlled',
        )
        intent = IntentoPagoWebPay(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='BUY-PAYLOAD-SECRET',
            session_id='SESSION-PAYLOAD-SECRET',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.PREPARED,
            provider_payload={'token': 'secret-token', 'status_ref': 'webpay-status-v1'},
        )

        with self.assertRaises(ValidationError) as payload_error:
            intent.full_clean()
        self.assertIn('provider_payload', payload_error.exception.message_dict)

    def test_webpay_intent_full_clean_rejects_sensitive_block_reason(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-BLOCK-SECRET')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-gate-evidence-controlled',
        )
        intent = IntentoPagoWebPay(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='BUY-BLOCK-SECRET',
            session_id='SESSION-BLOCK-SECRET',
            estado=EstadoIntentoPagoWebPay.BLOCKED,
            motivo_bloqueo='Bloqueo por https://transbank.example.test/block?token=secret',
        )

        with self.assertRaises(ValidationError) as block_error:
            intent.full_clean()
        self.assertIn('motivo_bloqueo', block_error.exception.message_dict)

    def test_webpay_intent_refs_normalize_before_persisting(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-REF-NORM')
        payment.monto_pagado_clp = payment.monto_calculado_clp
        payment.fecha_pago_webpay = date(2026, 1, 8)
        payment.fecha_deteccion_sistema = date(2026, 1, 8)
        payment.estado_pago = EstadoPago.PAID
        payment.full_clean()
        payment.save()
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-gate-evidence-controlled',
        )
        intent = IntentoPagoWebPay(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='BUY-WP-REF-NORM',
            session_id='SESSION-WP-REF-NORM',
            return_url_ref='  webpay-return-controlled-v1  ',
            estado=EstadoIntentoPagoWebPay.CONFIRMED_MANUAL,
            motivo_bloqueo='  provider-confirmed-controlled  ',
            external_ref='  TBK-REF-NORM-001  ',
            fecha_pago_webpay=date(2026, 1, 8),
            usuario=self.user,
        )

        intent.full_clean()
        self.assertEqual(intent.return_url_ref, 'webpay-return-controlled-v1')
        self.assertEqual(intent.motivo_bloqueo, 'provider-confirmed-controlled')
        self.assertEqual(intent.external_ref, 'TBK-REF-NORM-001')
        intent.save()
        intent.refresh_from_db()

        self.assertEqual(intent.return_url_ref, 'webpay-return-controlled-v1')
        self.assertEqual(intent.motivo_bloqueo, 'provider-confirmed-controlled')
        self.assertEqual(intent.external_ref, 'TBK-REF-NORM-001')

    def test_webpay_apis_redact_inherited_sensitive_references(self):
        self.user.default_role_code = 'AdministradorGlobal'
        self.user.save(update_fields=['default_role_code'])
        payment = self._generate_monthly_payment(codigo='CON-WP-API-REDACT')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='https://transbank.example.test/token/secret',
            restricciones_operativas={
                'api_key': 'controlled-webpay-reference',
                'safe_ref': 'webpay-controlled-ref',
                'headers': {'authorization': 'opaque-inherited-webpay-value'},
            },
        )
        IntentoPagoWebPay.objects.create(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='BUY-LEGACY-SECRET',
            session_id='SESSION-LEGACY',
            return_url_ref='https://front.example.test/webpay?token=secret',
            estado=EstadoIntentoPagoWebPay.CONFIRMED_MANUAL,
            motivo_bloqueo='Bloqueo heredado por https://transbank.example.test/block?token=secret',
            external_ref='https://transbank.example.test/token/secret',
            fecha_pago_webpay='2026-01-06',
            usuario=self.user,
            provider_payload={
                'transaction_status': 'AUTHORIZED',
                'callback': 'https://front.example.test/webpay?token=secret',
                'headers': {'authorization': 'Bearer inherited-webpay-value'},
                'events': [{'result_ref': 'controlled-result-1'}],
            },
        )

        gates_response = self.client.get(reverse('cobranza-webpay-gate-list'))
        intents_response = self.client.get(reverse('cobranza-webpay-intent-list'))
        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(gates_response.status_code, status.HTTP_200_OK)
        self.assertEqual(intents_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(gates_response.data[0]['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intents_response.data[0]['return_url_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intents_response.data[0]['motivo_bloqueo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(intents_response.data[0]['external_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['gates_cobro'][0]['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        gate_restrictions = gates_response.data[0]['restricciones_operativas']
        self.assertEqual(gate_restrictions['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(gate_restrictions['safe_ref'], 'webpay-controlled-ref')
        self.assertEqual(gate_restrictions['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        snapshot_gate_restrictions = snapshot_response.data['gates_cobro'][0]['restricciones_operativas']
        self.assertEqual(snapshot_gate_restrictions['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_gate_restrictions['safe_ref'], 'webpay-controlled-ref')
        self.assertEqual(snapshot_gate_restrictions['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['intentos_webpay'][0]['motivo_bloqueo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['intentos_webpay'][0]['external_ref'], REDACTED_SENSITIVE_REFERENCE)
        payload = intents_response.data[0]['provider_payload']
        self.assertEqual(payload['transaction_status'], 'AUTHORIZED')
        self.assertEqual(payload['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(payload['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(payload['events'][0]['result_ref'], 'controlled-result-1')

        for response in (gates_response, intents_response, snapshot_response):
            body = response.content.decode()
            self.assertNotIn('transbank.example.test', body)
            self.assertNotIn('front.example.test', body)
            self.assertNotIn('controlled-webpay-reference', body)
            self.assertNotIn('token', body)
            self.assertNotIn('secret', body)

    def test_webpay_prepare_open_gate_creates_local_intent_without_closing_payment(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-PREP')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )

        response = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'webpay-return-controlled-v1'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoIntentoPagoWebPay.PREPARED)
        self.assertEqual(response.data['external_ref'], '')
        self.assertTrue(response.data['buy_order'].startswith(f'LM-PM-{payment.pk}-'))
        self.assertTrue(response.data['session_id'].startswith(f'LM-WP-{payment.pk}-'))
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertIsNone(payment.fecha_pago_webpay)
        audit_event = AuditEvent.objects.get(
            event_type=WEBPAY_PREPARE_EVENT_TYPE,
            entity_type='webpay_intento',
            entity_id=str(response.data['id']),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.metadata['estado'], EstadoIntentoPagoWebPay.PREPARED)
        self.assertEqual(audit_event.metadata['return_url_ref'], 'webpay-return-controlled-v1')
        self.assertEqual(audit_event.metadata['provider_key'], 'transbank_webpay')

    def test_webpay_prepare_service_reuses_existing_intent_and_realigns_missing_audit(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-PREP-REALIGN')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        existing = prepare_webpay_intent(
            payment=payment,
            gate=gate,
            return_url_ref='webpay-return-controlled-v1',
            usuario=self.user,
            ip_address='127.0.0.1',
        )
        AuditEvent.objects.filter(
            event_type=WEBPAY_PREPARE_EVENT_TYPE,
            entity_type='webpay_intento',
            entity_id=str(existing.pk),
        ).delete()

        reused = prepare_webpay_intent(
            payment=payment,
            gate=gate,
            return_url_ref='webpay-return-controlled-v1',
            usuario=self.user,
            ip_address='127.0.0.1',
        )

        self.assertEqual(reused.pk, existing.pk)
        self.assertEqual(IntentoPagoWebPay.objects.filter(pago_mensual=payment).count(), 1)
        audit_event = AuditEvent.objects.get(
            event_type=WEBPAY_PREPARE_EVENT_TYPE,
            entity_type='webpay_intento',
            entity_id=str(existing.pk),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.ip_address, '127.0.0.1')
        self.assertEqual(audit_event.metadata['estado'], EstadoIntentoPagoWebPay.PREPARED)

    def test_webpay_prepare_service_blocks_existing_prepared_intent_when_gate_closes(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-PREP-GATE-CLOSED')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        existing = prepare_webpay_intent(
            payment=payment,
            gate=gate,
            return_url_ref='webpay-return-controlled-v1',
            usuario=self.user,
            ip_address='127.0.0.1',
        )
        gate.estado_gate = EstadoGateCobroExterno.CONDITIONED
        gate.save(update_fields=['estado_gate', 'updated_at'])

        blocked = prepare_webpay_intent(
            payment=payment,
            gate=gate,
            return_url_ref='webpay-return-controlled-v1',
            usuario=self.user,
            ip_address='127.0.0.1',
        )

        self.assertEqual(blocked.pk, existing.pk)
        self.assertEqual(blocked.estado, EstadoIntentoPagoWebPay.BLOCKED)
        self.assertIn('gate WebPay no esta abierto', blocked.motivo_bloqueo)
        self.assertEqual(IntentoPagoWebPay.objects.filter(pago_mensual=payment).count(), 1)
        self.assertTrue(
            ManualResolution.objects.filter(
                category='cobranza.webpay.bloqueado',
                scope_type='cobranza.webpay',
                scope_reference=str(existing.pk),
            ).exists()
        )
        audit_states = [
            event.metadata.get('estado')
            for event in AuditEvent.objects.filter(
                event_type=WEBPAY_PREPARE_EVENT_TYPE,
                entity_type='webpay_intento',
                entity_id=str(existing.pk),
            )
        ]
        self.assertIn(EstadoIntentoPagoWebPay.BLOCKED, audit_states)

    def test_webpay_prepare_service_replaces_stale_prepared_intent_with_invalid_return_ref(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-PREP-STALE-RETURN')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        existing = prepare_webpay_intent(
            payment=payment,
            gate=gate,
            return_url_ref='webpay-return-controlled-v1',
            usuario=self.user,
            ip_address='127.0.0.1',
        )
        IntentoPagoWebPay.objects.filter(pk=existing.pk).update(
            return_url_ref='https://front.example.test/webpay?token=secret'
        )

        replacement = prepare_webpay_intent(
            payment=payment,
            gate=gate,
            return_url_ref='webpay-return-controlled-v2',
            usuario=self.user,
            ip_address='127.0.0.1',
        )

        existing.refresh_from_db()
        self.assertNotEqual(replacement.pk, existing.pk)
        self.assertEqual(existing.estado, EstadoIntentoPagoWebPay.BLOCKED)
        self.assertEqual(existing.return_url_ref, '')
        self.assertIn('validacion vigente', existing.motivo_bloqueo)
        self.assertEqual(replacement.estado, EstadoIntentoPagoWebPay.PREPARED)
        self.assertEqual(replacement.return_url_ref, 'webpay-return-controlled-v2')
        self.assertEqual(IntentoPagoWebPay.objects.filter(pago_mensual=payment).count(), 2)

    def test_webpay_prepare_service_rolls_back_when_audit_creation_fails(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-PREP-AUDITFAIL')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )

        with patch('cobranza.services.create_audit_event', side_effect=RuntimeError('webpay audit unavailable')):
            with self.assertRaises(RuntimeError):
                prepare_webpay_intent(
                    payment=payment,
                    gate=gate,
                    return_url_ref='webpay-return-controlled-v1',
                    usuario=self.user,
                    ip_address='127.0.0.1',
                )

        self.assertFalse(IntentoPagoWebPay.objects.filter(pago_mensual=payment).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type=WEBPAY_PREPARE_EVENT_TYPE).exists())

    def test_webpay_prepare_rejects_sensitive_return_reference_before_persisting(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-RETURN-SECRET')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )

        response = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'https://front.example.test/webpay?token=secret'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('return_url_ref no sensible', response.data['detail'])
        self.assertEqual(IntentoPagoWebPay.objects.count(), 0)
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)

    def test_webpay_manual_confirmation_requires_external_ref(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-EXTREF')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'webpay-return-controlled-v1'},
            format='json',
        )
        self.assertEqual(intent.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-webpay-intent-confirm-manual', args=[intent.data['id']]),
            {'external_ref': '', 'fecha_pago_webpay': '2026-01-06'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)

    def test_webpay_manual_confirmation_rejects_sensitive_external_ref(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-SECRET')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'webpay-return-controlled-v1'},
            format='json',
        )
        self.assertEqual(intent.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-webpay-intent-confirm-manual', args=[intent.data['id']]),
            {
                'external_ref': 'https://transbank.example.test/token/secret',
                'fecha_pago_webpay': '2026-01-06',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no sensible', response.data['detail'])
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        stored_intent = IntentoPagoWebPay.objects.get(pk=intent.data['id'])
        self.assertEqual(stored_intent.estado, EstadoIntentoPagoWebPay.PREPARED)
        self.assertEqual(stored_intent.external_ref, '')

    def test_webpay_manual_confirmation_marks_payment_paid_with_webpay_date(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-CONF')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = self.client.post(
            reverse('cobranza-webpay-prepare', args=[payment.pk]),
            {'gate_cobro': gate.pk, 'return_url_ref': 'webpay-return-controlled-v1'},
            format='json',
        )
        self.assertEqual(intent.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-webpay-intent-confirm-manual', args=[intent.data['id']]),
            {'external_ref': 'TBK-TEST-123', 'fecha_pago_webpay': '2026-01-08'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], EstadoIntentoPagoWebPay.CONFIRMED_MANUAL)
        self.assertEqual(response.data['external_ref'], 'TBK-TEST-123')
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.PAID)
        self.assertEqual(str(payment.monto_pagado_clp), str(payment.monto_calculado_clp))
        self.assertEqual(str(payment.fecha_pago_webpay), '2026-01-08')
        self.assertIsNone(payment.fecha_deposito_banco)
        self.assertEqual(payment.dias_mora, 3)
        audit_event = AuditEvent.objects.get(
            event_type=WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
            entity_type='webpay_intento',
            entity_id=str(intent.data['id']),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.metadata['external_ref'], 'TBK-TEST-123')
        self.assertEqual(audit_event.metadata['pago_mensual_id'], payment.pk)
        self.assertEqual(audit_event.metadata['fecha_pago_webpay'], '2026-01-08')

    def test_webpay_manual_confirmation_service_creates_audit_event(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-SERVICE')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = IntentoPagoWebPay.objects.create(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='LM-PM-WP-SERVICE',
            session_id='LM-WP-SERVICE',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.PREPARED,
            usuario=self.user,
        )

        confirmed, paid_payment = confirm_webpay_intent_manually(
            intent=intent,
            external_ref='TBK-SERVICE-001',
            fecha_pago_webpay=date(2026, 1, 8),
            actor_user=self.user,
            ip_address='127.0.0.1',
        )

        self.assertEqual(confirmed.estado, EstadoIntentoPagoWebPay.CONFIRMED_MANUAL)
        self.assertEqual(paid_payment.estado_pago, EstadoPago.PAID)
        audit_event = AuditEvent.objects.get(
            event_type=WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
            entity_type='webpay_intento',
            entity_id=str(intent.pk),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.ip_address, '127.0.0.1')
        self.assertEqual(audit_event.metadata['external_ref'], 'TBK-SERVICE-001')
        self.assertEqual(audit_event.metadata['pago_mensual_id'], payment.pk)
        self.assertEqual(audit_event.metadata['fecha_pago_webpay'], '2026-01-08')

    def test_webpay_manual_confirmation_rolls_back_when_audit_creation_fails(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-CONF-AUDIT-FAIL')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = IntentoPagoWebPay.objects.create(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='LM-PM-WP-CONF-AUDIT-FAIL',
            session_id='LM-WP-CONF-AUDIT-FAIL',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.PREPARED,
            usuario=self.user,
        )

        with patch('cobranza.services.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'audit unavailable'):
                confirm_webpay_intent_manually(
                    intent=intent,
                    external_ref='TBK-AUDIT-FAIL-001',
                    fecha_pago_webpay=date(2026, 1, 8),
                    actor_user=self.user,
                    ip_address='127.0.0.1',
                )

        intent.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(intent.estado, EstadoIntentoPagoWebPay.PREPARED)
        self.assertEqual(intent.external_ref, '')
        self.assertIsNone(intent.fecha_pago_webpay)
        self.assertIsNone(intent.confirmado_at)
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertEqual(payment.monto_pagado_clp, Decimal('0.00'))
        self.assertIsNone(payment.fecha_pago_webpay)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
                entity_type='webpay_intento',
                entity_id=str(intent.pk),
            ).exists()
        )

    def test_webpay_manual_confirmation_service_requires_actor(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-ACTOR')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = IntentoPagoWebPay.objects.create(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='LM-PM-WP-ACTOR',
            session_id='LM-WP-ACTOR',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.PREPARED,
            usuario=self.user,
        )

        with self.assertRaisesRegex(ValueError, 'actor trazable'):
            confirm_webpay_intent_manually(
                intent=intent,
                external_ref='TBK-ACTOR-001',
                fecha_pago_webpay=date(2026, 1, 8),
            )

        intent.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(intent.estado, EstadoIntentoPagoWebPay.PREPARED)
        self.assertEqual(intent.external_ref, '')
        self.assertEqual(payment.estado_pago, EstadoPago.PENDING)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
                entity_type='webpay_intento',
                entity_id=str(intent.pk),
            ).exists()
        )

    def test_webpay_confirmed_intent_requires_payment_alignment(self):
        payment = self._generate_monthly_payment(codigo='CON-WP-ALIGN')
        gate = GateCobroExterno.objects.create(
            provider_key='transbank_webpay',
            estado_gate=EstadoGateCobroExterno.OPEN,
            evidencia_ref='webpay-sandbox-evidence-ok',
        )
        intent = IntentoPagoWebPay(
            pago_mensual=payment,
            gate_cobro=gate,
            provider_key='transbank_webpay',
            monto_clp_snapshot=payment.monto_calculado_clp,
            buy_order='LM-PM-WP-ALIGN',
            session_id='LM-WP-ALIGN',
            return_url_ref='webpay-return-controlled-v1',
            estado=EstadoIntentoPagoWebPay.CONFIRMED_MANUAL,
            external_ref='TBK-ALIGN-001',
            fecha_pago_webpay=date(2026, 1, 8),
        )

        with self.assertRaises(ValidationError) as not_paid_error:
            intent.full_clean()
        self.assertIn('pago_mensual', not_paid_error.exception.message_dict)

        payment.estado_pago = EstadoPago.PAID
        payment.monto_pagado_clp = payment.monto_calculado_clp
        payment.fecha_pago_webpay = date(2026, 1, 9)
        payment.fecha_deteccion_sistema = date(2026, 1, 9)
        payment.save()

        with self.assertRaises(ValidationError) as date_error:
            intent.full_clean()
        self.assertIn('fecha_pago_webpay', date_error.exception.message_dict)

    def test_payment_rejects_invalid_state_transition(self):
        contrato = self._create_active_contract(codigo='CON-STATE', monto_base='100000.00', code='111')
        generate = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generate.status_code, status.HTTP_201_CREATED)

        invalid = self.client.patch(
            reverse('cobranza-pago-detail', args=[generate.data['id']]),
            {'estado_pago': EstadoPago.PAID_VIA_REPAYMENT},
            format='json',
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guarantee_movements_update_aggregates_and_state(self):
        contrato = self._create_active_contract(codigo='CON-GAR', monto_base='100000.00', code='111')
        garantia = self.client.post(
            reverse('cobranza-garantia-list'),
            {'contrato': contrato.id, 'monto_pactado': '100000.00'},
            format='json',
        )
        self.assertEqual(garantia.status_code, status.HTTP_201_CREATED)

        deposit = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.data['id']]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '100000.00', 'fecha': '2026-01-01'},
            format='json',
        )
        self.assertEqual(deposit.status_code, status.HTTP_201_CREATED)

        partial_return = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.data['id']]),
            {
                'tipo_movimiento': 'devolucion_parcial',
                'monto_clp': '30000.00',
                'fecha': '2026-12-31',
                'movimiento_origen': deposit.data['id'],
                'justificacion': 'Devolucion parcial',
            },
            format='json',
        )
        self.assertEqual(partial_return.status_code, status.HTTP_201_CREATED)

        guarantee_detail = self.client.get(reverse('cobranza-garantia-detail', args=[garantia.data['id']]))
        self.assertEqual(guarantee_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(guarantee_detail.data['monto_recibido'], '100000.00')
        self.assertEqual(guarantee_detail.data['monto_devuelto'], '30000.00')
        self.assertEqual(guarantee_detail.data['estado_garantia'], EstadoGarantia.PARTIALLY_RETURNED)

        total_retention = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.data['id']]),
            {
                'tipo_movimiento': 'retencion_total',
                'monto_clp': '70000.00',
                'fecha': '2027-01-10',
                'movimiento_origen': deposit.data['id'],
                'justificacion': 'Aplicacion final',
            },
            format='json',
        )
        self.assertEqual(total_retention.status_code, status.HTTP_201_CREATED)

        final_detail = self.client.get(reverse('cobranza-garantia-detail', args=[garantia.data['id']]))
        self.assertEqual(final_detail.data['estado_garantia'], EstadoGarantia.APPLIED)
        self.assertEqual(final_detail.data['monto_aplicado'], '70000.00')
        self.assertEqual(final_detail.data['fecha_cierre'], '2027-01-10')
        state_event_metadata = [
            event.metadata
            for event in AuditEvent.objects.filter(
                event_type='cobranza.garantia_contractual.state_changed',
                entity_type='garantia_contractual',
                entity_id=str(garantia.data['id']),
            ).order_by('id')
        ]
        self.assertIn(
            {
                'campo_estado': 'estado_garantia',
                'estado_anterior': EstadoGarantia.PARTIALLY_RETURNED,
                'estado_nuevo': EstadoGarantia.APPLIED,
            },
            state_event_metadata,
        )

    def test_guarantee_movement_rolls_back_when_view_audit_fails(self):
        contrato = self._create_active_contract(codigo='CON-GAR-AUDIT', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.post(
                    reverse('cobranza-garantia-movimiento', args=[garantia.id]),
                    {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-01'},
                    format='json',
                )

        garantia.refresh_from_db()
        self.assertEqual(garantia.monto_recibido, Decimal('0.00'))
        self.assertEqual(garantia.estado_garantia, EstadoGarantia.PENDING)
        self.assertFalse(HistorialGarantia.objects.filter(garantia_contractual=garantia).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='cobranza.historial_garantia.created').exists())

    def test_guarantee_deposit_above_pactado_requires_resolution(self):
        contrato = self._create_active_contract(codigo='CON-GAR-FAIL', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '60000.00', 'fecha': '2026-01-01'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resolucion_exceso_garantia_ref', response.data)

    def test_guarantee_deposit_above_pactado_accepts_controlled_resolution(self):
        contrato = self._create_active_contract(codigo='CON-GAR-EXCESS', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'deposito',
                'monto_clp': '60000.00',
                'fecha': '2026-01-01',
                'resolucion_exceso_garantia': 'devolver',
                'resolucion_exceso_garantia_ref': 'manual-resolution-guarantee-excess-2026-01',
                'resolucion_exceso_garantia_motivo': 'Exceso recibido identificado y marcado para devolucion controlada.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        detail = self.client.get(reverse('cobranza-garantia-detail', args=[garantia.id]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['monto_recibido'], '60000.00')
        self.assertEqual(detail.data['exceso_garantia_clp'], '10000.00')
        self.assertEqual(detail.data['resolucion_exceso_garantia'], 'devolver')
        self.assertTrue(detail.data['tiene_resolucion_exceso_garantia'])

    def test_guarantee_excess_resolution_rejects_sensitive_reference(self):
        contrato = self._create_active_contract(codigo='CON-GAR-EXCESS-SENS', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'deposito',
                'monto_clp': '60000.00',
                'fecha': '2026-01-01',
                'resolucion_exceso_garantia': 'regularizar',
                'resolucion_exceso_garantia_ref': 'https://example.test/approval?token=secret',
                'resolucion_exceso_garantia_motivo': 'Regularizacion controlada.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resolucion_exceso_garantia_ref', response.data)

    def test_guarantee_excess_resolution_apis_and_snapshot_redact_sensitive_motive(self):
        contrato = self._create_active_contract(codigo='CON-GAR-EXCESS-MOT', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(
            contrato=contrato,
            monto_pactado=Decimal('50000.00'),
            monto_recibido=Decimal('60000.00'),
            fecha_recepcion=date(2026, 1, 1),
            estado_garantia=EstadoGarantia.HELD,
            resolucion_exceso_garantia='bloquear',
            resolucion_exceso_garantia_ref='manual-resolution-guarantee-excess-2026-01',
            resolucion_exceso_garantia_motivo=(
                'Exceso heredado con detalle en https://example.test/approval?token=secret'
            ),
        )

        list_response = self.client.get(reverse('cobranza-garantia-list'))
        detail_response = self.client.get(reverse('cobranza-garantia-detail', args=[garantia.id]))
        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list_response.data[0]['resolucion_exceso_garantia_motivo'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            detail_response.data['resolucion_exceso_garantia_motivo'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            snapshot_response.data['garantias'][0]['resolucion_exceso_garantia_motivo'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_guarantee_movement_rejects_sensitive_justification(self):
        contrato = self._create_active_contract(codigo='CON-GAR-JUST-SENS', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'deposito',
                'monto_clp': '50000.00',
                'fecha': '2026-01-01',
                'justificacion': 'Deposito validado en https://example.test/receipt?token=secret',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('justificacion', response.data)

    def test_guarantee_history_apis_and_snapshot_redact_sensitive_justification(self):
        contrato = self._create_active_contract(codigo='CON-GAR-JUST-RED', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(
            contrato=contrato,
            monto_pactado='50000.00',
            monto_recibido='50000.00',
            fecha_recepcion=date(2026, 1, 1),
            estado_garantia=EstadoGarantia.HELD,
        )
        movement = HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento='deposito',
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 1),
            justificacion='Deposito heredado en https://example.test/receipt?token=secret',
        )

        list_response = self.client.get(reverse('cobranza-historial-list'))
        detail_response = self.client.get(reverse('cobranza-historial-detail', args=[movement.id]))
        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['justificacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['justificacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            snapshot_response.data['historial_garantias'][0]['justificacion'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_partial_guarantee_exposes_incomplete_until_formal_acceptance(self):
        contrato = self._create_active_contract(codigo='CON-GAR-PARTIAL', monto_base='100000.00', code='111')
        garantia = self.client.post(
            reverse('cobranza-garantia-list'),
            {'contrato': contrato.id, 'monto_pactado': '100000.00'},
            format='json',
        )
        self.assertEqual(garantia.status_code, status.HTTP_201_CREATED)

        deposit = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.data['id']]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-01'},
            format='json',
        )
        self.assertEqual(deposit.status_code, status.HTTP_201_CREATED)

        incomplete = self.client.get(reverse('cobranza-garantia-detail', args=[garantia.data['id']]))
        self.assertEqual(incomplete.status_code, status.HTTP_200_OK)
        self.assertEqual(incomplete.data['brecha_garantia_clp'], '50000.00')
        self.assertTrue(incomplete.data['garantia_incompleta'])
        self.assertFalse(incomplete.data['garantia_parcial_aceptada'])

        accepted = self.client.patch(
            reverse('cobranza-garantia-detail', args=[garantia.data['id']]),
            {'aceptacion_parcial_ref': 'partial-guarantee-acceptance-2026-01'},
            format='json',
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertFalse(accepted.data['garantia_incompleta'])
        self.assertTrue(accepted.data['garantia_parcial_aceptada'])

    def test_partial_guarantee_acceptance_rejects_sensitive_reference(self):
        contrato = self._create_active_contract(codigo='CON-GAR-PARTIAL-SENS', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(
            contrato=contrato,
            monto_pactado='100000.00',
            monto_recibido='50000.00',
            fecha_recepcion=date(2026, 1, 1),
            estado_garantia=EstadoGarantia.HELD,
        )

        response = self.client.patch(
            reverse('cobranza-garantia-detail', args=[garantia.id]),
            {'aceptacion_parcial_ref': 'https://example.test/approval?token=secret'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('aceptacion_parcial_ref', response.data)

    def test_guarantee_full_clean_rejects_inconsistent_state_and_amounts(self):
        contrato = self._create_active_contract(codigo='CON-GAR-STATE', monto_base='100000.00', code='111')
        garantia = GarantiaContractual(
            contrato=contrato,
            monto_pactado=Decimal('100000.00'),
            monto_recibido=Decimal('50000.00'),
            estado_garantia=EstadoGarantia.PENDING,
        )

        with self.assertRaises(ValidationError):
            garantia.full_clean()

    def test_guarantee_full_clean_rejects_closure_before_reception(self):
        contrato = self._create_active_contract(codigo='CON-GAR-CLOSE-DATE', monto_base='100000.00', code='111')
        garantia = GarantiaContractual(
            contrato=contrato,
            monto_pactado=Decimal('100000.00'),
            monto_recibido=Decimal('50000.00'),
            monto_devuelto=Decimal('50000.00'),
            estado_garantia=EstadoGarantia.RETURNED,
            fecha_recepcion=date(2026, 1, 5),
            fecha_cierre=date(2026, 1, 4),
        )

        with self.assertRaises(ValidationError) as error:
            garantia.full_clean()
        self.assertIn('fecha_cierre', error.exception.message_dict)

    def test_guarantee_movement_rejects_origin_from_different_guarantee(self):
        contrato_a = self._create_active_contract(codigo='CON-GAR-A', monto_base='100000.00', code='111')
        contrato_b = self._create_active_contract(codigo='CON-GAR-B', monto_base='120000.00', code='222')
        garantia_a = GarantiaContractual.objects.create(contrato=contrato_a, monto_pactado='50000.00')
        garantia_b = GarantiaContractual.objects.create(contrato=contrato_b, monto_pactado='80000.00')

        deposito_a = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia_a.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-01'},
            format='json',
        )
        self.assertEqual(deposito_a.status_code, status.HTTP_201_CREATED)

        deposito_b = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia_b.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '80000.00', 'fecha': '2026-01-02'},
            format='json',
        )
        self.assertEqual(deposito_b.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia_b.id]),
            {
                'tipo_movimiento': 'devolucion_parcial',
                'monto_clp': '10000.00',
                'fecha': '2026-01-31',
                'movimiento_origen': deposito_a.data['id'],
                'justificacion': 'Origen cruzado invalido',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('movimiento_origen', response.data)
        self.assertEqual(garantia_b.historial_movimientos.count(), 1)

    def test_guarantee_movement_rejects_derived_date_before_origin(self):
        contrato = self._create_active_contract(codigo='CON-GAR-ORIGIN-DATE', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        deposito = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-10'},
            format='json',
        )
        self.assertEqual(deposito.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'devolucion_parcial',
                'monto_clp': '10000.00',
                'fecha': '2026-01-09',
                'movimiento_origen': deposito.data['id'],
                'justificacion': 'Fecha derivada invalida',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('anterior', response.data['detail'])
        self.assertEqual(garantia.historial_movimientos.count(), 1)

    def test_guarantee_movement_rejects_derived_without_origin(self):
        contrato = self._create_active_contract(codigo='CON-GAR-NO-ORIGIN', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        deposit = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-10'},
            format='json',
        )
        self.assertEqual(deposit.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'devolucion_parcial',
                'monto_clp': '10000.00',
                'fecha': '2026-01-31',
                'justificacion': 'Sin deposito trazado',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('movimiento_origen', response.data)
        self.assertEqual(garantia.historial_movimientos.count(), 1)

    def test_guarantee_movement_rejects_non_deposit_origin(self):
        contrato = self._create_active_contract(codigo='CON-GAR-NON-DEPOSIT', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        deposit = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-10'},
            format='json',
        )
        self.assertEqual(deposit.status_code, status.HTTP_201_CREATED)
        partial_return = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'devolucion_parcial',
                'monto_clp': '10000.00',
                'fecha': '2026-01-31',
                'movimiento_origen': deposit.data['id'],
                'justificacion': 'Devolucion parcial trazada',
            },
            format='json',
        )
        self.assertEqual(partial_return.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'retencion_parcial',
                'monto_clp': '10000.00',
                'fecha': '2026-02-01',
                'movimiento_origen': partial_return.data['id'],
                'justificacion': 'Origen no deposito',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('movimiento_origen', response.data)
        self.assertEqual(garantia.historial_movimientos.count(), 2)

    def test_guarantee_movement_rejects_derived_total_above_origin_deposit(self):
        contrato = self._create_active_contract(codigo='CON-GAR-ORIGIN-AMOUNT', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='100000.00')

        deposit = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-10'},
            format='json',
        )
        self.assertEqual(deposit.status_code, status.HTTP_201_CREATED)
        second_deposit = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '50000.00', 'fecha': '2026-01-11'},
            format='json',
        )
        self.assertEqual(second_deposit.status_code, status.HTTP_201_CREATED)
        partial_return = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'devolucion_parcial',
                'monto_clp': '40000.00',
                'fecha': '2026-01-31',
                'movimiento_origen': deposit.data['id'],
                'justificacion': 'Devolucion parcial trazada',
            },
            format='json',
        )
        self.assertEqual(partial_return.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {
                'tipo_movimiento': 'retencion_parcial',
                'monto_clp': '20000.00',
                'fecha': '2026-02-01',
                'movimiento_origen': deposit.data['id'],
                'justificacion': 'Excede deposito origen',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('monto_clp', response.data)
        self.assertEqual(garantia.historial_movimientos.count(), 3)

    def test_adjustment_rejects_invalid_month_range(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE', monto_base='100000.00', code='111')
        response = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'descuento',
                'monto': '-1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-02-01',
                'mes_fin': '2026-01-01',
                'justificacion': 'Invalido',
                'activo': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_adjustment_rejects_discount_below_operational_minimum(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-MIN', monto_base='1000.00', code='111')

        response = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'descuento_controlado',
                'monto': '-1.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-01-01',
                'mes_fin': '2026-01-01',
                'justificacion': 'Descuento operativo controlado',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('monto', response.data)
        self.assertFalse(AjusteContrato.objects.filter(contrato=contrato).exists())

    def test_adjustment_rejects_blank_justification_after_trim(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-JUST-BLANK', monto_base='100000.00', code='111')

        response = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'cargo_controlado',
                'monto': '1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-01-01',
                'mes_fin': '2026-01-01',
                'justificacion': '   ',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('justificacion', response.data)
        self.assertFalse(AjusteContrato.objects.filter(contrato=contrato).exists())

    def test_adjustment_rejects_non_month_start_range(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-MES', monto_base='100000.00', code='111')

        invalid_start = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'cargo_controlado',
                'monto': '1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-01-02',
                'mes_fin': '2026-02-01',
                'justificacion': 'Mes inicial no normalizado',
                'activo': True,
            },
            format='json',
        )
        invalid_end = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'cargo_controlado',
                'monto': '1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-01-01',
                'mes_fin': '2026-02-02',
                'justificacion': 'Mes final no normalizado',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(invalid_start.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mes_inicio', invalid_start.data)
        self.assertEqual(invalid_end.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mes_fin', invalid_end.data)
        self.assertFalse(AjusteContrato.objects.filter(contrato=contrato).exists())

    def test_adjustment_rejects_sensitive_justification(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-SENS', monto_base='100000.00', code='111')

        response = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'cargo_controlado',
                'monto': '1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-01-01',
                'mes_fin': '2026-01-01',
                'justificacion': 'Cargo respaldado en https://billing.example.test/adjustment?token=secret',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('justificacion', response.data)
        self.assertFalse(AjusteContrato.objects.filter(contrato=contrato).exists())

    def test_adjustment_create_rolls_back_when_view_audit_fails(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-AUDIT', monto_base='100000.00', code='111')

        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.post(
                    reverse('cobranza-ajuste-list'),
                    {
                        'contrato': contrato.id,
                        'tipo_ajuste': 'cargo_controlado',
                        'monto': '1000.00',
                        'moneda': 'CLP',
                        'mes_inicio': '2026-01-01',
                        'mes_fin': '2026-01-01',
                        'justificacion': 'Cargo operativo controlado',
                        'activo': True,
                    },
                    format='json',
                )

        self.assertFalse(AjusteContrato.objects.filter(contrato=contrato).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='cobranza.ajuste_contrato.created').exists())

    def test_adjustment_apis_and_snapshot_redact_inherited_sensitive_justification(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-RED', monto_base='100000.00', code='111')
        adjustment = AjusteContrato.objects.create(
            contrato=contrato,
            tipo_ajuste='cargo_controlado',
            monto=Decimal('1000.00'),
            moneda='CLP',
            mes_inicio=date(2026, 1, 1),
            mes_fin=date(2026, 1, 1),
            justificacion='Cargo operativo controlado',
        )
        AjusteContrato.objects.filter(pk=adjustment.pk).update(
            justificacion='Cargo respaldado en https://billing.example.test/adjustment?token=secret'
        )

        list_response = self.client.get(reverse('cobranza-ajuste-list'))
        detail_response = self.client.get(reverse('cobranza-ajuste-detail', args=[adjustment.pk]))
        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['justificacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['justificacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['ajustes'][0]['justificacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('billing.example.test', str(list_response.data))
        self.assertNotIn('billing.example.test', str(detail_response.data))
        self.assertNotIn('billing.example.test', str(snapshot_response.data))

    def test_adjustment_rejects_month_range_outside_contract_validity(self):
        contrato = self._create_active_contract(codigo='CON-AJUSTE-VIG', monto_base='100000.00', code='111')

        starts_before = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'cargo_controlado',
                'monto': '1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2025-12-01',
                'mes_fin': '2026-01-01',
                'justificacion': 'Fuera de vigencia',
                'activo': True,
            },
            format='json',
        )
        ends_after = self.client.post(
            reverse('cobranza-ajuste-list'),
            {
                'contrato': contrato.id,
                'tipo_ajuste': 'cargo_controlado',
                'monto': '1000.00',
                'moneda': 'CLP',
                'mes_inicio': '2026-12-01',
                'mes_fin': '2027-01-01',
                'justificacion': 'Fuera de vigencia',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(starts_before.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mes_inicio', starts_before.data)
        self.assertEqual(ends_after.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mes_fin', ends_after.data)
        self.assertFalse(AjusteContrato.objects.filter(contrato=contrato).exists())

    def test_create_residual_code_generates_canonical_reference(self):
        contrato = self._create_active_contract(codigo='CON-RES', monto_base='100000.00', code='111')

        response = self.client.post(
            reverse('cobranza-residual-list'),
            {
                'arrendatario': contrato.arrendatario_id,
                'contrato_origen': contrato.id,
                'saldo_actual': '25000.00',
                'estado': 'activa',
                'fecha_activacion': '2027-01-10',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertRegex(response.data['referencia_visible'], r'^CCR-[A-Z2-9]{6}$')

    def test_residual_code_full_clean_rejects_non_canonical_reference(self):
        contrato = self._create_active_contract(codigo='CON-RES-FMT', monto_base='100000.00', code='111')
        residual = CodigoCobroResidual(
            referencia_visible='BAD-00001',
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            saldo_actual='25000.00',
            estado='activa',
            fecha_activacion='2027-01-10',
        )

        with self.assertRaises(ValidationError) as error:
            residual.full_clean()
        self.assertIn('referencia_visible', error.exception.message_dict)

    def test_residual_code_full_clean_rejects_activation_during_contract(self):
        contrato = self._create_active_contract(codigo='CON-RES-DATE', monto_base='100000.00', code='111')
        residual = CodigoCobroResidual(
            referencia_visible='CCR-ABC234',
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            saldo_actual='25000.00',
            estado='activa',
            fecha_activacion='2026-12-31',
        )

        with self.assertRaises(ValidationError) as error:
            residual.full_clean()
        self.assertIn('fecha_activacion', error.exception.message_dict)

    def test_create_residual_code_rejects_activation_during_contract(self):
        contrato = self._create_active_contract(codigo='CON-RES-API', monto_base='100000.00', code='111')

        response = self.client.post(
            reverse('cobranza-residual-list'),
            {
                'arrendatario': contrato.arrendatario_id,
                'contrato_origen': contrato.id,
                'saldo_actual': '25000.00',
                'estado': 'activa',
                'fecha_activacion': '2026-12-31',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_activacion', response.data)

    def test_residual_code_full_clean_rejects_closed_state_with_balance(self):
        contrato = self._create_active_contract(codigo='CON-RES-BAL', monto_base='100000.00', code='111')

        for estado in ('pagada', 'cancelada'):
            residual = CodigoCobroResidual(
                referencia_visible='CCR-ABC234' if estado == 'pagada' else 'CCR-DEF234',
                arrendatario=contrato.arrendatario,
                contrato_origen=contrato,
                saldo_actual='25000.00',
                estado=estado,
                fecha_activacion='2027-01-10',
            )
            with self.subTest(estado=estado):
                with self.assertRaises(ValidationError) as error:
                    residual.full_clean()
                self.assertIn('saldo_actual', error.exception.message_dict)

    def test_update_residual_code_rejects_generic_mutation_after_creation(self):
        contrato = self._create_active_contract(codigo='CON-RES-UPD', monto_base='100000.00', code='111')
        residual = CodigoCobroResidual.objects.create(
            referencia_visible='CCR-ABC234',
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            saldo_actual='25000.00',
            estado='activa',
            fecha_activacion='2027-01-10',
        )

        response = self.client.patch(
            reverse('cobranza-residual-detail', args=[residual.id]),
            {'estado': 'pagada', 'saldo_actual': '0.00'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('saldo_actual', response.data)
        residual.refresh_from_db()
        self.assertEqual(residual.estado, EstadoCobroResidual.ACTIVE)
        self.assertEqual(residual.saldo_actual, Decimal('25000.00'))

    def test_repactacion_rejects_contract_arrendatario_mismatch(self):
        contrato = self._create_active_contract(codigo='CON-REP', monto_base='100000.00', code='111')
        other_tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Otro Arrendatario',
            rut='55555555-5',
            email='other@example.com',
            telefono='888',
            domicilio_notificaciones='Otra',
            estado_contacto='activo',
        )

        response = self.client.post(
            reverse('cobranza-repactacion-list'),
            {
                'arrendatario': other_tenant.id,
                'contrato_origen': contrato.id,
                'deuda_total_original': '50000.00',
                'cantidad_cuotas': 5,
                'monto_cuota': '10000.00',
                'saldo_pendiente': '50000.00',
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_repactacion_full_clean_rejects_inconsistent_state_balance(self):
        contrato = self._create_active_contract(codigo='CON-REP-STATE', monto_base='100000.00', code='111')
        active_without_balance = RepactacionDeuda(
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='0.00',
            estado='activa',
        )
        completed_with_balance = RepactacionDeuda(
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='10000.00',
            estado='cumplida',
        )

        with self.assertRaises(ValidationError) as active_error:
            active_without_balance.full_clean()
        with self.assertRaises(ValidationError) as completed_error:
            completed_with_balance.full_clean()

        self.assertIn('saldo_pendiente', active_error.exception.message_dict)
        self.assertIn('saldo_pendiente', completed_error.exception.message_dict)

    def test_partial_repayment_requires_formal_exception(self):
        contrato = self._create_active_contract(codigo='CON-REP-PARTIAL', monto_base='100000.00', code='111')

        response = self.client.post(
            reverse('cobranza-repactacion-list'),
            {
                'arrendatario': contrato.arrendatario_id,
                'contrato_origen': contrato.id,
                'deuda_total_original': '50000.00',
                'cantidad_cuotas': 4,
                'monto_cuota': '10000.00',
                'saldo_pendiente': '40000.00',
                'estado': 'activa',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('excepcion_parcial_ref', response.data)
        self.assertIn('excepcion_parcial_motivo', response.data)

    def test_partial_repayment_apis_and_snapshot_redact_sensitive_exception_motive(self):
        contrato = self._create_active_contract(codigo='CON-REP-PARTIAL-RED', monto_base='100000.00', code='111')
        repayment = RepactacionDeuda.objects.create(
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            deuda_total_original=Decimal('50000.00'),
            cantidad_cuotas=4,
            monto_cuota=Decimal('10000.00'),
            saldo_pendiente=Decimal('40000.00'),
            estado='activa',
            excepcion_parcial_ref='partial-repayment-exception-2026-01',
            excepcion_parcial_motivo='Excepcion parcial heredada en https://example.test/approval?token=secret',
        )
        residual = CodigoCobroResidual.objects.create(
            referencia_visible='CCR-ABC123',
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            saldo_actual=Decimal('25000.00'),
            estado=EstadoCobroResidual.ACTIVE,
            fecha_activacion=date(2027, 1, 1),
        )

        list_response = self.client.get(reverse('cobranza-repactacion-list'))
        detail_response = self.client.get(reverse('cobranza-repactacion-detail', args=[repayment.id]))
        snapshot_response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['excepcion_parcial_motivo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['excepcion_parcial_motivo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            snapshot_response.data['repactaciones'][0]['excepcion_parcial_motivo'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(snapshot_response.data['codigos_residuales'][0]['id'], residual.id)
        self.assertEqual(snapshot_response.data['codigos_residuales'][0]['referencia_visible'], 'CCR-ABC123')
        self.assertEqual(snapshot_response.data['codigos_residuales'][0]['saldo_actual'], Decimal('25000.00'))
        self.assertEqual(snapshot_response.data['codigos_residuales'][0]['estado'], EstadoCobroResidual.ACTIVE)
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_partial_repayment_records_exception_audit_event(self):
        contrato = self._create_active_contract(codigo='CON-REP-PARTIAL-OK', monto_base='100000.00', code='111')

        response = self.client.post(
            reverse('cobranza-repactacion-list'),
            {
                'arrendatario': contrato.arrendatario_id,
                'contrato_origen': contrato.id,
                'deuda_total_original': '50000.00',
                'cantidad_cuotas': 4,
                'monto_cuota': '10000.00',
                'saldo_pendiente': '40000.00',
                'estado': 'activa',
                'excepcion_parcial_ref': '  partial-repayment-exception-2026-01  ',
                'excepcion_parcial_motivo': '  Excepcion formal autorizada por acuerdo operativo controlado.  ',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['excepcion_parcial_ref'], 'partial-repayment-exception-2026-01')
        self.assertEqual(
            response.data['excepcion_parcial_motivo'],
            'Excepcion formal autorizada por acuerdo operativo controlado.',
        )
        repayment = RepactacionDeuda.objects.get(pk=response.data['id'])
        self.assertEqual(repayment.excepcion_parcial_ref, 'partial-repayment-exception-2026-01')
        self.assertEqual(
            repayment.excepcion_parcial_motivo,
            'Excepcion formal autorizada por acuerdo operativo controlado.',
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
                entity_type='repactacion_deuda',
                entity_id=str(response.data['id']),
                metadata__excepcion_parcial_ref='partial-repayment-exception-2026-01',
                metadata__excepcion_parcial_motivo='Excepcion formal autorizada por acuerdo operativo controlado.',
            ).exists()
        )

    def test_repayment_create_rolls_back_when_view_audit_fails(self):
        contrato = self._create_active_contract(codigo='CON-REP-AUDIT', monto_base='100000.00', code='111')

        with patch('cobranza.views.create_audit_event', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaisesMessage(RuntimeError, 'audit unavailable'):
                self.client.post(
                    reverse('cobranza-repactacion-list'),
                    {
                        'arrendatario': contrato.arrendatario_id,
                        'contrato_origen': contrato.id,
                        'deuda_total_original': '50000.00',
                        'cantidad_cuotas': 5,
                        'monto_cuota': '10000.00',
                        'saldo_pendiente': '50000.00',
                        'estado': 'activa',
                    },
                    format='json',
                )

        self.assertFalse(RepactacionDeuda.objects.filter(contrato_origen=contrato).exists())
        self.assertFalse(AuditEvent.objects.filter(event_type='cobranza.repactacion_deuda.created').exists())

    def test_partial_repayment_service_creates_exception_audit_event(self):
        contrato = self._create_active_contract(codigo='CON-REP-PARTIAL-SVC', monto_base='100000.00', code='111')

        repayment, audit_event = save_repayment_plan(
            validated_data={
                'arrendatario': contrato.arrendatario,
                'contrato_origen': contrato,
                'deuda_total_original': Decimal('50000.00'),
                'cantidad_cuotas': 4,
                'monto_cuota': Decimal('10000.00'),
                'saldo_pendiente': Decimal('40000.00'),
                'estado': 'activa',
                'excepcion_parcial_ref': '  partial-repayment-service-2026-01  ',
                'excepcion_parcial_motivo': '  Excepcion formal autorizada por acuerdo operativo controlado.  ',
            },
            actor_user=self.user,
            ip_address='127.0.0.1',
        )

        self.assertIsNotNone(audit_event)
        self.assertEqual(repayment.excepcion_parcial_ref, 'partial-repayment-service-2026-01')
        self.assertEqual(
            repayment.excepcion_parcial_motivo,
            'Excepcion formal autorizada por acuerdo operativo controlado.',
        )
        self.assertEqual(audit_event.event_type, PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE)
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.ip_address, '127.0.0.1')
        self.assertEqual(audit_event.entity_id, str(repayment.pk))
        self.assertEqual(audit_event.metadata['arrendatario_id'], contrato.arrendatario_id)
        self.assertEqual(audit_event.metadata['contrato_id'], contrato.id)
        self.assertEqual(audit_event.metadata['excepcion_parcial_ref'], 'partial-repayment-service-2026-01')
        self.assertEqual(
            audit_event.metadata['excepcion_parcial_motivo'],
            'Excepcion formal autorizada por acuerdo operativo controlado.',
        )

    def test_partial_repayment_service_requires_actor(self):
        contrato = self._create_active_contract(codigo='CON-REP-PARTIAL-ACTOR', monto_base='100000.00', code='111')

        with self.assertRaisesMessage(ValueError, 'actor trazable'):
            save_repayment_plan(
                validated_data={
                    'arrendatario': contrato.arrendatario,
                    'contrato_origen': contrato,
                    'deuda_total_original': Decimal('50000.00'),
                    'cantidad_cuotas': 4,
                    'monto_cuota': Decimal('10000.00'),
                    'saldo_pendiente': Decimal('40000.00'),
                    'estado': 'activa',
                    'excepcion_parcial_ref': 'partial-repayment-service-2026-01',
                    'excepcion_parcial_motivo': 'Excepcion formal autorizada por acuerdo operativo controlado.',
                },
            )

        self.assertFalse(RepactacionDeuda.objects.filter(contrato_origen=contrato).exists())
        self.assertFalse(
            AuditEvent.objects.filter(event_type=PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE).exists()
        )

    def test_payment_entering_repayment_requires_traceable_repayment_plan(self):
        payment = self._generate_monthly_payment(codigo='CON-REP-PAYMENT-TRACE')
        self.client.post(
            reverse('cobranza-pago-refresh-mora'),
            {'fecha_corte': '2026-01-10'},
            format='json',
        )
        payment.refresh_from_db()
        self.assertEqual(payment.estado_pago, EstadoPago.OVERDUE)
        self.assertEqual(payment.dias_mora, 5)

        without_plan = self.client.patch(
            reverse('cobranza-pago-detail', args=[payment.pk]),
            {'estado_pago': EstadoPago.IN_REPAYMENT},
            format='json',
        )

        self.assertEqual(without_plan.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('repactacion_deuda', without_plan.data)

        repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='30000.00',
            estado='activa',
        )
        with_plan = self.client.patch(
            reverse('cobranza-pago-detail', args=[payment.pk]),
            {
                'estado_pago': EstadoPago.IN_REPAYMENT,
                'repactacion_deuda': repayment.pk,
            },
            format='json',
        )

        self.assertEqual(with_plan.status_code, status.HTTP_200_OK)
        self.assertEqual(with_plan.data['estado_pago'], EstadoPago.IN_REPAYMENT)
        self.assertEqual(with_plan.data['repactacion_deuda'], repayment.pk)
        self.assertEqual(with_plan.data['dias_mora'], 5)
        payment.refresh_from_db()
        self.assertEqual(payment.repactacion_deuda_id, repayment.pk)
        self.assertEqual(payment.dias_mora, 5)

    def test_payment_paid_via_repayment_requires_completed_plan(self):
        payment = self._generate_monthly_payment(codigo='CON-REP-PAYMENT-CLOSE')
        active_repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='30000.00',
            estado='activa',
        )
        payment.estado_pago = EstadoPago.OVERDUE
        payment.dias_mora = 5
        payment.save(update_fields=['estado_pago', 'dias_mora', 'updated_at'])
        payment.estado_pago = EstadoPago.IN_REPAYMENT
        payment.repactacion_deuda = active_repayment
        payment.full_clean()
        payment.save(update_fields=['estado_pago', 'repactacion_deuda', 'updated_at'])

        payment.estado_pago = EstadoPago.PAID_VIA_REPAYMENT
        payment.monto_pagado_clp = Decimal('30000.00')
        payment.fecha_deteccion_sistema = date(2026, 2, 5)

        with self.assertRaises(ValidationError) as error:
            payment.full_clean()

        self.assertIn('estado_pago', error.exception.message_dict)

        active_repayment.estado = 'cumplida'
        active_repayment.saldo_pendiente = Decimal('0.00')
        active_repayment.save(update_fields=['estado', 'saldo_pendiente', 'updated_at'])
        payment.full_clean()

    def test_rebuild_account_state_summarizes_open_payments_repactations_and_residuals(self):
        contrato = self._create_active_contract(codigo='CON-STATE-ALL', monto_base='100000.00', code='111')
        generate = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generate.status_code, status.HTTP_201_CREATED)

        pago = PagoMensual.objects.get(pk=generate.data['id'])
        pago.estado_pago = EstadoPago.OVERDUE
        pago.save(update_fields=['estado_pago'])

        RepactacionDeuda.objects.create(
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='20000.00',
            estado='activa',
        )
        CodigoCobroResidual.objects.create(
            referencia_visible='CCR-ABC234',
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            saldo_actual='15000.00',
            estado='activa',
            fecha_activacion='2027-01-10',
        )

        response = self.client.post(
            reverse('cobranza-estado-cuenta-rebuild'),
            {'arrendatario_id': contrato.arrendatario_id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resumen_operativo']['pagos_atrasados'], 1)
        self.assertEqual(response.data['resumen_operativo']['repactaciones_activas'], 1)
        self.assertEqual(response.data['resumen_operativo']['cobranzas_residuales_activas'], 1)
        self.assertEqual(response.data['resumen_operativo']['saldo_total_clp'], '135111.00')

    def test_rebuild_account_state_calculates_payment_score_and_counts(self):
        contrato = self._create_active_contract(codigo='CON-STATE-SCORE', monto_base='100000.00', code='111')
        january_response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        february_response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 2},
            format='json',
        )
        self.assertEqual(january_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(february_response.status_code, status.HTTP_201_CREATED)

        january = PagoMensual.objects.get(pk=january_response.data['id'])
        february = PagoMensual.objects.get(pk=february_response.data['id'])
        january.estado_pago = EstadoPago.PAID
        january.monto_pagado_clp = january.monto_calculado_clp
        january.fecha_deposito_banco = date(2026, 1, 5)
        january.save(
            update_fields=[
                'estado_pago',
                'monto_pagado_clp',
                'fecha_deposito_banco',
                'updated_at',
            ]
        )
        february.estado_pago = EstadoPago.OVERDUE
        february.dias_mora = 5
        february.save(update_fields=['estado_pago', 'dias_mora', 'updated_at'])

        state = rebuild_account_state(contrato.arrendatario, reference_date=date(2026, 2, 10))

        self.assertEqual(state.score_pago, 50)
        self.assertEqual(state.resumen_operativo['score_pago_porcentaje'], 50)
        self.assertEqual(state.resumen_operativo['score_meses_evaluados'], 2)
        self.assertEqual(state.resumen_operativo['score_pagos_en_plazo'], 1)
        self.assertEqual(state.resumen_operativo['score_pagos_fuera_plazo'], 1)
        self.assertEqual(state.resumen_operativo['score_meses_sin_registro_operativo'], 0)

    def test_rebuild_account_state_score_excludes_months_without_operational_record(self):
        contrato = self._create_active_contract(codigo='CON-STATE-SCORE-OPS', monto_base='100000.00', code='111')
        contrato.fecha_registro_operativo = date(2026, 2, 10)
        contrato.save(update_fields=['fecha_registro_operativo', 'updated_at'])
        period = contrato.periodos_contractuales.get()
        PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=period,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_efecto_codigo_efectivo_clp='111.00',
            fecha_vencimiento=date(2026, 1, 5),
            estado_pago=EstadoPago.OVERDUE,
            dias_mora=65,
            codigo_conciliacion_efectivo='111',
        )
        PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=period,
            mes=3,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_efecto_codigo_efectivo_clp='111.00',
            monto_pagado_clp='100111.00',
            fecha_vencimiento=date(2026, 3, 5),
            fecha_deposito_banco=date(2026, 3, 5),
            estado_pago=EstadoPago.PAID,
            codigo_conciliacion_efectivo='111',
        )

        state = rebuild_account_state(contrato.arrendatario, reference_date=date(2026, 3, 6))

        self.assertEqual(state.score_pago, 100)
        self.assertEqual(state.resumen_operativo['score_pago_porcentaje'], 100)
        self.assertEqual(state.resumen_operativo['score_meses_evaluados'], 1)
        self.assertEqual(state.resumen_operativo['score_pagos_en_plazo'], 1)
        self.assertEqual(state.resumen_operativo['score_pagos_fuera_plazo'], 0)
        self.assertEqual(state.resumen_operativo['score_meses_sin_registro_operativo'], 1)

    def test_payment_score_with_repayment_requires_full_monthly_due(self):
        payment = self._generate_monthly_payment(codigo='CON-STATE-SCORE-REP')
        repayment = RepactacionDeuda.objects.create(
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='0.00',
            estado='cumplida',
        )
        payment.estado_pago = EstadoPago.PAID_VIA_REPAYMENT
        payment.repactacion_deuda = repayment
        payment.monto_pagado_clp = payment.monto_calculado_clp
        payment.fecha_deteccion_sistema = payment.fecha_vencimiento
        payment.save(
            update_fields=[
                'estado_pago',
                'repactacion_deuda',
                'monto_pagado_clp',
                'fecha_deteccion_sistema',
                'updated_at',
            ]
        )

        state = rebuild_account_state(payment.contrato.arrendatario, reference_date=date(2026, 1, 6))

        self.assertEqual(state.score_pago, 0)
        self.assertEqual(state.resumen_operativo['score_meses_evaluados'], 1)
        self.assertEqual(state.resumen_operativo['score_pagos_en_plazo'], 0)

    def test_rebuild_account_state_respects_company_scope(self):
        shared_tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Scope Shared',
            rut='55555555-5',
            email='shared@example.com',
            telefono='888',
            domicilio_notificaciones='Otra',
            estado_contacto='activo',
        )
        company_a = self._create_active_empresa('Scope A', '81818181-8', self._rut_for_code('SCOPEA', 1), self._rut_for_code('SCOPEA', 2))
        company_b = self._create_active_empresa('Scope B', '82828282-8', self._rut_for_code('SCOPEB', 1), self._rut_for_code('SCOPEB', 2))
        contrato_a, periodo_a = self._create_contract_for_company_and_arrendatario(empresa=company_a, arrendatario=shared_tenant, codigo='SCOPE-A')
        contrato_b, periodo_b = self._create_contract_for_company_and_arrendatario(empresa=company_b, arrendatario=shared_tenant, codigo='SCOPE-B')
        PagoMensual.objects.create(
            contrato=contrato_a,
            periodo_contractual=periodo_a,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_efecto_codigo_efectivo_clp='111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago=EstadoPago.OVERDUE,
            codigo_conciliacion_efectivo='111',
        )
        PagoMensual.objects.create(
            contrato=contrato_b,
            periodo_contractual=periodo_b,
            mes=1,
            anio=2026,
            monto_facturable_clp='200000.00',
            monto_calculado_clp='200222.00',
            monto_efecto_codigo_efectivo_clp='222.00',
            fecha_vencimiento='2026-01-05',
            estado_pago=EstadoPago.OVERDUE,
            codigo_conciliacion_efectivo='222',
        )
        RepactacionDeuda.objects.create(
            arrendatario=shared_tenant,
            contrato_origen=contrato_b,
            deuda_total_original='30000.00',
            cantidad_cuotas=3,
            monto_cuota='10000.00',
            saldo_pendiente='20000.00',
            estado='activa',
        )
        CodigoCobroResidual.objects.create(
            referencia_visible='CCR-ZZZ999',
            arrendatario=shared_tenant,
            contrato_origen=contrato_b,
            saldo_actual='15000.00',
            estado='activa',
            fecha_activacion='2027-01-10',
        )

        scoped_user = get_user_model().objects.create_user(
            username='billing-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        scope = Scope.objects.create(
            code=f'company-{company_a.id}',
            name=f'Empresa {company_a.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(company_a.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=scoped_user, role=operator_role, scope=scope, is_primary=True)
        self.client.force_authenticate(scoped_user)

        response = self.client.post(
            reverse('cobranza-estado-cuenta-rebuild'),
            {'arrendatario_id': shared_tenant.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['resumen_operativo']['pagos_abiertos'], 1)
        self.assertEqual(response.data['resumen_operativo']['pagos_atrasados'], 1)
        self.assertEqual(response.data['resumen_operativo']['repactaciones_activas'], 0)
        self.assertEqual(response.data['resumen_operativo']['cobranzas_residuales_activas'], 0)
        self.assertEqual(response.data['resumen_operativo']['saldo_total_clp'], '100111.00')

    def test_payment_distribution_snapshot_uses_month_effective_participations(self):
        company_a = self._create_active_empresa('Hist A', '83838383-8', self._rut_for_code('HISTA', 1), self._rut_for_code('HISTA', 2))
        company_b = self._create_active_empresa('Hist B', '84848484-8', self._rut_for_code('HISTB', 1), self._rut_for_code('HISTB', 2))
        tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Hist',
            rut='56565656-5',
            email='hist@example.com',
            telefono='777',
            domicilio_notificaciones='Hist',
            estado_contacto='activo',
        )
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Hist', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_empresa=company_a,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            vigente_hasta='2026-01-31',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_empresa=company_b,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            vigente_hasta='2026-01-31',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_empresa=company_a,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-02-01',
            activo=True,
        )
        contrato, periodo = self._create_contract_for_company_and_arrendatario(
            empresa=company_a,
            arrendatario=tenant,
            codigo='HIST-DIST',
            owner_kind='comunidad',
            comunidad=comunidad,
        )
        pago = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_efecto_codigo_efectivo_clp='111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago=EstadoPago.PENDING,
            codigo_conciliacion_efectivo='111',
        )

        sync_payment_distribution(pago)

        distribuciones = list(pago.distribuciones_cobro.order_by('id'))
        self.assertEqual(len(distribuciones), 2)
        self.assertEqual([str(item.monto_devengado_clp) for item in distribuciones], ['50000.00', '50000.00'])

        response = self.client.get(reverse('cobranza-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        snapshot_pago = response.data['pagos'][0]
        self.assertEqual(snapshot_pago['id'], pago.id)
        self.assertEqual(
            [item['beneficiario_display'] for item in snapshot_pago['distribuciones_detail']],
            ['Hist A', 'Hist B'],
        )
        self.assertEqual(
            [item['porcentaje_snapshot'] for item in snapshot_pago['distribuciones_detail']],
            ['50.00', '50.00'],
        )
        self.assertEqual(
            [item['monto_devengado_clp'] for item in snapshot_pago['distribuciones_detail']],
            ['50000.00', '50000.00'],
        )


class DistribucionCobroConstraintTests(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(nombre='Socio Dist', rut='12345678-5')
        self.empresa = Empresa.objects.create(razon_social='Empresa Dist', rut='87654321-4')
        self.owner_socio = Socio.objects.create(nombre='Owner Dist', rut='11222333-0')
        self.propiedad = Propiedad.objects.create(
            direccion='Av Restricciones 123',
            comuna='Temuco',
            region='Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='DIST-001',
            socio_owner=self.owner_socio,
        )
        self.cuenta = CuentaRecaudadora.objects.create(
            socio_owner=self.owner_socio,
            institucion='Banco Dist',
            numero_cuenta='DIST-ACC-001',
            tipo_cuenta='corriente',
            titular_nombre=self.owner_socio.nombre,
            titular_rut=self.owner_socio.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        self.arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Dist',
            rut='14567890-8',
            email='dist@example.com',
            telefono='123',
            domicilio_notificaciones='Dist',
            estado_contacto='activo',
        )
        self.mandato = MandatoOperacion.objects.create(
            propiedad=self.propiedad,
            propietario_socio_owner=self.owner_socio,
            administrador_socio_owner=self.owner_socio,
            recaudador_socio_owner=self.owner_socio,
            cuenta_recaudadora=self.cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=False,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
        )
        self.contrato = Contrato.objects.create(
            codigo_contrato='DIST-CON-001',
            mandato_operacion=self.mandato,
            arrendatario=self.arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            dia_pago_mensual=5,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=self.contrato,
            propiedad=self.propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        self.periodo = PeriodoContractual.objects.create(
            contrato=self.contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='base',
            origen_periodo='manual',
        )
        self.pago = PagoMensual.objects.create(
            contrato=self.contrato,
            periodo_contractual=self.periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_efecto_codigo_efectivo_clp='111.00',
            monto_pagado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago=EstadoPago.PAID,
            codigo_conciliacion_efectivo='111',
        )

    def test_distribution_db_rejects_facturable_without_dte_flag(self):
        with self.assertRaises(IntegrityError):
            DistribucionCobroMensual.objects.create(
                pago_mensual=self.pago,
                beneficiario_empresa_owner=self.empresa,
                porcentaje_snapshot='100.00',
                monto_devengado_clp='100000.00',
                monto_conciliado_clp='100111.00',
                monto_facturable_clp='100000.00',
                requiere_dte=False,
            )

    def test_distribution_db_rejects_duplicate_beneficiary_per_payment(self):
        DistribucionCobroMensual.objects.create(
            pago_mensual=self.pago,
            beneficiario_empresa_owner=self.empresa,
            porcentaje_snapshot='100.00',
            monto_devengado_clp='100000.00',
            monto_conciliado_clp='100111.00',
            monto_facturable_clp='100000.00',
            requiere_dte=True,
        )

        with self.assertRaises(IntegrityError):
            DistribucionCobroMensual.objects.create(
                pago_mensual=self.pago,
                beneficiario_empresa_owner=self.empresa,
                porcentaje_snapshot='100.00',
                monto_devengado_clp='100000.00',
                monto_conciliado_clp='100111.00',
                monto_facturable_clp='100000.00',
                requiere_dte=True,
            )


class CobranzaMigrationSafetyTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = [
        ('patrimonio', '0002_participaciones_mixtas_y_representacion_comunidad'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0003_pagomensual_monto_facturable_clp'),
    ]
    migrate_to = [
        ('patrimonio', '0003_repair_legacy_representacion_modes'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0004_distribucioncobromensual'),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(self.migrate_from).apps

    def migrate(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def test_historical_distribution_backfill_uses_operational_month_and_non_zero_fallback(self):
        Socio = self.old_apps.get_model('patrimonio', 'Socio')
        Empresa = self.old_apps.get_model('patrimonio', 'Empresa')
        ComunidadPatrimonial = self.old_apps.get_model('patrimonio', 'ComunidadPatrimonial')
        ParticipacionPatrimonial = self.old_apps.get_model('patrimonio', 'ParticipacionPatrimonial')
        Propiedad = self.old_apps.get_model('patrimonio', 'Propiedad')
        CuentaRecaudadora = self.old_apps.get_model('operacion', 'CuentaRecaudadora')
        MandatoOperacion = self.old_apps.get_model('operacion', 'MandatoOperacion')
        Arrendatario = self.old_apps.get_model('contratos', 'Arrendatario')
        Contrato = self.old_apps.get_model('contratos', 'Contrato')
        ContratoPropiedad = self.old_apps.get_model('contratos', 'ContratoPropiedad')
        PeriodoContractual = self.old_apps.get_model('contratos', 'PeriodoContractual')
        PagoMensual = self.old_apps.get_model('cobranza', 'PagoMensual')

        admin_socio_a = Socio.objects.create(nombre='Admin A', rut='10101010-8', activo=True)
        admin_socio_b = Socio.objects.create(nombre='Admin B', rut='20202020-6', activo=True)
        company_a = Empresa.objects.create(razon_social='Hist A', rut='76111111-1', estado='activa')
        company_b = Empresa.objects.create(razon_social='Hist B', rut='76222222-2', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=admin_socio_a.id,
            empresa_owner_id=company_a.id,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=admin_socio_b.id,
            empresa_owner_id=company_b.id,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Hist', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_empresa_id=company_a.id,
            comunidad_owner_id=comunidad.id,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            vigente_hasta='2026-01-31',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_empresa_id=company_b.id,
            comunidad_owner_id=comunidad.id,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            vigente_hasta='2026-01-31',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_empresa_id=company_a.id,
            comunidad_owner_id=comunidad.id,
            porcentaje='100.00',
            vigente_desde='2026-02-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            direccion='Av Hist 123',
            comuna='Santiago',
            region='RM',
            tipo_inmueble='local',
            codigo_propiedad='HIST-001',
            comunidad_owner_id=comunidad.id,
            estado='activa',
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner_id=company_a.id,
            institucion='Banco Hist',
            numero_cuenta='HIST-ACC',
            tipo_cuenta='corriente',
            titular_nombre='Hist A',
            titular_rut='76111111-1',
            moneda_operativa='CLP',
            estado_operativo='activa',
        )
        tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Tenant Hist',
            rut='56565656-5',
            email='hist@example.com',
            telefono='777',
            domicilio_notificaciones='Hist',
            estado_contacto='activo',
        )
        mandato = MandatoOperacion.objects.create(
            propiedad_id=propiedad.id,
            propietario_comunidad_owner_id=comunidad.id,
            administrador_empresa_owner_id=company_a.id,
            cuenta_recaudadora_id=cuenta.id,
            entidad_facturadora_id=company_a.id,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado='activa',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='HIST-DIST',
            mandato_operacion_id=mandato.id,
            arrendatario_id=tenant.id,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            dia_pago_mensual=5,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato_id=contrato.id,
            propiedad_id=propiedad.id,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        periodo = PeriodoContractual.objects.create(
            contrato_id=contrato.id,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='base',
            origen_periodo='manual',
        )
        PagoMensual.objects.create(
            contrato_id=contrato.id,
            periodo_contractual_id=periodo.id,
            mes=1,
            anio=2026,
            monto_facturable_clp='0.00',
            monto_calculado_clp='100111.00',
            monto_pagado_clp='0.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pendiente',
            codigo_conciliacion_efectivo='111',
        )

        self.migrate()

        PagoMensualNew = self.apps.get_model('cobranza', 'PagoMensual')
        DistribucionCobroMensualNew = self.apps.get_model('cobranza', 'DistribucionCobroMensual')
        payment = PagoMensualNew.objects.get(contrato__codigo_contrato='HIST-DIST')
        distributions = list(DistribucionCobroMensualNew.objects.filter(pago_mensual_id=payment.id).order_by('id'))

        self.assertEqual(len(distributions), 2)
        self.assertEqual(
            [str(item.monto_devengado_clp) for item in distributions],
            ['50055.50', '50055.50'],
        )
        self.assertEqual(
            [item.beneficiario_empresa_owner.razon_social for item in distributions],
            ['Hist A', 'Hist B'],
        )


class CobranzaRepairMigrationSafetyTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = [
        ('audit', '0003_manual_resolution_superseded_status'),
        ('patrimonio', '0003_repair_legacy_representacion_modes'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0004_distribucioncobromensual'),
        ('sii', '0004_dte_emitido_distribucion_cobro_mensual'),
    ]
    migrate_to = [
        ('audit', '0003_manual_resolution_superseded_status'),
        ('patrimonio', '0003_repair_legacy_representacion_modes'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0005_repair_legacy_distribuciones_and_add_constraints'),
        ('sii', '0004_dte_emitido_distribucion_cobro_mensual'),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(self.migrate_from).apps

    def migrate(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def _create_active_company(self, Empresa, Socio, ParticipacionPatrimonial, *, nombre, rut, socio_rut_base):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=f'{socio_rut_base}1-1', activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=f'{socio_rut_base}2-2', activo=True)
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=socio_1.id,
            empresa_owner_id=empresa.id,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=socio_2.id,
            empresa_owner_id=empresa.id,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        return empresa

    def _create_payment_with_legacy_distributions(
        self,
        *,
        include_facturadora_in_snapshot,
        dte_attached_to_other_company_distribution=False,
        payment_monto_facturable='100000.00',
        dte_monto_neto='100000.00',
    ):
        Socio = self.old_apps.get_model('patrimonio', 'Socio')
        Empresa = self.old_apps.get_model('patrimonio', 'Empresa')
        ComunidadPatrimonial = self.old_apps.get_model('patrimonio', 'ComunidadPatrimonial')
        ParticipacionPatrimonial = self.old_apps.get_model('patrimonio', 'ParticipacionPatrimonial')
        Propiedad = self.old_apps.get_model('patrimonio', 'Propiedad')
        CuentaRecaudadora = self.old_apps.get_model('operacion', 'CuentaRecaudadora')
        MandatoOperacion = self.old_apps.get_model('operacion', 'MandatoOperacion')
        Arrendatario = self.old_apps.get_model('contratos', 'Arrendatario')
        Contrato = self.old_apps.get_model('contratos', 'Contrato')
        ContratoPropiedad = self.old_apps.get_model('contratos', 'ContratoPropiedad')
        PeriodoContractual = self.old_apps.get_model('contratos', 'PeriodoContractual')
        PagoMensual = self.old_apps.get_model('cobranza', 'PagoMensual')
        DistribucionCobroMensual = self.old_apps.get_model('cobranza', 'DistribucionCobroMensual')
        CapacidadTributariaSII = self.old_apps.get_model('sii', 'CapacidadTributariaSII')
        DTEEmitido = self.old_apps.get_model('sii', 'DTEEmitido')

        facturadora = self._create_active_company(
            Empresa,
            Socio,
            ParticipacionPatrimonial,
            nombre='Facturadora Legacy',
            rut='76101010-0',
            socio_rut_base='1100110',
        )
        other_company = self._create_active_company(
            Empresa,
            Socio,
            ParticipacionPatrimonial,
            nombre='Otra Empresa Legacy',
            rut='76202020-0',
            socio_rut_base='2200220',
        )
        socio_comunidad = Socio.objects.create(nombre='Socio Comunidad', rut='33333333-3', activo=True)
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Legacy Repair', estado='activa')
        if include_facturadora_in_snapshot:
            if dte_attached_to_other_company_distribution:
                ParticipacionPatrimonial.objects.create(
                    participante_empresa_id=other_company.id,
                    comunidad_owner_id=comunidad.id,
                    porcentaje='25.00',
                    vigente_desde='2026-01-01',
                    activo=True,
                )
            ParticipacionPatrimonial.objects.create(
                participante_empresa_id=facturadora.id,
                comunidad_owner_id=comunidad.id,
                porcentaje='50.00',
                vigente_desde='2026-01-01',
                activo=True,
            )
            ParticipacionPatrimonial.objects.create(
                participante_socio_id=socio_comunidad.id,
                comunidad_owner_id=comunidad.id,
                porcentaje='25.00' if dte_attached_to_other_company_distribution else '50.00',
                vigente_desde='2026-01-01',
                activo=True,
            )
        else:
            ParticipacionPatrimonial.objects.create(
                participante_empresa_id=other_company.id,
                comunidad_owner_id=comunidad.id,
                porcentaje='50.00',
                vigente_desde='2026-01-01',
                activo=True,
            )
            ParticipacionPatrimonial.objects.create(
                participante_socio_id=socio_comunidad.id,
                comunidad_owner_id=comunidad.id,
                porcentaje='50.00',
                vigente_desde='2026-01-01',
                activo=True,
            )

        propiedad = Propiedad.objects.create(
            direccion='Av Legacy Repair 123',
            comuna='Santiago',
            region='RM',
            tipo_inmueble='local',
            codigo_propiedad='LEG-RPR-001',
            comunidad_owner_id=comunidad.id,
            estado='activa',
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner_id=facturadora.id,
            institucion='Banco Legacy',
            numero_cuenta='LEG-RPR-ACC',
            tipo_cuenta='corriente',
            titular_nombre=facturadora.razon_social,
            titular_rut=facturadora.rut,
            moneda_operativa='CLP',
            estado_operativo='activa',
        )
        tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Tenant Repair',
            rut='56565656-5',
            email='repair@example.com',
            telefono='777',
            domicilio_notificaciones='Legacy',
            estado_contacto='activo',
        )
        mandato = MandatoOperacion.objects.create(
            propiedad_id=propiedad.id,
            propietario_comunidad_owner_id=comunidad.id,
            administrador_empresa_owner_id=facturadora.id,
            entidad_facturadora_id=facturadora.id,
            cuenta_recaudadora_id=cuenta.id,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado='activa',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='LEG-RPR-CON',
            mandato_operacion_id=mandato.id,
            arrendatario_id=tenant.id,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            dia_pago_mensual=5,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato_id=contrato.id,
            propiedad_id=propiedad.id,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        periodo = PeriodoContractual.objects.create(
            contrato_id=contrato.id,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='base',
            origen_periodo='manual',
        )
        pago = PagoMensual.objects.create(
            contrato_id=contrato.id,
            periodo_contractual_id=periodo.id,
            mes=1,
            anio=2026,
            monto_facturable_clp=payment_monto_facturable,
            monto_calculado_clp='100111.00',
            monto_pagado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pagado',
            codigo_conciliacion_efectivo='111',
        )
        if include_facturadora_in_snapshot:
            if dte_attached_to_other_company_distribution:
                DistribucionCobroMensual.objects.create(
                    pago_mensual_id=pago.id,
                    beneficiario_empresa_owner_id=other_company.id,
                    porcentaje_snapshot='25.00',
                    monto_devengado_clp='25000.00',
                    monto_conciliado_clp='25027.75',
                    monto_facturable_clp='0.00',
                    requiere_dte=False,
                    origen_atribucion='backfill_migracion',
                )
            DistribucionCobroMensual.objects.create(
                pago_mensual_id=pago.id,
                beneficiario_empresa_owner_id=facturadora.id,
                porcentaje_snapshot='50.00',
                monto_devengado_clp='50000.00',
                monto_conciliado_clp='50055.50',
                monto_facturable_clp='0.00',
                requiere_dte=False,
                origen_atribucion='backfill_migracion',
            )
        else:
            DistribucionCobroMensual.objects.create(
                pago_mensual_id=pago.id,
                beneficiario_empresa_owner_id=other_company.id,
                porcentaje_snapshot='50.00',
                monto_devengado_clp='50000.00',
                monto_conciliado_clp='50055.50',
                monto_facturable_clp='0.00',
                requiere_dte=False,
                origen_atribucion='backfill_migracion',
            )
        DistribucionCobroMensual.objects.create(
            pago_mensual_id=pago.id,
            beneficiario_socio_owner_id=socio_comunidad.id,
            porcentaje_snapshot='25.00' if dte_attached_to_other_company_distribution else '50.00',
            monto_devengado_clp='25000.00' if dte_attached_to_other_company_distribution else '50000.00',
            monto_conciliado_clp='25027.75' if dte_attached_to_other_company_distribution else '50055.50',
            monto_facturable_clp='0.00',
            requiere_dte=False,
            origen_atribucion='backfill_migracion',
        )
        orphan_distribution = DistribucionCobroMensual.objects.create(
            pago_mensual_id=pago.id,
            beneficiario_empresa_owner_id=(
                other_company.id if dte_attached_to_other_company_distribution else facturadora.id
            ),
            porcentaje_snapshot='100.00',
            monto_devengado_clp=dte_monto_neto,
            monto_conciliado_clp='100111.00',
            monto_facturable_clp=dte_monto_neto,
            requiere_dte=True,
            origen_atribucion='backfill_dte_orfano',
        )
        capacidad = CapacidadTributariaSII.objects.create(
            empresa_id=facturadora.id,
            capacidad_key='DTEEmision',
            certificado_ref='cert-legacy',
            ambiente='certificacion',
            estado_gate='abierto',
        )
        dte = DTEEmitido.objects.create(
            empresa_id=facturadora.id,
            capacidad_tributaria_id=capacidad.id,
            contrato_id=contrato.id,
            pago_mensual_id=pago.id,
            distribucion_cobro_mensual_id=orphan_distribution.id,
            arrendatario_id=tenant.id,
            tipo_dte='34',
            monto_neto_clp=dte_monto_neto,
            fecha_emision='2026-01-06',
            estado_dte='borrador',
        )
        return {
            'pago_id': pago.id,
            'dte_id': dte.id,
            'facturadora_id': facturadora.id,
            'other_company_id': other_company.id,
            'socio_comunidad_id': socio_comunidad.id,
        }

    def test_0005_repairs_backfill_dte_orfano_when_facturadora_is_in_snapshot(self):
        refs = self._create_payment_with_legacy_distributions(include_facturadora_in_snapshot=True)

        self.migrate()

        DistribucionCobroMensual = self.apps.get_model('cobranza', 'DistribucionCobroMensual')
        DTEEmitido = self.apps.get_model('sii', 'DTEEmitido')

        distributions = list(DistribucionCobroMensual.objects.filter(pago_mensual_id=refs['pago_id']).order_by('id'))
        self.assertEqual(len(distributions), 2)
        self.assertEqual(
            {item.beneficiario_empresa_owner_id or item.beneficiario_socio_owner_id for item in distributions},
            {refs['facturadora_id'], refs['socio_comunidad_id']},
        )
        company_row = next(item for item in distributions if item.beneficiario_empresa_owner_id == refs['facturadora_id'])
        self.assertEqual(str(company_row.porcentaje_snapshot), '50.00')
        self.assertEqual(str(company_row.monto_devengado_clp), '50000.00')
        self.assertTrue(company_row.requiere_dte)
        dte = DTEEmitido.objects.get(pk=refs['dte_id'])
        self.assertEqual(dte.distribucion_cobro_mensual_id, company_row.id)

    def test_0005_relinks_dte_when_legacy_orphan_points_to_wrong_company_row(self):
        refs = self._create_payment_with_legacy_distributions(
            include_facturadora_in_snapshot=True,
            dte_attached_to_other_company_distribution=True,
        )

        self.migrate()

        DistribucionCobroMensual = self.apps.get_model('cobranza', 'DistribucionCobroMensual')
        DTEEmitido = self.apps.get_model('sii', 'DTEEmitido')

        distributions = list(DistribucionCobroMensual.objects.filter(pago_mensual_id=refs['pago_id']).order_by('id'))
        self.assertEqual(len(distributions), 3)
        company_row = next(item for item in distributions if item.beneficiario_empresa_owner_id == refs['facturadora_id'])
        other_company_row = next(item for item in distributions if item.beneficiario_empresa_owner_id == refs['other_company_id'])
        dte = DTEEmitido.objects.get(pk=refs['dte_id'])
        self.assertEqual(dte.distribucion_cobro_mensual_id, company_row.id)
        self.assertTrue(company_row.requiere_dte)
        self.assertFalse(other_company_row.requiere_dte)
        self.assertEqual(str(company_row.monto_facturable_clp), '50000.00')

    def test_0005_derives_full_facturable_amount_from_company_dte_share(self):
        refs = self._create_payment_with_legacy_distributions(
            include_facturadora_in_snapshot=True,
            payment_monto_facturable='0.00',
            dte_monto_neto='50000.00',
        )

        self.migrate()

        PagoMensual = self.apps.get_model('cobranza', 'PagoMensual')
        DistribucionCobroMensual = self.apps.get_model('cobranza', 'DistribucionCobroMensual')

        payment = PagoMensual.objects.get(pk=refs['pago_id'])
        distributions = list(DistribucionCobroMensual.objects.filter(pago_mensual_id=refs['pago_id']).order_by('id'))
        company_row = next(item for item in distributions if item.beneficiario_empresa_owner_id == refs['facturadora_id'])
        socio_row = next(item for item in distributions if item.beneficiario_socio_owner_id == refs['socio_comunidad_id'])

        self.assertEqual(str(payment.monto_facturable_clp), '100000.00')
        self.assertEqual(str(company_row.monto_devengado_clp), '50000.00')
        self.assertEqual(str(company_row.monto_facturable_clp), '50000.00')
        self.assertEqual(str(socio_row.monto_devengado_clp), '50000.00')

    def test_0005_keeps_existing_rows_when_dte_company_is_outside_historical_snapshot(self):
        refs = self._create_payment_with_legacy_distributions(include_facturadora_in_snapshot=False)

        self.migrate()

        ManualResolution = self.apps.get_model('audit', 'ManualResolution')
        DistribucionCobroMensual = self.apps.get_model('cobranza', 'DistribucionCobroMensual')
        DTEEmitido = self.apps.get_model('sii', 'DTEEmitido')

        distributions = list(DistribucionCobroMensual.objects.filter(pago_mensual_id=refs['pago_id']).order_by('id'))
        self.assertEqual(len(distributions), 3)
        self.assertTrue(any(item.beneficiario_empresa_owner_id == refs['facturadora_id'] for item in distributions))
        self.assertTrue(any(item.beneficiario_empresa_owner_id == refs['other_company_id'] for item in distributions))
        self.assertTrue(any(item.beneficiario_socio_owner_id == refs['socio_comunidad_id'] for item in distributions))
        dte = DTEEmitido.objects.get(pk=refs['dte_id'])
        self.assertEqual(dte.distribucion_cobro_mensual.beneficiario_empresa_owner_id, refs['facturadora_id'])
        resolution = ManualResolution.objects.get(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_reference=str(refs['pago_id']),
        )
        self.assertEqual(resolution.status, 'open')
        self.assertEqual(resolution.metadata['dte_id'], refs['dte_id'])
