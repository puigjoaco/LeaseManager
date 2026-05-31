from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from cobranza.models import HistorialGarantia, TipoMovimientoGarantia
from conciliacion.models import (
    CuadraturaBancaria,
    EstadoConciliacionMovimiento,
    EstadoCuadraturaBancaria,
    EstadoIngresoDesconocido,
    MovimientoBancarioImportado,
    TransferenciaIntercuenta,
)

from .models import (
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
    LiquidacionMensual,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
    TipoEfectoReaperturaCierre,
    TipoMovimientoAsiento,
    TipoOwnerLiquidacion,
    has_text,
)


DEFAULT_REGIME_CODE = 'EmpresaContabilidadCompletaV1'
MONTHLY_CLOSE_REOPEN_POLICY_TYPE = 'reapertura_cierre_mensual'
MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE = 'ReaperturaCierreMensualReverso'
MONTHLY_CLOSE_REOPEN_COMPLEMENTARY_EVENT_TYPE = 'ReaperturaCierreMensualComplementario'
MONTHLY_CLOSE_REOPEN_EFFECT_EVENT_TYPES = {
    TipoEfectoReaperturaCierre.REVERSAL: MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
    TipoEfectoReaperturaCierre.COMPLEMENTARY_ENTRY: MONTHLY_CLOSE_REOPEN_COMPLEMENTARY_EVENT_TYPE,
}


def period_date_bounds(anio, mes):
    return date(anio, mes, 1), date(anio, mes, monthrange(anio, mes)[1])


def next_period_start(anio, mes):
    if mes == 12:
        return date(anio + 1, 1, 1)
    return date(anio, mes + 1, 1)


def _effective_company_allocations_for_community(comunidad, amount, effective_date):
    all_participaciones = list(comunidad.participaciones_vigentes_en(effective_date).order_by('id'))
    allocated_amounts = _split_amount_by_percentages(
        Decimal(amount),
        [participacion.porcentaje for participacion in all_participaciones],
    )
    allocations = []
    for participacion, allocated in zip(all_participaciones, allocated_amounts, strict=False):
        if participacion.participante_empresa_id:
            allocations.append((participacion.participante_empresa, allocated))
    return allocations


def _split_amount_by_percentages(total_amount, percentages):
    if not percentages:
        return []
    allocated = []
    running_total = Decimal('0.00')
    for index, percentage in enumerate(percentages):
        if index == len(percentages) - 1:
            amount = total_amount - running_total
        else:
            amount = (total_amount * percentage / Decimal('100.00')).quantize(Decimal('0.01'))
            running_total += amount
        allocated.append(amount)
    return allocated


def resolve_company_distributions_for_payment(payment):
    return list(
        payment.distribuciones_cobro.filter(beneficiario_empresa_owner__isnull=False).select_related(
            'beneficiario_empresa_owner'
        )
    )


def resolve_company_allocations_for_contract(contrato, amount, *, effective_date=None):
    mandato = contrato.mandato_operacion
    effective_date = effective_date or timezone.localdate()
    if mandato.propietario_empresa_owner_id:
        return [(mandato.propietario_empresa_owner, Decimal(amount))]
    if mandato.propietario_socio_owner_id:
        return []
    return _effective_company_allocations_for_community(
        mandato.propietario_comunidad_owner,
        amount,
        effective_date,
    )


def _get_monthly_close_for_date(empresa, fecha_operativa):
    if empresa is None or fecha_operativa is None:
        return None
    return CierreMensualContable.objects.filter(
        empresa=empresa,
        anio=fecha_operativa.year,
        mes=fecha_operativa.month,
    ).first()


def ensure_default_regime():
    return RegimenTributarioEmpresa.objects.get_or_create(
        codigo_regimen=DEFAULT_REGIME_CODE,
        defaults={
            'descripcion': 'Regimen fiscal automatizable canonico del v1',
            'estado': 'activa',
        },
    )[0]


