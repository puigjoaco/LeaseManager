import secrets
from datetime import date
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils import timezone

from .models import (
    AjusteContrato,
    CodigoCobroResidual,
    DistribucionCobroMensual,
    EstadoGarantia,
    EstadoPago,
    EstadoCuentaArrendatario,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    RepactacionDeuda,
    TipoMovimientoGarantia,
    ValorUFDiario,
)


def get_operational_month_start(anio, mes):
    return date(int(anio), int(mes), 1)


def get_uf_value_for_month(anio, mes):
    month_start = get_operational_month_start(anio, mes)
    uf_value = ValorUFDiario.objects.filter(fecha=month_start).first()
    if not uf_value:
        raise ValueError(f'No existe valor UF cargado para {month_start.isoformat()}.')
    return uf_value.valor


def get_period_for_month(contrato, anio, mes):
    month_start = get_operational_month_start(anio, mes)
    return (
        contrato.periodos_contractuales.filter(fecha_inicio__lte=month_start, fecha_fin__gte=month_start)
        .order_by('numero_periodo')
        .first()
    )


def get_primary_contract_property(contrato):
    return contrato.contrato_propiedades.filter(rol_en_contrato='principal').select_related('propiedad').first()


def truncate_to_clp(value):
    return Decimal(value).quantize(Decimal('1'), rounding=ROUND_DOWN)


