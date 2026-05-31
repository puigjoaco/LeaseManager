import json
import os
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cobranza.models import PagoMensual
from conciliacion.models import ConexionBancaria, MovimientoBancarioImportado
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import ComunidadPatrimonial, Empresa, ModoRepresentacionComunidad, Propiedad, Socio, TipoInmueble

from .admin import AuditEventAdmin, ManualResolutionAdmin
from .models import AuditEvent, ManualResolution
from .services import (
    GENERIC_MANUAL_RESOLUTION_CREATED_EVENT_TYPE,
    GENERIC_MANUAL_RESOLUTION_STATUS_CHANGED_EVENT_TYPE,
    GENERIC_MANUAL_RESOLUTION_UPDATED_EVENT_TYPE,
    MANUAL_RESOLUTION_AUDIT_ENTITY_TYPE,
)


class AuditAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='audit', password='secret123')
        self.client.force_authenticate(self.user)

    def test_auth_is_required_for_manual_resolution_endpoints(self):
        client = self.client_class()
        response = client.get(reverse('manual-resolution-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manual_resolution_list_supports_filters(self):
        first = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-1',
            summary='Primera',
            status='open',
        )
        ManualResolution.objects.create(
            category='migration.arrendatario.invalid_rut',
            scope_type='legacy_arrendatario',
            scope_reference='arr-1',
            summary='Segunda',
            status='resolved',
        )

        response = self.client.get(
            f"{reverse('manual-resolution-list')}?status=open&category={first.category}&scope_type=legacy_propiedad"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['scope_reference'], 'prop-1')

    def test_manual_resolution_apis_redact_sensitive_metadata(self):
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='https://audit.example.test/resolution?token=secret',
            summary='Metadata heredada en https://audit.example.test/summary?token=secret',
            rationale='Rationale heredado con bearer token',
            metadata={
                'safe_ref': 'controlled-reference',
                'callback_url': 'https://provider.example.test/token/value',
                'access_token': 'opaque-token-value',
                'nested': {
                    'authorization': 'Bearer inherited-value',
                    'result_ref': 'controlled-result',
                },
            },
        )

        list_response = self.client.get(reverse('manual-resolution-list'))
        detail_response = self.client.get(reverse('manual-resolution-detail', args=[resolution.pk]))
        snapshot_response = self.client.get(reverse('audit-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        for payload in (
            list_response.data[0],
            detail_response.data,
            snapshot_response.data['manual_resolutions'][0],
        ):
            self.assertEqual(payload['scope_reference'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(payload['summary'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(payload['rationale'], REDACTED_SENSITIVE_REFERENCE)
        for metadata in (
            list_response.data[0]['metadata'],
            detail_response.data['metadata'],
            snapshot_response.data['manual_resolutions'][0]['metadata'],
        ):
            self.assertEqual(metadata['safe_ref'], 'controlled-reference')
            self.assertEqual(metadata['callback_url'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(metadata['access_token'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(metadata['nested']['authorization'], REDACTED_SENSITIVE_REFERENCE)
            self.assertEqual(metadata['nested']['result_ref'], 'controlled-result')

        for response in (list_response, detail_response, snapshot_response):
            body = response.content.decode()
            self.assertNotIn('audit.example.test', body)
            self.assertNotIn('provider.example.test', body)
            self.assertNotIn('opaque-token-value', body)
            self.assertNotIn('Bearer inherited-value', body)

    def test_audit_event_api_redacts_sensitive_metadata(self):
        admin = get_user_model().objects.create_user(
            username='audit-admin',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(admin)
        AuditEvent.objects.create(
            actor_identifier='service-account-token-value',
            event_type='audit.metadata.test',
            entity_type='empresa',
            entity_id='https://audit.example.test/entities/1?token=secret',
            summary='Evento con metadata heredada en https://audit.example.test/event?token=secret',
            metadata={
                'safe_ref': 'controlled-event',
                'callback_url': 'https://audit.example.test/token/value',
                'api_key': 'opaque-key-value',
            },
            request_id='request-token-value',
        )

        response = self.client.get(reverse('audit-events'))
        snapshot_response = self.client.get(reverse('audit-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['actor_identifier'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data[0]['actor_user_display'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data[0]['entity_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data[0]['summary'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data[0]['request_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['events'][0]['actor_user_display'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['events'][0]['entity_id'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['events'][0]['summary'], REDACTED_SENSITIVE_REFERENCE)
        metadata = response.data[0]['metadata']
        self.assertEqual(metadata['safe_ref'], 'controlled-event')
        self.assertEqual(metadata['callback_url'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(metadata['api_key'], REDACTED_SENSITIVE_REFERENCE)
        for raw_body in (response.content.decode(), snapshot_response.content.decode()):
            self.assertNotIn('audit.example.test', raw_body)
            self.assertNotIn('opaque-key-value', raw_body)
            self.assertNotIn('service-account-token-value', raw_body)
            self.assertNotIn('request-token-value', raw_body)

    def test_audit_admin_redacts_sensitive_event_and_resolution_fields(self):
        event = AuditEvent.objects.create(
            actor_identifier='service-account-token-value',
            event_type='audit.metadata.test',
            entity_type='empresa',
            entity_id='https://audit.example.test/entities/1?token=secret',
            summary='Evento heredado en https://audit.example.test/event?token=secret',
            metadata={
                'safe_ref': 'controlled-event',
                'callback_url': 'https://audit.example.test/callback?token=secret',
                'headers': {'authorization': 'Bearer inherited-value'},
            },
            request_id='request-token-value',
        )
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='https://audit.example.test/resolution?token=secret',
            summary='Resolucion heredada en https://audit.example.test/summary?token=secret',
            rationale='Rationale heredado con bearer token',
            metadata={
                'safe_ref': 'controlled-resolution',
                'api_key': 'opaque-key-value',
                'nested': {'callback': 'https://audit.example.test/nested?token=secret'},
            },
        )

        event_admin = AuditEventAdmin(AuditEvent, AdminSite())
        resolution_admin = ManualResolutionAdmin(ManualResolution, AdminSite())

        for raw_field in ('actor_identifier', 'entity_id', 'summary', 'metadata', 'request_id', 'ip_address'):
            self.assertNotIn(raw_field, event_admin.fields)
            self.assertNotIn(raw_field, event_admin.search_fields)
        for raw_field in ('scope_reference', 'summary', 'rationale', 'metadata'):
            self.assertNotIn(raw_field, resolution_admin.fields)
            self.assertNotIn(raw_field, resolution_admin.search_fields)

        self.assertFalse(event_admin.has_add_permission(None))
        self.assertFalse(event_admin.has_delete_permission(None, event))
        self.assertFalse(resolution_admin.has_add_permission(None))
        self.assertFalse(resolution_admin.has_delete_permission(None, resolution))

        self.assertEqual(event_admin.actor_identifier_redacted(event), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(event_admin.entity_id_redacted(event), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(event_admin.summary_redacted(event), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(event_admin.request_id_redacted(event), REDACTED_SENSITIVE_REFERENCE)
        event_metadata = json.loads(event_admin.metadata_redacted(event))
        self.assertEqual(event_metadata['safe_ref'], 'controlled-event')
        self.assertEqual(event_metadata['callback_url'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(event_metadata['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)

        self.assertEqual(resolution_admin.scope_reference_redacted(resolution), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(resolution_admin.summary_redacted(resolution), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(resolution_admin.rationale_redacted(resolution), REDACTED_SENSITIVE_REFERENCE)
        resolution_metadata = json.loads(resolution_admin.metadata_redacted(resolution))
        self.assertEqual(resolution_metadata['safe_ref'], 'controlled-resolution')
        self.assertEqual(resolution_metadata['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(resolution_metadata['nested']['callback'], REDACTED_SENSITIVE_REFERENCE)

    def test_unknown_income_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            scope_type='movimiento_bancario',
            scope_reference='123',
            summary='Ingreso desconocido',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_specialized_resolution_cannot_be_created_via_generic_endpoint(self):
        response = self.client.post(
            reverse('manual-resolution-list'),
            {
                'category': 'conciliacion.ingreso_desconocido',
                'scope_type': 'movimiento_bancario',
                'scope_reference': '123',
                'summary': 'Ingreso desconocido creado directo',
                'status': 'open',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)
        self.assertFalse(
            ManualResolution.objects.filter(
                category='conciliacion.ingreso_desconocido',
                scope_type='movimiento_bancario',
                scope_reference='123',
            ).exists()
        )

    def test_generic_resolution_rejects_sensitive_fields(self):
        response = self.client.post(
            reverse('manual-resolution-list'),
            {
                'category': 'operacion.revision_manual',
                'scope_type': 'operacion',
                'scope_reference': 'https://audit.example.test/scope?token=secret',
                'summary': 'Revision en https://audit.example.test/summary?token=secret',
                'rationale': 'Rationale con bearer token',
                'metadata': {'api_key': 'opaque-key-value'},
                'status': 'open',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scope_reference', response.data)
        self.assertIn('summary', response.data)
        self.assertIn('rationale', response.data)
        self.assertIn('metadata', response.data)
        self.assertFalse(ManualResolution.objects.filter(category='operacion.revision_manual').exists())

    def test_generic_resolution_create_uses_current_user_and_open_status(self):
        other_user = get_user_model().objects.create_user(
            username='resolution-spoof',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )

        response = self.client.post(
            reverse('manual-resolution-list'),
            {
                'category': 'operacion.revision_manual',
                'scope_type': 'operacion',
                'scope_reference': 'operacion-review-001',
                'summary': 'Revision operativa trazable',
                'requested_by': other_user.pk,
                'resolved_by': other_user.pk,
                'status': 'in_review',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        resolution = ManualResolution.objects.get(category='operacion.revision_manual')
        self.assertEqual(resolution.requested_by, self.user)
        self.assertIsNone(resolution.resolved_by)
        self.assertIsNone(resolution.resolved_at)
        self.assertEqual(resolution.status, ManualResolution.Status.OPEN)
        self.assertEqual(response.data['requested_by'], self.user.pk)
        self.assertIsNone(response.data['resolved_by'])
        self.assertEqual(response.data['status'], ManualResolution.Status.OPEN)
        event = AuditEvent.objects.get(
            event_type=GENERIC_MANUAL_RESOLUTION_CREATED_EVENT_TYPE,
            entity_type=MANUAL_RESOLUTION_AUDIT_ENTITY_TYPE,
            entity_id=str(resolution.pk),
        )
        self.assertEqual(event.actor_user, self.user)
        self.assertEqual(event.metadata['resolution_category'], resolution.category)
        self.assertEqual(event.metadata['scope_type'], resolution.scope_type)
        self.assertEqual(event.metadata['status'], ManualResolution.Status.OPEN)

    def test_generic_resolution_create_rolls_back_when_audit_event_fails(self):
        with patch(
            'audit.views.create_manual_resolution_lifecycle_event',
            side_effect=RuntimeError('audit unavailable'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    reverse('manual-resolution-list'),
                    {
                        'category': 'operacion.revision_manual',
                        'scope_type': 'operacion',
                        'scope_reference': 'operacion-review-rollback',
                        'summary': 'Revision operativa sin auditoria',
                    },
                    format='json',
                )

        self.assertFalse(ManualResolution.objects.filter(scope_reference='operacion-review-rollback').exists())

    def test_generic_resolution_cannot_be_created_closed(self):
        response = self.client.post(
            reverse('manual-resolution-list'),
            {
                'category': 'operacion.revision_manual',
                'scope_type': 'operacion',
                'scope_reference': 'operacion-review-closed',
                'summary': 'Revision operativa cerrada directo',
                'rationale': 'Motivo trazable',
                'status': ManualResolution.Status.RESOLVED,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        self.assertFalse(ManualResolution.objects.filter(scope_reference='operacion-review-closed').exists())

    def test_generic_resolution_close_stamps_current_actor(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='operacion-review-close',
            summary='Revision operativa',
            requested_by=self.user,
            status=ManualResolution.Status.OPEN,
        )
        closer = get_user_model().objects.create_user(
            username='resolution-closer',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.client.force_authenticate(closer)

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': ManualResolution.Status.RESOLVED, 'rationale': 'Cierre operativo trazable'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ManualResolution.Status.RESOLVED)
        self.assertEqual(resolution.requested_by, self.user)
        self.assertEqual(resolution.resolved_by, closer)
        self.assertIsNotNone(resolution.resolved_at)
        self.assertEqual(response.data['resolved_by'], closer.pk)
        self.assertIsNotNone(response.data['resolved_at'])
        event = AuditEvent.objects.get(
            event_type=GENERIC_MANUAL_RESOLUTION_STATUS_CHANGED_EVENT_TYPE,
            entity_type=MANUAL_RESOLUTION_AUDIT_ENTITY_TYPE,
            entity_id=str(resolution.pk),
        )
        self.assertEqual(event.actor_user, closer)
        self.assertEqual(event.metadata['previous_status'], ManualResolution.Status.OPEN)
        self.assertEqual(event.metadata['status'], ManualResolution.Status.RESOLVED)
        self.assertEqual(event.metadata['changed_fields'], ['rationale', 'status'])

    def test_generic_resolution_close_rolls_back_when_audit_event_fails(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='operacion-review-close-rollback',
            summary='Revision operativa',
            requested_by=self.user,
            status=ManualResolution.Status.OPEN,
        )

        with patch(
            'audit.views.create_manual_resolution_lifecycle_event',
            side_effect=RuntimeError('audit unavailable'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.patch(
                    reverse('manual-resolution-detail', args=[resolution.pk]),
                    {'status': ManualResolution.Status.RESOLVED, 'rationale': 'Cierre operativo trazable'},
                    format='json',
                )

        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ManualResolution.Status.OPEN)
        self.assertIsNone(resolution.resolved_by)
        self.assertIsNone(resolution.resolved_at)

    def test_generic_resolution_update_creates_audit_event(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='operacion-review-update',
            summary='Revision operativa',
            requested_by=self.user,
            status=ManualResolution.Status.OPEN,
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {
                'summary': 'Revision operativa ajustada',
                'metadata': {'tracking_ref': 'manual-resolution-update-001'},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resolution.refresh_from_db()
        self.assertEqual(resolution.summary, 'Revision operativa ajustada')
        event = AuditEvent.objects.get(
            event_type=GENERIC_MANUAL_RESOLUTION_UPDATED_EVENT_TYPE,
            entity_type=MANUAL_RESOLUTION_AUDIT_ENTITY_TYPE,
            entity_id=str(resolution.pk),
        )
        self.assertEqual(event.actor_user, self.user)
        self.assertEqual(event.metadata['status'], ManualResolution.Status.OPEN)
        self.assertEqual(event.metadata['changed_fields'], ['metadata', 'summary'])

    def test_generic_resolution_update_rolls_back_when_audit_event_fails(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='operacion-review-update-rollback',
            summary='Revision operativa',
            requested_by=self.user,
            status=ManualResolution.Status.OPEN,
        )

        with patch(
            'audit.views.create_manual_resolution_lifecycle_event',
            side_effect=RuntimeError('audit unavailable'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.patch(
                    reverse('manual-resolution-detail', args=[resolution.pk]),
                    {'summary': 'Revision operativa sin auditoria'},
                    format='json',
                )

        resolution.refresh_from_db()
        self.assertEqual(resolution.summary, 'Revision operativa')

    def test_generic_resolution_close_requires_rationale(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='operacion-review-close-empty',
            summary='Revision operativa',
            requested_by=self.user,
            status=ManualResolution.Status.OPEN,
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': ManualResolution.Status.RESOLVED},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rationale', response.data)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ManualResolution.Status.OPEN)
        self.assertIsNone(resolution.resolved_by)
        self.assertIsNone(resolution.resolved_at)

    def test_closed_generic_resolution_cannot_be_reopened(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='operacion-review-reopen',
            summary='Revision operativa',
            rationale='Cierre operativo trazable',
            requested_by=self.user,
            resolved_by=self.user,
            status=ManualResolution.Status.RESOLVED,
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': ManualResolution.Status.IN_REVIEW},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, ManualResolution.Status.RESOLVED)

    def test_generic_resolution_cannot_be_converted_to_specialized_category(self):
        resolution = ManualResolution.objects.create(
            category='operacion.revision_manual',
            scope_type='operacion',
            scope_reference='op-1',
            summary='Revision operativa',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'category': 'conciliacion.movimiento_cargo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)
        resolution.refresh_from_db()
        self.assertEqual(resolution.category, 'operacion.revision_manual')

    def test_specialized_resolution_cannot_be_retargeted_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            scope_type='movimiento_bancario',
            scope_reference='124',
            summary='Cargo bancario',
            status='open',
            metadata={'movimiento_id': 124},
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {
                'scope_reference': '999',
                'metadata': {'movimiento_id': 999},
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('scope_reference', response.data)
        self.assertIn('metadata', response.data)
        resolution.refresh_from_db()
        self.assertEqual(resolution.scope_reference, '124')
        self.assertEqual(resolution.metadata['movimiento_id'], 124)

    def test_unknown_income_resolution_cannot_be_marked_superseded_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            scope_type='movimiento_bancario',
            scope_reference='123',
            summary='Ingreso desconocido',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'superseded', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            scope_type='movimiento_bancario',
            scope_reference='124',
            summary='Cargo bancario',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_migration_owner_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='legacy-123',
            summary='Owner manual pendiente',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_distribution_conflict_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_type='pago_mensual',
            scope_reference='123',
            summary='Conflicto DTE distribucion',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resolve_property_owner_manual_resolution_creates_comunidad_and_propiedad(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-1',
            summary='Owner manual',
            metadata={
                'codigo': 46,
                'codigo_propiedad': None,
                'direccion': 'Av. Santa Maria 9500 Dpto 1014',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-1',
                'comuna': 'Santiago',
                'region': '',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Av Santa Maria 9500 Dpto 1014',
                'representante_socio_id': socio_1.pk,
                'representante_modo': ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, 'resolved')
        self.assertEqual(ComunidadPatrimonial.objects.count(), 1)
        self.assertEqual(Propiedad.objects.count(), 1)
        self.assertEqual(Propiedad.objects.get().comunidad_owner_id, ComunidadPatrimonial.objects.get().pk)
        self.assertEqual(ComunidadPatrimonial.objects.get().representacion_vigente().modo_representacion, ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT)

    def test_resolve_property_owner_manual_resolution_allows_designated_representative(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        socio_designado = Socio.objects.create(nombre='Joaquin', rut='33333333-3', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-2',
            summary='Owner manual',
            metadata={
                'codigo': 47,
                'direccion': 'Av. Comunidad Designada 123',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-2',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Designada',
                'representante_socio_id': socio_designado.pk,
                'representante_modo': ModoRepresentacionComunidad.DESIGNATED,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get()
        self.assertEqual(comunidad.representacion_vigente().modo_representacion, ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(comunidad.representante_socio_id, socio_designado.pk)

    def test_resolve_property_owner_designated_mode_can_use_default_representative(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        default_representative = Socio.objects.create(nombre='Joaquin Puig Vittini', rut='17.366.287-4', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-default-representative',
            summary='Owner manual',
            metadata={
                'codigo': 48,
                'direccion': 'DIRECCION_TEST_NO_PRODUCTIVA',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-3',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                ],
            },
        )

        with patch.dict(os.environ, {'MIGRATION_CURRENT_COMMUNITY_REPRESENTATIVE_RUT': default_representative.rut}):
            response = self.client.post(
                reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
                {
                    'nombre_comunidad': 'Comunidad Designada Default',
                    'representante_modo': ModoRepresentacionComunidad.DESIGNATED,
                    'region': 'RM',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get()
        self.assertEqual(comunidad.representacion_vigente().modo_representacion, ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(comunidad.representante_socio_id, default_representative.pk)

    def test_resolve_property_owner_manual_resolution_accepts_mixed_participants(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(razon_social='Inmobiliaria Puig SpA', rut='76311245-4', estado='activa')
        socio_empresa_1 = Socio.objects.create(nombre='Socio Empresa Uno', rut='44444444-4', activo=True)
        socio_empresa_2 = Socio.objects.create(nombre='Socio Empresa Dos', rut='55555555-5', activo=True)
        from patrimonio.models import ParticipacionPatrimonial

        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_1,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_2,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-3',
            summary='Owner manual mixed',
            metadata={
                'codigo': 48,
                'direccion': 'Edificio Q 1014',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-3',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Mixta Edificio Q',
                'representante_socio_id': socio_1.pk,
                'representante_modo': ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                'region': 'RM',
                'participaciones': [
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_1.pk,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'empresa',
                        'participante_id': empresa.pk,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Mixta Edificio Q')
        participant_types = {item.participante_tipo for item in comunidad.participaciones.all()}
        self.assertEqual(participant_types, {'socio', 'empresa'})


class AuditManualResolutionScopeTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.user = user_model.objects.create_user(
            username='audit-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.context_a = self._create_operational_context(
            code='AUD-A',
            company_name='Empresa Audit A',
            company_rut='76.311.245-4',
            tenant_rut='11.111.111-1',
        )
        self.context_b = self._create_operational_context(
            code='AUD-B',
            company_name='Empresa Audit B',
            company_rut='76.390.560-8',
            tenant_rut='22.222.222-2',
        )
        self._assign_company_scope(self.user, self.context_a['empresa'])
        self.client.force_authenticate(self.user)

    def _assign_company_scope(self, user, empresa):
        scope = Scope.objects.create(
            code=f'company-{empresa.id}',
            name=f'Empresa {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=user, role=self.operator_role, scope=scope, is_primary=True)

    def _create_operational_context(self, *, code, company_name, company_rut, tenant_rut):
        empresa = Empresa.objects.create(razon_social=company_name, rut=company_rut, estado='activa')
        propiedad = Propiedad.objects.create(
            direccion=f'Av. {code} 100',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=code,
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{code}',
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
            nombre_razon_social=f'Arrendatario {code}',
            rut=tenant_rut,
            email=f'{code.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Direccion {code}',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'CTR-{code}',
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
        periodo = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        pago = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100000.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pendiente',
            codigo_conciliacion_efectivo='111',
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key=f'provider-{code}',
            credencial_ref=f'cred-{code}',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        return {
            'empresa': empresa,
            'propiedad': propiedad,
            'cuenta': cuenta,
            'mandato': mandato,
            'contrato': contrato,
            'periodo': periodo,
            'pago': pago,
            'conexion': conexion,
        }

    def _create_movement_resolution(self, context, *, category, movement_type, amount, summary):
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=context['conexion'],
            fecha_movimiento='2026-01-08',
            tipo_movimiento=movement_type,
            monto=amount,
            descripcion_origen=summary,
        )
        resolution = ManualResolution.objects.create(
            category=category,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary=summary,
            status='open',
        )
        return resolution, movimiento

    def test_manual_resolution_list_only_returns_in_scope_resolutions(self):
        visible_resolution, _ = self._create_movement_resolution(
            self.context_a,
            category='conciliacion.ingreso_desconocido',
            movement_type='abono',
            amount='150000.00',
            summary='Ingreso visible',
        )
        hidden_resolution, _ = self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope',
        )
        hidden_migration = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-1',
            summary='Migracion fuera de scope',
            metadata={'codigo': 46, 'direccion': 'Av. Santa Maria 9500 Dpto 1014'},
        )
        visible_distribution_conflict = ManualResolution.objects.create(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_type='pago_mensual',
            scope_reference=str(self.context_a['pago'].pk),
            summary='Conflicto distribucion visible',
            metadata={'pago_mensual_id': self.context_a['pago'].pk},
        )
        hidden_distribution_conflict = ManualResolution.objects.create(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_type='pago_mensual',
            scope_reference=str(self.context_b['pago'].pk),
            summary='Conflicto distribucion fuera de scope',
            metadata={'pago_mensual_id': self.context_b['pago'].pk},
        )

        response = self.client.get(reverse('manual-resolution-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in response.data},
            {str(visible_resolution.pk), str(visible_distribution_conflict.pk)},
        )
        self.assertNotIn(str(hidden_resolution.pk), {item['id'] for item in response.data})
        self.assertNotIn(str(hidden_migration.pk), {item['id'] for item in response.data})
        self.assertNotIn(str(hidden_distribution_conflict.pk), {item['id'] for item in response.data})

    def test_audit_snapshot_only_includes_in_scope_manual_resolutions(self):
        visible_resolution, _ = self._create_movement_resolution(
            self.context_a,
            category='conciliacion.ingreso_desconocido',
            movement_type='abono',
            amount='150000.00',
            summary='Ingreso visible snapshot',
        )
        self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope snapshot',
        )

        response = self.client.get(reverse('audit-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['manual_resolutions']), 1)
        self.assertEqual(response.data['manual_resolutions'][0]['id'], str(visible_resolution.pk))

    def test_manual_resolution_detail_returns_404_when_resolution_is_out_of_scope(self):
        hidden_resolution, _ = self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope detail',
        )

        response = self.client.get(reverse('manual-resolution-detail', args=[hidden_resolution.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resolve_charge_movement_returns_404_when_resolution_is_out_of_scope(self):
        hidden_resolution, _ = self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope resolver',
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[hidden_resolution.pk]),
            {'rationale': 'No deberia poder resolverse.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resolve_unknown_income_rejects_payment_outside_scope(self):
        visible_resolution, _ = self._create_movement_resolution(
            self.context_a,
            category='conciliacion.ingreso_desconocido',
            movement_type='abono',
            amount='150000.00',
            summary='Ingreso visible resolver',
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[visible_resolution.pk]),
            {
                'pago_mensual_id': self.context_b['pago'].pk,
                'periodo_economico': '2026-01',
                'criterio_aplicado': 'Intento de cruce manual fuera de scope.',
                'evidencia_regularizacion_ref': 'unknown-income-scope-test',
                'rationale': 'Intento de cruce fuera de scope.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['pago_mensual_id'][0], 'El pago mensual indicado queda fuera del scope asignado.')

    def test_audit_event_list_only_returns_in_scope_events(self):
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        reviewer_user = get_user_model().objects.create_user(
            username='audit-reviewer-scope',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        reviewer_scope = Scope.objects.create(
            code=f'company-{self.context_a["empresa"].id}-review',
            name=f'Empresa reviewer {self.context_a["empresa"].razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(self.context_a['empresa'].id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=reviewer_user, role=reviewer_role, scope=reviewer_scope, is_primary=True)
        reviewer_client = self.client_class()
        reviewer_client.force_authenticate(reviewer_user)

        AuditEvent.objects.create(
            event_type='conciliacion.movimiento_bancario.created',
            entity_type='movimiento_bancario',
            entity_id=str(self.context_a['pago'].pk),
            summary='Evento visible',
            metadata={'empresa_id': self.context_a['empresa'].pk, 'cuenta_recaudadora_id': self.context_a['cuenta'].pk},
        )
        AuditEvent.objects.create(
            event_type='conciliacion.movimiento_bancario.created',
            entity_type='movimiento_bancario',
            entity_id=str(self.context_b['pago'].pk),
            summary='Evento fuera de scope',
            metadata={'empresa_id': self.context_b['empresa'].pk, 'cuenta_recaudadora_id': self.context_b['cuenta'].pk},
        )
        AuditEvent.objects.create(
            event_type='patrimonio.socio.updated',
            entity_type='socio',
            entity_id=str(self.context_a['empresa'].pk),
            summary='Evento colision empresa no visible',
        )
        AuditEvent.objects.create(
            event_type='contratos.arrendatario.updated',
            entity_type='arrendatario',
            entity_id=str(self.context_a['propiedad'].pk),
            summary='Evento colision propiedad no visible',
        )

        response = reviewer_client.get(reverse('audit-events'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item['summary'] for item in response.data}, {'Evento visible'})
