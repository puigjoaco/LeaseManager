import json
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent
from compliance.audit import (
    EXPORT_ACCESS_DENIED_EVENT_TYPE,
    EXPORT_ACCESSED_EVENT_TYPE,
    EXPORT_AUDIT_ENTITY_TYPE,
    EXPORT_PREPARED_EVENT_TYPE,
    EXPORT_REVOKED_EVENT_TYPE,
    build_export_audit_metadata,
)
from compliance.models import (
    CategoriaDato,
    EstadoExportacionSensible,
    EstadoRegistro,
    ExportacionSensible,
    PoliticaRetencionDatos,
)
from compliance.services import encrypt_payload, prepare_sensitive_export
from core.compliance_data_readiness import collect_compliance_data_readiness


class ComplianceDataReadinessTests(TestCase):
    def _create_policies(self):
        for category in CategoriaDato:
            PoliticaRetencionDatos.objects.create(
                categoria_dato=category.value,
                evento_inicio='cierre-operacional',
                plazo_minimo_anos=6,
                permite_borrado_logico=True,
                permite_purga_fisica=False,
                requiere_hold=category in {CategoriaDato.TAX, CategoriaDato.DOCUMENT},
                estado=EstadoRegistro.ACTIVE,
            )

    def _create_user(self):
        return get_user_model().objects.create_user(
            username='compliance-admin',
            email='compliance-admin@example.test',
            password='test-pass',
        )

    def _create_prepared_audit_event(self, export, user=None):
        AuditEvent.objects.create(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible preparada y cifrada',
            actor_user=user,
            metadata=build_export_audit_metadata(
                export,
                extra_metadata={'estado': EstadoExportacionSensible.PREPARED},
            ),
        )

    def _create_revoked_audit_event(self, export, *, reason='Rotacion controlada de evidencia'):
        AuditEvent.objects.create(
            event_type=EXPORT_REVOKED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible revocada',
            actor_user=export.created_by,
            metadata=build_export_audit_metadata(
                export,
                extra_metadata={
                    'estado': EstadoExportacionSensible.REVOKED,
                    'revocation_reason': reason,
                },
            ),
        )

    def _create_valid_export(self):
        user = self._create_user()
        export = prepare_sensitive_export(
            categoria_dato=CategoriaDato.FINANCIAL,
            export_kind='financiero_mensual',
            scope_resumen={'anio': 2026, 'mes': 5},
            motivo='control-compliance-v1',
            payload={'ok': True, 'periodo': '2026-05'},
            created_by=user,
        )
        self._create_prepared_audit_event(export, user=user)
        return export

    def _create_raw_export(self, **overrides):
        user = overrides.pop('created_by', None)
        if user is None:
            user = self._create_user()
        defaults = {
            'categoria_dato': CategoriaDato.FINANCIAL,
            'export_kind': 'financiero_mensual',
            'scope_resumen': {'periodo_ref': 'periodo-controlado-v1'},
            'motivo': 'control-compliance-v1',
            'encrypted_payload': 'encrypted-payload-placeholder',
            'payload_hash': 'a' * 64,
            'encrypted_ref': 'export-ref-controlado-v1',
            'expires_at': timezone.now() + timedelta(days=1),
            'hold_activo': False,
            'estado': EstadoExportacionSensible.PREPARED,
            'created_by': user,
        }
        defaults.update(overrides)
        return ExportacionSensible.objects.create(**defaults)

    def _collect_with_final_refs(self, **overrides):
        params = {
            'source_kind': 'snapshot_controlado',
            'source_label': 'compliance-controlled-v1',
            'authorization_ref': 'compliance-authorization-v1',
            'policy_approval_ref': 'compliance-policy-approved-v1',
            'responsible_ref': 'compliance-responsibles-v1',
            'controls_evidence_ref': 'compliance-controls-v1',
            'archived_evidence_ref': 'compliance-archive-v1',
            'legal_review_ref': 'compliance-legal-review-v1',
        }
        params.update(overrides)
        return collect_compliance_data_readiness(**params)

    def test_empty_database_reports_partial_without_sensitive_values(self):
        result = collect_compliance_data_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_compliance_data'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('compliance.source_kind_not_authorized', issue_codes)
        self.assertIn('compliance.retention_policy_missing', issue_codes)
        self.assertIn('compliance.policy_approval_ref_missing', issue_codes)
        self.assertIn('retention_policies', result['sections'])
        self.assertNotIn('://', json.dumps(result))

    def test_state_changed_event_without_transition_metadata_is_blocking(self):
        AuditEvent.objects.create(
            event_type='compliance.politica_retencion.state_changed',
            entity_type='politica_retencion_datos',
            entity_id='1',
            summary='Politica de retencion heredada sin metadata de transicion.',
            metadata={'estado_nuevo': EstadoRegistro.ACTIVE},
        )

        result = collect_compliance_data_readiness()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertIn('compliance.audit_state_transition_metadata_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['state_transition_metadata_missing'], 1)

    def test_bootstrap_demo_compliance_policies_validates_before_persisting(self):
        output = StringIO()

        with self.assertRaises(CommandError) as sensitive_context:
            call_command(
                'bootstrap_demo_compliance_policies',
                event_start='https://policy.example.test/source?token=secret',
                stdout=output,
            )
        self.assertIn('campos=evento_inicio', str(sensitive_context.exception))
        self.assertNotIn('policy.example.test', str(sensitive_context.exception))
        self.assertEqual(PoliticaRetencionDatos.objects.count(), 0)

        with self.assertRaises(CommandError) as years_context:
            call_command(
                'bootstrap_demo_compliance_policies',
                min_years=0,
                stdout=output,
            )
        self.assertIn('campos=plazo_minimo_anos', str(years_context.exception))
        self.assertEqual(PoliticaRetencionDatos.objects.count(), 0)

    def test_bootstrap_demo_compliance_policies_creates_valid_canonical_set(self):
        output = StringIO()

        call_command('bootstrap_demo_compliance_policies', stdout=output)

        result = collect_compliance_data_readiness()
        self.assertEqual(PoliticaRetencionDatos.objects.count(), len(CategoriaDato))
        self.assertEqual(result['sections']['retention_policies']['missing_active_categories'], [])
        self.assertEqual(result['sections']['retention_policies']['hold_missing_categories'], [])
        self.assertEqual(result['sections']['retention_policies']['physical_purge_enabled_for_restricted_categories'], 0)

    def test_valid_authorized_controls_and_refs_can_pass_readiness(self):
        self._create_policies()
        self._create_valid_export()

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_compliance_data'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertEqual(result['issues'], [])

    def test_valid_local_controls_prepare_but_do_not_close_readiness(self):
        self._create_policies()
        self._create_valid_export()

        result = self._collect_with_final_refs(
            source_kind='local',
            source_label='compliance-local-v1',
            authorization_ref='',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_compliance_data'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('compliance.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        self._create_policies()
        self._create_valid_export()

        result = self._collect_with_final_refs(source_label='', authorization_ref='')
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.source_label_missing', issue_codes)
        self.assertIn('compliance.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_sensitive_final_refs_do_not_close_readiness(self):
        self._create_policies()
        self._create_valid_export()

        result = self._collect_with_final_refs(policy_approval_ref='https://example.test/policy?token=secret')
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.policy_approval_ref_sensitive', issue_codes)
        self.assertNotIn('compliance.policy_approval_ref_missing', issue_codes)
        self.assertTrue(result['sections']['final_evidence_sensitive']['policy_approval_ref'])
        self.assertFalse(result['sections']['final_evidence']['policy_approval_ref'])
        self.assertNotIn('example.test', json.dumps(result))

    def test_sensitive_source_trace_refs_do_not_close_readiness(self):
        self._create_policies()
        self._create_valid_export()

        result = self._collect_with_final_refs(
            source_label='https://source.example.test/dump?token=secret',
            authorization_ref='bearer-token-secret',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.source_label_sensitive', issue_codes)
        self.assertIn('compliance.authorization_ref_sensitive', issue_codes)
        self.assertNotIn('compliance.source_label_missing', issue_codes)
        self.assertNotIn('compliance.authorization_ref_missing', issue_codes)
        self.assertTrue(result['sections']['source_trace_sensitive']['source_label'])
        self.assertTrue(result['sections']['source_trace_sensitive']['authorization_ref'])
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])
        self.assertNotIn('source.example.test', json.dumps(result))

    def test_retention_hold_and_purge_controls_are_blocking(self):
        self._create_policies()
        PoliticaRetencionDatos.objects.filter(categoria_dato=CategoriaDato.TAX).update(requiere_hold=False)
        PoliticaRetencionDatos.objects.filter(categoria_dato=CategoriaDato.SECRET).update(permite_purga_fisica=True)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.retention_hold_missing', issue_codes)
        self.assertIn('compliance.retention_physical_purge_enabled', issue_codes)

    def test_sensitive_retention_policy_event_is_blocking_without_exposing_values(self):
        self._create_policies()
        self._create_valid_export()
        PoliticaRetencionDatos.objects.filter(categoria_dato=CategoriaDato.FINANCIAL).update(
            evento_inicio='https://policy.example.test/source?token=secret',
        )

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.retention_policy_invalid', {issue['code'] for issue in result['issues']})
        self.assertNotIn('policy.example.test', json.dumps(result))

    def test_sensitive_export_metadata_is_blocking_without_exposing_values(self):
        self._create_policies()
        export = self._create_raw_export(scope_resumen={'callback': 'https://files.example.test/export?token=secret'})
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_sensitive_visible_metadata', issue_codes)
        self.assertNotIn('files.example.test', json.dumps(result))

    def test_missing_export_motive_is_blocking(self):
        self._create_policies()
        encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = self._create_raw_export(
            motivo='   ',
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-financiero_mensual-{payload_hash[:12]}',
        )
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_motive_missing', issue_codes)
        self.assertEqual(result['sections']['exports']['motive_missing'], 1)

    def test_sensitive_encrypted_ref_is_blocking_without_exposing_values(self):
        self._create_policies()
        export = self._create_raw_export(encrypted_ref='https://files.example.test/export?token=secret')
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_encrypted_ref_sensitive', issue_codes)
        self.assertEqual(result['sections']['exports']['encrypted_ref_sensitive'], 1)
        self.assertNotIn('files.example.test', json.dumps(result))

    def test_expired_prepared_export_without_hold_is_blocking(self):
        self._create_policies()
        export = self._create_raw_export(expires_at=timezone.now() - timedelta(days=1))
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_prepared_expired_without_hold', {issue['code'] for issue in result['issues']})

    def test_inconsistent_expired_export_state_is_blocking(self):
        self._create_policies()
        export = self._create_raw_export(
            estado=EstadoExportacionSensible.EXPIRED,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_expired_state_inconsistent', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['exports']['expired_state_inconsistent'], 1)

    def test_secret_category_export_is_blocking(self):
        self._create_policies()
        export = self._create_raw_export(categoria_dato=CategoriaDato.SECRET)
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_secret_category', {issue['code'] for issue in result['issues']})

    def test_non_hex_payload_hash_is_blocking(self):
        self._create_policies()
        export = self._create_raw_export(payload_hash='z' * 64)
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_payload_hash_invalid', issue_codes)
        self.assertEqual(result['sections']['exports']['payload_hash_invalid'], 1)

    def test_payload_hash_mismatch_is_blocking(self):
        self._create_policies()
        _original_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        tampered_payload, _tampered_hash = encrypt_payload({'resultado': 'alterado'})
        export = self._create_raw_export(
            encrypted_payload=tampered_payload,
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-financiero_mensual-{payload_hash[:12]}',
        )
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_payload_hash_mismatch', issue_codes)
        self.assertEqual(result['sections']['exports']['payload_hash_mismatch'], 1)

    def test_unreadable_encrypted_payload_is_blocking(self):
        self._create_policies()
        _encrypted_payload, payload_hash = encrypt_payload({'resultado': 'controlado'})
        export = self._create_raw_export(
            encrypted_payload='payload-no-descifrable',
            payload_hash=payload_hash,
            encrypted_ref=f'export-ref-financiero_mensual-{payload_hash[:12]}',
        )
        self._create_prepared_audit_event(export, user=export.created_by)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_payload_unreadable', issue_codes)
        self.assertEqual(result['sections']['exports']['payload_unreadable'], 1)
        self.assertEqual(result['sections']['exports']['payload_hash_mismatch'], 0)

    def test_missing_prepared_audit_event_is_blocking(self):
        self._create_policies()
        self._create_raw_export()

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_prepared_audit_event_missing', {issue['code'] for issue in result['issues']})

    def test_prepared_audit_event_unaligned_is_blocking(self):
        self._create_policies()
        export = self._create_raw_export()
        AuditEvent.objects.create(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible preparada y cifrada',
            actor_user=export.created_by,
            metadata={'export_kind': export.export_kind, 'payload_hash': 'b' * 64},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertNotIn('compliance.export_prepared_audit_event_missing', issue_codes)
        self.assertIn('compliance.export_prepared_audit_event_unaligned', issue_codes)
        self.assertIn('compliance.audit_metadata_unaligned', issue_codes)
        self.assertEqual(result['sections']['exports']['prepared_audit_event_unaligned'], 1)
        self.assertEqual(result['sections']['audit']['metadata_unaligned_events'], 1)

    def test_revoked_export_without_revoked_audit_event_is_blocking(self):
        self._create_policies()
        export = self._create_valid_export()
        ExportacionSensible.objects.filter(pk=export.pk).update(estado=EstadoExportacionSensible.REVOKED)

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_revoked_audit_event_missing', issue_codes)
        self.assertEqual(result['sections']['exports']['revoked_audit_event_missing'], 1)

    def test_revoked_audit_event_unaligned_is_blocking(self):
        self._create_policies()
        export = self._create_valid_export()
        ExportacionSensible.objects.filter(pk=export.pk).update(estado=EstadoExportacionSensible.REVOKED)
        export.refresh_from_db()
        AuditEvent.objects.create(
            event_type=EXPORT_REVOKED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible revocada',
            actor_user=export.created_by,
            metadata=build_export_audit_metadata(
                export,
                extra_metadata={'estado': EstadoExportacionSensible.PREPARED},
            ),
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertNotIn('compliance.export_revoked_audit_event_missing', issue_codes)
        self.assertIn('compliance.export_revoked_audit_event_unaligned', issue_codes)
        self.assertIn('compliance.audit_metadata_unaligned', issue_codes)
        self.assertEqual(result['sections']['exports']['revoked_audit_event_unaligned'], 1)

    def test_revoked_export_without_revocation_reason_is_blocking(self):
        self._create_policies()
        export = self._create_valid_export()
        ExportacionSensible.objects.filter(pk=export.pk).update(estado=EstadoExportacionSensible.REVOKED)
        export.refresh_from_db()
        AuditEvent.objects.create(
            event_type=EXPORT_REVOKED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible revocada',
            actor_user=export.created_by,
            metadata=build_export_audit_metadata(
                export,
                extra_metadata={'estado': EstadoExportacionSensible.REVOKED},
            ),
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertNotIn('compliance.export_revoked_audit_event_missing', issue_codes)
        self.assertNotIn('compliance.export_revoked_audit_event_unaligned', issue_codes)
        self.assertIn('compliance.export_revoked_audit_reason_missing', issue_codes)
        self.assertEqual(result['sections']['exports']['revoked_audit_reason_missing'], 1)
        self.assertEqual(result['sections']['exports']['revoked_audit_reason_sensitive'], 0)

    def test_revoked_export_with_sensitive_revocation_reason_is_blocking(self):
        self._create_policies()
        export = self._create_valid_export()
        ExportacionSensible.objects.filter(pk=export.pk).update(estado=EstadoExportacionSensible.REVOKED)
        export.refresh_from_db()
        self._create_revoked_audit_event(export, reason='https://audit.example.test/revoke?token=secret')

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.export_revoked_audit_reason_sensitive', issue_codes)
        self.assertNotIn('compliance.export_revoked_audit_reason_missing', issue_codes)
        self.assertIn('compliance.audit_sensitive_metadata', issue_codes)
        self.assertEqual(result['sections']['exports']['revoked_audit_reason_missing'], 0)
        self.assertEqual(result['sections']['exports']['revoked_audit_reason_sensitive'], 1)
        self.assertNotIn('audit.example.test', json.dumps(result))

    def test_revoked_export_with_non_sensitive_reason_can_pass_readiness(self):
        self._create_policies()
        export = self._create_valid_export()
        ExportacionSensible.objects.filter(pk=export.pk).update(estado=EstadoExportacionSensible.REVOKED)
        export.refresh_from_db()
        self._create_revoked_audit_event(export)

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_compliance_data'])
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['sections']['exports']['revoked_audit_reason_missing'], 0)
        self.assertEqual(result['sections']['exports']['revoked_audit_reason_sensitive'], 0)

    def test_historical_access_event_does_not_block_after_revocation(self):
        self._create_policies()
        export = self._create_valid_export()
        AuditEvent.objects.create(
            event_type=EXPORT_ACCESSED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Contenido de exportacion sensible accedido',
            actor_user=export.created_by,
            metadata=build_export_audit_metadata(export),
        )
        ExportacionSensible.objects.filter(pk=export.pk).update(estado=EstadoExportacionSensible.REVOKED)
        export.refresh_from_db()
        self._create_revoked_audit_event(export)

        result = self._collect_with_final_refs()

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_compliance_data'])
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['sections']['audit']['metadata_unaligned_events'], 0)

    def test_access_denied_events_are_counted_without_blocking(self):
        self._create_policies()
        export = self._create_valid_export()
        AuditEvent.objects.create(
            event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Acceso a exportacion sensible denegado',
            actor_user=export.created_by,
            metadata=build_export_audit_metadata(export),
        )

        result = self._collect_with_final_refs()

        self.assertTrue(result['ready_for_compliance_data'])
        self.assertEqual(result['sections']['audit']['access_denied_events'], 1)

    def test_sensitive_audit_metadata_is_blocking_without_exposing_values(self):
        self._create_policies()
        export = self._create_raw_export()
        AuditEvent.objects.create(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible preparada y cifrada',
            actor_user=export.created_by,
            metadata={'download_url': 'https://audit.example.test/export?token=secret'},
        )

        result = self._collect_with_final_refs()

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.audit_sensitive_metadata', {issue['code'] for issue in result['issues']})
        self.assertNotIn('audit.example.test', json.dumps(result))

    def test_export_audit_event_without_actor_is_blocking(self):
        self._create_policies()
        export = self._create_raw_export()
        AuditEvent.objects.create(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id=str(export.pk),
            summary='Exportacion sensible preparada y cifrada',
            actor_user=None,
            metadata={'export_kind': export.export_kind},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.audit_actor_missing', issue_codes)
        self.assertEqual(result['sections']['audit']['actor_missing_events'], 1)

    def test_export_audit_event_with_invalid_target_is_blocking(self):
        self._create_policies()
        export = self._create_valid_export()
        AuditEvent.objects.create(
            event_type=EXPORT_ACCESSED_EVENT_TYPE,
            entity_type=EXPORT_AUDIT_ENTITY_TYPE,
            entity_id='999999',
            summary='Contenido de exportacion sensible accedido',
            actor_user=export.created_by,
            metadata={'export_kind': export.export_kind},
        )
        AuditEvent.objects.create(
            event_type=EXPORT_REVOKED_EVENT_TYPE,
            entity_type='otra_entidad',
            entity_id=str(export.pk),
            summary='Exportacion sensible revocada',
            actor_user=export.created_by,
            metadata={'export_kind': export.export_kind},
        )

        result = self._collect_with_final_refs()
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.audit_target_invalid', issue_codes)
        self.assertEqual(result['sections']['audit']['invalid_target_events'], 2)

    def test_deadline_requires_suspension_if_not_ready(self):
        result = collect_compliance_data_readiness(as_of_date=date(2026, 12, 1))

        self.assertFalse(result['ready_for_compliance_data'])
        self.assertIn('compliance.production_suspension_required', {issue['code'] for issue in result['issues']})
        self.assertTrue(result['sections']['deadline']['after_deadline'])

    def test_command_writes_json_and_rejects_versionable_repo_output(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'compliance_readiness.json'
            call_command('audit_compliance_data_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertIn('retention_policies', result['sections'])

        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'compliance-readiness-should-not-be-versioned.json'
        with self.assertRaisesMessage(CommandError, 'local-evidence'):
            call_command(
                'audit_compliance_data_readiness',
                output=str(blocked_output),
                stdout=StringIO(),
            )
        self.assertFalse(blocked_output.exists())

        with self.assertRaises(CommandError):
            call_command('audit_compliance_data_readiness', fail_on_attention=True, stdout=StringIO())
