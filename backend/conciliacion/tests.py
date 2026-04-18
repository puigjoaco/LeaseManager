from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import ManualResolution
from cobranza.models import CodigoCobroResidual, EstadoCobroResidual, EstadoPago, PagoMensual
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import ConexionBancaria, EstadoConciliacionMovimiento, IngresoDesconocido, MovimientoBancarioImportado


class ConciliacionAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='reconcile', password='secret123')
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

    def _create_contract_and_payment(self, codigo='REC-001', amount='100111.00'):
        propietario = self._create_socio(f'Prop {codigo}', '11111111-1')
        admin_company = self._create_active_empresa(f'Admin {codigo}', '88888888-8', '22222222-2', '33333333-3')
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
        pago = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_calculado_clp=amount,
            fecha_vencimiento='2026-01-05',
            codigo_conciliacion_efectivo='111',
            estado_pago=EstadoPago.PENDING,
        )
        return cuenta, pago, contrato

    def _create_connection(self, cuenta, provider='banco_de_chile'):
        return ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key=provider,
            credencial_ref=f'cred-{provider}',
            estado_conexion='activa',
            primaria_movimientos=True,
        )

    def test_auth_is_required_for_conciliacion_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('conciliacion-conexion-list'),
            reverse('conciliacion-movimiento-list'),
            reverse('conciliacion-ingreso-list'),
        ]
        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_exact_match_payment_marks_payment_as_paid(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-PAY', amount='100111.00')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '100111.00',
                'descripcion_origen': 'Pago arrendatario',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        pago.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(pago.dias_mora, 3)

    def test_exact_match_residual_marks_reference_as_paid(self):
        cuenta, _, contrato = self._create_contract_and_payment(codigo='REC-RES')
        conexion = self._create_connection(cuenta)
        residual = CodigoCobroResidual.objects.create(
            referencia_visible='CCR-ABC234',
            arrendatario=contrato.arrendatario,
            contrato_origen=contrato,
            saldo_actual='15000.00',
            estado=EstadoCobroResidual.ACTIVE,
            fecha_activacion='2027-01-10',
        )

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2027-01-15',
                'tipo_movimiento': 'abono',
                'monto': '15000.00',
                'descripcion_origen': 'Cobranza residual',
                'referencia': residual.referencia_visible,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        residual.refresh_from_db()
        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        self.assertEqual(residual.estado, EstadoCobroResidual.PAID)
        self.assertEqual(residual.saldo_actual, 0)
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)

    def test_unmatched_income_creates_ingreso_desconocido_and_manual_resolution(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-UNK')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '999999.00',
                'descripcion_origen': 'Abono desconocido',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertTrue(IngresoDesconocido.objects.filter(movimiento_bancario=movimiento).exists())
        self.assertTrue(
            ManualResolution.objects.filter(
                category='conciliacion.ingreso_desconocido',
                scope_reference=str(movimiento.pk),
            ).exists()
        )

    def test_debit_movement_requires_manual_resolution(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-09',
                'tipo_movimiento': 'cargo',
                'monto': '50000.00',
                'descripcion_origen': 'Cargo bancario',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertTrue(
            ManualResolution.objects.filter(
                category='conciliacion.movimiento_cargo',
                scope_reference=str(movimiento.pk),
            ).exists()
        )

    def test_retry_match_resolves_unknown_income_when_payment_appears(self):
        cuenta, _, contrato = self._create_contract_and_payment(codigo='REC-RETRY', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '777777.00',
                'descripcion_origen': 'Abono temprano',
            },
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)

        pago = PagoMensual.objects.get(contrato=contrato, mes=1, anio=2026)
        pago.monto_calculado_clp = '777777.00'
        pago.save(update_fields=['monto_calculado_clp'])

        retry = self.client.post(
            reverse('conciliacion-movimiento-match', args=[movimiento.id]),
            format='json',
        )
        self.assertEqual(retry.status_code, status.HTTP_200_OK)

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        ingreso = IngresoDesconocido.objects.get(movimiento_bancario=movimiento)
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(ingreso.estado, 'resuelto')

    def test_manual_resolution_can_regularize_unknown_income_to_selected_payment(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '777777.00',
                'descripcion_origen': 'Abono requiere regularizacion manual',
            },
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[resolution.pk]),
            {
                'pago_mensual_id': pago.pk,
                'rationale': 'Regularizado manualmente contra el pago correcto.',
            },
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_200_OK)

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        resolution.refresh_from_db()
        ingreso = IngresoDesconocido.objects.get(movimiento_bancario=movimiento)

        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(movimiento.pago_mensual_id, pago.pk)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(str(pago.monto_pagado_clp), '777777.00')
        self.assertEqual(ingreso.estado, 'resuelto')
        self.assertEqual(resolution.status, 'resolved')
        self.assertEqual(resolution.rationale, 'Regularizado manualmente contra el pago correcto.')
        self.assertEqual(resolution.metadata['resolved_payment_id'], pago.pk)
