from core.reference_validation import redact_sensitive_reference


FORMALIZATION_AUDIT_EVENT_TYPE = 'documentos.documento_emitido.formalized'
FORMALIZATION_AUDIT_ENTITY_TYPE = 'documento_emitido'


def build_formalization_audit_metadata(document):
    return {
        'expediente_id': str(document.expediente_id),
        'tipo_documental': document.tipo_documental,
        'estado': document.estado,
        'evidencia_formalizacion_ref': redact_sensitive_reference(document.evidencia_formalizacion_ref),
        'firma_arrendador_registrada': bool(document.firma_arrendador_registrada),
        'firma_arrendatario_registrada': bool(document.firma_arrendatario_registrada),
        'firma_codeudor_registrada': bool(document.firma_codeudor_registrada),
        'recepcion_notarial_registrada': bool(document.recepcion_notarial_registrada),
        'comprobante_notarial_id': str(document.comprobante_notarial_id or ''),
    }
