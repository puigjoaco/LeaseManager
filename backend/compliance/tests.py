from datetime import timedelta

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
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from reporting.tests import ReportingAPITests

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
    PAYLOAD_HASH_MISMATCH_ERROR,
    PAYLOAD_UNREADABLE_ERROR,
    SENSITIVE_EXPORT_METADATA_ERROR,
    encrypt_payload,
    prepare_sensitive_export,
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

        revoked = self.client.post(reverse('compliance-export-revoke', args=[prepared.data['id']]), format='json')
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        self.assertEqual(revoked.data['estado'], 'revocada')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EXPORT_REVOKED_EVENT_TYPE,
                entity_type=EXPORT_AUDIT_ENTITY_TYPE,
                entity_id=str(prepared.data['id']),
                metadata__estado=EstadoExportacionSensible.REVOKED,
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

    def test_export_expires_after_window_when_no_hold(self):
        self._create_context('EXP')
        self._create_policy('tributario')
        prepared = self.client.post(
            reverse('compliance-export-prepare'),
            {
                'categoria_dato': 'tributario',
                'export_kind': 'tributario_anual',
                'motivo': 'Revision anual',
                'anio_tributario': 2027,
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
