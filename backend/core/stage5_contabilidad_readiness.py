from __future__ import annotations

from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    ReglaContable,
)
from contabilidad.services import (
    asiento_period_matches_accounting_date,
    get_company_period_events,
    get_company_period_unresolved_bank_movements,
    summarize_asiento_movement_integrity,
)
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference


AUTHORIZED_STAGE5_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}


def _non_sensitive_reference(value: str) -> bool:
    return is_non_sensitive_reference(value)


def _issue(code: str, message: str, *, count: int = 1, severity: str = 'blocking') -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _count_invalid(queryset) -> int:
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _count_sensitive_payloads(queryset, field_name: str) -> int:
    count = 0
    for item in queryset:
        if contains_sensitive_reference(getattr(item, field_name, None), include_sensitive_keys=True):
            count += 1
    return count


def _count_sensitive_references(queryset, field_name: str) -> int:
    count = 0
    for item in queryset:
        value = getattr(item, field_name, '')
        if str(value or '').strip() and not is_non_sensitive_reference(value):
            count += 1
    return count


def _count_by(queryset, field_name: str) -> dict[str, int]:
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _count_rules_without_active_matrix(rules) -> int:
    count = 0
    for rule in rules:
        if not rule.lineas_matriz.filter(estado=EstadoRegistro.ACTIVE).exists():
            count += 1
    return count


def _ledger_close_issues(closes) -> dict[str, int]:
    counts = Counter()
    for close in closes:
        period = f'{close.anio:04d}-{close.mes:02d}'
        libro_diario = LibroDiario.objects.filter(empresa=close.empresa, periodo=period).first()
        libro_mayor = LibroMayor.objects.filter(empresa=close.empresa, periodo=period).first()
        balance = BalanceComprobacion.objects.filter(empresa=close.empresa, periodo=period).first()

        if close.estado == EstadoCierreMensual.APPROVED and not close.fecha_aprobacion:
            counts['approved_without_approval_date'] += 1
        if close.estado in {EstadoCierreMensual.PREPARED, EstadoCierreMensual.APPROVED} and not close.fecha_preparacion:
            counts['prepared_without_preparation_date'] += 1
        if not libro_diario or not libro_mayor or not balance:
            counts['snapshots_missing'] += 1
        elif balance.resumen.get('cuadrado') is not True:
            counts['balance_not_square'] += 1

        if get_company_period_unresolved_bank_movements(close.empresa, close.anio, close.mes).exists():
            counts['conciliation_unresolved'] += 1
        if get_company_period_events(close.empresa, close.anio, close.mes).exclude(
            estado_contable=EstadoEventoContable.POSTED
        ).exists():
            counts['events_pending'] += 1

    return dict(sorted(counts.items()))


