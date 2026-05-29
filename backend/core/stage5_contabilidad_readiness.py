from __future__ import annotations

from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count
from django.utils import timezone

from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EfectoReaperturaCierreMensual,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EstadoLiquidacionMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    EventoContable,
    LibroDiario,
    LibroMayor,
    LineaLiquidacionMensual,
    LiquidacionMensual,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    ReglaContable,
    TipoLineaLiquidacion,
    TipoOwnerLiquidacion,
    has_text,
)
from contabilidad.services import (
    MONTHLY_CLOSE_REOPEN_POLICY_TYPE,
    asiento_period_matches_accounting_date,
    get_active_monthly_close_reopen_policy,
    get_company_period_events,
    get_company_period_unresolved_bank_movements,
    summarize_company_period_bank_square,
    summarize_asiento_movement_integrity,
)
from conciliacion.models import TransferenciaIntercuenta
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


def _count_internal_transfer_accounting_event_gaps(transfers) -> int:
    missing = 0
    for transfer in transfers:
        origin_movement = transfer.movimiento_origen
        destination_movement = transfer.movimiento_destino
        origin_account = transfer.movimiento_origen.conexion_bancaria.cuenta_recaudadora
        destination_account = transfer.movimiento_destino.conexion_bancaria.cuenta_recaudadora
        expected_specs = []
        if origin_account.empresa_owner_id:
            expected_specs.append(
                (
                    'TransferenciaIntercuentaSalida',
                    origin_account.empresa_owner_id,
                    origin_movement.fecha_movimiento,
                    origin_movement.monto,
                )
            )
        if destination_account.empresa_owner_id:
            expected_specs.append(
                (
                    'TransferenciaIntercuentaEntrada',
                    destination_account.empresa_owner_id,
                    destination_movement.fecha_movimiento,
                    destination_movement.monto,
                )
            )

        for event_type, company_id, movement_date, movement_amount in expected_specs:
            if not EventoContable.objects.filter(
                empresa_id=company_id,
                evento_tipo=event_type,
                entidad_origen_tipo='transferencia_intercuenta',
                entidad_origen_id=str(transfer.pk),
                fecha_operativa=movement_date,
                moneda='CLP',
                monto_base=movement_amount,
            ).exists():
                missing += 1
    return missing


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
        bank_square = summarize_company_period_bank_square(close.empresa, close.anio, close.mes)
        if bank_square['cuadraturas_bancarias_faltantes']:
            counts['bank_square_missing'] += 1
        if bank_square['cuadraturas_bancarias_no_cuadradas']:
            counts['bank_square_not_square'] += 1
        if get_company_period_events(close.empresa, close.anio, close.mes).exclude(
            estado_contable=EstadoEventoContable.POSTED
        ).exists():
            counts['events_pending'] += 1

    return dict(sorted(counts.items()))


def _count_approved_closes_without_company_liquidation(approved_closes) -> int:
    missing = 0
    for close in approved_closes:
        if not LiquidacionMensual.objects.filter(
            owner_tipo=TipoOwnerLiquidacion.COMPANY,
            empresa=close.empresa,
            anio=close.anio,
            mes=close.mes,
            estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED],
        ).exists():
            missing += 1
    return missing


def _count_required_admin_fee_line_missing(liquidations) -> int:
    missing = 0
    for liquidation in liquidations:
        if liquidation.comision_administracion_aplica and not liquidation.lineas.filter(
            tipo_linea=TipoLineaLiquidacion.ADMINISTRATION_FEE
        ).exists():
            missing += 1
    return missing


