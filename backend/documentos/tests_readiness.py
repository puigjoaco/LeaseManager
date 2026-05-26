import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from audit.models import AuditEvent

from .models import DocumentoEmitido, EstadoDocumento, ExpedienteDocumental, PoliticaFirmaYNotaria, TipoDocumental
from .pdf_generation import GENERATED_PDF_AUDIT_EVENT_TYPE
from .readiness import collect_document_readiness


VALID_SHA256 = 'a' * 64
VALID_SHA256_ALT = 'b' * 64
FORMALIZATION_REF = 'formalizacion-readiness-doc-001'


def create_user(username='docs-readiness'):
    return get_user_model().objects.create_user(
        username=username,
        password='secret123',
        default_role_code='AdministradorGlobal',
    )


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
        user = create_user('docs-readiness-issues')
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
            usuario=user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='storage/docs/not-pdf.docx',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.TAX_SUPPORT,
            version_plantilla='',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='storage/docs/tax-support.pdf',
        )

        result = collect_document_readiness()
        issues = {issue['code']: issue for issue in result['issues']}

        self.assertEqual(result['sections']['documents']['non_pdf_storage_refs'], 1)
        self.assertEqual(result['sections']['documents']['without_active_policy'], 1)
        self.assertEqual(result['sections']['documents']['missing_metadata'], 1)
        self.assertEqual(result['sections']['documents']['missing_user'], 0)
        self.assertEqual(result['sections']['documents']['invalid_checksums'], 1)
        self.assertEqual(issues['documents.non_pdf_storage_ref']['count'], 1)
        self.assertEqual(issues['documents.document_without_active_policy']['count'], 1)
        self.assertEqual(issues['documents.metadata_missing']['count'], 1)
        self.assertEqual(issues['documents.invalid_checksum']['count'], 1)

    def test_document_without_user_is_blocking(self):
        create_all_active_policies()
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='missing-user',
            estado='abierto',
            owner_operativo='manual:missing-user',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            origen='carga_externa_controlada',
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
        self.assertIn('documents.user_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['missing_user'], 1)

    def test_inactive_policy_with_existing_document_is_blocking(self):
        user = create_user('docs-readiness-inactive-policy')
        PoliticaFirmaYNotaria.objects.create(
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            modo_firma_permitido='firma_simple',
            estado='inactiva',
        )
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='inactive-policy',
            estado='abierto',
            owner_operativo='manual:inactive-policy',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='storage/docs/inactive-policy.pdf',
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
        self.assertIn('documents.active_policy_missing', issue_codes)
        self.assertIn('documents.document_without_active_policy', issue_codes)
        self.assertEqual(result['sections']['documents']['without_active_policy'], 1)

    def test_invalid_checksum_is_blocking_without_exposing_values(self):
        create_all_active_policies()
        user = create_user('docs-readiness-invalid-checksum')
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
            usuario=user,
            origen='carga_externa_controlada',
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
        user = create_user('docs-readiness-sensitive-storage')
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
            usuario=user,
            origen='carga_externa_controlada',
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

    def test_generated_document_without_generation_audit_is_blocking(self):
        create_all_active_policies()
        user = create_user('docs-readiness-generated-audit')
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='generated-audit',
            estado='abierto',
            owner_operativo='manual:generated-audit',
        )
        document = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='generado_sistema',
            estado='emitido',
            storage_ref='storage/docs/generated-audit.pdf',
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
        self.assertIn('documents.generated_pdf_audit_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['generated_without_audit'], 1)

        AuditEvent.objects.create(
            event_type=GENERATED_PDF_AUDIT_EVENT_TYPE,
            entity_type='documento_emitido',
            entity_id=str(document.pk),
            summary='Documento PDF generado por sistema',
            metadata={'checksum_sha256': document.checksum},
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
        self.assertEqual(result['sections']['documents']['generated_without_audit'], 0)
        self.assertNotIn('documents.generated_pdf_audit_missing', {issue['code'] for issue in result['issues']})

    def test_formalized_document_without_formalization_audit_is_blocking(self):
        create_all_active_policies()
        user = create_user('docs-readiness-formalized')
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
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.FORMALIZED,
            storage_ref='storage/docs/formalized-no-audit.pdf',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
            evidencia_formalizacion_ref=FORMALIZATION_REF,
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

    def test_formalized_document_without_evidence_is_blocking(self):
        create_all_active_policies()
        user = create_user('docs-readiness-formalization-evidence')
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='formalized-no-evidence',
            estado='abierto',
            owner_operativo='manual:formalized-evidence',
        )
        document = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.FORMALIZED,
            storage_ref='storage/docs/formalized-no-evidence.pdf',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
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

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.formalization_evidence_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['formalized_without_evidence'], 1)

    def test_formalized_document_sensitive_evidence_is_blocking_without_exposing_value(self):
        create_all_active_policies()
        user = create_user('docs-readiness-formalization-sensitive')
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='formalized-sensitive-evidence',
            estado='abierto',
            owner_operativo='manual:formalized-sensitive',
        )
        sensitive_ref = 'https://docs.example.test/formalizacion?token=secret'
        document = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.FORMALIZED,
            storage_ref='storage/docs/formalized-sensitive-evidence.pdf',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
            evidencia_formalizacion_ref=sensitive_ref,
        )
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

        rendered = json.dumps(result)
        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.formalization_evidence_sensitive', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['formalized_with_sensitive_evidence'], 1)
        self.assertNotIn(sensitive_ref, rendered)

    def test_invalid_notary_receipts_are_reported_with_specific_codes(self):
        create_all_active_policies()
        PoliticaFirmaYNotaria.objects.filter(
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
        ).update(requiere_notaria=True)
        user = create_user('docs-readiness-notary-receipts')
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='notary-receipts',
            estado='abierto',
            owner_operativo='manual:notary-receipts',
        )
        other_expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='notary-receipts-other',
            estado='abierto',
            owner_operativo='manual:notary-receipts-other',
        )
        valid_receipt = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.NOTARY_RECEIPT,
            version_plantilla='notary-v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/notary-valid.pdf',
        )
        wrong_type_receipt = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.ADDENDUM,
            version_plantilla='notary-wrong-type-v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/notary-wrong-type.pdf',
        )
        wrong_expediente_receipt = DocumentoEmitido.objects.create(
            expediente=other_expediente,
            tipo_documental=TipoDocumental.NOTARY_RECEIPT,
            version_plantilla='notary-wrong-exp-v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/notary-wrong-exp.pdf',
        )
        invalid_state_receipt = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.NOTARY_RECEIPT,
            version_plantilla='notary-draft-v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.DRAFT,
            storage_ref='storage/docs/notary-draft.pdf',
        )
        documents = [
            DocumentoEmitido.objects.create(
                expediente=expediente,
                tipo_documental=TipoDocumental.MAIN_CONTRACT,
                version_plantilla='contract-missing-reception',
                checksum='1' * 64,
                fecha_carga=timezone.now(),
                usuario=user,
                origen='carga_externa_controlada',
                estado=EstadoDocumento.FORMALIZED,
                storage_ref='storage/docs/contract-missing-reception.pdf',
                firma_arrendador_registrada=True,
                firma_arrendatario_registrada=True,
                recepcion_notarial_registrada=False,
                comprobante_notarial=valid_receipt,
                evidencia_formalizacion_ref=FORMALIZATION_REF,
            ),
            DocumentoEmitido.objects.create(
                expediente=expediente,
                tipo_documental=TipoDocumental.MAIN_CONTRACT,
                version_plantilla='contract-wrong-type',
                checksum='2' * 64,
                fecha_carga=timezone.now(),
                usuario=user,
                origen='carga_externa_controlada',
                estado=EstadoDocumento.FORMALIZED,
                storage_ref='storage/docs/contract-wrong-type.pdf',
                firma_arrendador_registrada=True,
                firma_arrendatario_registrada=True,
                recepcion_notarial_registrada=True,
                comprobante_notarial=wrong_type_receipt,
                evidencia_formalizacion_ref=FORMALIZATION_REF,
            ),
            DocumentoEmitido.objects.create(
                expediente=expediente,
                tipo_documental=TipoDocumental.MAIN_CONTRACT,
                version_plantilla='contract-wrong-exp',
                checksum='3' * 64,
                fecha_carga=timezone.now(),
                usuario=user,
                origen='carga_externa_controlada',
                estado=EstadoDocumento.FORMALIZED,
                storage_ref='storage/docs/contract-wrong-exp.pdf',
                firma_arrendador_registrada=True,
                firma_arrendatario_registrada=True,
                recepcion_notarial_registrada=True,
                comprobante_notarial=wrong_expediente_receipt,
                evidencia_formalizacion_ref=FORMALIZATION_REF,
            ),
            DocumentoEmitido.objects.create(
                expediente=expediente,
                tipo_documental=TipoDocumental.MAIN_CONTRACT,
                version_plantilla='contract-invalid-state',
                checksum='4' * 64,
                fecha_carga=timezone.now(),
                usuario=user,
                origen='carga_externa_controlada',
                estado=EstadoDocumento.FORMALIZED,
                storage_ref='storage/docs/contract-invalid-state.pdf',
                firma_arrendador_registrada=True,
                firma_arrendatario_registrada=True,
                recepcion_notarial_registrada=True,
                comprobante_notarial=invalid_state_receipt,
                evidencia_formalizacion_ref=FORMALIZATION_REF,
            ),
        ]
        for document in documents:
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
        issue_codes = {issue['code'] for issue in result['issues']}

        self.assertFalse(result['ready_for_stage5_documents'])
        self.assertIn('documents.notary_reception_missing', issue_codes)
        self.assertIn('documents.notary_receipt_wrong_type', issue_codes)
        self.assertIn('documents.notary_receipt_wrong_expediente', issue_codes)
        self.assertIn('documents.notary_receipt_invalid_state', issue_codes)
        self.assertEqual(result['sections']['documents']['formalized_without_notary_reception'], 1)
        self.assertEqual(result['sections']['documents']['notary_receipts_wrong_type'], 1)
        self.assertEqual(result['sections']['documents']['notary_receipts_wrong_expediente'], 1)
        self.assertEqual(result['sections']['documents']['notary_receipts_invalid_state'], 1)

    def test_corrective_version_without_dedicated_audit_is_blocking(self):
        create_all_active_policies()
        user = create_user('docs-readiness-correction')
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='correction-no-audit',
            estado='abierto',
            owner_operativo='manual:correction',
        )
        origin = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.FORMALIZED,
            storage_ref='storage/docs/formalized-origin.pdf',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
            evidencia_formalizacion_ref=FORMALIZATION_REF,
        )
        AuditEvent.objects.create(
            event_type='documentos.documento_emitido.formalized',
            entity_type='documento_emitido',
            entity_id=str(origin.pk),
            summary='Documento formalizado',
        )
        correction = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v2',
            checksum=VALID_SHA256_ALT,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/formalized-correction.pdf',
            documento_origen=origin,
            correccion_ref='correction-ticket-readiness-001',
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
        self.assertIn('documents.corrective_version_audit_missing', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['corrective_versions_without_audit'], 1)

        AuditEvent.objects.create(
            event_type='documentos.documento_emitido.corrective_version_created',
            entity_type='documento_emitido',
            entity_id=str(correction.pk),
            summary='Version correctiva de documento',
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
        self.assertEqual(result['sections']['documents']['corrective_versions'], 1)
        self.assertNotIn('documents.corrective_version_audit_missing', {issue['code'] for issue in result['issues']})

    def test_invalid_corrective_version_is_blocking(self):
        create_all_active_policies()
        user = create_user('docs-readiness-invalid-correction')
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='manual',
            entidad_id='invalid-correction',
            estado='abierto',
            owner_operativo='manual:invalid-correction',
        )
        origin = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/origin-not-formalized.pdf',
        )
        correction = DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental=TipoDocumental.MAIN_CONTRACT,
            version_plantilla='v2',
            checksum=VALID_SHA256_ALT,
            fecha_carga=timezone.now(),
            usuario=user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/correction-invalid-origin.pdf',
            documento_origen=origin,
            correccion_ref='correction-ticket-invalid-origin',
        )
        AuditEvent.objects.create(
            event_type='documentos.documento_emitido.corrective_version_created',
            entity_type='documento_emitido',
            entity_id=str(correction.pk),
            summary='Version correctiva de documento',
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
        self.assertIn('documents.corrective_version_invalid', {issue['code'] for issue in result['issues']})
        self.assertEqual(result['sections']['documents']['invalid_corrective_versions'], 1)

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
