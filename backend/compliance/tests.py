from datetime import timedelta
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from compliance.audit import (
    EXPORT_ACCESSED_EVENT_TYPE,
    EXPORT_ACCESS_DENIED_EVENT_TYPE,
    EXPORT_AUDIT_ENTITY_TYPE,
    EXPORT_PREPARED_EVENT_TYPE,
    EXPORT_REVOKED_EVENT_TYPE,
)
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from reporting.tests import ReportingAPITests

from .admin import ExportacionSensibleAdmin, PoliticaRetencionDatosAdmin
from .models import (
    CategoriaDato,
    EstadoExportacionSensible,
    ENCRYPTED_REF_SENSITIVE_ERROR,
    EXPIRED_EXPORT_STATE_ERROR,
    ExportacionSensible,
    MAX_EXPORT_WINDOW_ERROR,
    PAYLOAD_HASH_FORMAT_ERROR,
    PoliticaRetencionDatos,
    SECRET_EXPORT_ERROR,
    SENSITIVE_EXPORT_MAX_DAYS,
)
from .services import (
    ACTIVE_RETENTION_POLICY_ERROR,
    EXPIRED_EXPORT_REVOKE_ERROR,
    EXPORT_ALREADY_REVOKED_ERROR,
    PAYLOAD_HASH_MISMATCH_ERROR,
    PAYLOAD_UNREADABLE_ERROR,
    SENSITIVE_EXPORT_METADATA_ERROR,
    encrypt_payload,
    prepare_sensitive_export,
    revoke_export,
)


class ComplianceAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='compliance',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)
        helper = ReportingAPITests()
        helper.client = self.client
        helper.user = self.user
        self._create_context = helper._create_context

    def _create_policy(self, categoria='financiero'):
        response = self.client.post(
            reverse('compliance-politica-list'),
            {
                'categoria_dato': categoria,
                'evento_inicio': 'ultimo_evento_relevante',
                'plazo_minimo_anos': 6,
                'permite_borrado_logico': True,
                'permite_purga_fisica': False,
                'requiere_hold': categoria in {'tributario', 'documental_sensible'},
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _create_scoped_reviewer_client(self, empresa, *, username_suffix=''):
        user_model = get_user_model()
        reviewer = user_model.objects.create_user(
            username=f'compliance-reviewer-{empresa.id}{username_suffix}',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        reviewer_role, _ = Role.objects.get_or_create(
            code='RevisorFiscalExterno',
            defaults={'name': 'Revisor fiscal externo'},
        )
        scope = Scope.objects.create(
            code=f'compliance-company-{empresa.id}{username_suffix}',
            name=f'Compliance scope {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=reviewer, role=reviewer_role, scope=scope, is_primary=True)

        reviewer_client = self.client_class()
        reviewer_client.force_authenticate(reviewer)
        return reviewer_client, reviewer

    def test_auth_is_required_for_compliance_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('compliance-politica-list'),
            reverse('compliance-export-list'),
            reverse('compliance-export-prepare'),
        ]
        for url in urls:
            response = client.get(url) if 'preparar' not in url else client.post(url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_prepare_sensitive_export_encrypts_payload_and_can_be_decrypted(self):
        self._create_context('CMP')
        self._create_policy('financiero')

        response = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'financiero_mensual',
                'motivo': 'Revision mensual',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        export = ExportacionSensible.objects.get(pk=response.data['id'])
        self.assertTrue(export.encrypted_payload)
        self.assertNotIn('monto', export.encrypted_payload)

        content = self.client.get(reverse('compliance-export-content', args=[export.id]))
        self.assertEqual(content.status_code, status.HTTP_200_OK)
        self.assertEqual(content.data['id'], export.id)
        prepared_event = AuditEvent.objects.get(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.id),
        )
        accessed_event = AuditEvent.objects.get(
            event_type=EXPORT_ACCESSED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.id),
        )
        self.assertEqual(prepared_event.actor_user_id, self.user.id)
        self.assertEqual(prepared_event.metadata['export_kind'], export.export_kind)
        self.assertEqual(prepared_event.metadata['categoria_dato'], export.categoria_dato)
        self.assertEqual(prepared_event.metadata['payload_hash'], export.payload_hash)
        self.assertEqual(prepared_event.metadata['estado'], EstadoExportacionSensible.PREPARED)
        self.assertEqual(accessed_event.actor_user_id, self.user.id)
        self.assertEqual(accessed_event.metadata['payload_hash'], export.payload_hash)

    def test_prepare_sensitive_export_service_creates_audit_event(self):
        self._create_policy('financiero')

        export = prepare_sensitive_export(
            categoria_dato='financiero',
            export_kind='financiero_mensual',
            scope_resumen={'anio': 2026, 'mes': 1},
            motivo='Revision mensual desde servicio',
            payload={'total': 'controlado'},
            created_by=self.user,
            actor_user=self.user,
            ip_address='127.0.0.1',
        )

        prepared_event = AuditEvent.objects.get(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.id),
        )
        self.assertEqual(prepared_event.actor_user_id, self.user.id)
        self.assertEqual(prepared_event.ip_address, '127.0.0.1')
        self.assertEqual(prepared_event.metadata['export_kind'], export.export_kind)
        self.assertEqual(prepared_event.metadata['payload_hash'], export.payload_hash)

    def test_prepare_sensitive_export_rolls_back_when_audit_creation_fails(self):
        self._create_policy('financiero')

        with patch('compliance.audit.create_audit_event', side_effect=RuntimeError('export audit unavailable')):
            with self.assertRaises(RuntimeError):
                prepare_sensitive_export(
                    categoria_dato='financiero',
                    export_kind='financiero_mensual',
                    scope_resumen={'anio': 2026, 'mes': 1},
                    motivo='Revision sin auditoria',
                    payload={'total': 'controlado'},
                    created_by=self.user,
                    actor_user=self.user,
                )

        self.assertFalse(ExportacionSensible.objects.filter(motivo='Revision sin auditoria').exists())

    def test_scoped_reviewer_can_prepare_and_download_in_scope_sensitive_export(self):
        socio, empresa, *_rest = self._create_context('CMP-SCOPE-A')
        self._create_policy('documental_sensible')
        reviewer_client, reviewer = self._create_scoped_reviewer_client(empresa, username_suffix='-in')

        response = reviewer_client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'documental_sensible',
                'export_kind': 'socio_resumen',
                'motivo': 'Revision documental scoped',
                'socio_id': socio.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        export = ExportacionSensible.objects.get(pk=response.data['id'])
        self.assertEqual(export.created_by_id, reviewer.id)
        content = reviewer_client.get(reverse('compliance-export-content', args=[export.id]))
        self.assertEqual(content.status_code, status.HTTP_200_OK)
        self.assertEqual(content.data['payload']['socio']['id'], socio.id)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESSED_EVENT_TYPE,
                entity_id=str(export.id),
                actor_user_id=reviewer.id,
            ).exists()
        )

    def test_scoped_reviewer_cannot_prepare_sensitive_export_outside_scope(self):
        _socio_in_scope, empresa_in_scope, *_rest = self._create_context('CMP-SCOPE-IN')
        socio_out_scope, _empresa_out_scope, *_other = self._create_context('CMP-SCOPE-OUT')
        self._create_policy('documental_sensible')
        reviewer_client, reviewer = self._create_scoped_reviewer_client(empresa_in_scope, username_suffix='-out')

        response = reviewer_client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'documental_sensible',
                'export_kind': 'socio_resumen',
                'motivo': 'Revision documental fuera de scope',
                'socio_id': socio_out_scope.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ExportacionSensible.objects.filter(created_by=reviewer).exists())

    def test_scoped_reviewer_cannot_download_sensitive_export_created_by_other_user(self):
        socio, empresa, *_rest = self._create_context('CMP-SCOPE-OWN')
        self._create_policy('documental_sensible')
        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'documental_sensible',
                'export_kind': 'socio_resumen',
                'motivo': 'Revision documental admin',
                'socio_id': socio.id,
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        reviewer_client, reviewer = self._create_scoped_reviewer_client(empresa, username_suffix='-foreign')

        content = reviewer_client.get(reverse('compliance-export-content', args=[export.id]))

        self.assertEqual(content.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESSED_EVENT_TYPE,
                entity_id=str(export.id),
                actor_user_id=reviewer.id,
            ).exists()
        )

    def test_scoped_reviewer_cannot_download_sensitive_export_after_scope_changes(self):
        socio, empresa, *_rest = self._create_context('CMP-SCOPE-OLD')
        _socio_other, empresa_other, *_other = self._create_context('CMP-SCOPE-NEW')
        self._create_policy('documental_sensible')
        reviewer_client, reviewer = self._create_scoped_reviewer_client(empresa, username_suffix='-shift')
        prepared = reviewer_client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'documental_sensible',
                'export_kind': 'socio_resumen',
                'motivo': 'Revision documental antes de cambio de scope',
                'socio_id': socio.id,
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        export = ExportacionSensible.objects.get(pk=prepared.data['id'])

        UserScopeAssignment.objects.filter(user=reviewer).update(effective_to=timezone.now())
        reviewer_role = Role.objects.get(code='RevisorFiscalExterno')
        next_scope = Scope.objects.create(
            code=f'compliance-company-{empresa_other.id}-shift',
            name=f'Compliance scope {empresa_other.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa_other.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=reviewer, role=reviewer_role, scope=next_scope, is_primary=True)

        content = reviewer_client.get(reverse('compliance-export-content', args=[export.id]))

        self.assertEqual(content.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESSED_EVENT_TYPE,
                entity_id=str(export.id),
                actor_user_id=reviewer.id,
            ).exists()
        )

    def test_export_content_rejects_payload_hash_mismatch(self):
        self._create_context('HASH-MISMATCH')
        self._create_policy('financiero')

        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'financiero_mensual',
                'motivo': 'Revision mensual',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        tampered_payload, _tampered_hash = encrypt_payload({'resultado': 'alterado'})
        ExportacionSensible.objects.filter(pk=export.pk).update(encrypted_payload=tampered_payload)

        denied = self.client.get(reverse('compliance-export-content', args=[export.id]))

        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(denied.data['detail'], PAYLOAD_HASH_MISMATCH_ERROR)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(export.id),
                metadata__payload_hash=export.payload_hash,
            ).exists()
        )
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESSED_EVENT_TYPE,
                entity_id=str(export.id),
            ).exists()
        )

    def test_export_content_rejects_unreadable_encrypted_payload(self):
        self._create_context('UNREADABLE')
        self._create_policy('financiero')

        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'financiero_mensual',
                'motivo': 'Revision mensual',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        ExportacionSensible.objects.filter(pk=export.pk).update(encrypted_payload='payload-no-descifrable')

        denied = self.client.get(reverse('compliance-export-content', args=[export.id]))

        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(denied.data['detail'], PAYLOAD_UNREADABLE_ERROR)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(export.id),
                metadata__payload_hash=export.payload_hash,
            ).exists()
        )
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESSED_EVENT_TYPE,
                entity_id=str(export.id),
            ).exists()
        )

    def test_prepare_export_rejects_sensitive_visible_metadata(self):
        self._create_policy('financiero')

        sensitive_motive = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'financiero_mensual',
                'motivo': 'Revision https://provider.example.test/export?token=secret',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )
        self.assertEqual(sensitive_motive.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', sensitive_motive.data)

        sensitive_scope = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'libros_periodo',
                'motivo': 'Revision libros',
                'empresa_id': 1,
                'periodo': '2026-01?api_key=secret',
            },
            format='json',
        )
        self.assertEqual(sensitive_scope.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scope_resumen', sensitive_scope.data)

    def test_prepare_sensitive_export_service_rejects_sensitive_visible_metadata(self):
        with self.assertRaisesMessage(ValueError, SENSITIVE_EXPORT_METADATA_ERROR):
            prepare_sensitive_export(
                categoria_dato='financiero',
                export_kind='financiero_mensual',
                scope_resumen={'api_key': 'legacy-key'},
                motivo='Revision mensual',
                payload={'resultado': 'controlado'},
                created_by=self.user,
            )

    def test_prepare_sensitive_export_service_rejects_category_mismatch_and_missing_policy(self):
        with self.assertRaises(ValidationError) as category_context:
            prepare_sensitive_export(
                categoria_dato='operativo',
                export_kind='financiero_mensual',
                scope_resumen={'anio': 2026, 'mes': 1},
                motivo='Revision mensual',
                payload={'resultado': 'controlado'},
                created_by=self.user,
            )
        self.assertEqual(
            category_context.exception.message_dict['categoria_dato'][0],
            'La categoria_dato debe ser financiero para export_kind=financiero_mensual.',
        )

        PoliticaRetencionDatos.objects.create(
            categoria_dato='financiero',
            evento_inicio='ultimo_evento_relevante',
            plazo_minimo_anos=6,
            permite_borrado_logico=True,
            permite_purga_fisica=False,
            requiere_hold=False,
            estado='inactiva',
        )
        with self.assertRaises(ValidationError) as policy_context:
            prepare_sensitive_export(
                categoria_dato='financiero',
                export_kind='financiero_mensual',
                scope_resumen={'anio': 2026, 'mes': 1},
                motivo='Revision mensual',
                payload={'resultado': 'controlado'},
                created_by=self.user,
            )
        self.assertEqual(policy_context.exception.message_dict['categoria_dato'][0], ACTIVE_RETENTION_POLICY_ERROR)

    def test_export_model_clean_rejects_sensitive_visible_metadata(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible(
            categoria_dato='financiero',
            export_kind='financiero_mensual',
            scope_resumen={'periodo': '2026-01?token=secret'},
            motivo='Revision mensual',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-financiero_mensual-{payload_hash[:12]}',
            expires_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            export.full_clean()
        self.assertIn('scope_resumen', context.exception.message_dict)

    def test_export_model_and_service_reject_secret_category(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible(
            categoria_dato=CategoriaDato.SECRET,
            export_kind='resumen_restringido',
            scope_resumen={'control_ref': 'categoria-controlada-v1'},
            motivo='Revision restringida',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-resumen_restringido-{payload_hash[:12]}',
            expires_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            export.full_clean()
        self.assertEqual(context.exception.message_dict['categoria_dato'][0], SECRET_EXPORT_ERROR)

        with self.assertRaises(ValidationError) as service_context:
            prepare_sensitive_export(
                categoria_dato=CategoriaDato.SECRET,
                export_kind='resumen_restringido',
                scope_resumen={'control_ref': 'categoria-controlada-v1'},
                motivo='Revision restringida',
                payload={'resultado': 'controlado'},
                created_by=self.user,
            )
        self.assertEqual(service_context.exception.message_dict['categoria_dato'][0], SECRET_EXPORT_ERROR)

    def test_export_model_rejects_non_hex_payload_hash(self):
        encrypted_payload, _payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible(
            categoria_dato=CategoriaDato.FINANCIAL,
            export_kind='financiero_mensual',
            scope_resumen={'periodo': '2026-01'},
            motivo='Revision mensual',
            encrypted_payload=encrypted_payload,
            payload_hash='z' * 64,
            encrypted_ref='export-ref-financiero_mensual-hash-no-hex',
            expires_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            export.full_clean()
        self.assertEqual(context.exception.message_dict['payload_hash'][0], PAYLOAD_HASH_FORMAT_ERROR)

    def test_export_apis_redact_inherited_sensitive_visible_metadata(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible.objects.create(
            categoria_dato='financiero',
            export_kind='financiero_mensual',
            scope_resumen={
                'periodo': '2026-01',
                'callback': 'https://provider.example.test/export?token=secret',
                'api_key': 'legacy-key',
            },
            motivo='Revision con Bearer inherited-token',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref='https://exports.example.test/file.pdf?token=secret',
            expires_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        list_response = self.client.get(reverse('compliance-export-list'))
        detail_response = self.client.get(reverse('compliance-export-detail', args=[export.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        for export_data in (list_response.data[0], detail_response.data):
            self.assertEqual(export_data['motivo'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(export_data['scope_resumen']['periodo'], '2026-01')
            self.assertEqual(export_data['scope_resumen']['callback'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(export_data['scope_resumen']['api_key'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(export_data['encrypted_ref'], REDACTED_SENSITIVE_REFERENCE)

        rendered = str(list_response.data) + str(detail_response.data)
        self.assertNotIn('token=secret', rendered)
        self.assertNotIn('legacy-key', rendered)
        self.assertNotIn('inherited-token', rendered)
        self.assertNotIn('exports.example.test', rendered)

    def test_export_model_rejects_sensitive_encrypted_ref(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible(
            categoria_dato=CategoriaDato.FINANCIAL,
            export_kind='financiero_mensual',
            scope_resumen={'anio': 2026, 'mes': 5},
            motivo='Revision mensual',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref='https://exports.example.test/file.pdf?token=secret',
            expires_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            export.full_clean()
        self.assertEqual(context.exception.message_dict['encrypted_ref'][0], ENCRYPTED_REF_SENSITIVE_ERROR)

    def test_export_admin_redacts_sensitive_export_fields(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible.objects.create(
            categoria_dato=CategoriaDato.FINANCIAL,
            export_kind='financiero_mensual',
            scope_resumen={
                'periodo': '2026-01',
                'callback': 'https://provider.example.test/export?token=secret',
                'api_key': 'legacy-key',
            },
            motivo='Revision con Bearer inherited-token',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref='https://exports.example.test/file.pdf?token=secret',
            expires_at=timezone.now() + timedelta(days=1),
            created_by=self.user,
        )
        model_admin = ExportacionSensibleAdmin(ExportacionSensible, AdminSite())

        for raw_field in ('scope_resumen', 'motivo', 'encrypted_payload', 'encrypted_ref'):
            self.assertNotIn(raw_field, model_admin.fields)
        self.assertNotIn('encrypted_ref', model_admin.search_fields)
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, export))
        self.assertFalse(model_admin.has_delete_permission(None, export))
        for readonly_field in ('categoria_dato', 'export_kind', 'expires_at', 'hold_activo', 'estado', 'created_by'):
            self.assertIn(readonly_field, model_admin.readonly_fields)
        self.assertEqual(model_admin.motivo_redacted(export), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(model_admin.encrypted_ref_redacted(export), REDACTED_SENSITIVE_REFERENCE)

        rendered_scope = model_admin.scope_resumen_redacted(export)
        self.assertIn(REDACTED_SENSITIVE_REFERENCE, rendered_scope)
        self.assertNotIn('provider.example.test', rendered_scope)
        self.assertNotIn('legacy-key', rendered_scope)

    def test_retention_policy_admin_redacts_sensitive_event_start(self):
        policy = PoliticaRetencionDatos.objects.create(
            categoria_dato=CategoriaDato.FINANCIAL,
            evento_inicio='https://audit.example.test/policy?token=secret',
            plazo_minimo_anos=6,
            permite_borrado_logico=True,
            permite_purga_fisica=False,
            requiere_hold=False,
            estado='activa',
        )
        model_admin = PoliticaRetencionDatosAdmin(PoliticaRetencionDatos, AdminSite())

        self.assertNotIn('evento_inicio', model_admin.fields)
        self.assertNotIn('evento_inicio', model_admin.search_fields)
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, policy))
        self.assertFalse(model_admin.has_delete_permission(None, policy))
        for readonly_field in (
            'categoria_dato',
            'plazo_minimo_anos',
            'permite_borrado_logico',
            'permite_purga_fisica',
            'requiere_hold',
            'estado',
        ):
            self.assertIn(readonly_field, model_admin.readonly_fields)
        self.assertEqual(model_admin.evento_inicio_redacted(policy), REDACTED_SENSITIVE_REFERENCE)
        self.assertNotIn('audit.example.test', model_admin.evento_inicio_redacted(policy))

    def test_retention_policy_apis_redact_inherited_sensitive_event_start(self):
        policy = PoliticaRetencionDatos.objects.create(
            categoria_dato=CategoriaDato.FINANCIAL,
            evento_inicio='https://audit.example.test/policy?token=secret',
            plazo_minimo_anos=6,
            permite_borrado_logico=True,
            permite_purga_fisica=False,
            requiere_hold=False,
            estado='activa',
        )

        list_response = self.client.get(reverse('compliance-politica-list'))
        detail_response = self.client.get(reverse('compliance-politica-detail', args=[policy.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        for policy_data in (list_response.data[0], detail_response.data):
            self.assertEqual(policy_data['evento_inicio'], REDACTED_SENSITIVE_REFERENCE)

        rendered = str(list_response.data) + str(detail_response.data)
        self.assertNotIn('audit.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_export_can_be_revoked(self):
        self._create_context('REV')
        self._create_policy('operativo')

        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'dashboard_operativo',
                'motivo': 'Revision interna',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        revoked = self.client.post(
            reverse('compliance-export-revoke', args=[prepared.data['id']]),
            {'motivo': 'Rotacion controlada de evidencia'},
            format='json',
        )
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        self.assertEqual(revoked.data['estado'], 'revocada')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(prepared.data['id']),
                metadata__estado=EstadoExportacionSensible.REVOKED,
                metadata__revocation_reason='Rotacion controlada de evidencia',
            ).exists()
        )

        denied = self.client.get(reverse('compliance-export-content', args=[prepared.data['id']]))
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(prepared.data['id']),
                metadata__estado=EstadoExportacionSensible.REVOKED,
            ).exists()
        )
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESSED_EVENT_TYPE,
                entity_id=str(prepared.data['id']),
            ).exists()
        )

    def test_revoke_export_service_rolls_back_when_audit_creation_fails(self):
        self._create_policy('operativo')
        export = prepare_sensitive_export(
            categoria_dato='operativo',
            export_kind='dashboard_operativo',
            scope_resumen={},
            motivo='Revision interna',
            payload={'dashboard': 'controlado'},
            created_by=self.user,
            actor_user=self.user,
        )

        with patch('compliance.audit.create_audit_event', side_effect=RuntimeError('revoke audit unavailable')):
            with self.assertRaises(RuntimeError):
                revoke_export(
                    export,
                    actor_user=self.user,
                    ip_address='127.0.0.1',
                    revocation_reason='Rotacion controlada de evidencia',
                )

        export.refresh_from_db()
        self.assertEqual(export.estado, EstadoExportacionSensible.PREPARED)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_id=str(export.id),
            ).exists()
        )

    def test_export_revoke_requires_non_sensitive_reason(self):
        self._create_context('REV-REASON')
        self._create_policy('operativo')

        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'dashboard_operativo',
                'motivo': 'Revision interna',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        missing_reason = self.client.post(
            reverse('compliance-export-revoke', args=[prepared.data['id']]),
            {},
            format='json',
        )
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', missing_reason.data)

        sensitive_reason = self.client.post(
            reverse('compliance-export-revoke', args=[prepared.data['id']]),
            {'motivo': 'https://audit.example.test/revoke?token=secret'},
            format='json',
        )
        self.assertEqual(sensitive_reason.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo', sensitive_reason.data)

        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        self.assertEqual(export.estado, EstadoExportacionSensible.PREPARED)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_id=str(prepared.data['id']),
            ).exists()
        )

    def test_export_revoke_rejects_terminal_states(self):
        self._create_context('REV-TERM')
        self._create_policy('operativo')

        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'dashboard_operativo',
                'motivo': 'Revision interna',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        first_revoke = self.client.post(
            reverse('compliance-export-revoke', args=[prepared.data['id']]),
            {'motivo': 'Rotacion controlada de evidencia'},
            format='json',
        )
        self.assertEqual(first_revoke.status_code, status.HTTP_200_OK)

        repeated_revoke = self.client.post(
            reverse('compliance-export-revoke', args=[prepared.data['id']]),
            {'motivo': 'Intento duplicado'},
            format='json',
        )
        self.assertEqual(repeated_revoke.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(repeated_revoke.data['detail'], EXPORT_ALREADY_REVOKED_ERROR)
        self.assertEqual(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(prepared.data['id']),
            ).count(),
            1,
        )

        expired = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'dashboard_operativo',
                'motivo': 'Revision expirada',
            },
            format='json',
        )
        self.assertEqual(expired.status_code, status.HTTP_201_CREATED)
        ExportacionSensible.objects.filter(pk=expired.data['id']).update(
            estado=EstadoExportacionSensible.EXPIRED,
            expires_at=timezone.now() - timedelta(days=1),
        )

        expired_revoke = self.client.post(
            reverse('compliance-export-revoke', args=[expired.data['id']]),
            {'motivo': 'Intento posterior a expiracion'},
            format='json',
        )
        self.assertEqual(expired_revoke.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expired_revoke.data['detail'], EXPIRED_EXPORT_REVOKE_ERROR)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(expired.data['id']),
            ).exists()
        )

    def test_export_revoke_expires_overdue_export_before_rejecting(self):
        self._create_context('REV-OVERDUE')
        self._create_policy('operativo')

        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'dashboard_operativo',
                'motivo': 'Revision interna',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        export.expires_at = timezone.now() - timedelta(days=1)
        export.save(update_fields=['expires_at'])

        response = self.client.post(
            reverse('compliance-export-revoke', args=[export.id]),
            {'motivo': 'Intento posterior a vencimiento'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], EXPIRED_EXPORT_REVOKE_ERROR)
        export.refresh_from_db()
        self.assertEqual(export.estado, EstadoExportacionSensible.EXPIRED)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(export.id),
            ).exists()
        )

    def test_export_expires_after_window_when_no_hold(self):
        self._create_context('EXP')
        self._create_policy('operativo')
        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'dashboard_operativo',
                'motivo': 'Revision operativa',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        export.expires_at = timezone.now() - timedelta(days=1)
        export.save(update_fields=['expires_at'])

        denied = self.client.get(reverse('compliance-export-content', args=[export.id]))
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        export.refresh_from_db()
        self.assertEqual(export.estado, 'expirada')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(export.id),
                metadata__estado=EstadoExportacionSensible.EXPIRED,
                metadata__payload_hash=export.payload_hash,
            ).exists()
        )

    def test_prepare_tax_export_returns_traceability_error_without_annual_process(self):
        self._create_context('EXP-TAX-MISSING')
        self._create_policy('tributario')

        response = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'tributario',
                'export_kind': 'tributario_anual',
                'motivo': 'Revision anual',
                'anio_tributario': 2027,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_missing')

    def test_expired_export_status_is_terminal_even_before_expiry(self):
        self._create_context('EXP-STATE')
        self._create_policy('financiero')
        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'financiero_mensual',
                'motivo': 'Revision mensual',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        ExportacionSensible.objects.filter(pk=export.pk).update(
            estado=EstadoExportacionSensible.EXPIRED,
            expires_at=timezone.now() + timedelta(days=1),
        )

        denied = self.client.get(reverse('compliance-export-content', args=[export.id]))

        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(denied.data['detail'], 'La exportacion expiro y ya no puede descargarse.')
        self.assertFalse(AuditEvent.objects.filter(event_type=EXPORT_ACCESSED_EVENT_TYPE).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(export.id),
                metadata__estado=EstadoExportacionSensible.EXPIRED,
                metadata__payload_hash=export.payload_hash,
            ).exists()
        )

    def test_export_with_hold_stays_downloadable_after_expiry(self):
        socio, _, _, _, _, _ = self._create_context('HOLD')
        self._create_policy('documental_sensible')
        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'documental_sensible',
                'export_kind': 'socio_resumen',
                'motivo': 'Hold legal',
                'socio_id': socio.id,
                'hold_activo': True,
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        export = ExportacionSensible.objects.get(pk=prepared.data['id'])
        export.expires_at = timezone.now() - timedelta(days=1)
        export.save(update_fields=['expires_at'])

        allowed = self.client.get(reverse('compliance-export-content', args=[export.id]))
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    def test_export_model_rejects_inconsistent_expired_state(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible(
            categoria_dato=CategoriaDato.FINANCIAL,
            export_kind='financiero_mensual',
            scope_resumen={'anio': 2026, 'mes': 5},
            motivo='Revision mensual',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-financiero_mensual-{payload_hash[:12]}',
            expires_at=timezone.now() + timedelta(days=1),
            estado=EstadoExportacionSensible.EXPIRED,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            export.full_clean()
        self.assertEqual(context.exception.message_dict['expires_at'][0], EXPIRED_EXPORT_STATE_ERROR)

        export.expires_at = timezone.now() - timedelta(days=1)
        export.hold_activo = True
        with self.assertRaises(ValidationError) as hold_context:
            export.full_clean()
        self.assertEqual(hold_context.exception.message_dict['hold_activo'][0], EXPIRED_EXPORT_STATE_ERROR)

    def test_export_model_rejects_window_over_30_days_without_hold(self):
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = ExportacionSensible(
            categoria_dato=CategoriaDato.FINANCIAL,
            export_kind='financiero_mensual',
            scope_resumen={'anio': 2026, 'mes': 5},
            motivo='Revision mensual',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-financiero_mensual-{payload_hash[:12]}',
            expires_at=timezone.now() + timedelta(days=SENSITIVE_EXPORT_MAX_DAYS + 1),
            created_by=self.user,
        )

        with self.assertRaises(ValidationError) as context:
            export.full_clean()
        self.assertEqual(context.exception.message_dict['expires_at'][0], MAX_EXPORT_WINDOW_ERROR)

        export.hold_activo = True
        export.full_clean()

    def test_prepare_export_requires_matching_categoria_for_export_kind(self):
        self._create_context('CMP-CAT')
        self._create_policy('operativo')

        response = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'operativo',
                'export_kind': 'financiero_mensual',
                'motivo': 'Categoria incorrecta',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['categoria_dato'][0],
            'La categoria_dato debe ser financiero para export_kind=financiero_mensual.',
        )

    def test_prepare_export_requires_active_policy_for_category(self):
        self._create_context('CMP-POL')

        response = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'financiero',
                'export_kind': 'financiero_mensual',
                'motivo': 'Sin politica activa',
                'anio': 2026,
                'mes': 1,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['categoria_dato'][0],
            'No existe una politica de retencion activa para la categoria indicada.',
        )

    def test_retention_policy_model_rejects_unsafe_controls(self):
        cases = [
            (
                PoliticaRetencionDatos(
                    categoria_dato=CategoriaDato.FINANCIAL,
                    evento_inicio='https://audit.example.test/policy?token=secret',
                    plazo_minimo_anos=6,
                    permite_borrado_logico=True,
                    permite_purga_fisica=False,
                    requiere_hold=False,
                    estado='activa',
                ),
                'evento_inicio',
            ),
            (
                PoliticaRetencionDatos(
                    categoria_dato=CategoriaDato.OPERATIONAL,
                    evento_inicio='cierre-operacional',
                    plazo_minimo_anos=0,
                    permite_borrado_logico=True,
                    permite_purga_fisica=False,
                    requiere_hold=False,
                    estado='activa',
                ),
                'plazo_minimo_anos',
            ),
            (
                PoliticaRetencionDatos(
                    categoria_dato=CategoriaDato.TAX,
                    evento_inicio='cierre-tributario',
                    plazo_minimo_anos=6,
                    permite_borrado_logico=True,
                    permite_purga_fisica=False,
                    requiere_hold=False,
                    estado='activa',
                ),
                'requiere_hold',
            ),
            (
                PoliticaRetencionDatos(
                    categoria_dato=CategoriaDato.SECRET,
                    evento_inicio='rotacion-credencial',
                    plazo_minimo_anos=6,
                    permite_borrado_logico=True,
                    permite_purga_fisica=True,
                    requiere_hold=False,
                    estado='activa',
                ),
                'permite_purga_fisica',
            ),
        ]

        for policy, field_name in cases:
            with self.subTest(field_name=field_name), self.assertRaises(ValidationError) as context:
                policy.full_clean()
            self.assertIn(field_name, context.exception.message_dict)

    def test_retention_policy_api_rejects_unsafe_controls(self):
        responses = [
            self.client.post(
                reverse('compliance-politica-list'),
                {
                    'categoria_dato': 'tributario',
                    'evento_inicio': 'cierre-tributario',
                    'plazo_minimo_anos': 6,
                    'permite_borrado_logico': True,
                    'permite_purga_fisica': False,
                    'requiere_hold': False,
                    'estado': 'activa',
                },
                format='json',
            ),
            self.client.post(
                reverse('compliance-politica-list'),
                {
                    'categoria_dato': 'documental_sensible',
                    'evento_inicio': 'https://audit.example.test/policy?token=secret',
                    'plazo_minimo_anos': 6,
                    'permite_borrado_logico': True,
                    'permite_purga_fisica': True,
                    'requiere_hold': True,
                    'estado': 'activa',
                },
                format='json',
            ),
        ]

        self.assertEqual(responses[0].status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('requiere_hold', responses[0].data)
        self.assertEqual(responses[1].status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evento_inicio', responses[1].data)
        self.assertIn('permite_purga_fisica', responses[1].data)
        self.assertNotIn('token=secret', str(responses[1].data))