@transaction.atomic
def create_accounting_event(*, empresa, evento_tipo, entidad_origen_tipo, entidad_origen_id, fecha_operativa, moneda, monto_base, payload_resumen, idempotency_key):
    if Decimal(monto_base) <= Decimal('0.00'):
        raise ValueError('El monto_base del evento contable debe ser mayor que cero.')
    event, created = EventoContable.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            'empresa': empresa,
            'evento_tipo': evento_tipo,
            'entidad_origen_tipo': entidad_origen_tipo,
            'entidad_origen_id': str(entidad_origen_id),
            'fecha_operativa': fecha_operativa,
            'moneda': moneda,
            'monto_base': monto_base,
            'payload_resumen': payload_resumen,
        },
    )
    if created:
        post_accounting_event(event)
    return event, created


def get_active_fiscal_config(empresa):
    if empresa is None:
        return None
    config = getattr(empresa, 'configuracion_fiscal', None)
    if config and config.estado == 'activa':
        return config
    return None


def get_active_rule(event):
    if event.empresa_id is None:
        return None
    return (
        ReglaContable.objects.filter(
            empresa=event.empresa,
            evento_tipo=event.evento_tipo,
            estado='activa',
        )
        .filter(vigencia_desde__lte=event.fecha_operativa)
        .filter(Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=event.fecha_operativa))
        .order_by('-vigencia_desde', '-id')
        .first()
    )


@transaction.atomic
def post_accounting_event(event):
    if event.estado_contable == EstadoEventoContable.POSTED:
        return event.asiento_contable
    if event.monto_base <= Decimal('0.00'):
        event.estado_contable = EstadoEventoContable.REVIEW
        event.save(update_fields=['estado_contable', 'updated_at'])
        return None
    if event.empresa_id and EventoContable.objects.filter(
        empresa_id=event.empresa_id,
        evento_tipo=event.evento_tipo,
        entidad_origen_tipo=event.entidad_origen_tipo,
        entidad_origen_id=event.entidad_origen_id,
        estado_contable=EstadoEventoContable.POSTED,
    ).exclude(pk=event.pk).exists():
        event.estado_contable = EstadoEventoContable.REVIEW
        event.save(update_fields=['estado_contable', 'updated_at'])
        return None

    close = _get_monthly_close_for_date(event.empresa, event.fecha_operativa)
    if close and close.estado == EstadoCierreMensual.APPROVED:
        event.estado_contable = EstadoEventoContable.REVIEW
        event.save(update_fields=['estado_contable', 'updated_at'])
        return None

    config = get_active_fiscal_config(event.empresa)
    if not config or config.regimen_tributario.codigo_regimen != DEFAULT_REGIME_CODE:
        event.estado_contable = EstadoEventoContable.REVIEW
        event.save(update_fields=['estado_contable', 'updated_at'])
        return None

    rule = get_active_rule(event)
    if not rule:
        event.estado_contable = EstadoEventoContable.REVIEW
        event.save(update_fields=['estado_contable', 'updated_at'])
        return None

    matrix_rows = list(
        MatrizReglasContables.objects.filter(regla_contable=rule, estado='activa').select_related(
            'cuenta_debe',
            'cuenta_haber',
        )
    )
    if len(matrix_rows) != 1:
        event.estado_contable = EstadoEventoContable.REVIEW
        event.save(update_fields=['estado_contable', 'updated_at'])
        return None

    row = matrix_rows[0]
    asiento, _ = AsientoContable.objects.get_or_create(
        evento_contable=event,
        defaults={
            'fecha_contable': event.fecha_operativa,
            'periodo_contable': event.fecha_operativa.strftime('%Y-%m'),
            'estado': EstadoAsientoContable.POSTED,
            'debe_total': event.monto_base,
            'haber_total': event.monto_base,
            'moneda_funcional': config.moneda_funcional,
        },
    )
    asiento.debe_total = event.monto_base
    asiento.haber_total = event.monto_base
    asiento.moneda_funcional = config.moneda_funcional
    asiento.set_hash_integridad()
    asiento.full_clean()
    asiento.save()

    asiento.movimientos.all().delete()
    MovimientoAsiento.objects.bulk_create(
        [
            MovimientoAsiento(
                asiento_contable=asiento,
                cuenta_contable=row.cuenta_debe,
                tipo_movimiento=TipoMovimientoAsiento.DEBIT,
                monto=event.monto_base,
                glosa=f'{event.evento_tipo} {event.entidad_origen_tipo}:{event.entidad_origen_id}',
            ),
            MovimientoAsiento(
                asiento_contable=asiento,
                cuenta_contable=row.cuenta_haber,
                tipo_movimiento=TipoMovimientoAsiento.CREDIT,
                monto=event.monto_base,
                glosa=f'{event.evento_tipo} {event.entidad_origen_tipo}:{event.entidad_origen_id}',
            ),
        ]
    )

    event.estado_contable = EstadoEventoContable.POSTED
    event.save(update_fields=['estado_contable', 'updated_at'])
    return asiento


