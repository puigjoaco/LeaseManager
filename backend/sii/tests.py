from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cobranza.models import PagoMensual
from cobranza.services import sync_payment_distribution
from contabilidad.models import CierreMensualContable, ConfiguracionFiscalEmpresa, ObligacionTributariaMensual, RegimenTributarioEmpresa
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual

from .models import DDJJPreparacionAnual, DTEEmitido, EstadoGateSII, F22PreparacionAnual, ProcesoRentaAnual


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

    def _activate_capability(self, empresa, estado_gate='abierto'):
        return self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'DTEEmision',
                'certificado_ref': 'certificado-sii-ref',
                'ambiente': 'certificacion',
                'estado_gate': estado_gate,
                'ultimo_resultado': {},
            },
            format='json',
        )

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
                    'certificado_ref': f'cert-{capability_key}',
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

        self._activate_capability(empresa)
        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_rejects_conditioned_gate(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_capability(empresa, estado_gate='condicionado')
        self._activate_fiscal_config(empresa)

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_uses_facturable_amount_not_coded_amount(self):
        empresa, pago = self._setup_paid_payment(monto_facturable='100000.00', monto_cobrado='100111.00')
        self._activate_capability(empresa)
        self._activate_fiscal_config(empresa)

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
        self._activate_capability(empresa)
        self._activate_fiscal_config(empresa)

        first = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')
        second = self.client.post(reverse('sii-dte-generate'), {'pago_mensual_id': pago.id}, format='json')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(DTEEmitido.objects.filter(pago_mensual=pago).count(), 1)

    def test_generate_dte_draft_rejects_missing_facturadora(self):
        empresa, pago = self._setup_paid_payment(with_facturadora=False)
        self._activate_capability(empresa)
        self._activate_fiscal_config(empresa)

        response = self.client.post(
            reverse('sii-dte-generate'),
            {'pago_mensual_id': pago.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_generate_dte_draft_only_allows_factura_exenta_from_paid_payment_path(self):
        empresa, pago = self._setup_paid_payment()
        self._activate_capability(empresa)
        self._activate_fiscal_config(empresa)

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
        self._activate_capability(empresa, estado_gate='abierto')
        self._activate_fiscal_config(empresa)
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
                'certificado_ref': 'certificado-f29-ref',
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
                'certificado_ref': 'certificado-f29-ref',
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
                'certificado_ref': 'certificado-f29-ref',
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
                'certificado_ref': 'certificado-f29-ref',
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

    def test_update_f29_status_manually(self):
        empresa, _ = self._setup_paid_payment()
        self._activate_fiscal_config(empresa)
        self.client.post(
            reverse('sii-capacidad-list'),
            {
                'empresa': empresa.id,
                'capacidad_key': 'F29Preparacion',
                'certificado_ref': 'certificado-f29-ref',
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
                'certificado_ref': 'certificado-f29-ref',
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
