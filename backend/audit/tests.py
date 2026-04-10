from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from patrimonio.models import ComunidadPatrimonial, Empresa, ModoRepresentacionComunidad, Propiedad, Socio

from .models import ManualResolution


class AuditAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='audit', password='secret123')
        self.client.force_authenticate(self.user)

    def test_auth_is_required_for_manual_resolution_endpoints(self):
        client = self.client_class()
        response = client.get(reverse('manual-resolution-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manual_resolution_list_supports_filters(self):
        first = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-1',
            summary='Primera',
            status='open',
        )
        ManualResolution.objects.create(
            category='migration.arrendatario.invalid_rut',
            scope_type='legacy_arrendatario',
            scope_reference='arr-1',
            summary='Segunda',
            status='resolved',
        )

        response = self.client.get(
            f"{reverse('manual-resolution-list')}?status=open&category={first.category}&scope_type=legacy_propiedad"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['scope_reference'], 'prop-1')

    def test_resolve_property_owner_manual_resolution_creates_comunidad_and_propiedad(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-1',
            summary='Owner manual',
            metadata={
                'codigo': 46,
                'codigo_propiedad': None,
                'direccion': 'Av. Santa Maria 9500 Dpto 1014',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-1',
                'comuna': 'Santiago',
                'region': '',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Av Santa Maria 9500 Dpto 1014',
                'representante_socio_id': socio_1.pk,
                'representante_modo': ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, 'resolved')
        self.assertEqual(ComunidadPatrimonial.objects.count(), 1)
        self.assertEqual(Propiedad.objects.count(), 1)
        self.assertEqual(Propiedad.objects.get().comunidad_owner_id, ComunidadPatrimonial.objects.get().pk)
        self.assertEqual(ComunidadPatrimonial.objects.get().representacion_vigente().modo_representacion, ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT)

    def test_resolve_property_owner_manual_resolution_allows_designated_representative(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        socio_designado = Socio.objects.create(nombre='Joaquin', rut='33333333-3', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-2',
            summary='Owner manual',
            metadata={
                'codigo': 47,
                'direccion': 'Av. Comunidad Designada 123',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-2',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Designada',
                'representante_socio_id': socio_designado.pk,
                'representante_modo': ModoRepresentacionComunidad.DESIGNATED,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get()
        self.assertEqual(comunidad.representacion_vigente().modo_representacion, ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(comunidad.representante_socio_id, socio_designado.pk)

    def test_resolve_property_owner_manual_resolution_accepts_mixed_participants(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(razon_social='Inmobiliaria Puig SpA', rut='76311245-4', estado='activa')
        socio_empresa_1 = Socio.objects.create(nombre='Socio Empresa Uno', rut='44444444-4', activo=True)
        socio_empresa_2 = Socio.objects.create(nombre='Socio Empresa Dos', rut='55555555-5', activo=True)
        from patrimonio.models import ParticipacionPatrimonial

        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_1,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_2,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-3',
            summary='Owner manual mixed',
            metadata={
                'codigo': 48,
                'direccion': 'Edificio Q 1014',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-3',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Mixta Edificio Q',
                'representante_socio_id': socio_1.pk,
                'representante_modo': ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                'region': 'RM',
                'participaciones': [
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_1.pk,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'empresa',
                        'participante_id': empresa.pk,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Mixta Edificio Q')
        participant_types = {item.participante_tipo for item in comunidad.participaciones.all()}
        self.assertEqual(participant_types, {'socio', 'empresa'})