def collect_stage5_contabilidad_readiness(
    *,
    stage3_evidence_ref: str = '',
    ledger_proof_ref: str = '',
    reports_proof_ref: str = '',
    responsible_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
    fiscal_configs = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario')
    active_fiscal_configs = fiscal_configs.filter(estado=EstadoRegistro.ACTIVE)
    invalid_active_fiscal_configs = _count_invalid(active_fiscal_configs)

    accounts = CuentaContable.objects.select_related('empresa')
    active_accounts = accounts.filter(estado=EstadoRegistro.ACTIVE)
    control_accounts = active_accounts.filter(es_control_obligatoria=True)

    rules = ReglaContable.objects.select_related('empresa')
    active_rules = rules.filter(estado=EstadoRegistro.ACTIVE)
    matrices = MatrizReglasContables.objects.select_related('regla_contable', 'cuenta_debe', 'cuenta_haber')
    active_matrices = matrices.filter(estado=EstadoRegistro.ACTIVE)
    invalid_rules = _count_invalid(active_rules)
    invalid_matrices = _count_invalid(active_matrices)
    rules_without_active_matrix = _count_rules_without_active_matrix(active_rules)

    events = EventoContable.objects.select_related('empresa')
    posted_events = events.filter(estado_contable=EstadoEventoContable.POSTED)
    pending_events = events.exclude(estado_contable=EstadoEventoContable.POSTED).count()
    posted_events_without_asiento = posted_events.filter(asiento_contable__isnull=True).count()
    events_sensitive_payloads = _count_sensitive_payloads(events, 'payload_resumen')

    asientos_qs = AsientoContable.objects.select_related('evento_contable').prefetch_related(
        'movimientos__cuenta_contable'
    )
    asientos = list(asientos_qs)
    unbalanced_asientos = sum(1 for asiento in asientos if asiento.debe_total != asiento.haber_total)
    asiento_period_mismatches = sum(1 for asiento in asientos if not asiento_period_matches_accounting_date(asiento))
    posted_asientos_without_hash = asientos_qs.filter(estado=EstadoAsientoContable.POSTED, hash_integridad='').count()
    asientos_without_movements = sum(1 for asiento in asientos if not asiento.movimientos.exists())
    movement_totals_mismatch = 0
    movement_company_mismatch = 0
    for asiento in asientos:
        movement_integrity = summarize_asiento_movement_integrity(asiento)
        if movement_integrity['company_mismatch_count']:
            movement_company_mismatch += 1
        if movement_integrity['movement_count'] and (
            movement_integrity['debit_total'] != asiento.debe_total
            or movement_integrity['credit_total'] != asiento.haber_total
        ):
            movement_totals_mismatch += 1
    movement_sensitive_refs = _count_sensitive_references(MovimientoAsiento.objects.all(), 'centro_resultado_ref')

    obligations = ObligacionTributariaMensual.objects.select_related('empresa')
    pending_obligations = obligations.filter(
        estado_preparacion__in=[
            EstadoPreparacionTributaria.PENDING_DATA,
            EstadoPreparacionTributaria.IN_PREPARATION,
            EstadoPreparacionTributaria.OBSERVED,
        ]
    ).count()
    obligations_sensitive_payloads = _count_sensitive_payloads(obligations, 'detalle_calculo')

    closes = CierreMensualContable.objects.select_related('empresa')
    prepared_or_approved_closes = closes.filter(
        estado__in=[EstadoCierreMensual.PREPARED, EstadoCierreMensual.APPROVED]
    )
    approved_closes = closes.filter(estado=EstadoCierreMensual.APPROVED)
    libro_diario_snapshots = LibroDiario.objects.all()
    libro_mayor_snapshots = LibroMayor.objects.all()
    balance_snapshots = BalanceComprobacion.objects.all()
    ledger_snapshot_sensitive_references = sum(
        [
            _count_sensitive_references(libro_diario_snapshots, 'storage_ref'),
            _count_sensitive_payloads(libro_diario_snapshots, 'resumen'),
            _count_sensitive_references(libro_mayor_snapshots, 'storage_ref'),
            _count_sensitive_payloads(libro_mayor_snapshots, 'resumen'),
            _count_sensitive_references(balance_snapshots, 'storage_ref'),
            _count_sensitive_payloads(balance_snapshots, 'resumen'),
        ]
    )
    close_sensitive_payloads = _count_sensitive_payloads(closes, 'resumen_obligaciones')
    close_issues = _ledger_close_issues(prepared_or_approved_closes)

    final_evidence = {
        'stage3_evidence_ref': _non_sensitive_reference(stage3_evidence_ref),
        'ledger_proof_ref': _non_sensitive_reference(ledger_proof_ref),
        'reports_proof_ref': _non_sensitive_reference(reports_proof_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE5_SOURCE_KINDS

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage5.source_kind_not_authorized',
                'La readiness local de Etapa 5 no puede cerrar Contabilidad sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, code, message in [
            (
                'source_label',
                'stage5.source_label_missing',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 5.',
            ),
            (
                'authorization_ref',
                'stage5.authorization_ref_missing',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 5.',
            ),
        ]:
            if not source_trace[key]:
                issues.append(_issue(code, message))
    if active_fiscal_configs.count() == 0:
        issues.append(
            _issue(
                'stage5.fiscal_config_missing',
                'Etapa 5 requiere al menos una configuracion fiscal activa para cierre mensual.',
            )
        )
    if invalid_active_fiscal_configs:
        issues.append(
            _issue(
                'stage5.fiscal_config_invalid',
                'Existen configuraciones fiscales activas que no pasan validacion de dominio.',
                count=invalid_active_fiscal_configs,
            )
        )
    if active_accounts.count() == 0:
        issues.append(
            _issue('stage5.accounts_missing', 'Etapa 5 requiere plan de cuentas activo para contabilizar.')
        )
    if control_accounts.count() == 0:
        issues.append(
            _issue(
                'stage5.control_accounts_missing',
                'Etapa 5 requiere cuentas contables de control marcadas para ledger operativo.',
            )
        )
    if active_rules.count() == 0:
        issues.append(
            _issue('stage5.rules_missing', 'Etapa 5 requiere reglas contables activas.')
        )
    if active_matrices.count() == 0:
        issues.append(
            _issue('stage5.matrix_missing', 'Etapa 5 requiere matriz de reglas contables activa.')
        )
    if invalid_rules:
        issues.append(
            _issue(
                'stage5.rules_invalid',
                'Existen reglas contables activas que no pasan validacion de dominio.',
                count=invalid_rules,
            )
        )
    if invalid_matrices:
        issues.append(
            _issue(
                'stage5.matrix_invalid',
                'Existen matrices contables activas que no pasan validacion de dominio.',
                count=invalid_matrices,
            )
        )
    if rules_without_active_matrix:
        issues.append(
            _issue(
                'stage5.rules_without_matrix',
                'Existen reglas contables activas sin linea de matriz activa.',
                count=rules_without_active_matrix,
            )
        )
    if events.count() == 0:
        issues.append(
            _issue('stage5.events_missing', 'No existen eventos contables para auditar ledger mensual.')
        )
    if pending_events:
        issues.append(
            _issue(
                'stage5.events_not_posted',
                'Existen eventos contables pendientes o en revision.',
                count=pending_events,
            )
        )
    if posted_events_without_asiento:
        issues.append(
            _issue(
                'stage5.posted_event_without_asiento',
                'Existen eventos contabilizados sin asiento contable.',
                count=posted_events_without_asiento,
            )
        )
    if events_sensitive_payloads:
        issues.append(
            _issue(
                'stage5.events_sensitive_payload',
                'Existen eventos contables con payload heredado que contiene URLs, tokens, credenciales o correos.',
                count=events_sensitive_payloads,
            )
        )
    if unbalanced_asientos:
        issues.append(
            _issue(
                'stage5.asiento_unbalanced',
                'Existen asientos contables descuadrados.',
                count=unbalanced_asientos,
            )
        )
    if asiento_period_mismatches:
        issues.append(
            _issue(
                'stage5.asiento_period_mismatch',
                'Existen asientos cuyo periodo_contable no coincide con fecha_contable.',
                count=asiento_period_mismatches,
            )
        )
    if posted_asientos_without_hash:
        issues.append(
            _issue(
                'stage5.asiento_hash_missing',
                'Existen asientos contabilizados sin hash de integridad.',
                count=posted_asientos_without_hash,
            )
        )
    if asientos_without_movements:
        issues.append(
            _issue(
                'stage5.asiento_movements_missing',
                'Existen asientos sin movimientos de debe/haber.',
                count=asientos_without_movements,
            )
        )
    if movement_company_mismatch:
        issues.append(
            _issue(
                'stage5.asiento_movement_company_mismatch',
                'Existen asientos con movimientos asociados a cuentas de otra empresa.',
                count=movement_company_mismatch,
            )
        )
    if movement_totals_mismatch:
        issues.append(
            _issue(
                'stage5.asiento_movement_totals_mismatch',
                'Existen asientos cuyos movimientos no cuadran con sus totales debe/haber.',
                count=movement_totals_mismatch,
            )
        )
    if movement_sensitive_refs:
        issues.append(
            _issue(
                'stage5.asiento_movement_sensitive_reference',
                'Existen movimientos de asiento con referencias de centro de resultado sensibles.',
                count=movement_sensitive_refs,
            )
        )
    if pending_obligations:
        issues.append(
            _issue(
                'stage5.tax_obligations_pending',
                'Existen obligaciones tributarias mensuales pendientes, en preparacion u observadas.',
                count=pending_obligations,
            )
        )
    if obligations_sensitive_payloads:
        issues.append(
            _issue(
                'stage5.tax_obligations_sensitive_payload',
                'Existen obligaciones tributarias mensuales con detalle de calculo sensible.',
                count=obligations_sensitive_payloads,
            )
        )
    if ledger_snapshot_sensitive_references:
        issues.append(
            _issue(
                'stage5.ledger_snapshot_sensitive_reference',
                'Existen snapshots de libros o balance con storage_ref/resumen sensible heredado.',
                count=ledger_snapshot_sensitive_references,
            )
        )
    if close_sensitive_payloads:
        issues.append(
            _issue(
                'stage5.close_sensitive_payload',
                'Existen cierres mensuales con resumen de obligaciones sensible.',
                count=close_sensitive_payloads,
            )
        )
    if approved_closes.count() == 0:
        issues.append(
            _issue(
                'stage5.approved_close_missing',
                'Etapa 5 requiere al menos un cierre mensual aprobado para evidencia local de ledger.',
            )
        )

    for key, code, message in [
        (
            'snapshots_missing',
            'stage5.close_snapshots_missing',
            'Existen cierres preparados/aprobados sin libro diario, libro mayor o balance del periodo.',
        ),
        (
            'balance_not_square',
            'stage5.close_balance_not_square',
            'Existen balances de comprobacion del cierre que no cuadran.',
        ),
        (
            'conciliation_unresolved',
            'stage5.close_conciliation_unresolved',
            'Existen cierres con movimientos bancarios no resueltos en el periodo.',
        ),
        (
            'events_pending',
            'stage5.close_events_pending',
            'Existen cierres con eventos del periodo pendientes o en revision.',
        ),
        (
            'prepared_without_preparation_date',
            'stage5.close_preparation_date_missing',
            'Existen cierres preparados/aprobados sin fecha de preparacion.',
        ),
        (
            'approved_without_approval_date',
            'stage5.close_approval_date_missing',
            'Existen cierres aprobados sin fecha de aprobacion.',
        ),
    ]:
        if close_issues.get(key):
            issues.append(_issue(code, message, count=close_issues[key]))

    for key, code, message in [
        (
            'stage3_evidence_ref',
            'stage5.stage3_evidence_ref_missing',
            'Falta referencia no sensible a cierre/evidencia de Conciliacion.',
        ),
        (
            'ledger_proof_ref',
            'stage5.ledger_proof_ref_missing',
            'Falta referencia no sensible a prueba de ledger/asientos.',
        ),
        (
            'reports_proof_ref',
            'stage5.reports_proof_ref_missing',
            'Falta referencia no sensible a reportes contables trazables.',
        ),
        (
            'responsible_ref',
            'stage5.responsible_ref_missing',
            'Falta referencia no sensible a responsables contables.',
        ),
    ]:
        if not final_evidence[key]:
            issues.append(_issue(code, message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 5 - Cierre mensual y contabilidad',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_STAGE5_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage5_contabilidad': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'fiscal_setup': {
                'configs_total': fiscal_configs.count(),
                'active_configs': active_fiscal_configs.count(),
                'invalid_active_configs': invalid_active_fiscal_configs,
            },
            'rules': {
                'accounts_total': accounts.count(),
                'active_accounts': active_accounts.count(),
                'control_accounts': control_accounts.count(),
                'active_rules': active_rules.count(),
                'rules_by_event_type': _count_by(active_rules, 'evento_tipo'),
                'active_matrix_rows': active_matrices.count(),
                'invalid_rules': invalid_rules,
                'invalid_matrices': invalid_matrices,
                'rules_without_active_matrix': rules_without_active_matrix,
            },
            'ledger': {
                'events_total': events.count(),
                'events_by_state': _count_by(events, 'estado_contable'),
                'pending_events': pending_events,
                'posted_events_without_asiento': posted_events_without_asiento,
                'events_sensitive_payloads': events_sensitive_payloads,
                'asientos_total': asientos_qs.count(),
                'asientos_by_state': _count_by(asientos_qs, 'estado'),
                'unbalanced_asientos': unbalanced_asientos,
                'asiento_period_mismatches': asiento_period_mismatches,
                'posted_asientos_without_hash': posted_asientos_without_hash,
                'asientos_without_movements': asientos_without_movements,
                'movement_company_mismatch': movement_company_mismatch,
                'movement_totals_mismatch': movement_totals_mismatch,
                'movement_sensitive_refs': movement_sensitive_refs,
                'movimientos_asiento_total': MovimientoAsiento.objects.count(),
                'movimientos_by_type': _count_by(MovimientoAsiento.objects.all(), 'tipo_movimiento'),
                'ledger_snapshot_sensitive_references': ledger_snapshot_sensitive_references,
            },
            'monthly_close': {
                'closes_total': closes.count(),
                'closes_by_state': _count_by(closes, 'estado'),
                'approved_closes': approved_closes.count(),
                'close_sensitive_payloads': close_sensitive_payloads,
                'obligations_total': obligations.count(),
                'obligations_by_state': _count_by(obligations, 'estado_preparacion'),
                'obligations_sensitive_payloads': obligations_sensitive_payloads,
                **close_issues,
            },
            'final_evidence': final_evidence,
            'source_trace': source_trace,
        },
        'limitations': [
            'Auditoria local de solo lectura; no presenta F29/F21 ni conecta SII.',
            'No usa secretos, .env, datos reales, banco real ni snapshots externos.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No cierra Etapa 5 sin Conciliacion cerrada y evidencia controlada de ledger/reportes.',
        ],
    }
