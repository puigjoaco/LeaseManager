import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from audit.services import create_audit_event
from core.reference_validation import is_non_sensitive_reference

from .models import (
    AUTOMATIC_RENEWAL_EVENT_TYPE,
    AUTOMATIC_RENEWAL_ORIGIN,
    AvisoTermino,
    Contrato,
    EstadoAvisoTermino,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RENEWAL_PERIOD_KIND,
)


def _last_day_of_month(value):
    return calendar.monthrange(value.year, value.month)[1]


def _validate_month_end(field_name, value):
    if value.day != _last_day_of_month(value):
        raise ValidationError({field_name: 'La renovacion automatica debe terminar el ultimo dia del mes.'})


def _validate_amount(moneda_base, monto_base):
    if moneda_base == MonedaBaseContrato.CLP and monto_base < Decimal('1000.00'):
        raise ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
    if moneda_base == MonedaBaseContrato.UF and monto_base <= Decimal('0.00'):
        raise ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})


def _validate_renewal_base_policy(*, base_changed, policy_ref, policy_reason):
    if not base_changed:
        return
    if not policy_ref or not policy_reason:
        raise ValidationError(
            {
                'politica_base_renovacion_ref': (
                    'Una renovacion con base distinta al ultimo tramo vigente requiere politica documentada.'
                )
            }
        )
    if not is_non_sensitive_reference(policy_ref):
        raise ValidationError(
            {
                'politica_base_renovacion_ref': (
                    'La politica de base de renovacion debe usar una referencia no sensible.'
                )
            }
        )


@transaction.atomic
def execute_automatic_contract_renewal(
    *,
    contract,
    fecha_fin,
    monto_base=None,
    moneda_base='',
    politica_base_renovacion_ref='',
    politica_base_renovacion_motivo='',
    actor_user=None,
    ip_address=None,
):
    contract = (
        Contrato.objects.select_for_update()
        .select_related('mandato_operacion', 'arrendatario', 'politica_documental')
        .get(pk=contract.pk)
    )
    if contract.estado != EstadoContrato.ACTIVE:
        raise ValidationError({'estado': 'Solo un contrato vigente puede renovarse automaticamente.'})

    if AvisoTermino.objects.filter(
        contrato=contract,
        estado=EstadoAvisoTermino.REGISTERED,
    ).exists():
        raise ValidationError({'aviso_termino': 'Un AvisoTermino registrado bloquea la renovacion automatica.'})

    previous_period = contract.periodos_contractuales.order_by('-fecha_fin', '-numero_periodo').first()
    if previous_period is None:
        raise ValidationError({'periodos_contractuales': 'La renovacion automatica requiere un tramo vigente base.'})
    if previous_period.fecha_fin != contract.fecha_fin_vigente:
        raise ValidationError(
            {
                'periodos_contractuales': (
                    'La renovacion automatica requiere que el ultimo tramo cubra la fecha fin vigente.'
                )
            }
        )

    renewal_start = contract.fecha_fin_vigente + timedelta(days=1)
    if renewal_start.day != 1:
        raise ValidationError(
            {'fecha_inicio': 'La renovacion automatica debe iniciar el primer dia del mes siguiente.'}
        )
    if fecha_fin < renewal_start:
        raise ValidationError({'fecha_fin': 'La fecha fin de renovacion no puede ser anterior al inicio renovado.'})
    _validate_month_end('fecha_fin', fecha_fin)

    renewal_amount = Decimal(monto_base) if monto_base is not None else previous_period.monto_base
    renewal_currency = moneda_base or previous_period.moneda_base
    _validate_amount(renewal_currency, renewal_amount)

    policy_ref = str(politica_base_renovacion_ref or '').strip()
    policy_reason = str(politica_base_renovacion_motivo or '').strip()
    base_changed = (
        renewal_currency != previous_period.moneda_base
        or Decimal(renewal_amount) != Decimal(previous_period.monto_base)
    )
    _validate_renewal_base_policy(
        base_changed=base_changed,
        policy_ref=policy_ref,
        policy_reason=policy_reason,
    )

    previous_contract_end = contract.fecha_fin_vigente
    next_period_number = previous_period.numero_periodo + 1
    contract.fecha_fin_vigente = fecha_fin
    contract.tiene_tramos = True
    contract.full_clean()
    contract.save(update_fields=['fecha_fin_vigente', 'tiene_tramos', 'updated_at'])

    renewal_period = PeriodoContractual(
        contrato=contract,
        numero_periodo=next_period_number,
        fecha_inicio=renewal_start,
        fecha_fin=fecha_fin,
        monto_base=renewal_amount,
        moneda_base=renewal_currency,
        tipo_periodo=RENEWAL_PERIOD_KIND,
        origen_periodo=AUTOMATIC_RENEWAL_ORIGIN,
        politica_base_renovacion_ref=policy_ref,
        politica_base_renovacion_motivo=policy_reason,
    )
    renewal_period.full_clean()
    renewal_period.save()

    create_audit_event(
        event_type=AUTOMATIC_RENEWAL_EVENT_TYPE,
        entity_type='periodo_contractual',
        entity_id=str(renewal_period.pk),
        summary='Se ejecuto renovacion automatica de contrato por PeriodoContractual.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'contrato_id': contract.pk,
            'codigo_contrato': contract.codigo_contrato,
            'periodo_contractual_id': renewal_period.pk,
            'numero_periodo': renewal_period.numero_periodo,
            'fecha_fin_anterior': previous_contract_end.isoformat(),
            'fecha_inicio_renovacion': renewal_start.isoformat(),
            'fecha_fin_renovacion': fecha_fin.isoformat(),
            'base_modificada': base_changed,
            'politica_base_renovacion_ref': policy_ref,
        },
    )
    return renewal_period
