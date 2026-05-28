import json
from calendar import monthrange
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from audit.models import AuditEvent, ManualResolution
from cobranza.models import CodigoCobroResidual, EstadoCobroResidual, EstadoPago, PagoMensual
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
    CuadraturaBancaria,
    EstadoCuadraturaBancaria,
    EstadoConciliacionMovimiento,
    EstadoConexionBancaria,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    OrigenImportacionMovimiento,
    TipoMovimientoBancario,
    TransferenciaIntercuenta,
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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
            monto_efecto_codigo_efectivo_clp=Decimal('0.00'),
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

    def _create_secondary_account(self, cuenta, suffix='DST'):
        return CuentaRecaudadora.objects.create(
            empresa_owner=cuenta.empresa_owner,
            institucion='Banco Stage3',
            numero_cuenta=f'ACC-{suffix}',
            tipo_cuenta='corriente',
            titular_nombre=cuenta.empresa_owner.razon_social,
            titular_rut=cuenta.empresa_owner.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
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
        payment.fecha_deposito_banco = date(2026, 1, 8)
        payment.save(update_fields=['fecha_deposito_banco', 'updated_at'])
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

    def _create_reconciled_charge_movement(self, conexion):
        return MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 9),
            tipo_movimiento=TipoMovimientoBancario.DEBIT,
            monto=Decimal('10000.00'),
            descripcion_origen='Cargo bancario clasificado Stage3',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3-charge',
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
        )

    def _create_square_balance(self, cuenta, periodo='2026-01'):
        year, month = (int(part) for part in periodo.split('-'))
        return CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico=periodo,
            fecha_cuadratura=date(year, month, monthrange(year, month)[1]),
            saldo_sistema_clp=Decimal('1000000.00'),
            saldo_banco_clp=Decimal('1000000.00'),
            estado=EstadoCuadraturaBancaria.SQUARED,
            evidencia_cuadratura_ref='balance-square-stage3',
            responsable_ref='stage3-balance-owner',
        )

    def _create_superseded_audit_event(
        self,
        resolution,
        movimiento,
        *,
        superseded_by='conciliacion.exact_match',
        match_type='payment',
        metadata_extra=None,
    ):
        metadata = {
            'resolution_category': resolution.category,
            'superseded_by': superseded_by,
            'superseded_match_type': match_type,
            'movimiento_id': movimiento.pk,
            'conexion_bancaria_id': movimiento.conexion_bancaria_id,
            **(metadata_extra or {}),
        }
        return AuditEvent.objects.create(
            actor_identifier='system.conciliacion',
            event_type='audit.manual_resolution.superseded',
            entity_type='manual_resolution',
            entity_id=str(resolution.pk),
            summary='Resolucion manual supersedida por conciliacion trazada.',
            metadata=metadata,
        )

    def _create_internal_transfer_pair(self, cuenta_origen, conexion_origen, suffix='OK'):
        cuenta_destino = self._create_secondary_account(cuenta_origen, suffix=suffix)
        conexion_destino = self._create_ready_connection(cuenta_destino)
        movimiento_origen = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion_origen,
            fecha_movimiento=date(2026, 1, 10),
            tipo_movimiento=TipoMovimientoBancario.DEBIT,
            monto=Decimal('50000.00'),
            descripcion_origen='Transferencia interna enviada',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-transfer-origin',
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
        )
        movimiento_destino = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion_destino,
            fecha_movimiento=date(2026, 1, 10),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('50000.00'),
            descripcion_origen='Transferencia interna recibida',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-transfer-destination',
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
        )
        transfer = TransferenciaIntercuenta.objects.create(
            movimiento_origen=movimiento_origen,
            movimiento_destino=movimiento_destino,
            periodo_economico='2026-01',
            criterio_conciliacion='Par cargo/abono exacto entre cuentas recaudadoras.',
            evidencia_transferencia_ref='internal-transfer-controlled-2026-01',
            responsable_ref='stage3-transfer-owner',
            rationale='Transferencia interna validada por cartola controlada.',
        )
        self._create_square_balance(cuenta_destino)
        return transfer, movimiento_origen, movimiento_destino

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
        self.assertIn('stage3.balance_square_record_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        cuenta, payment = self._create_payment_matrix()
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage3_conciliacion'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertEqual(result['issues'], [])

    def test_exact_match_payment_period_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-PAY-PERIOD')
        conexion = self._create_ready_connection(cuenta)
        payment.fecha_deposito_banco = date(2026, 2, 8)
        payment.save(update_fields=['fecha_deposito_banco', 'updated_at'])
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 2, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Pago conciliado fuera de periodo',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.invalid_model', issue_codes)
        self.assertEqual(result['sections']['movements']['invalid_model'], 1)

    def test_partial_payment_exact_match_without_manual_resolution_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-PARTIAL-NO-MANUAL')
        conexion = self._create_ready_connection(cuenta)
        payment.fecha_deposito_banco = date(2026, 1, 8)
        payment.save(update_fields=['fecha_deposito_banco', 'updated_at'])
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('100000.00'),
            descripcion_origen='Abono parcial conciliado sin resolucion manual',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )
        self._create_square_balance(cuenta)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.payment_partial_without_manual_resolution', issue_codes)
        self.assertEqual(result['sections']['movements']['payment_partial_without_manual_resolution'], 1)

    def test_partial_payment_exact_match_with_manual_resolution_trace_can_pass_readiness(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-PARTIAL-MANUAL')
        conexion = self._create_ready_connection(cuenta)
        payment.fecha_deposito_banco = date(2026, 1, 8)
        payment.save(update_fields=['fecha_deposito_banco', 'updated_at'])
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('100000.00'),
            descripcion_origen='Abono parcial conciliado con resolucion manual',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Abono parcial regularizado manualmente',
            rationale='Se regularizo un abono parcial contra pago mensual con respaldo controlado.',
            metadata={
                'resolved_with': 'payment_manual_assignment',
                'resolved_payment_id': payment.pk,
                'resolved_contract_id': payment.contrato_id,
                'periodo_economico': '2026-01',
                'criterio_aplicado': 'Suma parcial auditada contra saldo del pago mensual.',
                'evidencia_regularizacion_ref': 'partial-payment-evidence-2026-01',
            },
        )
        self._create_square_balance(cuenta)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage3_conciliacion'])
        self.assertNotIn('stage3.movement.payment_partial_without_manual_resolution', issue_codes)

    def test_debit_exact_match_without_manual_resolution_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-DEBIT-NO-RESOLUTION')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_reconciled_charge_movement(conexion)
        self._create_square_balance(cuenta)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.debit_exact_match_without_manual_resolution', issue_codes)
        self.assertEqual(result['sections']['movements']['debit_exact_match_without_manual_resolution'], 1)

    def test_debit_exact_match_with_manual_resolution_trace_can_pass_readiness(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-DEBIT-RESOLUTION')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo bancario clasificado manualmente',
            rationale='Se clasifico comision bancaria con respaldo controlado.',
            metadata={
                'categoria_movimiento': 'comision_bancaria',
                'entidad_afectada_tipo': 'empresa',
                'entidad_afectada_id': cuenta.empresa_owner_id,
                'periodo_economico': '2026-01',
                'criterio_reparto': 'Cargo asignado a empresa duena de la cuenta.',
                'evidencia_clasificacion_ref': 'charge-classification-controlled-ref',
            },
        )
        self._create_square_balance(cuenta)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage3_conciliacion'])
        self.assertNotIn('stage3.movement.debit_exact_match_without_manual_resolution', issue_codes)

    def test_internal_transfer_pair_can_pass_readiness(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-TRANSFER')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        transfer, movimiento_origen, movimiento_destino = self._create_internal_transfer_pair(cuenta, conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento_origen.pk),
            summary='Transferencia interna registrada',
            rationale='Transferencia interna validada por cartola controlada.',
            metadata={
                'categoria_movimiento': 'transferencia_interna',
                'resolved_with': 'internal_transfer',
                'transferencia_intercuenta_id': transfer.pk,
                'movimiento_origen_id': movimiento_origen.pk,
                'movimiento_destino_id': movimiento_destino.pk,
                'entidad_origen_tipo': transfer.entidad_origen_tipo,
                'entidad_origen_id': transfer.entidad_origen_id,
                'entidad_destino_tipo': transfer.entidad_destino_tipo,
                'entidad_destino_id': transfer.entidad_destino_id,
                'periodo_economico': '2026-01',
                'criterio_conciliacion': 'Par cargo/abono exacto entre cuentas recaudadoras.',
                'evidencia_transferencia_ref': 'internal-transfer-controlled-2026-01',
                'responsable_ref': 'stage3-transfer-owner',
            },
        )

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage3_conciliacion'])
        self.assertEqual(result['sections']['internal_transfers']['total'], 1)
        self.assertEqual(result['issues'], [])

    def test_resolved_internal_transfer_with_metadata_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-TRANSFER-METADATA-MISMATCH')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        transfer, movimiento_origen, movimiento_destino = self._create_internal_transfer_pair(
            cuenta,
            conexion,
            suffix='META-MISMATCH',
        )
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento_origen.pk),
            summary='Transferencia interna registrada con metadata heredada desalineada',
            rationale='Transferencia interna validada por cartola controlada.',
            metadata={
                'categoria_movimiento': 'transferencia_interna',
                'resolved_with': 'internal_transfer',
                'transferencia_intercuenta_id': transfer.pk,
                'movimiento_origen_id': movimiento_origen.pk,
                'movimiento_destino_id': movimiento_destino.pk,
                'entidad_origen_tipo': transfer.entidad_origen_tipo,
                'entidad_origen_id': transfer.entidad_origen_id,
                'entidad_destino_tipo': transfer.entidad_destino_tipo,
                'entidad_destino_id': transfer.entidad_destino_id,
                'periodo_economico': transfer.periodo_economico,
                'criterio_conciliacion': transfer.criterio_conciliacion,
                'evidencia_transferencia_ref': 'internal-transfer-other-controlled-ref',
                'responsable_ref': transfer.responsable_ref,
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.internal_transfer_target_mismatch', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['internal_transfer_target_mismatch'], 1)

    def test_internal_transfer_sensitive_reference_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-TRANSFER-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        transfer, movimiento_origen, movimiento_destino = self._create_internal_transfer_pair(
            cuenta,
            conexion,
            suffix='SENSITIVE',
        )
        TransferenciaIntercuenta.objects.filter(pk=transfer.pk).update(
            evidencia_transferencia_ref='https://bank.example.test/transfer?token=secret'
        )
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento_origen.pk),
            summary='Transferencia interna con evidencia sensible',
            rationale='Transferencia interna registrada con metadata heredada.',
            metadata={
                'categoria_movimiento': 'transferencia_interna',
                'resolved_with': 'internal_transfer',
                'transferencia_intercuenta_id': transfer.pk,
                'movimiento_origen_id': movimiento_origen.pk,
                'movimiento_destino_id': movimiento_destino.pk,
                'entidad_origen_tipo': transfer.entidad_origen_tipo,
                'entidad_origen_id': transfer.entidad_origen_id,
                'entidad_destino_tipo': transfer.entidad_destino_tipo,
                'entidad_destino_id': transfer.entidad_destino_id,
                'periodo_economico': '2026-01',
                'criterio_conciliacion': 'Par cargo/abono exacto entre cuentas recaudadoras.',
                'evidencia_transferencia_ref': 'https://bank.example.test/transfer?token=secret',
                'responsable_ref': 'stage3-transfer-owner',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.internal_transfer.sensitive_reference', issue_codes)
        self.assertIn('stage3.manual_resolution.internal_transfer_evidence_sensitive', issue_codes)
        self.assertEqual(result['sections']['internal_transfers']['sensitive_reference'], 1)

    def test_internal_transfer_sensitive_context_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-TRANSFER-CONTEXT-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        transfer, movimiento_origen, movimiento_destino = self._create_internal_transfer_pair(
            cuenta,
            conexion,
            suffix='CTX-SENSITIVE',
        )
        TransferenciaIntercuenta.objects.filter(pk=transfer.pk).update(
            criterio_conciliacion='Criterio en https://bank.example.test/transfer?token=secret',
            rationale='Motivo en https://bank.example.test/transfer?token=secret',
        )
        transfer.refresh_from_db()
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento_origen.pk),
            summary='Transferencia interna con contexto sensible',
            rationale='Transferencia interna registrada con metadata controlada.',
            metadata={
                'categoria_movimiento': 'transferencia_interna',
                'resolved_with': 'internal_transfer',
                'transferencia_intercuenta_id': transfer.pk,
                'movimiento_origen_id': movimiento_origen.pk,
                'movimiento_destino_id': movimiento_destino.pk,
                'entidad_origen_tipo': transfer.entidad_origen_tipo,
                'entidad_origen_id': transfer.entidad_origen_id,
                'entidad_destino_tipo': transfer.entidad_destino_tipo,
                'entidad_destino_id': transfer.entidad_destino_id,
                'periodo_economico': '2026-01',
                'criterio_conciliacion': 'Criterio en https://bank.example.test/transfer?token=secret',
                'evidencia_transferencia_ref': 'internal-transfer-controlled-2026-01',
                'responsable_ref': 'stage3-transfer-owner',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.internal_transfer.sensitive_reference', issue_codes)
        self.assertIn('stage3.manual_resolution.internal_transfer_context_sensitive', issue_codes)
        self.assertEqual(result['sections']['internal_transfers']['sensitive_reference'], 1)
        self.assertEqual(result['sections']['manual_resolutions']['internal_transfer_context_sensitive'], 1)

    def test_resolved_internal_transfer_without_context_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-TRANSFER-CONTEXT')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_charge_movement(conexion)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Transferencia interna sin contexto',
            rationale='Clasificada historicamente.',
            metadata={'categoria_movimiento': 'transferencia_interna'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.internal_transfer_context_missing', issue_codes)

    def test_superseded_manual_resolution_with_trace_can_pass_readiness(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-SUPERSEDED-OK')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        resolution = ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.SUPERSEDED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso supersedido por match exacto posterior',
            rationale='Supersedida por match exacto trazable.',
            metadata={
                'superseded_by': 'conciliacion.exact_match',
                'superseded_match_type': 'payment',
                'movimiento_id': movimiento.pk,
                'pago_mensual_id': payment.pk,
            },
        )
        self._create_superseded_audit_event(
            resolution,
            movimiento,
            metadata_extra={'pago_mensual_id': payment.pk},
        )

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage3_conciliacion'])
        self.assertNotIn(
            'stage3.manual_resolution.superseded_trace_missing',
            {issue['code'] for issue in result['issues']},
        )
        self.assertNotIn(
            'stage3.manual_resolution.superseded_audit_event_missing',
            {issue['code'] for issue in result['issues']},
        )

    def test_superseded_manual_resolution_without_audit_event_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-SUPERSEDED-NO-AUDIT')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.SUPERSEDED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso supersedido sin evento',
            rationale='Supersedida por match exacto trazable.',
            metadata={
                'superseded_by': 'conciliacion.exact_match',
                'superseded_match_type': 'payment',
                'movimiento_id': movimiento.pk,
                'pago_mensual_id': payment.pk,
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.superseded_audit_event_missing', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['superseded_without_audit_event'], 1)

    def test_superseded_manual_resolution_with_mismatched_audit_event_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-SUPERSEDED-AUDIT-MISMATCH')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta)
        resolution = ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.SUPERSEDED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso supersedido con evento desalineado',
            rationale='Supersedida por match exacto trazable.',
            metadata={
                'superseded_by': 'conciliacion.exact_match',
                'superseded_match_type': 'payment',
                'movimiento_id': movimiento.pk,
                'pago_mensual_id': payment.pk,
            },
        )
        self._create_superseded_audit_event(
            resolution,
            movimiento,
            superseded_by='conciliacion.manual_resolution',
            metadata_extra={'pago_mensual_id': payment.pk},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.superseded_audit_event_missing', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['superseded_without_audit_event'], 1)

    def test_missing_balance_square_record_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-MISSING')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_square_record_missing', issue_codes)
        self.assertEqual(result['sections']['balance_squares']['total'], 0)

    def test_missing_balance_square_for_movement_account_period_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-COVERAGE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta, periodo='2026-01')
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 2, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('150000.00'),
            descripcion_origen='Movimiento febrero sin cuadratura',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3-feb',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_square.account_period_missing', issue_codes)
        self.assertEqual(result['sections']['balance_squares']['missing_account_period'], 1)

    def test_balance_square_for_each_movement_account_period_satisfies_coverage(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-COVERED')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        self._create_square_balance(cuenta, periodo='2026-01')
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 2, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('150000.00'),
            descripcion_origen='Movimiento febrero con cuadratura',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3-feb-covered',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )
        self._create_square_balance(cuenta, periodo='2026-02')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertNotIn('stage3.balance_square.account_period_missing', issue_codes)
        self.assertNotIn('missing_account_period', result['sections']['balance_squares'])

    def test_nonzero_balance_square_difference_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-DIFF')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura=date(2026, 1, 31),
            saldo_sistema_clp=Decimal('1000000.00'),
            saldo_banco_clp=Decimal('999990.00'),
            estado=EstadoCuadraturaBancaria.EXPLAINED_DIFFERENCE,
            evidencia_cuadratura_ref='balance-square-stage3-diff',
            responsable_ref='stage3-balance-owner',
            rationale='Diferencia detectada en cartola controlada pendiente de ajuste.',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_square.nonzero_difference', issue_codes)
        self.assertIn('stage3.balance_square.not_squared', issue_codes)
        self.assertEqual(result['sections']['balance_squares']['nonzero_difference'], 1)

    def test_balance_square_sensitive_reference_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura=date(2026, 1, 31),
            saldo_sistema_clp=Decimal('1000000.00'),
            saldo_banco_clp=Decimal('1000000.00'),
            estado=EstadoCuadraturaBancaria.SQUARED,
            evidencia_cuadratura_ref='https://bank.example.test/balance?token=secret',
            responsable_ref='stage3-balance-owner',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_square.sensitive_reference', issue_codes)
        self.assertEqual(result['sections']['balance_squares']['sensitive_reference'], 1)

    def test_balance_square_sensitive_rationale_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-RATIONALE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura=date(2026, 1, 31),
            saldo_sistema_clp=Decimal('1000000.00'),
            saldo_banco_clp=Decimal('1000000.00'),
            estado=EstadoCuadraturaBancaria.SQUARED,
            evidencia_cuadratura_ref='balance-square-stage3',
            responsable_ref='stage3-balance-owner',
            rationale='Cuadratura revisada en https://bank.example.test/balance?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_square.sensitive_reference', issue_codes)
        self.assertEqual(result['sections']['balance_squares']['sensitive_reference'], 1)

    def test_balance_square_period_date_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-BALANCE-PERIOD')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura=date(2026, 2, 1),
            saldo_sistema_clp=Decimal('1000000.00'),
            saldo_banco_clp=Decimal('1000000.00'),
            estado=EstadoCuadraturaBancaria.SQUARED,
            evidencia_cuadratura_ref='balance-square-stage3',
            responsable_ref='stage3-balance-owner',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.balance_square.period_date_mismatch', issue_codes)
        self.assertEqual(result['sections']['balance_squares']['period_date_mismatch'], 1)

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

    def test_unknown_income_snapshot_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-MISMATCH')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto=movimiento.monto + Decimal('1.00'),
            fecha_movimiento=movimiento.fecha_movimiento,
            descripcion_origen=movimiento.descripcion_origen,
            estado=EstadoIngresoDesconocido.RESOLVED,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.unknown_income.invalid_model', issue_codes)
        self.assertEqual(result['sections']['unknown_income']['invalid_model'], 1)

    def test_unknown_income_sensitive_assisted_suggestion_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-SUGGESTION')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto=movimiento.monto,
            fecha_movimiento=movimiento.fecha_movimiento,
            descripcion_origen=movimiento.descripcion_origen,
            estado=EstadoIngresoDesconocido.RESOLVED,
            sugerencia_asistida={
                'payment_candidate_ids': [payment.pk],
                'authorization': 'opaque-authorization-value',
                'nested': {'private_key': 'opaque-private-key-value'},
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.unknown_income.sensitive_suggestion', issue_codes)
        self.assertEqual(result['sections']['unknown_income']['sensitive_suggestion'], 1)

    def test_exact_matched_payment_snapshot_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-EXACT-MISMATCH')
        conexion = self._create_ready_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp + Decimal('1.00'),
            descripcion_origen='Pago conciliado con snapshot inconsistente',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.invalid_model', issue_codes)
        self.assertEqual(result['sections']['movements']['invalid_model'], 1)

    def test_exact_matched_residual_from_other_account_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-RES-ACCOUNT')
        other_account = self._create_secondary_account(cuenta, suffix='RES-MISMATCH')
        conexion = self._create_ready_connection(other_account)
        residual = CodigoCobroResidual.objects.create(
            referencia_visible='CCR-ABC234',
            arrendatario=payment.contrato.arrendatario,
            contrato_origen=payment.contrato,
            saldo_actual=Decimal('0.00'),
            estado=EstadoCobroResidual.PAID,
            fecha_activacion=date(2027, 1, 10),
        )
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('15000.00'),
            descripcion_origen='Cobranza residual conciliada en cuenta incorrecta',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            codigo_cobro_residual=residual,
        )
        self._create_square_balance(other_account)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.invalid_model', issue_codes)
        self.assertEqual(result['sections']['movements']['invalid_model'], 1)

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

    def test_resolved_manual_resolution_without_rationale_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-REASON')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Regularizacion historica sin motivo',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.rationale_missing', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['resolved_without_rationale'], 1)

    def test_resolved_manual_resolution_with_sensitive_rationale_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-REASON-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Regularizacion historica con motivo sensible',
            rationale='Motivo con https://bank.example.test/income?token=secret',
            metadata={
                'resolved_with': 'payment_manual_assignment',
                'resolved_payment_id': payment.pk,
                'resolved_contract_id': payment.contrato_id,
                'periodo_economico': '2026-01',
                'criterio_aplicado': 'Saldo exacto contra pago mensual.',
                'evidencia_regularizacion_ref': 'unknown-income-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.rationale_sensitive', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['resolved_sensitive_rationale'], 1)

    def test_superseded_manual_resolution_without_trace_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-SUPERSEDED-TRACE')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.SUPERSEDED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso supersedido sin traza',
            metadata={'superseded_by': 'legacy'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.superseded_trace_missing', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['superseded_without_trace'], 1)

    def test_resolved_unknown_income_without_resolution_context_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-CONTEXT')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso historico sin contexto',
            rationale='Regularizado historicamente.',
            metadata={'resolved_with': 'payment_manual_assignment'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.unknown_income_resolution_context_missing', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['unknown_income_resolution_context_missing'], 1)

    def test_resolved_unknown_income_with_sensitive_evidence_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso con evidencia sensible',
            rationale='Regularizado con evidencia heredada.',
            metadata={
                'resolved_with': 'payment_manual_assignment',
                'resolved_payment_id': payment.pk,
                'resolved_contract_id': payment.contrato_id,
                'periodo_economico': '2026-01',
                'criterio_aplicado': 'Saldo exacto contra pago mensual.',
                'evidencia_regularizacion_ref': 'https://bank.example.test/income?token=secret',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.unknown_income_resolution_evidence_sensitive', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['unknown_income_resolution_evidence_sensitive'], 1)

    def test_resolved_unknown_income_with_sensitive_context_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-CONTEXT-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso con criterio sensible',
            rationale='Regularizado con criterio heredado.',
            metadata={
                'resolved_with': 'payment_manual_assignment',
                'resolved_payment_id': payment.pk,
                'resolved_contract_id': payment.contrato_id,
                'periodo_economico': '2026-01',
                'criterio_aplicado': 'Saldo exacto en https://bank.example.test/income?token=secret',
                'evidencia_regularizacion_ref': 'unknown-income-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.unknown_income_resolution_context_sensitive', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['unknown_income_resolution_context_sensitive'], 1)

    def test_resolved_unknown_income_with_invalid_period_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-PERIOD')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso con periodo economico invalido',
            rationale='Regularizado con metadata heredada.',
            metadata={
                'resolved_with': 'payment_manual_assignment',
                'resolved_payment_id': payment.pk,
                'resolved_contract_id': payment.contrato_id,
                'periodo_economico': '2026-13',
                'criterio_aplicado': 'Saldo exacto contra pago mensual.',
                'evidencia_regularizacion_ref': 'unknown-income-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.unknown_income_resolution_period_invalid', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['unknown_income_resolution_period_invalid'], 1)

    def test_resolved_unknown_income_with_target_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-UNKNOWN-TARGET')
        conexion = self._create_ready_connection(cuenta)
        movimiento = self._create_reconciled_movement(conexion, payment)
        ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary='Ingreso con target inconsistente',
            rationale='Regularizado con metadata heredada.',
            metadata={
                'resolved_with': 'payment_manual_assignment',
                'resolved_payment_id': payment.pk,
                'resolved_contract_id': payment.contrato_id,
                'periodo_economico': '2026-02',
                'criterio_aplicado': 'Saldo exacto contra pago mensual.',
                'evidencia_regularizacion_ref': 'unknown-income-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.unknown_income_resolution_target_mismatch', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['unknown_income_resolution_target_mismatch'], 1)

    def test_resolved_charge_manual_resolution_without_classification_context_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-CHARGE-CONTEXT')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo historico sin contexto',
            rationale='Clasificado historicamente.',
            metadata={'resolved_with': 'charge_manual_classification'},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.charge_classification_context_missing', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['charge_classification_context_missing'], 1)

    def test_resolved_charge_manual_resolution_with_sensitive_evidence_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-CHARGE-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo con evidencia sensible',
            rationale='Clasificado con evidencia heredada.',
            metadata={
                'categoria_movimiento': 'comision_bancaria',
                'entidad_afectada_tipo': 'empresa',
                'entidad_afectada_id': cuenta.empresa_owner_id,
                'periodo_economico': '2026-01',
                'criterio_reparto': 'Cargo asignado a empresa duena de la cuenta.',
                'evidencia_clasificacion_ref': 'https://bank.example.test/fee?token=secret',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.charge_classification_evidence_sensitive', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['charge_classification_evidence_sensitive'], 1)

    def test_resolved_charge_manual_resolution_with_sensitive_context_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-CHARGE-CONTEXT-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo con criterio sensible',
            rationale='Clasificado con criterio heredado.',
            metadata={
                'categoria_movimiento': 'comision_bancaria',
                'entidad_afectada_tipo': 'empresa',
                'entidad_afectada_id': cuenta.empresa_owner_id,
                'periodo_economico': '2026-01',
                'criterio_reparto': 'Cargo revisado en https://bank.example.test/fee?token=secret',
                'evidencia_clasificacion_ref': 'charge-classification-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.charge_classification_context_sensitive', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['charge_classification_context_sensitive'], 1)

    def test_resolved_charge_manual_resolution_with_invalid_period_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-CHARGE-PERIOD')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo con periodo economico invalido',
            rationale='Clasificado con metadata heredada.',
            metadata={
                'categoria_movimiento': 'comision_bancaria',
                'entidad_afectada_tipo': 'empresa',
                'entidad_afectada_id': cuenta.empresa_owner_id,
                'periodo_economico': '2026-13',
                'criterio_reparto': 'Cargo asignado a empresa duena de la cuenta.',
                'evidencia_clasificacion_ref': 'charge-classification-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.charge_classification_period_invalid', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['charge_classification_period_invalid'], 1)

    def test_resolved_charge_manual_resolution_with_target_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-CHARGE-TARGET')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo con entidad afectada inconsistente',
            rationale='Clasificado con metadata heredada.',
            metadata={
                'categoria_movimiento': 'comision_bancaria',
                'entidad_afectada_tipo': 'empresa',
                'entidad_afectada_id': cuenta.empresa_owner_id + 99,
                'periodo_economico': '2026-01',
                'criterio_reparto': 'Cargo asignado a empresa duena de la cuenta.',
                'evidencia_clasificacion_ref': 'charge-classification-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.charge_classification_target_mismatch', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['charge_classification_target_mismatch'], 1)

    def test_resolved_charge_manual_resolution_with_movement_period_mismatch_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-CHARGE-MOVEMENT-PERIOD')
        conexion = self._create_ready_connection(cuenta)
        self._create_reconciled_movement(conexion, payment)
        charge = self._create_reconciled_charge_movement(conexion)
        ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            status=ManualResolution.Status.RESOLVED,
            scope_type='movimiento_bancario',
            scope_reference=str(charge.pk),
            summary='Cargo con periodo economico desalineado al movimiento',
            rationale='Clasificado con metadata heredada.',
            metadata={
                'categoria_movimiento': 'comision_bancaria',
                'entidad_afectada_tipo': 'empresa',
                'entidad_afectada_id': cuenta.empresa_owner_id,
                'periodo_economico': '2026-02',
                'criterio_reparto': 'Cargo asignado a empresa duena de la cuenta.',
                'evidencia_clasificacion_ref': 'charge-classification-controlled-ref',
            },
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.manual_resolution.charge_classification_target_mismatch', issue_codes)
        self.assertEqual(result['sections']['manual_resolutions']['charge_classification_target_mismatch'], 1)

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

    def test_sensitive_movement_bank_reference_is_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-MOV-REF-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Pago conciliado con referencia sensible',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            referencia='https://bank.example.test/reference?token=secret',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.sensitive_reference', issue_codes)
        self.assertEqual(result['sections']['movements']['sensitive_reference'], 1)

    def test_sensitive_movement_admin_notes_are_blocking(self):
        cuenta, payment = self._create_payment_matrix(codigo='ST3-MOV-NOTES-SENSITIVE')
        conexion = self._create_ready_connection(cuenta)
        movement = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 8),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=payment.monto_calculado_clp,
            descripcion_origen='Pago conciliado con nota administrativa sensible',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage3',
            saldo_reportado=Decimal('1000000.00'),
            estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH,
            pago_mensual=payment,
        )
        MovimientoBancarioImportado.objects.filter(pk=movement.pk).update(
            notas_admin='Revision interna en https://bank.example.test/note?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage3_conciliacion'])
        self.assertIn('stage3.movement.sensitive_admin_notes', issue_codes)
        self.assertEqual(result['sections']['movements']['sensitive_admin_notes'], 1)
        self.assertNotIn('bank.example.test', json.dumps(result))

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
