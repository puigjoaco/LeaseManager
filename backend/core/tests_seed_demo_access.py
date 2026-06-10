from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.management.commands.bootstrap_demo_control_activity import (
    Command as ControlActivityCommand,
)
from core.management.commands.bootstrap_demo_operational_data import (
    Command as OperationalDataCommand,
)
from core.management.commands.bootstrap_demo_public_showcase import (
    Command as PublicShowcaseCommand,
    OperationalMonth,
)
from core.management.commands.bootstrap_demo_tax_annual_flow import (
    Command as TaxAnnualCommand,
)
from core.management.commands.bootstrap_demo_tax_monthly_flow import (
    Command as TaxMonthlyCommand,
)
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

    def test_seed_demo_access_controlled_errors_sanitize_explicit_ids(self):
        missing_id = 991001
        cases = (
            ({'company_id': missing_id}, 'La empresa indicada no existe.'),
            ({'socio_id': missing_id}, 'El socio indicado no existe.'),
            ({'property_id': missing_id}, 'La propiedad indicada no existe.'),
            ({'bank_account_id': missing_id}, 'La cuenta recaudadora indicada no existe.'),
        )

        for kwargs, expected_message in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesMessage(CommandError, expected_message) as context:
                    call_command('seed_demo_access', stdout=StringIO(), **kwargs)

                rendered_error = str(context.exception)
                self.assertNotIn(str(missing_id), rendered_error)

    def test_showcase_access_controlled_errors_sanitize_raw_inputs(self):
        missing_id = 992001

        with self.assertRaisesMessage(CommandError, 'El usuario demo indicado no existe.') as missing_user:
            call_command('bootstrap_demo_showcase_access', username=f'demo-missing-{missing_id}', stdout=StringIO())
        self.assertNotIn(str(missing_id), str(missing_user.exception))
        self.assertNotIn('demo-missing', str(missing_user.exception))

        call_command('seed_demo_access', stdout=StringIO())

        with self.assertRaisesMessage(CommandError, 'El rol indicado no existe.') as missing_role:
            call_command(
                'bootstrap_demo_showcase_access',
                role_code=f'RoleMissing{missing_id}',
                stdout=StringIO(),
            )
        self.assertNotIn(str(missing_id), str(missing_role.exception))
        self.assertNotIn('RoleMissing', str(missing_role.exception))

        with self.assertRaisesMessage(CommandError, 'Una o mas empresas indicadas no existen.') as missing_company:
            call_command(
                'bootstrap_demo_showcase_access',
                company_ids=[self.empresa.id, missing_id],
                stdout=StringIO(),
            )
        rendered_error = str(missing_company.exception)
        self.assertNotIn(str(missing_id), rendered_error)
        self.assertNotIn(str([self.empresa.id, missing_id]), rendered_error)

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

    def test_public_showcase_start_summary_sanitizes_scope_ids(self):
        output = StringIO()
        command = PublicShowcaseCommand(stdout=output)

        command._write_start_summary(
            company_ids=[self.empresa.id, 999],
            months=[OperationalMonth(2026, 4), OperationalMonth(2026, 5)],
            showcase_month=OperationalMonth(2026, 5),
            annual_year=2027,
        )

        rendered_output = output.getvalue()
        self.assertIn('empresas_total=2', rendered_output)
        self.assertIn('meses_operativos_total=2', rendered_output)
        self.assertIn('showcase_month_validado=true', rendered_output)
        self.assertIn('annual_year=2027', rendered_output)
        self.assertNotIn('empresas=', rendered_output)
        self.assertNotIn('company_ids', rendered_output)
        self.assertNotIn(f'[{self.empresa.id}', rendered_output)
        self.assertNotIn('999', rendered_output)
        self.assertNotIn('2026-04', rendered_output)
        self.assertNotIn('2026-05', rendered_output)

    def test_public_showcase_input_errors_sanitize_raw_values(self):
        command = PublicShowcaseCommand()
        missing_id = 994001
        raw_month = '2026-secret-994001'
        raw_uf = '2026-05-01=secret-994001'

        with self.assertRaisesMessage(CommandError, 'Una o mas empresas indicadas no existen.') as missing_company:
            command._resolve_company_ids([self.empresa.id, missing_id])
        self.assertNotIn(str(missing_id), str(missing_company.exception))
        self.assertNotIn(str([self.empresa.id, missing_id]), str(missing_company.exception))

        with self.assertRaisesMessage(CommandError, 'El socio indicado no existe.') as missing_socio:
            command._resolve_socio_id(missing_id)
        self.assertNotIn(str(missing_id), str(missing_socio.exception))

        with self.assertRaisesMessage(CommandError, 'Mes invalido. Usa YYYY-MM.') as invalid_month:
            command._parse_month(raw_month)
        self.assertNotIn(raw_month, str(invalid_month.exception))

        with self.assertRaisesMessage(CommandError, 'Mes invalido. Usa YYYY-MM.') as invalid_month_range:
            command._parse_month('2026-13')
        self.assertNotIn('2026-13', str(invalid_month_range.exception))

        with self.assertRaisesMessage(CommandError, 'UF invalido. Usa YYYY-MM-DD=VALOR.') as invalid_uf:
            command._build_uf_values([OperationalMonth(2026, 5)], [raw_uf])
        self.assertNotIn(raw_uf, str(invalid_uf.exception))
        self.assertNotIn('secret-994001', str(invalid_uf.exception))

        with self.assertRaisesMessage(CommandError, 'Faltan valores UF para uno o mas meses.') as missing_uf:
            command._build_uf_values([OperationalMonth(2026, 6)], [])
        self.assertNotIn('2026-06-01', str(missing_uf.exception))

    def test_operational_data_input_errors_sanitize_raw_values(self):
        command = OperationalDataCommand()
        raw_month = '2026-secret-995001'
        raw_uf = '2026-05-01=secret-995001'

        with self.assertRaisesMessage(CommandError, 'Mes invalido. Usa YYYY-MM.') as invalid_month:
            command._parse_months([raw_month])
        self.assertNotIn(raw_month, str(invalid_month.exception))

        with self.assertRaisesMessage(CommandError, 'Mes invalido. Usa YYYY-MM.') as invalid_month_range:
            command._parse_months(['2026-13'])
        self.assertNotIn('2026-13', str(invalid_month_range.exception))

        with self.assertRaisesMessage(CommandError, 'UF invalido. Usa YYYY-MM-DD=VALOR.') as invalid_uf_shape:
            command._parse_uf_values(['secret-995001'])
        self.assertNotIn('secret-995001', str(invalid_uf_shape.exception))

        with self.assertRaisesMessage(CommandError, 'Fecha UF invalida. Usa YYYY-MM-DD=VALOR.') as invalid_uf_date:
            command._parse_uf_values(['secret-995001=1'])
        self.assertNotIn('secret-995001', str(invalid_uf_date.exception))

        with self.assertRaisesMessage(CommandError, 'Valor UF invalido. Usa YYYY-MM-DD=VALOR.') as invalid_uf_value:
            command._parse_uf_values([raw_uf])
        self.assertNotIn(raw_uf, str(invalid_uf_value.exception))
        self.assertNotIn('secret-995001', str(invalid_uf_value.exception))

    def test_public_showcase_step_output_does_not_replay_raw_stdout(self):
        output = StringIO()
        command = PublicShowcaseCommand(stdout=output)

        def write_raw_output(*args, **kwargs):
            kwargs['stdout'].write(f'demo-revisor\ncompany_ids=[{self.empresa.id}]\n{self.empresa.razon_social}\n')

        with patch('core.management.commands.bootstrap_demo_public_showcase.call_command', side_effect=write_raw_output):
            succeeded = command._run_step('bootstrap_demo_showcase_access', [], False, company_ids=[self.empresa.id])

        rendered_output = output.getvalue()
        self.assertTrue(succeeded)
        self.assertIn('[ok] bootstrap_demo_showcase_access', rendered_output)
        self.assertIn('salida_lineas=3', rendered_output)
        self.assertIn('stdout_detalle_no_impreso=true', rendered_output)
        self.assertNotIn('demo-revisor', rendered_output)
        self.assertNotIn('company_ids', rendered_output)
        self.assertNotIn(str([self.empresa.id]), rendered_output)
        self.assertNotIn(self.empresa.razon_social, rendered_output)

    def test_public_showcase_warning_output_is_sanitized(self):
        output = StringIO()
        command = PublicShowcaseCommand(stdout=output)
        warnings = []

        def fail_with_raw_output(*args, **kwargs):
            kwargs['stdout'].write(f'Empresa {self.empresa.razon_social}\ncompany_ids=[{self.empresa.id}]\n')
            raise CommandError(f'Empresa inexistente: {self.empresa.id}')

        with patch('core.management.commands.bootstrap_demo_public_showcase.call_command', side_effect=fail_with_raw_output):
            succeeded = command._run_step('bootstrap_demo_showcase_access', warnings, False, company_ids=[self.empresa.id])

        rendered_output = output.getvalue()
        self.assertFalse(succeeded)
        self.assertEqual(warnings, ['bootstrap_demo_showcase_access: fallo_controlado=true'])
        self.assertIn('[warn] bootstrap_demo_showcase_access', rendered_output)
        self.assertIn('detalle_no_impreso=true', rendered_output)
        self.assertIn('salida_lineas=2', rendered_output)
        self.assertNotIn('Empresa inexistente', rendered_output)
        self.assertNotIn('company_ids', rendered_output)
        self.assertNotIn(str([self.empresa.id]), rendered_output)
        self.assertNotIn(self.empresa.razon_social, rendered_output)

    def test_public_showcase_strict_error_is_sanitized(self):
        output = StringIO()
        command = PublicShowcaseCommand(stdout=output)

        def fail_with_raw_output(*args, **kwargs):
            kwargs['stdout'].write(f'demo-revisor\ncompany_ids=[{self.empresa.id}]\n')
            raise CommandError(f'Empresa inexistente: {self.empresa.id}')

        with patch('core.management.commands.bootstrap_demo_public_showcase.call_command', side_effect=fail_with_raw_output):
            with self.assertRaisesMessage(CommandError, 'bootstrap_demo_showcase_access: fallo_controlado=true'):
                command._run_step('bootstrap_demo_showcase_access', [], True, company_ids=[self.empresa.id])

        rendered_output = output.getvalue()
        self.assertNotIn('demo-revisor', rendered_output)
        self.assertNotIn('company_ids', rendered_output)
        self.assertNotIn(str([self.empresa.id]), rendered_output)

    def test_tax_monthly_flow_summary_sanitizes_internal_ids(self):
        output = StringIO()
        command = TaxMonthlyCommand(stdout=output)

        command._write_summary(
            anio=2026,
            mes=5,
            payment=SimpleNamespace(id=991001, estado_pago='pagado'),
            updated_capabilities=2,
            dte_created=True,
            f29_created=False,
            close=SimpleNamespace(id=991002, estado='aprobado'),
            movement=SimpleNamespace(id=991003, estado_conciliacion='conciliado_exacto'),
            match_result='matched_pago_991001',
        )

        rendered_output = output.getvalue()
        self.assertIn('empresa_validada=true', rendered_output)
        self.assertIn('periodo=2026-05', rendered_output)
        self.assertIn('pago_validado=true', rendered_output)
        self.assertIn('dte_disponible=true', rendered_output)
        self.assertIn('f29_disponible=true', rendered_output)
        self.assertIn('cierre_disponible=true', rendered_output)
        self.assertIn('movimiento_bancario_generado=true', rendered_output)
        self.assertNotIn('payment=991001', rendered_output)
        self.assertNotIn('dte=991001', rendered_output)
        self.assertNotIn('f29=991001', rendered_output)
        self.assertNotIn('cierre=991002', rendered_output)
        self.assertNotIn('movimiento=991003', rendered_output)
        self.assertNotIn('matched_pago_991001', rendered_output)

    def test_demo_numeric_and_company_errors_sanitize_raw_values(self):
        raw_value = 'secret-996001'
        missing_id = 996001

        with self.assertRaisesMessage(CommandError, 'Monto invalido. Usa un valor decimal.') as invalid_amount:
            ControlActivityCommand()._parse_amount(raw_value)
        self.assertNotIn(raw_value, str(invalid_amount.exception))

        with self.assertRaisesMessage(CommandError, 'Valor invalido para ppm-rate. Usa un valor decimal.') as invalid_monthly_rate:
            TaxMonthlyCommand()._parse_decimal(raw_value, field_name='ppm-rate')
        self.assertNotIn(raw_value, str(invalid_monthly_rate.exception))

        with self.assertRaisesMessage(CommandError, 'Valor invalido para ppm-rate. Usa un valor decimal.') as invalid_annual_rate:
            TaxAnnualCommand()._parse_decimal(raw_value, field_name='ppm-rate')
        self.assertNotIn(raw_value, str(invalid_annual_rate.exception))

        with self.assertRaisesMessage(CommandError, 'La empresa indicada no existe.') as missing_company:
            call_command('bootstrap_demo_control_baseline', company_id=missing_id, stdout=StringIO())
        self.assertNotIn(str(missing_id), str(missing_company.exception))

    def test_tax_annual_flow_summary_sanitizes_ids_and_ddjj_codes(self):
        output = StringIO()
        command = TaxAnnualCommand(stdout=output)

        command._write_summary(
            anio_tributario=2027,
            fiscal_year=2026,
            prepared_months=12,
            approved_months=12,
            updated_capabilities=2,
            ddjj_codes=('1887', '1943'),
            process=SimpleNamespace(id=992001, estado='preparado'),
            ddjj=SimpleNamespace(id=992002, estado_preparacion='preparado'),
            f22=SimpleNamespace(id=992003, estado_preparacion='preparado'),
        )

        rendered_output = output.getvalue()
        self.assertIn('empresa_validada=true', rendered_output)
        self.assertIn('anio_tributario=2027', rendered_output)
        self.assertIn('ddjj_habilitadas_total=2', rendered_output)
        self.assertIn('proceso_generado=true', rendered_output)
        self.assertIn('ddjj_generada=true', rendered_output)
        self.assertIn('f22_generado=true', rendered_output)
        self.assertNotIn('empresa=', rendered_output)
        self.assertNotIn('ddjj_habilitadas=[', rendered_output)
        self.assertNotIn('1887', rendered_output)
        self.assertNotIn('1943', rendered_output)
        self.assertNotIn('992001', rendered_output)
        self.assertNotIn('992002', rendered_output)
        self.assertNotIn('992003', rendered_output)

    def test_control_activity_summary_sanitizes_ids_and_f29_warning(self):
        output = StringIO()
        command = ControlActivityCommand(stdout=output)
        raw_warning = 'La empresa 993001 no tiene certificado token://secret-demo'

        command._write_summary(
            anio=2026,
            mes=5,
            event=SimpleNamespace(id=993001, estado_contable='contabilizado'),
            event_created=True,
            close=SimpleNamespace(id=993002, estado='aprobado'),
            close_approved=True,
            ensure_demo_sii_refs=True,
            capability_updates=1,
            f29=SimpleNamespace(id=993003, estado_preparacion='preparado'),
            f29_created=True,
            f29_warning=None,
        )

        rendered_output = output.getvalue()
        self.assertIn('empresa_validada=true', rendered_output)
        self.assertIn('periodo=2026-05', rendered_output)
        self.assertIn('evento_generado=true', rendered_output)
        self.assertIn('cierre_disponible=true', rendered_output)
        self.assertIn('f29_disponible=true', rendered_output)
        self.assertNotIn('evento=993001', rendered_output)
        self.assertNotIn('cierre=993002', rendered_output)
        self.assertNotIn('f29=993003', rendered_output)

        warning_output = StringIO()
        warning_command = ControlActivityCommand(stdout=warning_output)
        warning_command._write_summary(
            anio=2026,
            mes=5,
            event=SimpleNamespace(id=993001, estado_contable='contabilizado'),
            event_created=True,
            close=SimpleNamespace(id=993002, estado='aprobado'),
            close_approved=True,
            ensure_demo_sii_refs=False,
            capability_updates=0,
            f29=None,
            f29_created=False,
            f29_warning=raw_warning,
        )

        warning_rendered_output = warning_output.getvalue()
        self.assertIn('f29_no_generado=true', warning_rendered_output)
        self.assertIn('detalle_no_impreso=true', warning_rendered_output)
        self.assertNotIn(raw_warning, warning_rendered_output)
        self.assertNotIn('token://secret-demo', warning_rendered_output)
