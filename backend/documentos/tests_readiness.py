import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from .models import DocumentoEmitido, ExpedienteDocumental, PoliticaFirmaYNotaria, TipoDocumental
from .readiness import collect_document_readiness


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
            checksum='missing-policy',
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
        self.assertEqual(issues['documents.non_pdf_storage_ref']['count'], 1)
        self.assertEqual(issues['documents.document_without_active_policy']['count'], 1)
        self.assertEqual(issues['documents.metadata_missing']['count'], 1)

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
