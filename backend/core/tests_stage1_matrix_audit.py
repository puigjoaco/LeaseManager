from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from cobranza.models import EstadoGarantia, GarantiaContractual
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from contratos.models import (
    Arrendatario,
    Contrato,
    ContratoPropiedad,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RolContratoPropiedad,
    TipoArrendatario,
)
from core.stage1_matrix_audit import collect_stage1_matrix_audit
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
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
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario=TipoArrendatario.NATURAL,
            nombre_razon_social='Arrendatario Controlado',
            rut='33333333-3',
            email='arrendatario@example.com',
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

    def test_empty_database_is_not_evidence_grade_ready(self):
        result = collect_stage1_matrix_audit(source_kind='local')

        self.assertFalse(result['has_required_stage1_data'])
        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'implementado_sin_evidencia')

    def test_valid_controlled_snapshot_can_pass_stage1_matrix_gate(self):
        self._create_valid_stage1_matrix()

        result = collect_stage1_matrix_audit(source_kind='snapshot_controlado', require_data=True)

        self.assertTrue(result['has_required_stage1_data'])
        self.assertTrue(result['evidence_grade'])
        self.assertTrue(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertEqual(result['issue_counts'].get('blocking', 0), 0)
        self.assertGreater(result['summary']['participaciones_patrimoniales'], 0)
        self.assertGreater(result['summary']['representaciones_comunidad'], 0)

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

        result = collect_stage1_matrix_audit(source_kind='snapshot_controlado', require_data=True)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.participacion.validacion_modelo', issue_codes)
        self.assertIn('stage1.arrendatario.validacion_modelo', issue_codes)

    def test_contract_without_matrix_components_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        contrato.contrato_propiedades.all().delete()
        contrato.periodos_contractuales.all().delete()
        contrato.garantia_contractual.delete()

        result = collect_stage1_matrix_audit(source_kind='snapshot_controlado', require_data=True)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.contrato.propiedad_principal_invalida', issue_codes)
        self.assertIn('stage1.contrato.periodos_faltantes', issue_codes)
        self.assertIn('stage1.contrato.garantia_faltante', issue_codes)

    def test_inconsistent_guarantee_state_is_blocking(self):
        contrato = self._create_valid_stage1_matrix()
        garantia = contrato.garantia_contractual
        garantia.monto_pactado = Decimal('100000.00')
        garantia.monto_recibido = Decimal('50000.00')
        garantia.estado_garantia = EstadoGarantia.PENDING
        garantia.save(update_fields=['monto_pactado', 'monto_recibido', 'estado_garantia', 'updated_at'])

        result = collect_stage1_matrix_audit(source_kind='snapshot_controlado', require_data=True)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.garantia.validacion_modelo', issue_codes)

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

        result = collect_stage1_matrix_audit(source_kind='snapshot_controlado', require_data=True)
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

        result = collect_stage1_matrix_audit(source_kind='snapshot_controlado', require_data=True)
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage1_close'])
        self.assertEqual(result['classification'], 'defectuoso')
        self.assertIn('stage1.codigo_efectivo.duplicado_en_cuenta', issue_codes)
        self.assertIn('stage1.contrato_propiedad.validacion_modelo', issue_codes)

    def test_command_can_fail_when_required_data_is_missing(self):
        with self.assertRaises(CommandError):
            call_command(
                'audit_stage1_matrix',
                source_kind='snapshot_controlado',
                require_data=True,
                fail_on_violations=True,
                stdout=StringIO(),
            )
