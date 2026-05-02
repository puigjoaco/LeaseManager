from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Role, RoleScope, Scope, UserScopeAssignment
from operacion.models import CuentaRecaudadora
from patrimonio.models import Empresa, Propiedad, Socio
from users.models import User


class SeedDemoAccessCommandTests(TestCase):
    def setUp(self):
        self.socio = Socio.objects.create(
            nombre='Socio Demo',
            rut='12.345.678-5',
            activo=True,
        )
        self.empresa = Empresa.objects.create(
            razon_social='Empresa Demo',
            rut='76.311.245-4',
            estado='borrador',
        )
        self.propiedad = Propiedad.objects.create(
            codigo_propiedad='P-001',
            direccion='Propiedad Demo',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble='oficina',
            estado='borrador',
            socio_owner=self.socio,
        )
        self.cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=self.empresa,
            institucion='Banco Demo',
            numero_cuenta='123456789',
            tipo_cuenta='corriente',
            titular_nombre='Empresa Demo',
            titular_rut='76.311.245-4',
            moneda_operativa='CLP',
            estado_operativo='borrador',
        )

    def test_command_creates_roles_scopes_users_and_assignments(self):
        output = StringIO()

        call_command('seed_demo_access', stdout=output)

        self.assertEqual(Role.objects.count(), 4)
        self.assertEqual(Scope.objects.count(), 4)
        self.assertEqual(RoleScope.objects.count(), 4)
        self.assertEqual(User.objects.filter(username__startswith='demo-').count(), 4)
        self.assertEqual(UserScopeAssignment.objects.filter(effective_to__isnull=True).count(), 4)

        partner_user = User.objects.get(username='demo-socio')
        self.assertEqual(partner_user.default_role_code, 'Socio')
        self.assertEqual(partner_user.metadata['socio_id'], self.socio.id)

        partner_assignment = UserScopeAssignment.objects.get(user=partner_user, effective_to__isnull=True)
        self.assertEqual(partner_assignment.scope.code, f'property-{self.propiedad.id}')

        operator_assignment = UserScopeAssignment.objects.get(
            user__username='demo-operador',
            effective_to__isnull=True,
        )
        self.assertEqual(operator_assignment.scope.code, f'company-{self.empresa.id}')

        reviewer_assignment = UserScopeAssignment.objects.get(
            user__username='demo-revisor',
            effective_to__isnull=True,
        )
        self.assertEqual(reviewer_assignment.scope.code, f'company-{self.empresa.id}')

        self.assertIn('demo-admin', output.getvalue())
        self.assertIn('demo-socio', output.getvalue())
        self.assertIn('password=<no impreso>', output.getvalue())
        self.assertNotIn('demo12345', output.getvalue())

    def test_command_is_idempotent_for_demo_users(self):
        call_command('seed_demo_access')
        call_command('seed_demo_access')

        self.assertEqual(Role.objects.count(), 4)
        self.assertEqual(Scope.objects.count(), 4)
        self.assertEqual(RoleScope.objects.count(), 4)
        self.assertEqual(User.objects.filter(username__startswith='demo-').count(), 4)
        self.assertEqual(UserScopeAssignment.objects.filter(effective_to__isnull=True).count(), 4)
