import json
from datetime import timedelta

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .admin import (
    OperationalRuntimeSignalAdmin,
    PlatformSettingAdmin,
    RoleAdmin,
    RoleScopeAdmin,
    ScopeAdmin,
    UserScopeAssignmentAdmin,
)
from .admin_security_control import ADMIN_SECURITY_SETTING_KEY
from .models import (
    OperationalRuntimeSignal,
    PlatformSetting,
    Role,
    RoleScope,
    RuntimeSignalKey,
    RuntimeSignalSourceKind,
    RuntimeSignalStatus,
    Scope,
    UserScopeAssignment,
)
from .permissions import get_effective_role_codes
from .reference_validation import (
    REDACTED_SENSITIVE_REFERENCE,
    contains_chilean_rut_reference,
    contains_local_absolute_path_reference,
    contains_sensitive_reference,
    count_chilean_rut_references,
    is_non_sensitive_control_reference,
    redact_sensitive_control_payload,
    redact_sensitive_control_reference,
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


class CoreAdminRedactionTests(TestCase):
    def test_core_admin_redacts_sensitive_platform_payloads_and_runtime_refs(self):
        user = get_user_model().objects.create_user(username='core-admin-redaction', password='secret123')
        scope = Scope.objects.create(
            code='scope-sensitive',
            name='Scope sensible',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='https://scope.example.test/company?token=secret',
            metadata={
                'safe_ref': 'controlled-scope',
                'callback_url': 'https://scope.example.test/callback?token=secret',
                'headers': {'authorization': 'Bearer inherited-value'},
            },
        )
        role = Role.objects.create(code='OperadorSeguro', name='Operador seguro')
        role_scope = RoleScope.objects.create(
            role=role,
            scope=scope,
            permission_set=[
                {'code': 'read'},
                {'api_key': 'opaque-key-value'},
            ],
        )
        assignment = UserScopeAssignment.objects.create(
            user=user,
            role=role,
            scope=scope,
            metadata={
                'safe_ref': 'controlled-assignment',
                'callback': 'https://assignment.example.test/callback?token=secret',
            },
        )
        setting = PlatformSetting.objects.create(
            key='provider-runtime',
            value={'safe_ref': 'controlled-setting', 'access_token': 'opaque-token-value'},
            description='Setting de proveedor',
            is_secret_reference=True,
        )
        signal = OperationalRuntimeSignal.objects.create(
            signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
            status=RuntimeSignalStatus.OK,
            source_kind=RuntimeSignalSourceKind.REAL_AUTORIZADO,
            value={'healthy': True, 'callback': 'https://runtime.example.test/hook?token=secret'},
            evidence_ref='https://runtime.example.test/evidence?token=secret',
            source_label='source-token-value',
            authorization_ref='Bearer inherited-authorization',
            notes='Nota heredada con https://runtime.example.test/note?token=secret',
        )

        site = AdminSite()
        scope_admin = ScopeAdmin(Scope, site)
        role_admin = RoleAdmin(Role, site)
        role_scope_admin = RoleScopeAdmin(RoleScope, site)
        assignment_admin = UserScopeAssignmentAdmin(UserScopeAssignment, site)
        setting_admin = PlatformSettingAdmin(PlatformSetting, site)
        signal_admin = OperationalRuntimeSignalAdmin(OperationalRuntimeSignal, site)

        for raw_field in ('external_reference', 'metadata'):
            self.assertNotIn(raw_field, scope_admin.fields)
            self.assertNotIn(raw_field, scope_admin.search_fields)
        self.assertNotIn('permission_set', role_scope_admin.fields)
        self.assertNotIn('metadata', assignment_admin.fields)
        self.assertNotIn('value', setting_admin.fields)
        for raw_field in ('value', 'evidence_ref', 'source_label', 'authorization_ref', 'notes'):
            self.assertNotIn(raw_field, signal_admin.fields)
            self.assertNotIn(raw_field, signal_admin.search_fields)

        self.assertFalse(scope_admin.has_delete_permission(None, scope))
        self.assertFalse(role_admin.has_delete_permission(None, role))
        self.assertFalse(role_scope_admin.has_delete_permission(None, role_scope))
        self.assertFalse(assignment_admin.has_delete_permission(None, assignment))
        self.assertFalse(setting_admin.has_add_permission(None))
        self.assertFalse(setting_admin.has_delete_permission(None, setting))
        self.assertFalse(signal_admin.has_add_permission(None))
        self.assertFalse(signal_admin.has_change_permission(None, signal))
        self.assertFalse(signal_admin.has_delete_permission(None, signal))

        self.assertEqual(scope_admin.external_reference_redacted(scope), REDACTED_SENSITIVE_REFERENCE)
        scope_metadata = json.loads(scope_admin.metadata_redacted(scope))
        self.assertEqual(scope_metadata['safe_ref'], 'controlled-scope')
        self.assertEqual(scope_metadata['callback_url'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(scope_metadata['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)

        permission_set = json.loads(role_scope_admin.permission_set_redacted(role_scope))
        self.assertEqual(permission_set[0]['code'], 'read')
        self.assertEqual(permission_set[1]['api_key'], REDACTED_SENSITIVE_REFERENCE)

        assignment_metadata = json.loads(assignment_admin.metadata_redacted(assignment))
        self.assertEqual(assignment_metadata['safe_ref'], 'controlled-assignment')
        self.assertEqual(assignment_metadata['callback'], REDACTED_SENSITIVE_REFERENCE)

        setting_value = json.loads(setting_admin.value_redacted(setting))
        self.assertEqual(setting_value['safe_ref'], 'controlled-setting')
        self.assertEqual(setting_value['access_token'], REDACTED_SENSITIVE_REFERENCE)

        signal_value = json.loads(signal_admin.value_redacted(signal))
        self.assertTrue(signal_value['healthy'])
        self.assertEqual(signal_value['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(signal_admin.evidence_ref_redacted(signal), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(signal_admin.source_label_redacted(signal), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(signal_admin.authorization_ref_redacted(signal), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(signal_admin.notes_redacted(signal), REDACTED_SENSITIVE_REFERENCE)


class PlatformSettingValidationTests(TestCase):
    def test_admin_security_setting_accepts_mfa_control(self):
        setting = PlatformSetting(
            key=ADMIN_SECURITY_SETTING_KEY,
            value={
                'mode': 'mfa_enforced',
                'mfa_enforced': True,
                'mfa_evidence_ref': 'admin-mfa-controlled-v1',
                'authorization_ref': 'stage7-admin-security-authorization-v1',
                'responsible_ref': 'security-owner-v1',
            },
        )

        setting.full_clean()

    def test_admin_security_setting_normalizes_refs_before_full_clean_and_save(self):
        setting = PlatformSetting(
            key=ADMIN_SECURITY_SETTING_KEY,
            description='  Control MFA validado  ',
            value={
                'mode': ' mfa_enforced ',
                'mfa_enforced': True,
                'mfa_evidence_ref': '  admin-mfa-controlled-v1  ',
                'authorization_ref': '  stage7-admin-security-authorization-v1  ',
                'responsible_ref': '  security-owner-v1  ',
            },
        )

        setting.full_clean()
        self.assertEqual(setting.description, 'Control MFA validado')
        self.assertEqual(setting.value['mode'], 'mfa_enforced')
        self.assertEqual(setting.value['mfa_evidence_ref'], 'admin-mfa-controlled-v1')
        self.assertEqual(setting.value['authorization_ref'], 'stage7-admin-security-authorization-v1')
        self.assertEqual(setting.value['responsible_ref'], 'security-owner-v1')

        setting.save()
        stored = PlatformSetting.objects.get(key=ADMIN_SECURITY_SETTING_KEY)
        self.assertEqual(stored.description, 'Control MFA validado')
        self.assertEqual(stored.value['mode'], 'mfa_enforced')
        self.assertEqual(stored.value['mfa_evidence_ref'], 'admin-mfa-controlled-v1')
        self.assertEqual(stored.value['authorization_ref'], 'stage7-admin-security-authorization-v1')
        self.assertEqual(stored.value['responsible_ref'], 'security-owner-v1')

    def test_admin_security_setting_accepts_current_risk_acceptance(self):
        setting = PlatformSetting(
            key=ADMIN_SECURITY_SETTING_KEY,
            value={
                'mode': 'risk_accepted',
                'risk_accepted': True,
                'risk_acceptance_ref': 'admin-mfa-risk-acceptance-v1',
                'authorization_ref': 'stage7-admin-security-authorization-v1',
                'responsible_ref': 'security-owner-v1',
                'valid_until': (timezone.localdate() + timedelta(days=30)).isoformat(),
            },
        )

        setting.full_clean()

    def test_admin_security_setting_rejects_missing_mode_or_refs(self):
        setting = PlatformSetting(
            key=ADMIN_SECURITY_SETTING_KEY,
            value={
                'mode': 'mfa_enforced',
                'mfa_enforced': True,
                'mfa_evidence_ref': '',
                'authorization_ref': '',
                'responsible_ref': 'security-owner-v1',
            },
        )

        with self.assertRaises(ValidationError) as context:
            setting.full_clean()

        self.assertIn('value', context.exception.message_dict)
        rendered = ' '.join(context.exception.message_dict['value'])
        self.assertIn('MFA administrativo requiere evidencia_ref no sensible.', rendered)
        self.assertIn('MFA administrativo requiere authorization_ref no sensible.', rendered)

    def test_admin_security_setting_rejects_sensitive_or_expired_payload(self):
        setting = PlatformSetting(
            key=ADMIN_SECURITY_SETTING_KEY,
            value={
                'mode': 'risk_accepted',
                'risk_accepted': True,
                'risk_acceptance_ref': 'https://security.example.test/acceptance?token=secret',
                'authorization_ref': 'stage7-admin-security-authorization-v1',
                'responsible_ref': 'security-owner-v1',
                'valid_until': (timezone.localdate() + timedelta(days=30)).isoformat(),
            },
        )

        with self.assertRaises(ValidationError) as context:
            setting.full_clean()

        self.assertIn('value', context.exception.message_dict)
        self.assertIn(
            'El control de seguridad administrativa contiene payload sensible.',
            context.exception.message_dict['value'],
        )

        setting.value = {
            'mode': 'risk_accepted',
            'risk_accepted': True,
            'risk_acceptance_ref': 'admin-mfa-risk-acceptance-v1',
            'authorization_ref': 'stage7-admin-security-authorization-v1',
            'responsible_ref': 'security-owner-v1',
            'valid_until': (timezone.localdate() - timedelta(days=1)).isoformat(),
        }

        with self.assertRaises(ValidationError) as context:
            setting.full_clean()

        self.assertIn('value', context.exception.message_dict)
        self.assertIn(
            'La aceptacion formal de riesgo MFA esta vencida.',
            context.exception.message_dict['value'],
        )

    def test_admin_security_setting_rejects_sensitive_description(self):
        setting = PlatformSetting(
            key=ADMIN_SECURITY_SETTING_KEY,
            description='Evidencia en https://security.example.test/mfa?token=secret',
            value={
                'mode': 'mfa_enforced',
                'mfa_enforced': True,
                'mfa_evidence_ref': 'admin-mfa-controlled-v1',
                'authorization_ref': 'stage7-admin-security-authorization-v1',
                'responsible_ref': 'security-owner-v1',
            },
        )

        with self.assertRaises(ValidationError) as context:
            setting.full_clean()

        self.assertIn('description', context.exception.message_dict)
        self.assertIn(
            'La descripcion del control administrativo debe ser no sensible.',
            context.exception.message_dict['description'],
        )


class ReferenceValidationTests(TestCase):
    def test_chilean_rut_reference_detector_counts_prefixed_values(self):
        value = 'source_11.111.111-1 participant_22222222-2 invalid-123'

        self.assertTrue(contains_chilean_rut_reference(value))
        self.assertEqual(count_chilean_rut_references(value), 2)
        self.assertFalse(contains_chilean_rut_reference('source-without-rut'))

    def test_local_absolute_path_detector_covers_windows_and_unc_paths(self):
        self.assertTrue(contains_local_absolute_path_reference('D:/Privado/socio.pdf'))
        self.assertTrue(contains_local_absolute_path_reference('source_C:/Privado/socio.pdf'))
        self.assertTrue(contains_local_absolute_path_reference(r'\\server\share\socio.pdf'))
        self.assertFalse(contains_local_absolute_path_reference('controlled-reference:C'))

    def test_control_reference_rejects_sensitive_rut_and_local_path_values(self):
        self.assertTrue(is_non_sensitive_control_reference('controlled-reference-at2026'))
        self.assertFalse(is_non_sensitive_control_reference('https://example.test/ref?token=secret'))
        self.assertFalse(is_non_sensitive_control_reference('source_11.111.111-1'))
        self.assertFalse(is_non_sensitive_control_reference('source_C:/Privado/socio.pdf'))

    def test_control_redaction_covers_rut_local_paths_and_payloads(self):
        self.assertEqual(redact_sensitive_control_reference('controlled-reference'), 'controlled-reference')
        self.assertEqual(redact_sensitive_control_reference('source_11.111.111-1'), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(redact_sensitive_control_reference('source_C:/Privado/socio.pdf'), REDACTED_SENSITIVE_REFERENCE)

        payload = {
            'safe_ref': 'controlled-reference',
            'rut_ref': 'participant_22.222.222-2',
            'path_ref': 'source_C:/Privado/socio.pdf',
            'nested': [{'authorization': 'opaque-header-value'}],
        }

        self.assertEqual(
            redact_sensitive_control_payload(payload),
            {
                'safe_ref': 'controlled-reference',
                'rut_ref': REDACTED_SENSITIVE_REFERENCE,
                'path_ref': REDACTED_SENSITIVE_REFERENCE,
                'nested': [{'authorization': REDACTED_SENSITIVE_REFERENCE}],
            },
        )

    def test_redact_sensitive_payload_recurses_values_and_sensitive_keys(self):
        payload = {
            'safe_ref': 'controlled-reference',
            'callback': 'https://provider.example.test/token/value',
            'access_token': 'opaque-value',
            'headers': {'authorization': 'opaque-header-value'},
            'private_key': 'opaque-private-key-value',
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
        self.assertEqual(redacted['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(redacted['private_key'], REDACTED_SENSITIVE_REFERENCE)
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
        self.assertTrue(contains_sensitive_reference({'authorization': 'opaque-value'}, include_sensitive_keys=True))
        self.assertTrue(contains_sensitive_reference({'private-key': None}, include_sensitive_keys=True))
        self.assertFalse(contains_sensitive_reference('stage2-authorization-v1', include_sensitive_keys=True))

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

    def test_runtime_signal_rejects_opaque_authorization_or_private_key_metadata(self):
        for payload in (
            {'healthy': True, 'authorization': 'opaque-runtime-header'},
            {'healthy': True, 'private_key': 'opaque-private-key'},
        ):
            signal = OperationalRuntimeSignal(
                signal_key=RuntimeSignalKey.QUEUE_RUNTIME,
                status=RuntimeSignalStatus.OK,
                source_kind=RuntimeSignalSourceKind.LOCAL,
                value=payload,
                evidence_ref='runtime-evidence-v1',
            )
            with self.subTest(payload=payload), self.assertRaises(ValidationError) as context:
                signal.full_clean()
            self.assertIn('value', context.exception.message_dict)
