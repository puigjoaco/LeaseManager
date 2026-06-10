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

        rendered_output = output.getvalue()
        self.assertIn('Seed de acceso demo aplicado correctamente.', rendered_output)
        self.assertIn('usuario_demo=1', rendered_output)
        self.assertIn('rol=AdministradorGlobal', rendered_output)
        self.assertIn('scope_type=global', rendered_output)
        self.assertIn('scope_type=company', rendered_output)
        self.assertIn('scope_type=property', rendered_output)
        self.assertIn('scope_ref_presente=true', rendered_output)
        self.assertIn('socio_demo_vinculado=true', rendered_output)
        self.assertIn('password=<no impreso>', rendered_output)
        self.assertNotIn('demo12345', rendered_output)
        self.assertNotIn('demo-admin', rendered_output)
        self.assertNotIn('demo-socio', rendered_output)
        self.assertNotIn('global-backoffice', rendered_output)
        self.assertNotIn(f'company-{self.empresa.id}', rendered_output)
        self.assertNotIn(f'property-{self.propiedad.id}', rendered_output)
        self.assertNotIn(str(self.cuenta.numero_cuenta), rendered_output)
        self.assertNotIn(self.socio.nombre, rendered_output)

    def test_command_is_idempotent_for_demo_users(self):
        call_command('seed_demo_access', stdout=StringIO())
        call_command('seed_demo_access', stdout=StringIO())

        self.assertEqual(Role.objects.count(), 4)
        self.assertEqual(Scope.objects.count(), 4)
        self.assertEqual(RoleScope.objects.count(), 4)
        self.assertEqual(User.objects.filter(username__startswith='demo-').count(), 4)
        self.assertEqual(UserScopeAssignment.objects.filter(effective_to__isnull=True).count(), 4)

    def test_showcase_access_command_sanitizes_stdout(self):
        second_company = Empresa.objects.create(
            razon_social='Empresa Showcase Dos',
            rut='76.111.111-1',
            estado='activa',
        )
        call_command(
            'seed_demo_access',
            company_id=self.empresa.id,
            socio_id=self.socio.id,
            property_id=self.propiedad.id,
            bank_account_id=self.cuenta.id,
            stdout=StringIO(),
        )
        output = StringIO()

        call_command(
            'bootstrap_demo_showcase_access',
            company_ids=[self.empresa.id, second_company.id],
            stdout=output,
        )

        reviewer_assignments = UserScopeAssignment.objects.filter(
            user__username='demo-revisor',
            role__code='RevisorFiscalExterno',
            effective_to__isnull=True,
        )
        self.assertEqual(reviewer_assignments.count(), 2)
        self.assertTrue(reviewer_assignments.filter(scope__code=f'company-{self.empresa.id}').exists())
        self.assertTrue(reviewer_assignments.filter(scope__code=f'company-{second_company.id}').exists())

        rendered_output = output.getvalue()
        self.assertIn('Scope de showcase aplicado correctamente.', rendered_output)
        self.assertIn('usuario_demo_validado=true', rendered_output)
        self.assertIn('rol_validado=true', rendered_output)
        self.assertIn('empresas_scope_total=2', rendered_output)
        self.assertIn('asignaciones_creadas=1', rendered_output)
        self.assertIn('asignaciones_reutilizadas=1', rendered_output)
        self.assertNotIn('demo-revisor', rendered_output)
        self.assertNotIn('RevisorFiscalExterno', rendered_output)
        self.assertNotIn('company_ids', rendered_output)
        self.assertNotIn(f'company-{self.empresa.id}', rendered_output)
        self.assertNotIn(f'company-{second_company.id}', rendered_output)
        self.assertNotIn(f'[{self.empresa.id}, {second_company.id}]', rendered_output)
        self.assertNotIn(self.empresa.razon_social, rendered_output)
        self.assertNotIn(second_company.razon_social, rendered_output)
