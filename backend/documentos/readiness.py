from collections import Counter

from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditEvent
from core.reference_validation import is_non_sensitive_reference

from .models import (
    DocumentoEmitido,
    EstadoDocumento,
    EstadoPoliticaFirma,
    PoliticaFirmaYNotaria,
    TipoDocumental,
    is_pdf_storage_ref,
    is_valid_pdf_checksum,
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
    return AuditEvent.objects.filter(
        event_type='documentos.documento_emitido.formalized',
        entity_type='documento_emitido',
        entity_id=str(document.pk),
    ).exists()


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

    documents = DocumentoEmitido.objects.select_related('expediente', 'comprobante_notarial').all()
    documents_without_policy = documents.exclude(tipo_documental__in=active_policy_types).count()
    non_pdf_documents = 0
    sensitive_storage_refs = 0
    documents_missing_metadata = 0
    documents_missing_user = 0
    invalid_checksum_documents = 0
    invalid_formalized_documents = 0
    notary_required_policies = set(
        active_policies.filter(requiere_notaria=True).values_list('tipo_documental', flat=True)
    )
    formalized_without_notary_receipt = 0
    formalized_without_formalization_audit = 0

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
        if document.estado == EstadoDocumento.FORMALIZED:
            try:
                document.full_clean()
            except ValidationError:
                invalid_formalized_documents += 1
            if not _has_formalization_audit(document):
                formalized_without_formalization_audit += 1
            if document.tipo_documental in notary_required_policies and not document.comprobante_notarial_id:
                formalized_without_notary_receipt += 1

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
    if formalized_without_notary_receipt:
        issues.append(
            _issue(
                'documents.notary_receipt_missing',
                'Existen documentos formalizados con politica notarial sin comprobante asociado.',
                count=formalized_without_notary_receipt,
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
                'formalized_without_notary_receipt': formalized_without_notary_receipt,
                'formalized_without_formalization_audit': formalized_without_formalization_audit,
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
