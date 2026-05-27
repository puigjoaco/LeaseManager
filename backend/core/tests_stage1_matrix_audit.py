from datetime import date, datetime, timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent
from cobranza.models import (
    AjusteContrato,
    DistribucionCobroMensual,
    EstadoGarantia,
    EstadoPago,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    TipoMovimientoGarantia,
    ValorUFDiario,
)
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from documentos.models import EstadoPoliticaFirma, PoliticaFirmaYNotaria, TipoDocumental
from contratos.models import (
    AUTOMATIC_RENEWAL_EVENT_TYPE,
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    ContactoPagoArrendatario,
    Contrato,
    ContratoPropiedad,
    EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE,
    EstadoContactoArrendatario,
    EstadoAvisoTermino,
    EstadoCodeudorSolidario,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RolContratoPropiedad,
    TENANT_REPLACEMENT_EVENT_TYPE,
    TipoArrendatario,
)
from core.stage1_matrix_audit import collect_stage1_matrix_audit
from operacion.models import (
    AsignacionCanalOperacion,
    CanalOperacion,
    CuentaRecaudadora,
    EstadoAsignacionCanal,
    EstadoCuentaRecaudadora,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
    ModoOperacionCuentaRecaudadora,
)
from patrimonio.models import (
    ComunidadPatrimonial,
    Empresa,
    EstadoPatrimonial,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    ServicioPropiedad,
    Socio,
    TipoInmueble,
    TipoServicioPropiedad,
)
from patrimonio.services import PARTICIPATION_TRANSFER_EVENT_TYPE