def create_payment_reconciled_event(payment, movimiento):
    events = []
    for distribution in resolve_company_distributions_for_payment(payment):
        if distribution.monto_conciliado_clp <= 0:
            continue
        event = create_accounting_event(
            empresa=distribution.beneficiario_empresa_owner,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='pago_mensual',
            entidad_origen_id=payment.pk,
            fecha_operativa=payment.fecha_deposito_banco or payment.fecha_deteccion_sistema or movimiento.fecha_movimiento,
            moneda='CLP',
            monto_base=distribution.monto_conciliado_clp,
            payload_resumen={
                'movimiento_bancario_id': movimiento.pk,
                'contrato_id': payment.contrato_id,
                'distribucion_cobro_mensual_id': distribution.pk,
            },
            idempotency_key=f'PagoConciliadoArriendo:{payment.pk}:{movimiento.pk}:{distribution.pk}',
        )
        events.append(event)
    return events


def create_guarantee_event(historial):
    event_type_map = {
        TipoMovimientoGarantia.DEPOSIT: 'GarantiaRecibida',
        TipoMovimientoGarantia.PARTIAL_RETURN: 'GarantiaDevuelta',
        TipoMovimientoGarantia.TOTAL_RETURN: 'GarantiaDevuelta',
        TipoMovimientoGarantia.PARTIAL_RETENTION: 'GarantiaAplicadaADeuda',
        TipoMovimientoGarantia.TOTAL_RETENTION: 'GarantiaAplicadaADeuda',
    }
    events = []
    for empresa, allocated_amount in resolve_company_allocations_for_contract(
        historial.garantia_contractual.contrato,
        historial.monto_clp,
        effective_date=historial.fecha,
    ):
        if allocated_amount <= 0:
            continue
        event = create_accounting_event(
            empresa=empresa,
            evento_tipo=event_type_map[historial.tipo_movimiento],
            entidad_origen_tipo='historial_garantia',
            entidad_origen_id=historial.pk,
            fecha_operativa=historial.fecha,
            moneda='CLP',
            monto_base=allocated_amount,
            payload_resumen={
                'garantia_contractual_id': historial.garantia_contractual_id,
                'contrato_id': historial.garantia_contractual.contrato_id,
                'tipo_movimiento': historial.tipo_movimiento,
            },
            idempotency_key=f'Garantia:{historial.pk}:{historial.tipo_movimiento}:{empresa.pk}',
        )
        events.append(event)
    return events


def _direct_company_owner_for_bank_account(cuenta_recaudadora):
    if cuenta_recaudadora is None or not cuenta_recaudadora.empresa_owner_id:
        return None
    return cuenta_recaudadora.empresa_owner


def _internal_transfer_event_payload(transfer):
    origin = transfer.movimiento_origen
    destination = transfer.movimiento_destino
    origin_account = origin.conexion_bancaria.cuenta_recaudadora
    destination_account = destination.conexion_bancaria.cuenta_recaudadora
    return {
        'transferencia_intercuenta_id': transfer.pk,
        'movimiento_origen_id': origin.pk,
        'movimiento_destino_id': destination.pk,
        'cuenta_origen_id': origin_account.pk,
        'cuenta_destino_id': destination_account.pk,
        'entidad_origen_tipo': transfer.entidad_origen_tipo,
        'entidad_origen_id': transfer.entidad_origen_id,
        'entidad_destino_tipo': transfer.entidad_destino_tipo,
        'entidad_destino_id': transfer.entidad_destino_id,
        'periodo_economico': transfer.periodo_economico,
        'criterio_conciliacion': transfer.criterio_conciliacion,
        'evidencia_transferencia_ref': transfer.evidencia_transferencia_ref,
        'responsable_ref': transfer.responsable_ref,
    }


