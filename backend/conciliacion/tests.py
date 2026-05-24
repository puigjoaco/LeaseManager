import json

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
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import CuadraturaBancaria, ConexionBancaria, EstadoConciliacionMovimiento, IngresoDesconocido, MovimientoBancarioImportado


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
        )

        response = self.client.get(reverse('conciliacion-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data, default=str)
        self.assertEqual(
            response.data['cuadraturas_bancarias'][0]['evidencia_cuadratura_ref'],
            '<redacted-sensitive-reference>',
        )
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
            transaction_id_banco='https://bank.example.test/tx?token=secret',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )

        response = self.client.get(reverse('conciliacion-movimiento-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rendered = json.dumps(response.data)
        self.assertEqual(response.data[0]['evidencia_importacion_ref'], '<redacted-sensitive-reference>')
        self.assertEqual(response.data[0]['transaction_id_banco'], '<redacted-sensitive-reference>')
        self.assertNotIn('bank.example.test', rendered)
        self.assertNotIn('secret', rendered)

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
