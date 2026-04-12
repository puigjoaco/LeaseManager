from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Role, UserScopeAssignment
from patrimonio.models import Socio


class RolePermissionTests(APITestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def _force_user(self, *, username, role_code, metadata=None):
        user = self.user_model.objects.create_user(
            username=username,
            password='secret123',
            default_role_code=role_code,
            metadata=metadata or {},
        )
        self.client.force_authenticate(user)
        return user

    def test_operador_can_create_operational_record(self):
        self._force_user(username='operator-role', role_code='operator')

        response = self.client.post(
            reverse('patrimonio-socio-list'),
            {
                'nombre': 'Socio Operador',
                'rut': '11.111.111-1',
                'email': 'operador@example.com',
                'telefono': '123',
                'domicilio': 'Temuco',
                'activo': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_operador_cannot_write_control_modules(self):
        self._force_user(username='operator-control', role_code='operator')

        response = self.client.post(
            reverse('contabilidad-regimen-list'),
            {
                'codigo_regimen': 'TEST-REG',
                'descripcion': 'Regimen test',
                'estado': 'activa',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operador_cannot_read_control_modules(self):
        self._force_user(username='operator-control-read', role_code='operator')

        response = self.client.get(reverse('contabilidad-regimen-list'))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_can_read_control_modules_but_not_operational_write(self):
        self._force_user(username='reviewer-role', role_code='RevisorFiscalExterno')

        control_read = self.client.get(reverse('contabilidad-regimen-list'))
        self.assertEqual(control_read.status_code, status.HTTP_200_OK)

        operational_write = self.client.post(
            reverse('operacion-cuenta-list'),
            {
                'owner_tipo': 'socio',
                'owner_id': 999,
            },
            format='json',
        )
        self.assertEqual(operational_write.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_can_read_reporting_but_not_operational_dashboard(self):
        self._force_user(username='reviewer-reporting', role_code='RevisorFiscalExterno')

        financial_read = self.client.get(reverse('reporting-tributario-anual'), {'anio_tributario': 2027})
        dashboard_read = self.client.get(reverse('reporting-dashboard-operativo'))

        self.assertEqual(financial_read.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard_read.status_code, status.HTTP_403_FORBIDDEN)

    def test_socio_can_only_access_own_partner_summary(self):
        own_socio = Socio.objects.create(nombre='Socio Propio', rut='12.345.678-5', activo=True)
        other_socio = Socio.objects.create(nombre='Socio Ajeno', rut='16.222.333-4', activo=True)
        self._force_user(
            username='partner-role',
            role_code='Socio',
            metadata={'socio_id': own_socio.id},
        )

        own_response = self.client.get(reverse('reporting-socio-resumen', args=[own_socio.id]))
        other_response = self.client.get(reverse('reporting-socio-resumen', args=[other_socio.id]))
        dashboard_response = self.client.get(reverse('reporting-dashboard-operativo'))

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(other_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(dashboard_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_active_assignment_role_expands_permissions(self):
        user = self.user_model.objects.create_user(
            username='assigned-reviewer',
            password='secret123',
            default_role_code='Socio',
            metadata={},
        )
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        UserScopeAssignment.objects.create(user=user, role=reviewer_role, scope=None, is_primary=True)
        self.client.force_authenticate(user)

        response = self.client.get(reverse('contabilidad-regimen-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RolePermissionUtilityTests(TestCase):
    def test_role_alias_operator_maps_to_operador_de_cartera(self):
        from core.permissions import ROLE_OPERATOR, normalize_role_code

        self.assertEqual(normalize_role_code('operator'), ROLE_OPERATOR)
