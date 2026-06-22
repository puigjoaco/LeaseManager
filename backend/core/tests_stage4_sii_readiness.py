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

from audit.models import AuditEvent
from cobranza.models import PagoMensual
from cobranza.services import sync_payment_distribution
from contabilidad.models import (
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    ObligacionTributariaMensual,
    RegimenTributarioEmpresa,
)
from contabilidad.services import ensure_default_regime
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from core.stage4_sii_readiness import collect_stage4_sii_readiness
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from sii.models import (
    AmbienteSII,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DTEEmitido,
    EstadoDTE,
    EstadoGateSII,
    F22PreparacionAnual,
    F29PreparacionMensual,
    ProcesoRentaAnual,
)


class Stage4SiiReadinessTests(TestCase):
    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='Empresa Stage4 SpA', rut='88888888-8'):
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

    def _sii_readiness_fields(self, prefix):
        return {
            'certificado_ref': f'certificado-{prefix}-ref',
            'evidencia_ref': f'evidencia-{prefix}-gate',
            'prueba_flujo_ref': f'prueba-{prefix}-flujo',
            'autorizacion_ambiente_ref': f'ambiente-{prefix}-certificacion',
            'regla_fiscal_ref': f'regla-{prefix}-validada',
        }

    def _activate_fiscal_config(self, empresa):
        return ConfiguracionFiscalEmpresa.objects.create(
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

    def _open_capability(self, empresa, capability_key, prefix=None, **overrides):
        payload = {
            'empresa': empresa,
            'capacidad_key': capability_key,
            **self._sii_readiness_fields(prefix or capability_key.lower()),
            'ambiente': AmbienteSII.CERTIFICATION,
            'estado_gate': EstadoGateSII.OPEN,
            'ultimo_resultado': {},
        }
        payload.update(overrides)
        return CapacidadTributariaSII.objects.create(**payload)

    def _create_paid_payment(self, empresa):
        propiedad = Propiedad.objects.create(
            direccion='Av Stage4',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='ST4-001',
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Stage4',
            numero_cuenta='ACC-ST4-001',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Stage4',
            rut='44444444-4',
            email='tenant-stage4@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio Stage4',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='SII-ST4-001',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            fecha_entrega=date(2026, 1, 1),
            dia_pago_mensual=5,
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
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base=Decimal('100000.00'),
            moneda_base='CLP',
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        payment = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('100000.00'),
            monto_calculado_clp=Decimal('100111.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('111.00'),
            monto_pagado_clp=Decimal('100111.00'),
            fecha_vencimiento=date(2026, 1, 5),
            fecha_deposito_banco=date(2026, 1, 8),
            estado_pago='pagado',
            dias_mora=3,
            codigo_conciliacion_efectivo='111',
        )
        sync_payment_distribution(payment)
        return payment

    def _create_monthly_tax_inputs(self, empresa):
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
            fecha_preparacion=timezone.now(),
            fecha_aprobacion=timezone.now(),
        )
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible=Decimal('100111.00'),
            monto_calculado=Decimal('10011.10'),
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
        )
        return close

    def _create_valid_local_matrix(self):
        empresa = self._create_active_empresa()
        self._activate_fiscal_config(empresa)
        dte_capability = self._open_capability(empresa, CapacidadSII.DTE_EMISION, 'dte')
        self._open_capability(empresa, CapacidadSII.DTE_CONSULTA, 'dte-status')
        f29_capability = self._open_capability(empresa, CapacidadSII.F29_PREPARACION, 'f29')
        payment = self._create_paid_payment(empresa)
        distribution = payment.distribuciones_cobro.get()
        DTEEmitido.objects.create(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=payment.contrato,
            pago_mensual=payment,
            distribucion_cobro_mensual=distribution,
            arrendatario=payment.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision=date(2026, 1, 8),
            estado_dte=EstadoDTE.SENT_MANUAL,
            sii_track_id='track-stage4-controlled',
            ultimo_estado_sii='Recibido controlado',
        )
        close = self._create_monthly_tax_inputs(empresa)
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
            borrador_ref='f29-stage4-controlled',
            responsable_revision_ref='tax-reviewer-f29-stage4-controlled',
        )
        return empresa

    def _collect_with_final_refs(self):
        return collect_stage4_sii_readiness(
            stage5_evidence_ref='stage5-ledger-controlled-v1',
            environment_proof_ref='sii-certification-proof-v1',
            fiscal_rule_ref='tax-rule-expert-v1',
            responsible_ref='stage4-responsibles-v1',
            source_label='stage4-controlled-v1',
            authorization_ref='stage4-authorization-v1',
            source_kind='snapshot_controlado',
        )

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_stage4_sii_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage4.source_kind_not_authorized', issue_codes)
        self.assertIn('stage4.fiscal_config_missing', issue_codes)
        self.assertIn('stage4.dte.open_capability_missing', issue_codes)
        self.assertIn('stage4.dte_status.open_capability_missing', issue_codes)
        self.assertIn('stage4.f29_missing', issue_codes)
        self.assertIn('stage4.environment_proof_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_state_changed_event_without_transition_metadata_is_blocking(self):
        AuditEvent.objects.create(
            event_type='sii.capacidad_sii.state_changed',
            entity_type='capacidad_sii',
            entity_id='1',
            summary='Capacidad SII heredada sin metadata de transicion.',
            metadata={'estado_nuevo': EstadoGateSII.OPEN},
        )

        result = collect_stage4_sii_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage4.audit.state_transition_metadata_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['state_transition_metadata_missing'], 1)

    def test_status_updated_event_without_transition_metadata_is_blocking(self):
        AuditEvent.objects.create(
            event_type='sii.f29_preparacion.status_updated',
            entity_type='f29_preparacion',
            entity_id='1',
            summary='Actualizacion SII heredada sin metadata de transicion.',
            metadata={'estado_nuevo': EstadoPreparacionTributaria.PREPARED},
        )

        result = collect_stage4_sii_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage4.audit.status_transition_metadata_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['status_transition_metadata_missing'], 1)

    def test_valid_authorized_matrix_and_non_sensitive_refs_can_pass_readiness(self):
        self._create_valid_local_matrix()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage4_sii'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertTrue(result['sections']['source_trace']['source_label'])
        self.assertTrue(result['sections']['source_trace']['authorization_ref'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_matrix_and_non_sensitive_refs_cannot_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage4_sii_readiness(
            stage5_evidence_ref='stage5-ledger-controlled-v1',
            environment_proof_ref='sii-certification-proof-v1',
            fiscal_rule_ref='tax-rule-expert-v1',
            responsible_ref='stage4-responsibles-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage4.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_valid_local_matrix()

        result = collect_stage4_sii_readiness(
            stage5_evidence_ref='stage5-ledger-controlled-v1',
            environment_proof_ref='sii-certification-proof-v1',
            fiscal_rule_ref='tax-rule-expert-v1',
            responsible_ref='stage4-responsibles-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage4.source_label_missing', issue_codes)
        self.assertIn('stage4.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_authorized_source_sensitive_trace_refs_are_classified(self):
        self._create_valid_local_matrix()

        result = collect_stage4_sii_readiness(
            stage5_evidence_ref='stage5-ledger-controlled-v1',
            environment_proof_ref='sii-certification-proof-v1',
            fiscal_rule_ref='tax-rule-expert-v1',
            responsible_ref='stage4-responsibles-v1',
            source_kind='snapshot_controlado',
            source_label='https://example.test/stage4?signed_token=secret',
            authorization_ref='Bearer stage4-secret-token',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertIn('stage4.source_label_sensitive', issue_codes)
        self.assertIn('stage4.authorization_ref_sensitive', issue_codes)
        self.assertNotIn('stage4.source_label_missing', issue_codes)
        self.assertNotIn('stage4.authorization_ref_missing', issue_codes)
        self.assertTrue(result['sections']['source_trace_sensitive']['source_label'])
        self.assertTrue(result['sections']['source_trace_sensitive']['authorization_ref'])
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_authorized_source_sensitive_final_refs_are_classified(self):
        self._create_valid_local_matrix()

        result = collect_stage4_sii_readiness(
            source_kind='snapshot_controlado',
            source_label='stage4-controlled-source-v1',
            authorization_ref='stage4-authorization-v1',
            stage5_evidence_ref='https://example.test/stage5?signed_token=secret',
            environment_proof_ref='https://example.test/sii-env?signed_token=secret',
            fiscal_rule_ref='https://example.test/fiscal-rule?signed_token=secret',
            responsible_ref='Bearer stage4-responsible-secret',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        expected_sensitive_codes = {
            'stage4.stage5_evidence_ref_sensitive',
            'stage4.environment_proof_ref_sensitive',
            'stage4.fiscal_rule_ref_sensitive',
            'stage4.responsible_ref_sensitive',
        }
        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertTrue(expected_sensitive_codes.issubset(issue_codes))
        self.assertNotIn('stage4.stage5_evidence_ref_missing', issue_codes)
        self.assertNotIn('stage4.environment_proof_ref_missing', issue_codes)
        self.assertNotIn('stage4.fiscal_rule_ref_missing', issue_codes)
        self.assertNotIn('stage4.responsible_ref_missing', issue_codes)
        for key in ('stage5_evidence_ref', 'environment_proof_ref', 'fiscal_rule_ref', 'responsible_ref'):
            self.assertTrue(result['sections']['final_evidence_sensitive'][key])
            self.assertFalse(result['sections']['final_evidence'][key])

    def test_capabilities_dte_and_f29_require_same_company_fiscal_config(self):
        empresa_con_config = self._create_active_empresa(nombre='Empresa Fiscal Stage4 SpA', rut='77777777-7')
        self._activate_fiscal_config(empresa_con_config)
        empresa_sin_config = Empresa.objects.create(
            razon_social='Empresa SII Sin Config SpA',
            rut='99999999-9',
            estado='activa',
        )
        dte_capability = self._open_capability(empresa_sin_config, CapacidadSII.DTE_EMISION, 'dte-sin-config')
        f29_capability = self._open_capability(empresa_sin_config, CapacidadSII.F29_PREPARACION, 'f29-sin-config')
        payment = self._create_paid_payment(empresa_sin_config)
        distribution = payment.distribuciones_cobro.get()
        DTEEmitido.objects.create(
            empresa=empresa_sin_config,
            capacidad_tributaria=dte_capability,
            contrato=payment.contrato,
            pago_mensual=payment,
            distribucion_cobro_mensual=distribution,
            arrendatario=payment.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision=date(2026, 1, 8),
            estado_dte=EstadoDTE.SENT_MANUAL,
            sii_track_id='track-stage4-sin-config',
            ultimo_estado_sii='Recibido controlado',
        )
        close = self._create_monthly_tax_inputs(empresa_sin_config)
        F29PreparacionMensual.objects.create(
            empresa=empresa_sin_config,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
            borrador_ref='f29-stage4-sin-config',
            responsable_revision_ref='tax-reviewer-f29-stage4-sin-config',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.capability_fiscal_config_missing', issue_codes)
        self.assertIn('stage4.dte_fiscal_config_missing', issue_codes)
        self.assertIn('stage4.f29_fiscal_config_missing', issue_codes)
        self.assertEqual(result['sections']['capabilities']['open_without_active_fiscal_config'], 2)

    def test_unsupported_fiscal_regime_is_blocking(self):
        empresa = self._create_valid_local_matrix()
        unsupported_regime = RegimenTributarioEmpresa.objects.create(
            codigo_regimen='RentaPresuntaV1',
            descripcion='Regimen no automatizable en v1',
            estado='activa',
        )
        ConfiguracionFiscalEmpresa.objects.filter(empresa=empresa).update(
            regimen_tributario=unsupported_regime,
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.fiscal_config_unsupported_regime', issue_codes)
        self.assertIn('stage4.capability_invalid', issue_codes)
        self.assertEqual(result['sections']['fiscal_setup']['unsupported_active_regime'], 1)

    def test_open_capability_without_readiness_refs_is_blocking(self):
        empresa = self._create_active_empresa()
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.DTE_EMISION,
            certificado_ref='cert-stage4',
            ambiente=AmbienteSII.CERTIFICATION,
            estado_gate=EstadoGateSII.OPEN,
        )

        result = collect_stage4_sii_readiness()

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.capability_invalid', {issue['code'] for issue in result['issues']})

    def test_dte_external_state_without_tracking_or_status_is_blocking(self):
        empresa = self._create_valid_local_matrix()
        DTEEmitido.objects.update(estado_dte=EstadoDTE.ACCEPTED, sii_track_id='', ultimo_estado_sii='')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.dte_external_tracking_missing', issue_codes)
        self.assertIn('stage4.dte_external_status_missing', issue_codes)
        self.assertEqual(empresa.estado, 'activa')

    def test_dte_and_f29_advanced_state_without_ready_capability_is_blocking(self):
        self._create_valid_local_matrix()
        CapacidadTributariaSII.objects.filter(capacidad_key=CapacidadSII.DTE_EMISION).update(
            estado_gate=EstadoGateSII.CONDITIONED
        )
        CapacidadTributariaSII.objects.filter(capacidad_key=CapacidadSII.F29_PREPARACION).update(
            estado_gate=EstadoGateSII.CONDITIONED
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.dte_capability_not_ready', issue_codes)
        self.assertIn('stage4.f29_capability_not_ready', issue_codes)
        self.assertEqual(result['sections']['dte']['external_capability_not_ready'], 1)
        self.assertEqual(result['sections']['f29']['capability_not_ready'], 1)

    def test_final_dte_status_without_status_query_capability_is_blocking(self):
        self._create_valid_local_matrix()
        CapacidadTributariaSII.objects.filter(capacidad_key=CapacidadSII.DTE_CONSULTA).delete()
        DTEEmitido.objects.update(
            estado_dte=EstadoDTE.ACCEPTED,
            sii_track_id='dte-final-track-001',
            ultimo_estado_sii='Aceptado',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.dte_status.open_capability_missing', issue_codes)
        self.assertIn('stage4.dte_status_query_capability_not_ready', issue_codes)
        self.assertEqual(result['sections']['dte']['status_query_capability_not_ready'], 1)

    def test_artifacts_with_wrong_sii_capability_kind_are_blocking(self):
        empresa = self._create_valid_local_matrix()
        dte_capability = CapacidadTributariaSII.objects.get(
            empresa=empresa,
            capacidad_key=CapacidadSII.DTE_EMISION,
        )
        f29_capability = CapacidadTributariaSII.objects.get(
            empresa=empresa,
            capacidad_key=CapacidadSII.F29_PREPARACION,
        )
        DTEEmitido.objects.update(capacidad_tributaria=f29_capability)
        F29PreparacionMensual.objects.update(capacidad_tributaria=dte_capability)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.dte_invalid', issue_codes)
        self.assertIn('stage4.f29_invalid', issue_codes)
        self.assertEqual(result['sections']['dte']['invalid_model'], 1)
        self.assertEqual(result['sections']['f29']['invalid_model'], 1)

    def test_f29_presented_or_approved_without_ref_is_blocking(self):
        self._create_valid_local_matrix()
        F29PreparacionMensual.objects.update(
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='',
            responsable_revision_ref='tax-reviewer-f29-local',
        )

        result = self._collect_with_final_refs()
        self.assertIn('stage4.f29_ref_missing', {issue['code'] for issue in result['issues']})

        F29PreparacionMensual.objects.update(
            estado_preparacion=EstadoPreparacionTributaria.PRESENTED,
            borrador_ref='f29-presented-local',
            responsable_revision_ref='tax-reviewer-f29-local',
        )
        result = self._collect_with_final_refs()
        self.assertIn('stage4.f29_presented_boundary', {issue['code'] for issue in result['issues']})

    def test_f29_approved_without_responsible_ref_is_blocking(self):
        self._create_valid_local_matrix()
        F29PreparacionMensual.objects.update(
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f29-approved-local',
            responsable_revision_ref='',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('stage4.f29_responsible_ref_missing', issue_codes)
        self.assertEqual(result['sections']['f29']['responsible_ref_missing'], 1)

    def test_annual_artifacts_without_ready_capability_are_blocking(self):
        empresa = self._create_valid_local_matrix()
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            fecha_preparacion=timezone.now(),
            resumen_anual={'source': 'stage4-controlled'},
            paquete_ddjj_ref='ddjj-stage4-controlled',
            borrador_f22_ref='f22-stage4-controlled',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'source': 'stage4-controlled'},
            paquete_ref='ddjj-stage4-controlled',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'source': 'stage4-controlled'},
            borrador_ref='f22-stage4-controlled',
        )
        ddjj_capability.estado_gate = EstadoGateSII.CONDITIONED
        ddjj_capability.save(update_fields=['estado_gate', 'updated_at'])
        f22_capability.estado_gate = EstadoGateSII.CONDITIONED
        f22_capability.save(update_fields=['estado_gate', 'updated_at'])

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.ddjj_capability_not_ready', issue_codes)
        self.assertIn('stage4.f22_capability_not_ready', issue_codes)
        self.assertEqual(result['sections']['annual']['ddjj_capability_not_ready'], 1)
        self.assertEqual(result['sections']['annual']['f22_capability_not_ready'], 1)

    def test_annual_artifacts_with_wrong_capability_kind_are_blocking(self):
        empresa = self._create_valid_local_matrix()
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            fecha_preparacion=timezone.now(),
            resumen_anual={'source': 'stage4-controlled'},
            paquete_ddjj_ref='ddjj-stage4-controlled',
            borrador_f22_ref='f22-stage4-controlled',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_paquete={'source': 'stage4-controlled'},
            paquete_ref='ddjj-stage4-controlled',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            resumen_f22={'source': 'stage4-controlled'},
            borrador_ref='f22-stage4-controlled',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.ddjj_invalid', issue_codes)
        self.assertIn('stage4.f22_invalid', issue_codes)
        self.assertEqual(result['sections']['annual']['ddjj_invalid_model'], 1)
        self.assertEqual(result['sections']['annual']['f22_invalid_model'], 1)

    def test_production_capability_without_authorization_is_blocking(self):
        empresa = self._create_active_empresa()
        self._activate_fiscal_config(empresa)
        self._open_capability(
            empresa,
            CapacidadSII.DTE_EMISION,
            'prod',
            ambiente=AmbienteSII.PRODUCTION,
            ultimo_resultado={},
        )

        result = collect_stage4_sii_readiness()

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.capability_invalid', {issue['code'] for issue in result['issues']})

    def test_sensitive_final_refs_do_not_close_readiness(self):
        self._create_valid_local_matrix()

        result = collect_stage4_sii_readiness(
            stage5_evidence_ref='stage5-ledger-controlled-v1',
            environment_proof_ref='https://sii.example/proof',
            fiscal_rule_ref='tax-rule-expert-v1',
            responsible_ref='stage4-responsibles-v1',
            source_label='stage4-controlled-v1',
            authorization_ref='stage4-authorization-v1',
            source_kind='snapshot_controlado',
        )

        self.assertFalse(result['ready_for_stage4_sii'])
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertIn('stage4.environment_proof_ref_sensitive', issue_codes)
        self.assertNotIn('stage4.environment_proof_ref_missing', issue_codes)
        self.assertTrue(result['sections']['final_evidence_sensitive']['environment_proof_ref'])

    def test_sensitive_sii_operational_refs_do_not_close_readiness(self):
        self._create_valid_local_matrix()
        CapacidadTributariaSII.objects.update(
            certificado_ref='https://sii.example.test/cert?token=secret',
            ultimo_resultado={'api_key': None},
        )
        DTEEmitido.objects.update(sii_track_id='https://sii.example.test/track?token=secret')
        F29PreparacionMensual.objects.update(
            borrador_ref='https://sii.example.test/f29?token=secret',
            responsable_revision_ref='https://sii.example.test/reviewer?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.capability_sensitive_reference', issue_codes)
        self.assertIn('stage4.dte_sensitive_tracking_ref', issue_codes)
        self.assertIn('stage4.f29_sensitive_ref', issue_codes)
        self.assertIn('stage4.f29_responsible_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['capabilities']['open_sensitive_refs'], 3)
        self.assertEqual(result['sections']['dte']['sensitive_tracking_ref'], 1)
        self.assertEqual(result['sections']['f29']['sensitive_ref'], 1)
        self.assertEqual(result['sections']['f29']['sensitive_responsible_ref'], 1)
        self.assertNotIn('api_key', json.dumps(result))

    def test_control_sensitive_sii_operational_refs_do_not_close_readiness(self):
        self._create_valid_local_matrix()
        CapacidadTributariaSII.objects.update(
            certificado_ref='cert_11.111.111-1',
            ultimo_resultado={'source_ref': 'source_C:/Privado/cert.json'},
        )
        DTEEmitido.objects.update(sii_track_id='track_11.111.111-1')
        F29PreparacionMensual.objects.update(
            borrador_ref='source_C:/Privado/f29.pdf',
            responsable_revision_ref='review_11.111.111-1',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.capability_sensitive_reference', issue_codes)
        self.assertIn('stage4.dte_sensitive_tracking_ref', issue_codes)
        self.assertIn('stage4.f29_sensitive_ref', issue_codes)
        self.assertIn('stage4.f29_responsible_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['capabilities']['open_sensitive_refs'], 3)
        self.assertEqual(result['sections']['dte']['sensitive_tracking_ref'], 1)
        self.assertEqual(result['sections']['f29']['sensitive_ref'], 1)
        self.assertEqual(result['sections']['f29']['sensitive_responsible_ref'], 1)
        serialized_result = json.dumps(result)
        self.assertNotIn('11.111.111-1', serialized_result)
        self.assertNotIn('C:/Privado', serialized_result)

    def test_sensitive_tax_payload_keys_do_not_close_readiness(self):
        empresa = self._create_valid_local_matrix()
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        F29PreparacionMensual.objects.update(resumen_formulario={'access_token': None})
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.PREPARED,
            fecha_preparacion=timezone.now(),
            resumen_anual={'credential': None},
            paquete_ddjj_ref='ddjj-stage4-controlled',
            borrador_f22_ref='f22-stage4-controlled',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete={'resumen_anual': {'fiscal_year': 2026}, 'api_key': None},
            paquete_ref='ddjj-stage4-controlled',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'resumen_anual': {'fiscal_year': 2026}, 'secret': None},
            borrador_ref='f22-stage4-controlled',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.f29_sensitive_payload', issue_codes)
        self.assertIn('stage4.annual_process_sensitive_payload', issue_codes)
        self.assertIn('stage4.ddjj_sensitive_payload', issue_codes)
        self.assertIn('stage4.f22_sensitive_payload', issue_codes)
        self.assertEqual(result['sections']['f29']['sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual']['process_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual']['ddjj_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual']['f22_sensitive_payload'], 1)
        self.assertNotIn('api_key', json.dumps(result))

    def test_control_sensitive_tax_payload_values_do_not_close_readiness(self):
        empresa = self._create_valid_local_matrix()
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        F29PreparacionMensual.objects.update(resumen_formulario={'source_ref': 'source_11.111.111-1'})
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.PREPARED,
            fecha_preparacion=timezone.now(),
            resumen_anual={'support_ref': 'source_C:/Privado/renta.xlsx'},
            paquete_ddjj_ref='ddjj-stage4-controlled',
            borrador_f22_ref='f22-stage4-controlled',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete={'resumen_anual': {'fiscal_year': 2026}, 'source_ref': 'source_11.111.111-1'},
            paquete_ref='ddjj-stage4-controlled',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'resumen_anual': {'fiscal_year': 2026}, 'support_ref': 'source_C:/Privado/f22.xlsx'},
            borrador_ref='f22-stage4-controlled',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.f29_sensitive_payload', issue_codes)
        self.assertIn('stage4.annual_process_sensitive_payload', issue_codes)
        self.assertIn('stage4.ddjj_sensitive_payload', issue_codes)
        self.assertIn('stage4.f22_sensitive_payload', issue_codes)
        self.assertEqual(result['sections']['f29']['sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual']['process_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual']['ddjj_sensitive_payload'], 1)
        self.assertEqual(result['sections']['annual']['f22_sensitive_payload'], 1)
        serialized_result = json.dumps(result)
        self.assertNotIn('11.111.111-1', serialized_result)
        self.assertNotIn('C:/Privado', serialized_result)

    def test_sensitive_tax_observations_do_not_close_readiness(self):
        empresa = self._create_valid_local_matrix()
        ddjj_capability = self._open_capability(empresa, CapacidadSII.DDJJ_PREPARACION, 'ddjj')
        f22_capability = self._open_capability(empresa, CapacidadSII.F22_PREPARACION, 'f22')
        DTEEmitido.objects.update(observaciones='No exponer https://sii.example.test/dte?token=secret')
        F29PreparacionMensual.objects.update(observaciones='No exponer https://sii.example.test/f29?token=secret')
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.PREPARED,
            fecha_preparacion=timezone.now(),
            resumen_anual={'source': 'stage4-controlled'},
            paquete_ddjj_ref='ddjj-stage4-controlled',
            borrador_f22_ref='f22-stage4-controlled',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete={'resumen_anual': {'fiscal_year': 2026}},
            paquete_ref='ddjj-stage4-controlled',
            observaciones='No exponer https://sii.example.test/ddjj?token=secret',
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'resumen_anual': {'fiscal_year': 2026}},
            borrador_ref='f22-stage4-controlled',
            observaciones='No exponer https://sii.example.test/f22?token=secret',
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage4_sii'])
        self.assertIn('stage4.dte_sensitive_observations', issue_codes)
        self.assertIn('stage4.f29_sensitive_observations', issue_codes)
        self.assertIn('stage4.ddjj_sensitive_observations', issue_codes)
        self.assertIn('stage4.f22_sensitive_observations', issue_codes)
        self.assertEqual(result['sections']['dte']['sensitive_observations'], 1)
        self.assertEqual(result['sections']['f29']['sensitive_observations'], 1)
        self.assertEqual(result['sections']['annual']['ddjj_sensitive_observations'], 1)
        self.assertEqual(result['sections']['annual']['f22_sensitive_observations'], 1)
        self.assertNotIn('sii.example.test', json.dumps(result))

    def test_command_writes_json_and_rejects_versionable_repo_output(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'stage4_readiness.json'
            call_command('audit_stage4_sii_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('stage4.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('capabilities', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage4-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage4_sii_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_stage4_sii_readiness', fail_on_attention=True, stdout=StringIO())
