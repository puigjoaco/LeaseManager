import secrets
from datetime import date
from decimal import Decimal, ROUND_DOWN

from django.db import transaction
from django.utils import timezone
from audit.models import ManualResolution
from audit.services import create_audit_event
from contratos.models import MonedaBaseContrato
from core.reference_validation import is_non_sensitive_reference
from core.scope_access import ScopeAccess, scope_queryset_for_access

from .models import (
    AjusteContrato,
    CapacidadCobroExterno,
    CodigoCobroResidual,
    DistribucionCobroMensual,
    EstadoGarantia,
    EstadoGateCobroExterno,
    EstadoIntentoPagoWebPay,
    EstadoPago,
    EstadoCuentaArrendatario,
    EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
    GateCobroExterno,
    GarantiaContractual,
    HistorialGarantia,
    IntentoPagoWebPay,
    MANUAL_UF_LOAD_EVENT_TYPE,
    PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
    PagoMensual,
    RepactacionDeuda,
    TipoMovimientoGarantia,
    ValorUFDiario,
    WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
)


def get_operational_month_start(anio, mes):
    return date(int(anio), int(mes), 1)


def get_uf_value_for_month(anio, mes):
    month_start = get_operational_month_start(anio, mes)
    return get_uf_value_for_date(month_start).valor


def get_uf_value_for_date(effective_date):
    uf_value = ValorUFDiario.objects.filter(fecha=effective_date).first()
    if not uf_value:
        raise ValueError(f'No existe valor UF cargado para {effective_date.isoformat()}.')
    return uf_value


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


def calculate_effective_code_effect(amount_before_code, amount_after_code):
    return Decimal(amount_after_code) - Decimal(amount_before_code)