def create_internal_transfer_events(transfer: TransferenciaIntercuenta):
    transfer = TransferenciaIntercuenta.objects.select_related(
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora__empresa_owner',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora__empresa_owner',
    ).get(pk=transfer.pk)
    payload = _internal_transfer_event_payload(transfer)
    origin = transfer.movimiento_origen
    destination = transfer.movimiento_destino
    origin_company = _direct_company_owner_for_bank_account(origin.conexion_bancaria.cuenta_recaudadora)
    destination_company = _direct_company_owner_for_bank_account(destination.conexion_bancaria.cuenta_recaudadora)

    events = []
    if origin_company is not None:
        event, _ = create_accounting_event(
            empresa=origin_company,
            evento_tipo='TransferenciaIntercuentaSalida',
            entidad_origen_tipo='transferencia_intercuenta',
            entidad_origen_id=transfer.pk,
            fecha_operativa=origin.fecha_movimiento,
            moneda='CLP',
            monto_base=origin.monto,
            payload_resumen={**payload, 'direccion_transferencia': 'salida'},
            idempotency_key=f'TransferenciaIntercuentaSalida:{transfer.pk}:{origin_company.pk}',
        )
        events.append(event)

    if destination_company is not None:
        event, _ = create_accounting_event(
            empresa=destination_company,
            evento_tipo='TransferenciaIntercuentaEntrada',
            entidad_origen_tipo='transferencia_intercuenta',
            entidad_origen_id=transfer.pk,
            fecha_operativa=destination.fecha_movimiento,
            moneda='CLP',
            monto_base=destination.monto,
            payload_resumen={**payload, 'direccion_transferencia': 'entrada'},
            idempotency_key=f'TransferenciaIntercuentaEntrada:{transfer.pk}:{destination_company.pk}',
        )
        events.append(event)

    return events


def get_company_period_events(empresa, anio, mes):
    return EventoContable.objects.filter(
        empresa=empresa,
        fecha_operativa__year=anio,
        fecha_operativa__month=mes,
    )


def get_company_period_asientos(empresa, anio, mes):
    return AsientoContable.objects.filter(
        evento_contable__empresa=empresa,
        fecha_contable__year=anio,
        fecha_contable__month=mes,
    )


def summarize_asiento_movement_integrity(asiento):
    debit_total = Decimal('0.00')
    credit_total = Decimal('0.00')
    movement_count = 0
    company_mismatch_count = 0
    for movement in asiento.movimientos.all():
        movement_count += 1
        if movement.cuenta_contable.empresa_id != asiento.evento_contable.empresa_id:
            company_mismatch_count += 1
        if movement.tipo_movimiento == TipoMovimientoAsiento.DEBIT:
            debit_total += movement.monto
        elif movement.tipo_movimiento == TipoMovimientoAsiento.CREDIT:
            credit_total += movement.monto

    return {
        'movement_count': movement_count,
        'debit_total': debit_total,
        'credit_total': credit_total,
        'company_mismatch_count': company_mismatch_count,
    }


def asiento_period_matches_accounting_date(asiento):
    if not asiento.fecha_contable or not asiento.periodo_contable:
        return False
    return asiento.periodo_contable == str(asiento.fecha_contable)[:7]


