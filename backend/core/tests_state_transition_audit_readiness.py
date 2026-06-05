from django.test import TestCase

from audit.models import AuditEvent
from core.state_transition_audit_readiness import (
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
