import json

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from cobranza.models import PagoMensual
from cobranza.services import sync_payment_distribution
from contabilidad.models import CierreMensualContable, ConfiguracionFiscalEmpresa, ObligacionTributariaMensual, RegimenTributarioEmpresa
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual

from .admin import (
    CapacidadTributariaSIIAdmin,
    DDJJPreparacionAnualAdmin,
    DTEEmitidoAdmin,
    F22PreparacionAnualAdmin,
    F29PreparacionMensualAdmin,
    ProcesoRentaAnualAdmin,
)
from .models import CapacidadTributariaSII, DDJJPreparacionAnual, DTEEmitido, EstadoGateSII, F22PreparacionAnual, F29PreparacionMensual, ProcesoRentaAnual


class SiiAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='sii',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='SiiCo', rut='88888888-8'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', '11111111-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', '22222222-2')
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

    def _setup_paid_payment(self, with_facturadora=True, monto_facturable='100000.00', monto_cobrado='100111.00'):
        empresa = self._create_active_empresa()
        propiedad = Propiedad.objects.create(
            direccion='Av SII',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='SII-001',
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta='ACC-SII',
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
            entidad_facturadora=empresa if with_facturadora else None,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=with_facturadora,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario SII',
            rut='44444444-4',
            email='tenant@example.com',
            telefono='999',
            domicilio_notificaciones='Dir 123',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='SII-CTR',
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
            monto_facturable_clp=monto_facturable,
            monto_calculado_clp=monto_cobrado,
            monto_pagado_clp=monto_cobrado,
            fecha_vencimiento='2026-01-05',
            fecha_deposito_banco='2026-01-08',
            estado_pago='pagado',
            dias_mora=3,
            codigo_conciliacion_efectivo='111',
        )
        sync_payment_distribution(pago)
        return empresa, pago

    def _activate_capability(self, empresa, estado_gate='abierto', capacidad_key='DTEEmision', prefix='dte'):
        return self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': capacidad_key,
                **self._sii_readiness_fields(prefix),
                'ambiente': 'certificacion',
                'estado_gate': estado_gate,
                'ultimo_resultado': {},
            },
            format='json',
        )

    def _sii_readiness_fields(self, prefix):
        return {
            'certificado_ref': f'certificado-{prefix}-ref',
            'evidencia_ref': f'evidencia-{prefix}-gate',
            'prueba_flujo_ref': f'prueba-{prefix}-flujo',
            'autorizacion_ambiente_ref': f'ambiente-{prefix}-certificacion',
            'regla_fiscal_ref': f'regla-{prefix}-validada',
        }

    def _activate_fiscal_config(self, empresa, ddjj_habilitadas=None):
        regime, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regime,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=ddjj_habilitadas or [],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )

    def _create_monthly_close_and_obligation(self, empresa, estado_preparacion='preparado'):
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )
        obligation = ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100111.00',
            monto_calculado='10011.10',
            estado_preparacion=estado_preparacion,
        )
        return close, obligation

    def _create_twelve_approved_closes(self, empresa, fiscal_year=2026):
        for month in range(1, 13):
            CierreMensualContable.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                estado='aprobado',
            )
            ObligacionTributariaMensual.objects.create(
                empresa=empresa,
                anio=fiscal_year,
                mes=month,
                obligacion_tipo='PPM',
                base_imponible='100111.00',
                monto_calculado='10011.10',
                estado_preparacion='preparado',
            )

    def _activate_annual_capabilities(self, empresa):
        for capability_key in ('DDJJPreparacion', 'F22Preparacion'):
            response = self.client.post(
                reverse('sii-capacidad-list'),
                {
                    'empresa': empresa.id,
                    'capacidad_key': capability_key,
                    **self._sii_readiness_fields(capability_key.lower()),
                    'ambiente': 'certificacion',
                    'estado_gate': 'abierto',
                    'ultimo_resultado': {},
                },
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_auth_is_required_for_sii_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('sii-capacidad-list'),
            reverse('sii-dte-list'),
            reverse('sii-dte-generate'),
        ]
        for url in urls:
            response = client.get(url) if 'generar' not in url else client.post(url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_generate_dte_draft_requires_capability_and_fiscal_setup(self):
        empresa, pago = self._setup_paid_payment()
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self._activate_fiscal_config(empresa)
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self._activate_capability(empresa)
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_tax_artifacts_reject_wrong_sii_capability_kind(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        wrong_f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('wrong-f29'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        wrong_dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            **self._sii_readiness_fields('wrong-dte'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido(
            empresa=empresa,
            capacidad_tributaria=wrong_f29_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
        )
        with self.assertRaisesMessage(ValidationError, 'DTEEmision'):
            dte.full_clean()

        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=wrong_dte_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
        )
        with self.assertRaisesMessage(ValidationError, 'F29Preparacion'):
            f29.full_clean()

        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'source': 'controlled'},
        )
        with self.assertRaisesMessage(ValidationError, 'DDJJPreparacion'):
            ddjj.full_clean()

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'source': 'controlled'},
        )
        with self.assertRaisesMessage(ValidationError, 'F22Preparacion'):
            f22.full_clean()

    def test_annual_tax_payloads_require_expected_commercial_year(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        wrong_summary = {
            'fiscal_year': 2025,
            'obligaciones': [{'anio': 2025, 'mes': 1, 'tipo': 'PPM'}],
        }

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual=wrong_summary,
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('resumen_anual', process_error.exception.message_dict)

        stored_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'anio': 2026, 'mes': 1, 'tipo': 'PPM'}]},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'resumen_anual': wrong_summary},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('resumen_paquete', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'resumen_anual': wrong_summary},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('resumen_f22', f22_error.exception.message_dict)

    def test_tax_payloads_reject_sensitive_keys(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'api_key': None},
        )
        with self.assertRaises(ValidationError) as f29_error:
            f29.full_clean()
        self.assertIn('resumen_formulario', f29_error.exception.message_dict)

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'access_token': None},
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('resumen_anual', process_error.exception.message_dict)

        stored_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'resumen_anual': {'fiscal_year': 2026}, 'credential': None},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('resumen_paquete', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'resumen_anual': {'fiscal_year': 2026}, 'secret': None},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('resumen_f22', f22_error.exception.message_dict)

    def test_tax_artifacts_require_traceable_ref_for_advanced_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='abierto',
            ultimo_resultado={},
        )

        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
        )
        with self.assertRaises(ValidationError) as f29_error:
            f29.full_clean()
        self.assertIn('borrador_ref', f29_error.exception.message_dict)

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='aprobado_para_presentacion',
            resumen_anual={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('paquete_ddjj_ref', process_error.exception.message_dict)
        self.assertIn('borrador_f22_ref', process_error.exception.message_dict)

        prepared_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=prepared_process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('paquete_ref', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=prepared_process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('borrador_ref', f22_error.exception.message_dict)

    def test_tax_artifacts_require_active_fiscal_config(self):
        empresa, pago = self._setup_paid_payment()
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            **self._sii_readiness_fields('dte-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22-no-fiscal'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
        )
        with self.assertRaises(ValidationError) as dte_error:
            dte.full_clean()
        self.assertIn('empresa', dte_error.exception.message_dict)

        f29 = F29PreparacionMensual(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'obligaciones': [{'tipo': 'PPM'}]},
        )
        with self.assertRaises(ValidationError) as f29_error:
            f29.full_clean()
        self.assertIn('empresa', f29_error.exception.message_dict)

        process = ProcesoRentaAnual(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as process_error:
            process.full_clean()
        self.assertIn('empresa', process_error.exception.message_dict)

        stored_process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'source': 'controlled'},
        )
        ddjj = DDJJPreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as ddjj_error:
            ddjj.full_clean()
        self.assertIn('empresa', ddjj_error.exception.message_dict)

        f22 = F22PreparacionAnual(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=stored_process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'source': 'controlled'},
        )
        with self.assertRaises(ValidationError) as f22_error:
            f22.full_clean()
        self.assertIn('empresa', f22_error.exception.message_dict)

    def test_open_sii_capability_requires_readiness_references(self):
        empresa = self._create_active_empresa()

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                'certificado_ref': 'certificado-sii-ref',
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_ref', response.data)
        self.assertIn('prueba_flujo_ref', response.data)
        self.assertIn('regla_fiscal_ref', response.data)

        self._activate_fiscal_config(empresa)
        response = self._activate_capability(empresa)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_open_sii_capability_rejects_sensitive_references(self):
        empresa = self._create_active_empresa()

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                **self._sii_readiness_fields('dte'),
                'certificado_ref': 'https://sii.example.test/cert?token=secret',
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('certificado_ref', response.data)

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'produccion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {
                    'autorizacion_produccion_ref': 'prod-auth-safe',
                    'api_key': None,
                },
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ultimo_resultado', response.data)

    def test_open_sii_capability_rejects_unsupported_fiscal_regime(self):
        empresa = self._create_active_empresa(nombre='SII Unsupported Regime SpA', rut='33333333-3')
        unsupported_regime = RegimenTributarioEmpresa.objects.create(
            codigo_regimen='RentaPresuntaV1',
            descripcion='Regimen no automatizable en v1',
            estado='activa',
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=unsupported_regime,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                **self._sii_readiness_fields('unsupported-regime'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('empresa', response.data)

    def test_open_sii_capability_requires_active_fiscal_config(self):
        empresa = self._create_active_empresa(nombre='SII No Fiscal Config SpA', rut='34343434-3')

        response = self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                **self._sii_readiness_fields('missing-fiscal-config'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('empresa', response.data)

    def test_sii_apis_redact_inherited_sensitive_references(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='https://sii.example.test/cert?token=secret',
            evidencia_ref='https://sii.example.test/evidence?token=secret',
            prueba_flujo_ref='https://sii.example.test/flow?token=secret',
            autorizacion_ambiente_ref='https://sii.example.test/env?token=secret',
            regla_fiscal_ref='https://sii.example.test/rule?token=secret',
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={'access_token': 'opaque-token-value', 'safe_ref': 'controlled-result'},
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido.objects.create(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
            estado_dte='aceptado',
            sii_track_id='https://sii.example.test/track?token=secret',
            ultimo_estado_sii='Aceptado controlado',
            observaciones='Observacion con https://sii.example.test/obs?token=secret',
        )
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29 = F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'callback': 'https://sii.example.test/f29?token=secret'},
            borrador_ref='https://sii.example.test/f29?token=secret',
            observaciones='Observacion con https://sii.example.test/f29?token=secret',
        )
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'callback': 'https://sii.example.test/anual?token=secret'},
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'api_key': 'secret-api-key-value'},
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            observaciones='Observacion con https://sii.example.test/ddjj?token=secret',
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'access_token': 'secret-f22-token-value'},
            borrador_ref='https://sii.example.test/f22?token=secret',
            observaciones='Observacion con https://sii.example.test/f22?token=secret',
        )

        capabilities = self.client.get(reverse('sii-capacidad-list'))
        capability_detail = self.client.get(reverse('sii-capacidad-detail', args=[dte_capability.id]))
        dtes = self.client.get(reverse('sii-dte-list'))
        dte_detail = self.client.get(reverse('sii-dte-detail', args=[dte.id]))
        f29s = self.client.get(reverse('sii-f29-list'))
        f29_detail = self.client.get(reverse('sii-f29-detail', args=[f29.id]))
        annual = self.client.get(reverse('sii-anual-list'))
        ddjjs = self.client.get(reverse('sii-ddjj-list'))
        f22s = self.client.get(reverse('sii-f22-list'))
        snapshot = self.client.get(reverse('sii-snapshot'))

        capability_data = next(item for item in capabilities.data if item['id'] == dte_capability.id)
        self.assertEqual(capability_data['certificado_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_data['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_data['ultimo_resultado']['access_token'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_data['ultimo_resultado']['safe_ref'], 'controlled-result')
        self.assertEqual(capability_detail.data['regla_fiscal_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dtes.data[0]['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dtes.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dte_detail.data['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dte_detail.data['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29s.data[0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29s.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_detail.data['resumen_formulario']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_detail.data['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        process_data = next(item for item in annual.data if item['id'] == process.id)
        self.assertEqual(process_data['paquete_ddjj_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(process_data['resumen_anual']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjjs.data[0]['paquete_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjjs.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjjs.data[0]['resumen_paquete']['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22s.data[0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22s.data[0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22s.data[0]['resumen_f22']['access_token'], REDACTED_SENSITIVE_REFERENCE)
        snapshot_capability = next(item for item in snapshot.data['capacidades'] if item['id'] == dte_capability.id)
        self.assertEqual(snapshot_capability['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['dtes'][0]['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['dtes'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f29s'][0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f29s'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['ddjjs'][0]['paquete_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['ddjjs'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f22s'][0]['borrador_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot.data['f22s'][0]['observaciones'], REDACTED_SENSITIVE_REFERENCE)

        body = b''.join(
            response.content
            for response in [capabilities, capability_detail, dtes, dte_detail, f29s, f29_detail, annual, ddjjs, f22s, snapshot]
        ).decode()
        self.assertNotIn('sii.example.test', body)
        self.assertNotIn('opaque-token-value', body)
        self.assertNotIn('secret-api-key-value', body)
        self.assertEqual(ddjj.estado_preparacion, 'aprobado_para_presentacion')
        self.assertEqual(f22.estado_preparacion, 'aprobado_para_presentacion')

    def test_sii_admin_redacts_sensitive_tax_refs_and_payloads(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        dte_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='https://sii.example.test/cert?token=secret',
            evidencia_ref='https://sii.example.test/evidence?token=secret',
            prueba_flujo_ref='https://sii.example.test/flow?token=secret',
            autorizacion_ambiente_ref='https://sii.example.test/env?token=secret',
            regla_fiscal_ref='https://sii.example.test/rule?token=secret',
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={'access_token': 'opaque-token-value', 'safe_ref': 'controlled-result'},
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            **self._sii_readiness_fields('f29'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        ddjj_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DDJJPreparacion',
            **self._sii_readiness_fields('ddjj'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F22Preparacion',
            **self._sii_readiness_fields('f22'),
            ambiente='certificacion',
            estado_gate='condicionado',
            ultimo_resultado={},
        )
        distribution = pago.distribuciones_cobro.get()
        dte = DTEEmitido.objects.create(
            empresa=empresa,
            capacidad_tributaria=dte_capability,
            contrato=pago.contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=distribution,
            arrendatario=pago.contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp=distribution.monto_facturable_clp,
            fecha_emision='2026-01-08',
            estado_dte='aceptado',
            sii_track_id='https://sii.example.test/track?token=secret',
            ultimo_estado_sii='Aceptado controlado',
            observaciones='Observacion con https://sii.example.test/obs?token=secret',
        )
        close, _ = self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        f29 = F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='aprobado_para_presentacion',
            resumen_formulario={'callback': 'https://sii.example.test/f29?token=secret'},
            borrador_ref='https://sii.example.test/f29?token=secret',
            observaciones='Observacion con https://sii.example.test/f29?token=secret',
        )
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'callback': 'https://sii.example.test/anual?token=secret'},
            paquete_ddjj_ref='https://sii.example.test/ddjj?token=secret',
            borrador_f22_ref='https://sii.example.test/f22?token=secret',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_paquete={'api_key': 'secret-api-key-value'},
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            observaciones='Observacion con https://sii.example.test/ddjj?token=secret',
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='aprobado_para_presentacion',
            resumen_f22={'access_token': 'secret-f22-token-value'},
            borrador_ref='https://sii.example.test/f22?token=secret',
            observaciones='Observacion con https://sii.example.test/f22?token=secret',
        )
        site = AdminSite()

        capability_admin = CapacidadTributariaSIIAdmin(CapacidadTributariaSII, site)
        dte_admin = DTEEmitidoAdmin(DTEEmitido, site)
        f29_admin = F29PreparacionMensualAdmin(F29PreparacionMensual, site)
        process_admin = ProcesoRentaAnualAdmin(ProcesoRentaAnual, site)
        ddjj_admin = DDJJPreparacionAnualAdmin(DDJJPreparacionAnual, site)
        f22_admin = F22PreparacionAnualAdmin(F22PreparacionAnual, site)

        for raw_field in (
            'certificado_ref',
            'evidencia_ref',
            'prueba_flujo_ref',
            'autorizacion_ambiente_ref',
            'regla_fiscal_ref',
            'ultimo_resultado',
        ):
            self.assertNotIn(raw_field, capability_admin.fields)
            self.assertNotIn(raw_field, capability_admin.search_fields)
        self.assertEqual(capability_admin.certificado_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_admin.evidencia_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(capability_admin.prueba_flujo_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            capability_admin.autorizacion_ambiente_ref_redacted(dte_capability),
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(capability_admin.regla_fiscal_ref_redacted(dte_capability), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            capability_admin.ultimo_resultado_redacted(dte_capability)['access_token'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(capability_admin.ultimo_resultado_redacted(dte_capability)['safe_ref'], 'controlled-result')

        self.assertNotIn('sii_track_id', dte_admin.fields)
        self.assertNotIn('observaciones', dte_admin.fields)
        self.assertNotIn('sii_track_id', dte_admin.search_fields)
        self.assertEqual(dte_admin.sii_track_id_redacted(dte), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(dte_admin.observaciones_redacted(dte), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_formulario', f29_admin.fields)
        self.assertNotIn('borrador_ref', f29_admin.fields)
        self.assertNotIn('observaciones', f29_admin.fields)
        self.assertEqual(f29_admin.resumen_formulario_redacted(f29)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_admin.borrador_ref_redacted(f29), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f29_admin.observaciones_redacted(f29), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_anual', process_admin.fields)
        self.assertNotIn('paquete_ddjj_ref', process_admin.fields)
        self.assertNotIn('borrador_f22_ref', process_admin.fields)
        self.assertEqual(process_admin.resumen_anual_redacted(process)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(process_admin.paquete_ddjj_ref_redacted(process), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(process_admin.borrador_f22_ref_redacted(process), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_paquete', ddjj_admin.fields)
        self.assertNotIn('paquete_ref', ddjj_admin.fields)
        self.assertEqual(ddjj_admin.resumen_paquete_redacted(ddjj)['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjj_admin.paquete_ref_redacted(ddjj), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(ddjj_admin.observaciones_redacted(ddjj), REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_f22', f22_admin.fields)
        self.assertNotIn('borrador_ref', f22_admin.fields)
        self.assertEqual(f22_admin.resumen_f22_redacted(f22)['access_token'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22_admin.borrador_ref_redacted(f22), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(f22_admin.observaciones_redacted(f22), REDACTED_SENSITIVE_REFERENCE)

        for model_admin in (capability_admin, dte_admin, f29_admin, process_admin, ddjj_admin, f22_admin):
            self.assertFalse(model_admin.has_add_permission(None))

    def test_generate_dte_draft_rejects_conditioned_gate(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='condicionado')

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_rechecks_readiness_refs(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='cert-directo',
            ambiente='certificacion',
            estado_gate='abierto',
        )

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('readiness SII', response.data['detail'])

    def test_generate_dte_draft_uses_facturable_amount_not_coded_amount(self):
        empresa, pago = self._setup_paid_payment(monto_facturable='100000.00', monto_cobrado='100111.00')
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['monto_neto_clp'], '100000.00')
        self.assertIsNotNone(response.data['distribucion_cobro_mensual'])
        self.assertEqual(response.data['estado_dte'], 'borrador')

    def test_generate_dte_draft_is_idempotent(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        first = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        second = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(DTEEmitido.objects.filter(pago_mensual=pago).count(), 1)

    def test_generate_dte_draft_rejects_missing_facturadora(self):
        empresa, pago = self._setup_paid_payment(with_facturadora=False)
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_only_allows_factura_exenta_from_paid_payment_path(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        for tipo_dte in ('56', '61'):
            response = self.client.post(
                reverse('sii-dte-generate'),
                {'pago_mensual_id': pago.id, 'tipo_dte': tipo_dte},
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(DTEEmitido.objects.filter(pago_mensual=pago).count(), 0)

    def test_update_dte_status_manually(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'enviado_manual_controlado',
                'sii_track_id': '0245399452',
                'ultimo_estado_sii': 'Recibido',
            },
            format='json',
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_dte'], 'enviado_manual_controlado')
        self.assertEqual(update.data['sii_track_id'], '0245399452')

    def test_dte_status_audit_metadata_redacts_inherited_sensitive_tracking_ref(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        DTEEmitido.objects.filter(pk=generated.data['id']).update(
            sii_track_id='https://sii.example.test/track?token=secret'
        )

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {'estado_dte': 'borrador'},
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        event = AuditEvent.objects.filter(
            event_type='sii.dte_emitido.status_updated',
            entity_id=str(generated.data['id']),
        ).latest('id')
        self.assertEqual(event.metadata['sii_track_id'], REDACTED_SENSITIVE_REFERENCE)
        serialized_metadata = json.dumps(event.metadata)
        self.assertNotIn('sii.example.test', serialized_metadata)
        self.assertNotIn('token', serialized_metadata)
        self.assertNotIn('secret', serialized_metadata)

    def test_update_dte_status_requires_tracking_reference_for_external_state(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'aceptado',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sii_track_id', update.data['detail'])

    def test_update_final_dte_status_requires_status_query_capability(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'aceptado',
                'sii_track_id': 'dte-status-track-001',
                'ultimo_estado_sii': 'Aceptado',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('DTEConsultaEstado', update.data['detail'])

    def test_update_final_dte_status_accepts_ready_status_query_capability(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa, estado_gate='abierto')
        self._activate_capability(
            empresa,
            estado_gate='abierto',
            capacidad_key='DTEConsultaEstado',
            prefix='dte-status',
        )
        generated = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-dte-status', args=[generated.data['id']]),
            {
                'estado_dte': 'aceptado',
                'sii_track_id': 'dte-status-track-002',
                'ultimo_estado_sii': 'Aceptado',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_dte'], 'aceptado')
        self.assertEqual(update.data['ultimo_estado_sii'], 'Aceptado')

    def test_sii_status_updates_reject_sensitive_references(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        self._activate_capability(empresa, estado_gate='abierto')
        generated_dte = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        self.assertEqual(generated_dte.status_code, status.HTTP_201_CREATED)

        dte_update = self.client.post(
            reverse('sii-dte-status', args=[generated_dte.data['id']]),
            {
                'estado_dte': 'aceptado',
                'sii_track_id': 'https://sii.example.test/track?token=secret',
                'ultimo_estado_sii': 'Aceptado',
            },
            format='json',
        )
        self.assertEqual(dte_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sii_track_id', dte_update.data['detail'])

        dte_observations_update = self.client.post(
            reverse('sii-dte-status', args=[generated_dte.data['id']]),
            {
                'estado_dte': 'borrador',
                'observaciones': 'No registrar https://sii.example.test/dte?token=secret',
            },
            format='json',
        )
        self.assertEqual(dte_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', dte_observations_update.data['detail'])

        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated_f29 = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated_f29.status_code, status.HTTP_201_CREATED)
        f29_update = self.client.post(
            reverse('sii-f29-status', args=[generated_f29.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'https://sii.example.test/f29?token=secret',
            },
            format='json',
        )
        self.assertEqual(f29_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('borrador_ref', f29_update.data['detail'])

        f29_observations_update = self.client.post(
            reverse('sii-f29-status', args=[generated_f29.data['id']]),
            {
                'estado_preparacion': generated_f29.data['estado_preparacion'],
                'observaciones': 'No registrar https://sii.example.test/f29?token=secret',
            },
            format='json',
        )
        self.assertEqual(f29_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', f29_observations_update.data['detail'])

        annual_empresa = Empresa.objects.create(
            razon_social='Annual Sensitive SpA',
            rut='33333333-3',
            estado='activa',
        )
        self._activate_fiscal_config(annual_empresa, ddjj_habilitadas=['1887'])
        self._activate_annual_capabilities(annual_empresa)
        self._create_twelve_approved_closes(annual_empresa, fiscal_year=2026)
        generated_annual = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': annual_empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated_annual.status_code, status.HTTP_201_CREATED)
        ddjj_update = self.client.post(
            reverse('sii-ddjj-status', args=[generated_annual.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'https://sii.example.test/ddjj?token=secret',
            },
            format='json',
        )
        self.assertEqual(ddjj_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('ref_value', ddjj_update.data['detail'])

        ddjj_observations_update = self.client.post(
            reverse('sii-ddjj-status', args=[generated_annual.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': generated_annual.data['ddjj_preparacion']['estado_preparacion'],
                'observaciones': 'No registrar https://sii.example.test/ddjj?token=secret',
            },
            format='json',
        )
        self.assertEqual(ddjj_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', ddjj_observations_update.data['detail'])

        f22_observations_update = self.client.post(
            reverse('sii-f22-status', args=[generated_annual.data['f22_preparacion']['id']]),
            {
                'estado_preparacion': generated_annual.data['f22_preparacion']['estado_preparacion'],
                'observaciones': 'No registrar https://sii.example.test/f22?token=secret',
            },
            format='json',
        )
        self.assertEqual(f22_observations_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('observaciones', f22_observations_update.data['detail'])

    def test_generate_f29_requires_capability_and_approved_close(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_f29_rejects_conditioned_gate(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'condicionado',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_f29_uses_obligations_and_returns_prepared_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado_preparacion'], 'preparado')
        self.assertEqual(len(response.data['resumen_formulario']['obligaciones']), 1)

    def test_generate_f29_returns_pending_data_when_obligation_is_not_ready(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='pendiente_datos')

        response = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado_preparacion'], 'pendiente_datos')

    def test_update_f29_status_rechecks_gate_for_prepared_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='pendiente_datos')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='F29Preparacion').update(
            estado_gate='condicionado'
        )

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate', update.data['detail'])

    def test_update_f29_status_manually(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'f29-2026-01',
            },
            format='json',
        )
        self.assertEqual(update.status_code, status.HTTP_200_OK)
        self.assertEqual(update.data['estado_preparacion'], 'aprobado_para_presentacion')

    def test_update_f29_status_requires_borrador_ref_for_approved_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')
        generated = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        update = self.client.post(
            reverse('sii-f29-status', args=[generated.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
            },
            format='json',
        )

        self.assertEqual(update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('borrador_ref', update.data['detail'])

    def test_monthly_sii_workflow_from_paid_payment_to_dte_and_f29(self):
        empresa, pago = self._setup_paid_payment(monto_facturable='100000.00', monto_cobrado='100111.00')
        self._activate_fiscal_config(empresa)
        self._activate_capability(empresa)

        dte = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(dte.status_code, status.HTTP_201_CREATED)
        self.assertEqual(dte.data['monto_neto_clp'], '100000.00')
        self.assertEqual(dte.data['estado_dte'], 'borrador')

        dte_status = self.client.post(
            reverse('sii-dte-status', args=[dte.data['id']]),
            {
                'estado_dte': 'enviado_manual_controlado',
                'sii_track_id': '0245399452',
                'ultimo_estado_sii': 'Recibido',
            },
            format='json',
        )
        self.assertEqual(dte_status.status_code, status.HTTP_200_OK)
        self.assertEqual(dte_status.data['estado_dte'], 'enviado_manual_controlado')

        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                **self._sii_readiness_fields('f29'),
                'ambiente': 'certificacion',
                'estado_gate': 'abierto',
                'ultimo_resultado': {},
            },
            format='json',
        )
        self._create_monthly_close_and_obligation(empresa, estado_preparacion='preparado')

        f29 = self.client.post(
            reverse('sii-f29-generate'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(f29.status_code, status.HTTP_201_CREATED)
        self.assertEqual(f29.data['estado_preparacion'], 'preparado')
        self.assertEqual(len(f29.data['resumen_formulario']['obligaciones']), 1)

        f29_status = self.client.post(
            reverse('sii-f29-status', args=[f29.data['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'borrador_ref': 'f29-2026-01',
            },
            format='json',
        )
        self.assertEqual(f29_status.status_code, status.HTTP_200_OK)
        self.assertEqual(f29_status.data['estado_preparacion'], 'aprobado_para_presentacion')

    def test_generate_annual_preparation_requires_twelve_approved_closes(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        self._activate_annual_capabilities(empresa)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_annual_preparation_rejects_conditioned_gates(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        for capability_key in ('DDJJPreparacion', 'F22Preparacion'):
            response = self.client.post(
                reverse('sii-capacidad-list'),
                {
                    'empresa': empresa.id,
                    'capacidad_key': capability_key,
                    'certificado_ref': f'cert-{capability_key}',
                    'ambiente': 'certificacion',
                    'estado_gate': 'condicionado',
                    'ultimo_resultado': {},
                },
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_annual_preparation_builds_ddjj_and_f22(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['proceso_renta_anual']['estado'], 'preparado')
        self.assertEqual(response.data['ddjj_preparacion']['estado_preparacion'], 'preparado')
        self.assertEqual(response.data['f22_preparacion']['estado_preparacion'], 'preparado')

    def test_annual_sii_workflow_prepares_and_updates_ddjj_and_f22(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        self.assertEqual(generated.data['proceso_renta_anual']['estado'], 'preparado')
        self.assertEqual(generated.data['ddjj_preparacion']['estado_preparacion'], 'preparado')
        self.assertEqual(generated.data['f22_preparacion']['estado_preparacion'], 'preparado')

        ddjj_status = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'ddjj-2027',
                'observaciones': 'Paquete DDJJ listo.',
            },
            format='json',
        )
        self.assertEqual(ddjj_status.status_code, status.HTTP_200_OK)
        self.assertEqual(ddjj_status.data['estado_preparacion'], 'aprobado_para_presentacion')
        self.assertEqual(ddjj_status.data['paquete_ref'], 'ddjj-2027')

        f22_status = self.client.post(
            reverse('sii-f22-status', args=[generated.data['f22_preparacion']['id']]),
            {
                'estado_preparacion': 'aprobado_para_presentacion',
                'ref_value': 'f22-2027',
                'observaciones': 'Borrador F22 listo.',
            },
            format='json',
        )
        self.assertEqual(f22_status.status_code, status.HTTP_200_OK)
        self.assertEqual(f22_status.data['estado_preparacion'], 'aprobado_para_presentacion')
        self.assertEqual(f22_status.data['borrador_ref'], 'f22-2027')

        process = ProcesoRentaAnual.objects.get(pk=generated.data['proceso_renta_anual']['id'])
        ddjj = DDJJPreparacionAnual.objects.get(pk=generated.data['ddjj_preparacion']['id'])
        f22 = F22PreparacionAnual.objects.get(pk=generated.data['f22_preparacion']['id'])

        self.assertEqual(process.paquete_ddjj_ref, 'ddjj-2027')
        self.assertEqual(process.borrador_f22_ref, 'f22-2027')
        self.assertEqual(ddjj.estado_preparacion, 'aprobado_para_presentacion')
        self.assertEqual(f22.estado_preparacion, 'aprobado_para_presentacion')

    def test_annual_status_rechecks_gate_for_prepared_state(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887', '1879'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='DDJJPreparacion').update(
            estado_gate='condicionado'
        )
        ddjj_status = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )
        self.assertEqual(ddjj_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate', ddjj_status.data['detail'])

        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='DDJJPreparacion').update(
            estado_gate='abierto'
        )
        CapacidadTributariaSII.objects.filter(empresa=empresa, capacidad_key='F22Preparacion').update(
            estado_gate='condicionado'
        )
        f22_status = self.client.post(
            reverse('sii-f22-status', args=[generated.data['f22_preparacion']['id']]),
            {'estado_preparacion': 'preparado'},
            format='json',
        )
        self.assertEqual(f22_status.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate', f22_status.data['detail'])

    def test_annual_status_rejects_final_presentation_boundary(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=['1887'])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)
        generated = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('sii-ddjj-status', args=[generated.data['ddjj_preparacion']['id']]),
            {
                'estado_preparacion': 'presentado',
                'ref_value': 'ddjj-final',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('PresentacionAnualFinal', response.data['detail'])

    def test_generate_annual_preparation_leaves_ddjj_pending_when_no_ddjj_enabled(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa, ddjj_habilitadas=[])
        self._activate_annual_capabilities(empresa)
        self._create_twelve_approved_closes(empresa, fiscal_year=2026)

        response = self.client.post(
            reverse('sii-anual-generate'),
            {'empresa_id': empresa.id, 'anio_tributario': 2027},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['ddjj_preparacion']['estado_preparacion'], 'pendiente_datos')
        self.assertEqual(response.data['f22_preparacion']['estado_preparacion'], 'preparado')


class SiiMigrationSafetyTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = [
        ('patrimonio', '0002_participaciones_mixtas_y_representacion_comunidad'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0003_pagomensual_monto_facturable_clp'),
        ('sii', '0003_procesorentaanual_f22preparacionanual_and_more'),
    ]
    migrate_to = [
        ('patrimonio', '0003_repair_legacy_representacion_modes'),
        ('operacion', '0001_initial'),
        ('contratos', '0001_initial'),
        ('cobranza', '0004_distribucioncobromensual'),
        ('sii', '0004_dte_emitido_distribucion_cobro_mensual'),
    ]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(self.migrate_from).apps

    def migrate(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def test_dte_backfill_links_distribution_even_when_legacy_payment_lacked_facturable_amount(self):
        Socio = self.old_apps.get_model('patrimonio', 'Socio')
        Empresa = self.old_apps.get_model('patrimonio', 'Empresa')
        ParticipacionPatrimonial = self.old_apps.get_model('patrimonio', 'ParticipacionPatrimonial')
        Propiedad = self.old_apps.get_model('patrimonio', 'Propiedad')
        CuentaRecaudadora = self.old_apps.get_model('operacion', 'CuentaRecaudadora')
        MandatoOperacion = self.old_apps.get_model('operacion', 'MandatoOperacion')
        Arrendatario = self.old_apps.get_model('contratos', 'Arrendatario')
        Contrato = self.old_apps.get_model('contratos', 'Contrato')
        ContratoPropiedad = self.old_apps.get_model('contratos', 'ContratoPropiedad')
        PeriodoContractual = self.old_apps.get_model('contratos', 'PeriodoContractual')
        PagoMensual = self.old_apps.get_model('cobranza', 'PagoMensual')
        CapacidadTributariaSII = self.old_apps.get_model('sii', 'CapacidadTributariaSII')
        DTEEmitidoOld = self.old_apps.get_model('sii', 'DTEEmitido')

        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        empresa = Empresa.objects.create(razon_social='Empresa Legacy SII', rut='76999999-9', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=socio_1.id,
            empresa_owner_id=empresa.id,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio_id=socio_2.id,
            empresa_owner_id=empresa.id,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            direccion='Av Legacy SII',
            comuna='Santiago',
            region='RM',
            tipo_inmueble='local',
            codigo_propiedad='SII-HIST-001',
            estado='activa',
            empresa_owner_id=empresa.id,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner_id=empresa.id,
            institucion='Banco Uno',
            numero_cuenta='ACC-SII-HIST',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo='activa',
        )
        mandato = MandatoOperacion.objects.create(
            propiedad_id=propiedad.id,
            propietario_empresa_owner_id=empresa.id,
            administrador_empresa_owner_id=empresa.id,
            cuenta_recaudadora_id=cuenta.id,
            entidad_facturadora_id=empresa.id,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado='activa',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Legacy',
            rut='56565656-5',
            email='legacy@example.com',
            telefono='777',
            domicilio_notificaciones='Legacy',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='SII-HIST',
            mandato_operacion_id=mandato.id,
            arrendatario_id=arrendatario.id,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            dia_pago_mensual=5,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato_id=contrato.id,
            propiedad_id=propiedad.id,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        periodo = PeriodoContractual.objects.create(
            contrato_id=contrato.id,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='base',
            origen_periodo='manual',
        )
        pago = PagoMensual.objects.create(
            contrato_id=contrato.id,
            periodo_contractual_id=periodo.id,
            mes=1,
            anio=2026,
            monto_facturable_clp='0.00',
            monto_calculado_clp='100111.00',
            monto_pagado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pagado',
            codigo_conciliacion_efectivo='111',
        )
        capacidad = CapacidadTributariaSII.objects.create(
            empresa_id=empresa.id,
            capacidad_key='DTEEmision',
            certificado_ref='cert-legacy',
            ambiente='certificacion',
            estado_gate='abierto',
        )
        DTEEmitidoOld.objects.create(
            empresa_id=empresa.id,
            capacidad_tributaria_id=capacidad.id,
            contrato_id=contrato.id,
            pago_mensual_id=pago.id,
            arrendatario_id=arrendatario.id,
            tipo_dte='34',
            monto_neto_clp='100000.00',
            fecha_emision='2026-01-06',
            estado_dte='borrador',
        )

        self.migrate()

        DTEEmitidoNew = self.apps.get_model('sii', 'DTEEmitido')
        dte = DTEEmitidoNew.objects.get(contrato__codigo_contrato='SII-HIST')

        self.assertIsNotNone(dte.distribucion_cobro_mensual_id)
        self.assertTrue(dte.distribucion_cobro_mensual.requiere_dte)
        self.assertEqual(dte.distribucion_cobro_mensual.beneficiario_empresa_owner_id, dte.empresa_id)
