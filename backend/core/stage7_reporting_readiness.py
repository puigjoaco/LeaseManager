from __future__ import annotations

from collections import Counter
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EstadoPreparacionTributaria,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MovimientoAsiento,
    ObligacionTributariaMensual,
)
from sii.models import DDJJPreparacionAnual, F22PreparacionAnual, ProcesoRentaAnual, has_text


SENSITIVE_REFERENCE_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
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
    return bool(normalized) and not SENSITIVE_REFERENCE_PATTERN.search(normalized)


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


def _period_label(anio: int, mes: int) -> str:
    return f'{int(anio):04d}-{int(mes):02d}'


def _annual_summary_is_traceable(summary: Any) -> bool:
    if not isinstance(summary, dict):
        return False
    obligations = summary.get('obligaciones')
    return bool(summary.get('fiscal_year')) and isinstance(obligations, list) and bool(obligations)


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
    asientos_without_movements = 0
    for asiento in asientos:
        if asiento.estado != EstadoAsientoContable.POSTED:
            invalid_asientos += 1
        if asiento.debe_total != asiento.haber_total:
            unbalanced_asientos += 1
        if asiento.estado == EstadoAsientoContable.POSTED and not has_text(asiento.hash_integridad):
            posted_without_hash += 1
        if not asiento.movimientos.exists():
            asientos_without_movements += 1

    if invalid_asientos:
        counts['asiento_not_posted'] = invalid_asientos
    if unbalanced_asientos:
        counts['asiento_unbalanced'] = unbalanced_asientos
    if posted_without_hash:
        counts['asiento_hash_missing'] = posted_without_hash
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

    for ddjj in ddjj_preparations:
        try:
            ddjj.full_clean()
        except ValidationError:
            counts['ddjj_invalid_model'] += 1
        if ddjj.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            counts['ddjj_not_traceable'] += 1
        if not ddjj.resumen_paquete:
            counts['ddjj_summary_missing'] += 1
        if ddjj.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not has_text(ddjj.paquete_ref):
            counts['ddjj_ref_missing'] += 1

    for f22 in f22_preparations:
        try:
            f22.full_clean()
        except ValidationError:
            counts['f22_invalid_model'] += 1
        if f22.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            counts['f22_not_traceable'] += 1
        if not f22.resumen_f22:
            counts['f22_summary_missing'] += 1
        if f22.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not has_text(f22.borrador_ref):
            counts['f22_ref_missing'] += 1

    return dict(sorted(counts.items()))


def collect_stage7_reporting_readiness(
    *,
    stage5_evidence_ref: str = '',
    stage6_evidence_ref: str = '',
    reporting_api_proof_ref: str = '',
    backoffice_visual_ref: str = '',
    responsible_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
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

    final_evidence = {
        'stage5_evidence_ref': _non_sensitive_reference(stage5_evidence_ref),
        'stage6_evidence_ref': _non_sensitive_reference(stage6_evidence_ref),
        'reporting_api_proof_ref': _non_sensitive_reference(reporting_api_proof_ref),
        'backoffice_visual_ref': _non_sensitive_reference(backoffice_visual_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }

    issues: list[dict[str, Any]] = []
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
    if ddjj_preparations.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.ddjj_missing',
                'Reporting tributario anual requiere DDJJ asociada al proceso anual.',
            )
        )
    if f22_preparations.count() == 0:
        issues.append(
            _issue(
                'stage7.reporting.f22_missing',
                'Reporting tributario anual requiere F22 asociado al proceso anual.',
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
            'ddjj_invalid_model',
            'stage7.reporting.annual_ddjj_invalid',
            'Existen DDJJ que no pasan validacion de dominio.',
        ),
        (
            'f22_invalid_model',
            'stage7.reporting.annual_f22_invalid',
            'Existen F22 que no pasan validacion de dominio.',
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
            'f22_summary_missing',
            'stage7.reporting.annual_f22_summary_missing',
            'F22 requiere resumen_f22 trazable para reporting.',
        ),
        (
            'ddjj_ref_missing',
            'stage7.reporting.annual_ddjj_ref_missing',
            'DDJJ aprobada, observada, rectificada o presentada requiere paquete_ref.',
        ),
        (
            'f22_ref_missing',
            'stage7.reporting.annual_f22_ref_missing',
            'F22 aprobado, observado, rectificado o presentado requiere borrador_ref.',
        ),
    ]:
        if annual_issues.get(key):
            issues.append(_issue(code, message, count=annual_issues[key]))

    for key, code, message in [
        (
            'stage5_evidence_ref',
            'stage7.reporting.stage5_evidence_ref_missing',
            'Falta referencia no sensible a ledger/cierres habilitantes.',
        ),
        (
            'stage6_evidence_ref',
            'stage7.reporting.stage6_evidence_ref_missing',
            'Falta referencia no sensible a renta anual habilitante.',
        ),
        (
            'reporting_api_proof_ref',
            'stage7.reporting.api_proof_ref_missing',
            'Falta referencia no sensible a prueba de APIs de reporting.',
        ),
        (
            'backoffice_visual_ref',
            'stage7.reporting.backoffice_visual_ref_missing',
            'Falta referencia no sensible a visualizacion backoffice trazable.',
        ),
        (
            'responsible_ref',
            'stage7.reporting.responsible_ref_missing',
            'Falta referencia no sensible a responsables de reporting.',
        ),
    ]:
        if not final_evidence[key]:
            issues.append(_issue(code, message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 7 - Reporting trazable',
        'source_kind': source_kind,
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
                'processes_total': annual_processes.count(),
                'processes_by_state': _count_by(annual_processes, 'estado'),
                'ddjj_total': ddjj_preparations.count(),
                'ddjj_by_state': _count_by(ddjj_preparations, 'estado_preparacion'),
                'f22_total': f22_preparations.count(),
                'f22_by_state': _count_by(f22_preparations, 'estado_preparacion'),
                **annual_issues,
            },
            'final_evidence': final_evidence,
        },
        'limitations': [
            'Auditoria local de solo lectura; no genera reportes publicos ni ejecuta smoke externo.',
            'No usa secretos, .env, datos reales, snapshots externos ni integraciones externas.',
            'No cierra Reporting sin evidencia controlada de ledger, renta anual, APIs y visualizacion backoffice.',
        ],
    }
