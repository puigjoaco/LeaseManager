from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import PlatformSetting, Role, Scope, UserScopeAssignment
from .permissions import get_effective_role_codes
from .reference_validation import (
    REDACTED_SENSITIVE_REFERENCE,
    contains_sensitive_reference,
    redact_sensitive_payload,
    redact_sensitive_payload_values,
)


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


class ReferenceValidationTests(TestCase):
    def test_redact_sensitive_payload_recurses_values_and_sensitive_keys(self):
        payload = {
            'safe_ref': 'controlled-reference',
            'callback': 'https://provider.example.test/token/value',
            'access_token': 'opaque-value',
            'nested': [
                {'api_key': 'opaque-key'},
                {'result_ref': 'controlled-result'},
            ],
            'count': 2,
            'empty': None,
        }

        redacted = redact_sensitive_payload(payload)

        self.assertEqual(redacted['safe_ref'], 'controlled-reference')
        self.assertEqual(redacted['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(redacted['access_token'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(redacted['nested'][0]['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(redacted['nested'][1]['result_ref'], 'controlled-result')
        self.assertEqual(redacted['count'], 2)
        self.assertIsNone(redacted['empty'])

    def test_redact_sensitive_payload_values_preserves_operational_reference_keys(self):
        payload = {
            'credencial_validada_ref': 'email-ref-validado-v1',
            'callback_ref': 'https://provider.example.test/token/value',
            'nested': [{'oauth_validado_ref': 'oauth-ref-v1'}, {'headers': 'Bearer inherited-value'}],
        }

        redacted = redact_sensitive_payload_values(payload)

        self.assertEqual(redacted['credencial_validada_ref'], 'email-ref-validado-v1')
        self.assertEqual(redacted['callback_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(redacted['nested'][0]['oauth_validado_ref'], 'oauth-ref-v1')
        self.assertEqual(redacted['nested'][1]['headers'], REDACTED_SENSITIVE_REFERENCE)

    def test_contains_sensitive_reference_can_include_sensitive_keys(self):
        payload = {'access_token': 'opaque-value', 'safe_ref': 'controlled-reference'}

        self.assertFalse(contains_sensitive_reference(payload))
        self.assertTrue(contains_sensitive_reference(payload, include_sensitive_keys=True))
        self.assertTrue(contains_sensitive_reference({'api_key': None}, include_sensitive_keys=True))

    def test_contains_sensitive_reference_allows_canonical_reference_keys(self):
        payload = {
            'credencial_validada_ref': 'email-proof-v1',
            'nested': {'api_key': 'opaque-value'},
        }

        self.assertTrue(
            contains_sensitive_reference(
                payload,
                include_sensitive_keys=True,
                allowed_sensitive_keys=('credencial_validada_ref',),
            )
        )
        self.assertFalse(
            contains_sensitive_reference(
                {'credencial_validada_ref': 'email-proof-v1'},
                include_sensitive_keys=True,
                allowed_sensitive_keys=('credencial_validada_ref',),
            )
        )