def _count_prepared_economic_lines_without_event(lines) -> int:
    economic_line_types = {
        TipoLineaLiquidacion.RENT_INCOME,
        TipoLineaLiquidacion.OPERATING_EXPENSE,
        TipoLineaLiquidacion.ADMINISTRATION_FEE,
        TipoLineaLiquidacion.PARTNER_DISTRIBUTION,
        TipoLineaLiquidacion.TAX_PROVISION,
        TipoLineaLiquidacion.ADJUSTMENT,
    }
    return lines.filter(
        liquidacion__estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED],
        tipo_linea__in=economic_line_types,
        evento_contable__isnull=True,
    ).count()


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
    internal_transfers = TransferenciaIntercuenta.objects.select_related(
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora',
    )
    internal_transfer_accounting_event_gaps = _count_internal_transfer_accounting_event_gaps(internal_transfers)

    events = EventoContable.objects.select_related('empresa')
    posted_events = events.filter(estado_contable=EstadoEventoContable.POSTED)
    pending_events = events.exclude(estado_contable=EstadoEventoContable.POSTED).count()
    posted_events_without_asiento = posted_events.filter(asiento_contable__isnull=True).count()
    duplicate_posted_events = (
        posted_events.filter(empresa_id__isnull=False)
        .values('empresa_id', 'evento_tipo', 'entidad_origen_tipo', 'entidad_origen_id')
        .annotate(event_count=Count('id'))
        .filter(event_count__gt=1)
        .count()
    )
    events_sensitive_payloads = _count_sensitive_payloads(events, 'payload_resumen')

    asientos_qs = AsientoContable.objects.select_related('evento_contable').prefetch_related(
        'movimientos__cuenta_contable'
    )
    asientos = list(asientos_qs)
    unbalanced_asientos = sum(1 for asiento in asientos if asiento.debe_total != asiento.haber_total)
    asiento_period_mismatches = sum(1 for asiento in asientos if not asiento_period_matches_accounting_date(asiento))
    posted_asientos_without_hash = sum(
        1
        for asiento in asientos
        if asiento.estado == EstadoAsientoContable.POSTED and not has_text(asiento.hash_integridad)
    )
    posted_asientos_with_stale_hash = sum(
        1
        for asiento in asientos
        if asiento.estado == EstadoAsientoContable.POSTED
        and has_text(asiento.hash_integridad)
        and not asiento.hash_integridad_matches()
    )
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
    reopened_closes = closes.filter(estado=EstadoCierreMensual.REOPENED)
    reopen_effects = EfectoReaperturaCierreMensual.objects.select_related(
        'cierre',
        'politica_reverso',
        'evento_contable',
    )
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
    monthly_close_reopen_policies = PoliticaReversoContable.objects.filter(
        tipo_ajuste=MONTHLY_CLOSE_REOPEN_POLICY_TYPE,
        estado=EstadoRegistro.ACTIVE,
        permite_reapertura=True,
        aprobacion_requerida=True,
    )
    approved_closes_without_reopen_policy = sum(
        1 for close in approved_closes if not get_active_monthly_close_reopen_policy(close.empresa)
    )
    reopened_closes_without_effect = sum(1 for close in reopened_closes if not close.efectos_reapertura.exists())
    reopen_effects_without_posted_event = reopen_effects.exclude(
        evento_contable__estado_contable=EstadoEventoContable.POSTED
    ).count()
    reopen_effects_sensitive_references = sum(
        [
            _count_sensitive_references(reopen_effects, 'evidencia_ref'),
            _count_sensitive_payloads(reopen_effects, 'motivo'),
            _count_sensitive_payloads(reopen_effects, 'efecto_esperado'),
        ]
    )

    liquidations = LiquidacionMensual.objects.select_related(
        'empresa',
        'comunidad',
        'socio',
        'cierre_contable',
    ).prefetch_related('lineas')
    prepared_or_approved_liquidations = liquidations.filter(
        estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED]
    )
    liquidation_lines = LineaLiquidacionMensual.objects.select_related(
        'liquidacion',
        'beneficiario_socio',
        'evento_contable',
    )
    invalid_liquidations = _count_invalid(liquidations)
    invalid_liquidation_lines = _count_invalid(liquidation_lines)
    approved_closes_without_company_liquidation = _count_approved_closes_without_company_liquidation(approved_closes)
    required_admin_fee_line_missing = _count_required_admin_fee_line_missing(prepared_or_approved_liquidations)
    prepared_economic_lines_without_event = _count_prepared_economic_lines_without_event(liquidation_lines)
    liquidation_sensitive_references = sum(
        [
            _count_sensitive_references(liquidations, 'evidencia_base_ref'),
            _count_sensitive_references(liquidations, 'responsable_ref'),
            _count_sensitive_references(liquidations, 'saldo_final_evidencia_ref'),
            _count_sensitive_payloads(liquidations, 'saldo_final_explicacion'),
            _count_sensitive_references(liquidation_lines, 'evidencia_ref'),
            _count_sensitive_payloads(liquidation_lines, 'descripcion'),
        ]
    )

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
    if internal_transfer_accounting_event_gaps:
        issues.append(
            _issue(
                'stage5.internal_transfer_accounting_event_missing',
                'Existen transferencias intercuenta de empresas sin evento contable de salida o entrada.',
                count=internal_transfer_accounting_event_gaps,
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
    if duplicate_posted_events:
        issues.append(
            _issue(
                'stage5.duplicate_posted_events',
                'Existen hechos economicos con mas de un evento contable contabilizado para la misma empresa y origen.',
                count=duplicate_posted_events,
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
    if posted_asientos_with_stale_hash:
        issues.append(
            _issue(
                'stage5.asiento_hash_mismatch',
                'Existen asientos contabilizados con hash de integridad desactualizado.',
                count=posted_asientos_with_stale_hash,
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
    if approved_closes_without_reopen_policy:
        issues.append(
            _issue(
                'stage5.close_reopen_policy_missing',
                'Existen cierres aprobados sin politica activa que permita reapertura controlada y exija aprobacion.',
                count=approved_closes_without_reopen_policy,
            )
        )
    if reopened_closes_without_effect:
        issues.append(
            _issue(
                'stage5.reopened_close_effect_missing',
                'Existen cierres reabiertos sin reverso o asiento complementario trazable.',
                count=reopened_closes_without_effect,
            )
        )
    if reopen_effects_without_posted_event:
        issues.append(
            _issue(
                'stage5.reopen_effect_event_not_posted',
                'Existen efectos de reapertura sin evento contable contabilizado.',
                count=reopen_effects_without_posted_event,
            )
        )
    if reopen_effects_sensitive_references:
        issues.append(
            _issue(
                'stage5.reopen_effect_sensitive_reference',
                'Existen efectos de reapertura con motivo, efecto esperado o evidencia sensible.',
                count=reopen_effects_sensitive_references,
            )
        )
    if approved_closes_without_company_liquidation:
        issues.append(
            _issue(
                'stage5.liquidation_missing_for_approved_close',
                'Existen cierres mensuales aprobados sin liquidacion mensual de empresa trazable.',
                count=approved_closes_without_company_liquidation,
            )
        )
    if invalid_liquidations:
        issues.append(
            _issue(
                'stage5.liquidation_invalid',
                'Existen liquidaciones mensuales que no pasan validacion de dominio.',
                count=invalid_liquidations,
            )
        )
    if invalid_liquidation_lines:
        issues.append(
            _issue(
                'stage5.liquidation_line_invalid',
                'Existen lineas de liquidacion mensual que no pasan validacion de dominio.',
                count=invalid_liquidation_lines,
            )
        )
    if required_admin_fee_line_missing:
        issues.append(
            _issue(
                'stage5.liquidation_admin_fee_line_missing',
                'Existen liquidaciones con comision de administracion aplicable sin linea explicita.',
                count=required_admin_fee_line_missing,
            )
        )
    if prepared_economic_lines_without_event:
        issues.append(
            _issue(
                'stage5.liquidation_line_accounting_trace_missing',
                'Existen lineas economicas de liquidacion preparada/aprobada sin evento contable trazable.',
                count=prepared_economic_lines_without_event,
            )
        )
    if liquidation_sensitive_references:
        issues.append(
            _issue(
                'stage5.liquidation_sensitive_reference',
                'Existen liquidaciones o lineas con evidencia, responsable, explicacion o descripcion sensible.',
                count=liquidation_sensitive_references,
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
            'bank_square_missing',
            'stage5.close_bank_square_missing',
            'Existen cierres con movimientos bancarios del periodo sin CuadraturaBancaria.',
        ),
        (
            'bank_square_not_square',
            'stage5.close_bank_square_not_square',
            'Existen cierres con cuadraturas bancarias no cuadradas o con diferencia.',
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
                'duplicate_posted_events': duplicate_posted_events,
                'events_sensitive_payloads': events_sensitive_payloads,
                'asientos_total': asientos_qs.count(),
                'asientos_by_state': _count_by(asientos_qs, 'estado'),
                'unbalanced_asientos': unbalanced_asientos,
                'asiento_period_mismatches': asiento_period_mismatches,
                'posted_asientos_without_hash': posted_asientos_without_hash,
                'posted_asientos_with_stale_hash': posted_asientos_with_stale_hash,
                'asientos_without_movements': asientos_without_movements,
                'movement_company_mismatch': movement_company_mismatch,
                'movement_totals_mismatch': movement_totals_mismatch,
                'movement_sensitive_refs': movement_sensitive_refs,
                'movimientos_asiento_total': MovimientoAsiento.objects.count(),
                'movimientos_by_type': _count_by(MovimientoAsiento.objects.all(), 'tipo_movimiento'),
                'ledger_snapshot_sensitive_references': ledger_snapshot_sensitive_references,
            },
            'internal_transfers': {
                'total': internal_transfers.count(),
                'accounting_event_gaps': internal_transfer_accounting_event_gaps,
            },
            'monthly_close': {
                'closes_total': closes.count(),
                'closes_by_state': _count_by(closes, 'estado'),
                'approved_closes': approved_closes.count(),
                'reopened_closes': reopened_closes.count(),
                'monthly_close_reopen_policies_active': monthly_close_reopen_policies.count(),
                'approved_closes_without_reopen_policy': approved_closes_without_reopen_policy,
                'reopen_effects_total': reopen_effects.count(),
                'reopened_closes_without_effect': reopened_closes_without_effect,
                'reopen_effects_without_posted_event': reopen_effects_without_posted_event,
                'reopen_effects_sensitive_references': reopen_effects_sensitive_references,
                'close_sensitive_payloads': close_sensitive_payloads,
                'obligations_total': obligations.count(),
                'obligations_by_state': _count_by(obligations, 'estado_preparacion'),
                'obligations_sensitive_payloads': obligations_sensitive_payloads,
                **close_issues,
            },
            'liquidations': {
                'liquidations_total': liquidations.count(),
                'liquidations_by_state': _count_by(liquidations, 'estado'),
                'liquidations_by_owner_type': _count_by(liquidations, 'owner_tipo'),
                'prepared_or_approved_liquidations': prepared_or_approved_liquidations.count(),
                'lines_total': liquidation_lines.count(),
                'lines_by_type': _count_by(liquidation_lines, 'tipo_linea'),
                'approved_closes_without_company_liquidation': approved_closes_without_company_liquidation,
                'invalid_liquidations': invalid_liquidations,
                'invalid_liquidation_lines': invalid_liquidation_lines,
                'required_admin_fee_line_missing': required_admin_fee_line_missing,
                'prepared_economic_lines_without_event': prepared_economic_lines_without_event,
                'liquidation_sensitive_references': liquidation_sensitive_references,
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
