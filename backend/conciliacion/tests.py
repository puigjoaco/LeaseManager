import json
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent, ManualResolution
from contabilidad.models import AsientoContable, ConfiguracionFiscalEmpresa, CuentaContable, EventoContable, MatrizReglasContables, ReglaContable
from contabilidad.services import ensure_default_regime
from cobranza.models import CodigoCobroResidual, EstadoCobroResidual, EstadoPago, PagoMensual
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .admin import (
    ConexionBancariaAdmin,
    CuadraturaBancariaAdmin,
    IngresoDesconocidoAdmin,
    MovimientoBancarioImportadoAdmin,
    TransferenciaIntercuentaAdmin,
)
from .models import (
    CuadraturaBancaria,
    ConexionBancaria,
    EstadoConciliacionMovimiento,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    TransferenciaIntercuenta,
)


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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
            evidencia_gate_ref=f'evidence-{provider}',
            prueba_conectividad_ref=f'connectivity-{provider}',
            prueba_movimientos_ref=f'movements-{provider}',
            estado_conexion='activa',
            primaria_movimientos=True,
        )

    def _movement_payload(self, conexion, **overrides):
        payload = {
            'conexion_bancaria': conexion.id,
            'fecha_movimiento': '2026-01-08',
            'tipo_movimiento': 'abono',
            'monto': '100111.00',
            'descripcion_origen': 'Pago arrendatario',
            'origen_importacion': 'manual_controlada',
            'evidencia_importacion_ref': 'manual-import-controlled',
        }
        payload.update(overrides)
        return payload

    def _setup_contabilidad_for_company(self, empresa):
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )
        bancos = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='1101',
            nombre='Bancos',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        gasto = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='5101',
            nombre='ComisionesBancarias',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        regla = ReglaContable.objects.create(
            empresa=empresa,
            evento_tipo='ComisionBancaria',
            plan_cuentas_version='v1',
            criterio_cargo='default:5101',
            criterio_abono='default:1101',
            vigencia_desde='2026-01-01',
            estado='activa',
        )
        MatrizReglasContables.objects.create(
            regla_contable=regla,
            cuenta_debe=gasto,
            cuenta_haber=bancos,
            estado='activa',
        )

    def _charge_classification_payload(self, cuenta, **overrides):
        payload = {
            'categoria_movimiento': 'comision_bancaria',
            'entidad_afectada_tipo': 'empresa',
            'entidad_afectada_id': cuenta.empresa_owner_id,
            'periodo_economico': '2026-01',
            'criterio_reparto': 'Cargo asignado a la empresa duena de la cuenta recaudadora.',
            'evidencia_clasificacion_ref': 'bank-fee-statement-2026-01',
            'rationale': 'Comision bancaria del periodo.',
        }
        payload.update(overrides)
        return payload

    def _internal_transfer_payload(self, movimiento_destino, **overrides):
        payload = {
            'movimiento_destino_id': movimiento_destino.pk,
            'periodo_economico': '2026-01',
            'criterio_conciliacion': 'Par cargo/abono exacto entre cuentas recaudadoras.',
            'evidencia_transferencia_ref': 'internal-transfer-controlled-2026-01',
            'responsable_ref': 'stage3-transfer-owner',
            'rationale': 'Transferencia interna validada por cartola controlada.',
        }
        payload.update(overrides)
        return payload

    def _create_secondary_account(self, codigo='REC-DEST'):
        empresa = self._create_active_empresa(
            f'Destino {codigo}',
            '77777777-7',
            '55555555-5',
            '66666666-6',
        )
        return CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Dos',
            numero_cuenta=f'DST-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )

    def _unknown_income_resolution_payload(self, pago, **overrides):
        payload = {
            'pago_mensual_id': pago.pk,
            'periodo_economico': f'{pago.anio:04d}-{pago.mes:02d}',
            'criterio_aplicado': 'Asignacion manual contra saldo pendiente exacto del pago mensual.',
            'evidencia_regularizacion_ref': 'unknown-income-resolution-2026-01',
            'rationale': 'Regularizado manualmente contra el pago correcto.',
        }
        payload.update(overrides)
        return payload

    def test_conciliacion_admin_redacts_sensitive_bank_refs(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-ADM-CONC')
        conexion = self._create_connection(cuenta)
        ConexionBancaria.objects.filter(pk=conexion.pk).update(
            credencial_ref='https://bank.example.test/credential?token=secret',
            evidencia_gate_ref='https://bank.example.test/gate?token=secret',
            prueba_conectividad_ref='https://bank.example.test/connectivity?token=secret',
            prueba_movimientos_ref='https://bank.example.test/movements?token=secret',
            prueba_saldos_ref='https://bank.example.test/balances?token=secret',
        )
        conexion.refresh_from_db()
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto=Decimal('100111.00'),
            descripcion_origen='Movimiento con refs heredadas',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='https://bank.example.test/import?token=secret',
            numero_documento='DOC-ADM-CONC',
            saldo_reportado=Decimal('100111.00'),
            referencia='https://bank.example.test/reference?token=secret',
            transaction_id_banco='https://bank.example.test/tx?token=secret',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )
        cuadratura = CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura='2026-01-31',
            saldo_sistema_clp=Decimal('100111.00'),
            saldo_banco_clp=Decimal('100111.00'),
            estado='cuadrada',
            evidencia_cuadratura_ref='https://bank.example.test/balance?token=secret',
            responsable_ref='owner@example.test',
            rationale='Cuadratura en https://bank.example.test/balance?token=secret',
        )
        cuenta_destino = self._create_secondary_account('REC-ADM-CONC')
        conexion_destino = self._create_connection(cuenta_destino, provider='banco_estado_admin')
        movimiento_origen = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-10',
            tipo_movimiento='cargo',
            monto=Decimal('50000.00'),
            descripcion_origen='Transferencia enviada',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='internal-transfer-origin',
            estado_conciliacion=EstadoConciliacionMovimiento.MANUAL_REQUIRED,
        )
        movimiento_destino = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion_destino,
            fecha_movimiento='2026-01-10',
            tipo_movimiento='abono',
            monto=Decimal('50000.00'),
            descripcion_origen='Transferencia recibida',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='internal-transfer-destination',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )
        transferencia = TransferenciaIntercuenta.objects.create(
            movimiento_origen=movimiento_origen,
            movimiento_destino=movimiento_destino,
            periodo_economico='2026-01',
            criterio_conciliacion='Criterio con https://bank.example.test/transfer?token=secret',
            evidencia_transferencia_ref='https://bank.example.test/transfer?token=secret',
            responsable_ref='ops@example.test',
            rationale='Rationale en https://bank.example.test/transfer?token=secret',
        )
        ingreso = IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto=movimiento.monto,
            fecha_movimiento=movimiento.fecha_movimiento,
            descripcion_origen=movimiento.descripcion_origen,
            estado='pendiente_revision',
            sugerencia_asistida={
                'authorization': 'opaque-bank-auth',
                'callback_url': 'https://bank.example.test/callback?token=secret',
                'payment_candidate_ids': [1],
            },
        )
        site = AdminSite()

        connection_admin = ConexionBancariaAdmin(ConexionBancaria, site)
        movement_admin = MovimientoBancarioImportadoAdmin(MovimientoBancarioImportado, site)
        unknown_income_admin = IngresoDesconocidoAdmin(IngresoDesconocido, site)
        balance_admin = CuadraturaBancariaAdmin(CuadraturaBancaria, site)
        transfer_admin = TransferenciaIntercuentaAdmin(TransferenciaIntercuenta, site)

        self.assertNotIn('credencial_ref', connection_admin.fields)
        self.assertNotIn('evidencia_gate_ref', connection_admin.fields)
        self.assertNotIn('evidencia_gate_ref', connection_admin.search_fields)
        self.assertEqual(connection_admin.credencial_ref_redacted(conexion), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(connection_admin.evidencia_gate_ref_redacted(conexion), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(connection_admin.prueba_conectividad_ref_redacted(conexion), REDACTED_SENSITIVE_REFERENCE)
        self.assertFalse(connection_admin.has_add_permission(None))
        self.assertFalse(connection_admin.has_delete_permission(None))

        for raw_field in ('evidencia_importacion_ref', 'referencia', 'transaction_id_banco'):
            self.assertNotIn(raw_field, movement_admin.fields)
            self.assertNotIn(raw_field, movement_admin.search_fields)
        self.assertEqual(movement_admin.evidencia_importacion_ref_redacted(movimiento), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(movement_admin.referencia_redacted(movimiento), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(movement_admin.transaction_id_banco_redacted(movimiento), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(movement_admin.fields).issubset(set(movement_admin.readonly_fields)))
        self.assertFalse(movement_admin.has_add_permission(None))
        self.assertFalse(movement_admin.has_change_permission(None, movimiento))
        self.assertFalse(movement_admin.has_delete_permission(None))

        self.assertNotIn('sugerencia_asistida', unknown_income_admin.fields)
        self.assertIn('sugerencia_asistida_redacted', unknown_income_admin.fields)
        self.assertNotIn('sugerencia_asistida', unknown_income_admin.search_fields)
        suggestion = unknown_income_admin.sugerencia_asistida_redacted(ingreso)
        self.assertEqual(suggestion['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(suggestion['callback_url'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(suggestion['payment_candidate_ids'], [1])
        self.assertTrue(set(unknown_income_admin.fields).issubset(set(unknown_income_admin.readonly_fields)))
        self.assertFalse(unknown_income_admin.has_add_permission(None))
        self.assertFalse(unknown_income_admin.has_change_permission(None, ingreso))
        self.assertFalse(unknown_income_admin.has_delete_permission(None))

        for raw_field in ('evidencia_cuadratura_ref', 'responsable_ref', 'rationale'):
            self.assertNotIn(raw_field, balance_admin.fields)
            self.assertNotIn(raw_field, balance_admin.search_fields)
        self.assertEqual(balance_admin.evidencia_cuadratura_ref_redacted(cuadratura), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(balance_admin.responsable_ref_redacted(cuadratura), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(balance_admin.rationale_redacted(cuadratura), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(balance_admin.fields).issubset(set(balance_admin.readonly_fields)))
        self.assertFalse(balance_admin.has_add_permission(None))
        self.assertFalse(balance_admin.has_change_permission(None, cuadratura))
        self.assertFalse(balance_admin.has_delete_permission(None))

        for raw_field in (
            'criterio_conciliacion',
            'evidencia_transferencia_ref',
            'responsable_ref',
            'rationale',
        ):
            self.assertNotIn(raw_field, transfer_admin.fields)
            self.assertNotIn(raw_field, transfer_admin.search_fields)
        self.assertEqual(transfer_admin.criterio_conciliacion_redacted(transferencia), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(transfer_admin.evidencia_transferencia_ref_redacted(transferencia), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(transfer_admin.responsable_ref_redacted(transferencia), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(transfer_admin.rationale_redacted(transferencia), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(transfer_admin.fields).issubset(set(transfer_admin.readonly_fields)))
        self.assertFalse(transfer_admin.has_add_permission(None))
        self.assertFalse(transfer_admin.has_change_permission(None, transferencia))
        self.assertFalse(transfer_admin.has_delete_permission(None))

    def test_auth_is_required_for_conciliacion_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('conciliacion-conexion-list'),
            reverse('conciliacion-movimiento-list'),
            reverse('conciliacion-ingreso-list'),
            reverse('conciliacion-cuadratura-list'),
        ]
        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_can_create_square_balance_record(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BALANCE-SQUARE')

        response = self.client.post(
            reverse('conciliacion-cuadratura-list'),
            {
                'cuenta_recaudadora': cuenta.pk,
                'periodo_economico': '2026-01',
                'fecha_cuadratura': '2026-01-31',
                'saldo_sistema_clp': '1000000.00',
                'saldo_banco_clp': '1000000.00',
                'estado': 'cuadrada',
                'evidencia_cuadratura_ref': 'balance-square-controlled-2026-01',
                'responsable_ref': 'stage3-balance-owner',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['diferencia_clp'], '0.00')
        self.assertTrue(
            CuadraturaBancaria.objects.filter(
                cuenta_recaudadora=cuenta,
                periodo_economico='2026-01',
                diferencia_clp='0.00',
                estado='cuadrada',
            ).exists()
        )

    def test_balance_square_rejects_nonzero_difference_as_squared(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BALANCE-DIFF')

        response = self.client.post(
            reverse('conciliacion-cuadratura-list'),
            {
                'cuenta_recaudadora': cuenta.pk,
                'periodo_economico': '2026-01',
                'fecha_cuadratura': '2026-01-31',
                'saldo_sistema_clp': '1000000.00',
                'saldo_banco_clp': '999990.00',
                'estado': 'cuadrada',
                'evidencia_cuadratura_ref': 'balance-square-controlled-2026-01',
                'responsable_ref': 'stage3-balance-owner',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertFalse(CuadraturaBancaria.objects.filter(cuenta_recaudadora=cuenta).exists())

    def test_balance_square_rejects_period_date_mismatch(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BALANCE-PERIOD')

        response = self.client.post(
            reverse('conciliacion-cuadratura-list'),
            {
                'cuenta_recaudadora': cuenta.pk,
                'periodo_economico': '2026-01',
                'fecha_cuadratura': '2026-02-01',
                'saldo_sistema_clp': '1000000.00',
                'saldo_banco_clp': '1000000.00',
                'estado': 'cuadrada',
                'evidencia_cuadratura_ref': 'balance-square-controlled-2026-01',
                'responsable_ref': 'stage3-balance-owner',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodo_economico', response.data)
        self.assertFalse(CuadraturaBancaria.objects.filter(cuenta_recaudadora=cuenta).exists())

    def test_balance_square_rejects_sensitive_evidence(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BALANCE-SENSITIVE')

        response = self.client.post(
            reverse('conciliacion-cuadratura-list'),
            {
                'cuenta_recaudadora': cuenta.pk,
                'periodo_economico': '2026-01',
                'fecha_cuadratura': '2026-01-31',
                'saldo_sistema_clp': '1000000.00',
                'saldo_banco_clp': '1000000.00',
                'estado': 'cuadrada',
                'evidencia_cuadratura_ref': 'https://bank.example.test/balance?token=secret',
                'responsable_ref': 'stage3-balance-owner',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_cuadratura_ref', response.data)
        self.assertFalse(CuadraturaBancaria.objects.filter(cuenta_recaudadora=cuenta).exists())

    def test_balance_square_rejects_sensitive_rationale(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BALANCE-RATIONALE')

        response = self.client.post(
            reverse('conciliacion-cuadratura-list'),
            {
                'cuenta_recaudadora': cuenta.pk,
                'periodo_economico': '2026-01',
                'fecha_cuadratura': '2026-01-31',
                'saldo_sistema_clp': '1000000.00',
                'saldo_banco_clp': '999990.00',
                'estado': 'diferencia_explicada',
                'evidencia_cuadratura_ref': 'balance-square-controlled-2026-01',
                'responsable_ref': 'stage3-balance-owner',
                'rationale': 'Diferencia revisada en https://bank.example.test/balance?token=secret',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rationale', response.data)
        self.assertFalse(CuadraturaBancaria.objects.filter(cuenta_recaudadora=cuenta).exists())

    def test_active_bank_connection_requires_readiness_references(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BANK-GATE')

        response = self.client.post(
            reverse('conciliacion-conexion-list'),
            {
                'cuenta_recaudadora': cuenta.id,
                'provider_key': 'banco_de_chile',
                'credencial_ref': 'cred-bank',
                'estado_conexion': 'activa',
                'primaria_movimientos': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_gate_ref', response.data)
        self.assertIn('prueba_conectividad_ref', response.data)
        self.assertIn('prueba_movimientos_ref', response.data)

    def test_active_bank_connection_rejects_sensitive_references(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BANK-SENSITIVE')

        response = self.client.post(
            reverse('conciliacion-conexion-list'),
            {
                'cuenta_recaudadora': cuenta.id,
                'provider_key': 'banco_de_chile',
                'credencial_ref': 'https://bank.example.test/token/secret',
                'evidencia_gate_ref': 'bank-gate-controlled',
                'prueba_conectividad_ref': 'connectivity-controlled',
                'prueba_movimientos_ref': 'movements-controlled',
                'estado_conexion': 'activa',
                'primaria_movimientos': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('credencial_ref', response.data)

    def test_bank_connection_api_redacts_existing_sensitive_references(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-BANK-REDACT')
        ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='https://bank.example.test/token/secret',
            evidencia_gate_ref='bank-gate-token-secret',
            prueba_conectividad_ref='connectivity-controlled',
            prueba_movimientos_ref='movements-controlled',
            estado_conexion='activa',
            primaria_movimientos=True,
        )

        response = self.client.get(reverse('conciliacion-conexion-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data)
        self.assertEqual(response.data[0]['credencial_ref'], '<redacted-sensitive-reference>')
        self.assertEqual(response.data[0]['evidencia_gate_ref'], '<redacted-sensitive-reference>')
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_conciliacion_snapshot_redacts_existing_sensitive_credential_ref(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-SNAPSHOT-REDACT')
        ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='https://bank.example.test/token/secret',
            evidencia_gate_ref='bank-gate-controlled',
            prueba_conectividad_ref='connectivity-controlled',
            prueba_movimientos_ref='movements-controlled',
            estado_conexion='activa',
            primaria_movimientos=True,
        )

        response = self.client.get(reverse('conciliacion-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data)
        self.assertEqual(response.data['conexiones'][0]['credencial_ref'], '<redacted-sensitive-reference>')
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_conciliacion_snapshot_redacts_existing_sensitive_balance_square_refs(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-SNAPSHOT-BALANCE-REDACT')
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura='2026-01-31',
            saldo_sistema_clp='1000000.00',
            saldo_banco_clp='1000000.00',
            estado='cuadrada',
            evidencia_cuadratura_ref='https://bank.example.test/balance?token=secret',
            responsable_ref='stage3-balance-owner',
            rationale='Cuadratura revisada en https://bank.example.test/balance?token=secret',
        )

        response = self.client.get(reverse('conciliacion-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data, default=str)
        self.assertEqual(
            response.data['cuadraturas_bancarias'][0]['evidencia_cuadratura_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            response.data['cuadraturas_bancarias'][0]['rationale'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_balance_square_list_redacts_existing_sensitive_rationale(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-LIST-BALANCE-REDACT')
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura='2026-01-31',
            saldo_sistema_clp='1000000.00',
            saldo_banco_clp='1000000.00',
            estado='cuadrada',
            evidencia_cuadratura_ref='balance-square-controlled-2026-01',
            responsable_ref='stage3-balance-owner',
            rationale='Cuadratura revisada en https://bank.example.test/balance?token=secret',
        )

        response = self.client.get(reverse('conciliacion-cuadratura-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data, default=str)
        self.assertEqual(response.data[0]['rationale'], REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_manual_bank_movement_requires_import_evidence(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-MANUAL-GATE')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(conexion, evidencia_importacion_ref=''),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_importacion_ref', response.data)

    def test_manual_bank_movement_rejects_sensitive_import_evidence(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-MANUAL-SENSITIVE')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                evidencia_importacion_ref='https://bank.example.test/import?token=secret',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_importacion_ref', response.data)

    def test_bank_movement_rejects_sensitive_reference(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-MOV-REF-SENSITIVE')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                referencia='https://bank.example.test/reference?token=secret',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('referencia', response.data)

    def test_bank_movement_api_redacts_existing_sensitive_references(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-MOV-REDACT')
        conexion = self._create_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Movimiento con refs heredadas',
            origen_importacion='provider_sync',
            evidencia_importacion_ref='https://bank.example.test/import?token=secret',
            referencia='https://bank.example.test/reference?token=secret',
            transaction_id_banco='https://bank.example.test/tx?token=secret',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )

        response = self.client.get(reverse('conciliacion-movimiento-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data)
        self.assertEqual(response.data[0]['evidencia_importacion_ref'], '<redacted-sensitive-reference>')
        self.assertEqual(response.data[0]['referencia'], '<redacted-sensitive-reference>')
        self.assertEqual(response.data[0]['transaction_id_banco'], '<redacted-sensitive-reference>')
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_bank_movement_admin_notes_reject_and_redact_sensitive_values(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-MOV-NOTES-REDACT')
        conexion = self._create_connection(cuenta)
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Movimiento con notas heredadas',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )
        MovimientoBancarioImportado.objects.filter(pk=movimiento.pk).update(
            notas_admin='Revision interna en https://bank.example.test/note?token=secret',
        )
        movimiento.refresh_from_db()

        list_response = self.client.get(reverse('conciliacion-movimiento-list'))
        detail_response = self.client.get(reverse('conciliacion-movimiento-detail', args=[movimiento.pk]))
        create_response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                notas_admin='Revision en https://bank.example.test/note?token=secret',
            ),
            format='json',
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['notas_admin'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['notas_admin'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('notas_admin', create_response.data)
        rendered = json.dumps({'list': list_response.data, 'detail': detail_response.data}, default=str)
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

        movement_admin = MovimientoBancarioImportadoAdmin(MovimientoBancarioImportado, AdminSite())
        self.assertNotIn('notas_admin', movement_admin.fields)
        self.assertEqual(movement_admin.notas_admin_redacted(movimiento), REDACTED_SENSITIVE_REFERENCE)

    def test_bank_snapshot_redacts_sensitive_movement_reference(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-MOV-SNAP-REDACT')
        conexion = self._create_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Movimiento con referencia heredada',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            referencia='https://bank.example.test/reference?token=secret',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )

        response = self.client.get(reverse('conciliacion-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data, default=str)
        self.assertEqual(response.data['movimientos'][0]['referencia'], '<redacted-sensitive-reference>')
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_unknown_income_api_and_snapshot_redact_sensitive_assisted_suggestion(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-UNK-SUG-REDACT')
        conexion = self._create_connection(cuenta)
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Ingreso desconocido con sugerencia heredada',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            estado_conciliacion=EstadoConciliacionMovimiento.UNKNOWN_INCOME,
        )
        IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto=movimiento.monto,
            fecha_movimiento=movimiento.fecha_movimiento,
            descripcion_origen=movimiento.descripcion_origen,
            estado='pendiente_revision',
            sugerencia_asistida={
                'payment_candidate_ids': [101],
                'authorization': 'opaque-authorization-value',
                'nested': {'private_key': 'opaque-private-key-value'},
                'callback': 'https://bank.example.test/suggestion?token=secret',
            },
        )

        list_response = self.client.get(reverse('conciliacion-ingreso-list'))
        snapshot_response = self.client.get(reverse('conciliacion-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        list_suggestion = list_response.data[0]['sugerencia_asistida']
        snapshot_suggestion = snapshot_response.data['ingresos_desconocidos'][0]['sugerencia_asistida']
        for suggestion in (list_suggestion, snapshot_suggestion):
            self.assertEqual(suggestion['payment_candidate_ids'], [101])
            self.assertEqual(suggestion['authorization'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(suggestion['nested']['private_key'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(suggestion['callback'], REDACTED_SENSITIVE_REFERENCE)
        rendered = json.dumps({'list': list_response.data, 'snapshot': snapshot_response.data}, default=str)
        self.assertNotIn('opaque-authorization-value', rendered)
        self.assertNotIn('opaque-private-key-value', rendered)
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_provider_sync_requires_primary_bank_readiness(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-PROVIDER-GATE')
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='',
            estado_conexion='verificando',
        )

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                origen_importacion='provider_sync',
                evidencia_importacion_ref='',
                transaction_id_banco='bank-provider-not-ready-001',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('conexion_bancaria', response.data)

    def test_provider_sync_rejects_sensitive_transaction_id(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-PROVIDER-SENSITIVE')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                origen_importacion='provider_sync',
                evidencia_importacion_ref='',
                transaction_id_banco='https://bank.example.test/tx?token=secret',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('transaction_id_banco', response.data)

    def test_provider_sync_with_ready_connection_can_match_payment(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-PROVIDER-OK', amount='100111.00')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                origen_importacion='provider_sync',
                evidencia_importacion_ref='',
                transaction_id_banco='bank-provider-ready-001',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        pago.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)

    def test_exact_match_payment_marks_payment_as_paid(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-PAY', amount='100111.00')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(conexion),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        pago.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(pago.dias_mora, 3)

    def test_exact_match_payment_requires_same_economic_period(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-PAY-PERIOD', amount='100111.00')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(conexion, fecha_movimiento='2026-02-08'),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        pago.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertIsNone(movimiento.pago_mensual_id)
        self.assertEqual(pago.estado_pago, EstadoPago.PENDING)
        self.assertTrue(IngresoDesconocido.objects.filter(movimiento_bancario=movimiento).exists())

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
            self._movement_payload(
                conexion,
                fecha_movimiento='2027-01-15',
                monto='15000.00',
                descripcion_origen='Cobranza residual',
                referencia=residual.referencia_visible,
            ),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        residual.refresh_from_db()
        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        self.assertEqual(residual.estado, EstadoCobroResidual.PAID)
        self.assertEqual(residual.saldo_actual, 0)
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)

    def test_exact_match_residual_requires_same_account(self):
        cuenta, _, contrato = self._create_contract_and_payment(codigo='REC-RES-ACC')
        other_account = self._create_secondary_account(codigo='REC-RES-OTHER')
        conexion = self._create_connection(other_account, provider='banco_estado')
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
            self._movement_payload(
                conexion,
                fecha_movimiento='2027-01-15',
                monto='15000.00',
                descripcion_origen='Cobranza residual otra cuenta',
                referencia=residual.referencia_visible,
            ),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        residual.refresh_from_db()
        movimiento = MovimientoBancarioImportado.objects.get(pk=response.data['id'])
        self.assertEqual(residual.estado, EstadoCobroResidual.ACTIVE)
        self.assertEqual(residual.saldo_actual, Decimal('15000.00'))
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertIsNone(movimiento.codigo_cobro_residual_id)
        self.assertTrue(IngresoDesconocido.objects.filter(movimiento_bancario=movimiento).exists())

    def test_unmatched_income_creates_ingreso_desconocido_and_manual_resolution(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-UNK')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='999999.00',
                descripcion_origen='Abono desconocido',
            ),
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

    def test_unknown_income_full_clean_rejects_snapshot_mismatch(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-UNK-MISMATCH')
        conexion = self._create_connection(cuenta)
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Abono desconocido',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            estado_conciliacion=EstadoConciliacionMovimiento.UNKNOWN_INCOME,
        )
        ingreso = IngresoDesconocido(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto='100112.00',
            fecha_movimiento=movimiento.fecha_movimiento,
            descripcion_origen=movimiento.descripcion_origen,
            estado='pendiente_revision',
        )

        with self.assertRaises(ValidationError) as error:
            ingreso.full_clean()

        self.assertIn('monto', error.exception.message_dict)

    def test_exact_match_payment_full_clean_rejects_snapshot_mismatch(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-EXACT-MISMATCH')
        conexion = self._create_connection(cuenta)
        pago.estado_pago = EstadoPago.PAID
        pago.monto_pagado_clp = '100111.00'
        pago.fecha_deposito_banco = '2026-01-08'
        pago.save(update_fields=['estado_pago', 'monto_pagado_clp', 'fecha_deposito_banco', 'updated_at'])
        movimiento = MovimientoBancarioImportado(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100112.00',
            descripcion_origen='Pago conciliado inconsistente',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=pago,
        )

        with self.assertRaises(ValidationError) as error:
            movimiento.full_clean()

        self.assertIn('pago_mensual', error.exception.message_dict)

    def test_exact_match_payment_full_clean_rejects_period_mismatch(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-EXACT-PERIOD')
        conexion = self._create_connection(cuenta)
        pago.estado_pago = EstadoPago.PAID
        pago.monto_pagado_clp = '100111.00'
        pago.fecha_deposito_banco = '2026-02-08'
        pago.save(update_fields=['estado_pago', 'monto_pagado_clp', 'fecha_deposito_banco', 'updated_at'])
        movimiento = MovimientoBancarioImportado(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-02-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Pago conciliado fuera de periodo',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=pago,
        )

        with self.assertRaises(ValidationError) as error:
            movimiento.full_clean()

        self.assertIn('pago_mensual', error.exception.message_dict)
        self.assertIn('periodo', ' '.join(error.exception.message_dict['pago_mensual']).lower())

    def test_bank_movement_full_clean_rejects_duplicate_transaction_id_per_connection(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-DUP-TX-MODEL')
        conexion = self._create_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Pago con tx original',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            transaction_id_banco='tx-model-dup-001',
        )
        duplicate = MovimientoBancarioImportado(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-09',
            tipo_movimiento='abono',
            monto='100112.00',
            descripcion_origen='Pago con tx duplicado',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            transaction_id_banco='tx-model-dup-001',
        )

        with self.assertRaises(ValidationError) as error:
            duplicate.full_clean()

        self.assertIn('transaction_id_banco', error.exception.message_dict)

    def test_bank_movement_db_rejects_duplicate_transaction_id_per_connection(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-DUP-TX-DB')
        conexion = self._create_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='100111.00',
            descripcion_origen='Pago con tx original',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-import-controlled',
            transaction_id_banco='tx-db-dup-001',
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MovimientoBancarioImportado.objects.create(
                    conexion_bancaria=conexion,
                    fecha_movimiento='2026-01-09',
                    tipo_movimiento='abono',
                    monto='100112.00',
                    descripcion_origen='Pago con tx duplicado',
                    origen_importacion='manual_controlada',
                    evidencia_importacion_ref='manual-import-controlled',
                    transaction_id_banco='tx-db-dup-001',
                )

    def test_rejects_duplicate_transaction_id_banco_per_connection(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-DUP-TX')
        conexion = self._create_connection(cuenta)

        first = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                descripcion_origen='Pago duplicado 1',
                transaction_id_banco='tx-dup-001',
            ),
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        second = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                descripcion_origen='Pago duplicado 2',
                transaction_id_banco='tx-dup-001',
            ),
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('transaction_id_banco', second.data)

    def test_debit_movement_requires_manual_resolution(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO')
        conexion = self._create_connection(cuenta)

        response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario',
            ),
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

    def test_manual_resolution_can_classify_charge_and_generate_accounting_event(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO-RES')
        conexion = self._create_connection(cuenta)
        self._setup_contabilidad_for_company(cuenta.empresa_owner)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario clasificado manualmente',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[resolution.pk]),
            self._charge_classification_payload(cuenta, rationale='Comision bancaria del periodo.'),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_200_OK)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        event = EventoContable.objects.get(pk=resolve.data['evento_contable_id'])
        asiento = AsientoContable.objects.get(evento_contable=event)

        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(movimiento.notas_admin, 'Comision bancaria del periodo.')
        self.assertEqual(event.evento_tipo, 'ComisionBancaria')
        self.assertEqual(event.payload_resumen['categoria_movimiento'], 'comision_bancaria')
        self.assertEqual(event.payload_resumen['entidad_afectada_tipo'], 'empresa')
        self.assertEqual(event.payload_resumen['entidad_afectada_id'], cuenta.empresa_owner_id)
        self.assertEqual(event.payload_resumen['periodo_economico'], '2026-01')
        self.assertEqual(event.payload_resumen['evidencia_clasificacion_ref'], 'bank-fee-statement-2026-01')
        self.assertEqual(event.estado_contable, 'contabilizado')
        self.assertEqual(str(asiento.debe_total), '50000.00')
        self.assertEqual(str(asiento.haber_total), '50000.00')
        self.assertEqual(asiento.movimientos.count(), 2)
        self.assertEqual(resolution.status, 'resolved')
        self.assertEqual(resolution.metadata['resolved_event_id'], event.pk)
        self.assertEqual(resolution.metadata['categoria_movimiento'], 'comision_bancaria')
        self.assertEqual(resolution.metadata['periodo_economico'], '2026-01')

    def test_manual_resolution_charge_requires_rationale(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO-REASON')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario sin motivo',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[resolution.pk]),
            self._charge_classification_payload(cuenta, rationale='   '),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rationale', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(resolution.status, 'open')
        self.assertEqual(resolution.rationale, '')

    def test_manual_resolution_charge_requires_classification_context(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO-CONTEXT')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario sin contexto de clasificacion',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[resolution.pk]),
            {'rationale': 'Cargo revisado por administracion.'},
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('categoria_movimiento', resolve.data)
        self.assertIn('entidad_afectada_tipo', resolve.data)
        self.assertIn('entidad_afectada_id', resolve.data)
        self.assertIn('periodo_economico', resolve.data)
        self.assertIn('criterio_reparto', resolve.data)
        self.assertIn('evidencia_clasificacion_ref', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(resolution.status, 'open')

    def test_manual_resolution_charge_requires_period_matching_movement_month(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO-PERIOD')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario con periodo economico desalineado',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[resolution.pk]),
            self._charge_classification_payload(cuenta, periodo_economico='2026-02'),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            resolve.data['detail'],
            'El periodo economico del cargo debe coincidir con el mes del movimiento bancario.',
        )

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(resolution.status, 'open')
        self.assertFalse(EventoContable.objects.exists())

    def test_manual_resolution_charge_rejects_sensitive_classification_evidence(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO-SENSITIVE')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario con evidencia sensible',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[resolution.pk]),
            self._charge_classification_payload(
                cuenta,
                evidencia_clasificacion_ref='https://bank.example.test/fee?token=secret',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_clasificacion_ref', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(resolution.status, 'open')

    def test_manual_resolution_charge_rejects_sensitive_context(self):
        cuenta, _, _ = self._create_contract_and_payment(codigo='REC-CARGO-CONTEXT-SENSITIVE')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                fecha_movimiento='2026-01-09',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Cargo bancario con contexto sensible',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[resolution.pk]),
            self._charge_classification_payload(
                cuenta,
                criterio_reparto='Criterio revisado en https://bank.example.test/fee?token=secret',
                rationale='Motivo recibido desde ops@example.test con token bancario.',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('criterio_reparto', resolve.data)
        self.assertIn('rationale', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(resolution.status, 'open')

    def test_manual_resolution_can_register_internal_transfer_pair(self):
        cuenta_origen, _, _ = self._create_contract_and_payment(codigo='REC-TRANSFER')
        cuenta_destino = self._create_secondary_account('REC-TRANSFER')
        conexion_origen = self._create_connection(cuenta_origen, provider='banco_origen_transfer')
        conexion_destino = self._create_connection(cuenta_destino, provider='banco_destino_transfer')

        create_debit = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion_origen,
                fecha_movimiento='2026-01-10',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Transferencia enviada a cuenta destino',
            ),
            format='json',
        )
        self.assertEqual(create_debit.status_code, status.HTTP_201_CREATED)

        create_credit = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion_destino,
                fecha_movimiento='2026-01-10',
                tipo_movimiento='abono',
                monto='50000.00',
                descripcion_origen='Transferencia recibida desde cuenta origen',
            ),
            format='json',
        )
        self.assertEqual(create_credit.status_code, status.HTTP_201_CREATED)

        movimiento_origen = MovimientoBancarioImportado.objects.get(pk=create_debit.data['id'])
        movimiento_destino = MovimientoBancarioImportado.objects.get(pk=create_credit.data['id'])
        origin_resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento_origen.pk),
        )
        destination_resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento_destino.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-internal-transfer', args=[origin_resolution.pk]),
            self._internal_transfer_payload(movimiento_destino),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_200_OK)

        transferencia = TransferenciaIntercuenta.objects.get(pk=resolve.data['transferencia_intercuenta_id'])
        movimiento_origen.refresh_from_db()
        movimiento_destino.refresh_from_db()
        origin_resolution.refresh_from_db()
        destination_resolution.refresh_from_db()
        ingreso = IngresoDesconocido.objects.get(movimiento_bancario=movimiento_destino)

        self.assertEqual(movimiento_origen.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(movimiento_destino.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(ingreso.estado, 'resuelto')
        self.assertEqual(transferencia.movimiento_origen_id, movimiento_origen.pk)
        self.assertEqual(transferencia.movimiento_destino_id, movimiento_destino.pk)
        self.assertEqual(transferencia.entidad_origen_tipo, cuenta_origen.owner_tipo)
        self.assertEqual(transferencia.entidad_origen_id, cuenta_origen.owner_id)
        self.assertEqual(transferencia.entidad_destino_tipo, cuenta_destino.owner_tipo)
        self.assertEqual(transferencia.entidad_destino_id, cuenta_destino.owner_id)
        self.assertEqual(origin_resolution.status, 'resolved')
        self.assertEqual(origin_resolution.metadata['categoria_movimiento'], 'transferencia_interna')
        self.assertEqual(origin_resolution.metadata['transferencia_intercuenta_id'], transferencia.pk)
        self.assertEqual(destination_resolution.status, ManualResolution.Status.SUPERSEDED)
        self.assertEqual(destination_resolution.metadata['superseded_match_type'], 'internal_transfer')

        snapshot = self.client.get(reverse('conciliacion-snapshot'))
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.data['transferencias_intercuenta'][0]['id'], transferencia.pk)

    def test_manual_resolution_internal_transfer_rejects_sensitive_evidence(self):
        cuenta_origen, _, _ = self._create_contract_and_payment(codigo='REC-TRANSFER-SENSITIVE')
        cuenta_destino = self._create_secondary_account('REC-TRANSFER-SENSITIVE')
        conexion_origen = self._create_connection(cuenta_origen, provider='banco_origen_sensitive')
        conexion_destino = self._create_connection(cuenta_destino, provider='banco_destino_sensitive')
        create_debit = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion_origen,
                fecha_movimiento='2026-01-10',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Transferencia enviada con evidencia sensible',
            ),
            format='json',
        )
        create_credit = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion_destino,
                fecha_movimiento='2026-01-10',
                tipo_movimiento='abono',
                monto='50000.00',
                descripcion_origen='Transferencia recibida con evidencia sensible',
            ),
            format='json',
        )
        self.assertEqual(create_debit.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_credit.status_code, status.HTTP_201_CREATED)
        movimiento_origen = MovimientoBancarioImportado.objects.get(pk=create_debit.data['id'])
        movimiento_destino = MovimientoBancarioImportado.objects.get(pk=create_credit.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento_origen.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-internal-transfer', args=[resolution.pk]),
            self._internal_transfer_payload(
                movimiento_destino,
                evidencia_transferencia_ref='https://bank.example.test/transfer?token=secret',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_transferencia_ref', resolve.data)
        movimiento_origen.refresh_from_db()
        movimiento_destino.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento_origen.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(movimiento_destino.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertEqual(resolution.status, 'open')
        self.assertFalse(TransferenciaIntercuenta.objects.exists())

    def test_manual_resolution_internal_transfer_rejects_sensitive_context(self):
        cuenta_origen, _, _ = self._create_contract_and_payment(codigo='REC-TRANSFER-CONTEXT-SENSITIVE')
        cuenta_destino = self._create_secondary_account('REC-TRANSFER-CONTEXT-SENSITIVE')
        conexion_origen = self._create_connection(cuenta_origen, provider='banco_origen_context_sensitive')
        conexion_destino = self._create_connection(cuenta_destino, provider='banco_destino_context_sensitive')
        create_debit = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion_origen,
                fecha_movimiento='2026-01-10',
                tipo_movimiento='cargo',
                monto='50000.00',
                descripcion_origen='Transferencia enviada con contexto sensible',
            ),
            format='json',
        )
        create_credit = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion_destino,
                fecha_movimiento='2026-01-10',
                tipo_movimiento='abono',
                monto='50000.00',
                descripcion_origen='Transferencia recibida con contexto sensible',
            ),
            format='json',
        )
        self.assertEqual(create_debit.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_credit.status_code, status.HTTP_201_CREATED)
        movimiento_origen = MovimientoBancarioImportado.objects.get(pk=create_debit.data['id'])
        movimiento_destino = MovimientoBancarioImportado.objects.get(pk=create_credit.data['id'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.movimiento_cargo',
            scope_reference=str(movimiento_origen.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-internal-transfer', args=[resolution.pk]),
            self._internal_transfer_payload(
                movimiento_destino,
                criterio_conciliacion='Criterio en https://bank.example.test/transfer?token=secret',
                rationale='Motivo enviado por ops@example.test con token bancario.',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('criterio_conciliacion', resolve.data)
        self.assertIn('rationale', resolve.data)
        movimiento_origen.refresh_from_db()
        movimiento_destino.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento_origen.estado_conciliacion, EstadoConciliacionMovimiento.MANUAL_REQUIRED)
        self.assertEqual(movimiento_destino.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertEqual(resolution.status, 'open')
        self.assertFalse(TransferenciaIntercuenta.objects.exists())

    def test_internal_transfer_list_and_snapshot_redact_existing_sensitive_context(self):
        cuenta_origen, _, _ = self._create_contract_and_payment(codigo='REC-TRANSFER-REDACT')
        cuenta_destino = self._create_secondary_account('REC-TRANSFER-REDACT')
        conexion_origen = self._create_connection(cuenta_origen, provider='banco_origen_redact')
        conexion_destino = self._create_connection(cuenta_destino, provider='banco_destino_redact')
        movimiento_origen = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion_origen,
            fecha_movimiento='2026-01-10',
            tipo_movimiento='cargo',
            monto=Decimal('50000.00'),
            descripcion_origen='Transferencia enviada heredada',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='internal-transfer-origin',
            estado_conciliacion=EstadoConciliacionMovimiento.MANUAL_REQUIRED,
        )
        movimiento_destino = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion_destino,
            fecha_movimiento='2026-01-10',
            tipo_movimiento='abono',
            monto=Decimal('50000.00'),
            descripcion_origen='Transferencia recibida heredada',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='internal-transfer-destination',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )
        transferencia = TransferenciaIntercuenta.objects.create(
            movimiento_origen=movimiento_origen,
            movimiento_destino=movimiento_destino,
            periodo_economico='2026-01',
            criterio_conciliacion='Criterio en https://bank.example.test/transfer?token=secret',
            evidencia_transferencia_ref='internal-transfer-controlled-2026-01',
            responsable_ref='stage3-transfer-owner',
            rationale='Motivo en https://bank.example.test/transfer?token=secret',
        )

        list_response = self.client.get(reverse('conciliacion-transferencia-list'))
        snapshot_response = self.client.get(reverse('conciliacion-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        rendered = json.dumps({'list': list_response.data, 'snapshot': snapshot_response.data}, default=str)
        self.assertEqual(list_response.data[0]['id'], transferencia.pk)
        self.assertEqual(list_response.data[0]['criterio_conciliacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(list_response.data[0]['rationale'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            snapshot_response.data['transferencias_intercuenta'][0]['criterio_conciliacion'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            snapshot_response.data['transferencias_intercuenta'][0]['rationale'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

    def test_retry_match_rejects_already_reconciled_movement(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-LOCKED', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                descripcion_origen='Pago ya conciliado',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)

        retry = self.client.post(
            reverse('conciliacion-movimiento-match', args=[movimiento.id]),
            format='json',
        )
        self.assertEqual(retry.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(retry.data['detail'], 'El movimiento ya fue conciliado y no admite reintento.')

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(movimiento.pago_mensual_id, pago.pk)
        self.assertFalse(IngresoDesconocido.objects.filter(movimiento_bancario=movimiento).exists())

    def test_retry_match_resolves_unknown_income_when_payment_appears(self):
        cuenta, _, contrato = self._create_contract_and_payment(codigo='REC-RETRY', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono temprano',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )

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
        resolution.refresh_from_db()
        ingreso = IngresoDesconocido.objects.get(movimiento_bancario=movimiento)
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(ingreso.estado, 'resuelto')
        self.assertEqual(resolution.status, ManualResolution.Status.SUPERSEDED)
        self.assertEqual(resolution.rationale, 'Supersedida porque el movimiento obtuvo match exacto con pago mensual trazable.')
        self.assertEqual(resolution.metadata['superseded_by'], 'conciliacion.exact_match')
        self.assertEqual(resolution.metadata['superseded_match_type'], 'payment')
        self.assertEqual(resolution.metadata['pago_mensual_id'], pago.pk)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='audit.manual_resolution.superseded',
                entity_type='manual_resolution',
                entity_id=str(resolution.pk),
                metadata__superseded_by='conciliacion.exact_match',
            ).exists()
        )

    def test_manual_resolution_can_regularize_unknown_income_to_selected_payment(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono requiere regularizacion manual',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        pago.monto_calculado_clp = '777777.00'
        pago.save(update_fields=['monto_calculado_clp'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )
        duplicate_resolution = ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Revision duplicada del mismo ingreso desconocido.',
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[resolution.pk]),
            self._unknown_income_resolution_payload(
                pago,
                criterio_aplicado='Saldo pendiente exacto validado contra movimiento bancario.',
                evidencia_regularizacion_ref='unknown-income-payment-match-2026-01',
            ),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_200_OK)

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        resolution.refresh_from_db()
        duplicate_resolution.refresh_from_db()
        ingreso = IngresoDesconocido.objects.get(movimiento_bancario=movimiento)

        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(movimiento.pago_mensual_id, pago.pk)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(str(pago.monto_pagado_clp), '777777.00')
        self.assertEqual(ingreso.estado, 'resuelto')
        self.assertEqual(resolution.status, 'resolved')
        self.assertEqual(resolution.rationale, 'Regularizado manualmente contra el pago correcto.')
        self.assertEqual(resolution.metadata['resolved_payment_id'], pago.pk)
        self.assertEqual(resolution.metadata['periodo_economico'], '2026-01')
        self.assertEqual(resolution.metadata['criterio_aplicado'], 'Saldo pendiente exacto validado contra movimiento bancario.')
        self.assertEqual(resolution.metadata['evidencia_regularizacion_ref'], 'unknown-income-payment-match-2026-01')
        self.assertEqual(duplicate_resolution.status, ManualResolution.Status.SUPERSEDED)
        self.assertEqual(duplicate_resolution.metadata['superseded_by'], 'conciliacion.manual_resolution')
        self.assertEqual(duplicate_resolution.metadata['superseded_by_resolution_id'], str(resolution.pk))

    def test_manual_resolution_unknown_income_requires_matching_economic_period(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-PERIOD', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono con periodo economico inconsistente',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        pago.monto_calculado_clp = '777777.00'
        pago.save(update_fields=['monto_calculado_clp'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[resolution.pk]),
            self._unknown_income_resolution_payload(
                pago,
                periodo_economico='2026-02',
                rationale='Intento con periodo economico incorrecto.',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            resolve.data['detail'],
            'El periodo economico debe coincidir con el mes y anio del pago mensual seleccionado.',
        )

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertIsNone(movimiento.pago_mensual_id)
        self.assertEqual(pago.estado_pago, EstadoPago.PENDING)
        self.assertEqual(str(pago.monto_pagado_clp), '0.00')
        self.assertEqual(resolution.status, ManualResolution.Status.OPEN)

    def test_manual_resolution_unknown_income_requires_rationale(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-REASON', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono sin motivo de regularizacion',
            ),
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
            self._unknown_income_resolution_payload(pago, rationale=''),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rationale', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertEqual(resolution.status, 'open')
        self.assertEqual(resolution.rationale, '')

    def test_manual_resolution_unknown_income_requires_resolution_context(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-CONTEXT', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono sin contexto de regularizacion',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        pago.monto_calculado_clp = '777777.00'
        pago.save(update_fields=['monto_calculado_clp'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[resolution.pk]),
            {
                'pago_mensual_id': pago.pk,
                'rationale': 'Regularizacion revisada por administracion.',
            },
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodo_economico', resolve.data)
        self.assertIn('criterio_aplicado', resolve.data)
        self.assertIn('evidencia_regularizacion_ref', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertEqual(resolution.status, 'open')

    def test_manual_resolution_unknown_income_rejects_sensitive_resolution_evidence(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-SENSITIVE', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono con evidencia sensible',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        pago.monto_calculado_clp = '777777.00'
        pago.save(update_fields=['monto_calculado_clp'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[resolution.pk]),
            self._unknown_income_resolution_payload(
                pago,
                evidencia_regularizacion_ref='https://bank.example.test/income?token=secret',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_regularizacion_ref', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertEqual(resolution.status, 'open')

    def test_manual_resolution_unknown_income_rejects_sensitive_context(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-CONTEXT-SENSITIVE', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono con contexto sensible',
            ),
            format='json',
        )
        self.assertEqual(create_movement.status_code, status.HTTP_201_CREATED)

        movimiento = MovimientoBancarioImportado.objects.get(pk=create_movement.data['id'])
        pago.monto_calculado_clp = '777777.00'
        pago.save(update_fields=['monto_calculado_clp'])
        resolution = ManualResolution.objects.get(
            category='conciliacion.ingreso_desconocido',
            scope_reference=str(movimiento.pk),
        )

        resolve = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[resolution.pk]),
            self._unknown_income_resolution_payload(
                pago,
                criterio_aplicado='Criterio revisado en https://bank.example.test/income?token=secret',
                rationale='Motivo recibido desde ops@example.test con token bancario.',
            ),
            format='json',
        )

        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('criterio_aplicado', resolve.data)
        self.assertIn('rationale', resolve.data)

        movimiento.refresh_from_db()
        resolution.refresh_from_db()
        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertEqual(resolution.status, 'open')

    def test_manual_resolution_adds_unknown_income_to_existing_partial_payment(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-PARTIAL', amount='777777.00')
        conexion = self._create_connection(cuenta)
        pago.monto_pagado_clp = '100000.00'
        pago.save(update_fields=['monto_pagado_clp'])

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='677777.00',
                descripcion_origen='Abono complementario requiere regularizacion manual',
            ),
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
            self._unknown_income_resolution_payload(pago, rationale='Regularizado contra saldo pendiente parcial.'),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_200_OK)

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        resolution.refresh_from_db()

        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.EXACT_MATCH)
        self.assertEqual(movimiento.pago_mensual_id, pago.pk)
        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(str(pago.monto_pagado_clp), '777777.00')
        self.assertEqual(resolution.status, 'resolved')

    def test_manual_resolution_rejects_unknown_income_when_amount_exceeds_pending_payment(self):
        cuenta, pago, _ = self._create_contract_and_payment(codigo='REC-MANUAL-FAIL', amount='100111.00')
        conexion = self._create_connection(cuenta)

        create_movement = self.client.post(
            reverse('conciliacion-movimiento-list'),
            self._movement_payload(
                conexion,
                monto='777777.00',
                descripcion_origen='Abono sobredimensionado',
            ),
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
            self._unknown_income_resolution_payload(pago, rationale='Intento invalido por diferencia de monto.'),
            format='json',
        )
        self.assertEqual(resolve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            resolve.data['detail'],
            'El monto del movimiento debe coincidir exactamente con el saldo pendiente del pago seleccionado.',
        )

        movimiento.refresh_from_db()
        pago.refresh_from_db()
        resolution.refresh_from_db()
        ingreso = IngresoDesconocido.objects.get(movimiento_bancario=movimiento)

        self.assertEqual(movimiento.estado_conciliacion, EstadoConciliacionMovimiento.UNKNOWN_INCOME)
        self.assertIsNone(movimiento.pago_mensual_id)
        self.assertEqual(pago.estado_pago, EstadoPago.PENDING)
        self.assertEqual(str(pago.monto_pagado_clp), '0.00')
        self.assertEqual(ingreso.estado, 'pendiente_revision')
        self.assertEqual(resolution.status, 'open')