class Stage1MatrixAuditTests(TestCase):
    def _create_main_contract_policy(self):
        policy, _ = PoliticaFirmaYNotaria.objects.get_or_create(
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            defaults={
                'requiere_firma_arrendador': True,
                'requiere_firma_arrendatario': True,
            },
        )
        return policy

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
            uso_operativo='recaudacion_arriendos',
            modo_operativo=ModoOperacionCuentaRecaudadora.MANUAL_CONTROLLED,
            evidencia_operativa_ref='account-operational-evidence-stage1',
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
            autoridad_operativa_nombre='Representante Operativo Controlado',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
        ContactoPagoArrendatario.objects.create(
            arrendatario=arrendatario,
            nombre='Contacto Pago Controlado',
            rol_operativo='pago_arriendo',
            email='pagos-controlados@example.com',
            evidencia_autorizacion_ref='contacto-pago-controlado-v1',
            es_principal=True,
            estado='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='CON-CTRL-001',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
            politica_documental=self._create_main_contract_policy(),
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
            politica_documental=contrato.politica_documental,
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
            monto_efecto_codigo_efectivo_clp=Decimal('1.00'),
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

    def test_participation_transfer_without_audit_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        origin = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa, porcentaje=Decimal('40.00')).first()
        successor = Socio.objects.create(nombre='Socio Sucesor Sin Auditoria', rut='44444444-4', activo=True)
        effective_date = timezone.localdate()
        origin.vigente_hasta = effective_date - timedelta(days=1)
        origin.save(update_fields=['vigente_hasta', 'updated_at'])
        ParticipacionPatrimonial.objects.create(
            participante_socio=successor,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde=effective_date,
            activo=True,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.participacion.transferencia_sin_auditoria', issue_codes)

    def test_participation_transfer_with_audit_can_pass(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        origin = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa, porcentaje=Decimal('40.00')).first()
        successor = Socio.objects.create(nombre='Socio Sucesor Auditado', rut='44444444-4', activo=True)
        actor = get_user_model().objects.create_user(username='stage1-transfer-auditor')
        effective_date = timezone.localdate()
        origin.vigente_hasta = effective_date - timedelta(days=1)
        origin.save(update_fields=['vigente_hasta', 'updated_at'])
        target = ParticipacionPatrimonial.objects.create(
            participante_socio=successor,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde=effective_date,
            activo=True,
        )
        AuditEvent.objects.create(
            event_type=PARTICIPATION_TRANSFER_EVENT_TYPE,
            entity_type='participacion_patrimonial',
            entity_id=str(origin.pk),
            summary='Transferencia patrimonial auditada.',
            actor_user=actor,
            metadata={
                'owner_tipo': 'empresa',
                'owner_id': empresa.pk,
                'origin_participation_id': origin.pk,
                'origin_participant_type': origin.participante_tipo,
                'origin_participant_id': origin.participante_id,
                'effective_date': effective_date.isoformat(),
                'reason': 'Transferencia controlada de prueba.',
                'target_participation_ids': [target.pk],
                'target_count': 1,
                'transferred_percentage': '40.00',
                'evidence_ref': 'participation-transfer-audit-test',
            },
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertNotIn('stage1.participacion.transferencia_sin_auditoria', issue_codes)
        self.assertNotIn('stage1.participacion.transferencia_auditoria_desalineada', issue_codes)

    def test_participation_transfer_with_unaligned_audit_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        origin = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa, porcentaje=Decimal('40.00')).first()
        successor = Socio.objects.create(nombre='Socio Sucesor Desalineado', rut='44444444-4', activo=True)
        effective_date = timezone.localdate()
        origin.vigente_hasta = effective_date - timedelta(days=1)
        origin.save(update_fields=['vigente_hasta', 'updated_at'])
        target = ParticipacionPatrimonial.objects.create(
            participante_socio=successor,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde=effective_date,
            activo=True,
        )
        AuditEvent.objects.create(
            event_type=PARTICIPATION_TRANSFER_EVENT_TYPE,
            entity_type='participacion_patrimonial',
            entity_id=str(origin.pk),
            summary='Transferencia patrimonial con metadata incompleta.',
            metadata={
                'origin_participation_id': origin.pk,
                'target_participation_ids': [target.pk + 1000],
                'evidence_ref': 'https://docs.example.test/secret-token',
            },
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertNotIn('stage1.participacion.transferencia_sin_auditoria', issue_codes)
        self.assertIn('stage1.participacion.transferencia_auditoria_desalineada', issue_codes)

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

    def test_inactive_account_with_active_mandate_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        cuenta = contrato.mandato_operacion.cuenta_recaudadora
        cuenta.estado_operativo = EstadoCuentaRecaudadora.INACTIVE
        cuenta.save(update_fields=['estado_operativo', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.cuenta.validacion_modelo', issue_codes)
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['cuentas_recaudadoras']['classification'],
            'defectuoso',
        )

    def test_active_account_without_operational_evidence_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        cuenta = contrato.mandato_operacion.cuenta_recaudadora
        CuentaRecaudadora.objects.filter(pk=cuenta.pk).update(
            uso_operativo='',
            modo_operativo='',
            evidencia_operativa_ref='',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.cuenta.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['cuentas_recaudadoras']['classification'],
            'defectuoso',
        )

    def test_inactive_identity_with_active_assignment_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        identidad = contrato.mandato_operacion.asignaciones_canal.get().identidad_envio
        identidad.estado = EstadoIdentidadEnvio.SUSPENDED
        identidad.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.identidad_envio.validacion_modelo', issue_codes)
        self.assertIn('stage1.asignacion_canal.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.canal_operativo_faltante', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['identidades_envio_activas']['classification'],
            'defectuoso',
        )
        self.assertEqual(
            result['aggregate_classification']['asignaciones_canal_activas']['classification'],
            'defectuoso',
        )

    def test_inactive_mandate_with_active_contract_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        mandato = contrato.mandato_operacion
        mandato.estado = EstadoMandatoOperacion.INACTIVE
        mandato.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.mandato_no_activo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['mandatos']['classification'],
            'defectuoso',
        )
        self.assertEqual(
            result['aggregate_classification']['contratos_activos_o_futuros']['classification'],
            'defectuoso',
        )

    def test_active_property_overlapping_mandate_windows_are_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        mandato = contrato.mandato_operacion
        MandatoOperacion.objects.create(
            propiedad=mandato.propiedad,
            propietario_empresa_owner=mandato.propietario_empresa_owner,
            propietario_comunidad_owner=mandato.propietario_comunidad_owner,
            propietario_socio_owner=mandato.propietario_socio_owner,
            administrador_empresa_owner=mandato.administrador_empresa_owner,
            administrador_socio_owner=mandato.administrador_socio_owner,
            recaudador_empresa_owner=mandato.recaudador_empresa_owner,
            recaudador_comunidad_owner=mandato.recaudador_comunidad_owner,
            recaudador_socio_owner=mandato.recaudador_socio_owner,
            entidad_facturadora=mandato.entidad_facturadora,
            cuenta_recaudadora=mandato.cuenta_recaudadora,
            tipo_relacion_operativa=mandato.tipo_relacion_operativa,
            autoriza_recaudacion=mandato.autoriza_recaudacion,
            autoriza_facturacion=mandato.autoriza_facturacion,
            autoriza_comunicacion=mandato.autoriza_comunicacion,
            autoridad_operativa_nombre=mandato.autoridad_operativa_nombre,
            autoridad_operativa_rut=mandato.autoridad_operativa_rut,
            autoridad_operativa_evidencia_ref=mandato.autoridad_operativa_evidencia_ref,
            vigencia_desde=timezone.localdate() + timedelta(days=30),
            estado=EstadoMandatoOperacion.ACTIVE,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertIn('stage1.mandato.ventana_solapada', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['mandatos']['classification'],
            'defectuoso',
        )

    def test_active_mandate_missing_operational_authority_is_explicitly_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        mandato = contrato.mandato_operacion
        mandato.autoridad_operativa_nombre = ''
        mandato.autoridad_operativa_rut = ''
        mandato.autoridad_operativa_evidencia_ref = ''
        mandato.save(
            update_fields=[
                'autoridad_operativa_nombre',
                'autoridad_operativa_rut',
                'autoridad_operativa_evidencia_ref',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertIn('stage1.mandato.autoridad_operativa_nombre_faltante', issue_codes)
        self.assertIn('stage1.mandato.autoridad_operativa_rut_faltante', issue_codes)
        self.assertIn('stage1.mandato.autoridad_operativa_evidencia_faltante', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['mandatos']['classification'],
            'defectuoso',
        )

    def test_inactive_only_assignment_with_active_contract_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        asignacion = contrato.mandato_operacion.asignaciones_canal.get()
        asignacion.estado = EstadoAsignacionCanal.INACTIVE
        asignacion.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.asignacion_canal.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.canal_operativo_faltante', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['asignaciones_canal_activas']['classification'],
            'defectuoso',
        )

    def test_active_assignment_with_unrelated_identity_owner_is_explicitly_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        asignacion = contrato.mandato_operacion.asignaciones_canal.get()
        identidad = asignacion.identidad_envio
        unrelated_socio = Socio.objects.get(rut='11111111-1')
        identidad.empresa_owner = None
        identidad.socio_owner = unrelated_socio
        identidad.save(update_fields=['empresa_owner', 'socio_owner', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.asignacion_canal.validacion_modelo', issue_codes)
        self.assertIn('stage1.asignacion_canal.identidad_owner_no_autorizado', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['asignaciones_canal_activas']['classification'],
            'defectuoso',
        )

    def test_active_assignment_without_communication_authorization_is_explicitly_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        mandato = contrato.mandato_operacion
        admin_socio = Socio.objects.get(rut='11111111-1')
        mandato.administrador_empresa_owner = None
        mandato.administrador_socio_owner = admin_socio
        mandato.autoriza_comunicacion = False
        mandato.save(
            update_fields=[
                'administrador_empresa_owner',
                'administrador_socio_owner',
                'autoriza_comunicacion',
                'updated_at',
            ]
        )
        asignacion = mandato.asignaciones_canal.get()
        identidad = asignacion.identidad_envio
        identidad.empresa_owner = None
        identidad.socio_owner = admin_socio
        identidad.save(update_fields=['empresa_owner', 'socio_owner', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertIn('stage1.asignacion_canal.validacion_modelo', issue_codes)
        self.assertIn('stage1.asignacion_canal.comunicacion_no_autorizada', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['mandatos']['classification'],
            'defectuoso',
        )
        self.assertEqual(
            result['aggregate_classification']['asignaciones_canal_activas']['classification'],
            'defectuoso',
        )

    def test_contract_identity_override_with_unrelated_owner_is_explicitly_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        socio = Socio.objects.get(rut='11111111-1')
        unrelated_company = Empresa.objects.create(
            razon_social='Empresa Override No Autorizada SpA',
            rut='99999999-9',
            estado='activa',
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=unrelated_company,
            porcentaje='100.00',
            vigente_desde=date(2026, 1, 1),
            activo=True,
        )
        identidad = IdentidadDeEnvio.objects.create(
            empresa_owner=unrelated_company,
            canal=CanalOperacion.EMAIL,
            remitente_visible='Override No Autorizado',
            direccion_o_numero='override-no-autorizado@example.com',
            credencial_ref='cred-ref-override-no-autorizado',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )
        contrato.identidad_envio_override = identidad
        contrato.save(update_fields=['identidad_envio_override', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.identidad_override_owner_no_autorizado', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['contratos_activos_o_futuros']['classification'],
            'defectuoso',
        )

    def test_contract_identity_override_without_communication_authorization_is_explicitly_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        mandato = contrato.mandato_operacion
        admin_socio = Socio.objects.get(rut='11111111-1')
        mandato.administrador_empresa_owner = None
        mandato.administrador_socio_owner = admin_socio
        mandato.autoriza_comunicacion = False
        mandato.save(
            update_fields=[
                'administrador_empresa_owner',
                'administrador_socio_owner',
                'autoriza_comunicacion',
                'updated_at',
            ]
        )
        identidad = IdentidadDeEnvio.objects.create(
            socio_owner=admin_socio,
            canal=CanalOperacion.EMAIL,
            remitente_visible='Override Admin Socio',
            direccion_o_numero='override-admin-socio@example.com',
            credencial_ref='cred-ref-override-admin-socio',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )
        contrato.identidad_envio_override = identidad
        contrato.save(update_fields=['identidad_envio_override', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.identidad_override_comunicacion_no_autorizada', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['mandatos']['classification'],
            'defectuoso',
        )
        self.assertEqual(
            result['aggregate_classification']['contratos_activos_o_futuros']['classification'],
            'defectuoso',
        )

    def test_contract_identity_override_inactive_identity_is_explicitly_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.administrador_empresa_owner
        identidad = IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=CanalOperacion.EMAIL,
            remitente_visible='Override Inactivo',
            direccion_o_numero='override-inactivo@example.com',
            credencial_ref='cred-ref-override-inactivo',
            estado=EstadoIdentidadEnvio.SUSPENDED,
        )
        contrato.identidad_envio_override = identidad
        contrato.save(update_fields=['identidad_envio_override', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.identidad_override_no_activa', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['contratos_activos_o_futuros']['classification'],
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

    def test_active_company_duplicate_current_participant_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        socio = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).first().participante_socio
        ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).exclude(
            participante_socio=socio,
        ).update(participante_socio=socio)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.empresa.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['empresas']['classification'],
            'defectuoso',
        )

    def test_active_community_duplicate_current_participant_is_blocking(self):
        self._create_valid_stage1_matrix()
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Controlada')
        socio = ParticipacionPatrimonial.objects.filter(comunidad_owner=comunidad).first().participante_socio
        ParticipacionPatrimonial.objects.filter(comunidad_owner=comunidad).exclude(
            participante_socio=socio,
        ).update(participante_socio=socio)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.comunidad.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['comunidades']['classification'],
            'defectuoso',
        )

    def test_active_community_future_only_representation_is_blocking(self):
        self._create_valid_stage1_matrix()
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Controlada')
        future_date = timezone.localdate() + timedelta(days=30)
        RepresentacionComunidad.objects.filter(comunidad=comunidad).update(vigente_desde=future_date)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.comunidad.validacion_modelo', issue_codes)
        self.assertIn('stage1.comunidad.representacion_activa_invalida', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['comunidades']['classification'],
            'defectuoso',
        )

    def test_active_community_overlapping_representation_windows_are_blocking(self):
        self._create_valid_stage1_matrix()
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Controlada')
        socio = Socio.objects.get(nombre='Socio Controlado Dos')
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio,
            vigente_desde=timezone.localdate() + timedelta(days=30),
            activo=True,
            evidencia_ref='community-designated-representative-overlap-act-001',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.representacion.validacion_modelo', issue_codes)
        self.assertIn('stage1.comunidad.representacion_solapada', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['comunidades']['classification'],
            'defectuoso',
        )

    def test_designated_community_representation_without_evidence_is_blocking(self):
        self._create_valid_stage1_matrix()
        representation = RepresentacionComunidad.objects.get(comunidad__nombre='Comunidad Controlada')
        RepresentacionComunidad.objects.filter(pk=representation.pk).update(
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            evidencia_ref='',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.representacion.designada_evidencia_faltante', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['representaciones_comunidad']['classification'],
            'defectuoso',
        )

    def test_designated_community_representation_sensitive_evidence_is_blocking(self):
        self._create_valid_stage1_matrix()
        representation = RepresentacionComunidad.objects.get(comunidad__nombre='Comunidad Controlada')
        RepresentacionComunidad.objects.filter(pk=representation.pk).update(
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            evidencia_ref='https://example.test/acta?token=secret',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.representacion.designada_evidencia_sensible', issue_codes)

    def test_designated_community_representation_with_evidence_can_pass(self):
        self._create_valid_stage1_matrix()
        representation = RepresentacionComunidad.objects.get(comunidad__nombre='Comunidad Controlada')
        RepresentacionComunidad.objects.filter(pk=representation.pk).update(
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            evidencia_ref='community-designated-representative-act-003',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertNotIn('stage1.representacion.designada_evidencia_faltante', issue_codes)
        self.assertNotIn('stage1.representacion.designada_evidencia_sensible', issue_codes)

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

    def test_inactive_patrimonial_owner_with_active_property_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        empresa = contrato.mandato_operacion.propietario_empresa_owner
        empresa.estado = EstadoPatrimonial.INACTIVE
        empresa.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.empresa.validacion_modelo', issue_codes)
        self.assertIn('stage1.propiedad.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['empresas']['classification'],
            'defectuoso',
        )

    def test_inactive_company_with_active_own_participations_is_blocking(self):
        self._create_valid_stage1_matrix()
        socio = Socio.objects.create(nombre='Socio Empresa Cerrada', rut='71717171-8', activo=True)
        empresa = Empresa.objects.create(
            razon_social='Empresa Cerrada Con Ownership',
            rut='70707070-0',
            estado=EstadoPatrimonial.INACTIVE,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=empresa,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.empresa.validacion_modelo', issue_codes)

    def test_inactive_community_with_active_structure_is_blocking(self):
        self._create_valid_stage1_matrix()
        socio = Socio.objects.create(nombre='Socio Comunidad Cerrada', rut='72727272-6', activo=True)
        comunidad = ComunidadPatrimonial.objects.create(
            nombre='Comunidad Cerrada Con Estructura',
            estado=EstadoPatrimonial.INACTIVE,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio,
            vigente_desde='2026-01-01',
            activo=True,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.comunidad.validacion_modelo', issue_codes)

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

    def test_existing_contract_adjustment_outside_contract_validity_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        AjusteContrato.objects.create(
            contrato=contrato,
            tipo_ajuste='cargo_fuera_vigencia',
            monto=Decimal('1000.00'),
            moneda=MonedaBaseContrato.CLP,
            mes_inicio=date(2025, 12, 1),
            mes_fin=date(2026, 1, 1),
            justificacion='fixture de auditoria',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['ajustes_contrato'], 1)
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.ajuste_contrato.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['ajustes_contrato']['classification'],
            'defectuoso',
        )

    def test_existing_contract_adjustment_with_non_month_start_range_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        AjusteContrato.objects.create(
            contrato=contrato,
            tipo_ajuste='cargo_mes_no_normalizado',
            monto=Decimal('1000.00'),
            moneda=MonedaBaseContrato.CLP,
            mes_inicio=date(2026, 1, 2),
            mes_fin=date(2026, 2, 1),
            justificacion='fixture de auditoria',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['ajustes_contrato'], 1)
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.ajuste_contrato.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['ajustes_contrato']['classification'],
            'defectuoso',
        )

    def test_existing_contract_period_outside_contract_validity_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        periodo.fecha_inicio = date(2025, 12, 1)
        periodo.save(update_fields=['fecha_inicio', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['periodos_contractuales'], 1)
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.periodo.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['periodos_contractuales']['classification'],
            'defectuoso',
        )

    def test_existing_contract_period_with_non_month_boundary_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        periodo = contrato.periodos_contractuales.get(numero_periodo=1)
        periodo.fecha_fin = date(2026, 12, 30)
        periodo.save(update_fields=['fecha_fin', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['periodos_contractuales'], 1)
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.periodo.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['periodos_contractuales']['classification'],
            'defectuoso',
        )

    def test_existing_contract_period_number_outside_chronological_order_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        later_period = contrato.periodos_contractuales.get(numero_periodo=1)
        later_period.fecha_inicio = date(2026, 7, 1)
        later_period.fecha_fin = date(2026, 12, 31)
        later_period.save(update_fields=['fecha_inicio', 'fecha_fin', 'updated_at'])
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 6, 30),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='mensual',
            origen_periodo='snapshot_controlado',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['summary']['periodos_contractuales'], 2)
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.periodo.validacion_modelo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['periodos_contractuales']['classification'],
            'defectuoso',
        )

    def test_renewal_period_changed_base_without_policy_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.tiene_tramos = True
        contrato.save(update_fields=['tiene_tramos', 'updated_at'])
        first_period = contrato.periodos_contractuales.get(numero_periodo=1)
        first_period.fecha_fin = date(2026, 6, 30)
        first_period.save(update_fields=['fecha_fin', 'updated_at'])
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base=Decimal('260000.00'),
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='renovacion',
            origen_periodo='renovacion_automatica',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.periodo.renovacion_base_sin_politica', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['periodos_contractuales']['classification'],
            'defectuoso',
        )

    def test_automatic_renewal_period_without_audit_event_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.tiene_tramos = True
        contrato.fecha_fin_vigente = date(2027, 12, 31)
        contrato.save(update_fields=['tiene_tramos', 'fecha_fin_vigente', 'updated_at'])
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            monto_base=Decimal('250000.00'),
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='renovacion',
            origen_periodo='renovacion_automatica',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.periodo.renovacion_automatica_sin_auditoria', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['periodos_contractuales']['classification'],
            'defectuoso',
        )

    def test_automatic_renewal_period_with_audit_event_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.tiene_tramos = True
        contrato.fecha_fin_vigente = date(2027, 12, 31)
        contrato.save(update_fields=['tiene_tramos', 'fecha_fin_vigente', 'updated_at'])
        renewal = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            monto_base=Decimal('250000.00'),
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='renovacion',
            origen_periodo='renovacion_automatica',
        )
        AuditEvent.objects.create(
            event_type=AUTOMATIC_RENEWAL_EVENT_TYPE,
            entity_type='periodo_contractual',
            entity_id=str(renewal.pk),
            summary='Renovacion automatica auditada.',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('stage1.periodo.renovacion_automatica_sin_auditoria', issue_codes)

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
        ValorUFDiario.objects.create(fecha=date(2026, 1, 1), valor=Decimal('35000.0000'), source_key='UF.BancoCentral')
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
        ValorUFDiario.objects.create(fecha=date(2026, 1, 1), valor=Decimal('0.0000'), source_key='UF.BancoCentral')
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

    def test_manual_uf_without_provenance_is_blocking(self):
        self._create_valid_stage1_matrix()
        ValorUFDiario.objects.create(
            fecha=date(2026, 1, 1),
            valor=Decimal('35000.0000'),
            source_key='UF.CargaManualExtraordinaria',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.valor_uf.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['valores_uf_diarios']['classification'], 'defectuoso')

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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
            uso_operativo='recaudacion_arriendos',
            modo_operativo=ModoOperacionCuentaRecaudadora.MANUAL_CONTROLLED,
            evidencia_operativa_ref='account-operational-evidence-duplicate',
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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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

    def test_active_contract_without_structured_payment_contact_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.arrendatario.contactos_pago.all().delete()

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.arrendatario.contacto_pago_estructurado_faltante', issue_codes)

    def test_invalid_structured_payment_contact_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contacto = contrato.arrendatario.contactos_pago.get()
        contacto.email = ''
        contacto.telefono = ''
        contacto.save(update_fields=['email', 'telefono', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contacto_pago.validacion_modelo', issue_codes)

    def test_common_expense_contract_without_structured_property_service_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.tiene_gastos_comunes = True
        contrato.save(update_fields=['tiene_gastos_comunes', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.propiedad.gasto_comun_estructurado_faltante', issue_codes)

    def test_invalid_structured_property_service_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        ServicioPropiedad.objects.create(
            propiedad=contrato.mandato_operacion.propiedad,
            tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
            proveedor_nombre='Administracion Edificio',
            numero_cliente='',
            administrador_nombre='Administracion Edificio',
            activo=True,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.servicio_propiedad.validacion_modelo', issue_codes)

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
        self.assertIn('stage1.mandato.validacion_modelo', issue_codes)
        self.assertIn('stage1.contrato.mandato_no_vigente_al_inicio', issue_codes)
        self.assertIn('stage1.contrato.mandato_no_cubre_fin', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['mandatos']['classification'],
            'defectuoso',
        )

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

    def test_retroactive_contract_manual_notification_is_warning_only(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_registro_operativo = date(2026, 1, 10)
        contrato.save(update_fields=['fecha_registro_operativo', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertEqual(result['issue_counts'].get('warning'), 1)
        self.assertIn('stage1.contrato.notificacion_manual_retroactiva', issue_codes)

    def test_late_registered_notice_is_warning_only(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_registro_operativo = date(2026, 1, 1)
        contrato.save(update_fields=['fecha_registro_operativo', 'updated_at'])
        aviso = AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2026, 12, 31),
            causal='No renovacion tardia',
            estado=EstadoAvisoTermino.REGISTERED,
        )
        AvisoTermino.objects.filter(pk=aviso.pk).update(
            created_at=timezone.make_aware(datetime(2026, 11, 2, 10, 0, 0))
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertEqual(result['issue_counts'].get('warning'), 1)
        self.assertIn('stage1.aviso_termino.registro_fuera_plazo', issue_codes)

    def test_existing_payment_for_retroactive_past_billing_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_registro_operativo = date(2026, 2, 10)
        contrato.save(update_fields=['fecha_registro_operativo', 'updated_at'])
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
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.pago_mensual.cobro_pasado_retroactivo', issue_codes)
        self.assertEqual(
            result['aggregate_classification']['pagos_mensuales']['classification'],
            'defectuoso',
        )

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

    def test_company_tenant_with_invalid_representative_snapshot_rut_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        arrendatario = contrato.arrendatario
        arrendatario.tipo_arrendatario = TipoArrendatario.COMPANY
        arrendatario.save(update_fields=['tipo_arrendatario', 'updated_at'])
        contrato.snapshot_representante_legal = {
            'nombre': 'Representante Legal Controlado',
            'rut': '12.345.678-9',
        }
        contrato.save(update_fields=['snapshot_representante_legal', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.representante_legal_snapshot_rut_invalido', issue_codes)

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

    def test_future_contract_with_new_tenant_without_replacement_audit_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2026, 12, 31),
            causal='Termino controlado para cambio de arrendatario',
            estado=EstadoAvisoTermino.REGISTERED,
        )
        new_tenant = Arrendatario.objects.create(
            tipo_arrendatario=TipoArrendatario.NATURAL,
            nombre_razon_social='Arrendatario Nuevo Controlado',
            rut='44444444-4',
            email='arrendatario-nuevo@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio Nuevo 123',
            estado_contacto=EstadoContactoArrendatario.ACTIVE,
        )
        ContactoPagoArrendatario.objects.create(
            arrendatario=new_tenant,
            nombre='Contacto Pago Nuevo',
            rol_operativo='pago_arriendo',
            email='pagos-nuevo@example.com',
            evidencia_autorizacion_ref='contacto-pago-nuevo-v1',
            es_principal=True,
            estado='activo',
        )
        future_contract = self._create_future_contract_for(contrato)
        future_contract.arrendatario = new_tenant
        future_contract.save(update_fields=['arrendatario', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_futuro.cambio_arrendatario_sin_auditoria', issue_codes)

    def test_future_contract_with_new_tenant_and_replacement_audit_can_pass(self):
        contrato = self._create_valid_stage1_matrix()
        aviso = AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2026, 12, 31),
            causal='Termino controlado para cambio de arrendatario',
            estado=EstadoAvisoTermino.REGISTERED,
        )
        new_tenant = Arrendatario.objects.create(
            tipo_arrendatario=TipoArrendatario.NATURAL,
            nombre_razon_social='Arrendatario Nuevo Auditado',
            rut='55555555-5',
            email='arrendatario-nuevo-auditado@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio Nuevo Auditado 123',
            estado_contacto=EstadoContactoArrendatario.ACTIVE,
        )
        ContactoPagoArrendatario.objects.create(
            arrendatario=new_tenant,
            nombre='Contacto Pago Nuevo Auditado',
            rol_operativo='pago_arriendo',
            email='pagos-nuevo-auditado@example.com',
            evidencia_autorizacion_ref='contacto-pago-nuevo-auditado-v1',
            es_principal=True,
            estado='activo',
        )
        future_contract = self._create_future_contract_for(contrato)
        future_contract.arrendatario = new_tenant
        future_contract.save(update_fields=['arrendatario', 'updated_at'])
        AuditEvent.objects.create(
            event_type=TENANT_REPLACEMENT_EVENT_TYPE,
            entity_type='contrato',
            entity_id=str(future_contract.pk),
            summary='Cambio de arrendatario auditado.',
            metadata={
                'contrato_anterior_id': contrato.pk,
                'contrato_nuevo_id': future_contract.pk,
                'aviso_termino_id': aviso.pk,
                'arrendatario_anterior_id': contrato.arrendatario_id,
                'arrendatario_nuevo_id': new_tenant.pk,
            },
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('stage1.contrato_futuro.cambio_arrendatario_sin_auditoria', issue_codes)

    def test_future_contract_with_executed_renewal_conflict_needs_guided_resolution(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_fin_vigente = date(2027, 12, 31)
        contrato.save(update_fields=['fecha_fin_vigente', 'updated_at'])
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2027, 1, 1),
            fecha_fin=date(2027, 12, 31),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='renovacion',
            origen_periodo='renovacion_automatica',
        )
        AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2026, 12, 31),
            causal='Termino controlado con renovacion ya ejecutada',
            estado=EstadoAvisoTermino.REGISTERED,
        )
        self._create_future_contract_for(contrato)

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato_futuro.conflicto_renovacion_sin_resolucion', issue_codes)

    def test_early_terminated_partial_month_without_audit_event_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        partial_contract = Contrato.objects.create(
            codigo_contrato='CON-EARLY-PARTIAL',
            mandato_operacion=contrato.mandato_operacion,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2025, 1, 1),
            fecha_fin_vigente=date(2025, 6, 15),
            terminacion_anticipada_prorrata_ref='early-term-proration-controlled',
            terminacion_anticipada_prorrata_motivo='Prorrata aprobada por termino anticipado.',
            dia_pago_mensual=5,
            estado=EstadoContrato.EARLY_TERMINATED,
        )
        ContratoPropiedad.objects.create(
            contrato=partial_contract,
            propiedad=contrato.mandato_operacion.propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='003',
        )
        PeriodoContractual.objects.create(
            contrato=partial_contract,
            numero_periodo=1,
            fecha_inicio=date(2025, 1, 1),
            fecha_fin=date(2025, 6, 15),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='terminacion_anticipada',
            origen_periodo='decision_controlada',
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.terminacion_anticipada_prorrata_sin_auditoria', issue_codes)

    def test_early_terminated_partial_month_with_audit_event_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        partial_contract = Contrato.objects.create(
            codigo_contrato='CON-EARLY-PARTIAL-AUDIT',
            mandato_operacion=contrato.mandato_operacion,
            arrendatario=contrato.arrendatario,
            fecha_inicio=date(2025, 1, 1),
            fecha_fin_vigente=date(2025, 6, 15),
            terminacion_anticipada_prorrata_ref='early-term-proration-audited',
            terminacion_anticipada_prorrata_motivo='Prorrata aprobada por decision controlada.',
            dia_pago_mensual=5,
            estado=EstadoContrato.EARLY_TERMINATED,
        )
        ContratoPropiedad.objects.create(
            contrato=partial_contract,
            propiedad=contrato.mandato_operacion.propiedad,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='004',
        )
        PeriodoContractual.objects.create(
            contrato=partial_contract,
            numero_periodo=1,
            fecha_inicio=date(2025, 1, 1),
            fecha_fin=date(2025, 6, 15),
            monto_base='250000.00',
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='terminacion_anticipada',
            origen_periodo='decision_controlada',
        )
        AuditEvent.objects.create(
            event_type=EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE,
            entity_type='contrato',
            entity_id=str(partial_contract.pk),
            summary='Decision auditada para prorrata de termino anticipado.',
            metadata={
                'terminacion_anticipada_prorrata_ref': 'early-term-proration-audited',
            },
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('stage1.contrato.terminacion_anticipada_prorrata_sin_auditoria', issue_codes)

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

    def test_key_delivery_without_guarantee_or_authorization_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_entrega = date(2026, 1, 1)
        contrato.save(update_fields=['fecha_entrega', 'updated_at'])
        contrato.garantia_contractual.delete()

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.garantia_faltante', issue_codes)
        self.assertIn('stage1.contrato.entrega_llaves_sin_garantia_autorizada', issue_codes)

    def test_key_delivery_with_incomplete_guarantee_without_authorization_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_entrega = date(2026, 1, 1)
        contrato.save(update_fields=['fecha_entrega', 'updated_at'])
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('500000.00')
        garantia.monto_recibido = Decimal('250000.00')
        garantia.estado_garantia = EstadoGarantia.HELD
        garantia.fecha_recepcion = date(2026, 1, 1)
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'estado_garantia',
                'fecha_recepcion',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.entrega_llaves_garantia_no_cubierta', issue_codes)

    def test_key_delivery_authorization_suppresses_delivery_specific_blocker(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_entrega = date(2026, 1, 1)
        contrato.entrega_llaves_autorizacion_ref = 'acta-entrega-llaves-001'
        contrato.entrega_llaves_autorizacion_motivo = 'Autorizacion operativa aprobada por administracion.'
        contrato.save(
            update_fields=[
                'fecha_entrega',
                'entrega_llaves_autorizacion_ref',
                'entrega_llaves_autorizacion_motivo',
                'updated_at',
            ]
        )
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('500000.00')
        garantia.monto_recibido = Decimal('250000.00')
        garantia.estado_garantia = EstadoGarantia.HELD
        garantia.fecha_recepcion = date(2026, 1, 1)
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'estado_garantia',
                'fecha_recepcion',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertNotIn('stage1.contrato.entrega_llaves_sin_garantia_autorizada', issue_codes)
        self.assertNotIn('stage1.contrato.entrega_llaves_garantia_no_cubierta', issue_codes)

    def test_key_delivery_authorization_with_sensitive_reference_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.fecha_entrega = date(2026, 1, 1)
        contrato.entrega_llaves_autorizacion_ref = 'https://secreto.local/token=abc'
        contrato.entrega_llaves_autorizacion_motivo = 'Autorizacion operativa.'
        contrato.save(
            update_fields=[
                'fecha_entrega',
                'entrega_llaves_autorizacion_ref',
                'entrega_llaves_autorizacion_motivo',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.entrega_llaves_autorizacion_sensible', issue_codes)

    def test_active_contract_without_document_policy_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.politica_documental = None
        contrato.save(update_fields=['politica_documental', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.politica_documental_faltante', issue_codes)

    def test_active_contract_with_non_main_document_policy_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        addendum_policy = PoliticaFirmaYNotaria.objects.create(tipo_documental=TipoDocumental.ADDENDUM)
        contrato.politica_documental = addendum_policy
        contrato.save(update_fields=['politica_documental', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.politica_documental_tipo_invalido', issue_codes)

    def test_active_contract_with_inactive_document_policy_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.politica_documental.estado = EstadoPoliticaFirma.INACTIVE
        contrato.politica_documental.save(update_fields=['estado', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.politica_documental_no_activa', issue_codes)

    def test_natural_tenant_missing_document_profile_required_by_policy_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.politica_documental.requiere_nacionalidad_arrendatario = True
        contrato.politica_documental.requiere_estado_civil_arrendatario = True
        contrato.politica_documental.requiere_profesion_arrendatario = True
        contrato.politica_documental.save(
            update_fields=[
                'requiere_nacionalidad_arrendatario',
                'requiere_estado_civil_arrendatario',
                'requiere_profesion_arrendatario',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.arrendatario.nacionalidad_documental_faltante', issue_codes)
        self.assertIn('stage1.arrendatario.estado_civil_documental_faltante', issue_codes)
        self.assertIn('stage1.arrendatario.profesion_documental_faltante', issue_codes)

    def test_natural_tenant_document_profile_required_by_policy_can_pass(self):
        contrato = self._create_valid_stage1_matrix()
        tenant = contrato.arrendatario
        tenant.nacionalidad = 'chilena'
        tenant.estado_civil = 'soltero'
        tenant.profesion = 'arquitecto'
        tenant.save(update_fields=['nacionalidad', 'estado_civil', 'profesion', 'updated_at'])
        contrato.politica_documental.requiere_nacionalidad_arrendatario = True
        contrato.politica_documental.requiere_estado_civil_arrendatario = True
        contrato.politica_documental.requiere_profesion_arrendatario = True
        contrato.politica_documental.save(
            update_fields=[
                'requiere_nacionalidad_arrendatario',
                'requiere_estado_civil_arrendatario',
                'requiere_profesion_arrendatario',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertNotIn('stage1.arrendatario.nacionalidad_documental_faltante', issue_codes)
        self.assertNotIn('stage1.arrendatario.estado_civil_documental_faltante', issue_codes)
        self.assertNotIn('stage1.arrendatario.profesion_documental_faltante', issue_codes)

    def test_contract_property_linked_without_primary_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        link = contrato.contrato_propiedades.get(rol_en_contrato=RolContratoPropiedad.PRIMARY)
        link.rol_en_contrato = RolContratoPropiedad.LINKED
        link.save(update_fields=['rol_en_contrato', 'updated_at'])

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.propiedad_principal_invalida', issue_codes)
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['contrato_propiedades']['classification'], 'defectuoso')

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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
                autoridad_operativa_nombre='Representante Operativo',
                autoridad_operativa_rut='12345678-5',
                autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
        garantia.aceptacion_parcial_ref = 'partial-guarantee-acceptance-controlled'
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'fecha_recepcion',
                'estado_garantia',
                'aceptacion_parcial_ref',
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

    def test_guarantee_excess_without_resolution_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('120000.00')
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
            monto_clp=Decimal('120000.00'),
            fecha=date(2026, 1, 5),
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.garantia.exceso_sin_resolucion', issue_codes)
        self.assertEqual(result['aggregate_classification']['garantias_contractuales']['classification'], 'defectuoso')

    def test_guarantee_excess_with_resolution_can_pass_stage1_matrix_gate(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('120000.00')
        garantia.fecha_recepcion = date(2026, 1, 5)
        garantia.estado_garantia = EstadoGarantia.HELD
        garantia.resolucion_exceso_garantia = 'bloquear'
        garantia.resolucion_exceso_garantia_ref = 'manual-resolution-guarantee-excess-controlled'
        garantia.resolucion_exceso_garantia_motivo = 'Exceso identificado y bloqueado para resolucion controlada.'
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'fecha_recepcion',
                'estado_garantia',
                'resolucion_exceso_garantia',
                'resolucion_exceso_garantia_ref',
                'resolucion_exceso_garantia_motivo',
                'updated_at',
            ]
        )
        HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento=TipoMovimientoGarantia.DEPOSIT,
            monto_clp=Decimal('120000.00'),
            fecha=date(2026, 1, 5),
        )

        result = self._collect_controlled_snapshot()

        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')

    def test_partial_received_guarantee_without_acceptance_is_blocking(self):
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
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.garantia.parcial_sin_aceptacion', issue_codes)
        self.assertEqual(result['aggregate_classification']['garantias_contractuales']['classification'], 'defectuoso')

    def test_closed_guarantee_before_reception_date_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.monto_devuelto = Decimal('50000.00')
        garantia.fecha_recepcion = date(2026, 1, 5)
        garantia.fecha_cierre = date(2026, 1, 4)
        garantia.estado_garantia = EstadoGarantia.RETURNED
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'monto_devuelto',
                'fecha_recepcion',
                'fecha_cierre',
                'estado_garantia',
                'updated_at',
            ]
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.garantia.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['garantias_contractuales']['classification'], 'defectuoso')

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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
            politica_documental=contrato.politica_documental,
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

    def test_guarantee_history_derived_without_origin_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.monto_devuelto = Decimal('50000.00')
        garantia.fecha_recepcion = date(2026, 1, 10)
        garantia.fecha_cierre = date(2026, 1, 31)
        garantia.estado_garantia = EstadoGarantia.RETURNED
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'monto_devuelto',
                'fecha_recepcion',
                'fecha_cierre',
                'estado_garantia',
                'updated_at',
            ]
        )
        HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento=TipoMovimientoGarantia.DEPOSIT,
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 10),
        )
        HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento=TipoMovimientoGarantia.TOTAL_RETURN,
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 31),
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.historial_garantia.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['historial_garantias']['classification'], 'defectuoso')

    def test_guarantee_history_derived_date_before_origin_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.monto_devuelto = Decimal('50000.00')
        garantia.fecha_recepcion = date(2026, 1, 10)
        garantia.fecha_cierre = date(2026, 1, 11)
        garantia.estado_garantia = EstadoGarantia.RETURNED
        garantia.save(
            update_fields=[
                'monto_pactado',
                'monto_recibido',
                'monto_devuelto',
                'fecha_recepcion',
                'fecha_cierre',
                'estado_garantia',
                'updated_at',
            ]
        )
        origin = HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento=TipoMovimientoGarantia.DEPOSIT,
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 10),
        )
        HistorialGarantia.objects.create(
            garantia_contractual=garantia,
            tipo_movimiento=TipoMovimientoGarantia.TOTAL_RETURN,
            monto_clp=Decimal('50000.00'),
            fecha=date(2026, 1, 9),
            movimiento_origen=origin,
        )

        result = self._collect_controlled_snapshot()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.historial_garantia.validacion_modelo', issue_codes)
        self.assertEqual(result['aggregate_classification']['historial_garantias']['classification'], 'defectuoso')

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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
            politica_documental=contrato.politica_documental,
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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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
            politica_documental=contrato.politica_documental,
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

    def test_payment_effective_code_effect_mismatch_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        payment.monto_efecto_codigo_efectivo_clp = Decimal('0.00')
        payment.save(update_fields=['monto_efecto_codigo_efectivo_clp', 'updated_at'])
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
        self.assertEqual(result['aggregate_classification']['pagos_mensuales']['classification'], 'defectuoso')

    def test_payment_month_outside_contractual_period_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        first_period = contrato.periodos_contractuales.get(numero_periodo=1)
        first_period.fecha_fin = date(2026, 6, 30)
        first_period.save(update_fields=['fecha_fin', 'updated_at'])
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base=Decimal('260000.00'),
            moneda_base=MonedaBaseContrato.CLP,
            tipo_periodo='renovacion',
            origen_periodo='snapshot_controlado',
        )
        payment = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=first_period,
            mes=7,
            anio=2026,
            monto_facturable_clp=Decimal('250000.00'),
            monto_calculado_clp=Decimal('250001.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('1.00'),
            monto_pagado_clp=Decimal('0.00'),
            fecha_vencimiento=date(2026, 7, 5),
            codigo_conciliacion_efectivo='001',
        )
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
        self.assertEqual(result['aggregate_classification']['pagos_mensuales']['classification'], 'defectuoso')

    def test_payment_due_date_outside_operational_month_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        payment.fecha_vencimiento = date(2026, 2, 5)
        payment.save(update_fields=['fecha_vencimiento', 'updated_at'])
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
        self.assertEqual(result['aggregate_classification']['pagos_mensuales']['classification'], 'defectuoso')

    def test_paid_payment_without_traceable_payment_evidence_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        payment = self._create_payment_for(contrato)
        payment.estado_pago = EstadoPago.PAID
        payment.monto_pagado_clp = Decimal('0.00')
        payment.save(update_fields=['estado_pago', 'monto_pagado_clp', 'updated_at'])
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
        self.assertEqual(result['aggregate_classification']['pagos_mensuales']['classification'], 'defectuoso')

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
