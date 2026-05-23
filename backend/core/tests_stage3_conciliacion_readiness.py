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

from cobranza.models import EstadoPago, PagoMensual
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
from core.stage3_conciliacion_readiness import collect_stage3_conciliacion_readiness
from conciliacion.models import (
    ConexionBancaria,
    EstadoConciliacionMovimiento,
    EstadoConexionBancaria,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    OrigenImportacionMovimiento,
    TipoMovimientoBancario,
)
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble


class Stage3ConciliacionReadinessTests(TestCase):
    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='Empresa Stage3 SpA', rut='88888888-8'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', '11111111-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', '22222222-2')
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        return empresa

    def _create_payment_matrix(self, codigo='ST3-001', amount=Decimal('250000.00')):
        propietario = self._create_socio(f'Prop {codigo}', '33333333-3')
        empresa = self._create_active_empresa()
        propiedad = Propiedad.objects.create(
            direccion='Direccion Stage3 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=f'P-{codigo}'[:16],
            estado='activa',
            socio_owner=propietario,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Stage3',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_socio_owner=propietario,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario=TipoArrendatario.NATURAL,
            nombre_razon_social='Arrendatario Stage3',
            rut='44444444-4',
            email='tenant-stage3@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio Stage3',
            estado_contacto=EstadoContactoArrendatario.ACTIVE,
        )
        contrato = Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        period = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base=amount,
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        payment = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=period,
            mes=1,
            anio=2026,
            monto_facturable_clp=amount,
            monto_calculado_clp=amount,
            monto_pagado_clp=amount,
            fecha_vencimiento=date(2026, 1, 5),
            codigo_conciliacion_efectivo='111',
            estado_pago=EstadoPago.PAID,
        )
        return cuenta, payment

    def _create_ready_connection(self, cuenta):
        return ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_stage3',
            credencial_ref='bank-ref-stage3',
            evidencia_gate_ref='bank-gate-stage3',
            prueba_conectividad_ref='connectivity-stage3',
            prueba_movimientos_ref='movements-stage3',
            prueba_saldos_ref='balances-stage3',
            estado_conexion=EstadoConexionBancaria.ACTIVE,
            primaria_movimientos=True,
            primaria_saldos=True,
        )

    def _collect_with_final_refs(self):
        return collect_stage3_conciliacion_readiness(
            stage2_evidence_ref='stage2-readiness-controlled-v1',
            bank_proof_ref='bank-proof-controlled-v1',
            balance_square_ref='balance-square-controlled-v1',
            responsible_ref='stage3-responsibles-v1',
            source_label='stage3-controlled-v1',
            authorization_ref='stage3-authorization-v1',
            source_kind='snapshot_controlado',
        )

    def _create_reconciled_movement(self, conexion, payment):
        return MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Pago conciliado Stage3',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage3_conciliacion_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage3.source_kind_not_authorized', issue_codes)
        self.assertIn('stage3.bank_connection_missing', issue_codes)
        self.assertIn('stage3.movements_missing', issue_codes)
        self.assertIn('stage3.balance_square_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        cuenta, payment = self._create_payment_matrix()
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage3_conciliacion'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_matrix_and_non_sensitive_refs_cannot_close_readiness(self):
        cuenta, payment = self._create_payment_matrix()
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)

        result = collect_stage3_conciliacion_readiness(
            stage2_evidence_ref='stage2-readiness-controlled-v1',
            bank_proof_ref='bank-proof-controlled-v1',
            balance_square_ref='balance-square-controlled-v1',
            responsible_ref='stage3-responsibles-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage3.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        cuenta, payment = self._create_payment_matrix()
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)

        result = collect_stage3_conciliacion_readiness(
            stage2_evidence_ref='stage2-readiness-controlled-v1',
            bank_proof_ref='bank-proof-controlled-v1',
            balance_square_ref='balance-square-controlled-v1',
            responsible_ref='stage3-responsibles-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.source_label_missing', issue_codes)
        self.assertIn('stage3.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_provider_sync_without_transaction_or_ready_connection_is_blocking(self):
        cuenta, _ = self._create_payment_matrix(codigo='ST3-PROVIDER')
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_provider_stage3',
            credencial_ref='',
            estado_conexion=EstadoConexionBancaria.VERIFYING,
        )
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('250000.00'),
            descripcion_origen='Provider incompleto',
            origen_importacion=OrigenImportacionMovimiento.PROVIDER_SYNC,
        )

        result = collect_stage3_conciliacion_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.provider_sync_transaction_missing', issue_codes)
        self.assertIn('stage3.movement.provider_sync_connection_not_ready', issue_codes)

    def test_manual_import_without_evidence_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-MANUAL')
        conexion = self._create_ready_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Manual sin evidencia',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.manual_import_evidence_missing', issue_codes)

    def test_unresolved_movements_and_open_unknown_income_are_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN')
        conexion = self._create_ready_connection(cuenta)
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Ingreso desconocido',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.UNKNOWN_INCOME,
        )
        IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto=movimiento.monto,
            fecha_movimiento=movimiento.fecha_movimiento,
            descripcion_origen=movimiento.descripcion_origen,
            estado=EstadoIngresoDesconocido.OPEN,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movements_unresolved', issue_codes)
        self.assertIn('stage3.unknown_income_open', issue_codes)

    def test_reported_balance_continuity_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 9),
            tipo_movimiento=TipoMovimientoBancario.DEBIT,
            monto=Decimal('10000.00'),
            descripcion_origen='Cargo bancario controlado',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3-charge',
            saldo_reportado=Decimal('995000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_reported_continuity_mismatch', issue_codes)
        self.assertEqual(result['sections']['movements']['reported_balance_continuity_checks'], 1)

    def test_sensitive_final_refs_do_not_close_readiness(self):
        cuenta, payment = self._create_payment_matrix()
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)

        result = collect_stage3_conciliacion_readiness(
            stage2_evidence_ref='stage2-readiness-controlled-v1',
            bank_proof_ref='https://bank.example/proof',
            balance_square_ref='balance-square-controlled-v1',
            responsible_ref='stage3-responsibles-v1',
            source_kind='snapshot_controlado',
        )

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.bank_proof_ref_missing', {issue['code'] for issue in result['issues']})

    def test_sensitive_bank_connection_refs_are_blocking(self):
        cuenta, _ = self._create_payment_matrix(codigo='ST3-CONN-SENSITIVE')
        ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_stage3_sensitive',
            credencial_ref='https://bank.example.test/token/secret',
            evidencia_gate_ref='bank-gate-stage3',
            prueba_conectividad_ref='connectivity-stage3',
            prueba_movimientos_ref='movements-stage3',
            estado_conexion=EstadoConexionBancaria.ACTIVE,
            primaria_movimientos=True,
        )

        result = collect_stage3_conciliacion_readiness(
            stage2_evidence_ref='stage2-readiness-controlled-v1',
            bank_proof_ref='bank-proof-controlled-v1',
            balance_square_ref='balance-square-controlled-v1',
            responsible_ref='stage3-responsibles-v1',
            source_label='stage3-controlled-v1',
            authorization_ref='stage3-authorization-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.bank_connection.sensitive_reference', issue_codes)
        self.assertEqual(result['sections']['bank_connections']['sensitive_references'], 1)

    def test_sensitive_movement_refs_are_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-MOV-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Pago conciliado con evidencia sensible',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='https://bank.example.test/import?token=secret',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.sensitive_reference', issue_codes)
        self.assertEqual(result['sections']['movements']['sensitive_reference'], 1)

    def test_command_writes_json_and_rejects_versionable_repo_output(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage3_readiness.json'
            call_command('audit_stage3_conciliacion_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage3.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('bank_connections', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage3-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage3_conciliacion_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage3_conciliacion_readiness', fail_on_attention=True, stdout=StringIO())
