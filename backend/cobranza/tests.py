from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import (
    AjusteContrato,
    CodigoCobroResidual,
    EstadoGarantia,
    EstadoPago,
    GarantiaContractual,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
)


class CobranzaAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='billing', password='secret123')
        self.client.force_authenticate(self.user)

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
        propietario = self._create_socio(f'Prop {codigo}', '11111111-1')
        admin_company = self._create_active_empresa(
            f'Admin {codigo}',
            '88888888-8',
            '22222222-2',
            '33333333-3',
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
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut='44444444-4',
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

    def test_auth_is_required_for_cobranza_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('cobranza-valor-uf-list'),
            reverse('cobranza-ajuste-list'),
            reverse('cobranza-pago-list'),
            reverse('cobranza-pago-generate'),
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
        self.assertEqual(response.data['codigo_conciliacion_efectivo'], '042')
        self.assertEqual(len(response.data['distribuciones_detail']), 1)
        self.assertEqual(response.data['distribuciones_detail'][0]['beneficiario_tipo'], 'socio')
        self.assertEqual(response.data['distribuciones_detail'][0]['monto_devengado_clp'], '523456.00')
        self.assertEqual(response.data['distribuciones_detail'][0]['monto_facturable_clp'], '0.00')
        self.assertTrue(AuditEvent.objects.filter(event_type='cobranza.pago_mensual.generated').exists())

    def test_generate_uf_payment_requires_existing_uf_value(self):
        contrato = self._create_active_contract(codigo='CON-UF-MISS', moneda='UF', monto_base='10.00', code='123')

        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_uf_payment_applies_adjustments_before_effective_code(self):
        contrato = self._create_active_contract(codigo='CON-UF-OK', moneda='UF', monto_base='10.00', code='123')
        ValorUFDiario.objects.create(fecha='2026-01-01', valor='35000.0000', source_key='manual')
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

    def test_payment_update_calculates_days_late(self):
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

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['dias_mora'], 3)
        self.assertEqual(update.data['distribuciones_detail'][0]['monto_conciliado_clp'], '100111.00')
        self.assertTrue(AuditEvent.objects.filter(event_type='cobranza.pago_mensual.state_changed').exists())

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
                'justificacion': 'Aplicacion final',
            },
            format='json',
        )
        self.assertEqual(total_retention.status_code, status.HTTP_201_CREATED)

        final_detail = self.client.get(reverse('cobranza-garantia-detail', args=[garantia.data['id']]))
        self.assertEqual(final_detail.data['estado_garantia'], EstadoGarantia.APPLIED)
        self.assertEqual(final_detail.data['monto_aplicado'], '70000.00')
        self.assertTrue(AuditEvent.objects.filter(event_type='cobranza.garantia_contractual.state_changed').exists())

    def test_guarantee_deposit_rejects_amount_above_pactado(self):
        contrato = self._create_active_contract(codigo='CON-GAR-FAIL', monto_base='100000.00', code='111')
        garantia = GarantiaContractual.objects.create(contrato=contrato, monto_pactado='50000.00')

        response = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.id]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '60000.00', 'fecha': '2026-01-01'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