def build_ledger_snapshots(empresa, anio, mes):
    period = f'{anio:04d}-{mes:02d}'
    asientos = get_company_period_asientos(empresa, anio, mes).prefetch_related('movimientos__cuenta_contable')

    libro_diario, _ = LibroDiario.objects.get_or_create(
        empresa=empresa,
        periodo=period,
        defaults={'estado_snapshot': EstadoCierreMensual.PREPARED},
    )
    libro_diario.estado_snapshot = EstadoCierreMensual.PREPARED
    libro_diario.resumen = {
        'asientos': [
            {
                'asiento_id': asiento.id,
                'fecha_contable': asiento.fecha_contable.isoformat(),
                'debe_total': str(asiento.debe_total),
                'haber_total': str(asiento.haber_total),
            }
            for asiento in asientos
        ]
    }
    libro_diario.save()

    saldo_por_cuenta = {}
    for asiento in asientos:
        for movement in asiento.movimientos.all():
            saldo = saldo_por_cuenta.setdefault(
                movement.cuenta_contable.codigo,
                {
                    'cuenta': movement.cuenta_contable.codigo,
                    'nombre': movement.cuenta_contable.nombre,
                    'debe': Decimal('0.00'),
                    'haber': Decimal('0.00'),
                },
            )
            if movement.tipo_movimiento == TipoMovimientoAsiento.DEBIT:
                saldo['debe'] += movement.monto
            else:
                saldo['haber'] += movement.monto

    libro_mayor, _ = LibroMayor.objects.get_or_create(
        empresa=empresa,
        periodo=period,
        defaults={'estado_snapshot': EstadoCierreMensual.PREPARED},
    )
    libro_mayor.estado_snapshot = EstadoCierreMensual.PREPARED
    libro_mayor.resumen = {
        'cuentas': [
            {
                'cuenta': item['cuenta'],
                'nombre': item['nombre'],
                'debe': str(item['debe']),
                'haber': str(item['haber']),
            }
            for item in saldo_por_cuenta.values()
        ]
    }
    libro_mayor.save()

    balance, _ = BalanceComprobacion.objects.get_or_create(
        empresa=empresa,
        periodo=period,
        defaults={'estado_snapshot': EstadoCierreMensual.PREPARED},
    )
    total_debe = sum(item['debe'] for item in saldo_por_cuenta.values())
    total_haber = sum(item['haber'] for item in saldo_por_cuenta.values())
    balance.estado_snapshot = EstadoCierreMensual.PREPARED
    balance.resumen = {
        'total_debe': str(total_debe),
        'total_haber': str(total_haber),
        'cuadrado': total_debe == total_haber,
    }
    balance.save()

    return {
        'libro_diario': libro_diario,
        'libro_mayor': libro_mayor,
        'balance_comprobacion': balance,
    }


def update_ledger_snapshot_state(empresa, anio, mes, estado_snapshot):
    period = f'{anio:04d}-{mes:02d}'
    for model in (LibroDiario, LibroMayor, BalanceComprobacion):
        snapshot = model.objects.filter(empresa=empresa, periodo=period).first()
        if not snapshot:
            raise ValueError('No se puede cambiar estado del cierre sin snapshots contables del periodo.')
        snapshot.estado_snapshot = estado_snapshot
        snapshot.save(update_fields=['estado_snapshot', 'updated_at'])


def build_monthly_tax_obligations(empresa, anio, mes):
    config = get_active_fiscal_config(empresa)
    if not config or config.regimen_tributario.codigo_regimen != DEFAULT_REGIME_CODE:
        raise ValueError('La empresa no tiene configuracion fiscal activa apta para cierre mensual oficial.')

    payment_events = EventoContable.objects.filter(
        empresa=empresa,
        fecha_operativa__year=anio,
        fecha_operativa__month=mes,
        evento_tipo='PagoConciliadoArriendo',
        estado_contable=EstadoEventoContable.POSTED,
    )
    base_ingresos = sum((event.monto_base for event in payment_events), Decimal('0.00'))

    obligations = []
    if config.aplica_ppm:
        estado = EstadoPreparacionTributaria.PENDING_DATA
        monto = Decimal('0.00')
        detalle = {'base_ingresos': str(base_ingresos)}
        if config.tasa_ppm_vigente is not None:
            monto = (base_ingresos * config.tasa_ppm_vigente / Decimal('100')).quantize(Decimal('0.01'))
            estado = EstadoPreparacionTributaria.PREPARED
            detalle['tasa_ppm_vigente'] = str(config.tasa_ppm_vigente)
        obligation, _ = ObligacionTributariaMensual.objects.update_or_create(
            empresa=empresa,
            anio=anio,
            mes=mes,
            obligacion_tipo='PPM',
            defaults={
                'base_imponible': base_ingresos,
                'monto_calculado': monto,
                'estado_preparacion': estado,
                'detalle_calculo': detalle,
            },
        )
        obligations.append(obligation)

    if config.afecta_iva_arriendo:
        iva_amount = (base_ingresos * config.tasa_iva / Decimal('100')).quantize(Decimal('0.01'))
        obligation, _ = ObligacionTributariaMensual.objects.update_or_create(
            empresa=empresa,
            anio=anio,
            mes=mes,
            obligacion_tipo='IVA',
            defaults={
                'base_imponible': base_ingresos,
                'monto_calculado': iva_amount,
                'estado_preparacion': EstadoPreparacionTributaria.PREPARED,
                'detalle_calculo': {'tasa_iva': str(config.tasa_iva)},
            },
        )
        obligations.append(obligation)

    return obligations


