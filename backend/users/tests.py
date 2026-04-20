from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase

from contabilidad.models import ConfiguracionFiscalEmpresa, CuentaContable, EventoContable, RegimenTributarioEmpresa
from core.models import Role, Scope, UserScopeAssignment
from conciliacion.models import ConexionBancaria, MovimientoBancarioImportado
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio
from audit.models import ManualResolution
from reporting.services import build_manual_resolution_summary


class UserAuthAPITests(APITestCase):
    def setUp(self):
        cache.clear()

    def _create_active_company(self, *, nombre='AuthCo', rut='76000111-1'):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=f'{rut[:-2]}1-1', activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=f'{rut[:-2]}2-2', activo=True)
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

    def _assign_company_scope(self, user, empresa, *, role_code, is_primary=True):
        role, _ = Role.objects.get_or_create(code=role_code, defaults={'name': role_code})
        scope, _ = Scope.objects.get_or_create(
            code=f'company-{empresa.id}',
            defaults={
                'name': f'Empresa {empresa.razon_social}',
                'scope_type': Scope.ScopeType.COMPANY,
                'external_reference': str(empresa.id),
                'is_active': True,
            },
        )
        return UserScopeAssignment.objects.create(user=user, role=role, scope=scope, is_primary=is_primary)

    def _create_company_properties(self, empresa, *, prefix, count):
        properties = []
        for index in range(count):
            properties.append(
                Propiedad.objects.create(
                    codigo_propiedad=f'{prefix}-{index + 1:02d}',
                    direccion=f'Av. {prefix} {index + 1}',
                    comuna='Santiago',
                    region='RM',
                    tipo_inmueble='local',
                    estado='activa',
                    empresa_owner=empresa,
                )
            )
        return properties

    def _create_cuenta_contable(self, empresa, *, codigo='1101', nombre='Bancos'):
        return CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1-default',
            codigo=codigo,
            nombre=nombre,
            naturaleza='deudora',
            nivel=1,
            estado='activa',
        )

    def _create_evento_contable(self, empresa, *, idempotency_key='auth-event-1'):
        return EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='pago_mensual',
            entidad_origen_id='1',
            fecha_operativa='2026-01-15',
            moneda='CLP',
            monto_base=Decimal('100000.00'),
            payload_resumen={},
            idempotency_key=idempotency_key,
            estado_contable='pendiente_contabilizacion',
        )

    def _create_scoped_manual_resolution_for_company(self, empresa, *, suffix='manual'):
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{suffix}-{empresa.id}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref=f'cred-{suffix}-{empresa.id}',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='cargo',
            monto='45000.00',
            descripcion_origen=f'Movimiento {suffix}',
            estado_conciliacion='pendiente_revision',
        )
        return ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.id),
            summary=f'Movimiento {suffix} requiere clasificacion manual',
        )

    def test_login_returns_overview_bootstrap_for_admin(self):
        user = get_user_model().objects.create_user(
            username='admin-bootstrap',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('overview', response.data['bootstrap'])
        self.assertIn('dashboard', response.data['bootstrap']['overview'])
        self.assertNotIn('manual_summary', response.data['bootstrap']['overview'])
        self.assertNotIn('socios_total', response.data['bootstrap']['overview']['dashboard'])
        self.assertNotIn('control', response.data['bootstrap'])

    def test_login_includes_cached_manual_summary_when_available(self):
        user = get_user_model().objects.create_user(
            username='admin-bootstrap-cached',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        ManualResolution.objects.create(
            category='ops.retry_needed',
            scope_type='demo',
            scope_reference='demo-1',
            summary='Retry manual necesario',
        )
        build_manual_resolution_summary(status='open', use_cache=True)

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('manual_summary', response.data['bootstrap']['overview'])
        self.assertEqual(response.data['bootstrap']['overview']['manual_summary']['total'], 1)

    def test_scoped_operator_login_does_not_receive_global_manual_summary(self):
        user = get_user_model().objects.create_user(
            username='operator-bootstrap-scoped',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        scope = Scope.objects.create(
            code='company-999',
            name='Empresa Scope',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='999',
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=user, role=operator_role, scope=scope, is_primary=True)
        ManualResolution.objects.create(
            category='ops.retry_needed',
            scope_type='demo',
            scope_reference='demo-1',
            summary='Retry manual necesario',
        )
        build_manual_resolution_summary(status='open', use_cache=True)

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bootstrap']['overview']['manual_summary']['total'], 0)

    def test_scoped_operator_login_includes_only_in_scope_manual_summary(self):
        user = get_user_model().objects.create_user(
            username='operator-bootstrap-scoped-visible',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        assigned_company = self._create_active_company(nombre='ScopedAssignedCo', rut='76000115-5')
        other_company = self._create_active_company(nombre='ScopedOtherCo', rut='76000116-6')
        self._assign_company_scope(user, assigned_company, role_code='OperadorDeCartera', is_primary=True)
        self._create_scoped_manual_resolution_for_company(assigned_company, suffix='assigned')
        self._create_scoped_manual_resolution_for_company(other_company, suffix='other')

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['bootstrap']['overview']['manual_summary']['total'], 1)
        self.assertEqual(
            response.data['bootstrap']['overview']['manual_summary']['categorias'],
            [{'category': 'conciliacion.movimiento_cargo', 'total': 1}],
        )

    def test_login_returns_control_bootstrap_for_reviewer(self):
        user = get_user_model().objects.create_user(
            username='reviewer-bootstrap',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        empresa = self._create_active_company(nombre='ReviewerAuthCo', rut='76000112-2')
        regimen, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regimen,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )
        self._create_cuenta_contable(empresa)
        self._create_evento_contable(empresa)

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('control', response.data['bootstrap'])
        self.assertEqual(len(response.data['bootstrap']['control']['configuraciones_fiscales']), 1)
        self.assertEqual(len(response.data['bootstrap']['control']['cuentas_contables']), 1)
        self.assertEqual(response.data['bootstrap']['control']['eventos_contables'], [])

    def test_login_bootstrap_merges_multiple_assignment_roles(self):
        user = get_user_model().objects.create_user(
            username='multi-role-bootstrap',
            password='secret123',
            default_role_code='Socio',
        )
        empresa = self._create_active_company(nombre='ScopedMultiRoleCo', rut='76000119-9')
        self._assign_company_scope(user, empresa, role_code='OperadorDeCartera', is_primary=True)
        self._assign_company_scope(user, empresa, role_code='RevisorFiscalExterno', is_primary=False)

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('overview', response.data['bootstrap'])
        self.assertIn('control', response.data['bootstrap'])

    @override_settings(DEMO_LOGIN_USERS={'demo-revisor'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_reviewer_login_returns_full_control_bootstrap(self):
        user = get_user_model().objects.create_user(
            username='demo-revisor',
            password='another-secret',
            default_role_code='RevisorFiscalExterno',
        )
        empresa = self._create_active_company(nombre='DemoReviewerAuthCo', rut='76000113-3')
        regimen, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regimen,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )
        self._create_cuenta_contable(empresa)
        self._create_evento_contable(empresa, idempotency_key='demo-reviewer-event-1')

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'demo12345'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('control', response.data['bootstrap'])
        self.assertEqual(len(response.data['bootstrap']['control']['cuentas_contables']), 1)
        self.assertEqual(len(response.data['bootstrap']['control']['eventos_contables']), 1)

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_login_short_circuit_works_for_configured_demo_user(self):
        user = get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['username'], user.username)

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_admin_login_builds_manual_summary_without_prior_cache(self):
        get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )
        empresa = self._create_active_company(nombre='DemoAdminAuthCo', rut='76000114-4')
        regimen, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regimen,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )
        self._create_cuenta_contable(empresa)
        self._create_evento_contable(empresa, idempotency_key='demo-admin-event-1')
        ManualResolution.objects.create(
            category='ops.retry_needed',
            scope_type='demo',
            scope_reference='demo-1',
            summary='Retry manual necesario',
        )

        response = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('overview', response.data['bootstrap'])
        self.assertIn('manual_summary', response.data['bootstrap']['overview'])
        self.assertEqual(response.data['bootstrap']['overview']['manual_summary']['total'], 1)
        self.assertEqual(response.data['bootstrap']['overview']['dashboard']['socios_total'], 2)
        self.assertEqual(response.data['bootstrap']['overview']['dashboard']['empresas_total'], 1)
        self.assertIn('control', response.data['bootstrap'])
        self.assertEqual(len(response.data['bootstrap']['control']['cuentas_contables']), 1)
        self.assertEqual(len(response.data['bootstrap']['control']['eventos_contables']), 1)

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_login_bootstrap_uses_short_cache(self):
        get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )

        with patch('users.views.build_operational_dashboard', wraps=lambda **kwargs: {'propiedades_activas': 0}) as mocked_dashboard:
            response_one = self.client.post(
                reverse('login'),
                {'username': 'demo-admin', 'password': 'demo12345'},
                format='json',
            )
            response_two = self.client.post(
                reverse('login'),
                {'username': 'demo-admin', 'password': 'demo12345'},
                format='json',
            )

        self.assertEqual(response_one.status_code, status.HTTP_200_OK)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)
        self.assertEqual(mocked_dashboard.call_count, 1)

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_login_response_cache_skips_repeated_token_and_audit_work(self):
        user = get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )

        with patch.object(Token.objects, 'get_or_create', wraps=Token.objects.get_or_create) as mocked_get_or_create:
            with patch('users.views.create_audit_event') as mocked_audit:
                response_one = self.client.post(
                    reverse('login'),
                    {'username': 'demo-admin', 'password': 'demo12345'},
                    format='json',
                )
                response_two = self.client.post(
                    reverse('login'),
                    {'username': 'demo-admin', 'password': 'demo12345'},
                    format='json',
                )

        self.assertEqual(response_one.status_code, status.HTTP_200_OK)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)
        self.assertEqual(response_one.data['user']['username'], user.username)
        self.assertEqual(response_two.data['user']['username'], user.username)
        self.assertEqual(mocked_get_or_create.call_count, 1)
        self.assertEqual(mocked_audit.call_count, 0)

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_login_response_cache_is_invalidated_when_user_signature_changes(self):
        get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )

        response_one = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )

        user = get_user_model().objects.get(username='demo-admin')
        user.default_role_code = 'RevisorFiscalExterno'
        user.save(update_fields=['default_role_code'])

        response_two = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )

        self.assertEqual(response_one.status_code, status.HTTP_200_OK)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)
        self.assertIn('control', response_two.data['bootstrap'])

    @override_settings(DEMO_LOGIN_USERS={'demo-operator'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_login_response_cache_is_invalidated_when_scope_assignment_changes(self):
        user = get_user_model().objects.create_user(
            username='demo-operator',
            password='another-secret',
            default_role_code='OperadorDeCartera',
        )
        empresa_a = self._create_active_company(nombre='DemoScopeA', rut='76000120-0')
        empresa_b = self._create_active_company(nombre='DemoScopeB', rut='76000121-1')
        self._create_company_properties(empresa_a, prefix='SCOPEA', count=1)
        self._create_company_properties(empresa_b, prefix='SCOPEB', count=2)

        assignment = self._assign_company_scope(user, empresa_a, role_code='OperadorDeCartera', is_primary=True)

        first_response = self.client.post(
            reverse('login'),
            {'username': 'demo-operator', 'password': 'demo12345'},
            format='json',
        )

        assignment.effective_to = timezone.now()
        assignment.save(update_fields=['effective_to'])
        self._assign_company_scope(user, empresa_b, role_code='OperadorDeCartera', is_primary=True)

        second_response = self.client.post(
            reverse('login'),
            {'username': 'demo-operator', 'password': 'demo12345'},
            format='json',
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(first_response.data['bootstrap']['overview']['dashboard']['propiedades_activas'], 1)
        self.assertEqual(second_response.data['bootstrap']['overview']['dashboard']['propiedades_activas'], 2)
        self.assertEqual(
            {assignment['scope'] for assignment in second_response.data['user']['assignments']},
            {f'company-{empresa_b.id}'},
        )

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_login_cache_is_invalidated_by_logout(self):
        user = get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )

        first_login = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )
        self.assertEqual(first_login.status_code, status.HTTP_200_OK)
        first_token = first_login.data['token']

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {first_token}')
        logout = self.client.post(reverse('logout'))
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        self.client.credentials()

        second_login = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )
        self.assertEqual(second_login.status_code, status.HTTP_200_OK)
        self.assertEqual(second_login.data['user']['username'], user.username)
        self.assertNotEqual(second_login.data['token'], first_token)

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_login_cache_is_invalidated_when_token_is_deleted_outside_logout(self):
        user = get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )

        first_login = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )
        self.assertEqual(first_login.status_code, status.HTTP_200_OK)
        first_token = first_login.data['token']

        Token.objects.filter(user=user).delete()

        second_login = self.client.post(
            reverse('login'),
            {'username': 'demo-admin', 'password': 'demo12345'},
            format='json',
        )

        self.assertEqual(second_login.status_code, status.HTTP_200_OK)
        self.assertNotEqual(second_login.data['token'], first_token)
        self.assertTrue(Token.objects.filter(user=user, key=second_login.data['token']).exists())

    @override_settings(DEMO_LOGIN_USERS={'demo-admin', 'demo-revisor'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_warmup_builds_cached_demo_login_payloads(self):
        get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )
        get_user_model().objects.create_user(
            username='demo-revisor',
            password='another-secret',
            default_role_code='RevisorFiscalExterno',
        )

        response = self.client.post(reverse('demo-warmup'))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNotNone(cache.get('auth:demo-login-response:username=demo-admin'))
        self.assertIsNotNone(cache.get('auth:demo-login-response:username=demo-revisor'))

    @override_settings(DEMO_LOGIN_USERS={'demo-admin'}, DEMO_LOGIN_PASSWORD='demo12345')
    def test_demo_warmup_primes_admin_manual_summary_when_backlog_exists(self):
        get_user_model().objects.create_user(
            username='demo-admin',
            password='another-secret',
            default_role_code='AdministradorGlobal',
        )
        ManualResolution.objects.create(
            category='ops.retry_needed',
            scope_type='demo',
            scope_reference='demo-1',
            summary='Retry manual necesario',
        )

        response = self.client.post(reverse('demo-warmup'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        payload = cache.get('auth:demo-login-response:username=demo-admin')
        self.assertIsNotNone(payload)
        self.assertEqual(payload['bootstrap']['overview']['manual_summary']['total'], 1)
