from core.reference_validation import redact_sensitive_reference


CORRECTION_AUDIT_EVENT_TYPE = 'documentos.documento_emitido.corrective_version_created'
CORRECTION_AUDIT_ENTITY_TYPE = 'documento_emitido'


def build_correction_audit_metadata(document):
    return {
        'documento_origen_id': str(document.documento_origen_id or ''),
        'expediente_id': str(document.expediente_id),
        'tipo_documental': document.tipo_documental,
        'version_plantilla': str(document.version_plantilla or '').strip(),
        'checksum': str(document.checksum or '').strip(),
        'storage_ref': redact_sensitive_reference(document.storage_ref),
        'correccion_ref': redact_sensitive_reference(document.correccion_ref),
        'estado': document.estado,
    }
