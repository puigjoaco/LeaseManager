from collections import Counter

from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditEvent
from core.reference_validation import is_non_sensitive_reference, redact_sensitive_reference

from .correction_audit import (
    CORRECTION_AUDIT_ENTITY_TYPE,
    CORRECTION_AUDIT_EVENT_TYPE,
    build_correction_audit_metadata,
)
from .formalization_audit import (
    FORMALIZATION_AUDIT_ENTITY_TYPE,
    FORMALIZATION_AUDIT_EVENT_TYPE,
    build_formalization_audit_metadata,
)
from .models import (
    DocumentoEmitido,
    EstadoDocumento,
    EstadoPoliticaFirma,
    OrigenDocumento,
    PoliticaFirmaYNotaria,
    TipoDocumental,
    is_pdf_storage_ref,
    is_valid_pdf_checksum,
)
from .pdf_generation import (
    GENERATED_PDF_AUDIT_EVENT_TYPE,
    PDF_PREVIEW_ENTITY_TYPE,
    PREVIEW_PDF_AUDIT_EVENT_TYPE,
    build_generated_pdf_audit_metadata,
)


REQUIRED_POLICY_TYPES = set(TipoDocumental.values)
AUTHORIZED_DOCUMENT_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}


def _non_sensitive_reference(value):
    return is_non_sensitive_reference(value)


def _sensitive_reference(value):
    normalized = str(value or '').strip()
    return bool(normalized) and not is_non_sensitive_reference(normalized)


def _issue(code, message, count=1, severity='blocking'):
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _count_invalid(queryset):
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _document_missing_metadata(document):
    return not all(
        [
            str(document.version_plantilla or '').strip(),
            str(document.checksum or '').strip(),
            document.fecha_carga,
            str(document.origen or '').strip(),
            document.expediente_id,
            str(document.storage_ref or '').strip(),
        ]
    )


def _count_by(queryset, field_name):
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _has_formalization_audit(document):
    return _formalization_audit_events(document).exists()


def _formalization_audit_events(document):
    return AuditEvent.objects.filter(
        event_type=FORMALIZATION_AUDIT_EVENT_TYPE,
        entity_type=FORMALIZATION_AUDIT_ENTITY_TYPE,
        entity_id=str(document.pk),
    )


def _metadata_value_matches(actual, expected):
    if isinstance(expected, bool):
        return actual is expected
    return str(actual or '').strip() == str(expected or '').strip()


def _audit_event_has_actor(event):
    return bool(event.actor_user_id or str(event.actor_identifier or '').strip())


def _metadata_has_sensitive_reference(metadata, field_names):
    if not isinstance(metadata, dict):
        return False
    return any(_sensitive_reference(metadata.get(field_name)) for field_name in field_names)


def _formalization_audit_is_aligned(document):
    expected_metadata = build_formalization_audit_metadata(document)
    for event in _formalization_audit_events(document):
        if not _audit_event_has_actor(event):
            continue
        metadata = event.metadata or {}
        if all(
            _metadata_value_matches(metadata.get(key), expected)
            for key, expected in expected_metadata.items()
        ):
            return True
    return False


def _has_correction_audit(document):
    return _correction_audit_events(document).exists()


def _correction_audit_events(document):
    return AuditEvent.objects.filter(
        event_type=CORRECTION_AUDIT_EVENT_TYPE,
        entity_type=CORRECTION_AUDIT_ENTITY_TYPE,
        entity_id=str(document.pk),
    )


def _correction_audit_is_aligned(document):
    expected_metadata = build_correction_audit_metadata(document)
    for event in _correction_audit_events(document):
        if not _audit_event_has_actor(event):
            continue
        metadata = event.metadata or {}
        if all(
            _metadata_value_matches(metadata.get(key), expected)
            for key, expected in expected_metadata.items()
        ):
            return True
    return False


def _has_generated_pdf_audit(document):
    return _generated_pdf_audit_events(document).exists()


def _generated_pdf_audit_events(document):
    return AuditEvent.objects.filter(
        event_type=GENERATED_PDF_AUDIT_EVENT_TYPE,
        entity_type='documento_emitido',
        entity_id=str(document.pk),
    )


def _generated_pdf_audit_is_aligned(document):
    expected_metadata = build_generated_pdf_audit_metadata(document)
    for event in _generated_pdf_audit_events(document):
        if not _audit_event_has_actor(event):
            continue
        metadata = event.metadata or {}
        if all(
            _metadata_value_matches(metadata.get(key), expected)
            for key, expected in expected_metadata.items()
        ):
            return True
    return False


def _has_generated_pdf_preview(document):
    return _generated_pdf_preview_events(document).exists()


