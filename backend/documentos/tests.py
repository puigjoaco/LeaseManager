from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent

from .models import DocumentoEmitido, EstadoDocumento, PoliticaFirmaYNotaria


class DocumentosAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='docs', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_expediente(self, entidad_tipo='contrato', entidad_id='1', owner_operativo='mandato:1'):
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
        return response.data

    def _create_documento(self, expediente_id, **overrides):
        payload = {
            'expediente': expediente_id,
            'tipo_documental': 'contrato_principal',
            'version_plantilla': 'v1',
            'checksum': 'abc123',
            'fecha_carga': '2026-03-18T10:00:00-03:00',
            'origen': 'generado_sistema',
            'estado': 'emitido',
            'storage_ref': 'storage/contracts/contrato-1.pdf',
            'firma_arrendador_registrada': False,
            'firma_arrendatario_registrada': False,
            'firma_codeudor_registrada': False,
            'recepcion_notarial_registrada': False,
            'comprobante_notarial': None,
        }
        payload.update(overrides)
        response = self.client.post(reverse('documentos-documento-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def test_auth_is_required_for_document_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('documentos-expediente-list'),
            reverse('documentos-politica-list'),
            reverse('documentos-documento-list'),
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
            {},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

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
            {'recepcion_notarial_registrada': True},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_can_be_formalized_when_policy_is_satisfied(self):
        expediente = self._create_expediente(entidad_id='4')
        self._create_politica(requiere_notaria=True)
        receipt = self._create_documento(
            expediente['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='notary-v1',
            checksum='notary123',
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
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self.assertEqual(formalize.data['estado'], EstadoDocumento.FORMALIZED)
        self.assertTrue(AuditEvent.objects.filter(event_type='documentos.documento_emitido.formalized').exists())

    def test_codeudor_signature_is_enforced_by_policy(self):
        expediente = self._create_expediente(entidad_id='5')
        self._create_politica(requiere_codeudor=True)
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
