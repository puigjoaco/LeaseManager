from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent

from .models import (
    ComunidadPatrimonial,
    Empresa,
    EstadoPatrimonial,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
    TipoInmueble,
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


class PatrimonioAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='tester', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

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

    def _comunidad_payload(self, *, representante_modo, representante_socio_id, participaciones, estado=EstadoPatrimonial.ACTIVE):
        return {
            'nombre': 'Comunidad Patrimonial Uno',
            'representante_modo': representante_modo,
            'representante_socio_id': representante_socio_id,
            'estado': estado,
            'participaciones': participaciones,
        }

    def test_auth_is_required_for_all_list_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('patrimonio-socio-list'),
            reverse('patrimonio-empresa-list'),
            reverse('patrimonio-comunidad-list'),
            reverse('patrimonio-propiedad-list'),
            reverse('patrimonio-participacion-list'),
        ]

        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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

    def test_comunidad_allows_designated_representative_outside_participaciones(self):
        socio_1 = self._create_socio('Socio Uno', '11111111-1')
        socio_2 = self._create_socio('Socio Dos', '22222222-2')
        socio_designado = self._create_socio('Joaquin Designado', '33333333-3')
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['representacion_vigente']['modo_representacion'], ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(response.data['representacion_vigente']['socio_representante_id'], socio_designado.id)

    def test_comunidad_mixta_accepts_empresa_participant(self):
        empresa_participante = self.client.post(
            reverse('patrimonio-empresa-list'),
            self._empresa_payload(estado=EstadoPatrimonial.DRAFT),
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

        for payload in payloads:
            response = self.client.post(
                reverse('patrimonio-propiedad-list'),
                {
                    'rol_avaluo': 'ROL-1',
                    'direccion': 'Apoquindo 100',
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
            {**base_payload, 'owner_id': socio_2.id, 'direccion': 'Otra 2'},
            format='json',
        )
        self.assertEqual(second_owner_response.status_code, status.HTTP_201_CREATED)

    def test_empresa_update_emits_update_and_state_change_audit_events(self):
        create_response = self.client.post(reverse('patrimonio-empresa-list'), self._empresa_payload(), format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        patch_response = self.client.patch(
            reverse('patrimonio-empresa-detail', args=[create_response.data['id']]),
            {'estado': EstadoPatrimonial.INACTIVE},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditEvent.objects.filter(event_type='patrimonio.empresa.updated').exists())
        self.assertTrue(AuditEvent.objects.filter(event_type='patrimonio.empresa.state_changed').exists())

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
        )

        self.assertEqual(comunidad.representante_socio_id, socio_designado.id)
        self.assertFalse(comunidad.representante_es_participante_activo())
