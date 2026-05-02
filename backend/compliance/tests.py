from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from reporting.tests import ReportingAPITests

from .models import ExportacionSensible, PoliticaRetencionDatos


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
        self.assertTrue(AuditEvent.objects.filter(event_type='compliance.exportacion_sensible.accessed').exists())

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

        denied = self.client.get(reverse('compliance-export-content', args=[prepared.data['id']]))
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)

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