def calculate_monthly_amount(contrato, anio, mes):
    if contrato.blocks_automatic_past_billing(anio, mes):
        message = contrato.retroactive_manual_notification_alert()
        raise ValueError(
            message
            or 'Contrato retroactivo no permite reconstruir cobros pasados de forma automatica.'
        )

    period = get_period_for_month(contrato, anio, mes)
    if not period:
        raise ValueError('No existe un periodo contractual vigente para el mes operativo solicitado.')

    primary_property = get_primary_contract_property(contrato)
    if not primary_property:
        raise ValueError('El contrato no tiene una propiedad principal configurada.')

    due_date = date(int(anio), int(mes), contrato.dia_pago_mensual)
    uf_value = None
    base_amount = period.monto_base
    if period.moneda_base == 'UF':
        uf_value = get_uf_value_for_date(due_date)
        base_amount = base_amount * uf_value.valor

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
                uf_value = get_uf_value_for_date(due_date)
            adjustment_amount = adjustment_amount * uf_value.valor
        total_amount += adjustment_amount

    truncated = truncate_to_clp(total_amount)
    if truncated < Decimal('1000'):
        raise ValueError('El monto mensual calculado queda bajo el minimo operativo de CLP 1.000.')

    effective_code = primary_property.codigo_conciliacion_efectivo_snapshot
    final_amount = apply_effective_code(truncated, effective_code)
    effective_code_effect = calculate_effective_code_effect(truncated, final_amount)

    return {
        'periodo_contractual': period,
        'monto_facturable_clp': truncated,
        'monto_calculado_clp': final_amount,
        'monto_efecto_codigo_efectivo_clp': effective_code_effect,
        'moneda_calculo': MonedaBaseContrato.UF if uf_value else MonedaBaseContrato.CLP,
        'uf_fecha_usada': uf_value.fecha if uf_value else None,
        'uf_valor_usado': uf_value.valor if uf_value else None,
        'uf_source_key': uf_value.source_key if uf_value else '',
        'codigo_conciliacion_efectivo': effective_code,
        'fecha_vencimiento': due_date,
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
    effective_date = get_operational_month_start(payment.anio, payment.mes)

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
            mandato.propietario_comunidad_owner.participaciones_vigentes_en(effective_date)
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
    for item in distribution_items:
        item.full_clean()
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

EXCEPTIONAL_PAYMENT_STATES = {
    EstadoPago.PAID_BY_TERMINATION,
    EstadoPago.FORGIVEN,
}

PAYMENT_API_BLOCKED_CLOSED_STATES = {
    EstadoPago.PAID,
    EstadoPago.PAID_VIA_REPAYMENT,
}


def validate_payment_state_transition(previous_state, next_state):
    if next_state == previous_state:
        return
    allowed_states = PAYMENT_STATE_TRANSITIONS.get(previous_state, set())
    if next_state not in allowed_states:
        raise ValueError(f'Transicion invalida desde {previous_state} hacia {next_state}.')


def calculate_days_late(payment):
    reference_date = payment.fecha_deposito_banco or payment.fecha_pago_webpay or payment.fecha_deteccion_sistema
    if not reference_date and payment.estado_pago == EstadoPago.OVERDUE:
        reference_date = timezone.localdate()
    if not reference_date:
        return 0
    return max(0, (reference_date - payment.fecha_vencimiento).days)


def calculate_open_days_late(payment, reference_date=None):
    reference_date = reference_date or timezone.localdate()
    if not payment.fecha_vencimiento:
        return 0
    return max(0, (reference_date - payment.fecha_vencimiento).days)


def sync_payment_state(payment, reference_date=None):
    if payment.estado_pago == EstadoPago.IN_REPAYMENT:
        if not payment.dias_mora:
            payment.dias_mora = calculate_open_days_late(payment, reference_date)
        return payment
    if payment.estado_pago == EstadoPago.PAID_VIA_REPAYMENT:
        if not payment.dias_mora:
            payment.dias_mora = calculate_days_late(payment) or calculate_open_days_late(payment, reference_date)
        return payment
    if payment.estado_pago == EstadoPago.OVERDUE and not (
        payment.fecha_deposito_banco or payment.fecha_pago_webpay or payment.fecha_deteccion_sistema
    ):
        payment.dias_mora = calculate_open_days_late(payment, reference_date)
        return payment
    payment.dias_mora = calculate_days_late(payment)
    return payment


def create_exceptional_payment_state_event(
    payment,
    *,
    previous_state='',
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    if payment.estado_pago not in EXCEPTIONAL_PAYMENT_STATES:
        return None
    actor_identifier = (actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        raise ValueError('El cierre excepcional de pago requiere un actor trazable para auditoria.')
    return create_audit_event(
        event_type=EXCEPTIONAL_PAYMENT_STATE_EVENT_TYPE,
        entity_type='pago_mensual',
        entity_id=str(payment.pk),
        summary=f'Pago mensual cerrado excepcionalmente como {payment.estado_pago}',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={
            'contrato_id': payment.contrato_id,
            'previous_state': previous_state,
            'estado_pago': payment.estado_pago,
            'resolucion_pago_excepcional_ref': payment.resolucion_pago_excepcional_ref.strip(),
            'resolucion_pago_excepcional_motivo': payment.resolucion_pago_excepcional_motivo.strip(),
        },
    )


@transaction.atomic
def update_payment_operational_fields(
    *,
    payment,
    validated_data,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    next_state = validated_data.get('estado_pago', payment.estado_pago)
    previous_state = payment.estado_pago
    validate_payment_state_transition(previous_state, next_state)
    if next_state in PAYMENT_API_BLOCKED_CLOSED_STATES:
        raise ValueError(
            'Los pagos cerrados solo se registran desde conciliacion bancaria '
            'o desde el flujo especifico con artefacto de cierre.'
        )
    if next_state in EXCEPTIONAL_PAYMENT_STATES and actor_user is None and not (actor_identifier or '').strip():
        raise ValueError('El cierre excepcional de pago requiere un actor trazable para auditoria.')

    for field, value in validated_data.items():
        setattr(payment, field, value)

    sync_payment_state(payment)
    sync_payment_distribution(payment)
    payment.full_clean()
    payment.save(
        update_fields=[
            'monto_pagado_clp',
            'fecha_deposito_banco',
            'fecha_pago_webpay',
            'fecha_deteccion_sistema',
            'estado_pago',
            'repactacion_deuda',
            'resolucion_pago_excepcional_ref',
            'resolucion_pago_excepcional_motivo',
            'dias_mora',
            'updated_at',
        ]
    )

    exceptional_event = None
    if previous_state != payment.estado_pago:
        exceptional_event = create_exceptional_payment_state_event(
            payment,
            previous_state=previous_state or '',
            actor_user=actor_user,
            actor_identifier=actor_identifier,
            ip_address=ip_address,
        )
    return payment, previous_state, exceptional_event


def partial_repayment_exception_trace(repayment):
    if not isinstance(repayment, RepactacionDeuda) or not repayment.es_repactacion_parcial:
        return ''
    return '|'.join(
        [
            str(repayment.pk or ''),
            repayment.excepcion_parcial_ref.strip(),
            repayment.excepcion_parcial_motivo.strip(),
            str(repayment.monto_total_plan_clp),
            str(repayment.deuda_total_original),
        ]
    )


def create_partial_repayment_exception_event(
    repayment,
    *,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    if not repayment.es_repactacion_parcial:
        return None
    actor_identifier = (actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        raise ValueError('La repactacion parcial requiere un actor trazable para auditoria.')
    return create_audit_event(
        event_type=PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
        entity_type='repactacion_deuda',
        entity_id=str(repayment.pk),
        summary=f'Repactacion parcial autorizada para arrendatario {repayment.arrendatario_id}',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={
            'arrendatario_id': repayment.arrendatario_id,
            'contrato_id': repayment.contrato_origen_id,
            'deuda_total_original': str(repayment.deuda_total_original),
            'monto_total_plan_clp': str(repayment.monto_total_plan_clp),
            'excepcion_parcial_ref': repayment.excepcion_parcial_ref.strip(),
            'excepcion_parcial_motivo': repayment.excepcion_parcial_motivo.strip(),
        },
    )


@transaction.atomic
def save_repayment_plan(
    *,
    validated_data,
    repayment=None,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    repayment = repayment or RepactacionDeuda()
    previous_trace = partial_repayment_exception_trace(repayment)
    for field, value in validated_data.items():
        setattr(repayment, field, value)

    repayment.full_clean()
    current_trace = partial_repayment_exception_trace(repayment)
    if current_trace and current_trace != previous_trace and actor_user is None and not (actor_identifier or '').strip():
        raise ValueError('La repactacion parcial requiere un actor trazable para auditoria.')

    repayment.save()
    event = None
    if current_trace and current_trace != previous_trace:
        event = create_partial_repayment_exception_event(
            repayment,
            actor_user=actor_user,
            actor_identifier=actor_identifier,
            ip_address=ip_address,
        )
    return repayment, event


def manual_uf_trace(uf_value):
    if not isinstance(uf_value, ValorUFDiario) or not uf_value.requiere_auditoria_manual:
        return ''
    return '|'.join(
        [
            str(uf_value.pk or ''),
            str(uf_value.fecha or ''),
            str(uf_value.valor or ''),
            str(uf_value.source_key or '').strip(),
            str(uf_value.evidencia_ref or '').strip(),
            str(uf_value.motivo_carga or '').strip(),
            str(uf_value.responsable_ref or '').strip(),
        ]
    )


def create_manual_uf_load_event(
    uf_value,
    *,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    if not uf_value.requiere_auditoria_manual:
        return None
    actor_identifier = (actor_identifier or '').strip()
    if actor_user is None and not actor_identifier:
        raise ValueError('La carga manual UF requiere un actor trazable para auditoria.')
    return create_audit_event(
        event_type=MANUAL_UF_LOAD_EVENT_TYPE,
        entity_type='valor_uf_diario',
        entity_id=str(uf_value.pk),
        summary=f'Valor UF manual auditado para {uf_value.fecha.isoformat()}',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={
            'fecha': uf_value.fecha.isoformat(),
            'valor': str(uf_value.valor),
            'source_key': uf_value.source_key.strip(),
            'evidencia_ref': uf_value.evidencia_ref.strip(),
            'motivo_carga': uf_value.motivo_carga.strip(),
            'responsable_ref': uf_value.responsable_ref.strip(),
        },
    )


@transaction.atomic
def save_uf_value(
    *,
    validated_data,
    uf_value=None,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    uf_value = uf_value or ValorUFDiario()
    previous_trace = manual_uf_trace(uf_value)
    for field, value in validated_data.items():
        setattr(uf_value, field, value)

    uf_value.full_clean()
    if uf_value.requiere_auditoria_manual and actor_user is None and not (actor_identifier or '').strip():
        raise ValueError('La carga manual UF requiere un actor trazable para auditoria.')

    uf_value.save()
    current_trace = manual_uf_trace(uf_value)
    event = None
    if current_trace and current_trace != previous_trace:
        event = create_manual_uf_load_event(
            uf_value,
            actor_user=actor_user,
            actor_identifier=actor_identifier,
            ip_address=ip_address,
        )
    return uf_value, event


def sync_payment_overdue_state(payment, reference_date=None):
    if payment.estado_pago not in {EstadoPago.PENDING, EstadoPago.OVERDUE}:
        return sync_payment_state(payment, reference_date)

    days_late = calculate_open_days_late(payment, reference_date)
    if days_late > 0:
        payment.estado_pago = EstadoPago.OVERDUE
        payment.dias_mora = days_late
    elif payment.estado_pago == EstadoPago.PENDING:
        payment.dias_mora = 0
    return payment


def _payment_effective_paid_date(payment):
    return payment.fecha_deposito_banco or payment.fecha_pago_webpay or payment.fecha_deteccion_sistema


def _payment_required_amount_for_score(payment):
    required = Decimal(str(payment.monto_calculado_clp or Decimal('0.00')))
    if payment.repactacion_deuda_id:
        required += Decimal(str(payment.repactacion_deuda.monto_cuota or Decimal('0.00')))
    return required


def _payment_has_operational_record_for_score(payment):
    contrato = getattr(payment, 'contrato', None)
    if not contrato:
        return True
    return not contrato.blocks_automatic_past_billing(payment.anio, payment.mes)


def _payment_is_evaluated_for_score(payment, reference_date):
    if payment.estado_pago != EstadoPago.PENDING:
        return True
    return bool(payment.fecha_vencimiento and payment.fecha_vencimiento <= reference_date)


def _payment_is_on_time_for_score(payment):
    paid_states = {
        EstadoPago.PAID,
        EstadoPago.PAID_VIA_REPAYMENT,
        EstadoPago.PAID_BY_TERMINATION,
    }
    if payment.estado_pago not in paid_states:
        return False
    paid_date = _payment_effective_paid_date(payment)
    if not paid_date or not payment.fecha_vencimiento or paid_date > payment.fecha_vencimiento:
        return False
    return Decimal(str(payment.monto_pagado_clp or Decimal('0.00'))) >= _payment_required_amount_for_score(payment)


def calculate_payment_score(payments, reference_date=None):
    reference_date = reference_date or timezone.localdate()
    evaluated = 0
    on_time = 0
    without_operational_record = 0
    for payment in payments:
        if not _payment_has_operational_record_for_score(payment):
            without_operational_record += 1
            continue
        if not _payment_is_evaluated_for_score(payment, reference_date):
            continue
        evaluated += 1
        if _payment_is_on_time_for_score(payment):
            on_time += 1

    late_or_unpaid = max(0, evaluated - on_time)
    score = None
    if evaluated:
        score = int(
            (Decimal(on_time) * Decimal('100') / Decimal(evaluated)).quantize(Decimal('1'))
        )
    return {
        'score_pago_porcentaje': score,
        'score_meses_evaluados': evaluated,
        'score_pagos_en_plazo': on_time,
        'score_pagos_fuera_plazo': late_or_unpaid,
        'score_meses_sin_registro_operativo': without_operational_record,
    }


@transaction.atomic
def refresh_overdue_payments(*, queryset=None, reference_date=None, access: ScopeAccess | None = None):
    reference_date = reference_date or timezone.localdate()
    queryset = queryset or PagoMensual.objects.all()
    candidates = queryset.select_related('contrato__arrendatario').filter(
        estado_pago__in=[EstadoPago.PENDING, EstadoPago.OVERDUE],
        fecha_vencimiento__lt=reference_date,
    )

    updated_count = 0
    tenant_ids: set[int] = set()
    tenants = {}
    for payment in candidates.select_for_update():
        previous_state = payment.estado_pago
        previous_days = payment.dias_mora
        sync_payment_overdue_state(payment, reference_date)
        if payment.estado_pago == previous_state and payment.dias_mora == previous_days:
            continue
        payment.full_clean()
        payment.save(update_fields=['estado_pago', 'dias_mora', 'updated_at'])
        updated_count += 1
        tenant = payment.contrato.arrendatario
        tenant_ids.add(tenant.id)
        tenants[tenant.id] = tenant

    for tenant_id in sorted(tenant_ids):
        rebuild_account_state(tenants[tenant_id], access=access)

    return {
        'reference_date': reference_date.isoformat(),
        'updated_count': updated_count,
        'tenant_count': len(tenant_ids),
    }


def recalculate_guarantee_state(garantia, fecha_cierre=None):
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

    garantia.fecha_cierre = garantia.fecha_cierre or fecha_cierre or timezone.localdate()
    garantia.estado_garantia = EstadoGarantia.APPLIED if garantia.monto_aplicado > 0 else EstadoGarantia.RETURNED
    return garantia


@transaction.atomic
def apply_guarantee_movement(
    *,
    garantia,
    tipo_movimiento,
    monto_clp,
    fecha,
    justificacion='',
    movimiento_origen=None,
    resolucion_exceso_garantia='',
    resolucion_exceso_garantia_ref='',
    resolucion_exceso_garantia_motivo='',
):
    amount = Decimal(monto_clp)
    if amount <= 0:
        raise ValueError('El monto del movimiento de garantia debe ser mayor que cero.')
    if movimiento_origen and fecha < movimiento_origen.fecha:
        raise ValueError('La fecha del movimiento derivado no puede ser anterior al movimiento origen.')

    if tipo_movimiento == TipoMovimientoGarantia.DEPOSIT:
        garantia.monto_recibido += amount
        garantia.fecha_recepcion = garantia.fecha_recepcion or fecha
        if garantia.monto_recibido > garantia.monto_pactado:
            garantia.resolucion_exceso_garantia = resolucion_exceso_garantia
            garantia.resolucion_exceso_garantia_ref = resolucion_exceso_garantia_ref
            garantia.resolucion_exceso_garantia_motivo = resolucion_exceso_garantia_motivo
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

    recalculate_guarantee_state(garantia, fecha_cierre=fecha)
    garantia.full_clean()
    garantia.save()

    movimiento = HistorialGarantia(
        garantia_contractual=garantia,
        tipo_movimiento=tipo_movimiento,
        monto_clp=amount,
        fecha=fecha,
        justificacion=justificacion,
        movimiento_origen=movimiento_origen,
    )
    movimiento.full_clean()
    movimiento.save()
    return movimiento, garantia


RESIDUAL_REFERENCE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_residual_reference():
    while True:
        token = ''.join(secrets.choice(RESIDUAL_REFERENCE_ALPHABET) for _ in range(6))
        reference = f'CCR-{token}'
        if not CodigoCobroResidual.objects.filter(referencia_visible=reference).exists():
            return reference


WEBPAY_REFERENCE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_webpay_buy_order(payment):
    while True:
        token = ''.join(secrets.choice(WEBPAY_REFERENCE_ALPHABET) for _ in range(8))
        buy_order = f'LM-PM-{payment.pk}-{token}'
        if not IntentoPagoWebPay.objects.filter(buy_order=buy_order).exists():
            return buy_order


def get_or_create_webpay_gate(provider_key='transbank_webpay'):
    gate, _ = GateCobroExterno.objects.get_or_create(
        capacidad_key=CapacidadCobroExterno.WEBPAY_INTENT,
        provider_key=provider_key,
    )
    return gate


def ensure_manual_resolution_for_webpay_intent(intent, summary):
    existing = ManualResolution.objects.filter(
        category='cobranza.webpay.bloqueado',
        scope_type='cobranza.webpay',
        scope_reference=str(intent.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).first()
    if existing:
        return existing
    return ManualResolution.objects.create(
        category='cobranza.webpay.bloqueado',
        scope_type='cobranza.webpay',
        scope_reference=str(intent.pk),
        summary=summary,
        metadata={
            'intent_id': intent.pk,
            'pago_mensual_id': intent.pago_mensual_id,
            'gate_cobro_id': intent.gate_cobro_id,
            'provider_key': intent.provider_key,
        },
    )


def webpay_blocking_reason(payment, gate, return_url_ref):
    if gate.estado_gate != EstadoGateCobroExterno.OPEN:
        return 'El gate WebPay no esta abierto para preparar cobros externos.'
    if not is_non_sensitive_reference(gate.evidencia_ref):
        return 'El gate WebPay requiere evidencia_ref no sensible antes de operar.'
    if payment.estado_pago not in {EstadoPago.PENDING, EstadoPago.OVERDUE}:
        return 'Solo se puede preparar WebPay para pagos pendientes o atrasados.'
    pending_amount = Decimal(payment.monto_calculado_clp) - Decimal(payment.monto_pagado_clp)
    if pending_amount <= 0:
        return 'El pago no tiene saldo pendiente para WebPay.'
    if not return_url_ref.strip():
        return 'WebPay requiere una referencia de retorno no sensible.'
    return ''


@transaction.atomic
def prepare_webpay_intent(*, payment, gate=None, provider_key='transbank_webpay', return_url_ref='', usuario=None):
    provider_key = provider_key.strip()
    gate = gate or get_or_create_webpay_gate(provider_key=provider_key or 'transbank_webpay')
    provider_key = provider_key or gate.provider_key
    if gate.provider_key != provider_key:
        raise ValueError('El gate WebPay debe pertenecer al mismo provider_key solicitado.')
    if gate.capacidad_key != CapacidadCobroExterno.WEBPAY_INTENT:
        raise ValueError('El gate debe corresponder a WebPay.IntentoPago.')
    return_url_ref = return_url_ref.strip()
    if return_url_ref and not is_non_sensitive_reference(return_url_ref):
        raise ValueError('WebPay requiere return_url_ref no sensible; no use URLs, tokens, credenciales ni correos.')
    pending_amount = Decimal(payment.monto_calculado_clp) - Decimal(payment.monto_pagado_clp)
    blocking_reason = webpay_blocking_reason(payment, gate, return_url_ref)
    if not blocking_reason:
        existing = IntentoPagoWebPay.objects.filter(
            pago_mensual=payment,
            estado=EstadoIntentoPagoWebPay.PREPARED,
        ).first()
        if existing:
            return existing

    intent = IntentoPagoWebPay(
        pago_mensual=payment,
        gate_cobro=gate,
        provider_key=provider_key,
        monto_clp_snapshot=max(pending_amount, Decimal('0.00')),
        return_url_ref=return_url_ref,
        usuario=usuario,
    )

    if blocking_reason:
        intent.estado = EstadoIntentoPagoWebPay.BLOCKED
        intent.motivo_bloqueo = blocking_reason
        intent.full_clean()
        intent.save()
        ensure_manual_resolution_for_webpay_intent(intent, blocking_reason)
        return intent

    intent.estado = EstadoIntentoPagoWebPay.PREPARED
    intent.buy_order = generate_webpay_buy_order(payment)
    intent.session_id = f'LM-WP-{payment.pk}-{timezone.now().strftime("%Y%m%d%H%M%S%f")}'
    intent.full_clean()
    intent.save()
    return intent


@transaction.atomic
def confirm_webpay_intent_manually(
    *,
    intent,
    external_ref,
    fecha_pago_webpay,
    actor_user=None,
    actor_identifier='',
    ip_address=None,
):
    external_ref = external_ref.strip()
    actor_identifier = (actor_identifier or '').strip()
    if intent.estado != EstadoIntentoPagoWebPay.PREPARED:
        raise ValueError('Solo se puede confirmar manualmente un intento WebPay preparado.')
    if not external_ref:
        raise ValueError('La confirmacion WebPay requiere transaction id o token externo trazable.')
    if not is_non_sensitive_reference(external_ref):
        raise ValueError(
            'La confirmacion WebPay requiere external_ref no sensible; no use URLs, tokens, credenciales ni correos.'
        )
    if not fecha_pago_webpay:
        raise ValueError('La confirmacion WebPay requiere fecha de pago WebPay.')
    if actor_user is None and not actor_identifier:
        raise ValueError('La confirmacion WebPay manual requiere un actor trazable para auditoria.')

    payment = PagoMensual.objects.select_for_update().get(pk=intent.pago_mensual_id)
    gate = GateCobroExterno.objects.select_for_update().get(pk=intent.gate_cobro_id)
    blocking_reason = webpay_blocking_reason(payment, gate, intent.return_url_ref)
    if blocking_reason:
        raise ValueError(blocking_reason)

    pending_amount = Decimal(payment.monto_calculado_clp) - Decimal(payment.monto_pagado_clp)
    payment.monto_pagado_clp = Decimal(payment.monto_pagado_clp) + pending_amount
    payment.fecha_pago_webpay = fecha_pago_webpay
    payment.fecha_deteccion_sistema = payment.fecha_deteccion_sistema or timezone.localdate()
    payment.estado_pago = EstadoPago.PAID
    sync_payment_state(payment)
    payment.full_clean()
    payment.save(
        update_fields=[
            'monto_pagado_clp',
            'fecha_pago_webpay',
            'fecha_deteccion_sistema',
            'estado_pago',
            'dias_mora',
            'updated_at',
        ]
    )
    sync_payment_distribution(payment)

    intent.pago_mensual = payment
    intent.gate_cobro = gate
    intent.estado = EstadoIntentoPagoWebPay.CONFIRMED_MANUAL
    intent.external_ref = external_ref
    intent.fecha_pago_webpay = fecha_pago_webpay
    intent.confirmado_at = timezone.now()
    if actor_user is not None:
        intent.usuario = actor_user
    intent.full_clean()
    intent.save(
        update_fields=[
            'estado',
            'external_ref',
            'fecha_pago_webpay',
            'confirmado_at',
            'usuario',
            'updated_at',
        ]
    )
    create_audit_event(
        event_type=WEBPAY_MANUAL_CONFIRM_EVENT_TYPE,
        entity_type='webpay_intento',
        entity_id=str(intent.pk),
        summary='Confirmacion WebPay manual controlada registrada',
        actor_user=actor_user,
        actor_identifier=actor_identifier,
        ip_address=ip_address,
        metadata={
            'external_ref': external_ref,
            'pago_mensual_id': payment.pk,
            'fecha_pago_webpay': str(intent.fecha_pago_webpay),
        },
    )
    return intent, payment


def build_account_state_summary(arrendatario, access: ScopeAccess | None = None, reference_date=None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    reference_date = reference_date or timezone.localdate()
    open_payment_states = {
        EstadoPago.PENDING,
        EstadoPago.OVERDUE,
        EstadoPago.IN_REPAYMENT,
    }
    payments = scope_queryset_for_access(
        PagoMensual.objects.select_related('contrato', 'repactacion_deuda').filter(contrato__arrendatario=arrendatario),
        access,
        property_paths=('contrato__mandato_operacion__propiedad_id',),
    )
    repactaciones = scope_queryset_for_access(
        RepactacionDeuda.objects.filter(arrendatario=arrendatario),
        access,
        property_paths=('contrato_origen__mandato_operacion__propiedad_id',),
    )
    residuals = scope_queryset_for_access(
        CodigoCobroResidual.objects.filter(arrendatario=arrendatario),
        access,
        property_paths=('contrato_origen__mandato_operacion__propiedad_id',),
    )

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
    score = calculate_payment_score(payments, reference_date)

    return {
        'pagos_abiertos': pending_payments.count(),
        'pagos_atrasados': overdue_payments.count(),
        'repactaciones_activas': active_repayments.count(),
        'cobranzas_residuales_activas': active_residuals.count(),
        'saldo_pagos_clp': str(total_payment_balance),
        'saldo_repactaciones_clp': str(total_repayment_balance),
        'saldo_residual_clp': str(total_residual_balance),
        'saldo_total_clp': str(total_payment_balance + total_repayment_balance + total_residual_balance),
        **score,
    }


def rebuild_account_state(arrendatario, *, access: ScopeAccess | None = None, persist: bool | None = None, reference_date=None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    if persist is None:
        persist = not access.restricted

    summary = build_account_state_summary(arrendatario, access, reference_date=reference_date)
    state, _ = EstadoCuentaArrendatario.objects.get_or_create(arrendatario=arrendatario)
    state.resumen_operativo = summary
    state.score_pago = summary['score_pago_porcentaje']
    if persist:
        state.save(update_fields=['resumen_operativo', 'score_pago', 'updated_at'])
    return state
