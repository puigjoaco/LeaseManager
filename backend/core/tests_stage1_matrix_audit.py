from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from cobranza.models import (
    AjusteContrato,
    DistribucionCobroMensual,
    EstadoGarantia,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    TipoMovimientoGarantia,
    ValorUFDiario,
)
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from contratos.models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    Contrato,
    ContratoPropiedad,
    EstadoContactoArrendatario,
    EstadoAvisoTermino,
    EstadoCodeudorSolidario,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RolContratoPropiedad,
    TipoArrendatario,
)
from core.stage1_matrix_audit import collect_stage1_matrix_audit
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
from patrimonio.models import (
    ComunidadPatrimonial,
    Empresa,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
    TipoInmueble,
)


class Stage1MatrixAuditTests(TestCase):
    def _create_valid_stage1_matrix(self):
        socio_1 = Socio.objects.create(nombre='Socio Controlado Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Controlado Dos', rut='22222222-2', activo=True)
        empresa = Empresa.objects.create(razon_social='Empresa Controlada SpA', rut='88888888-8', estado='activa')
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
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Controlada', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_1,
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        regimen = RegimenTributarioEmpresa.objects.create(
            codigo_regimen='14D3-CONTROL',
            descripcion='Regimen controlado',
            estado=EstadoRegistro.ACTIVE,
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regimen,
            tasa_ppm_vigente='1.00',
            aplica_ppm=True,
            inicio_ejercicio=date(2026, 1, 1),
            estado=EstadoRegistro.ACTIVE,
        )
        propiedad = Propiedad.objects.create(
            direccion='Direccion Controlada 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-001',
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Controlado',
            numero_cuenta='CTRL-ACC-001',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        identidad_envio = IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=CanalOperacion.EMAIL,
            remitente_visible='LeaseManager Controlado',
            direccion_o_numero='cobranza@example.com',
            credencial_ref='cred-ref-controlada',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=mandato,
            canal=CanalOperacion.EMAIL,
            identidad_envio=identidad_envio,
            prioridad=1,
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario=TipoArrendatario.NATURAL,
            nombre_razon_social='Arrendatario Controlado',
            rut='33333333-3',
            email='arrendatario@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio Controlado 123',
            estado_contacto=EstadoContactoArrendatario.ACTIVE,
        )
        contrato = Contrato.objects.create(
            codigo_contrato='CON-CTRL-001',
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
            codigo_conciliacion_efectivo_snapshot='001',
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        GarantiaContractual.objects.create(contrato=contrato, monto_pactado='0.00')
        return contrato

    def _create_future_contract_for(self, contrato: Contrato) -> Contrato:
        future_contract = Contrato.objects.create(
            codigo_contrato='CON-CTRL-FUT',
            mandato_operacion=contrato.mandato_operacion,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin_vigente=date(2027, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.FUTURE,
        )
        ContratoPropiedad.objects.create(
            contrato=future_contract,
            propiedad=contrato.mandato_operacion.propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='002',
        )
        PeriodoContractual.objects.create(
            contrato=future_contract,
            numero_periodo=1,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        GarantiaContractual.objects.create(contrato=future_contract, monto_pactado='0.00')
        return future_contract

    def _create_payment_for(self, contrato: Contrato) -> PagoMensual:
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        return PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp=Decimal('250000.00'),
            monto_calculado_clp=Decimal('250001.00'),
            monto_pagado_clp=Decimal('0.00'),
            fecha_vencimiento=date(2026, 1, 5),
            codigo_conciliacion_efectivo='001',
        )

    def _collect_controlled_snapshot(self):
        return collect_stage1_matrix_audit(
            source_kind='snapshot_controlado',
            source_label='stage-one-test-snapshot',
            authorization_ref='auth-stage-one-test',
            responsible_ref='responsible-stage-one-test',
            require_data=True,
        )

    def test_empty_database_is_not_evidence_grade_ready(self):
        result = collect_stage1_matrix_audit(source_kind='local')

        self.assertFalse(result['has_required_stage1_data'])
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'implementado_sin_evidencia')

    def test_required_snapshot_reports_aggregate_classification_for_missing_data(self):
        result = self._collect_controlled_snapshot()
        aggregates = result['aggregate_classification']

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(aggregates['socios']['classification'], 'bloqueado_dato_real')
        self.assertTrue(aggregates['socios']['required_for_stage1_close'])
        self.assertEqual(aggregates['contratos_activos_o_futuros']['classification'], 'bloqueado_dato_real')
        self.assertEqual(aggregates['identidades_envio_activas']['classification'], 'bloqueado_dato_real')
        self.assertTrue(aggregates['identidades_envio_activas']['required_for_stage1_close'])
        self.assertEqual(aggregates['asignaciones_canal_activas']['classification'], 'bloqueado_dato_real')
        self.assertTrue(aggregates['asignaciones_canal_activas']['required_for_stage1_close'])
        self.assertEqual(aggregates['codeudores_solidarios']['classification'], 'implementado_sin_evidencia')
        self.assertFalse(aggregates['codeudores_solidarios']['required_for_stage1_close'])

    def test_snapshot_without_active_or_future_contract_is_data_blocked(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.estado = EstadoContrato.FINISHED
        contrato.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['contratos'], 1)
        self.assertEqual(result['summary']['contratos_activos_o_futuros'], 0)
        self.assertFalse(result['has_required_stage1_data'])
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'bloqueado_dato_real')
        self.assertEqual(issue_codes, {'stage1.data_missing'})

    def test_valid_controlled_snapshot_can_pass_stage1_matrix_gate(self):
        self._create_valid_stage1_matrix()

        result = self._collect_controlled_snapshot()

        self.assertTrue(result['has_required_stage1_data'])
        self.assertTrue(result['evidence_grade'])
        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertEqual(result['issue_counts'].get('blocking', 0), 0)
        self.assertGreater(result['summary']['participaciones_patrimoniales'], 0)
        self.assertGreater(result['summary']['representaciones_comunidad'], 0)
        self.assertEqual(result['aggregate_classification']['socios']['classification'], 'resuelto_confirmado')
        self.assertEqual(
            result['aggregate_classification']['codeudores_solidarios']['classification'],
            'resuelto_confirmado',
        )

    def test_active_identity_sensitive_credential_ref_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        identidad = contrato.mandato_operacion.asignaciones_canal.get().identidad_envio
        identidad.credencial_ref = 'https://mail.example.test/token/secret'
        identidad.save(update_fields=['credencial_ref', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.identidad_envio.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['identidades_envio_activas']['classification'],
            'defectuoso',
        )

    def test_active_company_future_only_participations_are_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        future_date = timezone.localdate() + timedelta(days=30)
        ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).update(vigente_desde=future_date)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.empresa.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['empresas']['classification'],
            'defectuoso',
        )

    def test_active_participation_with_inactive_participant_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        socio = ParticipacionPatrimonial.objects.filter(
            empresa_owner=contrato.mandato_operacion.propietario_empresa_owner,
            activo=True,
        ).last().participante_socio
        socio.activo = False
        socio.save(update_fields=['activo', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.participacion.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['participaciones_patrimoniales']['classification'],
            'defectuoso',
        )

    def test_evidence_grade_source_requires_traceable_source_label(self):
        self._create_valid_stage1_matrix()

        result = collect_stage1_matrix_audit(
            source_kind='snapshot_controlado',
            source_label='',
            authorization_ref='auth-stage-one-test',
            responsible_ref='responsible-stage-one-test',
            require_data=True,
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['has_required_stage1_data'])
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.source_label.faltante', issue_codes)

    def test_evidence_grade_source_redacts_sensitive_source_label(self):
        self._create_valid_stage1_matrix()

        result = collect_stage1_matrix_audit(
            source_kind='snapshot_controlado',
            source_label='postgres://user:token@example.test/db',
            authorization_ref='auth-stage-one-test',
            responsible_ref='responsible-stage-one-test',
            require_data=True,
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['source_label'], '<redacted-invalid-source-label>')
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.source_label.sensible', issue_codes)

    def test_evidence_grade_source_requires_authorization_and_responsible_refs(self):
        self._create_valid_stage1_matrix()

        result = collect_stage1_matrix_audit(
            source_kind='snapshot_controlado',
            source_label='stage-one-test-snapshot',
            authorization_ref='',
            responsible_ref='',
            require_data=True,
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['has_required_stage1_data'])
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.authorization_ref.faltante', issue_codes)
        self.assertIn('stage1.responsible_ref.faltante', issue_codes)

    def test_evidence_grade_source_redacts_sensitive_authorization_refs(self):
        self._create_valid_stage1_matrix()

        result = collect_stage1_matrix_audit(
            source_kind='snapshot_controlado',
            source_label='stage-one-test-snapshot',
            authorization_ref='https://example.test/token',
            responsible_ref='user@example.test',
            require_data=True,
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['authorization_ref'], '<redacted-invalid-reference>')
        self.assertEqual(result['responsible_ref'], '<redacted-invalid-reference>')
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.authorization_ref.sensible', issue_codes)
        self.assertIn('stage1.responsible_ref.sensible', issue_codes)

    def test_controlled_snapshot_with_payment_distribution_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('250000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('250000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertEqual(result['summary']['pagos_mensuales'], 1)
        self.assertEqual(result['summary']['distribuciones_cobro_mensual'], 1)

    def test_existing_contract_adjustment_with_invalid_dates_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        AjusteContrato.objects.create(
            contrato=contrato,
            tipo_ajuste='descuento_controlado',
            monto=Decimal('1000.00'),
            moneda=MonedaBaseContrato.CLP,
            mes_inicio=date(2026, 3, 1),
            mes_fin=date(2026, 2, 1),
            justificacion='fixture de auditoria',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['ajustes_contrato'], 1)
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.ajuste_contrato.validacion_modelo', issue_codes)

    def test_uf_payment_without_monthly_uf_value_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        periodo.moneda_base = MonedaBaseContrato.UF
        periodo.monto_base = Decimal('10.00')
        periodo.save(update_fields=['moneda_base', 'monto_base', 'updated_at'])
        payment = self._create_payment_for(contrato)
        payment.monto_facturable_clp = Decimal('350000.00')
        payment.monto_calculado_clp = Decimal('350001.00')
        payment.save(update_fields=['monto_facturable_clp', 'monto_calculado_clp', 'updated_at'])
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('350000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('350000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.pago_mensual.uf_valor_faltante', issue_codes)

    def test_uf_payment_with_monthly_uf_value_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        periodo.moneda_base = MonedaBaseContrato.UF
        periodo.monto_base = Decimal('10.00')
        periodo.save(update_fields=['moneda_base', 'monto_base', 'updated_at'])
        ValorUFDiario.objects.create(fecha=date(2026, 1, 1), valor=Decimal('35000.0000'), source_key='snapshot')
        payment = self._create_payment_for(contrato)
        payment.monto_facturable_clp = Decimal('350000.00')
        payment.monto_calculado_clp = Decimal('350001.00')
        payment.save(update_fields=['monto_facturable_clp', 'monto_calculado_clp', 'updated_at'])
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('350000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('350000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('stage1.pago_mensual.uf_valor_faltante', issue_codes)

    def test_invalid_uf_value_is_blocking_even_when_month_exists(self):
        contrato = self._create_valid_stage1_matrix()
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        periodo.moneda_base = MonedaBaseContrato.UF
        periodo.monto_base = Decimal('10.00')
        periodo.save(update_fields=['moneda_base', 'monto_base', 'updated_at'])
        ValorUFDiario.objects.create(fecha=date(2026, 1, 1), valor=Decimal('0.0000'), source_key='snapshot')
        payment = self._create_payment_for(contrato)
        payment.monto_facturable_clp = Decimal('350000.00')
        payment.monto_calculado_clp = Decimal('350001.00')
        payment.save(update_fields=['monto_facturable_clp', 'monto_calculado_clp', 'updated_at'])
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('350000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('350000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertEqual(result['summary']['valores_uf_diarios'], 1)
        self.assertIn('stage1.valor_uf.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['valores_uf_diarios']['classification'], 'defectuoso')
        self.assertIn(
            'stage1.valor_uf.validacion_modelo',
            result['aggregate_classification']['valores_uf_diarios']['blocking_issue_codes'],
        )

    def test_duplicate_active_property_by_rol_avaluo_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        propiedad = contrato.mandato_operacion.propiedad
        propiedad.rol_avaluo = '123-45'
        propiedad.save(update_fields=['rol_avaluo', 'updated_at'])
        empresa = contrato.mandato_operacion.propietario_empresa_owner

        duplicate_property = Propiedad.objects.create(
            rol_avaluo='123 45',
            direccion='Direccion Controlada Rol Duplicado',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-ROL',
            estado='activa',
            empresa_owner=empresa,
        )
        MandatoOperacion.objects.create(
            propiedad=duplicate_property,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=contrato.mandato_operacion.cuenta_recaudadora,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.propiedad.rol_avaluo_duplicado', issue_codes)

    def test_duplicate_active_property_by_operational_identity_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        socio = Socio.objects.get(rut='11111111-1')
        duplicate_property = Propiedad.objects.create(
            direccion='  direccion   controlada 100 ',
            comuna='santiago',
            region='rm',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-001',
            estado='activa',
            socio_owner=socio,
        )
        cuenta = CuentaRecaudadora.objects.create(
            socio_owner=socio,
            institucion='Banco Controlado',
            numero_cuenta='CTRL-ACC-SOCIO',
            tipo_cuenta='corriente',
            titular_nombre=socio.nombre,
            titular_rut=socio.rut,
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        MandatoOperacion.objects.create(
            propiedad=duplicate_property,
            propietario_socio_owner=socio,
            administrador_socio_owner=socio,
            recaudador_socio_owner=socio,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=False,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.propiedad.identidad_operativa_duplicada', issue_codes)

    def test_active_contract_without_ready_tenant_contact_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        arrendatario = contrato.arrendatario
        arrendatario.email = ''
        arrendatario.telefono = ''
        arrendatario.domicilio_notificaciones = ''
        arrendatario.estado_contacto = EstadoContactoArrendatario.PENDING
        arrendatario.save(
            update_fields=[
                'email',
                'telefono',
                'domicilio_notificaciones',
                'estado_contacto',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.arrendatario.contacto_no_activo', issue_codes)
        self.assertIn('stage1.arrendatario.contacto_operativo_faltante', issue_codes)
        self.assertIn('stage1.arrendatario.domicilio_notificaciones_faltante', issue_codes)

    def test_active_contract_without_operational_channel_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.mandato_operacion.asignaciones_canal.all().delete()

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.canal_operativo_faltante', issue_codes)

    def test_active_contract_outside_mandate_validity_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        mandato = contrato.mandato_operacion
        mandato.vigencia_desde = date(2026, 2, 1)
        mandato.vigencia_hasta = date(2026, 11, 30)
        mandato.save(update_fields=['vigencia_desde', 'vigencia_hasta', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.mandato_no_vigente_al_inicio', issue_codes)
        self.assertIn('stage1.contrato.mandato_no_cubre_fin', issue_codes)

    def test_codebtor_without_identity_snapshot_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        CodeudorSolidario.objects.create(contrato=contrato, snapshot_identidad={})

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.codeudor.validacion_modelo', issue_codes)

    def test_existing_payment_without_distribution_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        self._create_payment_for(contrato)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.pago_mensual.distribuciones_faltantes', issue_codes)

    def test_existing_payment_with_distribution_amount_mismatch_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('200000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('200000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.pago_mensual.distribucion_devengo_inconsistente', issue_codes)

    def test_distribution_marked_for_dte_must_match_billing_entity(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        other_company = Empresa.objects.create(
            razon_social='Facturadora Incorrecta SpA',
            rut='99999999-9',
            estado='activa',
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=Socio.objects.get(rut='11111111-1'),
            empresa_owner=other_company,
            porcentaje='100.00',
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=other_company,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('250000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('250000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.distribucion_cobro.facturadora_inconsistente', issue_codes)

    def test_contract_with_more_than_three_active_codebtors_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        for index, rut in enumerate(['44444444-4', '55555555-5', '66666666-6', '77777777-7'], start=1):
            CodeudorSolidario.objects.create(
                contrato=contrato,
                snapshot_identidad={'nombre': f'Codeudor Controlado {index}', 'rut': rut},
                estado=EstadoCodeudorSolidario.ACTIVE,
            )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.codeudor.validacion_modelo', issue_codes)

    def test_contract_with_duplicate_active_codebtor_rut_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        CodeudorSolidario.objects.create(
            contrato=contrato,
            snapshot_identidad={'nombre': 'Codeudor Controlado Uno', 'rut': '44444444-4'},
            estado=EstadoCodeudorSolidario.ACTIVE,
        )
        CodeudorSolidario.objects.create(
            contrato=contrato,
            snapshot_identidad={'nombre': 'Codeudor Controlado Dos', 'rut': '44.444.444-4'},
            estado=EstadoCodeudorSolidario.ACTIVE,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.codeudor.validacion_modelo', issue_codes)

    def test_company_tenant_without_representative_snapshot_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        arrendatario = contrato.arrendatario
        arrendatario.tipo_arrendatario = TipoArrendatario.COMPANY
        arrendatario.save(update_fields=['tipo_arrendatario', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.representante_legal_snapshot_faltante', issue_codes)

    def test_future_contract_without_notice_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        self._create_future_contract_for(contrato)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_futuro.aviso_termino_faltante', issue_codes)

    def test_future_contract_with_registered_notice_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2026, 12, 31),
            causal='Termino controlado para contrato futuro',
            estado=EstadoAvisoTermino.REGISTERED,
        )
        self._create_future_contract_for(contrato)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('stage1.contrato_futuro.aviso_termino_faltante', issue_codes)

    def test_notice_effective_date_after_contract_end_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2027, 1, 31),
            causal='Termino fuera de rango contractual',
            estado=EstadoAvisoTermino.REGISTERED,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.aviso_termino.validacion_modelo', issue_codes)

    def test_invalid_stage1_model_records_are_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        participacion = ParticipacionPatrimonial.objects.filter(
            empresa_owner=contrato.mandato_operacion.propietario_empresa_owner,
            activo=True,
        ).first()
        participacion.vigente_hasta = date(2025, 12, 31)
        participacion.save(update_fields=['vigente_hasta', 'updated_at'])
        contrato.arrendatario.rut = '33333333-4'
        contrato.arrendatario.save(update_fields=['rut', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.participacion.validacion_modelo', issue_codes)
        self.assertIn('stage1.arrendatario.validacion_modelo', issue_codes)

    def test_historical_contract_structural_rows_are_validated(self):
        contrato = self._create_valid_stage1_matrix()
        historical_contract = Contrato.objects.create(
            codigo_contrato='CON-HIST-INVALID',
            mandato_operacion=contrato.mandato_operacion,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2024, 1, 1),
            fecha_fin_vigente=date(2023, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.FINISHED,
        )
        ContratoPropiedad.objects.create(
            contrato=historical_contract,
            propiedad=contrato.mandato_operacion.propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='000',
        )
        PeriodoContractual.objects.create(
            contrato=historical_contract,
            numero_periodo=1,
            fecha_inicio=date(2024, 1, 1),
            fecha_fin=date(2024, 12, 31),
            monto_base='500.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        GarantiaContractual.objects.create(
            contrato=historical_contract,
            monto_pactado='1000.00',
            monto_recibido='2000.00',
            estado_garantia=EstadoGarantia.HELD,
            fecha_recepcion=date(2024, 1, 5),
        )
        AvisoTermino.objects.create(
            contrato=historical_contract,
            fecha_efectiva=date(2023, 12, 1),
            causal='fixture historico invalido',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['has_required_stage1_data'])
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertEqual(
            result['aggregate_classification']['contratos_activos_o_futuros']['classification'],
            'resuelto_confirmado',
        )
        self.assertEqual(
            result['aggregate_classification']['contratos_activos_o_futuros']['blocking_issue_codes'],
            [],
        )
        self.assertEqual(result['aggregate_classification']['contratos']['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)
        self.assertIn('stage1.periodo.validacion_modelo', issue_codes)
        self.assertIn('stage1.garantia.validacion_modelo', issue_codes)
        self.assertIn('stage1.aviso_termino.validacion_modelo', issue_codes)

    def test_invalid_fiscal_configuration_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        config = ConfiguracionFiscalEmpresa.objects.get(
            empresa=contrato.mandato_operacion.entidad_facturadora,
        )
        config.regimen_tributario.estado = EstadoRegistro.INACTIVE
        config.regimen_tributario.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.configuracion_fiscal.validacion_modelo', issue_codes)

    def test_contract_without_matrix_components_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.contrato_propiedades.all().delete()
        contrato.periodos_contractuales.all().delete()
        contrato.garantia_contractual.delete()

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.propiedad_principal_invalida', issue_codes)
        self.assertIn('stage1.contrato.periodos_faltantes', issue_codes)
        self.assertIn('stage1.contrato.garantia_faltante', issue_codes)

    def test_active_contract_with_inactive_linked_property_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        principal_link = contrato.contrato_propiedades.get(rol_en_contrato=RolContratoPropiedad.PRIMARY)
        principal_link.porcentaje_distribucion_interna = Decimal('50.00')
        principal_link.save(update_fields=['porcentaje_distribucion_interna', 'updated_at'])
        inactive_property = Propiedad.objects.create(
            direccion='Direccion Vinculada Inactiva',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-INACT',
            estado='inactiva',
            empresa_owner=contrato.mandato_operacion.propietario_empresa_owner,
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=inactive_property,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='50.00',
            codigo_conciliacion_efectivo_snapshot='001',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['contrato_propiedades']['classification'], 'defectuoso')

    def test_linked_property_with_different_effective_code_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        principal_link = contrato.contrato_propiedades.get(rol_en_contrato=RolContratoPropiedad.PRIMARY)
        principal_link.porcentaje_distribucion_interna = Decimal('50.00')
        principal_link.save(update_fields=['porcentaje_distribucion_interna', 'updated_at'])
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        linked_property = Propiedad.objects.create(
            direccion='Direccion Vinculada Codigo',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-LINK-CODE',
            estado='activa',
            empresa_owner=empresa,
        )
        MandatoOperacion.objects.create(
            propiedad=linked_property,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=contrato.mandato_operacion.cuenta_recaudadora,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=linked_property,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='50.00',
            codigo_conciliacion_efectivo_snapshot='002',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['contrato_propiedades']['classification'], 'defectuoso')

    def test_contract_with_more_than_principal_and_linked_pair_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        principal_link = contrato.contrato_propiedades.get(rol_en_contrato=RolContratoPropiedad.PRIMARY)
        principal_link.porcentaje_distribucion_interna = Decimal('40.00')
        principal_link.save(update_fields=['porcentaje_distribucion_interna', 'updated_at'])
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        for index, percentage in enumerate(('30.00', '30.00'), start=1):
            linked_property = Propiedad.objects.create(
                direccion=f'Direccion Vinculada Extra {index}',
                comuna='Santiago',
                region='RM',
                tipo_inmueble=TipoInmueble.LOCAL,
                codigo_propiedad=f'CTRL-LINK-{index}',
                estado='activa',
                empresa_owner=empresa,
            )
            MandatoOperacion.objects.create(
                propiedad=linked_property,
                propietario_empresa_owner=empresa,
                administrador_empresa_owner=empresa,
                recaudador_empresa_owner=empresa,
                entidad_facturadora=empresa,
                cuenta_recaudadora=contrato.mandato_operacion.cuenta_recaudadora,
                tipo_relacion_operativa='administracion_directa',
                autoriza_recaudacion=True,
                autoriza_facturacion=True,
                autoriza_comunicacion=True,
                estado=EstadoMandatoOperacion.ACTIVE,
                vigencia_desde=date(2026, 1, 1),
            )
            ContratoPropiedad.objects.create(
                contrato=contrato,
                propiedad=linked_property,
                rol_en_contrato=RolContratoPropiedad.LINKED,
                porcentaje_distribucion_interna=percentage,
                codigo_conciliacion_efectivo_snapshot='001',
            )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['contrato_propiedades']['classification'], 'defectuoso')

    def test_inconsistent_guarantee_state_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.estado_garantia = EstadoGarantia.PENDING
        garantia.save(update_fields=['monto_pactado', 'monto_recibido', 'estado_garantia', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.garantia.validacion_modelo', issue_codes)

    def test_received_guarantee_without_history_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.fecha_recepcion = date(2026, 1, 5)
        garantia.estado_garantia = EstadoGarantia.HELD
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'fecha_recepcion',
                'estado_garantia',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.garantia.historial_recepcion_inconsistente', issue_codes)

    def test_received_guarantee_with_matching_history_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.fecha_recepcion = date(2026, 1, 5)
        garantia.estado_garantia = EstadoGarantia.HELD
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'fecha_recepcion',
                'estado_garantia',
                'updated_at',
            ]
        )
        HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento=TipoMovimientoGarantia.DEPOSIT,
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 5),
        )

        result = self._collect_controlled_snapshot()

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')

    def test_guarantee_history_with_foreign_origin_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        propiedad = Propiedad.objects.create(
            direccion='Direccion Controlada Garantia',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-GAR',
            estado='activa',
            empresa_owner=empresa,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=contrato.mandato_operacion.cuenta_recaudadora,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        second_contract = Contrato.objects.create(
            codigo_contrato='CON-CTRL-GAR',
            mandato_operacion=mandato,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
        )
        ContratoPropiedad.objects.create(
            contrato=second_contract,
            propiedad=propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='002',
        )
        PeriodoContractual.objects.create(
            contrato=second_contract,
            numero_periodo=1,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        second_guarantee = GarantiaContractual.objects.create(contrato=second_contract, monto_pactado='0.00')
        origin = HistorialGarantia.objects.create(
            garantia_contractual=contrato.garantia_contractual,
            tipo_movimiento=TipoMovimientoGarantia.DEPOSIT,
            monto_clp=Decimal('1000.00'),
            fecha=date(2026, 1, 5),
        )
        HistorialGarantia.objects.create(
            garantia_contractual=second_guarantee,
            tipo_movimiento=TipoMovimientoGarantia.PARTIAL_RETURN,
            monto_clp=Decimal('1000.00'),
            fecha=date(2026, 1, 6),
            movimiento_origen=origin,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.historial_garantia.validacion_modelo', issue_codes)

    def test_linked_property_with_independent_active_contract_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        propiedad_linked_conflict = contrato.mandato_operacion.propiedad
        propiedad_principal = Propiedad.objects.create(
            direccion='Direccion Controlada 200',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-002',
            estado='activa',
            empresa_owner=empresa,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad_principal,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=contrato.mandato_operacion.cuenta_recaudadora,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        second_contract = Contrato.objects.create(
            codigo_contrato='CON-CTRL-002',
            mandato_operacion=mandato,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
        )
        ContratoPropiedad.objects.create(
            contrato=second_contract,
            propiedad=propiedad_principal,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='50.00',
            codigo_conciliacion_efectivo_snapshot='002',
        )
        ContratoPropiedad.objects.create(
            contrato=second_contract,
            propiedad=propiedad_linked_conflict,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='50.00',
            codigo_conciliacion_efectivo_snapshot='002',
        )
        PeriodoContractual.objects.create(
            contrato=second_contract,
            numero_periodo=1,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        GarantiaContractual.objects.create(contrato=second_contract, monto_pactado='0.00')

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.propiedad.contratos_duplicados', issue_codes)
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)

    def test_duplicate_effective_code_in_same_account_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        propiedad = Propiedad.objects.create(
            direccion='Direccion Controlada Codigo',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='CTRL-COD',
            estado='activa',
            empresa_owner=empresa,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=contrato.mandato_operacion.cuenta_recaudadora,
            tipo_relacion_operativa='administracion_directa',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde=date(2026, 1, 1),
        )
        second_contract = Contrato.objects.create(
            codigo_contrato='CON-CTRL-COD',
            mandato_operacion=mandato,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
        )
        ContratoPropiedad.objects.create(
            contrato=second_contract,
            propiedad=propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='001',
        )
        PeriodoContractual.objects.create(
            contrato=second_contract,
            numero_periodo=1,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )
        GarantiaContractual.objects.create(contrato=second_contract, monto_pactado='0.00')

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.codigo_efectivo.duplicado_en_cuenta', issue_codes)
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)

    def test_zero_effective_code_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        link = contrato.contrato_propiedades.get(rol_en_contrato=RolContratoPropiedad.PRIMARY)
        link.codigo_conciliacion_efectivo_snapshot = '000'
        link.save(update_fields=['codigo_conciliacion_efectivo_snapshot', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)

    def test_payment_zero_effective_code_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        payment.codigo_conciliacion_efectivo = '000'
        payment.save(update_fields=['codigo_conciliacion_efectivo', 'updated_at'])
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('250000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('250000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.pago_mensual.validacion_modelo', issue_codes)

    def test_payment_effective_code_must_match_primary_contract_property(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        payment.codigo_conciliacion_efectivo = '002'
        payment.save(update_fields=['codigo_conciliacion_efectivo', 'updated_at'])
        DistribucionCobroMensual.objects.create(
            pago_mensual=payment,
            beneficiario_empresa_owner=contrato.mandato_operacion.entidad_facturadora,
            porcentaje_snapshot=Decimal('100.00'),
            monto_devengado_clp=Decimal('250000.00'),
            monto_conciliado_clp=Decimal('0.00'),
            monto_facturable_clp=Decimal('250000.00'),
            requiere_dte=True,
            origen_atribucion='snapshot_pago',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.pago_mensual.codigo_efectivo_desalineado', issue_codes)

    def test_command_can_fail_when_required_data_is_missing(self):
        with self.assertRaises(CommandError):
            call_command(
                'audit_stage1_matrix',
                source_kind='snapshot_controlado',
                source_label='stage-one-command-test',
                authorization_ref='auth-stage-one-command-test',
                responsible_ref='responsible-stage-one-command-test',
                require_data=True,
                fail_on_violations=True,
                stdout=StringIO(),
            )

    def test_command_rejects_versionable_repo_output(self):
        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'stage1-audit-should-not-be-versioned.json'

        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_stage1_matrix',
                source_kind='local',
                source_label='stage-one-output-test',
                output=str(blocked_output),
                stdout=StringIO(),
            )

        self.assertFalse(blocked_output.exists())

    def test_command_allows_local_evidence_output(self):
        allowed_output = Path(settings.PROJECT_ROOT) / 'local-evidence' / 'stage1' / 'command-output-guard.json'
        allowed_output.unlink(missing_ok=True)

        try:
            call_command(
                'audit_stage1_matrix',
                source_kind='local',
                source_label='stage-one-output-test',
                output=str(allowed_output),
                stdout=StringIO(),
            )

            self.assertTrue(allowed_output.exists())
        finally:
            allowed_output.unlink(missing_ok=True)