def get_company_period_bank_movements(empresa, anio, mes):
    start, end = period_date_bounds(anio, mes)
    return MovimientoBancarioImportado.objects.filter(
        conexion_bancaria__cuenta_recaudadora__empresa_owner=empresa,
        fecha_movimiento__range=(start, end),
    )


def get_company_period_unresolved_bank_movements(empresa, anio, mes):
    return get_company_period_bank_movements(empresa, anio, mes).filter(
        Q(
            estado_conciliacion__in=[
                EstadoConciliacionMovimiento.PENDING,
                EstadoConciliacionMovimiento.UNKNOWN_INCOME,
                EstadoConciliacionMovimiento.MANUAL_REQUIRED,
            ]
        )
        | Q(ingreso_desconocido__estado=EstadoIngresoDesconocido.OPEN)
    )


def summarize_company_period_bank_square(empresa, anio, mes):
    periodo = f'{anio:04d}-{mes:02d}'
    account_ids = set(
        get_company_period_bank_movements(empresa, anio, mes)
        .values_list('conexion_bancaria__cuenta_recaudadora_id', flat=True)
        .distinct()
    )
    account_ids.discard(None)
    if not account_ids:
        return {
            'cuentas_bancarias_con_movimientos': 0,
            'cuadraturas_bancarias_cuadradas': 0,
            'cuadraturas_bancarias_faltantes': 0,
            'cuadraturas_bancarias_no_cuadradas': 0,
        }

    quadratures = list(
        CuadraturaBancaria.objects.filter(
            cuenta_recaudadora_id__in=account_ids,
            periodo_economico=periodo,
        ).only('cuenta_recaudadora_id', 'estado', 'diferencia_clp')
    )
    quadrature_account_ids = {item.cuenta_recaudadora_id for item in quadratures}
    squared_account_ids = {
        item.cuenta_recaudadora_id
        for item in quadratures
        if item.estado == EstadoCuadraturaBancaria.SQUARED and item.diferencia_clp == Decimal('0.00')
    }
    return {
        'cuentas_bancarias_con_movimientos': len(account_ids),
        'cuadraturas_bancarias_cuadradas': len(squared_account_ids),
        'cuadraturas_bancarias_faltantes': len(account_ids - quadrature_account_ids),
        'cuadraturas_bancarias_no_cuadradas': len(quadrature_account_ids - squared_account_ids),
    }


def assert_company_period_conciliacion_ready(empresa, anio, mes):
    unresolved = get_company_period_unresolved_bank_movements(empresa, anio, mes)
    count = unresolved.count()
    if count:
        raise ValueError(
            f'Conciliacion no cerrada para el periodo: existen {count} movimientos bancarios sin resolver.'
        )
    bank_square = summarize_company_period_bank_square(empresa, anio, mes)
    missing_or_invalid = (
        bank_square['cuadraturas_bancarias_faltantes']
        + bank_square['cuadraturas_bancarias_no_cuadradas']
    )
    if missing_or_invalid:
        raise ValueError(
            'Banco no cuadrado para el periodo: existen '
            f'{missing_or_invalid} cuentas con movimientos sin cuadratura bancaria cuadrada.'
        )
    return {
        'movimientos_bancarios_periodo': get_company_period_bank_movements(empresa, anio, mes).count(),
        'movimientos_bancarios_no_resueltos': 0,
        **bank_square,
    }


