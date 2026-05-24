import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent

from .models import DocumentoEmitido, EstadoDocumento, ExpedienteDocumental, PoliticaFirmaYNotaria, TipoDocumental
from .readiness import collect_document_readiness


VALID_SHA256 = 'a' * 64


def create_all_active_policies():
    for tipo_documental in TipoDocumental.values:
        defaults = {
            'tipo_documental': tipo_documental,
            'requiere_firma_arrendador': False,
            'requiere_firma_arrendatario': False,
            'requiere_codeudor': False,
            'requiere_notaria': False,
            'modo_firma_permitido': 'firma_simple',
            'estado': 'activa',
        }
        if tipo_documental == TipoDocumental.MAIN_CONTRACT:
            defaults['requiere_firma_arrendador'] = True
            defaults['requiere_firma_arrendatario'] = True
        PoliticaFirmaYNotaria.objects.create(**defaults)


class DocumentReadinessAuditTests(TestCase):
    def test_empty_database_reports_missing_policies_and_final_evidence(self):
        result = collect_document_readiness()

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertEqual(
            set(result['sections']['policy']['missing_policy_types']),
            set(TipoDocumental.values),
        )
        issue_codes = {issue['code'] for issue in result['issues']}
        self.assertIn('documents.source_kind_not_authorized', issue_codes)
        self.assertIn('documents.active_policy_missing', issue_codes)
        self.assertIn('documents.final_policy_ref_missing', issue_codes)
        self.assertIn('documents.controlled_pdf_ref_missing', issue_codes)
        self.assertNotIn('://', json.dumps(result))

    def test_all_policies_and_non_sensitive_refs_can_pass_authorized_readiness(self):
        create_all_active_policies()

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_label='documents-controlled-v1',
            authorization_ref='documents-authorization-v1',
            source_kind='snapshot_controlado',
        )

        self.assertEqual(result['classification'], 'resuelto_confirmado')
        self.assertTrue(result['ready_for_stage5_documents'])
        self.assertTrue(result['source_kind_authorized_for_close'])
        self.assertEqual(result['issues'], [])

    def test_all_policies_and_non_sensitive_refs_cannot_close_local_readiness(self):
        create_all_active_policies()

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_kind='local',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('documents.source_kind_not_authorized', issue_codes)

    def test_authorized_source_requires_source_trace_refs(self):
        create_all_active_policies()

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.source_label_missing', issue_codes)
        self.assertIn('documents.authorization_ref_missing', issue_codes)
        self.assertFalse(result['sections']['source_trace']['source_label'])
        self.assertFalse(result['sections']['source_trace']['authorization_ref'])

    def test_sensitive_final_refs_do_not_close_readiness(self):
        create_all_active_policies()

        result = collect_document_readiness(
            final_policy_ref='https://example.com/policy',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_label='documents-controlled-v1',
            authorization_ref='documents-authorization-v1',
            source_kind='snapshot_controlado',
        )

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.final_policy_ref_missing', {issue['code'] for issue in result['issues']})

    def test_document_issues_are_reported_without_reading_storage(self):
        PoliticaFirmaYNotaria.objects.create(
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            modo_firma_permitido='firma_simple',
            estado='activa',
        )
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='1',
            estado='abierto',
            owner_operativo='manual:1',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum='docx-check',
            fecha_carga=timezone.now(),
            origen='generado_sistema',
            estado='emitido',
            storage_ref='storage/docs/not-pdf.docx',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            version_plantilla='',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            origen='generado_sistema',
            estado='emitido',
            storage_ref='storage/docs/tax-support.pdf',
        )

        result = collect_document_readiness()
        issues = {issue['code']: issue for issue in result['issues']}

        self.assertEqual(result['sections']['documents']['non_pdf_storage_refs'], 1)
        self.assertEqual(result['sections']['documents']['without_active_policy'], 1)
        self.assertEqual(result['sections']['documents']['missing_metadata'], 1)
        self.assertEqual(result['sections']['documents']['invalid_checksums'], 1)
        self.assertEqual(issues['documents.non_pdf_storage_ref']['count'], 1)
        self.assertEqual(issues['documents.document_without_active_policy']['count'], 1)
        self.assertEqual(issues['documents.metadata_missing']['count'], 1)
        self.assertEqual(issues['documents.invalid_checksum']['count'], 1)

    def test_invalid_checksum_is_blocking_without_exposing_values(self):
        create_all_active_policies()
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='invalid-checksum',
            estado='abierto',
            owner_operativo='manual:checksum',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum='checksum-operativo-sin-digest',
            fecha_carga=timezone.now(),
            origen='generado_sistema',
            estado='emitido',
            storage_ref='storage/docs/contract.pdf',
        )

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_label='documents-controlled-v1',
            authorization_ref='documents-authorization-v1',
            source_kind='snapshot_controlado',
        )

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.invalid_checksum', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['invalid_checksums'], 1)
        rendered = json.dumps(result)
        self.assertNotIn('checksum-operativo-sin-digest', rendered)

    def test_sensitive_storage_refs_are_blocking_without_exposing_values(self):
        create_all_active_policies()
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='sensitive-storage',
            estado='abierto',
            owner_operativo='manual:1',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            origen='generado_sistema',
            estado='emitido',
            storage_ref='https://storage.example.test/docs/contract.pdf?token=secret',
        )

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_label='documents-controlled-v1',
            authorization_ref='documents-authorization-v1',
            source_kind='snapshot_controlado',
        )
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.sensitive_storage_ref', issue_codes)
        self.assertEqual(result['sections']['documents']['sensitive_storage_refs'], 1)
        rendered = json.dumps(result)
        self.assertNotIn('storage.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_formalized_document_without_formalization_audit_is_blocking(self):
        create_all_active_policies()
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='formalized-no-audit',
            estado='abierto',
            owner_operativo='manual:formalized',
        )
        document = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            origen='generado_sistema',
            estado=EstadoDocumento.FORMALIZED,
            storage_ref='storage/docs/formalized-no-audit.pdf',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_label='documents-controlled-v1',
            authorization_ref='documents-authorization-v1',
            source_kind='snapshot_controlado',
        )

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.formalization_audit_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['formalized_without_formalization_audit'], 1)

        AuditEvent.objects.create(
            event_type='documentos.documento_emitido.formalized',
            entity_type='documento_emitido',
            entity_id=str(document.pk),
            summary='Documento formalizado',
        )

        result = collect_document_readiness(
            final_policy_ref='policy-final-docs-v1',
            responsible_ref='responsables-docs-v1',
            controlled_pdf_ref='pdf-controlled-proof-v1',
            source_label='documents-controlled-v1',
            authorization_ref='documents-authorization-v1',
            source_kind='snapshot_controlado',
        )

        self.assertTrue(result['ready_for_stage5_documents'])
        self.assertNotIn('documents.formalization_audit_missing', {issue['code'] for issue in result['issues']})

    def test_command_writes_json_output_and_fail_on_attention_blocks_close(self):
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / 'document_readiness.json'
            call_command('audit_document_readiness', output=str(output_path), stdout=StringIO())
            result = json.loads(output_path.read_text(encoding='utf-8'))

        self.assertEqual(result['classification'], 'parcial')
        self.assertFalse(result['source_kind_authorized_for_close'])
        self.assertIn('documents.source_kind_not_authorized', {issue['code'] for issue in result['issues']})
        self.assertIn('policy', result['sections'])

        with self.assertRaises(CommandError):
            call_command('audit_document_readiness', fail_on_attention=True, stdout=StringIO())

    def test_command_rejects_repo_output_before_collecting_readiness(self):
        blocked_output = Path(settings.PROJECT_ROOT) / 'docs' / 'documents-readiness-should-not-be-versioned.json'
        with patch('documentos.management.commands.audit_document_readiness.collect_document_readiness') as collect:
            with self.assertRaisesMessage(CommandError, 'local-evidence'):
                call_command(
                    'audit_document_readiness',
                    output=str(blocked_output),
                    stdout=StringIO(),
                )

        collect.assert_not_called()
        self.assertFalse(blocked_output.exists())
