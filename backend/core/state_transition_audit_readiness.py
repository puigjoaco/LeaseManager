from __future__ import annotations

from collections.abc import Iterable

from django.db.models import Q

from audit.models import AuditEvent


REQUIRED_STATE_TRANSITION_METADATA_FIELDS = (
    'campo_estado',
    'estado_anterior',
    'estado_nuevo',
)


def _metadata_value_present(metadata: dict, key: str) -> bool:
    if key not in metadata:
        return False
    value = metadata[key]
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def state_changed_event_has_transition_metadata(event: AuditEvent) -> bool:
    metadata = event.metadata if isinstance(event.metadata, dict) else {}
    return all(_metadata_value_present(metadata, key) for key in REQUIRED_STATE_TRANSITION_METADATA_FIELDS)


def count_state_changed_events_without_transition_metadata(event_type_prefixes: Iterable[str]) -> int:
    query = Q()
    for prefix in event_type_prefixes:
        normalized_prefix = str(prefix or '').strip().rstrip('.')
        if normalized_prefix:
            query |= Q(event_type__startswith=f'{normalized_prefix}.')
    if not query:
        return 0

    events = AuditEvent.objects.filter(query, event_type__endswith='.state_changed').only('metadata')
    return sum(1 for event in events if not state_changed_event_has_transition_metadata(event))
