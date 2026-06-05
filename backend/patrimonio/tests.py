from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from operacion.models import (
    CanalOperacion,
    CuentaRecaudadora,
    EstadoCuentaRecaudadora,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
    ModoOperacionCuentaRecaudadora,
)

from .admin import (
    ComunidadPatrimonialAdmin,
    EmpresaAdmin,
    ParticipacionPatrimonialAdmin,
    PropiedadAdmin,
    RepresentacionComunidadAdmin,
    ServicioPropiedadAdmin,
    SocioAdmin,
)
from .models import (
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
from .validators import normalize_rut, validate_rut


class RutValidatorTests(TestCase):
    def test_normalize_rut_returns_canonical_value(self):
        self.assertEqual(normalize_rut('12.345.678-5'), '12345678-5')

    def test_validate_rut_accepts_valid_input(self):
        self.assertEqual(validate_rut('12.345.678-5'), '12345678-5')

    def test_validate_rut_rejects_invalid_input(self):
        with self.assertRaises(ValidationError):
            validate_rut('12.345.678-9')


class PropiedadModelConstraintTests(TestCase):
    def test_propiedad_rejects_multiple_owners(self):
        socio = Socio.objects.create(nombre='Socio Uno', rut='11111111-1')
        empresa = Empresa.objects.create(razon_social='Empresa Uno', rut='22222222-2')
        propiedad = Propiedad(
            direccion='Av Siempre Viva 123',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='P001',
            empresa_owner=empresa,
            socio_owner=socio,
        )

        with self.assertRaises(ValidationError):
            propiedad.full_clean()

    def test_active_property_rejects_duplicate_normalized_rol_avaluo(self):
        socio = Socio.objects.create(nombre='Socio Rol Uno', rut='11111111-1')
        other_socio = Socio.objects.create(nombre='Socio Rol Dos', rut='22222222-2')
        Propiedad.objects.create(
            rol_avaluo='123-45',
            direccion='Av Rol 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='ROL-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=socio,
        )
        duplicate = Propiedad(
            rol_avaluo='123 45',
            direccion='Av Rol 200',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='ROL-002',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=other_socio,
        )

        with self.assertRaises(ValidationError) as error:
            duplicate.full_clean()

        self.assertIn('rol_avaluo', error.exception.message_dict)

    def test_active_property_rejects_duplicate_operational_identity(self):
        socio = Socio.objects.create(nombre='Socio Identidad Uno', rut='11111111-1')
        other_socio = Socio.objects.create(nombre='Socio Identidad Dos', rut='22222222-2')
        Propiedad.objects.create(
            rol_avaluo='ROL-ID-1',
            direccion='Av Identidad 100',
            comuna='Las Condes',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='ID-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=socio,
        )
        duplicate = Propiedad(
            rol_avaluo='ROL-ID-2',
            direccion=' av identidad  100 ',
            comuna='LAS CONDES',
            region='rm',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='ID-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=other_socio,
        )

        with self.assertRaises(ValidationError) as error:
            duplicate.full_clean()

        self.assertIn('codigo_propiedad', error.exception.message_dict)

    def test_common_expense_service_requires_structured_administration_data(self):
        socio = Socio.objects.create(nombre='Socio Servicio', rut='11111111-1')
        propiedad = Propiedad.objects.create(
            direccion='Av Comunidad 123',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='SERV-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=socio,
        )
        service = ServicioPropiedad(
            propiedad=propiedad,
            tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
            proveedor_nombre='Administracion Edificio',
            numero_cliente='',
            administrador_nombre='',
        )

        with self.assertRaises(ValidationError) as error:
            service.full_clean()

        self.assertIn('numero_cliente', error.exception.message_dict)
        self.assertIn('administrador_nombre', error.exception.message_dict)


class PatrimonioAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='tester', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_socio_property(self):
        socio = self._create_socio('Socio Propiedad Servicio', '18181818-1')
        return Propiedad.objects.create(
            direccion='Av Servicio 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='SRV-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=socio,
        )

    def _create_active_account(self, *, empresa=None, comunidad=None, socio=None, numero='ACC-PAT-001'):
        titular_nombre = empresa.razon_social if empresa else comunidad.nombre if comunidad else socio.nombre
        titular_rut = empresa.rut if empresa else '12345678-5' if comunidad else socio.rut
        return CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            comunidad_owner=comunidad,
            socio_owner=socio,
            institucion='Banco Uno',
            numero_cuenta=numero,
            tipo_cuenta='corriente',
            titular_nombre=titular_nombre,
            titular_rut=titular_rut,
            moneda_operativa='CLP',
            uso_operativo='recaudacion_arriendos',
            modo_operativo=ModoOperacionCuentaRecaudadora.MANUAL_CONTROLLED,
            evidencia_operativa_ref=f'account-operational-evidence-{numero}',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )

    def _empresa_payload(self, estado=EstadoPatrimonial.ACTIVE, participaciones=None):
        if participaciones is None:
            socio_1 = self._create_socio('Socio Uno', '11111111-1')
            socio_2 = self._create_socio('Socio Dos', '22222222-2')
            participaciones = [
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '60.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '40.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ]

        return {
            'razon_social': 'Empresa Canonica',
            'rut': '88.888.888-8',
            'domicilio': 'Providencia 100',
            'giro': 'Renta inmobiliaria',
            'codigo_actividad_sii': '681000',
            'estado': estado,
            'participaciones': participaciones,
        }

    def _comunidad_payload(
        self,
        *,
        representante_modo,
        representante_socio_id,
        participaciones,
        estado=EstadoPatrimonial.ACTIVE,
        representante_evidencia_ref=None,
    ):
        payload = {
            'nombre': 'Comunidad Patrimonial Uno',
            'representante_modo': representante_modo,
            'representante_socio_id': representante_socio_id,
            'estado': estado,
            'participaciones': participaciones,
        }
        if representante_evidencia_ref is not None:
            payload['representante_evidencia_ref'] = representante_evidencia_ref
        return payload

    def test_auth_is_required_for_all_list_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('patrimonio-socio-list'),
            reverse('patrimonio-empresa-list'),
            reverse('patrimonio-comunidad-list'),
            reverse('patrimonio-propiedad-list'),
            reverse('patrimonio-servicio-propiedad-list'),
            reverse('patrimonio-participacion-list'),
        ]

        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_snapshot_endpoint_returns_payload(self):
        response = self.client.get(reverse('patrimonio-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('socios', response.data)
        self.assertIn('empresas', response.data)
        self.assertIn('comunidades', response.data)
        self.assertIn('propiedades', response.data)

    def test_create_property_service_requires_structured_number(self):
        propiedad = self._create_socio_property()

        response = self.client.post(
            reverse('patrimonio-servicio-propiedad-list'),
            {
                'propiedad': propiedad.id,
                'tipo_servicio': TipoServicioPropiedad.COMMON_EXPENSES,
                'proveedor_nombre': 'Administracion Edificio',
                'numero_cliente': '',
                'administrador_nombre': 'Administracion Edificio',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('numero_cliente', response.data)

    def test_create_property_service_structured_succeeds_and_audits(self):
        propiedad = self._create_socio_property()

        response = self.client.post(
            reverse('patrimonio-servicio-propiedad-list'),
            {
                'propiedad': propiedad.id,
                'tipo_servicio': TipoServicioPropiedad.COMMON_EXPENSES,
                'proveedor_nombre': 'Administracion Edificio',
                'numero_cliente': 'GC-100',
                'administrador_nombre': 'Administracion Edificio',
                'evidencia_ref': 'gasto-comun-propiedad-001',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['numero_cliente'], 'GC-100')
        self.assertTrue(AuditEvent.objects.filter(event_type='patrimonio.servicio_propiedad.created').exists())

    def test_snapshot_redacts_sensitive_property_service_evidence(self):
        propiedad = self._create_socio_property()
        ServicioPropiedad.objects.create(
            propiedad=propiedad,
            tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
            proveedor_nombre='Administracion Edificio',
            numero_cliente='GC-100',
            administrador_nombre='Administracion Edificio',
            evidencia_ref='postgres://user:secret@example.test/db',
            activo=True,
        )

        response = self.client.get(reverse('patrimonio-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        services = response.data['propiedades'][0]['servicios']
        self.assertEqual(services[0]['evidencia_ref'], '<redacted-sensitive-reference>')

    def test_snapshot_redacts_sensitive_designated_representation_evidence(self):
        socio_participante = self._create_socio('Socio Comunidad Snapshot', '11111111-1')
        socio_designado = self._create_socio('Representante Snapshot', '22222222-2')
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Snapshot', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_participante,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde='2026-01-01',
            activo=True,
            evidencia_ref='https://example.test/acta?token=secret',
        )

        response = self.client.get(reverse('patrimonio-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad_snapshot = next(item for item in response.data['comunidades'] if item['id'] == comunidad.id)
        self.assertEqual(
            comunidad_snapshot['representacion_vigente']['evidencia_ref'],
            '<redacted-sensitive-reference>',
        )

    def test_community_api_redacts_sensitive_representation_observations(self):
        socio_participante = self._create_socio('Socio Comunidad Observacion', '11111111-1')
        socio_designado = self._create_socio('Representante Observacion', '22222222-2')
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Observacion', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_participante,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde='2026-01-01',
            activo=True,
            evidencia_ref='community-designated-representative-act-obs',
            observaciones='Acta en https://docs.example.test/acta?token=secret',
        )

        list_response = self.client.get(reverse('patrimonio-comunidad-list'))
        detail_response = self.client.get(reverse('patrimonio-comunidad-detail', args=[comunidad.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        comunidad_list = next(item for item in list_response.data if item['id'] == comunidad.id)
        for comunidad_data in (comunidad_list, detail_response.data):
            self.assertEqual(
                comunidad_data['representacion_vigente']['observaciones'],
                REDACTED_SENSITIVE_REFERENCE,
            )

        rendered = str(list_response.data) + str(detail_response.data)
        self.assertNotIn('docs.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_representation_model_rejects_sensitive_observations(self):
        socio_participante = self._create_socio('Socio Comunidad Modelo', '11111111-1')
        socio_designado = self._create_socio('Representante Modelo', '22222222-2')
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Modelo', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_participante,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        representation = RepresentacionComunidad(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde='2026-01-01',
            activo=True,
            evidencia_ref='community-designated-representative-act-model',
            observaciones='Contacto juan@example.test',
        )

        with self.assertRaises(ValidationError) as error:
            representation.full_clean()

        self.assertIn('observaciones', error.exception.message_dict)

    def test_representation_admin_redacts_sensitive_designated_evidence(self):
        socio_participante = self._create_socio('Socio Comunidad Admin', '11111111-1')
        socio_designado = self._create_socio('Representante Admin', '22222222-2')
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Admin', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_participante,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        representacion = RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde='2026-01-01',
            activo=True,
            evidencia_ref='https://example.test/acta?token=secret',
        )

        model_admin = RepresentacionComunidadAdmin(RepresentacionComunidad, AdminSite())

        self.assertNotIn('evidencia_ref', model_admin.list_display)
        self.assertNotIn('evidencia_ref', model_admin.search_fields)
        self.assertNotIn('evidencia_ref', model_admin.fields)
        self.assertEqual(model_admin.evidencia_ref_redacted(representacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, representacion))
        self.assertFalse(model_admin.has_delete_permission(None, representacion))

    def test_property_service_admin_redacts_sensitive_evidence(self):
        propiedad = self._create_socio_property()
        service = ServicioPropiedad.objects.create(
            propiedad=propiedad,
            tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
            proveedor_nombre='Administracion Edificio',
            numero_cliente='GC-100',
            administrador_nombre='Administracion Edificio',
            evidencia_ref='postgres://user:secret@example.test/db',
            activo=True,
        )

        model_admin = ServicioPropiedadAdmin(ServicioPropiedad, AdminSite())

        self.assertNotIn('evidencia_ref', model_admin.list_display)
        self.assertNotIn('evidencia_ref', model_admin.search_fields)
        self.assertNotIn('evidencia_ref', model_admin.fields)
        self.assertIn('evidencia_ref_redacted', model_admin.readonly_fields)
        self.assertEqual(model_admin.evidencia_ref_redacted(service), REDACTED_SENSITIVE_REFERENCE)
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, service))
        self.assertFalse(model_admin.has_delete_permission(None, service))

    def test_structural_patrimony_admins_block_manual_mutations(self):
        socio = self._create_socio('Socio Admin Delete', '11111111-1')
        empresa = Empresa.objects.create(
            razon_social='Empresa Admin Delete',
            rut='22222222-2',
            domicilio='Providencia 100',
            giro='Renta inmobiliaria',
            codigo_actividad_sii='681000',
            estado=EstadoPatrimonial.ACTIVE,
        )
        comunidad = ComunidadPatrimonial.objects.create(
            nombre='Comunidad Admin Delete',
            estado=EstadoPatrimonial.ACTIVE,
        )
        participacion = ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=empresa,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            direccion='Av Patrimonio 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.APARTMENT,
            codigo_propiedad='ADM-DEL-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=socio,
        )
        site = AdminSite()
        admins = [
            (SocioAdmin(Socio, site), socio),
            (EmpresaAdmin(Empresa, site), empresa),
            (ComunidadPatrimonialAdmin(ComunidadPatrimonial, site), comunidad),
            (ParticipacionPatrimonialAdmin(ParticipacionPatrimonial, site), participacion),
            (PropiedadAdmin(Propiedad, site), propiedad),
        ]

        for model_admin, obj in admins:
            self.assertFalse(model_admin.has_add_permission(None))
            self.assertFalse(model_admin.has_change_permission(None, obj))
            self.assertFalse(model_admin.has_delete_permission(None, obj))

    def test_create_socio_normalizes_rut_and_rejects_duplicate(self):
        payload = {
            'nombre': 'Socio API',
            'rut': '12.345.678-5',
            'email': 'socio@example.com',
            'telefono': '999',
            'domicilio': 'Las Condes 123',
            'activo': True,
        }
        response = self.client.post(reverse('patrimonio-socio-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rut'], '12345678-5')

        duplicate_payload = {**payload, 'email': 'otro@example.com'}
        duplicate_response = self.client.post(reverse('patrimonio-socio-list'), duplicate_payload, format='json')
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empresa_active_with_100_percent_participations_is_created(self):
        response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['participaciones_detail']), 2)
        self.assertTrue(AuditEvent.objects.filter(event_type='patrimonio.empresa.created').exists())

    def test_empresa_create_rolls_back_when_audit_creation_fails(self):
        with patch('patrimonio.views.create_audit_event', side_effect=RuntimeError('patrimony audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'patrimony audit unavailable'):
                self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')

        self.assertFalse(Empresa.objects.filter(razon_social='Empresa Canonica').exists())
        self.assertFalse(
            ParticipacionPatrimonial.objects.filter(empresa_owner__razon_social='Empresa Canonica').exists()
        )

    def test_empresa_update_rejects_direct_participation_rewrite(self):
        create_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        empresa = Empresa.objects.get(pk=create_response.data['id'])
        original_participation_ids = set(empresa.participaciones.values_list('id', flat=True))
        replacement = self._create_socio('Socio Rewrite Empresa', '33333333-3')

        response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[empresa.id]),
            {
                'participaciones': [
                    {
                        'participante_tipo': 'socio',
                        'participante_id': replacement.id,
                        'porcentaje': '100.00',
                        'vigente_desde': timezone.localdate().isoformat(),
                        'activo': True,
                    }
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)
        self.assertEqual(set(empresa.participaciones.values_list('id', flat=True)), original_participation_ids)

    def test_empresa_active_rejects_invalid_participation_totals(self):
        socio_1 = self._create_socio('Socio Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Dos', '22222222-2')

        for first_value, second_value in (('59.99', '40.00'), ('60.01', '40.00')):
            payload = self._empresa_payload(
                participaciones=[
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_1.id,
                        'porcentaje': first_value,
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_2.id,
                        'porcentaje': second_value,
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ]
            )
            response = self.client.post(reverse('patrimonio-empresa-list'), payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empresa_active_rejects_duplicate_current_participant(self):
        socio = self._create_socio('Socio Duplicado Vigente', '11111111-1')
        payload = self._empresa_payload(
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio.id,
                    'porcentaje': '60.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio.id,
                    'porcentaje': '40.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-empresa-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)

    def test_empresa_allows_same_participant_in_historical_non_current_row(self):
        socio_1 = self._create_socio('Socio Historico Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Historico Dos', '22222222-2')
        historical_start = (timezone.localdate() - timedelta(days=90)).isoformat()
        historical_end = (timezone.localdate() - timedelta(days=30)).isoformat()
        payload = self._empresa_payload(
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '100.00',
                    'vigente_desde': historical_start,
                    'vigente_hasta': historical_end,
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '60.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '40.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-empresa-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['participaciones_detail']), 3)

    def test_empresa_active_rejects_future_participations_for_activation(self):
        socio_1 = self._create_socio('Socio Futuro Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Futuro Dos', '22222222-2')
        future_date = (timezone.localdate() + timedelta(days=30)).isoformat()
        payload = self._empresa_payload(
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '60.00',
                    'vigente_desde': future_date,
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '40.00',
                    'vigente_desde': future_date,
                    'activo': True,
                },
            ]
        )

        response = self.client.post(reverse('patrimonio-empresa-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)
        self.assertFalse(Empresa.objects.filter(razon_social='Empresa Canonica').exists())

    def test_empresa_active_rejects_inactive_socio_participant(self):
        socio_activo = self._create_socio('Socio Activo', '11111111-1')
        socio_inactivo = self._create_socio('Socio Inactivo', '22222222-2', activo=False)
        payload = self._empresa_payload(
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_activo.id,
                    'porcentaje': '60.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_inactivo.id,
                    'porcentaje': '40.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ]
        )

        response = self.client.post(reverse('patrimonio-empresa-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)
        self.assertFalse(Empresa.objects.filter(razon_social='Empresa Canonica').exists())

    def test_empresa_rejects_empresa_participant(self):
        company_participant = self.client.post(
            reverse('patrimonio-empresa-list'),
            self._empresa_payload(estado=EstadoPatrimonial.DRAFT),
            format='json',
        )
        self.assertEqual(company_participant.status_code, status.HTTP_201_CREATED)

        socio = self._create_socio('Socio Uno Extra', '23232323-3')
        payload = self._empresa_payload(
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'empresa',
                    'participante_id': company_participant.data['id'],
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ]
        )
        response = self.client.post(reverse('patrimonio-empresa-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comunidad_rejects_patrimonial_representative_outside_participaciones(self):
        socio_1 = self._create_socio('Socio Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Dos', '22222222-2')
        socio_3 = self._create_socio('Socio Tres', '33333333-3')
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            representante_socio_id=socio_3.id,
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_comunidad_active_rejects_future_participations_for_activation(self):
        socio_1 = self._create_socio('Socio Comunidad Futuro Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Comunidad Futuro Dos', '22222222-2')
        future_date = (timezone.localdate() + timedelta(days=30)).isoformat()
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            representante_socio_id=socio_1.id,
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '50.00',
                    'vigente_desde': future_date,
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '50.00',
                    'vigente_desde': future_date,
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)
        self.assertFalse(ComunidadPatrimonial.objects.filter(nombre='Comunidad Patrimonial Uno').exists())

    def test_comunidad_active_rejects_inactive_empresa_participant(self):
        socio = self._create_socio('Socio Comunidad Activo', '11111111-1')
        empresa_participante = Empresa.objects.create(
            razon_social='Empresa Participante Inactiva',
            rut='99999999-9',
            estado=EstadoPatrimonial.DRAFT,
        )
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            representante_socio_id=socio.id,
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'empresa',
                    'participante_id': empresa_participante.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)
        self.assertFalse(ComunidadPatrimonial.objects.filter(nombre='Comunidad Patrimonial Uno').exists())

    def test_comunidad_allows_designated_representative_outside_participaciones(self):
        socio_1 = self._create_socio('Socio Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Dos', '22222222-2')
        socio_designado = self._create_socio('Joaquin Designado', '33333333-3')
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.DESIGNATED,
            representante_socio_id=socio_designado.id,
            representante_evidencia_ref='community-designated-representative-act-001',
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['representacion_vigente']['modo_representacion'], ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(response.data['representacion_vigente']['socio_representante_id'], socio_designado.id)
        self.assertEqual(
            response.data['representacion_vigente']['evidencia_ref'],
            'community-designated-representative-act-001',
        )

    def test_comunidad_update_rejects_direct_participation_rewrite(self):
        socio_a = self._create_socio('Socio Comunidad Rewrite A', '14141414-9')
        socio_b = self._create_socio('Socio Comunidad Rewrite B', '15151515-7')
        replacement = self._create_socio('Socio Comunidad Rewrite Nuevo', '16161616-5')
        create_response = self.client.post(
            reverse('patrimonio-comunidad-list'),
            self._comunidad_payload(
                representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                representante_socio_id=socio_a.id,
                participaciones=[
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_a.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_b.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            ),
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        comunidad = ComunidadPatrimonial.objects.get(pk=create_response.data['id'])
        original_participation_ids = set(comunidad.participaciones.values_list('id', flat=True))

        response = self.client.patch(
            reverse('patrimonio-comunidad-detail', args=[comunidad.id]),
            {
                'participaciones': [
                    {
                        'participante_tipo': 'socio',
                        'participante_id': replacement.id,
                        'porcentaje': '100.00',
                        'vigente_desde': timezone.localdate().isoformat(),
                        'activo': True,
                    }
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('participaciones', response.data)
        self.assertEqual(set(comunidad.participaciones.values_list('id', flat=True)), original_participation_ids)

    def test_comunidad_designated_representative_requires_traceable_evidence(self):
        socio_1 = self._create_socio('Socio Evidencia Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Evidencia Dos', '22222222-2')
        socio_designado = self._create_socio('Joaquin Sin Evidencia', '33333333-3')
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.DESIGNATED,
            representante_socio_id=socio_designado.id,
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('representante_evidencia_ref', response.data)

    def test_comunidad_designated_representative_rejects_sensitive_evidence(self):
        socio_1 = self._create_socio('Socio Sensible Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Sensible Dos', '22222222-2')
        socio_designado = self._create_socio('Joaquin Sensible', '33333333-3')
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.DESIGNATED,
            representante_socio_id=socio_designado.id,
            representante_evidencia_ref='https://example.test/acta?token=secret',
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '50.00',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('representante_evidencia_ref', response.data)

    def test_comunidad_mixta_accepts_empresa_participant(self):
        empresa_participante = self.client.post(
            reverse('patrimonio-empresa-list'),
            self._empresa_payload(),
            format='json',
        )
        self.assertEqual(empresa_participante.status_code, status.HTTP_201_CREATED)

        socio_1 = self._create_socio('Socio Uno', '44444444-4')
        socio_2 = self._create_socio('Socio Dos', '55555555-5')
        payload = self._comunidad_payload(
            representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            representante_socio_id=socio_1.id,
            participaciones=[
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_1.id,
                    'porcentaje': '33.34',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'socio',
                    'participante_id': socio_2.id,
                    'porcentaje': '33.33',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
                {
                    'participante_tipo': 'empresa',
                    'participante_id': empresa_participante.data['id'],
                    'porcentaje': '33.33',
                    'vigente_desde': '2026-01-01',
                    'activo': True,
                },
            ],
        )

        response = self.client.post(reverse('patrimonio-comunidad-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        participant_types = {item['participante_tipo'] for item in response.data['participaciones_detail']}
        self.assertEqual(participant_types, {'socio', 'empresa'})

    def test_propiedad_active_accepts_empresa_comunidad_and_socio_owner(self):
        empresa_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(empresa_response.status_code, status.HTTP_201_CREATED)

        socio_a = self._create_socio('Socio A', '66666666-6')
        socio_b = self._create_socio('Socio B', '77777777-7')
        comunidad_response = self.client.post(
            reverse('patrimonio-comunidad-list'),
            self._comunidad_payload(
                representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                representante_socio_id=socio_a.id,
                participaciones=[
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_a.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_b.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            ),
            format='json',
        )
        self.assertEqual(comunidad_response.status_code, status.HTTP_201_CREATED)

        socio_directo = self._create_socio('Socio Directo', '88888888-8')

        payloads = [
            {'owner_tipo': 'empresa', 'owner_id': empresa_response.data['id'], 'codigo_propiedad': 'EMP-001'},
            {'owner_tipo': 'comunidad', 'owner_id': comunidad_response.data['id'], 'codigo_propiedad': 'COM-001'},
            {'owner_tipo': 'socio', 'owner_id': socio_directo.id, 'codigo_propiedad': 'SOC-001'},
        ]

        for index, payload in enumerate(payloads, start=1):
            response = self.client.post(
                reverse('patrimonio-propiedad-list'),
                {
                    'rol_avaluo': f'ROL-OWNER-{index}',
                    'direccion': f'Apoquindo {100 + index}',
                    'comuna': 'Las Condes',
                    'region': 'RM',
                    'tipo_inmueble': TipoInmueble.LOCAL,
                    'estado': EstadoPatrimonial.ACTIVE,
                    **payload,
                },
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_propiedad_active_rejects_incomplete_or_inactive_owner(self):
        socio_1 = self._create_socio('Socio Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Dos', '22222222-2')
        incomplete_company_response = self.client.post(
            reverse('patrimonio-empresa-list'),
            self._empresa_payload(
                estado=EstadoPatrimonial.DRAFT,
                participaciones=[
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_1.id,
                        'porcentaje': '60.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_2.id,
                        'porcentaje': '20.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            ),
            format='json',
        )
        self.assertEqual(incomplete_company_response.status_code, status.HTTP_201_CREATED)

        company_property_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-2',
                'direccion': 'Providencia 200',
                'comuna': 'Providencia',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.OFFICE,
                'codigo_propiedad': 'EMP-FAIL',
                'estado': EstadoPatrimonial.ACTIVE,
                'owner_tipo': 'empresa',
                'owner_id': incomplete_company_response.data['id'],
            },
            format='json',
        )
        self.assertEqual(company_property_response.status_code, status.HTTP_400_BAD_REQUEST)

        inactive_socio = self._create_socio('Socio Inactivo', '99999999-9', activo=False)
        socio_property_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-3',
                'direccion': 'Providencia 300',
                'comuna': 'Providencia',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.OFFICE,
                'codigo_propiedad': 'SOC-FAIL',
                'estado': EstadoPatrimonial.ACTIVE,
                'owner_tipo': 'socio',
                'owner_id': inactive_socio.id,
            },
            format='json',
        )
        self.assertEqual(socio_property_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codigo_propiedad_is_unique_per_owner(self):
        socio_1 = self._create_socio('Socio Uno', '12121212-4')
        socio_2 = self._create_socio('Socio Dos', '13131313-1')

        base_payload = {
            'rol_avaluo': 'ROL-4',
            'direccion': 'Vitacura 400',
            'comuna': 'Vitacura',
            'region': 'RM',
            'tipo_inmueble': TipoInmueble.LOCAL,
            'estado': EstadoPatrimonial.ACTIVE,
            'codigo_propiedad': 'SOC-100',
            'owner_tipo': 'socio',
        }

        first_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {**base_payload, 'owner_id': socio_1.id},
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        duplicate_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {**base_payload, 'owner_id': socio_1.id, 'direccion': 'Otra 1'},
            format='json',
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

        second_owner_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {**base_payload, 'owner_id': socio_2.id, 'rol_avaluo': 'ROL-5', 'direccion': 'Otra 2'},
            format='json',
        )
        self.assertEqual(second_owner_response.status_code, status.HTTP_201_CREATED)

    def test_propiedad_api_rejects_duplicate_normalized_rol_avaluo(self):
        socio_1 = self._create_socio('Socio Rol API Uno', '12121212-4')
        socio_2 = self._create_socio('Socio Rol API Dos', '13131313-1')
        first_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': '123-45',
                'direccion': 'Av Rol API 100',
                'comuna': 'Santiago',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'estado': EstadoPatrimonial.ACTIVE,
                'codigo_propiedad': 'ROL-API-1',
                'owner_tipo': 'socio',
                'owner_id': socio_1.id,
            },
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        duplicate_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': '123 45',
                'direccion': 'Av Rol API 200',
                'comuna': 'Santiago',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'estado': EstadoPatrimonial.ACTIVE,
                'codigo_propiedad': 'ROL-API-2',
                'owner_tipo': 'socio',
                'owner_id': socio_2.id,
            },
            format='json',
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rol_avaluo', duplicate_response.data)

    def test_propiedad_api_rejects_duplicate_operational_identity(self):
        socio_1 = self._create_socio('Socio Identidad API Uno', '14141414-9')
        socio_2 = self._create_socio('Socio Identidad API Dos', '15151515-5')
        first_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-ID-API-1',
                'direccion': 'Av Identidad API 100',
                'comuna': 'Las Condes',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'estado': EstadoPatrimonial.ACTIVE,
                'codigo_propiedad': 'ID-API-1',
                'owner_tipo': 'socio',
                'owner_id': socio_1.id,
            },
            format='json',
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        duplicate_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-ID-API-2',
                'direccion': ' av identidad api  100 ',
                'comuna': 'LAS CONDES',
                'region': 'rm',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'estado': EstadoPatrimonial.ACTIVE,
                'codigo_propiedad': 'ID-API-1',
                'owner_tipo': 'socio',
                'owner_id': socio_2.id,
            },
            format='json',
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('codigo_propiedad', duplicate_response.data)

    def test_empresa_update_emits_update_and_state_change_audit_events(self):
        create_response = self.client.post(
            reverse('patrimonio-empresa-list'),
            self._empresa_payload(estado=EstadoPatrimonial.DRAFT),
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        patch_response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[create_response.data['id']]),
            {'estado': EstadoPatrimonial.ACTIVE},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='patrimonio.empresa.updated',
                entity_type='empresa',
                entity_id=str(create_response.data['id']),
            ).exists()
        )
        state_event = AuditEvent.objects.get(
            event_type='patrimonio.empresa.state_changed',
            entity_type='empresa',
            entity_id=str(create_response.data['id']),
        )
        self.assertEqual(
            state_event.metadata,
            {
                'campo_estado': 'estado',
                'estado_anterior': EstadoPatrimonial.DRAFT,
                'estado_nuevo': EstadoPatrimonial.ACTIVE,
            },
        )

    def test_socio_update_emits_active_state_change_metadata(self):
        socio = self._create_socio('Socio Metadata', '12121212-8')

        patch_response = self.client.patch(
            reverse('patrimonio-socio-detail', args=[socio.id]),
            {'activo': False},
            format='json',
        )

        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        state_event = AuditEvent.objects.get(
            event_type='patrimonio.socio.state_changed',
            entity_type='socio',
            entity_id=str(socio.id),
        )
        self.assertEqual(
            state_event.metadata,
            {
                'campo_estado': 'activo',
                'estado_anterior': True,
                'estado_nuevo': False,
            },
        )

    def test_empresa_update_rolls_back_when_state_change_audit_fails(self):
        create_response = self.client.post(
            reverse('patrimonio-empresa-list'),
            self._empresa_payload(estado=EstadoPatrimonial.DRAFT),
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        empresa = Empresa.objects.get(pk=create_response.data['id'])

        from audit.services import create_audit_event as real_create_audit_event

        def fail_state_change_audit(**kwargs):
            if kwargs.get('event_type') == 'patrimonio.empresa.state_changed':
                raise RuntimeError('state change audit unavailable')
            return real_create_audit_event(**kwargs)

        with patch('patrimonio.views.create_audit_event', side_effect=fail_state_change_audit):
            with self.assertRaisesRegex(RuntimeError, 'state change audit unavailable'):
                self.client.patch(
                    reverse('patrimonio-empresa-detail', args=[empresa.id]),
                    {'estado': EstadoPatrimonial.ACTIVE},
                    format='json',
                )

        empresa.refresh_from_db()
        self.assertEqual(empresa.estado, EstadoPatrimonial.DRAFT)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type__in=['patrimonio.empresa.updated', 'patrimonio.empresa.state_changed'],
                entity_id=str(empresa.id),
            ).exists()
        )

    def test_empresa_deactivation_rejects_active_own_participations(self):
        create_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[create_response.data['id']]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertFalse(AuditEvent.objects.filter(event_type='patrimonio.empresa.state_changed').exists())

    def test_empresa_deactivation_rejects_active_account_dependency(self):
        create_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        empresa = Empresa.objects.get(pk=create_response.data['id'])
        self._create_active_account(empresa=empresa, numero='ACC-EXIT-001')

        response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[empresa.id]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('cuentas recaudadoras activas', str(response.data['estado']))
        self.assertFalse(AuditEvent.objects.filter(event_type='patrimonio.empresa.state_changed').exists())

    def test_empresa_deactivation_rejects_active_mandate_dependency(self):
        create_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        empresa = Empresa.objects.get(pk=create_response.data['id'])
        propietario = self._create_socio('Propietario Mandato Salida', '15151515-7')
        propiedad = Propiedad.objects.create(
            direccion='Av Mandato Salida 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='EXIT-MAN-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=propietario,
        )
        cuenta = self._create_active_account(socio=propietario, numero='ACC-EXIT-002')
        MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_socio_owner=propietario,
            administrador_empresa_owner=empresa,
            recaudador_socio_owner=propietario,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=False,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-exit-001',
            vigencia_desde='2026-01-01',
            estado=EstadoMandatoOperacion.ACTIVE,
        )

        response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[empresa.id]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('mandatos operativos activos', str(response.data['estado']))
        self.assertFalse(AuditEvent.objects.filter(event_type='patrimonio.empresa.state_changed').exists())

    def test_empresa_deactivation_rejects_active_identity_dependency(self):
        create_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        empresa = Empresa.objects.get(pk=create_response.data['id'])
        IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=CanalOperacion.EMAIL,
            remitente_visible=empresa.razon_social,
            direccion_o_numero='salida-operativa@example.com',
            credencial_ref='identity-exit-ref-001',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

        response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[empresa.id]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('identidades de envio activas', str(response.data['estado']))
        self.assertFalse(AuditEvent.objects.filter(event_type='patrimonio.empresa.state_changed').exists())

    def test_socio_deactivation_rejects_active_account_dependency(self):
        socio = self._create_socio('Socio Cuenta Salida', '13131313-0')
        self._create_active_account(socio=socio, numero='ACC-SOC-EXIT-001')

        response = self.client.patch(
            reverse('patrimonio-socio-detail', args=[socio.id]),
            {'activo': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('activo', response.data)
        self.assertIn('cuentas recaudadoras activas', str(response.data['activo']))
        socio.refresh_from_db()
        self.assertTrue(socio.activo)

    def test_socio_deactivation_rejects_active_mandate_dependency(self):
        socio = self._create_socio('Socio Mandato Salida', '14141414-9')
        propiedad = Propiedad.objects.create(
            direccion='Av Mandato Socio 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='EXIT-SOC-MAN-001',
            estado=EstadoPatrimonial.ACTIVE,
            socio_owner=socio,
        )
        cuenta = self._create_active_account(socio=socio, numero='ACC-SOC-EXIT-002')
        MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_socio_owner=socio,
            administrador_socio_owner=socio,
            recaudador_socio_owner=socio,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_directo',
            autoriza_recaudacion=True,
            autoriza_facturacion=False,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-socio-exit-001',
            vigencia_desde='2026-01-01',
            estado=EstadoMandatoOperacion.ACTIVE,
        )

        response = self.client.patch(
            reverse('patrimonio-socio-detail', args=[socio.id]),
            {'activo': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('activo', response.data)
        self.assertIn('mandatos operativos activos', str(response.data['activo']))
        socio.refresh_from_db()
        self.assertTrue(socio.activo)

    def test_socio_deactivation_rejects_active_identity_dependency(self):
        socio = self._create_socio('Socio Identidad Salida', '15151515-7')
        IdentidadDeEnvio.objects.create(
            socio_owner=socio,
            canal=CanalOperacion.EMAIL,
            remitente_visible=socio.nombre,
            direccion_o_numero='salida-socio@example.com',
            credencial_ref='identity-socio-exit-ref-001',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

        response = self.client.patch(
            reverse('patrimonio-socio-detail', args=[socio.id]),
            {'activo': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('activo', response.data)
        self.assertIn('identidades de envio activas', str(response.data['activo']))
        socio.refresh_from_db()
        self.assertTrue(socio.activo)

    def test_comunidad_deactivation_rejects_active_account_dependency(self):
        comunidad = ComunidadPatrimonial.objects.create(
            nombre='Comunidad Cuenta Salida',
            estado=EstadoPatrimonial.ACTIVE,
        )
        self._create_active_account(comunidad=comunidad, numero='ACC-COM-EXIT-001')

        response = self.client.patch(
            reverse('patrimonio-comunidad-detail', args=[comunidad.id]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('cuentas recaudadoras activas', str(response.data['estado']))
        comunidad.refresh_from_db()
        self.assertEqual(comunidad.estado, EstadoPatrimonial.ACTIVE)

    def test_comunidad_deactivation_rejects_active_mandate_dependency(self):
        administrador = self._create_socio('Administrador Comunidad Salida', '16161616-5')
        comunidad = ComunidadPatrimonial.objects.create(
            nombre='Comunidad Mandato Salida',
            estado=EstadoPatrimonial.ACTIVE,
        )
        propiedad = Propiedad.objects.create(
            direccion='Av Mandato Comunidad 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='EXIT-COM-MAN-001',
            estado=EstadoPatrimonial.ACTIVE,
            comunidad_owner=comunidad,
        )
        cuenta = self._create_active_account(comunidad=comunidad, numero='ACC-COM-EXIT-002')
        MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_comunidad_owner=comunidad,
            administrador_socio_owner=administrador,
            recaudador_comunidad_owner=comunidad,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_comunidad',
            autoriza_recaudacion=True,
            autoriza_facturacion=False,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-community-exit-001',
            vigencia_desde='2026-01-01',
            estado=EstadoMandatoOperacion.ACTIVE,
        )

        response = self.client.patch(
            reverse('patrimonio-comunidad-detail', args=[comunidad.id]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertIn('mandatos operativos activos', str(response.data['estado']))
        comunidad.refresh_from_db()
        self.assertEqual(comunidad.estado, EstadoPatrimonial.ACTIVE)

    def test_comunidad_deactivation_rejects_active_structure(self):
        socio_a = self._create_socio('Socio Comunidad Estructura A', '15151515-7')
        socio_b = self._create_socio('Socio Comunidad Estructura B', '16161616-5')
        create_response = self.client.post(
            reverse('patrimonio-comunidad-list'),
            self._comunidad_payload(
                representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                representante_socio_id=socio_a.id,
                participaciones=[
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_a.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_b.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            ),
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('patrimonio-comunidad-detail', args=[create_response.data['id']]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)

    def test_socio_deactivation_rejects_active_patrimonial_dependencies(self):
        socio = self._create_socio('Socio Con Dependencia', '14141414-9')
        empresa = Empresa.objects.create(
            razon_social='Empresa Dependiente',
            rut='99999999-9',
            estado=EstadoPatrimonial.ACTIVE,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=empresa,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        response = self.client.patch(
            reverse('patrimonio-socio-detail', args=[socio.id]),
            {'activo': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('activo', response.data)
        socio.refresh_from_db()
        self.assertTrue(socio.activo)

    def test_participation_transfer_endpoint_replaces_origin_with_audited_targets(self):
        origin = self._create_socio('Cristian Origen', '14141414-9')
        remaining = self._create_socio('Socio Continuador', '15151515-7')
        target_one = self._create_socio('Catalina Destino', '16161616-5')
        target_two = self._create_socio('Trinidad Destino', '17171717-3')
        empresa = Empresa.objects.create(razon_social='Empresa Transferible', rut='99999999-9', estado=EstadoPatrimonial.ACTIVE)
        origin_participation = ParticipacionPatrimonial.objects.create(
            participante_socio=origin,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=remaining,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        effective_date = timezone.localdate()

        response = self.client.post(
            reverse('patrimonio-participacion-transferir'),
            {
                'owner_tipo': 'empresa',
                'owner_id': empresa.id,
                'participante_origen_tipo': 'socio',
                'participante_origen_id': origin.id,
                'fecha_efectiva': effective_date.isoformat(),
                'transferencias': [
                    {'participante_tipo': 'socio', 'participante_id': target_one.id, 'porcentaje': '20.00'},
                    {'participante_tipo': 'socio', 'participante_id': target_two.id, 'porcentaje': '20.00'},
                ],
                'motivo': 'Redistribucion sucesoria controlada.',
                'evidencia_ref': 'participation-transfer-success-001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        origin_participation.refresh_from_db()
        self.assertEqual(origin_participation.vigente_hasta, effective_date - timedelta(days=1))
        self.assertEqual(len(response.data['participaciones_destino']), 2)
        self.assertEqual(empresa.total_participaciones_activas(), Decimal('100.00'))
        audit_event = AuditEvent.objects.get(event_type='patrimonio.participacion.transfer_executed')
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.entity_type, 'participacion_patrimonial')
        self.assertEqual(audit_event.entity_id, str(origin_participation.id))
        self.assertEqual(audit_event.metadata['owner_tipo'], 'empresa')
        self.assertEqual(audit_event.metadata['owner_id'], empresa.id)
        self.assertEqual(audit_event.metadata['origin_participation_id'], origin_participation.id)
        self.assertEqual(audit_event.metadata['origin_participant_type'], 'socio')
        self.assertEqual(audit_event.metadata['origin_participant_id'], origin.id)
        self.assertEqual(audit_event.metadata['effective_date'], effective_date.isoformat())
        self.assertEqual(audit_event.metadata['reason'], 'Redistribucion sucesoria controlada.')
        self.assertEqual(audit_event.metadata['evidence_ref'], 'participation-transfer-success-001')
        self.assertCountEqual(audit_event.metadata['target_participation_ids'], [item['id'] for item in response.data['participaciones_destino']])
        self.assertEqual(audit_event.metadata['target_count'], 2)
        self.assertEqual(audit_event.metadata['transferred_percentage'], '40.00')

    def test_participation_transfer_endpoint_rejects_sensitive_reason(self):
        origin = self._create_socio('Socio Origen Motivo', '14141414-9')
        remaining = self._create_socio('Socio Continuador Motivo', '15151515-7')
        target = self._create_socio('Socio Destino Motivo', '16161616-5')
        empresa = Empresa.objects.create(razon_social='Empresa Motivo Sensible', rut='99999999-9', estado=EstadoPatrimonial.ACTIVE)
        origin_participation = ParticipacionPatrimonial.objects.create(
            participante_socio=origin,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=remaining,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        response = self.client.post(
            reverse('patrimonio-participacion-transferir'),
            {
                'owner_tipo': 'empresa',
                'owner_id': empresa.id,
                'participante_origen_tipo': 'socio',
                'participante_origen_id': origin.id,
                'fecha_efectiva': timezone.localdate().isoformat(),
                'transferencias': [
                    {'participante_tipo': 'socio', 'participante_id': target.id, 'porcentaje': '40.00'},
                ],
                'motivo': 'Decision respaldada en https://docs.example.test/transfer?token=secret',
                'evidencia_ref': 'participation-transfer-sensitive-reason-001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        origin_participation.refresh_from_db()
        self.assertIsNone(origin_participation.vigente_hasta)
        self.assertFalse(AuditEvent.objects.filter(event_type='patrimonio.participacion.transfer_executed').exists())

    def test_participation_transfer_endpoint_rejects_percentage_mismatch(self):
        origin = self._create_socio('Socio Origen Mismatch', '14141414-9')
        remaining = self._create_socio('Socio Continuador Mismatch', '15151515-7')
        target = self._create_socio('Socio Destino Mismatch', '16161616-5')
        empresa = Empresa.objects.create(razon_social='Empresa Mismatch', rut='99999999-9', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=origin,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=remaining,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        response = self.client.post(
            reverse('patrimonio-participacion-transferir'),
            {
                'owner_tipo': 'empresa',
                'owner_id': empresa.id,
                'participante_origen_tipo': 'socio',
                'participante_origen_id': origin.id,
                'fecha_efectiva': timezone.localdate().isoformat(),
                'transferencias': [
                    {'participante_tipo': 'socio', 'participante_id': target.id, 'porcentaje': '30.00'},
                ],
                'motivo': 'Redistribucion con total incorrecto.',
                'evidencia_ref': 'participation-transfer-mismatch-001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertFalse(AuditEvent.objects.filter(event_type='patrimonio.participacion.transfer_executed').exists())

    def test_empresa_deactivation_rejects_active_property_dependency(self):
        empresa_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(empresa_response.status_code, status.HTTP_201_CREATED)
        property_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-DEP-1',
                'direccion': 'Dependencia 100',
                'comuna': 'Santiago',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'codigo_propiedad': 'DEP-EMP',
                'estado': EstadoPatrimonial.ACTIVE,
                'owner_tipo': 'empresa',
                'owner_id': empresa_response.data['id'],
            },
            format='json',
        )
        self.assertEqual(property_response.status_code, status.HTTP_201_CREATED)

        patch_response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[empresa_response.data['id']]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', patch_response.data)
        self.assertEqual(Empresa.objects.get(id=empresa_response.data['id']).estado, EstadoPatrimonial.ACTIVE)

    def test_comunidad_deactivation_rejects_active_property_dependency(self):
        socio_a = self._create_socio('Socio Comunidad A', '14141414-9')
        socio_b = self._create_socio('Socio Comunidad B', '15151515-7')
        comunidad_response = self.client.post(
            reverse('patrimonio-comunidad-list'),
            self._comunidad_payload(
                representante_modo=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                representante_socio_id=socio_a.id,
                participaciones=[
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_a.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_b.id,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            ),
            format='json',
        )
        self.assertEqual(comunidad_response.status_code, status.HTTP_201_CREATED)
        property_response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-DEP-2',
                'direccion': 'Dependencia 200',
                'comuna': 'Santiago',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'codigo_propiedad': 'DEP-COM',
                'estado': EstadoPatrimonial.ACTIVE,
                'owner_tipo': 'comunidad',
                'owner_id': comunidad_response.data['id'],
            },
            format='json',
        )
        self.assertEqual(property_response.status_code, status.HTTP_201_CREATED)

        patch_response = self.client.patch(
            reverse('patrimonio-comunidad-detail', args=[comunidad_response.data['id']]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )

        self.assertEqual(patch_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', patch_response.data)
        self.assertEqual(
            ComunidadPatrimonial.objects.get(id=comunidad_response.data['id']).estado,
            EstadoPatrimonial.ACTIVE,
        )

    def test_designated_representation_can_be_seen_from_model(self):
        socio_participante = self._create_socio('Socio Participante', '14141414-9')
        socio_designado = self._create_socio('Joaquin', '15151515-7')
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Modelo', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_participante,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde='2026-01-01',
            activo=True,
            evidencia_ref='community-designated-representative-act-002',
        )

        self.assertEqual(comunidad.representante_socio_id, socio_designado.id)
        self.assertFalse(comunidad.representante_es_participante_activo())

    def test_future_representation_is_not_current_for_active_community(self):
        socio_participante = self._create_socio('Socio Participante Futuro', '11111111-1')
        socio_designado = self._create_socio('Socio Representante Futuro', '22222222-2')
        future_date = timezone.localdate() + timedelta(days=30)
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Futura', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_participante,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde=future_date,
            activo=True,
            evidencia_ref='community-designated-representative-future-act-001',
        )

        self.assertIsNone(comunidad.representacion_vigente())
        with self.assertRaises(ValidationError) as error:
            comunidad.full_clean()
        self.assertIn('estado', error.exception.message_dict)

        detail_response = self.client.get(reverse('patrimonio-comunidad-detail', args=[comunidad.id]))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertIsNone(detail_response.data['representacion_vigente'])

        snapshot_response = self.client.get(reverse('patrimonio-snapshot'))
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        comunidad_snapshot = next(
            item for item in snapshot_response.data['comunidades']
            if item['id'] == comunidad.id
        )
        self.assertIsNone(comunidad_snapshot['representacion_vigente'])

    def test_future_representation_does_not_block_socio_deactivation(self):
        socio_designado = self._create_socio('Socio Futuro Desactivable', '11111111-1')
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Representacion Futura')
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_designado,
            vigente_desde=timezone.localdate() + timedelta(days=30),
            activo=True,
            evidencia_ref='community-designated-representative-future-act-002',
        )

        socio_designado.activo = False

        try:
            socio_designado.full_clean()
        except ValidationError as error:
            self.fail(f'Future representation should not block deactivation: {error}')

    def test_scheduled_representation_after_current_window_is_allowed(self):
        socio_actual = self._create_socio('Socio Actual Programado', '11111111-1')
        socio_futuro = self._create_socio('Socio Futuro Programado', '22222222-2')
        today = timezone.localdate()
        future_date = today + timedelta(days=30)
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Programable', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_actual,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde=today,
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_actual,
            vigente_desde=today,
            vigente_hasta=future_date - timedelta(days=1),
            activo=True,
        )
        future_representation = RepresentacionComunidad(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_futuro,
            vigente_desde=future_date,
            activo=True,
            evidencia_ref='community-designated-representative-future-act-003',
        )

        future_representation.full_clean()
        future_representation.save()
        comunidad.full_clean()

        self.assertEqual(comunidad.representacion_vigente().socio_representante_id, socio_actual.id)
        self.assertEqual(comunidad.representaciones.filter(activo=True).count(), 2)

    def test_scheduled_patrimonial_representation_uses_future_participation_window(self):
        socio_actual = self._create_socio('Socio Actual Ventana', '11111111-1')
        socio_futuro = self._create_socio('Socio Futuro Ventana', '22222222-2')
        today = timezone.localdate()
        future_date = today + timedelta(days=30)
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Ventana', estado=EstadoPatrimonial.ACTIVE)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_actual,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde=today,
            vigente_hasta=future_date - timedelta(days=1),
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_futuro,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde=future_date,
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_actual,
            vigente_desde=today,
            vigente_hasta=future_date - timedelta(days=1),
            activo=True,
        )
        future_representation = RepresentacionComunidad(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_futuro,
            vigente_desde=future_date,
            activo=True,
        )

        future_representation.full_clean()
        future_representation.save()
        comunidad.full_clean()

        self.assertEqual(comunidad.representacion_vigente().socio_representante_id, socio_actual.id)
        self.assertEqual(comunidad.representaciones.filter(activo=True).count(), 2)

    def test_scheduled_patrimonial_representation_rejects_missing_participation_window(self):
        socio_actual = self._create_socio('Socio Actual Sin Ventana', '11111111-1')
        socio_futuro = self._create_socio('Socio Futuro Sin Ventana', '22222222-2')
        today = timezone.localdate()
        future_date = today + timedelta(days=30)
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Sin Ventana')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_actual,
            comunidad_owner=comunidad,
            porcentaje='100.00',
            vigente_desde=today,
            activo=True,
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_actual,
            vigente_desde=today,
            vigente_hasta=future_date - timedelta(days=1),
            activo=True,
        )
        future_representation = RepresentacionComunidad(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_futuro,
            vigente_desde=future_date,
            activo=True,
        )

        with self.assertRaises(ValidationError) as error:
            future_representation.full_clean()
        self.assertIn('socio_representante', error.exception.message_dict)

    def test_overlapping_active_representation_window_is_rejected(self):
        socio_actual = self._create_socio('Socio Actual Solape', '11111111-1')
        socio_futuro = self._create_socio('Socio Futuro Solape', '22222222-2')
        today = timezone.localdate()
        comunidad = ComunidadPatrimonial.objects.create(nombre='Comunidad Solape')
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_actual,
            vigente_desde=today,
            activo=True,
            evidencia_ref='community-designated-representative-current-act-001',
        )
        overlapping_representation = RepresentacionComunidad(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.DESIGNATED,
            socio_representante=socio_futuro,
            vigente_desde=today + timedelta(days=30),
            activo=True,
            evidencia_ref='community-designated-representative-overlap-act-001',
        )

        with self.assertRaises(ValidationError) as error:
            overlapping_representation.full_clean()
        self.assertIn('vigente_desde', error.exception.message_dict)


class PatrimonioScopeAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.user = user_model.objects.create_user(
            username='patrimonio-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.company_a = self._create_active_company('Scope A', '88888888-8', ('11111111-1', '22222222-2'))
        self.company_b = self._create_active_company('Scope B', '99999999-9', ('33333333-3', '44444444-4'))
        self.propiedad_a = Propiedad.objects.create(
            rol_avaluo='ROL-SCOPE-A',
            direccion='Av Scope A 100',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='SCOPE-A',
            estado=EstadoPatrimonial.ACTIVE,
            empresa_owner=self.company_a,
        )
        scope = Scope.objects.create(
            code=f'company-{self.company_a.id}',
            name=f'Empresa {self.company_a.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(self.company_a.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=self.user, role=self.operator_role, scope=scope, is_primary=True)
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=True)

    def _create_active_company(self, nombre, rut, socio_ruts):
        socio_1 = self._create_socio(f'{nombre} Socio 1', socio_ruts[0])
        socio_2 = self._create_socio(f'{nombre} Socio 2', socio_ruts[1])
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado=EstadoPatrimonial.ACTIVE)
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

    def test_operator_cannot_create_property_for_company_outside_scope(self):
        response = self.client.post(
            reverse('patrimonio-propiedad-list'),
            {
                'rol_avaluo': 'ROL-SCOPE-B',
                'direccion': 'Av Scope B 200',
                'comuna': 'Santiago',
                'region': 'RM',
                'tipo_inmueble': TipoInmueble.LOCAL,
                'codigo_propiedad': 'SCOPE-B',
                'estado': EstadoPatrimonial.ACTIVE,
                'owner_tipo': 'empresa',
                'owner_id': self.company_b.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_reassign_property_to_company_outside_scope(self):
        response = self.client.patch(
            reverse('patrimonio-propiedad-detail', args=[self.propiedad_a.id]),
            {
                'owner_tipo': 'empresa',
                'owner_id': self.company_b.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PatrimonioMigrationSafetyTests(TransactionTestCase):
    reset_sequences = True

    migrate_from = [
        ('patrimonio', '0001_initial'),
    ]
    migrate_to = [
        ('patrimonio', '0003_repair_legacy_representacion_modes'),
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

    def test_legacy_representative_outside_participaciones_migrates_as_designated(self):
        Socio = self.old_apps.get_model('patrimonio', 'Socio')
        ComunidadPatrimonial = self.old_apps.get_model('patrimonio', 'ComunidadPatrimonial')
        ParticipacionPatrimonial = self.old_apps.get_model('patrimonio', 'ParticipacionPatrimonial')

        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        socio_designado = Socio.objects.create(nombre='Joaquin Designado', rut='33333333-3', activo=True)
        comunidad = ComunidadPatrimonial.objects.create(
            nombre='Comunidad Legacy',
            estado='activa',
            representante_socio_id=socio_designado.id,
        )
        ParticipacionPatrimonial.objects.create(
            socio_id=socio_1.id,
            comunidad_owner_id=comunidad.id,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            socio_id=socio_2.id,
            comunidad_owner_id=comunidad.id,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        self.migrate()

        RepresentacionComunidadNew = self.apps.get_model('patrimonio', 'RepresentacionComunidad')
        representacion = RepresentacionComunidadNew.objects.get(comunidad__nombre='Comunidad Legacy')
        self.assertEqual(representacion.modo_representacion, ModoRepresentacionComunidad.DESIGNATED)
