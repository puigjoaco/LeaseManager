from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditEvent
from compliance.models import (
    CategoriaDato,
    EstadoExportacionSensible,
    EstadoRegistro,
    ExportacionSensible,
    PoliticaRetencionDatos,
)
from compliance.services import MAX_EXPORT_DAYS, inspect_export_payload_integrity
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference


AUTHORIZED_COMPLIANCE_DATA_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
COMPLIANCE_DATA_READINESS_DEADLINE = date(2026, 12, 1)
REQUIRED_RETENTION_CATEGORIES = {choice.value for choice in CategoriaDato}
HOLD_REQUIRED_CATEGORIES = {
    CategoriaDato.TAX,
    CategoriaDato.DOCUMENT,
}
NO_PHYSICAL_PURGE_CATEGORIES = {
    CategoriaDato.DOCUMENT,
    CategoriaDato.SECRET,
}


def _issue(code: str, message: str, *, count: int = 1, severity: str = 'blocking') -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _non_sensitive_reference(value: str) -> bool:
    return is_non_sensitive_reference(value)


def _count_invalid(queryset) -> int:
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _count_by(queryset, field_name: str) -> dict[str, int]:
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _audit_event_has_sensitive_metadata(event: AuditEvent) -> bool:
    return contains_sensitive_reference(event.summary, include_sensitive_keys=True) or contains_sensitive_reference(
        event.metadata,
        include_sensitive_keys=True,
    )


def _is_sha256_hex_digest(value: str) -> bool:
    candidate = value.strip()
    return len(candidate) == 64 and all(char in '0123456789abcdefABCDEF' for char in candidate)


def _collect_export_issues(exports, now) -> dict[str, int]:
    counts = Counter()
    max_expiry_seconds = MAX_EXPORT_DAYS * 24 * 60 * 60
    for export in exports:
        try:
            export.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1
        if contains_sensitive_reference(export.motivo, include_sensitive_keys=True) or contains_sensitive_reference(
            export.scope_resumen,
            include_sensitive_keys=True,
        ):
            counts['sensitive_visible_metadata'] += 1
        if export.categoria_dato == CategoriaDato.SECRET:
            counts['secret_category_exports'] += 1
        if not export.created_by_id:
            counts['created_by_missing'] += 1
        has_encrypted_payload = bool(export.encrypted_payload.strip())
        has_payload_hash = bool(export.payload_hash.strip())
        if not has_encrypted_payload or not has_payload_hash or not export.encrypted_ref.strip():
            counts['integrity_fields_missing'] += 1
        payload_hash_is_valid = _is_sha256_hex_digest(export.payload_hash)
        if not payload_hash_is_valid:
            counts['payload_hash_invalid'] += 1
        elif has_encrypted_payload and has_payload_hash:
            integrity_status = inspect_export_payload_integrity(export)
            if integrity_status == 'unreadable':
                counts['payload_unreadable'] += 1
            elif integrity_status == 'mismatch':
                counts['payload_hash_mismatch'] += 1
        if export.estado == EstadoExportacionSensible.PREPARED:
            if not export.hold_activo and export.expires_at <= now:
                counts['prepared_expired_without_hold'] += 1
            if (
                not export.hold_activo
                and export.created_at
                and export.expires_at
                and (export.expires_at - export.created_at).total_seconds() > max_expiry_seconds
            ):
                counts['prepared_expiry_too_long'] += 1
        if export.estado == EstadoExportacionSensible.EXPIRED and (export.hold_activo or export.expires_at > now):
            counts['expired_state_inconsistent'] += 1
        if not AuditEvent.objects.filter(
            event_type='compliance.exportacion_sensible.prepared',
            entity_type='exportacion_sensible',
            entity_id=str(export.pk),
        ).exists():
            counts['prepared_audit_event_missing'] += 1
        if export.estado == EstadoExportacionSensible.REVOKED and not AuditEvent.objects.filter(
            event_type='compliance.exportacion_sensible.revoked',
            entity_type='exportacion_sensible',
            entity_id=str(export.pk),
        ).exists():
            counts['revoked_audit_event_missing'] += 1
    return dict(sorted(counts.items()))


