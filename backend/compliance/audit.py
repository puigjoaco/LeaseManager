from audit.services import create_audit_event


EXPORT_AUDIT_ENTITY_TYPE = 'exportacion_sensible'
EXPORT_PREPARED_EVENT_TYPE = 'compliance.exportacion_sensible.prepared'
EXPORT_ACCESSED_EVENT_TYPE = 'compliance.exportacion_sensible.accessed'
EXPORT_ACCESS_DENIED_EVENT_TYPE = 'compliance.exportacion_sensible.access_denied'
EXPORT_REVOKED_EVENT_TYPE = 'compliance.exportacion_sensible.revoked'
EXPORT_AUDIT_EVENT_TYPES = [
    EXPORT_PREPARED_EVENT_TYPE,
    EXPORT_ACCESSED_EVENT_TYPE,
    EXPORT_ACCESS_DENIED_EVENT_TYPE,
    EXPORT_REVOKED_EVENT_TYPE,
]


def build_export_audit_metadata(export, *, extra_metadata=None):
    metadata = {
        'categoria_dato': export.categoria_dato,
        'export_kind': export.export_kind,
        'scope_resumen': export.scope_resumen,
        'payload_hash': str(export.payload_hash or '').strip(),
        'estado': export.estado,
        'hold_activo': bool(export.hold_activo),
        'expires_at': export.expires_at.isoformat() if export.expires_at else '',
        'created_by_id': str(export.created_by_id or ''),
    }
    metadata.update(extra_metadata or {})
    return metadata


def create_export_audit_event(
    *,
    event_type,
    export,
    summary,
    actor_user,
    ip_address=None,
    severity='info',
    extra_metadata=None,
):
    return create_audit_event(
        event_type=event_type,
        entity_type=EXPORT_AUDIT_ENTITY_TYPE,
        entity_id=str(export.pk),
        summary=summary,
        severity=severity,
        actor_user=actor_user,
        ip_address=ip_address,
        metadata=build_export_audit_metadata(export, extra_metadata=extra_metadata),
    )