def assert_company_period_accounting_ready(empresa, anio, mes):
    pending_events = get_company_period_events(empresa, anio, mes).exclude(estado_contable=EstadoEventoContable.POSTED)
    if pending_events.exists():
        raise ValueError('Existen eventos contables pendientes o en revision para el periodo.')

    asientos = get_company_period_asientos(empresa, anio, mes).select_related('evento_contable').prefetch_related(
        'movimientos__cuenta_contable'
    )
    if asientos.filter(debe_total__isnull=True).exists():
        raise ValueError('Existen asientos incompletos en el periodo.')
    for asiento in asientos:
        if not asiento_period_matches_accounting_date(asiento):
            raise ValueError('Existen asientos cuyo periodo_contable no coincide con fecha_contable.')
        if asiento.debe_total != asiento.haber_total:
            raise ValueError('Existen asientos descuadrados en el periodo.')
        movement_integrity = summarize_asiento_movement_integrity(asiento)
        if movement_integrity['movement_count'] == 0:
            raise ValueError('Existen asientos sin movimientos de debe/haber en el periodo.')
        if movement_integrity['company_mismatch_count']:
            raise ValueError('Existen movimientos contables asociados a cuentas de otra empresa.')
        if (
            movement_integrity['debit_total'] != asiento.debe_total
            or movement_integrity['credit_total'] != asiento.haber_total
        ):
            raise ValueError('Los movimientos del asiento no cuadran con los totales registrados.')
        if asiento.estado == EstadoAsientoContable.POSTED:
            if not has_text(asiento.hash_integridad):
                raise ValueError('Existen asientos contabilizados sin hash de integridad.')
            if not asiento.hash_integridad_matches():
                raise ValueError('Existen asientos con hash de integridad desactualizado.')


def assert_company_period_liquidation_ready(close):
    liquidation = (
        LiquidacionMensual.objects.filter(
            owner_tipo=TipoOwnerLiquidacion.COMPANY,
            empresa=close.empresa,
            cierre_contable=close,
            anio=close.anio,
            mes=close.mes,
            estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED],
        )
        .order_by('-updated_at', '-id')
        .first()
    )
    if liquidation is None:
        raise ValueError(
            'Aprobar cierre mensual requiere liquidacion mensual de empresa preparada para el mismo periodo.'
        )
    try:
        liquidation.full_clean()
    except DjangoValidationError as error:
        raise ValueError('La liquidacion mensual de empresa no esta lista para aprobar el cierre.') from error
    return liquidation


@transaction.atomic
def prepare_monthly_close(empresa, anio, mes):
    existing_close = CierreMensualContable.objects.filter(empresa=empresa, anio=anio, mes=mes).first()
    if existing_close and existing_close.estado == EstadoCierreMensual.APPROVED:
        raise ValueError('El periodo ya fue aprobado; debe reabrirse antes de volver a preparar el cierre.')

    conciliacion_summary = assert_company_period_conciliacion_ready(empresa, anio, mes)
    assert_company_period_accounting_ready(empresa, anio, mes)

    obligations = build_monthly_tax_obligations(empresa, anio, mes)
    snapshots = build_ledger_snapshots(empresa, anio, mes)

    close, _ = CierreMensualContable.objects.get_or_create(
        empresa=empresa,
        anio=anio,
        mes=mes,
    )
    close.estado = EstadoCierreMensual.PREPARED
    close.fecha_preparacion = timezone.now()
    close.resumen_obligaciones = {
        'obligaciones': [
            {
                'tipo': obligation.obligacion_tipo,
                'base_imponible': str(obligation.base_imponible),
                'monto_calculado': str(obligation.monto_calculado),
                'estado_preparacion': obligation.estado_preparacion,
            }
            for obligation in obligations
        ],
        'snapshots': {key: value.periodo for key, value in snapshots.items()},
        'conciliacion': conciliacion_summary,
    }
    close.save()
    return close


@transaction.atomic
def approve_monthly_close(close):
    if close.estado != EstadoCierreMensual.PREPARED:
        raise ValueError('Solo se puede aprobar un cierre mensual en estado preparado.')
    conciliacion_summary = assert_company_period_conciliacion_ready(close.empresa, close.anio, close.mes)
    assert_company_period_accounting_ready(close.empresa, close.anio, close.mes)
    liquidation = assert_company_period_liquidation_ready(close)

    close.resumen_obligaciones = {
        **(close.resumen_obligaciones or {}),
        'conciliacion': conciliacion_summary,
        'liquidacion_mensual': {
            'id': liquidation.pk,
            'estado': liquidation.estado,
            'owner_tipo': liquidation.owner_tipo,
        },
    }
    update_ledger_snapshot_state(close.empresa, close.anio, close.mes, EstadoCierreMensual.APPROVED)
    close.estado = EstadoCierreMensual.APPROVED
    close.fecha_aprobacion = timezone.now()
    close.save(update_fields=['resumen_obligaciones', 'estado', 'fecha_aprobacion', 'updated_at'])
    return close


