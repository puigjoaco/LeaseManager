from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoRegistro, RegimenTributarioEmpresa
from contratos.models import Arrendatario, Contrato, EstadoContrato
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
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

from .models import (
    CanalOperacion,
    CuentaRecaudadora,
    EstadoAsignacionCanal,
    EstadoCuentaRecaudadora,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
    MonedaOperativa,
)


class OperacionModelTests(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(nombre='Owner Uno', rut='11111111-1', activo=True)

    def test_active_account_requires_active_owner(self):
        self.socio.activo = False
        self.socio.save()

        cuenta = CuentaRecaudadora(
            socio_owner=self.socio,
            institucion='Banco Uno',
            numero_cuenta='123456',
            tipo_cuenta='corriente',
            titular_nombre='Owner Uno',
            titular_rut='11111111-1',
            moneda_operativa=MonedaOperativa.CLP,
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )

        with self.assertRaisesMessage(Exception, 'owner activo'):
            cuenta.full_clean()


class OperacionAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='operator', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre, rut):
        socio_1 = self._create_socio(f'{nombre} Socio 1', f'{rut[:-1]}1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', f'{rut[:-1]}2')
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

    def _create_active_fiscal_config(self, empresa):
        regimen, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='pro_pyme_general',
            defaults={
                'descripcion': 'Pro Pyme General',
                'estado': EstadoRegistro.ACTIVE,
            },
        )
        config, _ = ConfiguracionFiscalEmpresa.objects.get_or_create(
            empresa=empresa,
            defaults={
                'regimen_tributario': regimen,
                'afecta_iva_arriendo': False,
                'tasa_iva': '0.00',
                'tasa_ppm_vigente': '1.00',
                'aplica_ppm': True,
                'ddjj_habilitadas': [],
                'inicio_ejercicio': '2026-01-01',
                'moneda_funcional': 'CLP',
                'estado': EstadoRegistro.ACTIVE,
            },
        )
        return config

    def _create_active_comunidad(self, nombre):
        socio_1 = self._create_socio(f'{nombre} Socio 1', '55555555-5')
        socio_2 = self._create_socio(f'{nombre} Socio 2', '66666666-6')
        comunidad = ComunidadPatrimonial.objects.create(
            nombre=nombre,
            estado='activa',
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_1,
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        return comunidad

    def _create_property_for_owner(self, *, empresa=None, comunidad=None, socio=None, codigo='P-001'):
        return Propiedad.objects.create(
            direccion='Av Apoquindo 1000',
            comuna='Las Condes',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=codigo,
            estado='activa',
            empresa_owner=empresa,
            comunidad_owner=comunidad,
            socio_owner=socio,
        )

    def _create_active_account(self, *, empresa=None, comunidad=None, socio=None, numero='123456'):
        titular_nombre = empresa.razon_social if empresa else comunidad.nombre if comunidad else socio.nombre
        titular_rut = empresa.rut if empresa else comunidad.representante_socio.rut if comunidad else socio.rut
        return CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            comunidad_owner=comunidad,
            socio_owner=socio,
            institucion='Banco Uno',
            numero_cuenta=numero,
            tipo_cuenta='corriente',
            titular_nombre=titular_nombre,
            titular_rut=titular_rut,
            moneda_operativa=MonedaOperativa.CLP,
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )

    def _create_active_identity(self, *, empresa=None, socio=None, canal=CanalOperacion.EMAIL, direccion='ops@example.com'):
        safe_ref = f"identity-ref-{direccion.replace('@', '-').replace('.', '-')}"
        return IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            socio_owner=socio,
            canal=canal,
            remitente_visible=empresa.razon_social if empresa else socio.nombre,
            direccion_o_numero=direccion,
            credencial_ref=safe_ref,
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

    def _create_active_mandato(self, *, propiedad, propietario_tipo, propietario_id, admin_tipo, admin_id, cuenta_id, facturadora_id=None):
        cuenta = CuentaRecaudadora.objects.get(pk=cuenta_id)
        payload = {
            'propiedad_id': propiedad.id,
            'propietario_tipo': propietario_tipo,
            'propietario_id': propietario_id,
            'administrador_operativo_tipo': admin_tipo,
            'administrador_operativo_id': admin_id,
            'recaudador_tipo': cuenta.owner_tipo,
            'recaudador_id': cuenta.owner_id,
            'cuenta_recaudadora_id': cuenta_id,
            'tipo_relacion_operativa': 'mandato_externo',
            'autoriza_recaudacion': True,
            'autoriza_facturacion': bool(facturadora_id),
            'autoriza_comunicacion': True,
            'autoridad_operativa_nombre': 'Representante Operativo',
            'autoridad_operativa_rut': '12.345.678-5',
            'autoridad_operativa_evidencia_ref': 'mandate-authority-act-001',
            'vigencia_desde': '2026-01-01',
            'estado': EstadoMandatoOperacion.ACTIVE,
        }
        if facturadora_id:
            payload['entidad_facturadora_id'] = facturadora_id
        return self.client.post(reverse('operacion-mandato-list'), payload, format='json')

    def _create_active_contract_for_mandato(self, mandato_id, codigo='CON-OP-001'):
        mandato = MandatoOperacion.objects.get(pk=mandato_id)
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut='30303030-3',
            email='arrendatario@example.com',
            telefono='999',
            domicilio_notificaciones='Domicilio 123',
            estado_contacto='activo',
        )
        return Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
        )

    def test_auth_is_required_for_operation_list_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('operacion-cuenta-list'),
            reverse('operacion-identidad-list'),
            reverse('operacion-mandato-list'),
            reverse('operacion-asignacion-list'),
        ]

        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_active_account_and_reject_duplicate_account(self):
        empresa = self._create_active_empresa('AdminCo', '88888888-8')
        payload = {
            'owner_tipo': 'empresa',
            'owner_id': empresa.id,
            'institucion': 'Banco Uno',
            'numero_cuenta': '999000',
            'tipo_cuenta': 'corriente',
            'titular_nombre': empresa.razon_social,
            'titular_rut': empresa.rut,
            'moneda_operativa': MonedaOperativa.CLP,
            'estado_operativo': EstadoCuentaRecaudadora.ACTIVE,
        }

        response = self.client.post(reverse('operacion-cuenta-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner_tipo'], 'empresa')

        duplicate_response = self.client.post(reverse('operacion-cuenta-list'), payload, format='json')
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_active_account_for_comunidad_owner(self):
        comunidad = self._create_active_comunidad('Comunidad Operativa')
        payload = {
            'owner_tipo': 'comunidad',
            'owner_id': comunidad.id,
            'institucion': 'Banco Uno',
            'numero_cuenta': '999001',
            'tipo_cuenta': 'corriente',
            'titular_nombre': comunidad.nombre,
            'titular_rut': comunidad.representante_socio.rut,
            'moneda_operativa': MonedaOperativa.CLP,
            'estado_operativo': EstadoCuentaRecaudadora.ACTIVE,
        }

        response = self.client.post(reverse('operacion-cuenta-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['owner_tipo'], 'comunidad')
        self.assertEqual(response.data['owner_id'], comunidad.id)

    def test_create_identity_validates_email_when_channel_is_email(self):
        socio = self._create_socio('Operador Uno', '33333333-3')
        invalid_response = self.client.post(
            reverse('operacion-identidad-list'),
            {
                'owner_tipo': 'socio',
                'owner_id': socio.id,
                'canal': CanalOperacion.EMAIL,
                'remitente_visible': socio.nombre,
                'direccion_o_numero': 'correo-invalido',
                'credencial_ref': 'cred-1',
                'estado': EstadoIdentidadEnvio.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

        valid_response = self.client.post(
            reverse('operacion-identidad-list'),
            {
                'owner_tipo': 'socio',
                'owner_id': socio.id,
                'canal': CanalOperacion.EMAIL,
                'remitente_visible': socio.nombre,
                'direccion_o_numero': 'operador@example.com',
                'credencial_ref': 'cred-2',
                'estado': EstadoIdentidadEnvio.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(valid_response.status_code, status.HTTP_201_CREATED)

    def test_active_identity_rejects_sensitive_credential_ref_before_persisting(self):
        socio = self._create_socio('Operador Sensible', '34343434-2')

        response = self.client.post(
            reverse('operacion-identidad-list'),
            {
                'owner_tipo': 'socio',
                'owner_id': socio.id,
                'canal': CanalOperacion.EMAIL,
                'remitente_visible': socio.nombre,
                'direccion_o_numero': 'sensible@example.com',
                'credencial_ref': 'https://mail.example.test/token/secret',
                'estado': EstadoIdentidadEnvio.ACTIVE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('credencial_ref', response.data)
        self.assertFalse(IdentidadDeEnvio.objects.filter(direccion_o_numero='sensible@example.com').exists())

    def test_identity_api_redacts_inherited_sensitive_credential_ref(self):
        socio = self._create_socio('Operador Heredado', '35353535-0')
        identidad = IdentidadDeEnvio.objects.create(
            socio_owner=socio,
            canal=CanalOperacion.EMAIL,
            remitente_visible=socio.nombre,
            direccion_o_numero='heredado@example.com',
            credencial_ref='https://mail.example.test/token/secret',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

        list_response = self.client.get(reverse('operacion-identidad-list'))
        detail_response = self.client.get(reverse('operacion-identidad-detail', args=[identidad.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['credencial_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['credencial_ref'], REDACTED_SENSITIVE_REFERENCE)

    def test_active_mandato_accepts_distinct_owner_admin_and_facturadora_when_authorized(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        facturadora = self._create_active_empresa('FacturaCo', '99999999-9')
        self._create_active_fiscal_config(facturadora)
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-001')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-001')

        response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
            facturadora_id=facturadora.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['administrador_operativo_tipo'], 'empresa')
        self.assertEqual(response.data['autoridad_operativa_rut'], '12345678-5')
        self.assertTrue(AuditEvent.objects.filter(event_type='operacion.mandato_operacion.created').exists())

    def test_active_mandato_requires_operational_authority_when_communicating(self):
        propietario = self._create_socio('Propietario Autoridad', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo Autoridad', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-001A')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-001A')

        response = self.client.post(
            reverse('operacion-mandato-list'),
            {
                'propiedad_id': propiedad.id,
                'propietario_tipo': 'socio',
                'propietario_id': propietario.id,
                'administrador_operativo_tipo': 'empresa',
                'administrador_operativo_id': admin_company.id,
                'recaudador_tipo': 'empresa',
                'recaudador_id': admin_company.id,
                'cuenta_recaudadora_id': cuenta.id,
                'tipo_relacion_operativa': 'mandato_externo',
                'autoriza_recaudacion': True,
                'autoriza_facturacion': False,
                'autoriza_comunicacion': True,
                'vigencia_desde': '2026-01-01',
                'estado': EstadoMandatoOperacion.ACTIVE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('autoridad_operativa_nombre', response.data)
        self.assertIn('autoridad_operativa_rut', response.data)
        self.assertIn('autoridad_operativa_evidencia_ref', response.data)

    def test_active_mandato_rejects_sensitive_operational_authority_evidence(self):
        propietario = self._create_socio('Propietario Evidencia', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo Evidencia', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-001S')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-001S')

        response = self.client.post(
            reverse('operacion-mandato-list'),
            {
                'propiedad_id': propiedad.id,
                'propietario_tipo': 'socio',
                'propietario_id': propietario.id,
                'administrador_operativo_tipo': 'empresa',
                'administrador_operativo_id': admin_company.id,
                'recaudador_tipo': 'empresa',
                'recaudador_id': admin_company.id,
                'cuenta_recaudadora_id': cuenta.id,
                'tipo_relacion_operativa': 'mandato_externo',
                'autoriza_recaudacion': True,
                'autoriza_facturacion': False,
                'autoriza_comunicacion': True,
                'autoridad_operativa_nombre': 'Representante Operativo',
                'autoridad_operativa_rut': '12345678-5',
                'autoridad_operativa_evidencia_ref': 'https://drive.example.test/token/secret',
                'vigencia_desde': '2026-01-01',
                'estado': EstadoMandatoOperacion.ACTIVE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('autoridad_operativa_evidencia_ref', response.data)

    def test_active_mandato_rejects_facturadora_without_active_fiscal_config(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        facturadora = self._create_active_empresa('FacturaCo', '99999999-9')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-001B')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-001B')

        response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
            facturadora_id=facturadora.id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('entidad_facturadora', response.data)

    def test_active_mandato_rejects_property_owner_mismatch(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        another_owner = self._create_socio('Propietario Dos', '12121212-4')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-002')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-002')

        response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=another_owner.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_active_mandato_accepts_third_party_recaudador_when_authorized(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        facturadora = self._create_active_empresa('FacturaCo', '99999999-9')
        self._create_active_fiscal_config(facturadora)
        unrelated_owner = self._create_socio('Tercero Uno', '13131313-1')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-003')
        cuenta = self._create_active_account(socio=unrelated_owner, numero='ACC-003')

        response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
            facturadora_id=facturadora.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recaudador_tipo'], 'socio')
        self.assertEqual(response.data['recaudador_id'], unrelated_owner.id)

    def test_account_deactivation_rejects_active_mandate_dependency(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-003C')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-003C')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('operacion-cuenta-detail', args=[cuenta.id]),
            {'estado_operativo': EstadoCuentaRecaudadora.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado_operativo', response.data)
        cuenta.refresh_from_db()
        self.assertEqual(cuenta.estado_operativo, EstadoCuentaRecaudadora.ACTIVE)

    def test_mandato_deactivation_rejects_active_contract_dependency(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-003D')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-003D')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)
        self._create_active_contract_for_mandato(mandato_response.data['id'], codigo='CON-OP-003D')

        response = self.client.patch(
            reverse('operacion-mandato-detail', args=[mandato_response.data['id']]),
            {'estado': EstadoMandatoOperacion.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        mandato = MandatoOperacion.objects.get(pk=mandato_response.data['id'])
        self.assertEqual(mandato.estado, EstadoMandatoOperacion.ACTIVE)

    def test_mandato_validity_shrink_rejects_active_contract_dependency(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-003E')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-003E')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)
        self._create_active_contract_for_mandato(mandato_response.data['id'], codigo='CON-OP-003E')

        starts_late_response = self.client.patch(
            reverse('operacion-mandato-detail', args=[mandato_response.data['id']]),
            {'vigencia_desde': '2026-02-01'},
            format='json',
        )
        ends_early_response = self.client.patch(
            reverse('operacion-mandato-detail', args=[mandato_response.data['id']]),
            {'vigencia_hasta': '2026-11-30'},
            format='json',
        )

        self.assertEqual(starts_late_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vigencia_desde', starts_late_response.data)
        self.assertEqual(ends_early_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('vigencia_hasta', ends_early_response.data)
        mandato = MandatoOperacion.objects.get(pk=mandato_response.data['id'])
        self.assertEqual(str(mandato.vigencia_desde), '2026-01-01')
        self.assertIsNone(mandato.vigencia_hasta)

    def test_mandato_validity_extension_accepts_active_contract_dependency(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-003F')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-003F')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)
        self._create_active_contract_for_mandato(mandato_response.data['id'], codigo='CON-OP-003F')

        response = self.client.patch(
            reverse('operacion-mandato-detail', args=[mandato_response.data['id']]),
            {'vigencia_hasta': '2027-12-31'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vigencia_hasta'], '2027-12-31')

    def test_active_mandato_accepts_comunidad_recaudadora(self):
        comunidad = self._create_active_comunidad('Comunidad Recaudadora')
        admin = comunidad.representante_socio
        propiedad = self._create_property_for_owner(comunidad=comunidad, codigo='COM-001')
        cuenta = self._create_active_account(comunidad=comunidad, numero='ACC-COM-001')

        response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='comunidad',
            propietario_id=comunidad.id,
            admin_tipo='socio',
            admin_id=admin.id,
            cuenta_id=cuenta.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recaudador_tipo'], 'comunidad')
        self.assertEqual(response.data['recaudador_id'], comunidad.id)

    def test_active_mandato_rejects_recaudador_that_does_not_match_account_owner(self):
        propietario = self._create_socio('Propietario Uno', '17171717-5')
        admin_company = self._create_active_empresa('AdminCo', '18181818-2')
        unrelated_owner = self._create_socio('Tercero Uno', '19191919-0')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-003B')
        cuenta = self._create_active_account(socio=unrelated_owner, numero='ACC-003B')

        response = self.client.post(
            reverse('operacion-mandato-list'),
            {
                'propiedad_id': propiedad.id,
                'propietario_tipo': 'socio',
                'propietario_id': propietario.id,
                'administrador_operativo_tipo': 'empresa',
                'administrador_operativo_id': admin_company.id,
                'recaudador_tipo': 'empresa',
                'recaudador_id': admin_company.id,
                'cuenta_recaudadora_id': cuenta.id,
                'tipo_relacion_operativa': 'mandato_externo',
                'autoriza_recaudacion': True,
                'autoriza_facturacion': False,
                'autoriza_comunicacion': True,
                'vigencia_desde': '2026-01-01',
                'estado': EstadoMandatoOperacion.ACTIVE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_active_mandato_requires_authorizations_when_actors_differ(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-004')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-004')

        response = self.client.post(
            reverse('operacion-mandato-list'),
            {
                'propiedad_id': propiedad.id,
                'propietario_tipo': 'socio',
                'propietario_id': propietario.id,
                'administrador_operativo_tipo': 'empresa',
                'administrador_operativo_id': admin_company.id,
                'recaudador_tipo': 'empresa',
                'recaudador_id': admin_company.id,
                'cuenta_recaudadora_id': cuenta.id,
                'tipo_relacion_operativa': 'mandato_externo',
                'autoriza_recaudacion': False,
                'autoriza_facturacion': False,
                'autoriza_comunicacion': False,
                'vigencia_desde': '2026-01-01',
                'estado': EstadoMandatoOperacion.ACTIVE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_active_assignment_accepts_identity_of_admin_or_facturadora(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        facturadora = self._create_active_empresa('FacturaCo', '99999999-9')
        self._create_active_fiscal_config(facturadora)
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-005')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-005')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
            facturadora_id=facturadora.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)

        identidad = self._create_active_identity(empresa=facturadora, direccion='factura@example.com')

        response = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': identidad.id,
                'prioridad': 1,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_active_assignment_rejects_channel_mismatch_or_unauthorized_identity(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-006')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-006')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)

        whatsapp_identity = self._create_active_identity(
            empresa=admin_company,
            canal=CanalOperacion.WHATSAPP,
            direccion='+56912345678',
        )
        channel_mismatch_response = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': whatsapp_identity.id,
                'prioridad': 1,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(channel_mismatch_response.status_code, status.HTTP_400_BAD_REQUEST)

        unrelated_company = self._create_active_empresa('OtraCo', '14141414-7')
        unrelated_identity = self._create_active_identity(
            empresa=unrelated_company,
            direccion='otra@example.com',
        )
        unauthorized_response = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': unrelated_identity.id,
                'prioridad': 1,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(unauthorized_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_identity_deactivation_rejects_active_assignment_dependency(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-006B')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-006B')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)

        identidad = self._create_active_identity(empresa=admin_company, direccion='admin-state@example.com')
        assignment_response = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': identidad.id,
                'prioridad': 1,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(assignment_response.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('operacion-identidad-detail', args=[identidad.id]),
            {'estado': EstadoIdentidadEnvio.SUSPENDED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        identidad.refresh_from_db()
        self.assertEqual(identidad.estado, EstadoIdentidadEnvio.ACTIVE)

    def test_assignment_deactivation_rejects_last_active_channel_for_active_contract(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-006C')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-006C')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)

        identidad = self._create_active_identity(empresa=admin_company, direccion='last-channel@example.com')
        assignment_response = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': identidad.id,
                'prioridad': 1,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(assignment_response.status_code, status.HTTP_201_CREATED)
        self._create_active_contract_for_mandato(mandato_response.data['id'], codigo='CON-OP-006C')

        response = self.client.patch(
            reverse('operacion-asignacion-detail', args=[assignment_response.data['id']]),
            {'estado': EstadoAsignacionCanal.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)

    def test_assignment_deactivation_accepts_when_another_active_channel_remains(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-006D')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-006D')
        mandato_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(mandato_response.status_code, status.HTTP_201_CREATED)

        first_identity = self._create_active_identity(empresa=admin_company, direccion='first-channel@example.com')
        second_identity = self._create_active_identity(empresa=admin_company, direccion='second-channel@example.com')
        first_assignment = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': first_identity.id,
                'prioridad': 1,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(first_assignment.status_code, status.HTTP_201_CREATED)
        second_assignment = self.client.post(
            reverse('operacion-asignacion-list'),
            {
                'mandato_operacion_id': mandato_response.data['id'],
                'canal': CanalOperacion.EMAIL,
                'identidad_envio_id': second_identity.id,
                'prioridad': 2,
                'estado': EstadoAsignacionCanal.ACTIVE,
            },
            format='json',
        )
        self.assertEqual(second_assignment.status_code, status.HTTP_201_CREATED)
        self._create_active_contract_for_mandato(mandato_response.data['id'], codigo='CON-OP-006D')

        response = self.client.patch(
            reverse('operacion-asignacion-detail', args=[first_assignment.data['id']]),
            {'estado': EstadoAsignacionCanal.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['estado'], EstadoAsignacionCanal.INACTIVE)

    def test_mandato_update_emits_update_and_state_change_audit_events(self):
        propietario = self._create_socio('Propietario Uno', '77777777-7')
        admin_company = self._create_active_empresa('AdminCo', '88888888-8')
        propiedad = self._create_property_for_owner(socio=propietario, codigo='SOC-007')
        cuenta = self._create_active_account(empresa=admin_company, numero='ACC-007')
        create_response = self._create_active_mandato(
            propiedad=propiedad,
            propietario_tipo='socio',
            propietario_id=propietario.id,
            admin_tipo='empresa',
            admin_id=admin_company.id,
            cuenta_id=cuenta.id,
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        patch_response = self.client.patch(
            reverse('operacion-mandato-detail', args=[create_response.data['id']]),
            {'estado': EstadoMandatoOperacion.INACTIVE},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditEvent.objects.filter(event_type='operacion.mandato_operacion.updated').exists())
        self.assertTrue(AuditEvent.objects.filter(event_type='operacion.mandato_operacion.state_changed').exists())
