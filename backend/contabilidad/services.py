from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from cobranza.models import HistorialGarantia, TipoMovimientoGarantia
from conciliacion.models import MovimientoBancarioImportado

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoEventoContable,
    EstadoPreparacionTributaria,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
    TipoMovimientoAsiento,
)


DEFAULT_REGIME_CODE = 'EmpresaContabilidadCompletaV1'


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


def resolve_company_allocations_for_contract(contrato, amount):
    mandato = contrato.mandato_operacion
    if mandato.propietario_empresa_owner_id:
        return [(mandato.propietario_empresa_owner, Decimal(amount))]
    if mandato.propietario_socio_owner_id:
        return []

    participaciones = list(
        mandato.propietario_comunidad_owner.participaciones_activas()
        .filter(participante_empresa__isnull=False)
        .select_related('participante_empresa')
        .order_by('id')
    )
    all_active_participaciones = list(mandato.propietario_comunidad_owner.participaciones_activas().order_by('id'))
    allocated_amounts = _split_amount_by_percentages(
        Decimal(amount),
        [participacion.porcentaje for participacion in all_active_participaciones],
    )
    allocations = []
    for participacion, allocated in zip(all_active_participaciones, allocated_amounts, strict=False):
        if participacion.participante_empresa_id:
            allocations.append((participacion.participante_empresa, allocated))
    return allocations


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
        .order_by('-vigencia_desde')
        .first()
    )


@transaction.atomic
def post_accounting_event(event):
    if event.estado_contable == EstadoEventoContable.POSTED:
        return event.asiento_contable

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


@transaction.atomic
def prepare_monthly_close(empresa, anio, mes):
    pending_events = get_company_period_events(empresa, anio, mes).exclude(estado_contable=EstadoEventoContable.POSTED)
    if pending_events.exists():
        raise ValueError('Existen eventos contables pendientes o en revision para el periodo.')

    asientos = get_company_period_asientos(empresa, anio, mes)
    if asientos.filter(debe_total__isnull=True).exists():
        raise ValueError('Existen asientos incompletos en el periodo.')
    for asiento in asientos:
        if asiento.debe_total != asiento.haber_total:
            raise ValueError('Existen asientos descuadrados en el periodo.')

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
    }
    close.save()
    return close


@transaction.atomic
def approve_monthly_close(close):
    if close.estado != EstadoCierreMensual.PREPARED:
        raise ValueError('Solo se puede aprobar un cierre mensual en estado preparado.')
    close.estado = EstadoCierreMensual.APPROVED
    close.fecha_aprobacion = timezone.now()
    close.save(update_fields=['estado', 'fecha_aprobacion', 'updated_at'])
    return close


@transaction.atomic
def reopen_monthly_close(close):
    if close.estado != EstadoCierreMensual.APPROVED:
        raise ValueError('Solo se puede reabrir un cierre mensual aprobado.')
    close.estado = EstadoCierreMensual.REOPENED
    close.save(update_fields=['estado', 'updated_at'])
    return close
