from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase

from contabilidad.models import ConfiguracionFiscalEmpresa, RegimenTributarioEmpresa
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio
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

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('control', response.data['bootstrap'])
        self.assertEqual(len(response.data['bootstrap']['control']['configuraciones_fiscales']), 1)
        self.assertEqual(response.data['bootstrap']['control']['eventos_contables'], [])

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
    def test_demo_login_response_cache_skips_repeated_user_lookup(self):
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

        with patch('users.views.get_demo_login_user', side_effect=AssertionError('cached demo login should not hit user lookup')):
            response_two = self.client.post(
                reverse('login'),
                {'username': 'demo-admin', 'password': 'demo12345'},
                format='json',
            )

        self.assertEqual(response_one.status_code, status.HTTP_200_OK)
        self.assertEqual(response_two.status_code, status.HTTP_200_OK)

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
