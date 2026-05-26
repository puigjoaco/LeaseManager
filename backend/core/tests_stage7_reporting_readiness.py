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

from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EstadoPreparacionTributaria,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    TipoMovimientoAsiento,
)
from contabilidad.services import ensure_default_regime
from core.stage7_reporting_readiness import collect_stage7_reporting_readiness
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio
from sii.models import CapacidadTributariaSII, DDJJPreparacionAnual, F22PreparacionAnual, ProcesoRentaAnual


class Stage7ReportingReadinessTests(TestCase):
    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='Empresa Stage7 Reporting SpA', rut='77777777-7'):
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

    def _create_accounts(self, empresa):
        debit = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='1101',
            nombre='Banco',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        credit = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='4101',
            nombre='Ingresos',
            naturaleza='acreedora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        return debit, credit

    def _activate_fiscal_config(self, empresa):
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=['1887'],
            inicio_ejercicio=date(2026, 1, 1),
            moneda_funcional='CLP',
            estado='activa',
        )

    def _create_posted_event_and_asiento(self, empresa, debit, credit, *, amount=Decimal('100000.00')):
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='pago_mensual',
            entidad_origen_id='stage7-payment-1',
            fecha_operativa=date(2026, 1, 10),
            moneda='CLP',
            monto_base=amount,
            payload_resumen={'source': 'stage7-reporting-controlled'},
            idempotency_key=f'stage7-reporting-event-{empresa.pk}',
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
            cuenta_contable=debit,
            tipo_movimiento=TipoMovimientoAsiento.DEBIT,
            monto=amount,
            glosa='Pago conciliado controlado',
        )
        MovimientoAsiento.objects.create(
            asiento_contable=asiento,
            cuenta_contable=credit,
            tipo_movimiento=TipoMovimientoAsiento.CREDIT,
            monto=amount,
            glosa='Pago conciliado controlado',
        )
        return event, asiento

    def _create_approved_close_and_snapshots(self, empresa):
        now = timezone.now()
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
            fecha_preparacion=now,
            fecha_aprobacion=now,
            resumen_obligaciones={'source': 'stage7-reporting-controlled'},
        )
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible=Decimal('100000.00'),
            monto_calculado=Decimal('10000.00'),
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
        )
        LibroDiario.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'asientos': [{'id': 'stage7'}]},
        )
        LibroMayor.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'cuentas': [{'codigo': '1101'}]},
        )
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'total_debe': '100000.00', 'total_haber': '100000.00', 'cuadrado': True},
        )

    def _annual_summary(self):
        return {
            'fiscal_year': 2026,
            'obligaciones': [{'anio': 2026, 'mes': 1, 'tipo': 'PPM', 'monto_calculado': '10000.00'}],
            'total_obligaciones': 1,
        }

    def _create_annual_reporting_sources(self, empresa):
        summary = self._annual_summary()
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.PREPARED,
            fecha_preparacion=timezone.now(),
            resumen_anual=summary,
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            certificado_ref='cert-ddjj-stage7',
            ambiente='certificacion',
            estado_gate='condicionado',
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            certificado_ref='cert-f22-stage7',
            ambiente='certificacion',
            estado_gate='condicionado',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1'},
        )
        return process

    def _create_valid_local_matrix(self):
        empresa = self._create_active_empresa()
        self._activate_fiscal_config(empresa)
        debit, credit = self._create_accounts(empresa)
        self._create_posted_event_and_asiento(empresa, debit, credit)
        self._create_approved_close_and_snapshots(empresa)
        self._create_annual_reporting_sources(empresa)
        return empresa

    def _collect_with_final_refs(self):
        return collect_stage7_reporting_readiness(
            stage5_evidence_ref='stage5-ledger-reporting-controlled-v1',
            stage6_evidence_ref='stage6-annual-reporting-controlled-v1',
            reporting_api_proof_ref='reporting-api-controlled-v1',
            backoffice_visual_ref='backoffice-reporting-controlled-v1',
            responsible_ref='stage7-reporting-responsibles-v1',
            source_label='stage7-reporting-controlled-v1',
            authorization_ref='stage7-reporting-authorization-v1',
            source_kind='snapshot_controlado',
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage7_reporting_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage7.reporting.source_kind_not_authorized', issue_codes)
        self.assertIn('stage7.reporting.approved_close_missing', issue_codes)
        self.assertIn('stage7.reporting.posted_events_missing', issue_codes)
        self.assertIn('stage7.reporting.books_snapshots_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_process_missing', issue_codes)
        self.assertIn('stage7.reporting.api_proof_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_valid_local_matrix()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage7_reporting'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertTrue(result['sections']['source_trace']['source_label'])
        self.assertTrue(result['sections']['source_trace']['authorization_ref'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_matrix_and_non_sensitive_refs_cannot_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage7_reporting_readiness(
            stage5_evidence_ref='stage5-ledger-reporting-controlled-v1',
            stage6_evidence_ref='stage6-annual-reporting-controlled-v1',
            reporting_api_proof_ref='reporting-api-controlled-v1',
            backoffice_visual_ref='backoffice-reporting-controlled-v1',
            responsible_ref='stage7-reporting-responsibles-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage7.reporting.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_valid_local_matrix()

        result = collect_stage7_reporting_readiness(
            stage5_evidence_ref='stage5-ledger-reporting-controlled-v1',
            stage6_evidence_ref='stage6-annual-reporting-controlled-v1',
            reporting_api_proof_ref='reporting-api-controlled-v1',
            backoffice_visual_ref='backoffice-reporting-controlled-v1',
            responsible_ref='stage7-reporting-responsibles-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage7.reporting.source_label_missing', issue_codes)
        self.assertIn('stage7.reporting.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_posted_event_without_origin_or_asiento_is_blocking(self):
        empresa = self._create_active_empresa(nombre='EventGapCo', rut='87878787-8')
        self._create_approved_close_and_snapshots(empresa)
        self._create_annual_reporting_sources(empresa)
        EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='',
            entidad_origen_id='',
            fecha_operativa=date(2026, 1, 10),
            moneda='CLP',
            monto_base=Decimal('100000.00'),
            payload_resumen={},
            idempotency_key='stage7-event-without-origin',
            estado_contable=EstadoEventoContable.POSTED,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.event_origin_missing', issue_codes)
        self.assertIn('stage7.reporting.accounting_entry_missing', issue_codes)

    def test_annual_reporting_sources_require_same_company_fiscal_config(self):
        empresa = self._create_valid_local_matrix()
        ConfiguracionFiscalEmpresa.objects.filter(empresa=empresa).delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.annual_process_fiscal_config_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_ddjj_fiscal_config_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_f22_fiscal_config_missing', issue_codes)
        self.assertEqual(result['sections']['annual_tax']['processes_without_active_fiscal_config'], 1)
        self.assertEqual(result['sections']['annual_tax']['ddjj_without_active_fiscal_config'], 1)
        self.assertEqual(result['sections']['annual_tax']['f22_without_active_fiscal_config'], 1)

    def test_accounting_entry_without_hash_or_movements_is_blocking(self):
        empresa = self._create_valid_local_matrix()
        AsientoContable.objects.update(hash_integridad='')
        MovimientoAsiento.objects.all().delete()

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.accounting_entry_hash_missing', issue_codes)
        self.assertIn('stage7.reporting.accounting_entry_movements_missing', issue_codes)
        self.assertEqual(empresa.estado, 'activa')

    def test_accounting_entry_with_stale_hash_is_blocking(self):
        self._create_valid_local_matrix()
        asiento = AsientoContable.objects.get()
        asiento.fecha_contable = date(2026, 1, 11)
        asiento.save(update_fields=['fecha_contable', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.accounting_entry_hash_mismatch', issue_codes)
        self.assertEqual(result['sections']['financial_monthly']['asiento_hash_mismatch'], 1)

    def test_book_snapshot_gaps_are_blocking(self):
        empresa = self._create_valid_local_matrix()
        LibroMayor.objects.all().delete()

        result = self._collect_with_final_refs()
        self.assertIn('stage7.reporting.books_snapshot_missing_for_close', {issue['code'] for issue in result['issues']})

        LibroMayor.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            resumen={'cuentas': [{'codigo': '1101'}]},
        )
        BalanceComprobacion.objects.update(resumen={'total_debe': '100.00', 'total_haber': '90.00', 'cuadrado': False})
        result = self._collect_with_final_refs()
        self.assertIn('stage7.reporting.books_balance_not_square', {issue['code'] for issue in result['issues']})

    def test_annual_summary_documents_and_refs_are_blocking(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={},
            paquete_ddjj_ref='',
            borrador_f22_ref='',
        )
        DDJJPreparacionAnual.objects.update(estado_preparacion=EstadoPreparacionTributaria.APPROVED, paquete_ref='', resumen_paquete={})
        F22PreparacionAnual.objects.update(estado_preparacion=EstadoPreparacionTributaria.APPROVED, borrador_ref='', resumen_f22={})

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.annual_summary_incomplete', issue_codes)
        self.assertIn('stage7.reporting.annual_process_ddjj_ref_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_process_f22_ref_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_ddjj_summary_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_f22_summary_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_ddjj_ref_missing', issue_codes)
        self.assertIn('stage7.reporting.annual_f22_ref_missing', issue_codes)

    def test_annual_reporting_wrong_fiscal_year_is_blocking(self):
        self._create_valid_local_matrix()
        wrong_summary = {
            'fiscal_year': 2025,
            'obligaciones': [{'anio': 2025, 'mes': 1, 'tipo': 'PPM'}],
            'total_obligaciones': 1,
        }
        ProcesoRentaAnual.objects.update(resumen_anual=wrong_summary)
        DDJJPreparacionAnual.objects.update(
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': wrong_summary}
        )
        F22PreparacionAnual.objects.update(
            resumen_f22={'resumen_anual': wrong_summary, 'regimen_tributario': 'propyme-general-v1'}
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.annual_fiscal_year_mismatch', issue_codes)
        self.assertIn('stage7.reporting.annual_ddjj_fiscal_year_mismatch', issue_codes)
        self.assertIn('stage7.reporting.annual_f22_fiscal_year_mismatch', issue_codes)

    def test_annual_reporting_sensitive_payload_keys_are_blocking(self):
        self._create_valid_local_matrix()
        summary = self._annual_summary()
        ProcesoRentaAnual.objects.update(resumen_anual={**summary, 'api_key': None})
        DDJJPreparacionAnual.objects.update(
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': summary, 'access_token': None}
        )
        F22PreparacionAnual.objects.update(
            resumen_f22={'resumen_anual': summary, 'regimen_tributario': 'propyme-general-v1', 'credential': None}
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.annual_process_sensitive_payload', issue_codes)
        self.assertIn('stage7.reporting.annual_ddjj_sensitive_payload', issue_codes)
        self.assertIn('stage7.reporting.annual_f22_sensitive_payload', issue_codes)
        self.assertEqual(result['sections']['annual_tax']['process_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual_tax']['ddjj_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual_tax']['f22_sensitive_payload'], 1)
        self.assertNotIn('api_key', json.dumps(result))

    def test_annual_reporting_sensitive_final_refs_are_classified_explicitly(self):
        self._create_valid_local_matrix()
        ProcesoRentaAnual.objects.update(
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
        )
        DDJJPreparacionAnual.objects.update(paquete_ref='https://sii.example.test/ddjj?token=secret')
        F22PreparacionAnual.objects.update(borrador_ref='https://sii.example.test/f22?token=secret')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.annual_process_ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage7.reporting.annual_process_f22_ref_sensitive', issue_codes)
        self.assertIn('stage7.reporting.annual_ddjj_ref_sensitive', issue_codes)
        self.assertIn('stage7.reporting.annual_f22_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['annual_tax']['process_ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_tax']['process_f22_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_tax']['ddjj_ref_sensitive'], 1)
        self.assertEqual(result['sections']['annual_tax']['f22_ref_sensitive'], 1)
        self.assertNotIn('token=secret', json.dumps(result))

    def test_sensitive_final_refs_and_command_behaviour(self):
        self._create_valid_local_matrix()

        result = collect_stage7_reporting_readiness(
            stage5_evidence_ref='stage5-ledger-reporting-controlled-v1',
            stage6_evidence_ref='stage6-annual-reporting-controlled-v1',
            reporting_api_proof_ref='https://reporting.example/api-proof',
            backoffice_visual_ref='backoffice-reporting-controlled-v1',
            responsible_ref='stage7-reporting-responsibles-v1',
            source_label='stage7-reporting-controlled-v1',
            authorization_ref='stage7-reporting-authorization-v1',
            source_kind='snapshot_controlado',
        )
        self.assertFalse(result['ready_for_stage7_reporting'])
        self.assertIn('stage7.reporting.api_proof_ref_missing', {issue['code'] for issue in result['issues']})

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage7_reporting_readiness.json'
            call_command('audit_stage7_reporting_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage7.reporting.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('financial_monthly', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage7-reporting-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage7_reporting_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage7_reporting_readiness', fail_on_attention=True, stdout=StringIO())