def apply_effective_code(amount_clp, code):
    return Decimal((int(amount_clp) // 1000) * 1000 + int(code))


def calculate_monthly_amount(contrato, anio, mes):
    period = get_period_for_month(contrato, anio, mes)
    if not period:
        raise ValueError('No existe un periodo contractual vigente para el mes operativo solicitado.')

    primary_property = get_primary_contract_property(contrato)
    if not primary_property:
        raise ValueError('El contrato no tiene una propiedad principal configurada.')

    uf_value = None
    base_amount = period.monto_base
    if period.moneda_base == 'UF':
        uf_value = get_uf_value_for_month(anio, mes)
        base_amount = base_amount * uf_value

    month_start = get_operational_month_start(anio, mes)
    adjustments = AjusteContrato.objects.filter(
        contrato=contrato,
        activo=True,
        mes_inicio__lte=month_start,
        mes_fin__gte=month_start,
    ).order_by('mes_inicio', 'id')

    total_amount = Decimal(base_amount)
    for adjustment in adjustments:
        adjustment_amount = adjustment.monto
        if adjustment.moneda == 'UF':
            if uf_value is None:
                uf_value = get_uf_value_for_month(anio, mes)
            adjustment_amount = adjustment_amount * uf_value
        total_amount += adjustment_amount

    truncated = truncate_to_clp(total_amount)
    if truncated < Decimal('1000'):
        raise ValueError('El monto mensual calculado queda bajo el minimo operativo de CLP 1.000.')

    effective_code = primary_property.codigo_conciliacion_efectivo_snapshot
    final_amount = apply_effective_code(truncated, effective_code)

    return {
        'periodo_contractual': period,
        'monto_facturable_clp': truncated,
        'monto_calculado_clp': final_amount,
        'codigo_conciliacion_efectivo': effective_code,
        'fecha_vencimiento': date(int(anio), int(mes), contrato.dia_pago_mensual),
    }


def _split_amount_by_percentages(total_amount, percentages):
    if not percentages:
        return []
    allocated = []
    running_total = Decimal('0.00')
    for index, percentage in enumerate(percentages):
        if index == len(percentages) - 1:
            amount = total_amount - running_total
        else:
            amount = (total_amount * percentage / Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            running_total += amount
        allocated.append(amount)
    return allocated


def build_payment_distribution_snapshot(payment):
    mandato = payment.contrato.mandato_operacion
    owner_type = mandato.propietario_tipo
    payment.distribuciones_cobro.all().delete()

    distribution_rows = []
    if owner_type == 'empresa':
        distribution_rows.append(
            {
                'beneficiario_empresa_owner': mandato.propietario_empresa_owner,
                'beneficiario_socio_owner': None,
                'porcentaje_snapshot': Decimal('100.00'),
            }
        )
    elif owner_type == 'socio':
        distribution_rows.append(
            {
                'beneficiario_empresa_owner': None,
                'beneficiario_socio_owner': mandato.propietario_socio_owner,
                'porcentaje_snapshot': Decimal('100.00'),
            }
        )
    else:
        participaciones = list(
            mandato.propietario_comunidad_owner.participaciones_activas()
            .select_related('participante_socio', 'participante_empresa')
            .order_by('id')
        )
        for participacion in participaciones:
            distribution_rows.append(
                {
                    'beneficiario_empresa_owner': participacion.participante_empresa,
                    'beneficiario_socio_owner': participacion.participante_socio,
                    'porcentaje_snapshot': participacion.porcentaje,
                }
            )

    devengados = _split_amount_by_percentages(
        Decimal(payment.monto_facturable_clp),
        [row['porcentaje_snapshot'] for row in distribution_rows],
    )
    conciliados = _split_amount_by_percentages(
        Decimal(payment.monto_pagado_clp),
        [row['porcentaje_snapshot'] for row in distribution_rows],
    )

    distribution_items = []
    for index, row in enumerate(distribution_rows):
        beneficiario_empresa = row['beneficiario_empresa_owner']
        requiere_dte = bool(
            beneficiario_empresa
            and mandato.entidad_facturadora_id
            and beneficiario_empresa.id == mandato.entidad_facturadora_id
        )
        distribution_items.append(
            DistribucionCobroMensual(
                pago_mensual=payment,
                beneficiario_socio_owner=row['beneficiario_socio_owner'],
                beneficiario_empresa_owner=beneficiario_empresa,
                porcentaje_snapshot=row['porcentaje_snapshot'],
                monto_devengado_clp=devengados[index],
                monto_conciliado_clp=conciliados[index],
                monto_facturable_clp=devengados[index] if requiere_dte else Decimal('0.00'),
                requiere_dte=requiere_dte,
                origen_atribucion='snapshot_pago',
            )
        )
    DistribucionCobroMensual.objects.bulk_create(distribution_items)
    return payment.distribuciones_cobro.order_by('id')


def sync_payment_distribution(payment):
    return build_payment_distribution_snapshot(payment)


PAYMENT_STATE_TRANSITIONS = {
    EstadoPago.PENDING: {
        EstadoPago.PAID,
        EstadoPago.OVERDUE,
        EstadoPago.PAID_BY_TERMINATION,
        EstadoPago.FORGIVEN,
    },
    EstadoPago.OVERDUE: {
        EstadoPago.IN_REPAYMENT,
        EstadoPago.PAID,
        EstadoPago.PAID_BY_TERMINATION,
        EstadoPago.FORGIVEN,
    },
    EstadoPago.IN_REPAYMENT: {EstadoPago.PAID_VIA_REPAYMENT},
    EstadoPago.PAID: set(),
    EstadoPago.PAID_VIA_REPAYMENT: set(),
    EstadoPago.PAID_BY_TERMINATION: set(),
    EstadoPago.FORGIVEN: set(),
}


def calculate_days_late(payment):
    reference_date = payment.fecha_deposito_banco or payment.fecha_deteccion_sistema
    if not reference_date:
        return 0
    return max(0, (reference_date - payment.fecha_vencimiento).days)


def sync_payment_state(payment):
    payment.dias_mora = calculate_days_late(payment)
    return payment


def recalculate_guarantee_state(garantia):
    if garantia.monto_recibido == 0:
        garantia.estado_garantia = EstadoGarantia.PENDING
        garantia.fecha_cierre = None
        return garantia

    saldo = garantia.saldo_vigente
    if saldo < 0:
        raise ValueError('La garantia no puede quedar con saldo negativo.')

    if saldo > 0:
        garantia.estado_garantia = (
            EstadoGarantia.PARTIALLY_RETURNED if garantia.monto_devuelto > 0 else EstadoGarantia.HELD
        )
        garantia.fecha_cierre = None
        return garantia

    garantia.fecha_cierre = garantia.fecha_cierre or timezone.localdate()
    garantia.estado_garantia = EstadoGarantia.APPLIED if garantia.monto_aplicado > 0 else EstadoGarantia.RETURNED
    return garantia


@transaction.atomic
def apply_guarantee_movement(*, garantia, tipo_movimiento, monto_clp, fecha, justificacion='', movimiento_origen=None):
    amount = Decimal(monto_clp)
    if amount <= 0:
        raise ValueError('El monto del movimiento de garantia debe ser mayor que cero.')

    if tipo_movimiento == TipoMovimientoGarantia.DEPOSIT:
        if garantia.monto_recibido + amount > garantia.monto_pactado:
            raise ValueError('El deposito no puede exceder el monto pactado de la garantia.')
        garantia.monto_recibido += amount
        garantia.fecha_recepcion = garantia.fecha_recepcion or fecha
    elif tipo_movimiento == TipoMovimientoGarantia.PARTIAL_RETURN:
        if amount >= garantia.saldo_vigente:
            raise ValueError('Use devolucion_total cuando la devolucion cubra el saldo completo.')
        garantia.monto_devuelto += amount
    elif tipo_movimiento == TipoMovimientoGarantia.TOTAL_RETURN:
        if amount != garantia.saldo_vigente:
            raise ValueError('La devolucion total debe coincidir exactamente con el saldo vigente.')
        garantia.monto_devuelto += amount
    elif tipo_movimiento == TipoMovimientoGarantia.PARTIAL_RETENTION:
        if amount >= garantia.saldo_vigente:
            raise ValueError('Use retencion_total cuando la retencion cubra el saldo completo.')
        garantia.monto_aplicado += amount
    elif tipo_movimiento == TipoMovimientoGarantia.TOTAL_RETENTION:
        if amount != garantia.saldo_vigente:
            raise ValueError('La retencion total debe coincidir exactamente con el saldo vigente.')
        garantia.monto_aplicado += amount
    else:
        raise ValueError('Tipo de movimiento de garantia no soportado.')

    garantia.full_clean()
    recalculate_guarantee_state(garantia)
    garantia.full_clean()
    garantia.save()

    movimiento = HistorialGarantia.objects.create(
        garantia_contractual=garantia,
        tipo_movimiento=tipo_movimiento,
        monto_clp=amount,
        fecha=fecha,
        justificacion=justificacion,
        movimiento_origen=movimiento_origen,
    )
    return movimiento, garantia


RESIDUAL_REFERENCE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_residual_reference():
    while True:
        token = ''.join(secrets.choice(RESIDUAL_REFERENCE_ALPHABET) for _ in range(6))
        reference = f'CCR-{token}'
        if not CodigoCobroResidual.objects.filter(referencia_visible=reference).exists():
            return reference


def rebuild_account_state(arrendatario):
    open_payment_states = {
        EstadoPago.PENDING,
        EstadoPago.OVERDUE,
        EstadoPago.IN_REPAYMENT,
    }
    payments = PagoMensual.objects.filter(contrato__arrendatario=arrendatario)
    repactaciones = RepactacionDeuda.objects.filter(arrendatario=arrendatario)
    residuals = CodigoCobroResidual.objects.filter(arrendatario=arrendatario)

    pending_payments = payments.filter(estado_pago__in=open_payment_states)
    overdue_payments = payments.filter(estado_pago=EstadoPago.OVERDUE)
    active_repayments = repactaciones.filter(estado='activa')
    active_residuals = residuals.filter(estado='activa')

    total_payment_balance = sum(
        max(Decimal('0.00'), payment.monto_calculado_clp - payment.monto_pagado_clp)
        for payment in pending_payments
    )
    total_repayment_balance = sum(repactacion.saldo_pendiente for repactacion in active_repayments)
    total_residual_balance = sum(code.saldo_actual for code in active_residuals)

    summary = {
        'pagos_abiertos': pending_payments.count(),
        'pagos_atrasados': overdue_payments.count(),
        'repactaciones_activas': active_repayments.count(),
        'cobranzas_residuales_activas': active_residuals.count(),
        'saldo_pagos_clp': str(total_payment_balance),
        'saldo_repactaciones_clp': str(total_repayment_balance),
        'saldo_residual_clp': str(total_residual_balance),
        'saldo_total_clp': str(total_payment_balance + total_repayment_balance + total_residual_balance),
    }

    state, _ = EstadoCuentaArrendatario.objects.get_or_create(arrendatario=arrendatario)
    state.resumen_operativo = summary
    state.save(update_fields=['resumen_operativo', 'updated_at'])
    return state
