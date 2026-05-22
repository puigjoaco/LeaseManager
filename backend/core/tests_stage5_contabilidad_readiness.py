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

from conciliacion.models import (
    ConexionBancaria,
    EstadoConciliacionMovimiento,
    EstadoConexionBancaria,
    MovimientoBancarioImportado,
    OrigenImportacionMovimiento,
    TipoMovimientoBancario,
)
from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MatrizReglasContables,
    MovimientoAsiento,
    ReglaContable,
    TipoMovimientoAsiento,
)
from contabilidad.services import ensure_default_regime
from core.stage5_contabilidad_readiness import collect_stage5_contabilidad_readiness
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio


class Stage5ContabilidadReadinessTests(TestCase):
    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='Empresa Stage5 SpA', rut='88888888-8'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', f'{rut[:7]}1-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', f'{rut[:7]}2-2')
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

    def _setup_contabilidad(self, empresa):
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio=date(2026, 1, 1),
            moneda_funcional='CLP',
            estado='activa',
        )
        banco = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='1101',
            nombre='Bancos',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        ingresos = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='4101',
            nombre='Ingresos por arriendo',
            naturaleza='acreedora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        rule = ReglaContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            plan_cuentas_version='v1',
            criterio_cargo='default:1101',
            criterio_abono='default:4101',
            vigencia_desde=date(2026, 1, 1),
            estado='activa',
        )
        MatrizReglasContables.objects.create(
            regla_contable=rule,
            cuenta_debe=banco,
            cuenta_haber=ingresos,
            estado='activa',
        )
        return banco, ingresos

    def _create_posted_event_and_asiento(self, empresa, debit_account, credit_account, amount=Decimal('100000.00')):
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='pago_mensual',
            entidad_origen_id='stage5-payment-1',
            fecha_operativa=date(2026, 1, 10),
            moneda='CLP',
            monto_base=amount,
            payload_resumen={'origen': 'fixture-controlado'},
            idempotency_key=f'stage5-posted-{empresa.pk}',
            estado_contable=EstadoEventoContable.POSTED,
        )
        asiento = AsientoContable.objects.create(
            evento_contable=event,
            fecha_contable=event.fecha_operativa,
            periodo_contable='2026-01',
            estado=EstadoAsientoContable.POSTED,
            debe_total=amount,
            haber_total=amount,
            moneda_funcional='CLP',
        )
        asiento.set_hash_integridad()
        asiento.save(update_fields=['hash_integridad'])
        MovimientoAsiento.objects.create(
            asiento_contable=asiento,
            cuenta_contable=debit_account,
            tipo_movimiento=TipoMovimientoAsiento.DEBIT,
            monto=amount,
            glosa='Pago conciliado controlado',
        )
        MovimientoAsiento.objects.create(
            asiento_contable=asiento,
            cuenta_contable=credit_account,
            tipo_movimiento=TipoMovimientoAsiento.CREDIT,
            monto=amount,
            glosa='Pago conciliado controlado',
        )
        return event, asiento

    def _create_approved_close_snapshots(self, empresa):
        now = timezone.now()
        LibroDiario.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'asientos': [{'asiento_id': 1}]},
        )
        LibroMayor.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'cuentas': [{'cuenta': '1101'}]},
        )
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'total_debe': '100000.00', 'total_haber': '100000.00', 'cuadrado': True},
        )
        return CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
            fecha_preparacion=now,
            fecha_aprobacion=now,
            resumen_obligaciones={
                'snapshots': {
                    'libro_diario': '2026-01',
                    'libro_mayor': '2026-01',
                    'balance_comprobacion': '2026-01',
                },
                'conciliacion': {
                    'movimientos_bancarios_periodo': 0,
                    'movimientos_bancarios_no_resueltos': 0,
                },
            },
        )

    def _create_valid_local_matrix(self):
        empresa = self._create_active_empresa()
        debit, credit = self._setup_contabilidad(empresa)
        self._create_posted_event_and_asiento(empresa, debit, credit)
        self._create_approved_close_snapshots(empresa)
        return empresa

    def _collect_with_final_refs(self):
        return collect_stage5_contabilidad_readiness(
            stage3_evidence_ref='stage3-conciliacion-controlled-v1',
            ledger_proof_ref='ledger-proof-controlled-v1',
            reports_proof_ref='reports-proof-controlled-v1',
            responsible_ref='stage5-responsibles-v1',
            source_label='stage5-controlled-v1',
            authorization_ref='stage5-authorization-v1',
            source_kind='snapshot_controlado',
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage5_contabilidad_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage5.source_kind_not_authorized', issue_codes)
        self.assertIn('stage5.fiscal_config_missing', issue_codes)
        self.assertIn('stage5.events_missing', issue_codes)
        self.assertIn('stage5.approved_close_missing', issue_codes)
        self.assertIn('stage5.stage3_evidence_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_valid_local_matrix()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage5_contabilidad'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_matrix_and_non_sensitive_refs_cannot_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage5_contabilidad_readiness(
            stage3_evidence_ref='stage3-conciliacion-controlled-v1',
            ledger_proof_ref='ledger-proof-controlled-v1',
            reports_proof_ref='reports-proof-controlled-v1',
            responsible_ref='stage5-responsibles-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage5.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_valid_local_matrix()

        result = collect_stage5_contabilidad_readiness(
            stage3_evidence_ref='stage3-conciliacion-controlled-v1',
            ledger_proof_ref='ledger-proof-controlled-v1',
            reports_proof_ref='reports-proof-controlled-v1',
            responsible_ref='stage5-responsibles-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.source_label_missing', issue_codes)
        self.assertIn('stage5.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_rule_without_active_matrix_is_blocking(self):
        empresa = self._create_active_empresa(nombre='RuleNoMatrixCo', rut='78787878-7')
        self._setup_contabilidad(empresa)
        MatrizReglasContables.objects.all().delete()

        result = collect_stage5_contabilidad_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.matrix_missing', issue_codes)
        self.assertIn('stage5.rules_without_matrix', issue_codes)

    def test_pending_event_and_unbalanced_asiento_are_blocking(self):
        empresa = self._create_active_empresa(nombre='PendingEventCo', rut='79797979-4')
        debit, credit = self._setup_contabilidad(empresa)
        self._create_posted_event_and_asiento(empresa, debit, credit)
        pending = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='pending-1',
            fecha_operativa=date(2026, 1, 12),
            moneda='CLP',
            monto_base=Decimal('50000.00'),
            payload_resumen={},
            idempotency_key='pending-event-stage5',
            estado_contable=EstadoEventoContable.REVIEW,
        )
        AsientoContable.objects.create(
            evento_contable=pending,
            fecha_contable=pending.fecha_operativa,
            periodo_contable='2026-01',
            estado=EstadoAsientoContable.POSTED,
            debe_total=Decimal('50000.00'),
            haber_total=Decimal('40000.00'),
            moneda_funcional='CLP',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.events_not_posted', issue_codes)
        self.assertIn('stage5.asiento_unbalanced', issue_codes)

    def test_asiento_movement_totals_and_company_mismatch_are_blocking(self):
        empresa = self._create_valid_local_matrix()
        other_empresa = self._create_active_empresa(nombre='OtherMovementCo', rut='76767676-7')
        other_debit, _ = self._setup_contabilidad(other_empresa)
        asiento = AsientoContable.objects.get(evento_contable__empresa=empresa)
        debit_movement = asiento.movimientos.get(tipo_movimiento=TipoMovimientoAsiento.DEBIT)
        debit_movement.monto = Decimal('99999.00')
        debit_movement.save(update_fields=['monto', 'updated_at'])
        credit_movement = asiento.movimientos.get(tipo_movimiento=TipoMovimientoAsiento.CREDIT)
        credit_movement.cuenta_contable = other_debit
        credit_movement.save(update_fields=['cuenta_contable', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.asiento_movement_totals_mismatch', issue_codes)
        self.assertIn('stage5.asiento_movement_company_mismatch', issue_codes)
        self.assertEqual(result['sections']['ledger']['movement_totals_mismatch'], 1)
        self.assertEqual(result['sections']['ledger']['movement_company_mismatch'], 1)

    def test_approved_close_without_snapshots_or_square_balance_is_blocking(self):
        empresa = self._create_valid_local_matrix()
        LibroMayor.objects.all().delete()
        BalanceComprobacion.objects.update(resumen={'total_debe': '100.00', 'total_haber': '90.00', 'cuadrado': False})

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.close_snapshots_missing', issue_codes)

        LibroMayor.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'cuentas': [{'cuenta': '1101'}]},
        )
        result = self._collect_with_final_refs()
        self.assertIn('stage5.close_balance_not_square', {issue['code'] for issue in result['issues']})

    def test_unresolved_bank_movement_in_close_period_is_blocking(self):
        empresa = self._create_valid_local_matrix()
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Stage5',
            numero_cuenta='ACC-ST5-001',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_stage5',
            credencial_ref='bank-stage5-ref',
            evidencia_gate_ref='bank-stage5-gate',
            prueba_conectividad_ref='bank-stage5-connectivity',
            prueba_movimientos_ref='bank-stage5-movements',
            estado_conexion=EstadoConexionBancaria.ACTIVE,
            primaria_movimientos=True,
        )
        MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento=date(2026, 1, 20),
            tipo_movimiento=TipoMovimientoBancario.CREDIT,
            monto=Decimal('888888.00'),
            descripcion_origen='Abono pendiente Stage5',
            origen_importacion=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
            evidencia_importacion_ref='manual-import-stage5',
            estado_conciliacion=EstadoConciliacionMovimiento.PENDING,
        )

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.close_conciliation_unresolved', {issue['code'] for issue in result['issues']})

    def test_sensitive_final_refs_do_not_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage5_contabilidad_readiness(
            stage3_evidence_ref='https://example.com/stage3',
            ledger_proof_ref='ledger-proof-controlled-v1',
            reports_proof_ref='reports-proof-controlled-v1',
            responsible_ref='stage5-responsibles-v1',
            source_kind='snapshot_controlado',
        )

        self.assertFalse(result['ready_for_stage5_contabilidad'])
        self.assertIn('stage5.stage3_evidence_ref_missing', {issue['code'] for issue in result['issues']})

    def test_command_writes_json_and_rejects_versionable_repo_output(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage5_readiness.json'
            call_command('audit_stage5_contabilidad_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage5.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('ledger', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage5-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage5_contabilidad_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage5_contabilidad_readiness', fail_on_attention=True, stdout=StringIO())