def get_active_monthly_close_reopen_policy(empresa):
    return PoliticaReversoContable.objects.filter(
        empresa=empresa,
        tipo_ajuste=MONTHLY_CLOSE_REOPEN_POLICY_TYPE,
        estado=EstadoRegistro.ACTIVE,
        permite_reapertura=True,
        aprobacion_requerida=True,
    ).first()


def assert_monthly_close_reopen_allowed(close):
    policy = get_active_monthly_close_reopen_policy(close.empresa)
    if not policy:
        raise ValueError(
            'Reapertura de cierre mensual requiere politica activa que permita reapertura y exija aprobacion.'
        )
    return policy


@transaction.atomic
def reopen_monthly_close(close, *, tipo_efecto, monto_efecto, motivo, efecto_esperado, evidencia_ref):
    if close.estado != EstadoCierreMensual.APPROVED:
        raise ValueError('Solo se puede reabrir un cierre mensual aprobado.')
    policy = assert_monthly_close_reopen_allowed(close)
    tipo_efecto = str(tipo_efecto or '').strip()
    if tipo_efecto not in MONTHLY_CLOSE_REOPEN_EFFECT_EVENT_TYPES:
        raise ValueError('La reapertura requiere tipo_efecto reverso o asiento_complementario.')
    if tipo_efecto == TipoEfectoReaperturaCierre.REVERSAL and not policy.usa_reverso:
        raise ValueError('La politica activa no permite reverso para esta reapertura.')
    if tipo_efecto == TipoEfectoReaperturaCierre.COMPLEMENTARY_ENTRY and not policy.usa_asiento_complementario:
        raise ValueError('La politica activa no permite asiento complementario para esta reapertura.')

    monto_efecto = Decimal(str(monto_efecto))
    if monto_efecto <= Decimal('0.00'):
        raise ValueError('La reapertura requiere monto_efecto mayor que cero.')

    event_type = MONTHLY_CLOSE_REOPEN_EFFECT_EVENT_TYPES[tipo_efecto]
    sequence = close.efectos_reapertura.count() + 1
    event = EventoContable.objects.create(
        empresa=close.empresa,
        evento_tipo=event_type,
        entidad_origen_tipo='cierre_mensual_contable',
        entidad_origen_id=str(close.pk),
        fecha_operativa=next_period_start(close.anio, close.mes),
        moneda='CLP',
        monto_base=monto_efecto,
        payload_resumen={
            'cierre_mensual_contable_id': close.pk,
            'periodo_reabierto': f'{close.anio:04d}-{close.mes:02d}',
            'tipo_efecto': tipo_efecto,
            'motivo': motivo,
            'efecto_esperado': efecto_esperado,
            'evidencia_ref': evidencia_ref,
            'politica_reverso_contable_id': policy.pk,
        },
        idempotency_key=f'{event_type}:{close.pk}:{sequence}',
    )
    event.full_clean()
    asiento = post_accounting_event(event)
    if asiento is None or event.estado_contable != EstadoEventoContable.POSTED:
        raise ValueError(
            'La reapertura requiere regla y matriz activas para contabilizar el efecto posterior al cierre.'
        )

    effect = EfectoReaperturaCierreMensual(
        cierre=close,
        politica_reverso=policy,
        evento_contable=event,
        tipo_efecto=tipo_efecto,
        monto_efecto=monto_efecto,
        motivo=motivo,
        efecto_esperado=efecto_esperado,
        evidencia_ref=evidencia_ref,
    )
    effect.full_clean()
    effect.save()

    update_ledger_snapshot_state(close.empresa, close.anio, close.mes, EstadoCierreMensual.REOPENED)
    reopen_trace = {
        'efecto_reapertura_id': effect.pk,
        'evento_contable_id': event.pk,
        'asiento_contable_id': asiento.pk,
        'tipo_efecto': tipo_efecto,
        'monto_efecto': str(monto_efecto),
        'motivo': motivo,
        'efecto_esperado': efecto_esperado,
        'evidencia_ref': evidencia_ref,
        'politica_reverso_contable_id': policy.pk,
    }
    close.resumen_obligaciones = {
        **(close.resumen_obligaciones or {}),
        'reapertura': reopen_trace,
    }
    close.estado = EstadoCierreMensual.REOPENED
    close.save(update_fields=['resumen_obligaciones', 'estado', 'updated_at'])
    return close, effect
