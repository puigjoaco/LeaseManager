from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PlatformSetting, Role, Scope, UserScopeAssignment
from .permissions import get_effective_role_codes


class PlatformBootstrapAPITests(APITestCase):
    def test_platform_bootstrap_admin_default_role_sees_all_active_scopes(self):
        user = get_user_model().objects.create_user(
            username='platform-bootstrap-admin',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        company_scope = Scope.objects.create(
            code='company-101',
            name='Empresa 101',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='101',
            is_active=True,
        )
        property_scope = Scope.objects.create(
            code='property-202',
            name='Propiedad 202',
            scope_type=Scope.ScopeType.PROPERTY,
            external_reference='202',
            is_active=True,
        )
        Scope.objects.create(
            code='company-303',
            name='Empresa 303',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='303',
            is_active=False,
        )
        self.client.force_authenticate(user)

        response = self.client.get(reverse('platform-bootstrap'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['available_scopes'],
            [
                {'code': company_scope.code, 'name': company_scope.name, 'scope_type': company_scope.scope_type},
                {'code': property_scope.code, 'name': property_scope.name, 'scope_type': property_scope.scope_type},
            ],
        )

    def test_platform_bootstrap_returns_only_effective_roles_and_assigned_active_scopes(self):
        user = get_user_model().objects.create_user(
            username='platform-bootstrap',
            password='secret123',
            default_role_code='Socio',
        )
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        assigned_scope = Scope.objects.create(
            code='company-101',
            name='Empresa 101',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='101',
            is_active=True,
        )
        Scope.objects.create(
            code='company-202',
            name='Empresa 202',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='202',
            is_active=True,
        )
        inactive_scope = Scope.objects.create(
            code='company-303',
            name='Empresa 303',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='303',
            is_active=False,
        )
        UserScopeAssignment.objects.create(user=user, role=reviewer_role, scope=assigned_scope, is_primary=True)
        UserScopeAssignment.objects.create(
            user=user,
            role=reviewer_role,
            scope=inactive_scope,
            is_primary=False,
            effective_to=timezone.now(),
        )
        PlatformSetting.objects.create(key='visible-setting', value={'enabled': True}, is_active=True)
        PlatformSetting.objects.create(key='inactive-setting', value={'enabled': False}, is_active=False)
        self.client.force_authenticate(user)

        response = self.client.get(reverse('platform-bootstrap'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data['available_roles']), {'Socio', 'RevisorFiscalExterno'})
        self.assertEqual(
            response.data['available_scopes'],
            [{'code': assigned_scope.code, 'name': assigned_scope.name, 'scope_type': assigned_scope.scope_type}],
        )
        self.assertEqual(response.data['settings_count'], 1)


class EffectiveRoleUtilityTests(TestCase):
    def test_get_effective_role_codes_includes_active_assignments(self):
        user = get_user_model().objects.create_user(
            username='effective-roles',
            password='secret123',
            default_role_code='Socio',
        )
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        UserScopeAssignment.objects.create(user=user, role=reviewer_role, scope=None, is_primary=True)

        self.assertEqual(get_effective_role_codes(user), {'Socio', 'RevisorFiscalExterno'})
