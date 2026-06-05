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


def transition_event_has_transition_metadata(event: AuditEvent) -> bool:
    metadata = event.metadata if isinstance(event.metadata, dict) else {}
    return all(_metadata_value_present(metadata, key) for key in REQUIRED_STATE_TRANSITION_METADATA_FIELDS)


def state_changed_event_has_transition_metadata(event: AuditEvent) -> bool:
    return transition_event_has_transition_metadata(event)


def _normalized_values(values: Iterable[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text:
            normalized.append(text)
    return normalized


def _event_prefix_query(event_type_prefixes: Iterable[str] | None) -> Q:
    query = Q()
    for prefix in _normalized_values(event_type_prefixes):
        normalized_prefix = str(prefix or '').strip().rstrip('.')
        if normalized_prefix:
            query |= Q(event_type__startswith=f'{normalized_prefix}.')
    return query


def _event_suffix_query(event_type_suffixes: Iterable[str] | None) -> Q:
    query = Q()
    for suffix in _normalized_values(event_type_suffixes):
        normalized_suffix = suffix if suffix.startswith('.') else f'.{suffix.lstrip(".")}'
        query |= Q(event_type__endswith=normalized_suffix)
    return query


def count_audit_events_without_transition_metadata(
    *,
    event_type_prefixes: Iterable[str] | None = None,
    event_type_suffixes: Iterable[str] | None = None,
    event_types: Iterable[str] | None = None,
) -> int:
    query = Q()
    prefix_query = _event_prefix_query(event_type_prefixes)
    suffix_query = _event_suffix_query(event_type_suffixes)
    exact_event_types = _normalized_values(event_types)

    if prefix_query and suffix_query:
        query |= prefix_query & suffix_query
    elif prefix_query:
        query |= prefix_query
    elif suffix_query:
        query |= suffix_query

    if exact_event_types:
        query |= Q(event_type__in=exact_event_types)

    if not query:
        return 0

    events = AuditEvent.objects.filter(query).only('metadata')
    return sum(1 for event in events if not transition_event_has_transition_metadata(event))


def count_state_changed_events_without_transition_metadata(event_type_prefixes: Iterable[str]) -> int:
    return count_audit_events_without_transition_metadata(
        event_type_prefixes=event_type_prefixes,
        event_type_suffixes=('.state_changed',),
    )
