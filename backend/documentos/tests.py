from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from contratos.models import Arrendatario, CodeudorSolidario, Contrato, ContratoPropiedad, PeriodoContractual
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .admin import (
    ArchivoExpedienteAdmin,
    DocumentoEmitidoAdmin,
    ExpedienteDocumentalAdmin,
    PlantillaDocumentalAdmin,
    PoliticaFirmaYNotariaAdmin,
)
from .correction_audit import CORRECTION_AUDIT_EVENT_TYPE
from .formalization_audit import FORMALIZATION_AUDIT_EVENT_TYPE
from .models import (
    ArchivoExpediente,
    DocumentoEmitido,
    EstadoClasificacionArchivoExpediente,
    EstadoDocumento,
    ExpedienteDocumental,
    PlantillaDocumental,
    PoliticaFirmaYNotaria,
)
from .pdf_generation import GENERATED_PDF_AUDIT_EVENT_TYPE, PREVIEW_PDF_AUDIT_EVENT_TYPE


VALID_SHA256 = 'a' * 64
VALID_SHA256_ALT = 'b' * 64
VALID_SHA256_THIRD = 'c' * 64
VALID_SHA256_FOURTH = 'd' * 64
FORMALIZATION_REF = 'formalizacion-controlada-doc-001'


class DocumentosAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='docs',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _create_expediente(self, entidad_tipo='manual', entidad_id='1', owner_operativo='manual:1'):
        response = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': entidad_tipo,
                'entidad_id': entidad_id,
                'estado': 'abierto',
                'owner_operativo': owner_operativo,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _create_politica(self, **overrides):
        payload = {
            'tipo_documental': 'contrato_principal',
            'requiere_firma_arrendador': True,
            'requiere_firma_arrendatario': True,
            'requiere_codeudor': False,
            'requiere_notaria': False,
            'modo_firma_permitido': 'firma_simple',
            'estado': 'activa',
        }
        payload.update(overrides)
        response = self.client.post(reverse('documentos-politica-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self._ensure_template(payload['tipo_documental'], 'v1')
        return response.data

    def _ensure_template(self, tipo_documental='contrato_principal', version_plantilla='v1'):
        template, _ = PlantillaDocumental.objects.get_or_create(
            tipo_documental=tipo_documental,
            version_plantilla=version_plantilla,
            defaults={
                'plantilla_ref': f'templates/{tipo_documental}/{version_plantilla}',
                'checksum_plantilla': VALID_SHA256,
                'descripcion': 'Plantilla controlada de prueba.',
                'estado': 'activa',
            },
        )
        return template

    def _create_documento(self, expediente_id, **overrides):
        payload = {
            'expediente': expediente_id,
            'tipo_documental': 'contrato_principal',
            'version_plantilla': 'v1',
            'checksum': VALID_SHA256,
            'fecha_carga': '2026-03-18T10:00:00-03:00',
            'origen': 'carga_externa_controlada',
            'estado': 'emitido',
            'storage_ref': 'storage/contracts/contrato-1.pdf',
            'firma_arrendador_registrada': False,
            'firma_arrendatario_registrada': False,
            'firma_codeudor_registrada': False,
            'recepcion_notarial_registrada': False,
            'comprobante_notarial': None,
        }
        payload.update(overrides)
        self._ensure_template(payload['tipo_documental'], payload['version_plantilla'])
        response = self.client.post(reverse('documentos-documento-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _archivo_expediente_payload(self, expediente_id, **overrides):
        payload = {
            'expediente': expediente_id,
            'categoria': 'imagen',
            'subcategoria': '05_fotos_y_videos',
            'titulo_operativo': 'Foto local controlada',
            'descripcion_objetiva': 'Vista interior del local asociada al expediente.',
            'extension': 'jpg',
            'mime_type': 'image/jpeg',
            'checksum_sha256': VALID_SHA256_THIRD,
            'size_bytes': 12345,
            'storage_ref': 'storage/expedientes/locales/foto-local.jpg',
            'origen_auditoria': 'carga-auditoria-revisar-controlada',
            'estado_clasificacion': 'confirmado',
            'duplicate_of': None,
            'fecha_archivo': None,
        }
        payload.update(overrides)
        return payload

    def test_document_operational_refs_normalize_before_full_clean_and_save(self):
        max_entity_id = 'doc-entity-' + ('x' * (64 - len('doc-entity-')))
        expediente = ExpedienteDocumental(
            entidad_tipo=' contrato ',
            entidad_id=f' {max_entity_id} ',
            owner_operativo=' mandato:normalizado ',
        )
        expediente.full_clean()
        self.assertEqual(expediente.entidad_tipo, 'contrato')
        self.assertEqual(expediente.entidad_id, max_entity_id)
        self.assertEqual(expediente.owner_operativo, 'mandato:normalizado')
        expediente.save()
        expediente.refresh_from_db()
        self.assertEqual(expediente.entidad_tipo, 'contrato')
        self.assertEqual(expediente.entidad_id, max_entity_id)
        self.assertEqual(expediente.owner_operativo, 'mandato:normalizado')

        max_version = 'doc-template-' + ('v' * (64 - len('doc-template-')))
        max_template_ref = 'templates/contrato-principal/' + (
            'x' * (255 - len('templates/contrato-principal/'))
        )
        template = PlantillaDocumental(
            tipo_documental='contrato_principal',
            version_plantilla=f' {max_version} ',
            plantilla_ref=f' {max_template_ref} ',
            checksum_plantilla=f' {VALID_SHA256.upper()} ',
            descripcion=' Plantilla documentada ',
            estado='activa',
        )
        template.full_clean()
        self.assertEqual(template.version_plantilla, max_version)
        self.assertEqual(template.plantilla_ref, max_template_ref)
        self.assertEqual(template.checksum_plantilla, VALID_SHA256)
        self.assertEqual(template.descripcion, 'Plantilla documentada')
        template.save()
        template.refresh_from_db()
        self.assertEqual(template.version_plantilla, max_version)
        self.assertEqual(template.plantilla_ref, max_template_ref)
        self.assertEqual(template.checksum_plantilla, VALID_SHA256)
        self.assertEqual(template.descripcion, 'Plantilla documentada')

        PoliticaFirmaYNotaria.objects.create(
            tipo_documental='contrato_principal',
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            requiere_codeudor=False,
            requiere_notaria=False,
            modo_firma_permitido='firma_simple',
            estado='activa',
        )

        storage_prefix = 'storage/docs/'
        storage_suffix = '.pdf'
        max_storage_ref = storage_prefix + (
            'x' * (255 - len(storage_prefix) - len(storage_suffix))
        ) + storage_suffix
        document = DocumentoEmitido(
            expediente=expediente,
            tipo_documental='contrato_principal',
            version_plantilla=f' {max_version} ',
            checksum=f' {VALID_SHA256.upper()} ',
            fecha_carga=timezone.now(),
            usuario=self.user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref=f' {max_storage_ref} ',
        )
        document.full_clean()
        self.assertEqual(document.version_plantilla, max_version)
        self.assertEqual(document.checksum, VALID_SHA256)
        self.assertEqual(document.storage_ref, max_storage_ref)
        document.save()
        document.refresh_from_db()
        self.assertEqual(document.version_plantilla, max_version)
        self.assertEqual(document.checksum, VALID_SHA256)
        self.assertEqual(document.storage_ref, max_storage_ref)

        max_evidence_ref = 'formalizacion-' + ('e' * (128 - len('formalizacion-')))
        document.estado = EstadoDocumento.FORMALIZED
        document.firma_arrendador_registrada = True
        document.firma_arrendatario_registrada = True
        document.evidencia_formalizacion_ref = f' {max_evidence_ref} '
        document.full_clean()
        self.assertEqual(document.evidencia_formalizacion_ref, max_evidence_ref)
        document.save(
            update_fields=[
                'estado',
                'firma_arrendador_registrada',
                'firma_arrendatario_registrada',
                'evidencia_formalizacion_ref',
                'updated_at',
            ]
        )
        document.refresh_from_db()
        self.assertEqual(document.evidencia_formalizacion_ref, max_evidence_ref)

        correction_prefix = 'storage/docs/correction-'
        max_correction_storage = correction_prefix + (
            'y' * (255 - len(correction_prefix) - len(storage_suffix))
        ) + storage_suffix
        max_correction_ref = 'correction-' + ('c' * (128 - len('correction-')))
        correction = DocumentoEmitido(
            expediente=expediente,
            tipo_documental='contrato_principal',
            version_plantilla=f' {max_version} ',
            checksum=f' {VALID_SHA256_ALT.upper()} ',
            fecha_carga=timezone.now(),
            usuario=self.user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref=f' {max_correction_storage} ',
            documento_origen=document,
            correccion_ref=f' {max_correction_ref} ',
        )
        correction.full_clean()
        self.assertEqual(correction.version_plantilla, max_version)
        self.assertEqual(correction.checksum, VALID_SHA256_ALT)
        self.assertEqual(correction.storage_ref, max_correction_storage)
        self.assertEqual(correction.correccion_ref, max_correction_ref)
        correction.save()
        correction.refresh_from_db()
        self.assertEqual(correction.version_plantilla, max_version)
        self.assertEqual(correction.checksum, VALID_SHA256_ALT)
        self.assertEqual(correction.storage_ref, max_correction_storage)
        self.assertEqual(correction.correccion_ref, max_correction_ref)

    def test_generate_pdf_endpoint_derives_checksum_storage_and_audit(self):
        expediente = self._create_expediente(entidad_id='generated-pdf')
        self._create_politica()
        self._ensure_template('contrato_principal', 'contrato-v1')
        payload = {
            'expediente': expediente['id'],
            'tipo_documental': 'contrato_principal',
            'version_plantilla': 'contrato-v1',
            'titulo': 'Contrato principal controlado',
            'lineas': [
                'Arrendador: referencia-operativa-arrendador',
                'Arrendatario: referencia-operativa-arrendatario',
                'Propiedad: referencia-operativa-propiedad',
            ],
        }

        preview = self.client.post(reverse('documentos-documento-previsualizar-pdf'), payload, format='json')
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        preview_event = AuditEvent.objects.get(
            event_type=PREVIEW_PDF_AUDIT_EVENT_TYPE,
            entity_type='documento_pdf_preview',
            entity_id=preview.data['preview_ref'],
        )
        self.assertEqual(preview_event.actor_user_id, self.user.id)
        self.assertEqual(preview_event.metadata['checksum_sha256'], preview.data['pdf_sha256'])
        self.assertEqual(preview_event.metadata['storage_ref'], preview.data['storage_ref_preview'])
        self.assertEqual(preview_event.metadata['version_plantilla'], payload['version_plantilla'])
        self.assertEqual(preview_event.metadata['tipo_documental'], payload['tipo_documental'])
        self.assertEqual(preview_event.metadata['expediente_id'], str(expediente['id']))
        self.assertEqual(preview_event.metadata['line_count'], len(payload['lineas']))

        response = self.client.post(reverse('documentos-documento-generar-pdf'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document_payload = response.data['documento']
        document = DocumentoEmitido.objects.get(pk=document_payload['id'])
        self.assertEqual(document.origen, 'generado_sistema')
        self.assertEqual(document.estado, EstadoDocumento.ISSUED)
        self.assertEqual(document.checksum, response.data['pdf_sha256'])
        self.assertEqual(preview.data['pdf_sha256'], response.data['pdf_sha256'])
        self.assertEqual(preview.data['storage_ref_preview'], document.storage_ref)
        self.assertRegex(document.checksum, r'^[0-9a-f]{64}$')
        self.assertTrue(document.storage_ref.startswith('storage/generated-documents/contrato_principal/contrato-v1-'))
        self.assertTrue(document.storage_ref.endswith('.pdf'))
        self.assertGreater(response.data['pdf_size_bytes'], 100)
        generated_event = AuditEvent.objects.get(
            event_type=GENERATED_PDF_AUDIT_EVENT_TYPE,
            entity_type='documento_emitido',
            entity_id=str(document.pk),
        )
        self.assertEqual(generated_event.actor_user_id, self.user.id)
        self.assertEqual(generated_event.metadata['checksum_sha256'], document.checksum)
        self.assertEqual(generated_event.metadata['storage_ref'], document.storage_ref)
        self.assertEqual(generated_event.metadata['version_plantilla'], document.version_plantilla)
        self.assertEqual(generated_event.metadata['tipo_documental'], document.tipo_documental)
        self.assertEqual(generated_event.metadata['expediente_id'], str(expediente['id']))
        self.assertEqual(generated_event.metadata['pdf_size_bytes'], response.data['pdf_size_bytes'])

    def test_generate_pdf_requires_matching_preview(self):
        expediente = self._create_expediente(entidad_id='generated-without-preview')
        self._create_politica()
        self._ensure_template('contrato_principal', 'contrato-v1')

        response = self.client.post(
            reverse('documentos-documento-generar-pdf'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'contrato-v1',
                'titulo': 'Contrato principal controlado',
                'lineas': [
                    'Arrendador: referencia-operativa-arrendador',
                    'Arrendatario: referencia-operativa-arrendatario',
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('preview', response.data)
        self.assertFalse(DocumentoEmitido.objects.filter(origen='generado_sistema').exists())

    def test_generate_pdf_requires_preview_of_same_content(self):
        expediente = self._create_expediente(entidad_id='generated-preview-mismatch')
        self._create_politica()
        self._ensure_template('contrato_principal', 'contrato-v1')
        payload = {
            'expediente': expediente['id'],
            'tipo_documental': 'contrato_principal',
            'version_plantilla': 'contrato-v1',
            'titulo': 'Contrato principal controlado',
            'lineas': ['Arrendador: referencia-operativa-arrendador'],
        }
        preview = self.client.post(reverse('documentos-documento-previsualizar-pdf'), payload, format='json')
        self.assertEqual(preview.status_code, status.HTTP_200_OK)

        mutated = {**payload, 'lineas': ['Arrendador: referencia-operativa-distinta']}
        response = self.client.post(reverse('documentos-documento-generar-pdf'), mutated, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('preview', response.data)
        self.assertFalse(DocumentoEmitido.objects.filter(origen='generado_sistema').exists())

    def test_generate_pdf_endpoint_rejects_sensitive_content(self):
        expediente = self._create_expediente(entidad_id='generated-sensitive')
        self._create_politica()
        self._ensure_template('contrato_principal', 'contrato-v1')

        response = self.client.post(
            reverse('documentos-documento-previsualizar-pdf'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'contrato-v1',
                'titulo': 'Contrato principal controlado',
                'lineas': ['No persistir token=secret-value en PDF generado'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('lineas', response.data)

    def test_generate_pdf_requires_active_document_template(self):
        expediente = self._create_expediente(entidad_id='generated-template-missing')
        self._create_politica()

        response = self.client.post(
            reverse('documentos-documento-previsualizar-pdf'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'contrato-v2-sin-registro',
                'titulo': 'Contrato principal controlado',
                'lineas': ['Arrendador: referencia-operativa-arrendador'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('version_plantilla', response.data)

    def test_template_api_rejects_sensitive_reference(self):
        response = self.client.post(
            reverse('documentos-plantilla-list'),
            {
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'contrato-v1-sensitive',
                'plantilla_ref': 'https://storage.example.test/templates/contrato.pdf?token=secret',
                'checksum_plantilla': VALID_SHA256,
                'descripcion': 'Plantilla heredada no controlada.',
                'estado': 'activa',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('plantilla_ref', response.data)

    def test_used_template_api_rejects_identity_and_checksum_mutation(self):
        expediente = self._create_expediente(entidad_id='template-immutability')
        self._create_politica()
        documento = self._create_documento(expediente['id'])
        template = PlantillaDocumental.objects.get(
            tipo_documental=documento['tipo_documental'],
            version_plantilla=documento['version_plantilla'],
        )

        response = self.client.patch(
            reverse('documentos-plantilla-detail', args=[template.id]),
            {
                'version_plantilla': 'v2',
                'checksum_plantilla': VALID_SHA256_ALT,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('version_plantilla', response.data)
        self.assertIn('checksum_plantilla', response.data)
        template.refresh_from_db()
        self.assertEqual(template.version_plantilla, 'v1')
        self.assertEqual(template.checksum_plantilla, VALID_SHA256)

        description_update = self.client.patch(
            reverse('documentos-plantilla-detail', args=[template.id]),
            {'descripcion': 'Descripcion operativa actualizada.'},
            format='json',
        )
        self.assertEqual(description_update.status_code, status.HTTP_200_OK)
        template.refresh_from_db()
        self.assertEqual(template.descripcion, 'Descripcion operativa actualizada.')

    def test_generic_document_endpoint_rejects_system_generated_origin(self):
        expediente = self._create_expediente(entidad_id='generic-generated-origin')
        self._create_politica()

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'generado_sistema',
                'estado': 'emitido',
                'storage_ref': 'storage/contracts/generic-generated-origin.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('origen', response.data)

    def test_generic_document_endpoint_rejects_patch_to_system_generated_origin(self):
        expediente = self._create_expediente(entidad_id='generic-generated-origin-patch')
        self._create_politica()
        documento = self._create_documento(expediente['id'])

        response = self.client.patch(
            reverse('documentos-documento-detail', args=[documento['id']]),
            {'origen': 'generado_sistema'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('origen', response.data)
        stored = DocumentoEmitido.objects.get(pk=documento['id'])
        self.assertEqual(stored.origen, 'carga_externa_controlada')

    def test_generated_pdf_document_cannot_be_mutated_from_generic_endpoint(self):
        expediente = self._create_expediente(entidad_id='generated-pdf-generic-mutation')
        self._create_politica()
        self._ensure_template('contrato_principal', 'contrato-v1')
        payload = {
            'expediente': expediente['id'],
            'tipo_documental': 'contrato_principal',
            'version_plantilla': 'contrato-v1',
            'titulo': 'Contrato principal controlado',
            'lineas': ['Arrendador: referencia-operativa-arrendador'],
        }
        preview = self.client.post(reverse('documentos-documento-previsualizar-pdf'), payload, format='json')
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        generated = self.client.post(reverse('documentos-documento-generar-pdf'), payload, format='json')
        self.assertEqual(generated.status_code, status.HTTP_201_CREATED)
        document_id = generated.data['documento']['id']

        response = self.client.patch(
            reverse('documentos-documento-detail', args=[document_id]),
            {'checksum': VALID_SHA256_ALT},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('origen', response.data)
        stored = DocumentoEmitido.objects.get(pk=document_id)
        self.assertEqual(stored.origen, 'generado_sistema')
        self.assertEqual(stored.checksum, generated.data['pdf_sha256'])

    def test_document_admin_redacts_sensitive_document_refs(self):
        expediente = self._create_expediente(entidad_id='admin-redaction')
        self._create_politica()
        document = DocumentoEmitido.objects.create(
            expediente_id=expediente['id'],
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=self.user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='https://storage.example.test/contracts/doc.pdf?token=secret',
            evidencia_formalizacion_ref='https://evidence.example.test/formalizacion?token=secret',
            correccion_ref='https://corrections.example.test/ref?token=secret',
        )
        model_admin = DocumentoEmitidoAdmin(DocumentoEmitido, AdminSite())

        for raw_field in ('storage_ref', 'evidencia_formalizacion_ref', 'correccion_ref'):
            self.assertNotIn(raw_field, model_admin.fields)
            self.assertNotIn(raw_field, model_admin.search_fields)
        self.assertEqual(set(model_admin.readonly_fields), set(model_admin.fields))
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, document))
        self.assertFalse(model_admin.has_delete_permission(None, document))
        self.assertEqual(model_admin.storage_ref_redacted(document), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            model_admin.evidencia_formalizacion_ref_redacted(document),
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(model_admin.correccion_ref_redacted(document), REDACTED_SENSITIVE_REFERENCE)

    def test_template_snapshot_and_admin_redact_sensitive_reference(self):
        template = PlantillaDocumental.objects.create(
            tipo_documental='contrato_principal',
            version_plantilla='legacy-sensitive',
            plantilla_ref='https://storage.example.test/templates/contrato.pdf?token=secret',
            checksum_plantilla=VALID_SHA256,
            estado='activa',
        )

        snapshot = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        legacy_template = next(
            item
            for item in snapshot.data['plantillas_documentales']
            if item['version_plantilla'] == 'legacy-sensitive'
        )
        self.assertEqual(legacy_template['plantilla_ref'], REDACTED_SENSITIVE_REFERENCE)

        model_admin = PlantillaDocumentalAdmin(PlantillaDocumental, AdminSite())
        self.assertNotIn('plantilla_ref', model_admin.fields)
        self.assertNotIn('plantilla_ref', model_admin.search_fields)
        self.assertEqual(set(model_admin.readonly_fields), set(model_admin.fields))
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, template))
        self.assertFalse(model_admin.has_delete_permission(None, template))
        self.assertEqual(model_admin.plantilla_ref_redacted(template), REDACTED_SENSITIVE_REFERENCE)

    def test_expediente_full_clean_rejects_sensitive_operational_reference(self):
        expediente = ExpedienteDocumental(
            entidad_tipo='manual',
            entidad_id='https://legacy.example.test/entity?token=secret',
            estado='abierto',
            owner_operativo='manual:safe-owner',
        )

        with self.assertRaises(ValidationError) as context:
            expediente.full_clean()

        self.assertIn('entidad_id', context.exception.message_dict)

    def test_expediente_api_rejects_sensitive_operational_references(self):
        base_payload = {
            'entidad_tipo': 'manual',
            'entidad_id': 'safe-entity',
            'estado': 'abierto',
            'owner_operativo': 'manual:safe-owner',
        }
        sensitive_cases = {
            'entidad_tipo': 'https://legacy.example.test/type?token=secret',
            'entidad_id': 'https://legacy.example.test/entity?token=secret',
            'owner_operativo': 'owner@example.test',
        }

        for field_name, value in sensitive_cases.items():
            payload = {**base_payload, field_name: value}
            response = self.client.post(reverse('documentos-expediente-list'), payload, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(field_name, response.data)

        self.assertFalse(ExpedienteDocumental.objects.exists())

    def test_expediente_apis_and_snapshot_redact_inherited_sensitive_references(self):
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='https://legacy.example.test/type?token=secret',
            entidad_id='https://legacy.example.test/entity?token=secret',
            estado='abierto',
            owner_operativo='owner@example.test',
        )

        list_response = self.client.get(reverse('documentos-expediente-list'))
        detail_response = self.client.get(reverse('documentos-expediente-detail', args=[expediente.id]))
        snapshot_response = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['entidad_tipo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(list_response.data[0]['entidad_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(list_response.data[0]['owner_operativo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['entidad_tipo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['entidad_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['owner_operativo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['expedientes'][0]['entidad_tipo'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['expedientes'][0]['entidad_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['expedientes'][0]['owner_operativo'], REDACTED_SENSITIVE_REFERENCE)
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('legacy.example.test', rendered)
        self.assertNotIn('owner@example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_snapshot_hides_archived_empty_legacy_expedientes(self):
        archived_empty = ExpedienteDocumental.objects.create(
            entidad_tipo='revisar_company_manual_evidence',
            entidad_id='legacy-empty',
            estado='archivado',
            owner_operativo='owner_operativo_inmobiliarias_herencia_papa',
        )
        open_empty = ExpedienteDocumental.objects.create(
            entidad_tipo='expediente_integral',
            entidad_id='integral-open-empty',
            estado='abierto',
            owner_operativo='Sociedad Inmobiliaria Santa Maria Ltda',
        )
        archived_with_content = ExpedienteDocumental.objects.create(
            entidad_tipo='expediente_integral',
            entidad_id='integral-archived-content',
            estado='archivado',
            owner_operativo='Sociedad Inmobiliaria Santa Maria Ltda',
        )
        ArchivoExpediente.objects.create(
            expediente=archived_with_content,
            categoria='imagen',
            subcategoria='05_fotos_y_videos',
            titulo_operativo='Foto local controlada',
            descripcion_objetiva='Vista interior del local asociada al expediente.',
            extension='.jpg',
            mime_type='image/jpeg',
            checksum_sha256=VALID_SHA256_THIRD,
            size_bytes=12345,
            storage_ref='storage/expedientes/locales/foto-local.jpg',
            origen_auditoria='carga-auditoria-revisar-controlada',
            estado_clasificacion='confirmado',
        )

        snapshot = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        expediente_ids = {item['id'] for item in snapshot.data['expedientes']}
        self.assertNotIn(archived_empty.id, expediente_ids)
        self.assertIn(open_empty.id, expediente_ids)
        self.assertIn(archived_with_content.id, expediente_ids)

    def test_expediente_admin_redacts_sensitive_operational_references(self):
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='https://legacy.example.test/type?token=secret',
            entidad_id='https://legacy.example.test/entity?token=secret',
            estado='abierto',
            owner_operativo='owner@example.test',
        )
        model_admin = ExpedienteDocumentalAdmin(ExpedienteDocumental, AdminSite())

        for raw_field in ('entidad_tipo', 'entidad_id', 'owner_operativo'):
            self.assertNotIn(raw_field, model_admin.list_display)
            self.assertNotIn(raw_field, model_admin.fields)
            self.assertNotIn(raw_field, model_admin.search_fields)
            self.assertNotIn(raw_field, model_admin.list_filter)
        self.assertEqual(set(model_admin.readonly_fields), set(model_admin.fields))
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, expediente))
        self.assertFalse(model_admin.has_delete_permission(None, expediente))
        self.assertEqual(model_admin.entidad_tipo_redacted(expediente), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(model_admin.entidad_id_redacted(expediente), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(model_admin.owner_operativo_redacted(expediente), REDACTED_SENSITIVE_REFERENCE)

    def test_archivo_expediente_api_accepts_non_pdf_evidence_and_snapshot_exposes_it(self):
        expediente = self._create_expediente(entidad_id='archivo-expediente')

        response = self.client.post(
            reverse('documentos-archivo-expediente-list'),
            self._archivo_expediente_payload(expediente['id']),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['extension'], '.jpg')
        self.assertEqual(response.data['categoria'], 'imagen')
        self.assertEqual(response.data['estado_clasificacion'], 'confirmado')
        self.assertFalse(DocumentoEmitido.objects.exists())
        self.assertTrue(
            AuditEvent.objects.filter(event_type='documentos.archivo_expediente.created').exists()
        )

        detail = self.client.get(reverse('documentos-archivo-expediente-detail', args=[response.data['id']]))
        snapshot = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['storage_ref'], 'storage/expedientes/locales/foto-local.jpg')
        self.assertEqual(len(snapshot.data['archivos_expediente']), 1)
        archivo_snapshot = snapshot.data['archivos_expediente'][0]
        self.assertEqual(archivo_snapshot['id'], response.data['id'])
        self.assertEqual(archivo_snapshot['expediente'], expediente['id'])
        self.assertEqual(archivo_snapshot['checksum_sha256'], VALID_SHA256_THIRD)
        self.assertEqual(archivo_snapshot['storage_ref'], 'storage/expedientes/locales/foto-local.jpg')
        self.assertEqual(len(snapshot.data['expediente_items']), 1)
        expediente_item = snapshot.data['expediente_items'][0]
        self.assertEqual(expediente_item['id'], f'archivo_expediente:{response.data["id"]}')
        self.assertEqual(expediente_item['source_model'], 'archivo_expediente')
        self.assertEqual(expediente_item['estado'], 'confirmado')

    def test_snapshot_expediente_items_unifies_order_and_hides_exact_duplicates(self):
        expediente = self._create_expediente(entidad_id='expediente-unificado')
        self._create_politica()
        documento = self._create_documento(expediente['id'], checksum=VALID_SHA256)
        archivo_response = self.client.post(
            reverse('documentos-archivo-expediente-list'),
            self._archivo_expediente_payload(expediente['id'], checksum_sha256=VALID_SHA256_THIRD),
            format='json',
        )
        self.assertEqual(archivo_response.status_code, status.HTTP_201_CREATED)

        alias_response = self.client.post(
            reverse('documentos-archivo-expediente-list'),
            self._archivo_expediente_payload(
                expediente['id'],
                checksum_sha256=VALID_SHA256_THIRD,
                titulo_operativo='Alias exacto foto local',
                storage_ref='storage/expedientes/locales/foto-local-alias.jpg',
                estado_clasificacion=EstadoClasificacionArchivoExpediente.EXACT_DUPLICATE,
                duplicate_of=archivo_response.data['id'],
            ),
            format='json',
        )
        self.assertEqual(alias_response.status_code, status.HTTP_201_CREATED)

        archivo_pdf_duplicado_response = self.client.post(
            reverse('documentos-archivo-expediente-list'),
            self._archivo_expediente_payload(
                expediente['id'],
                categoria='documento_fuente',
                subcategoria='01_titulos_y_escrituras',
                titulo_operativo='Copia exacta del PDF canonico',
                descripcion_objetiva='Mismo checksum que el documento PDF canonico.',
                extension='pdf',
                mime_type='application/pdf',
                checksum_sha256=VALID_SHA256,
                storage_ref='storage/expedientes/locales/contrato-duplicado.pdf',
            ),
            format='json',
        )
        self.assertEqual(archivo_pdf_duplicado_response.status_code, status.HTTP_201_CREATED)

        snapshot = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        self.assertEqual(len(snapshot.data['archivos_expediente']), 3)
        self.assertEqual(len(snapshot.data['expediente_items']), 2)
        expediente_item_ids = {item['id'] for item in snapshot.data['expediente_items']}
        self.assertIn(f'documento_emitido:{documento["id"]}', expediente_item_ids)
        self.assertIn(f'archivo_expediente:{archivo_response.data["id"]}', expediente_item_ids)
        self.assertNotIn(f'archivo_expediente:{alias_response.data["id"]}', expediente_item_ids)
        self.assertNotIn(f'archivo_expediente:{archivo_pdf_duplicado_response.data["id"]}', expediente_item_ids)

        documento_item = next(
            item for item in snapshot.data['expediente_items'] if item['source_model'] == 'documento_emitido'
        )
        archivo_item = next(
            item for item in snapshot.data['expediente_items'] if item['source_model'] == 'archivo_expediente'
        )
        self.assertEqual(documento_item['checksum_sha256'], VALID_SHA256)
        self.assertEqual(documento_item['clase'], 'pdf_canonico')
        self.assertEqual(archivo_item['checksum_sha256'], VALID_SHA256_THIRD)
        self.assertEqual(archivo_item['clase'], 'archivo_expediente')

    def test_archivo_expediente_rejects_sensitive_visible_refs(self):
        expediente = self._create_expediente(entidad_id='archivo-sensitive')
        cases = {
            'storage_ref': 'C:\\Users\\puigj\\Desktop\\Revisar\\foto-local.jpg',
            'origen_auditoria': 'C:\\Users\\puigj\\Desktop\\Revisar',
            'titulo_operativo': 'Foto local 11.111.111-1',
            'descripcion_objetiva': 'token=secret-value',
        }

        for field_name, value in cases.items():
            payload = self._archivo_expediente_payload(
                expediente['id'],
                checksum_sha256=VALID_SHA256_FOURTH,
                **{field_name: value},
            )
            response = self.client.post(reverse('documentos-archivo-expediente-list'), payload, format='json')

            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn(field_name, response.data)

        self.assertFalse(ArchivoExpediente.objects.exists())

    def test_archivo_expediente_apis_and_admin_redact_inherited_sensitive_refs(self):
        expediente = self._create_expediente(entidad_id='archivo-redaction')
        archivo = ArchivoExpediente.objects.create(
            expediente_id=expediente['id'],
            categoria='imagen',
            subcategoria='05_fotos_y_videos',
            titulo_operativo='Foto local 11.111.111-1',
            descripcion_objetiva='Archivo heredado con token=secret-value',
            extension='jpg',
            mime_type='image/jpeg',
            checksum_sha256=VALID_SHA256_THIRD,
            size_bytes=100,
            storage_ref='C:\\Users\\puigj\\Desktop\\Revisar\\foto-local.jpg',
            origen_auditoria='C:\\Users\\puigj\\Desktop\\Revisar',
            estado_clasificacion=EstadoClasificacionArchivoExpediente.CONFIRMED,
        )

        list_response = self.client.get(reverse('documentos-archivo-expediente-list'))
        detail_response = self.client.get(reverse('documentos-archivo-expediente-detail', args=[archivo.id]))
        snapshot_response = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        for payload in (
            list_response.data[0],
            detail_response.data,
            snapshot_response.data['archivos_expediente'][0],
            snapshot_response.data['expediente_items'][0],
        ):
            self.assertEqual(payload['titulo_operativo'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(payload['descripcion_objetiva'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(payload['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(payload['origen_auditoria'], REDACTED_SENSITIVE_REFERENCE)

        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('Users\\puigj', rendered)
        self.assertNotIn('token=secret', rendered)
        self.assertNotIn('11.111.111-1', rendered)

        model_admin = ArchivoExpedienteAdmin(ArchivoExpediente, AdminSite())
        for raw_field in ('titulo_operativo', 'descripcion_objetiva', 'storage_ref', 'origen_auditoria'):
            self.assertNotIn(raw_field, model_admin.fields)
            self.assertNotIn(raw_field, model_admin.search_fields)
        self.assertEqual(set(model_admin.readonly_fields), set(model_admin.fields))
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, archivo))
        self.assertFalse(model_admin.has_delete_permission(None, archivo))
        self.assertEqual(model_admin.titulo_operativo_redacted(archivo), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(model_admin.descripcion_objetiva_redacted(archivo), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(model_admin.storage_ref_redacted(archivo), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(model_admin.origen_auditoria_redacted(archivo), REDACTED_SENSITIVE_REFERENCE)

    def test_signature_policy_admin_blocks_manual_mutations(self):
        model_admin = PoliticaFirmaYNotariaAdmin(PoliticaFirmaYNotaria, AdminSite())
        policy = PoliticaFirmaYNotaria(
            tipo_documental='contrato_principal',
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            modo_firma_permitido='firma_simple',
            estado='activa',
        )

        self.assertEqual(set(model_admin.readonly_fields), set(model_admin.fields))
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None, policy))
        self.assertFalse(model_admin.has_delete_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None, policy))

    def _create_active_company(self, nombre, rut, socio_ruts):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=socio_ruts[0], activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=socio_ruts[1], activo=True)
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(participante_socio=socio_1, empresa_owner=empresa, porcentaje='60.00', vigente_desde='2026-01-01', activo=True)
        ParticipacionPatrimonial.objects.create(participante_socio=socio_2, empresa_owner=empresa, porcentaje='40.00', vigente_desde='2026-01-01', activo=True)
        return empresa

    def _create_contract_context(self, empresa, codigo, arr_rut):
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo} 123',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=codigo,
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arr {codigo}',
            rut=arr_rut,
            email=f'{codigo.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Dir {codigo}',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'CTR-{codigo}',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        return {'mandato': mandato, 'contrato': contrato, 'propiedad': propiedad}

    def test_auth_is_required_for_document_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('documentos-expediente-list'),
            reverse('documentos-politica-list'),
            reverse('documentos-documento-list'),
            reverse('documentos-archivo-expediente-list'),
        ]
        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_expediente_and_document_registers_user(self):
        expediente = self._create_expediente()
        self._create_politica()
        documento = self._create_documento(expediente['id'])

        detail = self.client.get(reverse('documentos-documento-detail', args=[documento['id']]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['usuario'], self.user.id)
        self.assertTrue(AuditEvent.objects.filter(event_type='documentos.documento_emitido.created').exists())

    def test_main_contract_policy_can_require_natural_tenant_document_profile(self):
        policy = self._create_politica(
            requiere_nacionalidad_arrendatario=True,
            requiere_estado_civil_arrendatario=True,
            requiere_profesion_arrendatario=True,
        )

        self.assertTrue(policy['requiere_nacionalidad_arrendatario'])
        self.assertTrue(policy['requiere_estado_civil_arrendatario'])
        self.assertTrue(policy['requiere_profesion_arrendatario'])

    def test_non_main_policy_rejects_natural_tenant_document_profile_requirements(self):
        response = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'anexo',
                'requiere_firma_arrendador': False,
                'requiere_firma_arrendatario': False,
                'requiere_codeudor': False,
                'requiere_nacionalidad_arrendatario': True,
                'requiere_estado_civil_arrendatario': False,
                'requiere_profesion_arrendatario': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PoliticaFirmaYNotaria.objects.filter(tipo_documental='anexo').exists())

    def test_document_storage_ref_must_be_pdf(self):
        expediente = self._create_expediente(entidad_id='pdf-guard')
        self._create_politica()

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/contracts/contrato-1.docx',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('storage_ref', response.data)

    def test_document_checksum_normalizes_to_canonical_digest(self):
        expediente = self._create_expediente(entidad_id='checksum-canonical')
        self._create_politica()

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': f' {VALID_SHA256.upper()} ',
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/contracts/contrato-canonical.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['checksum'], VALID_SHA256)
        self.assertEqual(DocumentoEmitido.objects.get(pk=response.data['id']).checksum, VALID_SHA256)

    def test_document_checksum_must_be_sha256(self):
        expediente = self._create_expediente(entidad_id='checksum-guard')
        self._create_politica()

        for checksum in ('checksum-operativo-sin-digest', f'sha256:{VALID_SHA256}'):
            with self.subTest(checksum=checksum):
                response = self.client.post(
                    reverse('documentos-documento-list'),
                    {
                        'expediente': expediente['id'],
                        'tipo_documental': 'contrato_principal',
                        'version_plantilla': 'v1',
                        'checksum': checksum,
                        'fecha_carga': '2026-03-18T10:00:00-03:00',
                        'origen': 'carga_externa_controlada',
                        'estado': 'emitido',
                        'storage_ref': 'storage/contracts/contrato-1.pdf',
                        'firma_arrendador_registrada': False,
                        'firma_arrendatario_registrada': False,
                        'firma_codeudor_registrada': False,
                        'recepcion_notarial_registrada': False,
                        'comprobante_notarial': None,
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('checksum', response.data)

    def test_document_full_clean_requires_responsible_user(self):
        expediente = self._create_expediente(entidad_id='user-guard')
        document = DocumentoEmitido(
            expediente_id=expediente['id'],
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='storage/contracts/contrato-1.pdf',
        )

        with self.assertRaises(ValidationError) as error:
            document.full_clean()

        self.assertIn('usuario', error.exception.message_dict)

    def test_document_full_clean_requires_active_template(self):
        expediente = self._create_expediente(entidad_id='template-domain-guard')
        self._create_politica()
        PlantillaDocumental.objects.filter(
            tipo_documental='contrato_principal',
            version_plantilla='v1',
        ).delete()
        document = DocumentoEmitido(
            expediente_id=expediente['id'],
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=self.user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='storage/contracts/template-domain-guard.pdf',
        )

        with self.assertRaises(ValidationError) as error:
            document.full_clean()

        self.assertIn('version_plantilla', error.exception.message_dict)

    def test_document_requires_active_policy_for_type(self):
        expediente = self._create_expediente(entidad_id='policy-guard')
        self._ensure_template('contrato_principal', 'v1')

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/contracts/policy-guard.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tipo_documental', response.data)

        self._create_politica()
        created = self._create_documento(expediente['id'], storage_ref='storage/contracts/policy-guard.pdf')
        self.assertEqual(created['tipo_documental'], 'contrato_principal')

    def test_policy_deactivation_rejected_when_documents_depend_on_type(self):
        expediente = self._create_expediente(entidad_id='policy-deactivate-guard')
        policy = self._create_politica()
        self._create_documento(expediente['id'])

        response = self.client.patch(
            reverse('documentos-politica-detail', args=[policy['id']]),
            {'estado': 'inactiva'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertEqual(PoliticaFirmaYNotaria.objects.get(pk=policy['id']).estado, 'activa')

    def test_used_policy_api_rejects_signature_requirement_mutation(self):
        expediente = self._create_expediente(entidad_id='policy-immutability')
        policy = self._create_politica()
        self._create_documento(expediente['id'])

        response = self.client.patch(
            reverse('documentos-politica-detail', args=[policy['id']]),
            {
                'requiere_notaria': True,
                'modo_firma_permitido': 'firma_avanzada',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('requiere_notaria', response.data)
        self.assertIn('modo_firma_permitido', response.data)
        stored = PoliticaFirmaYNotaria.objects.get(pk=policy['id'])
        self.assertFalse(stored.requiere_notaria)
        self.assertEqual(stored.modo_firma_permitido, 'firma_simple')

    def test_policy_update_rolls_back_when_view_audit_fails(self):
        policy = self._create_politica()
        audit_count = AuditEvent.objects.count()

        with patch('documentos.views.create_audit_event', side_effect=RuntimeError('policy audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'policy audit unavailable'):
                self.client.patch(
                    reverse('documentos-politica-detail', args=[policy['id']]),
                    {'requiere_codeudor': True},
                    format='json',
                )

        stored = PoliticaFirmaYNotaria.objects.get(pk=policy['id'])
        self.assertFalse(stored.requiere_codeudor)
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_expediente_state_update_rolls_back_when_state_audit_fails(self):
        from audit.services import create_audit_event as real_create_audit_event

        expediente = self._create_expediente(entidad_id='expediente-state-audit-rollback')
        audit_count = AuditEvent.objects.count()

        def fail_state_change_audit(**kwargs):
            if kwargs.get('event_type') == 'documentos.expediente.state_changed':
                raise RuntimeError('expediente state audit unavailable')
            return real_create_audit_event(**kwargs)

        with patch('documentos.views.create_audit_event', side_effect=fail_state_change_audit):
            with self.assertRaisesRegex(RuntimeError, 'expediente state audit unavailable'):
                self.client.patch(
                    reverse('documentos-expediente-detail', args=[expediente['id']]),
                    {'estado': 'cerrado'},
                    format='json',
                )

        stored = ExpedienteDocumental.objects.get(pk=expediente['id'])
        self.assertEqual(stored.estado, 'abierto')
        self.assertEqual(AuditEvent.objects.count(), audit_count)

    def test_expediente_state_change_audit_includes_metadata(self):
        expediente = self._create_expediente(entidad_id='expediente-state-audit-metadata')

        response = self.client.patch(
            reverse('documentos-expediente-detail', args=[expediente['id']]),
            {'estado': 'cerrado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        state_event = AuditEvent.objects.get(
            event_type='documentos.expediente.state_changed',
            entity_type='expediente',
            entity_id=str(expediente['id']),
        )
        self.assertEqual(
            state_event.metadata,
            {
                'campo_estado': 'estado',
                'estado_anterior': 'abierto',
                'estado_nuevo': 'cerrado',
            },
        )

    def test_document_storage_ref_must_be_non_sensitive_pdf_reference(self):
        expediente = self._create_expediente(entidad_id='pdf-sensitive-guard')
        self._create_politica()

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'https://storage.example.test/contracts/contrato-1.pdf?token=secret',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('storage_ref', response.data)

    def test_document_apis_redact_inherited_sensitive_storage_ref(self):
        expediente = self._create_expediente(entidad_id='pdf-redaction')
        self._create_politica()
        document = DocumentoEmitido.objects.create(
            expediente_id=expediente['id'],
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            checksum=VALID_SHA256,
            fecha_carga=timezone.now(),
            usuario=self.user,
            origen='carga_externa_controlada',
            estado='emitido',
            storage_ref='https://storage.example.test/contracts/contrato-1.pdf?token=secret',
            evidencia_formalizacion_ref='https://docs.example.test/formalizacion?token=secret',
        )

        list_response = self.client.get(reverse('documentos-documento-list'))
        detail_response = self.client.get(reverse('documentos-documento-detail', args=[document.id]))
        snapshot_response = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(list_response.data[0]['evidencia_formalizacion_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['evidencia_formalizacion_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['documentos_emitidos'][0]['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['documentos_emitidos'][0]['evidencia_formalizacion_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['documentos_emitidos'][0]['checksum'], VALID_SHA256)
        self.assertEqual(snapshot_response.data['documentos_emitidos'][0]['usuario'], self.user.id)
        self.assertIn('fecha_carga', snapshot_response.data['documentos_emitidos'][0])
        self.assertIn('comprobante_notarial', snapshot_response.data['documentos_emitidos'][0])
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('storage.example.test', rendered)
        self.assertNotIn('docs.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_main_contract_policy_requires_both_signatures(self):
        response = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'contrato_principal',
                'requiere_firma_arrendador': False,
                'requiere_firma_arrendatario': True,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_cannot_be_formalized_without_required_signatures(self):
        expediente = self._create_expediente(entidad_id='2')
        self._create_politica()
        documento = self._create_documento(expediente['id'])

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_formalization_requires_traceable_evidence(self):
        expediente = self._create_expediente(entidad_id='2C')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {},
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_formalizacion_ref', formalize.data)

    def test_document_formalization_rejects_sensitive_evidence_ref(self):
        expediente = self._create_expediente(entidad_id='2D')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': 'https://docs.example.test/formalizacion?token=secret'},
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_formalizacion_ref', formalize.data)

    def test_document_cannot_be_created_as_formalized_from_generic_endpoint(self):
        expediente = self._create_expediente(entidad_id='2A')
        self._create_politica()

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'formalizado',
                'storage_ref': 'storage/contracts/direct-formalized-create.pdf',
                'firma_arrendador_registrada': True,
                'firma_arrendatario_registrada': True,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        self.assertFalse(AuditEvent.objects.filter(event_type=FORMALIZATION_AUDIT_EVENT_TYPE).exists())

    def test_document_cannot_be_patched_as_formalized_from_generic_endpoint(self):
        expediente = self._create_expediente(entidad_id='2B')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        response = self.client.patch(
            reverse('documentos-documento-detail', args=[documento['id']]),
            {'estado': 'formalizado'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        stored = DocumentoEmitido.objects.get(pk=documento['id'])
        self.assertEqual(stored.estado, EstadoDocumento.ISSUED)
        self.assertFalse(AuditEvent.objects.filter(event_type=FORMALIZATION_AUDIT_EVENT_TYPE).exists())

    def test_document_with_notary_policy_requires_notary_receipt(self):
        expediente = self._create_expediente(entidad_id='3')
        self._create_politica(requiere_notaria=True)
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'evidencia_formalizacion_ref': FORMALIZATION_REF,
            },
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_notary_receipt_must_be_issued_formalized_or_archived(self):
        expediente = self._create_expediente(entidad_id='3B')
        self._create_politica(requiere_notaria=True)
        self._create_politica(
            tipo_documental='comprobante_notarial',
            requiere_firma_arrendador=False,
            requiere_firma_arrendatario=False,
        )
        receipt = self._create_documento(
            expediente['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='notary-v1',
            checksum=VALID_SHA256,
            storage_ref='storage/contracts/notary-draft.pdf',
            estado='borrador',
        )
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'evidencia_formalizacion_ref': FORMALIZATION_REF,
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprobante_notarial', formalize.data)

    def test_notary_receipt_must_have_notarial_document_type(self):
        expediente = self._create_expediente(entidad_id='3C')
        self._create_politica(requiere_notaria=True)
        receipt = self._create_documento(
            expediente['id'],
            tipo_documental='contrato_principal',
            version_plantilla='notary-wrong-type-v1',
            checksum=VALID_SHA256,
            storage_ref='storage/contracts/notary-wrong-type.pdf',
        )
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
            checksum=VALID_SHA256_ALT,
            storage_ref='storage/contracts/notary-wrong-type-target.pdf',
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'evidencia_formalizacion_ref': FORMALIZATION_REF,
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprobante_notarial', formalize.data)

    def test_document_can_be_formalized_when_policy_is_satisfied(self):
        expediente = self._create_expediente(entidad_id='4')
        self._create_politica(requiere_notaria=True)
        self._create_politica(
            tipo_documental='comprobante_notarial',
            requiere_firma_arrendador=False,
            requiere_firma_arrendatario=False,
        )
        receipt = self._create_documento(
            expediente['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='notary-v1',
            checksum=VALID_SHA256,
            storage_ref='storage/contracts/notary.pdf',
        )
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'evidencia_formalizacion_ref': FORMALIZATION_REF,
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self.assertEqual(formalize.data['estado'], EstadoDocumento.FORMALIZED)
        self.assertEqual(formalize.data['evidencia_formalizacion_ref'], FORMALIZATION_REF)
        event = AuditEvent.objects.get(
            event_type=FORMALIZATION_AUDIT_EVENT_TYPE,
            entity_type='documento_emitido',
            entity_id=str(formalize.data['id']),
        )
        self.assertEqual(event.actor_user, self.user)
        self.assertEqual(event.metadata['evidencia_formalizacion_ref'], FORMALIZATION_REF)
        self.assertTrue(event.metadata['firma_arrendador_registrada'])
        self.assertTrue(event.metadata['firma_arrendatario_registrada'])
        self.assertFalse(event.metadata['firma_codeudor_registrada'])
        self.assertTrue(event.metadata['recepcion_notarial_registrada'])
        self.assertEqual(event.metadata['comprobante_notarial_id'], str(receipt['id']))
        state_event = AuditEvent.objects.get(
            event_type='documentos.documento_emitido.state_changed',
            entity_type='documento_emitido',
            entity_id=str(formalize.data['id']),
        )
        self.assertEqual(
            state_event.metadata,
            {
                'campo_estado': 'estado',
                'estado_anterior': EstadoDocumento.ISSUED,
                'estado_nuevo': EstadoDocumento.FORMALIZED,
            },
        )

    def test_formalization_rolls_back_when_audit_creation_fails(self):
        from audit.services import create_audit_event as real_create_audit_event

        expediente = self._create_expediente(entidad_id='4A')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        calls = {'count': 0}

        def create_audit_then_fail_state_change(**kwargs):
            calls['count'] += 1
            if calls['count'] == 1:
                return real_create_audit_event(**kwargs)
            raise RuntimeError('state audit unavailable')

        with patch('documentos.views.create_audit_event', side_effect=create_audit_then_fail_state_change):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse('documentos-documento-formalizar', args=[documento['id']]),
                    {'evidencia_formalizacion_ref': FORMALIZATION_REF},
                    format='json',
                )

        self.assertEqual(calls['count'], 2)
        stored = DocumentoEmitido.objects.get(pk=documento['id'])
        self.assertEqual(stored.estado, EstadoDocumento.ISSUED)
        self.assertEqual(stored.evidencia_formalizacion_ref, '')
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=FORMALIZATION_AUDIT_EVENT_TYPE,
                entity_type='documento_emitido',
                entity_id=str(documento['id']),
            ).exists()
        )

    def test_formalized_document_cannot_be_mutated_from_generic_endpoint(self):
        expediente = self._create_expediente(entidad_id='4D')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)

        response = self.client.patch(
            reverse('documentos-documento-detail', args=[documento['id']]),
            {'checksum': VALID_SHA256_ALT},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', response.data)
        stored = DocumentoEmitido.objects.get(pk=documento['id'])
        self.assertEqual(stored.checksum, documento['checksum'])
        self.assertEqual(stored.estado, EstadoDocumento.FORMALIZED)

    def test_formalized_document_cannot_be_formalized_again(self):
        expediente = self._create_expediente(entidad_id='4E')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        first = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'firma_arrendador_registrada': False,
                'evidencia_formalizacion_ref': 'formalizacion-controlada-doc-002',
            },
            format='json',
        )

        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', second.data)
        stored = DocumentoEmitido.objects.get(pk=documento['id'])
        self.assertTrue(stored.firma_arrendador_registrada)
        self.assertEqual(stored.estado, EstadoDocumento.FORMALIZED)

    def test_formalized_document_can_have_traceable_corrective_version(self):
        expediente = self._create_expediente(entidad_id='4G')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)

        correction = self._create_documento(
            expediente['id'],
            version_plantilla='v2',
            checksum=VALID_SHA256_ALT,
            storage_ref='storage/contracts/contrato-1-v2.pdf',
            documento_origen=documento['id'],
            correccion_ref='correction-ticket-doc-001',
        )

        self.assertEqual(correction['documento_origen'], documento['id'])
        self.assertEqual(correction['correccion_ref'], 'correction-ticket-doc-001')
        event = AuditEvent.objects.get(
            event_type=CORRECTION_AUDIT_EVENT_TYPE,
            entity_type='documento_emitido',
            entity_id=str(correction['id']),
        )
        self.assertEqual(event.actor_user, self.user)
        self.assertEqual(event.metadata['documento_origen_id'], str(documento['id']))
        self.assertEqual(event.metadata['expediente_id'], str(expediente['id']))
        self.assertEqual(event.metadata['tipo_documental'], 'contrato_principal')
        self.assertEqual(event.metadata['version_plantilla'], 'v2')
        self.assertEqual(event.metadata['checksum'], VALID_SHA256_ALT)
        self.assertEqual(event.metadata['storage_ref'], 'storage/contracts/contrato-1-v2.pdf')
        self.assertEqual(event.metadata['correccion_ref'], 'correction-ticket-doc-001')
        snapshot = self.client.get(reverse('documentos-snapshot'))
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        correction_snapshot = next(
            item for item in snapshot.data['documentos_emitidos'] if item['id'] == correction['id']
        )
        self.assertEqual(correction_snapshot['documento_origen'], documento['id'])
        self.assertEqual(correction_snapshot['correccion_ref'], 'correction-ticket-doc-001')

    def test_corrective_version_creation_rolls_back_when_dedicated_audit_fails(self):
        from audit.services import create_audit_event as real_create_audit_event

        expediente = self._create_expediente(entidad_id='4G-correction-audit-rollback')
        self._create_politica()
        origin = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[origin['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self._ensure_template('contrato_principal', 'v2')
        document_count = DocumentoEmitido.objects.count()
        audit_count = AuditEvent.objects.count()

        def fail_dedicated_correction_audit(**kwargs):
            if kwargs.get('event_type') == CORRECTION_AUDIT_EVENT_TYPE:
                raise RuntimeError('correction audit unavailable')
            return real_create_audit_event(**kwargs)

        with patch('documentos.views.create_audit_event', side_effect=fail_dedicated_correction_audit):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse('documentos-documento-list'),
                    {
                        'expediente': expediente['id'],
                        'tipo_documental': 'contrato_principal',
                        'version_plantilla': 'v2',
                        'checksum': VALID_SHA256_ALT,
                        'fecha_carga': '2026-03-18T10:00:00-03:00',
                        'origen': 'carga_externa_controlada',
                        'estado': 'emitido',
                        'storage_ref': 'storage/contracts/contrato-correction-rollback.pdf',
                        'firma_arrendador_registrada': False,
                        'firma_arrendatario_registrada': False,
                        'firma_codeudor_registrada': False,
                        'recepcion_notarial_registrada': False,
                        'comprobante_notarial': None,
                        'documento_origen': origin['id'],
                        'correccion_ref': 'correction-ticket-doc-rollback',
                    },
                    format='json',
                )

        self.assertEqual(DocumentoEmitido.objects.count(), document_count)
        self.assertEqual(AuditEvent.objects.count(), audit_count)
        self.assertFalse(
            DocumentoEmitido.objects.filter(storage_ref='storage/contracts/contrato-correction-rollback.pdf').exists()
        )

    def test_existing_document_cannot_be_converted_to_corrective_version(self):
        expediente = self._create_expediente(entidad_id='4G-convert-correction')
        self._create_politica()
        origin = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[origin['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        target = self._create_documento(
            expediente['id'],
            version_plantilla='v2',
            checksum=VALID_SHA256_ALT,
            storage_ref='storage/contracts/contrato-target-v2.pdf',
        )

        response = self.client.patch(
            reverse('documentos-documento-detail', args=[target['id']]),
            {
                'documento_origen': origin['id'],
                'correccion_ref': 'correction-ticket-doc-conversion',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('documento_origen', response.data)
        stored = DocumentoEmitido.objects.get(pk=target['id'])
        self.assertIsNone(stored.documento_origen_id)
        self.assertEqual(stored.correccion_ref, '')
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type=CORRECTION_AUDIT_EVENT_TYPE,
                entity_type='documento_emitido',
                entity_id=str(target['id']),
            ).exists()
        )

    def test_corrective_version_trace_cannot_be_mutated_from_generic_endpoint(self):
        expediente = self._create_expediente(entidad_id='4G-mutate-correction')
        self._create_politica()
        origin = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[origin['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        correction = self._create_documento(
            expediente['id'],
            version_plantilla='v2',
            checksum=VALID_SHA256_ALT,
            storage_ref='storage/contracts/contrato-correction-v2.pdf',
            documento_origen=origin['id'],
            correccion_ref='correction-ticket-doc-immutable',
        )

        response = self.client.patch(
            reverse('documentos-documento-detail', args=[correction['id']]),
            {'correccion_ref': 'correction-ticket-doc-mutated'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('documento_origen', response.data)
        stored = DocumentoEmitido.objects.get(pk=correction['id'])
        self.assertEqual(stored.documento_origen_id, origin['id'])
        self.assertEqual(stored.correccion_ref, 'correction-ticket-doc-immutable')

    def test_corrective_version_requires_formalized_origin(self):
        expediente = self._create_expediente(entidad_id='4H')
        self._create_politica()
        documento = self._create_documento(expediente['id'])
        self._ensure_template('contrato_principal', 'v2')

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v2',
                'checksum': VALID_SHA256_ALT,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/contracts/contrato-1-v2.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
                'documento_origen': documento['id'],
                'correccion_ref': 'correction-ticket-doc-002',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('documento_origen', response.data)

    def test_corrective_version_rejects_sensitive_correction_ref(self):
        expediente = self._create_expediente(entidad_id='4I')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self._ensure_template('contrato_principal', 'v2')

        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v2',
                'checksum': VALID_SHA256_ALT,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/contracts/contrato-1-v2.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
                'documento_origen': documento['id'],
                'correccion_ref': 'https://docs.example.test/correccion?token=secret',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('correccion_ref', response.data)

    def test_document_cannot_be_formalized_with_notary_receipt_from_other_expediente(self):
        expediente_a = self._create_expediente(entidad_id='4A')
        expediente_b = self._create_expediente(entidad_id='4B')
        self._create_politica(requiere_notaria=True)
        self._create_politica(
            tipo_documental='comprobante_notarial',
            requiere_firma_arrendador=False,
            requiere_firma_arrendatario=False,
        )
        receipt = self._create_documento(
            expediente_b['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='notary-v1',
            checksum=VALID_SHA256,
            storage_ref='storage/contracts/notary-other.pdf',
        )
        documento = self._create_documento(
            expediente_a['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'evidencia_formalizacion_ref': FORMALIZATION_REF,
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_canceled_document_cannot_be_formalized(self):
        expediente = self._create_expediente(entidad_id='4C')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            estado='cancelado',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', formalize.data)

    def test_draft_document_cannot_be_formalized(self):
        expediente = self._create_expediente(entidad_id='4F')
        self._create_politica()
        documento = self._create_documento(
            expediente['id'],
            estado='borrador',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('estado', formalize.data)
        stored = DocumentoEmitido.objects.get(pk=documento['id'])
        self.assertEqual(stored.estado, EstadoDocumento.DRAFT)
        self.assertFalse(AuditEvent.objects.filter(event_type=FORMALIZATION_AUDIT_EVENT_TYPE).exists())

    def test_codeudor_signature_is_enforced_by_policy(self):
        empresa = self._create_active_company('Docs Codeudor', '76111111-1', ('11111111-1', '22222222-2'))
        context = self._create_contract_context(empresa, 'DOC-CODEB', '55555555-5')
        CodeudorSolidario.objects.create(
            contrato=context['contrato'],
            snapshot_identidad={'nombre': 'Codeudor Controlado', 'rut': '12345678-5'},
        )
        expediente = self._create_expediente(
            entidad_tipo='contrato',
            entidad_id=str(context['contrato'].id),
            owner_operativo=f"mandato:{context['mandato'].id}",
        )
        self._create_politica(requiere_codeudor=True)
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codeudor_signature_policy_does_not_block_contract_without_codeudor(self):
        empresa = self._create_active_company('Docs Sin Codeudor', '76222222-2', ('33333333-3', '44444444-4'))
        context = self._create_contract_context(empresa, 'DOC-NOCODEB', '66666666-6')
        expediente = self._create_expediente(
            entidad_tipo='contrato',
            entidad_id=str(context['contrato'].id),
            owner_operativo=f"mandato:{context['mandato'].id}",
        )
        self._create_politica(requiere_codeudor=True)
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'evidencia_formalizacion_ref': FORMALIZATION_REF},
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self.assertFalse(formalize.data['firma_codeudor_registrada'])
        self.assertEqual(formalize.data['estado'], EstadoDocumento.FORMALIZED)

    def test_contract_expediente_rejects_owner_operativo_from_another_mandate(self):
        company_a = self._create_active_company('Docs API A', '88888888-8', ('11111111-1', '22222222-2'))
        company_b = self._create_active_company('Docs API B', '99999999-9', ('33333333-3', '44444444-4'))
        context_a = self._create_contract_context(company_a, 'DOC-API-A', '55555555-5')
        context_b = self._create_contract_context(company_b, 'DOC-API-B', '66666666-6')

        response = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(context_a['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{context_b['mandato'].id}",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DocumentosScopeAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.user = user_model.objects.create_user(
            username='docs-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.company_a = self._create_active_company('Docs A', '76.311.245-4', ('11.111.111-1', '22.222.222-2'))
        self.company_b = self._create_active_company('Docs B', '76.390.560-8', ('33.333.333-3', '44.444.444-4'))
        self.context_a = self._create_contract_context(self.company_a, 'DOC-A', '55.555.555-5')
        self.context_b = self._create_contract_context(self.company_b, 'DOC-B', '66.666.666-6')
        scope = Scope.objects.create(
            code=f'company-{self.company_a.id}',
            name=f'Empresa {self.company_a.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(self.company_a.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=self.user, role=self.operator_role, scope=scope, is_primary=True)
        self.client.force_authenticate(self.user)

        self.policy = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'contrato_principal',
                'requiere_firma_arrendador': True,
                'requiere_firma_arrendatario': True,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(self.policy.status_code, status.HTTP_403_FORBIDDEN)
        PoliticaFirmaYNotaria.objects.create(
            tipo_documental='contrato_principal',
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            requiere_codeudor=False,
            requiere_notaria=False,
            modo_firma_permitido='firma_simple',
            estado='activa',
        )
        PlantillaDocumental.objects.create(
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            plantilla_ref='templates/contrato_principal/v1',
            checksum_plantilla=VALID_SHA256,
            descripcion='Plantilla controlada para pruebas de scope.',
            estado='activa',
        )

        self.expediente_a = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(self.context_a['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{self.context_a['mandato'].id}",
            },
            format='json',
        )
        self.assertEqual(self.expediente_a.status_code, status.HTTP_201_CREATED)

        admin_user = user_model.objects.create_user(
            username='docs-admin',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(admin_user)
        self.expediente_b = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(self.context_b['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{self.context_b['mandato'].id}",
            },
            format='json',
        )
        self.assertEqual(self.expediente_b.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(self.user)

        self.documento_a = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': self.expediente_a.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/doc-a.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )
        self.assertEqual(self.documento_a.status_code, status.HTTP_201_CREATED)
        self.archivo_a = ArchivoExpediente.objects.create(
            expediente_id=self.expediente_a.data['id'],
            categoria='imagen',
            subcategoria='05_fotos_y_videos',
            titulo_operativo='Foto scope A',
            descripcion_objetiva='Evidencia visual scope A.',
            extension='.jpg',
            mime_type='image/jpeg',
            checksum_sha256=VALID_SHA256_THIRD,
            size_bytes=10,
            storage_ref='storage/expedientes/scope-a/foto.jpg',
            origen_auditoria='auditoria-scope-a',
            estado_clasificacion=EstadoClasificacionArchivoExpediente.CONFIRMED,
        )
        self.archivo_b = ArchivoExpediente.objects.create(
            expediente_id=self.expediente_b.data['id'],
            categoria='imagen',
            subcategoria='05_fotos_y_videos',
            titulo_operativo='Foto scope B',
            descripcion_objetiva='Evidencia visual scope B.',
            extension='.jpg',
            mime_type='image/jpeg',
            checksum_sha256=VALID_SHA256_FOURTH,
            size_bytes=20,
            storage_ref='storage/expedientes/scope-b/foto.jpg',
            origen_auditoria='auditoria-scope-b',
            estado_clasificacion=EstadoClasificacionArchivoExpediente.CONFIRMED,
        )

    def _create_active_company(self, nombre, rut, socio_ruts):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=socio_ruts[0], activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=socio_ruts[1], activo=True)
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(participante_socio=socio_1, empresa_owner=empresa, porcentaje='60.00', vigente_desde='2026-01-01', activo=True)
        ParticipacionPatrimonial.objects.create(participante_socio=socio_2, empresa_owner=empresa, porcentaje='40.00', vigente_desde='2026-01-01', activo=True)
        return empresa

    def _create_contract_context(self, empresa, codigo, arr_rut):
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo} 123',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=codigo,
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arr {codigo}',
            rut=arr_rut,
            email=f'{codigo.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Dir {codigo}',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'CTR-{codigo}',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        return {'mandato': mandato, 'contrato': contrato, 'propiedad': propiedad}

    def test_operator_company_scope_limits_document_lists(self):
        expedientes = self.client.get(reverse('documentos-expediente-list'))
        documentos = self.client.get(reverse('documentos-documento-list'))
        archivos = self.client.get(reverse('documentos-archivo-expediente-list'))
        snapshot = self.client.get(reverse('documentos-snapshot'))

        self.assertEqual(expedientes.status_code, status.HTTP_200_OK)
        self.assertEqual(documentos.status_code, status.HTTP_200_OK)
        self.assertEqual(archivos.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        self.assertEqual(len(expedientes.data), 1)
        self.assertEqual(expedientes.data[0]['id'], self.expediente_a.data['id'])
        self.assertEqual(len(documentos.data), 1)
        self.assertEqual(documentos.data[0]['id'], self.documento_a.data['id'])
        self.assertEqual(len(archivos.data), 1)
        self.assertEqual(archivos.data[0]['id'], self.archivo_a.id)
        self.assertEqual(
            [item['id'] for item in snapshot.data['archivos_expediente']],
            [self.archivo_a.id],
        )

    def test_operator_cannot_create_document_for_expediente_outside_scope(self):
        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': self.expediente_b.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/doc-b.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_create_archivo_expediente_for_expediente_outside_scope(self):
        response = self.client.post(
            reverse('documentos-archivo-expediente-list'),
            {
                'expediente': self.expediente_b.data['id'],
                'categoria': 'imagen',
                'subcategoria': '05_fotos_y_videos',
                'titulo_operativo': 'Foto fuera de scope',
                'descripcion_objetiva': 'Evidencia visual fuera de scope.',
                'extension': 'jpg',
                'mime_type': 'image/jpeg',
                'checksum_sha256': 'e' * 64,
                'size_bytes': 10,
                'storage_ref': 'storage/expedientes/scope-b/nueva-foto.jpg',
                'origen_auditoria': 'auditoria-scope-b',
                'estado_clasificacion': 'confirmado',
                'duplicate_of': None,
                'fecha_archivo': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_create_expediente_for_contract_outside_scope(self):
        response = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(self.context_b['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{self.context_b['mandato'].id}",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_list_hides_mismatched_contract_and_owner_expediente(self):
        context_c = self._create_contract_context(self.company_a, 'DOC-C', '77.777.777-7')
        ExpedienteDocumental.objects.create(
            entidad_tipo='contrato',
            entidad_id=str(context_c['contrato'].id),
            estado='abierto',
            owner_operativo=f"mandato:{self.context_b['mandato'].id}",
        )

        response = self.client.get(reverse('documentos-expediente-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.expediente_a.data['id'])

    def test_operator_cannot_create_or_update_global_signature_policy(self):
        create_response = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'anexo',
                'requiere_firma_arrendador': True,
                'requiere_firma_arrendatario': True,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )
        existing_policy = PoliticaFirmaYNotaria.objects.get(tipo_documental='contrato_principal')
        update_response = self.client.patch(
            reverse('documentos-politica-detail', args=[existing_policy.id]),
            {'requiere_notaria': True},
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_formalization_rejects_notary_receipt_outside_scope_at_serializer_boundary(self):
        PoliticaFirmaYNotaria.objects.filter(tipo_documental='contrato_principal').update(requiere_notaria=True)
        out_of_scope_receipt = DocumentoEmitido.objects.create(
            expediente_id=self.expediente_b.data['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='v1',
            checksum=VALID_SHA256_ALT,
            fecha_carga=timezone.now(),
            usuario=self.user,
            origen='carga_externa_controlada',
            estado=EstadoDocumento.ISSUED,
            storage_ref='storage/docs/notary-outside-scope.pdf',
        )

        response = self.client.post(
            reverse('documentos-documento-formalizar', args=[self.documento_a.data['id']]),
            {
                'firma_arrendador_registrada': True,
                'firma_arrendatario_registrada': True,
                'recepcion_notarial_registrada': True,
                'evidencia_formalizacion_ref': FORMALIZATION_REF,
                'comprobante_notarial': out_of_scope_receipt.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comprobante_notarial', response.data)
        self.assertEqual(response.data['comprobante_notarial'][0].code, 'does_not_exist')