def _generated_pdf_preview_events(document):
    return AuditEvent.objects.filter(
        event_type=PREVIEW_PDF_AUDIT_EVENT_TYPE,
        entity_type=PDF_PREVIEW_ENTITY_TYPE,
        entity_id=str(document.checksum or '').strip(),
    )


def _generated_pdf_preview_is_aligned(document):
    expected_metadata = {
        'checksum_sha256': document.checksum,
        'expediente_id': document.expediente_id,
        'tipo_documental': document.tipo_documental,
        'version_plantilla': document.version_plantilla,
        'storage_ref': redact_sensitive_reference(document.storage_ref),
    }
    for event in _generated_pdf_preview_events(document):
        if not _audit_event_has_actor(event):
            continue
        metadata = event.metadata or {}
        if all(
            _metadata_value_matches(metadata.get(key), expected)
            for key, expected in expected_metadata.items()
        ):
            return True
    return False


def collect_document_readiness(
    *,
    final_policy_ref='',
    responsible_ref='',
    controlled_pdf_ref='',
    source_label='',
    authorization_ref='',
    source_kind='local',
):
    active_policies = PoliticaFirmaYNotaria.objects.filter(estado=EstadoPoliticaFirma.ACTIVE)
    active_policy_types = set(active_policies.values_list('tipo_documental', flat=True))
    missing_policy_types = sorted(REQUIRED_POLICY_TYPES - active_policy_types)
    invalid_active_policies = _count_invalid(active_policies)

    documents = DocumentoEmitido.objects.select_related('expediente', 'comprobante_notarial', 'documento_origen').all()
    documents_without_policy = documents.exclude(tipo_documental__in=active_policy_types).count()
    non_pdf_documents = 0
    sensitive_storage_refs = 0
    documents_missing_metadata = 0
    documents_missing_user = 0
    invalid_checksum_documents = 0
    invalid_formalized_documents = 0
    formalized_without_evidence = 0
    formalized_with_sensitive_evidence = 0
    notary_required_policies = set(
        active_policies.filter(requiere_notaria=True).values_list('tipo_documental', flat=True)
    )
    formalized_without_notary_reception = 0
    formalized_without_notary_receipt = 0
    formalized_without_required_codebtor_signature = 0
    notary_receipts_wrong_type = 0
    notary_receipts_wrong_expediente = 0
    notary_receipts_invalid_state = 0
    formalized_without_formalization_audit = 0
    formalized_with_unaligned_formalization_audit = 0
    formalization_audit_sensitive_metadata = 0
    generated_documents_without_preview = 0
    generated_documents_with_unaligned_preview = 0
    generated_preview_sensitive_metadata = 0
    generated_documents_without_audit = 0
    generated_documents_with_unaligned_audit = 0
    generated_audit_sensitive_metadata = 0
    corrective_versions_without_audit = 0
    corrective_versions_with_unaligned_audit = 0
    corrective_audit_sensitive_metadata = 0
    invalid_corrective_versions = 0

    for document in documents:
        if not is_pdf_storage_ref(document.storage_ref):
            non_pdf_documents += 1
        if _sensitive_reference(document.storage_ref):
            sensitive_storage_refs += 1
        if str(document.checksum or '').strip() and not is_valid_pdf_checksum(document.checksum):
            invalid_checksum_documents += 1
        if not document.usuario_id:
            documents_missing_user += 1
        if _document_missing_metadata(document):
            documents_missing_metadata += 1
        if document.origen == OrigenDocumento.GENERATED:
            if not _has_generated_pdf_preview(document):
                generated_documents_without_preview += 1
            else:
                preview_events = list(_generated_pdf_preview_events(document))
                if any(_metadata_has_sensitive_reference(event.metadata or {}, ('storage_ref',)) for event in preview_events):
                    generated_preview_sensitive_metadata += 1
                if not _generated_pdf_preview_is_aligned(document):
                    generated_documents_with_unaligned_preview += 1
            if not _has_generated_pdf_audit(document):
                generated_documents_without_audit += 1
            else:
                generated_events = list(_generated_pdf_audit_events(document))
                if any(_metadata_has_sensitive_reference(event.metadata or {}, ('storage_ref',)) for event in generated_events):
                    generated_audit_sensitive_metadata += 1
                if not _generated_pdf_audit_is_aligned(document):
                    generated_documents_with_unaligned_audit += 1
        if document.estado == EstadoDocumento.FORMALIZED:
            if not str(document.evidencia_formalizacion_ref or '').strip():
                formalized_without_evidence += 1
            elif _sensitive_reference(document.evidencia_formalizacion_ref):
                formalized_with_sensitive_evidence += 1
            try:
                document.full_clean()
            except ValidationError:
                invalid_formalized_documents += 1
            if not _has_formalization_audit(document):
                formalized_without_formalization_audit += 1
            else:
                formalization_events = list(_formalization_audit_events(document))
                if any(
                    _metadata_has_sensitive_reference(event.metadata or {}, ('evidencia_formalizacion_ref',))
                    for event in formalization_events
                ):
                    formalization_audit_sensitive_metadata += 1
                if not _formalization_audit_is_aligned(document):
                    formalized_with_unaligned_formalization_audit += 1
            if document.requires_codebtor_signature() and not document.firma_codeudor_registrada:
                formalized_without_required_codebtor_signature += 1
            if document.tipo_documental in notary_required_policies:
                if not document.recepcion_notarial_registrada:
                    formalized_without_notary_reception += 1
                if not document.comprobante_notarial_id:
                    formalized_without_notary_receipt += 1
                else:
                    receipt = document.comprobante_notarial
                    if receipt.tipo_documental != TipoDocumental.NOTARY_RECEIPT:
                        notary_receipts_wrong_type += 1
                    if receipt.expediente_id != document.expediente_id:
                        notary_receipts_wrong_expediente += 1
                    if receipt.estado in {EstadoDocumento.DRAFT, EstadoDocumento.CANCELED}:
                        notary_receipts_invalid_state += 1
        if document.documento_origen_id:
            try:
                document.full_clean()
            except ValidationError:
                invalid_corrective_versions += 1
            if not _has_correction_audit(document):
                corrective_versions_without_audit += 1
            else:
                correction_events = list(_correction_audit_events(document))
                if any(
                    _metadata_has_sensitive_reference(event.metadata or {}, ('storage_ref', 'correccion_ref'))
                    for event in correction_events
                ):
                    corrective_audit_sensitive_metadata += 1
                if not _correction_audit_is_aligned(document):
                    corrective_versions_with_unaligned_audit += 1

    checks = {
        'final_policy_ref': _non_sensitive_reference(final_policy_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
        'controlled_pdf_ref': _non_sensitive_reference(controlled_pdf_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_DOCUMENT_SOURCE_KINDS

    issues = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'documents.source_kind_not_authorized',
                'La readiness local de Documentos no puede cerrar Etapa 5 sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, code, message in [
            (
                'source_label',
                'documents.source_label_missing',
                'Falta etiqueta no sensible de la fuente autorizada documental.',
            ),
            (
                'authorization_ref',
                'documents.authorization_ref_missing',
                'Falta referencia no sensible a la autorizacion de uso de la fuente documental.',
            ),
        ]:
            if not source_trace[key]:
                issues.append(_issue(code, message))
    if missing_policy_types:
        issues.append(
            _issue(
                'documents.active_policy_missing',
                'Faltan politicas activas de firma/notaria para tipos documentales canonicos.',
                count=len(missing_policy_types),
            )
        )
    if invalid_active_policies:
        issues.append(
            _issue(
                'documents.active_policy_invalid',
                'Existen politicas activas que no pasan validacion de dominio.',
                count=invalid_active_policies,
            )
        )
    if documents_without_policy:
        issues.append(
            _issue(
                'documents.document_without_active_policy',
                'Existen documentos emitidos sin politica activa para su tipo documental.',
                count=documents_without_policy,
            )
        )
    if non_pdf_documents:
        issues.append(
            _issue(
                'documents.non_pdf_storage_ref',
                'Existen documentos cuyo storage_ref no referencia PDF canonico.',
                count=non_pdf_documents,
            )
        )
    if sensitive_storage_refs:
        issues.append(
            _issue(
                'documents.sensitive_storage_ref',
                'Existen documentos cuyo storage_ref contiene URLs, tokens, credenciales o correos.',
                count=sensitive_storage_refs,
            )
        )
    if documents_missing_metadata:
        issues.append(
            _issue(
                'documents.metadata_missing',
                'Existen documentos sin metadata obligatoria completa.',
                count=documents_missing_metadata,
            )
        )
    if documents_missing_user:
        issues.append(
            _issue(
                'documents.user_missing',
                'Existen documentos emitidos sin usuario responsable registrado.',
                count=documents_missing_user,
            )
        )
    if invalid_checksum_documents:
        issues.append(
            _issue(
                'documents.invalid_checksum',
                'Existen documentos cuyo checksum no es un SHA-256 canonico.',
                count=invalid_checksum_documents,
            )
        )
    if invalid_formalized_documents:
        issues.append(
            _issue(
                'documents.formalized_invalid',
                'Existen documentos formalizados que no satisfacen firmas/notaria requeridas.',
                count=invalid_formalized_documents,
            )
        )
    if formalized_without_evidence:
        issues.append(
            _issue(
                'documents.formalization_evidence_missing',
                'Existen documentos formalizados sin referencia de evidencia no sensible.',
                count=formalized_without_evidence,
            )
        )
    if formalized_with_sensitive_evidence:
        issues.append(
            _issue(
                'documents.formalization_evidence_sensitive',
                'Existen documentos formalizados con referencia de evidencia sensible.',
                count=formalized_with_sensitive_evidence,
            )
        )
    if generated_documents_without_audit:
        issues.append(
            _issue(
                'documents.generated_pdf_audit_missing',
                'Existen documentos generados por sistema sin auditoria dedicada de generacion PDF.',
                count=generated_documents_without_audit,
            )
        )
    if generated_documents_with_unaligned_audit:
        issues.append(
            _issue(
                'documents.generated_pdf_audit_unaligned',
                'Existen documentos generados por sistema cuya auditoria PDF no conserva actor y metadata alineada.',
                count=generated_documents_with_unaligned_audit,
            )
        )
    if generated_audit_sensitive_metadata:
        issues.append(
            _issue(
                'documents.generated_pdf_audit_sensitive_metadata',
                'Existen auditorias de PDF generado con metadata sensible.',
                count=generated_audit_sensitive_metadata,
            )
        )
    if generated_documents_without_preview:
        issues.append(
            _issue(
                'documents.generated_pdf_preview_missing',
                'Existen documentos generados por sistema sin vista previa auditada del mismo contenido.',
                count=generated_documents_without_preview,
            )
        )
    if generated_documents_with_unaligned_preview:
        issues.append(
            _issue(
                'documents.generated_pdf_preview_unaligned',
                'Existen documentos generados por sistema cuya vista previa auditada no conserva actor y metadata alineada.',
                count=generated_documents_with_unaligned_preview,
            )
        )
    if generated_preview_sensitive_metadata:
        issues.append(
            _issue(
                'documents.generated_pdf_preview_sensitive_metadata',
                'Existen auditorias de preview PDF con metadata sensible.',
                count=generated_preview_sensitive_metadata,
            )
        )
    if formalized_without_notary_reception:
        issues.append(
            _issue(
                'documents.notary_reception_missing',
                'Existen documentos formalizados con politica notarial sin recepcion notarial registrada.',
                count=formalized_without_notary_reception,
            )
        )
    if formalized_without_notary_receipt:
        issues.append(
            _issue(
                'documents.notary_receipt_missing',
                'Existen documentos formalizados con politica notarial sin comprobante asociado.',
                count=formalized_without_notary_receipt,
            )
        )
    if formalized_without_required_codebtor_signature:
        issues.append(
            _issue(
                'documents.codebtor_signature_missing',
                'Existen documentos formalizados de contratos con codeudor activo sin firma de codeudor requerida.',
                count=formalized_without_required_codebtor_signature,
            )
        )
    if notary_receipts_wrong_type:
        issues.append(
            _issue(
                'documents.notary_receipt_wrong_type',
                'Existen documentos formalizados con comprobante asociado que no es comprobante notarial.',
                count=notary_receipts_wrong_type,
            )
        )
    if notary_receipts_wrong_expediente:
        issues.append(
            _issue(
                'documents.notary_receipt_wrong_expediente',
                'Existen documentos formalizados con comprobante notarial de otro expediente.',
                count=notary_receipts_wrong_expediente,
            )
        )
    if notary_receipts_invalid_state:
        issues.append(
            _issue(
                'documents.notary_receipt_invalid_state',
                'Existen documentos formalizados con comprobante notarial en estado no permitido.',
                count=notary_receipts_invalid_state,
            )
        )
    if formalized_without_formalization_audit:
        issues.append(
            _issue(
                'documents.formalization_audit_missing',
                'Existen documentos formalizados sin evento de auditoria de formalizacion.',
                count=formalized_without_formalization_audit,
            )
        )
    if formalized_with_unaligned_formalization_audit:
        issues.append(
            _issue(
                'documents.formalization_audit_unaligned',
                'Existen documentos formalizados cuyo evento de auditoria no conserva actor y metadata de formalizacion alineada.',
                count=formalized_with_unaligned_formalization_audit,
            )
        )
    if formalization_audit_sensitive_metadata:
        issues.append(
            _issue(
                'documents.formalization_audit_sensitive_metadata',
                'Existen auditorias de formalizacion documental con metadata sensible.',
                count=formalization_audit_sensitive_metadata,
            )
        )
    if invalid_corrective_versions:
        issues.append(
            _issue(
                'documents.corrective_version_invalid',
                'Existen versiones correctivas documentales que no trazan correctamente a un documento formalizado.',
                count=invalid_corrective_versions,
            )
        )
    if corrective_versions_without_audit:
        issues.append(
            _issue(
                'documents.corrective_version_audit_missing',
                'Existen versiones correctivas documentales sin evento de auditoria dedicado.',
                count=corrective_versions_without_audit,
            )
        )
    if corrective_versions_with_unaligned_audit:
        issues.append(
            _issue(
                'documents.corrective_version_audit_unaligned',
                'Existen versiones correctivas documentales cuyo evento de auditoria no conserva actor y metadata de correccion alineada.',
                count=corrective_versions_with_unaligned_audit,
            )
        )
    if corrective_audit_sensitive_metadata:
        issues.append(
            _issue(
                'documents.corrective_version_audit_sensitive_metadata',
                'Existen auditorias de versiones correctivas con metadata sensible.',
                count=corrective_audit_sensitive_metadata,
            )
        )

    for key, code, message in [
        (
            'final_policy_ref',
            'documents.final_policy_ref_missing',
            'Falta referencia no sensible a la politica final de firma/notaria.',
        ),
        (
            'responsible_ref',
            'documents.responsible_ref_missing',
            'Falta referencia no sensible a responsables de operacion documental.',
        ),
        (
            'controlled_pdf_ref',
            'documents.controlled_pdf_ref_missing',
            'Falta referencia no sensible a prueba PDF controlada.',
        ),
    ]:
        if not checks[key]:
            issues.append(_issue(code, message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 5 - Documentos PDF y firma',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_DOCUMENT_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage5_documents': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'policy': {
                'required_policy_types': sorted(REQUIRED_POLICY_TYPES),
                'active_policy_types': sorted(active_policy_types),
                'missing_policy_types': missing_policy_types,
                'active_policies_total': active_policies.count(),
                'invalid_active_policies': invalid_active_policies,
            },
            'documents': {
                'total': documents.count(),
                'by_state': _count_by(documents, 'estado'),
                'by_type': _count_by(documents, 'tipo_documental'),
                'without_active_policy': documents_without_policy,
                'non_pdf_storage_refs': non_pdf_documents,
                'sensitive_storage_refs': sensitive_storage_refs,
                'missing_metadata': documents_missing_metadata,
                'missing_user': documents_missing_user,
                'invalid_checksums': invalid_checksum_documents,
                'invalid_formalized_documents': invalid_formalized_documents,
                'formalized_without_evidence': formalized_without_evidence,
                'formalized_with_sensitive_evidence': formalized_with_sensitive_evidence,
                'generated_without_preview': generated_documents_without_preview,
                'generated_with_unaligned_preview': generated_documents_with_unaligned_preview,
                'generated_preview_sensitive_metadata': generated_preview_sensitive_metadata,
                'generated_without_audit': generated_documents_without_audit,
                'generated_with_unaligned_audit': generated_documents_with_unaligned_audit,
                'generated_audit_sensitive_metadata': generated_audit_sensitive_metadata,
                'formalized_without_notary_reception': formalized_without_notary_reception,
                'formalized_without_notary_receipt': formalized_without_notary_receipt,
                'formalized_without_required_codebtor_signature': formalized_without_required_codebtor_signature,
                'notary_receipts_wrong_type': notary_receipts_wrong_type,
                'notary_receipts_wrong_expediente': notary_receipts_wrong_expediente,
                'notary_receipts_invalid_state': notary_receipts_invalid_state,
                'formalized_without_formalization_audit': formalized_without_formalization_audit,
                'formalized_with_unaligned_formalization_audit': formalized_with_unaligned_formalization_audit,
                'formalization_audit_sensitive_metadata': formalization_audit_sensitive_metadata,
                'corrective_versions': documents.filter(documento_origen__isnull=False).count(),
                'invalid_corrective_versions': invalid_corrective_versions,
                'corrective_versions_without_audit': corrective_versions_without_audit,
                'corrective_versions_with_unaligned_audit': corrective_versions_with_unaligned_audit,
                'corrective_audit_sensitive_metadata': corrective_audit_sensitive_metadata,
            },
            'final_evidence': checks,
            'source_trace': source_trace,
        },
        'limitations': [
            'Auditoria local de solo lectura; no lee storage ni documentos productivos.',
            'No usa secretos, .env, datos reales ni integraciones externas.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No reemplaza la decision final de politica de firma/notaria ni la prueba PDF controlada.',
        ],
    }
