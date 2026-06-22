from __future__ import annotations

from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from audit.models import AuditEvent
from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MovimientoAsiento,
    ObligacionTributariaMensual,
)
from core.reference_validation import contains_sensitive_control_reference, is_non_sensitive_control_reference
from core.state_transition_audit_readiness import count_audit_events_without_transition_metadata
from sii.models import DDJJPreparacionAnual, F22PreparacionAnual, ProcesoRentaAnual, has_text


AUTHORIZED_STAGE7_REPORTING_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
STAGE7_ANNUAL_STATUS_UPDATE_EVENT_TYPES = (
    'sii.ddjj_preparacion.status_updated',
    'sii.f22_preparacion.status_updated',
)

ANNUAL_TRACEABLE_STATES = {
    EstadoPreparacionTributaria.PREPARED,
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}

ANNUAL_STATES_REQUIRING_REF = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}


def _non_sensitive_reference(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and is_non_sensitive_control_reference(normalized)


def _sensitive_reference(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and not _non_sensitive_reference(normalized)


def _issue(code: str, message: str, *, count: int = 1, severity: str = 'blocking') -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _count_by(queryset, field_name: str) -> dict[str, int]:
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _count_invalid(queryset) -> int:
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _count_without_active_fiscal_config(items, active_fiscal_company_ids: set[int]) -> int:
    return sum(1 for item in items if item.empresa_id not in active_fiscal_company_ids)


def _count_annual_status_review_responsible_issues() -> dict[str, int]:
    counts = Counter()
    required_states = {str(state) for state in ANNUAL_STATES_REQUIRING_REF}
    events = AuditEvent.objects.filter(event_type__in=STAGE7_ANNUAL_STATUS_UPDATE_EVENT_TYPES).only('metadata')
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if str(metadata.get('estado_nuevo') or '').strip() not in required_states:
            continue
        responsible_ref = str(metadata.get('responsable_revision_ref') or '').strip()
        if not responsible_ref:
            counts['missing'] += 1
        elif _sensitive_reference(responsible_ref):
            counts['sensitive'] += 1
    return dict(sorted(counts.items()))


def _period_label(anio: int, mes: int) -> str:
    return f'{int(anio):04d}-{int(mes):02d}'


def _annual_summary_is_traceable(summary: Any) -> bool:
    if not isinstance(summary, dict):
        return False
    obligations = summary.get('obligaciones')
    return _annual_summary_fiscal_year(summary) is not None and isinstance(obligations, list) and bool(obligations)


def _annual_summary_fiscal_year(summary: Any) -> int | None:
    if not isinstance(summary, dict) or not summary.get('fiscal_year'):
        return None
    try:
        return int(summary.get('fiscal_year'))
    except (TypeError, ValueError):
        return None


def _annual_summary_fiscal_year_mismatch(summary: Any, anio_tributario: int) -> bool:
    fiscal_year = _annual_summary_fiscal_year(summary)
    return fiscal_year is not None and fiscal_year != anio_tributario - 1


def _annual_document_process_mismatch(document: Any) -> bool:
    process = document.proceso_renta_anual
    return document.empresa_id != process.empresa_id or document.anio_tributario != process.anio_tributario


def _collect_financial_report_issues(events, asientos) -> dict[str, int]:
    counts = Counter()
    posted_events = events.filter(estado_contable=EstadoEventoContable.POSTED)

    missing_origin = posted_events.filter(Q(entidad_origen_tipo='') | Q(entidad_origen_id='')).count()
    if missing_origin:
        counts['posted_event_origin_missing'] = missing_origin

    posted_without_asiento = posted_events.filter(asiento_contable__isnull=True).count()
    if posted_without_asiento:
        counts['posted_event_without_asiento'] = posted_without_asiento

    invalid_asientos = 0
    unbalanced_asientos = 0
    posted_without_hash = 0
    posted_with_stale_hash = 0
    asientos_without_movements = 0
    for asiento in asientos:
        if asiento.estado != EstadoAsientoContable.POSTED:
            invalid_asientos += 1
        if asiento.debe_total != asiento.haber_total:
            unbalanced_asientos += 1
        if asiento.estado == EstadoAsientoContable.POSTED and not has_text(asiento.hash_integridad):
            posted_without_hash += 1
        if (
            asiento.estado == EstadoAsientoContable.POSTED
            and has_text(asiento.hash_integridad)
            and not asiento.hash_integridad_matches()
        ):
            posted_with_stale_hash += 1
        if not asiento.movimientos.exists():
            asientos_without_movements += 1

    if invalid_asientos:
        counts['asiento_not_posted'] = invalid_asientos
    if unbalanced_asientos:
        counts['asiento_unbalanced'] = unbalanced_asientos
    if posted_without_hash:
        counts['asiento_hash_missing'] = posted_without_hash
    if posted_with_stale_hash:
        counts['asiento_hash_mismatch'] = posted_with_stale_hash
    if asientos_without_movements:
        counts['asiento_movements_missing'] = asientos_without_movements

    return dict(sorted(counts.items()))


def _collect_books_issues(approved_closes) -> dict[str, int]:
    counts = Counter()
    for close in approved_closes:
        period = _period_label(close.anio, close.mes)
        libro_diario = LibroDiario.objects.filter(empresa=close.empresa, periodo=period).first()
        libro_mayor = LibroMayor.objects.filter(empresa=close.empresa, periodo=period).first()
        balance = BalanceComprobacion.objects.filter(empresa=close.empresa, periodo=period).first()
        snapshots = [libro_diario, libro_mayor, balance]

        if any(snapshot is None for snapshot in snapshots):
            counts['snapshot_missing'] += 1
            continue
        if any(snapshot.estado_snapshot != EstadoCierreMensual.APPROVED for snapshot in snapshots):
            counts['snapshot_not_approved'] += 1
        if any(not snapshot.resumen for snapshot in snapshots):
            counts['snapshot_summary_missing'] += 1
        if balance.resumen.get('cuadrado') is not True:
            counts['balance_not_square'] += 1

    return dict(sorted(counts.items()))


def _collect_annual_report_issues(processes, ddjj_preparations, f22_preparations) -> dict[str, int]:
    counts = Counter()
    ddjj_by_process = {item.proceso_renta_anual_id: item for item in ddjj_preparations}
    f22_by_process = {item.proceso_renta_anual_id: item for item in f22_preparations}

    for process in processes:
        try:
            process.full_clean()
        except ValidationError:
            counts['process_invalid_model'] += 1

        if process.estado not in ANNUAL_TRACEABLE_STATES:
            counts['process_not_traceable'] += 1
        if not _annual_summary_is_traceable(process.resumen_anual):
            counts['process_summary_missing'] += 1
        if _annual_summary_fiscal_year_mismatch(process.resumen_anual, process.anio_tributario):
            counts['process_fiscal_year_mismatch'] += 1
        if contains_sensitive_control_reference(process.resumen_anual or {}, include_sensitive_keys=True):
            counts['process_sensitive_payload'] += 1
        if _sensitive_reference(process.paquete_ddjj_ref):
            counts['process_ddjj_ref_sensitive'] += 1
        if _sensitive_reference(process.borrador_f22_ref):
            counts['process_f22_ref_sensitive'] += 1
        if _sensitive_reference(process.responsable_revision_ref):
            counts['process_responsible_ref_sensitive'] += 1

        ddjj = ddjj_by_process.get(process.id)
        f22 = f22_by_process.get(process.id)
        if ddjj is None:
            counts['ddjj_missing_for_process'] += 1
        if f22 is None:
            counts['f22_missing_for_process'] += 1

        if process.estado in ANNUAL_STATES_REQUIRING_REF:
            if not has_text(process.paquete_ddjj_ref):
                counts['process_ddjj_ref_missing'] += 1
            if not has_text(process.borrador_f22_ref):
                counts['process_f22_ref_missing'] += 1
            if not has_text(process.responsable_revision_ref):
                counts['process_responsible_ref_missing'] += 1

    for ddjj in ddjj_preparations:
        try:
            ddjj.full_clean()
        except ValidationError:
            counts['ddjj_invalid_model'] += 1
        if _annual_document_process_mismatch(ddjj):
            counts['ddjj_process_mismatch'] += 1
        if ddjj.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            counts['ddjj_not_traceable'] += 1
        if not ddjj.resumen_paquete:
            counts['ddjj_summary_missing'] += 1
        ddjj_summary = ddjj.resumen_paquete.get('resumen_anual') if isinstance(ddjj.resumen_paquete, dict) else None
        if _annual_summary_fiscal_year_mismatch(ddjj_summary, ddjj.anio_tributario):
            counts['ddjj_summary_fiscal_year_mismatch'] += 1
        if contains_sensitive_control_reference(ddjj.resumen_paquete or {}, include_sensitive_keys=True):
            counts['ddjj_sensitive_payload'] += 1
        if _sensitive_reference(ddjj.paquete_ref):
            counts['ddjj_ref_sensitive'] += 1
        if _sensitive_reference(ddjj.responsable_revision_ref):
            counts['ddjj_responsible_ref_sensitive'] += 1
        if ddjj.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not has_text(ddjj.paquete_ref):
            counts['ddjj_ref_missing'] += 1
        if ddjj.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not has_text(ddjj.responsable_revision_ref):
            counts['ddjj_responsible_ref_missing'] += 1

    for f22 in f22_preparations:
        try:
            f22.full_clean()
        except ValidationError:
            counts['f22_invalid_model'] += 1
        if _annual_document_process_mismatch(f22):
            counts['f22_process_mismatch'] += 1
        if f22.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            counts['f22_not_traceable'] += 1
        if not f22.resumen_f22:
            counts['f22_summary_missing'] += 1
        f22_summary = f22.resumen_f22.get('resumen_anual') if isinstance(f22.resumen_f22, dict) else None
        if _annual_summary_fiscal_year_mismatch(f22_summary, f22.anio_tributario):
            counts['f22_summary_fiscal_year_mismatch'] += 1
        if contains_sensitive_control_reference(f22.resumen_f22 or {}, include_sensitive_keys=True):
            counts['f22_sensitive_payload'] += 1
        if _sensitive_reference(f22.borrador_ref):
            counts['f22_ref_sensitive'] += 1
        if _sensitive_reference(f22.responsable_revision_ref):
            counts['f22_responsible_ref_sensitive'] += 1
        if f22.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not has_text(f22.borrador_ref):
            counts['f22_ref_missing'] += 1
        if f22.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not has_text(f22.responsable_revision_ref):
            counts['f22_responsible_ref_missing'] += 1

    return dict(sorted(counts.items()))


def collect_stage7_reporting_readiness(
    *,
    stage5_evidence_ref: str = '',
    stage6_evidence_ref: str = '',
    reporting_api_proof_ref: str = '',
    backoffice_visual_ref: str = '',
    responsible_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
    fiscal_configs = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario')
    active_fiscal_configs = fiscal_configs.filter(estado=EstadoRegistro.ACTIVE)
    active_fiscal_company_ids = set(active_fiscal_configs.values_list('empresa_id', flat=True))

    approved_closes = CierreMensualContable.objects.filter(estado=EstadoCierreMensual.APPROVED).select_related('empresa')
    obligations = ObligacionTributariaMensual.objects.all()

    events = EventoContable.objects.select_related('empresa')
    posted_events = events.filter(estado_contable=EstadoEventoContable.POSTED)
    asientos = AsientoContable.objects.select_related('evento_contable')
    financial_issues = _collect_financial_report_issues(events, asientos)

    libro_diario = LibroDiario.objects.select_related('empresa')
    libro_mayor = LibroMayor.objects.select_related('empresa')
    balances = BalanceComprobacion.objects.select_related('empresa')
    books_issues = _collect_books_issues(approved_closes)

    annual_processes = ProcesoRentaAnual.objects.select_related('empresa')
    ddjj_preparations = DDJJPreparacionAnual.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'proceso_renta_anual',
    )
    f22_preparations = F22PreparacionAnual.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'proceso_renta_anual',
    )
    annual_issues = _collect_annual_report_issues(annual_processes, ddjj_preparations, f22_preparations)
    annual_processes_without_fiscal_config = _count_without_active_fiscal_config(
        annual_processes,
        active_fiscal_company_ids,
    )
    ddjj_without_fiscal_config = _count_without_active_fiscal_config(
        ddjj_preparations,
        active_fiscal_company_ids,
    )
    f22_without_fiscal_config = _count_without_active_fiscal_config(
        f22_preparations,
        active_fiscal_company_ids,
    )

    final_evidence = {
        'stage5_evidence_ref': _non_sensitive_reference(stage5_evidence_ref),
        'stage6_evidence_ref': _non_sensitive_reference(stage6_evidence_ref),
        'reporting_api_proof_ref': _non_sensitive_reference(reporting_api_proof_ref),
        'backoffice_visual_ref': _non_sensitive_reference(backoffice_visual_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    final_evidence_sensitive = {
        'stage5_evidence_ref': _sensitive_reference(stage5_evidence_ref),
        'stage6_evidence_ref': _sensitive_reference(stage6_evidence_ref),
        'reporting_api_proof_ref': _sensitive_reference(reporting_api_proof_ref),
        'backoffice_visual_ref': _sensitive_reference(backoffice_visual_ref),
        'responsible_ref': _sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_trace_sensitive = {
        'source_label': _sensitive_reference(source_label),
        'authorization_ref': _sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE7_REPORTING_SOURCE_KINDS
    annual_status_transition_metadata_missing = count_audit_events_without_transition_metadata(
        event_types=STAGE7_ANNUAL_STATUS_UPDATE_EVENT_TYPES
    )
    annual_status_review_responsible_issues = _count_annual_status_review_responsible_issues()

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage7.reporting.source_kind_not_authorized',
                'La readiness local de Etapa 7 Reporting no puede cerrar sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, missing_code, sensitive_code, missing_message, sensitive_message in [
            (
                'source_label',
                'stage7.reporting.source_label_missing',
                'stage7.reporting.source_label_sensitive',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 7 Reporting.',
                'La etiqueta de fuente autorizada de Etapa 7 Reporting contiene una referencia sensible.',
            ),
            (
                'authorization_ref',
                'stage7.reporting.authorization_ref_missing',
                'stage7.reporting.authorization_ref_sensitive',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 7 Reporting.',
                'La referencia de autorizacion de Etapa 7 Reporting contiene valores sensibles.',
            ),
        ]:
            if source_trace_sensitive[key]:
                issues.append(_issue(sensitive_code, sensitive_message))
            elif not source_trace[key]:
                issues.append(_issue(missing_code, missing_message))
    if annual_status_transition_metadata_missing:
        issues.append(
            _issue(
                'stage7.reporting.audit_annual_status_transition_metadata_missing',
                'Existen eventos status_updated de DDJJ/F22 usados por reporting sin campo_estado, estado_anterior o estado_nuevo.',
                count=annual_status_transition_metadata_missing,
            )
        )
    if annual_status_review_responsible_issues.get('missing'):
        issues.append(
            _issue(
                'stage7.reporting.audit_annual_status_responsible_ref_missing',
                'Existen eventos status_updated de DDJJ/F22 avanzados sin responsable_revision_ref auditado para reporting.',
                count=annual_status_review_responsible_issues['missing'],
            )
        )
    if annual_status_review_responsible_issues.get('sensitive'):
        issues.append(
            _issue(
                'stage7.reporting.audit_annual_status_responsible_ref_sensitive',
                'Existen eventos status_updated de DDJJ/F22 avanzados con responsable_revision_ref sensible para reporting.',
                count=annual_status_review_responsible_issues['sensitive'],
            )
        )
    if approved_closes.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.approved_close_missing',
                'Reporting requiere al menos un cierre mensual aprobado para reporte financiero trazable.',
            )
        )
    if posted_events.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.posted_events_missing',
                'Reporting financiero requiere eventos contables posteados.',
            )
        )
    if obligations.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.tax_obligations_missing',
                'Reporting requiere obligaciones tributarias mensuales para cifras fiscales.',
            )
        )
    if libro_diario.count() == 0 or libro_mayor.count() == 0 or balances.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.books_snapshots_missing',
                'Reporting de libros requiere LibroDiario, LibroMayor y BalanceComprobacion.',
            )
        )
    if annual_processes.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.annual_process_missing',
                'Reporting tributario anual requiere ProcesoRentaAnual trazable.',
            )
        )
    if annual_processes_without_fiscal_config:
        issues.append(
            _issue(
                'stage7.reporting.annual_process_fiscal_config_missing',
                'Existen procesos de renta anual para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=annual_processes_without_fiscal_config,
            )
        )
    if ddjj_preparations.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.ddjj_missing',
                'Reporting tributario anual requiere DDJJ asociada al proceso anual.',
            )
        )
    if ddjj_without_fiscal_config:
        issues.append(
            _issue(
                'stage7.reporting.annual_ddjj_fiscal_config_missing',
                'Existen DDJJ anuales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=ddjj_without_fiscal_config,
            )
        )
    if f22_preparations.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.f22_missing',
                'Reporting tributario anual requiere F22 asociado al proceso anual.',
            )
        )
    if f22_without_fiscal_config:
        issues.append(
            _issue(
                'stage7.reporting.annual_f22_fiscal_config_missing',
                'Existen F22 anuales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=f22_without_fiscal_config,
            )
        )

    for key, code, message in [
        (
            'posted_event_origin_missing',
            'stage7.reporting.event_origin_missing',
            'Existen eventos posteados sin origen trazable.',
        ),
        (
            'posted_event_without_asiento',
            'stage7.reporting.accounting_entry_missing',
            'Existen eventos posteados sin asiento contable asociado.',
        ),
        (
            'asiento_not_posted',
            'stage7.reporting.accounting_entry_not_posted',
            'Existen asientos incluidos en reporting que no estan posteados.',
        ),
        (
            'asiento_unbalanced',
            'stage7.reporting.accounting_entry_unbalanced',
            'Existen asientos descuadrados para reporting financiero.',
        ),
        (
            'asiento_hash_missing',
            'stage7.reporting.accounting_entry_hash_missing',
            'Existen asientos posteados sin hash de integridad.',
        ),
        (
            'asiento_hash_mismatch',
            'stage7.reporting.accounting_entry_hash_mismatch',
            'Existen asientos posteados con hash de integridad desactualizado.',
        ),
        (
            'asiento_movements_missing',
            'stage7.reporting.accounting_entry_movements_missing',
            'Existen asientos sin movimientos debe/haber.',
        ),
    ]:
        if financial_issues.get(key):
            issues.append(_issue(code, message, count=financial_issues[key]))

    for key, code, message in [
        (
            'snapshot_missing',
            'stage7.reporting.books_snapshot_missing_for_close',
            'Existen cierres aprobados sin set completo de snapshots contables.',
        ),
        (
            'snapshot_not_approved',
            'stage7.reporting.books_snapshot_not_approved',
            'Existen snapshots de libros no aprobados para cierres aprobados.',
        ),
        (
            'snapshot_summary_missing',
            'stage7.reporting.books_snapshot_summary_missing',
            'Existen snapshots de libros sin resumen trazable.',
        ),
        (
            'balance_not_square',
            'stage7.reporting.books_balance_not_square',
            'Existen balances de comprobacion no cuadrados.',
        ),
    ]:
        if books_issues.get(key):
            issues.append(_issue(code, message, count=books_issues[key]))

    for key, code, message in [
        (
            'process_invalid_model',
            'stage7.reporting.annual_process_invalid',
            'Existen procesos de renta anual que no pasan validacion de dominio.',
        ),
        (
            'process_not_traceable',
            'stage7.reporting.annual_process_not_traceable',
            'Existen procesos de renta anual sin estado trazable.',
        ),
        (
            'process_summary_missing',
            'stage7.reporting.annual_summary_incomplete',
            'Existen procesos de renta anual sin resumen con ejercicio y obligaciones.',
        ),
        (
            'process_fiscal_year_mismatch',
            'stage7.reporting.annual_fiscal_year_mismatch',
            'Existen procesos de renta anual con ejercicio distinto al ano tributario reportado.',
        ),
        (
            'process_sensitive_payload',
            'stage7.reporting.annual_process_sensitive_payload',
            'Existen procesos de renta anual con resumen_anual sensible.',
        ),
        (
            'process_ddjj_ref_sensitive',
            'stage7.reporting.annual_process_ddjj_ref_sensitive',
            'Proceso anual contiene paquete_ddjj_ref sensible para reporting.',
        ),
        (
            'process_f22_ref_sensitive',
            'stage7.reporting.annual_process_f22_ref_sensitive',
            'Proceso anual contiene borrador_f22_ref sensible para reporting.',
        ),
        (
            'process_responsible_ref_sensitive',
            'stage7.reporting.annual_process_responsible_ref_sensitive',
            'Proceso anual contiene responsable_revision_ref sensible para reporting.',
        ),
        (
            'ddjj_missing_for_process',
            'stage7.reporting.annual_ddjj_missing_for_process',
            'Existen procesos de renta anual sin DDJJ asociada.',
        ),
        (
            'f22_missing_for_process',
            'stage7.reporting.annual_f22_missing_for_process',
            'Existen procesos de renta anual sin F22 asociado.',
        ),
        (
            'process_ddjj_ref_missing',
            'stage7.reporting.annual_process_ddjj_ref_missing',
            'Proceso anual aprobado, observado, rectificado o presentado requiere paquete_ddjj_ref.',
        ),
        (
            'process_f22_ref_missing',
            'stage7.reporting.annual_process_f22_ref_missing',
            'Proceso anual aprobado, observado, rectificado o presentado requiere borrador_f22_ref.',
        ),
        (
            'process_responsible_ref_missing',
            'stage7.reporting.annual_process_responsible_ref_missing',
            'Proceso anual aprobado, observado, rectificado o presentado requiere responsable_revision_ref.',
        ),
        (
            'ddjj_invalid_model',
            'stage7.reporting.annual_ddjj_invalid',
            'Existen DDJJ que no pasan validacion de dominio.',
        ),
        (
            'ddjj_process_mismatch',
            'stage7.reporting.annual_ddjj_process_mismatch',
            'Existen DDJJ asociadas a un proceso anual de otra empresa o ano tributario.',
        ),
        (
            'f22_invalid_model',
            'stage7.reporting.annual_f22_invalid',
            'Existen F22 que no pasan validacion de dominio.',
        ),
        (
            'f22_process_mismatch',
            'stage7.reporting.annual_f22_process_mismatch',
            'Existen F22 asociados a un proceso anual de otra empresa o ano tributario.',
        ),
        (
            'ddjj_not_traceable',
            'stage7.reporting.annual_ddjj_not_traceable',
            'Existen DDJJ sin estado trazable.',
        ),
        (
            'f22_not_traceable',
            'stage7.reporting.annual_f22_not_traceable',
            'Existen F22 sin estado trazable.',
        ),
        (
            'ddjj_summary_missing',
            'stage7.reporting.annual_ddjj_summary_missing',
            'DDJJ requiere resumen_paquete trazable para reporting.',
        ),
        (
            'ddjj_summary_fiscal_year_mismatch',
            'stage7.reporting.annual_ddjj_fiscal_year_mismatch',
            'DDJJ contiene resumen anual de un ano comercial distinto al ano tributario reportado.',
        ),
        (
            'ddjj_sensitive_payload',
            'stage7.reporting.annual_ddjj_sensitive_payload',
            'DDJJ contiene resumen_paquete sensible para reporting.',
        ),
        (
            'ddjj_ref_sensitive',
            'stage7.reporting.annual_ddjj_ref_sensitive',
            'DDJJ contiene paquete_ref sensible para reporting.',
        ),
        (
            'ddjj_responsible_ref_sensitive',
            'stage7.reporting.annual_ddjj_responsible_ref_sensitive',
            'DDJJ contiene responsable_revision_ref sensible para reporting.',
        ),
        (
            'f22_summary_missing',
            'stage7.reporting.annual_f22_summary_missing',
            'F22 requiere resumen_f22 trazable para reporting.',
        ),
        (
            'f22_summary_fiscal_year_mismatch',
            'stage7.reporting.annual_f22_fiscal_year_mismatch',
            'F22 contiene resumen anual de un ano comercial distinto al ano tributario reportado.',
        ),
        (
            'f22_sensitive_payload',
            'stage7.reporting.annual_f22_sensitive_payload',
            'F22 contiene resumen_f22 sensible para reporting.',
        ),
        (
            'f22_ref_sensitive',
            'stage7.reporting.annual_f22_ref_sensitive',
            'F22 contiene borrador_ref sensible para reporting.',
        ),
        (
            'f22_responsible_ref_sensitive',
            'stage7.reporting.annual_f22_responsible_ref_sensitive',
            'F22 contiene responsable_revision_ref sensible para reporting.',
        ),
        (
            'ddjj_ref_missing',
            'stage7.reporting.annual_ddjj_ref_missing',
            'DDJJ aprobada, observada, rectificada o presentada requiere paquete_ref.',
        ),
        (
            'ddjj_responsible_ref_missing',
            'stage7.reporting.annual_ddjj_responsible_ref_missing',
            'DDJJ aprobada, observada, rectificada o presentada requiere responsable_revision_ref.',
        ),
        (
            'f22_ref_missing',
            'stage7.reporting.annual_f22_ref_missing',
            'F22 aprobado, observado, rectificado o presentado requiere borrador_ref.',
        ),
        (
            'f22_responsible_ref_missing',
            'stage7.reporting.annual_f22_responsible_ref_missing',
            'F22 aprobado, observado, rectificado o presentado requiere responsable_revision_ref.',
        ),
    ]:
        if annual_issues.get(key):
            issues.append(_issue(code, message, count=annual_issues[key]))

    for key, missing_code, sensitive_code, missing_message, sensitive_message in [
        (
            'stage5_evidence_ref',
            'stage7.reporting.stage5_evidence_ref_missing',
            'stage7.reporting.stage5_evidence_ref_sensitive',
            'Falta referencia no sensible a ledger/cierres habilitantes.',
            'La referencia a ledger/cierres habilitantes contiene valores sensibles.',
        ),
        (
            'stage6_evidence_ref',
            'stage7.reporting.stage6_evidence_ref_missing',
            'stage7.reporting.stage6_evidence_ref_sensitive',
            'Falta referencia no sensible a renta anual habilitante.',
            'La referencia a renta anual habilitante contiene valores sensibles.',
        ),
        (
            'reporting_api_proof_ref',
            'stage7.reporting.api_proof_ref_missing',
            'stage7.reporting.api_proof_ref_sensitive',
            'Falta referencia no sensible a prueba de APIs de reporting.',
            'La referencia a prueba de APIs de reporting contiene valores sensibles.',
        ),
        (
            'backoffice_visual_ref',
            'stage7.reporting.backoffice_visual_ref_missing',
            'stage7.reporting.backoffice_visual_ref_sensitive',
            'Falta referencia no sensible a visualizacion backoffice trazable.',
            'La referencia a visualizacion backoffice trazable contiene valores sensibles.',
        ),
        (
            'responsible_ref',
            'stage7.reporting.responsible_ref_missing',
            'stage7.reporting.responsible_ref_sensitive',
            'Falta referencia no sensible a responsables de reporting.',
            'La referencia a responsables de reporting contiene valores sensibles.',
        ),
    ]:
        if final_evidence_sensitive[key]:
            issues.append(_issue(sensitive_code, sensitive_message))
        elif not final_evidence[key]:
            issues.append(_issue(missing_code, missing_message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 7 - Reporting trazable',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_STAGE7_REPORTING_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage7_reporting': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'financial_monthly': {
                'approved_closes': approved_closes.count(),
                'posted_events': posted_events.count(),
                'events_total': events.count(),
                'events_by_state': _count_by(events, 'estado_contable'),
                'asientos_total': asientos.count(),
                'asientos_by_state': _count_by(asientos, 'estado'),
                'movimientos_asiento_total': MovimientoAsiento.objects.count(),
                'obligations_total': obligations.count(),
                'obligations_by_state': _count_by(obligations, 'estado_preparacion'),
                **financial_issues,
            },
            'books': {
                'libro_diario_total': libro_diario.count(),
                'libro_mayor_total': libro_mayor.count(),
                'balances_total': balances.count(),
                'libro_diario_by_state': _count_by(libro_diario, 'estado_snapshot'),
                'libro_mayor_by_state': _count_by(libro_mayor, 'estado_snapshot'),
                'balances_by_state': _count_by(balances, 'estado_snapshot'),
                **books_issues,
            },
            'annual_tax': {
                'active_fiscal_configs': active_fiscal_configs.count(),
                'processes_total': annual_processes.count(),
                'processes_by_state': _count_by(annual_processes, 'estado'),
                'processes_without_active_fiscal_config': annual_processes_without_fiscal_config,
                'ddjj_total': ddjj_preparations.count(),
                'ddjj_by_state': _count_by(ddjj_preparations, 'estado_preparacion'),
                'ddjj_without_active_fiscal_config': ddjj_without_fiscal_config,
                'f22_total': f22_preparations.count(),
                'f22_by_state': _count_by(f22_preparations, 'estado_preparacion'),
                'f22_without_active_fiscal_config': f22_without_fiscal_config,
                **annual_issues,
            },
            'audit': {
                'annual_status_transition_metadata_missing': annual_status_transition_metadata_missing,
                'annual_status_responsible_ref_missing': annual_status_review_responsible_issues.get('missing', 0),
                'annual_status_responsible_ref_sensitive': annual_status_review_responsible_issues.get('sensitive', 0),
            },
            'final_evidence': final_evidence,
            'final_evidence_sensitive': final_evidence_sensitive,
            'source_trace': source_trace,
            'source_trace_sensitive': source_trace_sensitive,
        },
        'limitations': [
            'Auditoria local de solo lectura; no genera reportes publicos ni ejecuta smoke externo.',
            'No usa secretos, .env, datos reales, snapshots externos ni integraciones externas.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No cierra Reporting sin configuracion fiscal activa por empresa y evidencia controlada de ledger, renta anual, APIs y visualizacion backoffice.',
        ],
    }
