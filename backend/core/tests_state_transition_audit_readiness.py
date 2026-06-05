from django.test import TestCase

from audit.models import AuditEvent
from core.state_transition_audit_readiness import (
    count_audit_events_without_transition_metadata,
    count_state_changed_events_without_transition_metadata,
    state_changed_event_has_transition_metadata,
)


class StateTransitionAuditReadinessTests(TestCase):
    def test_counts_state_changed_event_without_transition_metadata(self):
        AuditEvent.objects.create(
            event_type='canales.configuracion_notificacion_contrato.state_changed',
            entity_type='configuracion_notificacion_contrato',
            entity_id='1',
            summary='Cambio heredado incompleto.',
            metadata={'estado_nuevo': False},
        )

        count = count_state_changed_events_without_transition_metadata(['canales'])

        self.assertEqual(count, 1)

    def test_boolean_transition_values_are_valid_metadata(self):
        event = AuditEvent.objects.create(
            event_type='canales.configuracion_notificacion_contrato.state_changed',
            entity_type='configuracion_notificacion_contrato',
            entity_id='1',
            summary='Cambio heredado completo.',
            metadata={
                'campo_estado': 'activa',
                'estado_anterior': True,
                'estado_nuevo': False,
            },
        )

        self.assertTrue(state_changed_event_has_transition_metadata(event))
        self.assertEqual(count_state_changed_events_without_transition_metadata(['canales']), 0)

    def test_counts_status_updated_event_without_transition_metadata_by_suffix(self):
        AuditEvent.objects.create(
            event_type='sii.f29_preparacion.status_updated',
            entity_type='f29_preparacion',
            entity_id='1',
            summary='Actualizacion heredada incompleta.',
            metadata={'estado_nuevo': 'preparado'},
        )

        count = count_audit_events_without_transition_metadata(
            event_type_prefixes=['sii'],
            event_type_suffixes=['status_updated'],
        )

        self.assertEqual(count, 1)

    def test_counts_exact_event_types_without_transition_metadata(self):
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id='1',
            summary='Actualizacion anual heredada incompleta.',
            metadata={'estado_nuevo': 'aprobado'},
        )
        AuditEvent.objects.create(
            event_type='sii.f29_preparacion.status_updated',
            entity_type='f29_preparacion',
            entity_id='2',
            summary='Actualizacion mensual fuera del filtro exacto.',
            metadata={'estado_nuevo': 'aprobado'},
        )

        count = count_audit_events_without_transition_metadata(
            event_types=['sii.ddjj_preparacion.status_updated']
        )

        self.assertEqual(count, 1)