def collect_compliance_data_readiness(
    *,
    policy_approval_ref: str = '',
    responsible_ref: str = '',
    controls_evidence_ref: str = '',
    archived_evidence_ref: str = '',
    legal_review_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
    as_of_date: date | None = None,
) -> dict[str, Any]:
    now = timezone.now()
    effective_date = as_of_date or timezone.localdate()

    policies = PoliticaRetencionDatos.objects.all()
    active_policies = policies.filter(estado=EstadoRegistro.ACTIVE)
    active_categories = set(active_policies.values_list('categoria_dato', flat=True))
    missing_active_categories = sorted(REQUIRED_RETENTION_CATEGORIES - active_categories)
    invalid_policies = _count_invalid(policies)
    hold_ready_categories = set(
        active_policies.filter(requiere_hold=True).values_list('categoria_dato', flat=True)
    )
    hold_missing_categories = sorted(str(category) for category in HOLD_REQUIRED_CATEGORIES - hold_ready_categories)
    physical_purge_enabled = active_policies.filter(
        categoria_dato__in=[str(category) for category in NO_PHYSICAL_PURGE_CATEGORIES],
        permite_purga_fisica=True,
    ).count()

    exports = ExportacionSensible.objects.select_related('created_by')
    export_issues = _collect_export_issues(exports, now)
    export_audit_events = AuditEvent.objects.filter(entity_type='exportacion_sensible')
    sensitive_audit_metadata_events = sum(
        1 for event in export_audit_events if _audit_event_has_sensitive_metadata(event)
    )

    final_evidence = {
        'policy_approval_ref': _non_sensitive_reference(policy_approval_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
        'controls_evidence_ref': _non_sensitive_reference(controls_evidence_ref),
        'archived_evidence_ref': _non_sensitive_reference(archived_evidence_ref),
        'legal_review_ref': _non_sensitive_reference(legal_review_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_COMPLIANCE_DATA_SOURCE_KINDS

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'compliance.source_kind_not_authorized',
                'La readiness local de Compliance no puede cerrar DatosPersonalesChile2026 sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, code, message in [
            (
                'source_label',
                'compliance.source_label_missing',
                'Falta etiqueta no sensible de la fuente autorizada para Compliance.DatosPersonalesChile2026.',
            ),
            (
                'authorization_ref',
                'compliance.authorization_ref_missing',
                'Falta referencia no sensible a la autorizacion de uso de la fuente evidencial de Compliance.',
            ),
        ]:
            if not source_trace[key]:
                issues.append(_issue(code, message))

    if missing_active_categories:
        issues.append(
            _issue(
                'compliance.retention_policy_missing',
                'Faltan politicas de retencion activas para todas las categorias canonicas de dato.',
                count=len(missing_active_categories),
            )
        )
    if invalid_policies:
        issues.append(
            _issue(
                'compliance.retention_policy_invalid',
                'Existen politicas de retencion que no pasan validacion de dominio.',
                count=invalid_policies,
            )
        )
    if hold_missing_categories:
        issues.append(
            _issue(
                'compliance.retention_hold_missing',
                'Las categorias tributaria y documental sensible requieren hold operativo activo.',
                count=len(hold_missing_categories),
            )
        )
    if physical_purge_enabled:
        issues.append(
            _issue(
                'compliance.retention_physical_purge_enabled',
                'Las categorias documental sensible y secreto no deben permitir purga fisica por defecto.',
                count=physical_purge_enabled,
            )
        )

    for key, code, message in [
        (
            'invalid_model',
            'compliance.export_invalid_model',
            'Existen exportaciones sensibles que no pasan validacion de dominio.',
        ),
        (
            'sensitive_visible_metadata',
            'compliance.export_sensitive_visible_metadata',
            'Existen exportaciones con motivo o scope visible que contiene referencias sensibles.',
        ),
        (
            'secret_category_exports',
            'compliance.export_secret_category',
            'No debe existir exportacion operativa sobre categoria secreto.',
        ),
        (
            'created_by_missing',
            'compliance.export_actor_missing',
            'Toda exportacion sensible requiere actor creador trazable.',
        ),
        (
            'integrity_fields_missing',
            'compliance.export_integrity_fields_missing',
            'Toda exportacion sensible requiere payload cifrado, hash y referencia cifrada.',
        ),
        (
            'payload_hash_invalid',
            'compliance.export_payload_hash_invalid',
            'Toda exportacion sensible requiere hash SHA-256 de 64 caracteres.',
        ),
        (
            'payload_hash_mismatch',
            'compliance.export_payload_hash_mismatch',
            'El payload cifrado de la exportacion sensible debe coincidir con su payload_hash.',
        ),
        (
            'payload_unreadable',
            'compliance.export_payload_unreadable',
            'El payload cifrado de la exportacion sensible debe ser descifrable para verificar integridad.',
        ),
        (
            'prepared_expired_without_hold',
            'compliance.export_prepared_expired_without_hold',
            'Existen exportaciones preparadas expiradas sin hold activo.',
        ),
        (
            'prepared_expiry_too_long',
            'compliance.export_prepared_expiry_too_long',
            'Las exportaciones preparadas sin hold no pueden exceder la ventana maxima de retencion temporal.',
        ),
        (
            'expired_state_inconsistent',
            'compliance.export_expired_state_inconsistent',
            'Las exportaciones expiradas deben tener vencimiento ya cumplido y no estar bajo hold activo.',
        ),
        (
            'prepared_audit_event_missing',
            'compliance.export_prepared_audit_event_missing',
            'Toda exportacion sensible requiere evento de auditoria prepared trazable.',
        ),
        (
            'revoked_audit_event_missing',
            'compliance.export_revoked_audit_event_missing',
            'Toda exportacion sensible revocada requiere evento de auditoria revoked trazable.',
        ),
    ]:
        if export_issues.get(key):
            issues.append(_issue(code, message, count=export_issues[key]))

    if sensitive_audit_metadata_events:
        issues.append(
            _issue(
                'compliance.audit_sensitive_metadata',
                'Existen eventos de auditoria de exportacion sensible con metadata o resumen sensible.',
                count=sensitive_audit_metadata_events,
            )
        )

    for key, code, message in [
        (
            'policy_approval_ref',
            'compliance.policy_approval_ref_missing',
            'Falta referencia no sensible a politica de datos personales aprobada.',
        ),
        (
            'responsible_ref',
            'compliance.responsible_ref_missing',
            'Falta referencia no sensible a responsables designados de Compliance.',
        ),
        (
            'controls_evidence_ref',
            'compliance.controls_evidence_ref_missing',
            'Falta referencia no sensible a controles implementados y verificados.',
        ),
        (
            'archived_evidence_ref',
            'compliance.archived_evidence_ref_missing',
            'Falta referencia no sensible a evidencia archivada del checklist formal.',
        ),
        (
            'legal_review_ref',
            'compliance.legal_review_ref_missing',
            'Falta referencia no sensible a validacion legal-operativa vigente.',
        ),
    ]:
        if not final_evidence[key]:
            issues.append(_issue(code, message))

    if effective_date >= COMPLIANCE_DATA_READINESS_DEADLINE and issues:
        issues.append(
            _issue(
                'compliance.production_suspension_required',
                'Posterior al 2026-12-01, la operacion productiva requiere readiness Compliance.DatosPersonalesChile2026 resuelta o suspension formal.',
            )
        )

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': now.isoformat(),
        'gate': 'Compliance.DatosPersonalesChile2026',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_COMPLIANCE_DATA_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_compliance_data': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'retention_policies': {
                'total': policies.count(),
                'active_total': active_policies.count(),
                'required_categories': sorted(REQUIRED_RETENTION_CATEGORIES),
                'active_categories': sorted(active_categories),
                'missing_active_categories': missing_active_categories,
                'invalid_policies': invalid_policies,
                'hold_required_categories': sorted(str(category) for category in HOLD_REQUIRED_CATEGORIES),
                'hold_missing_categories': hold_missing_categories,
                'physical_purge_enabled_for_restricted_categories': physical_purge_enabled,
                'by_state': _count_by(policies, 'estado'),
            },
            'exports': {
                'total': exports.count(),
                'by_status': _count_by(exports, 'estado'),
                'by_category': _count_by(exports, 'categoria_dato'),
                'invalid_model': export_issues.get('invalid_model', 0),
                'sensitive_visible_metadata': export_issues.get('sensitive_visible_metadata', 0),
                'secret_category_exports': export_issues.get('secret_category_exports', 0),
                'created_by_missing': export_issues.get('created_by_missing', 0),
                'integrity_fields_missing': export_issues.get('integrity_fields_missing', 0),
                'payload_hash_invalid': export_issues.get('payload_hash_invalid', 0),
                'payload_hash_mismatch': export_issues.get('payload_hash_mismatch', 0),
                'payload_unreadable': export_issues.get('payload_unreadable', 0),
                'prepared_expired_without_hold': export_issues.get('prepared_expired_without_hold', 0),
                'prepared_expiry_too_long': export_issues.get('prepared_expiry_too_long', 0),
                'expired_state_inconsistent': export_issues.get('expired_state_inconsistent', 0),
                'prepared_audit_event_missing': export_issues.get('prepared_audit_event_missing', 0),
                'revoked_audit_event_missing': export_issues.get('revoked_audit_event_missing', 0),
            },
            'audit': {
                'export_events_total': export_audit_events.count(),
                'prepared_events': export_audit_events.filter(
                    event_type='compliance.exportacion_sensible.prepared'
                ).count(),
                'accessed_events': export_audit_events.filter(
                    event_type='compliance.exportacion_sensible.accessed'
                ).count(),
                'revoked_events': export_audit_events.filter(
                    event_type='compliance.exportacion_sensible.revoked'
                ).count(),
                'access_denied_events': export_audit_events.filter(
                    event_type='compliance.exportacion_sensible.access_denied'
                ).count(),
                'sensitive_metadata_events': sensitive_audit_metadata_events,
            },
            'final_evidence': final_evidence,
            'source_trace': source_trace,
            'deadline': {
                'readiness_required_by': COMPLIANCE_DATA_READINESS_DEADLINE.isoformat(),
                'as_of_date': effective_date.isoformat(),
                'after_deadline': effective_date >= COMPLIANCE_DATA_READINESS_DEADLINE,
            },
        },
        'limitations': [
            'Auditoria local de solo lectura; no procesa datos reales ni conecta integraciones externas.',
            'No usa secretos, .env, certificados, DB historicas ni credenciales.',
            'No cierra Compliance.DatosPersonalesChile2026 sin politica aprobada, responsables, controles, evidencia archivada y fuente autorizada.',
        ],
    }
