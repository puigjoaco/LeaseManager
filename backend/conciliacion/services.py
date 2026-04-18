from django.db import transaction
from django.utils import timezone

from audit.models import ManualResolution
from cobranza.models import CodigoCobroResidual, EstadoCobroResidual, EstadoPago, PagoMensual
from cobranza.services import sync_payment_distribution, sync_payment_state

from .models import (
    EstadoConciliacionMovimiento,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    TipoMovimientoBancario,
)


def get_open_manual_resolution(movimiento, category):
    return ManualResolution.objects.filter(
        category=category,
        scope_type='movimiento_bancario',
        scope_reference=str(movimiento.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).first()


def ensure_manual_resolution_for_movement(movimiento, category, summary):
    existing = get_open_manual_resolution(movimiento, category)
    if existing:
        return existing
    return ManualResolution.objects.create(
        category=category,
        scope_type='movimiento_bancario',
        scope_reference=str(movimiento.pk),
        summary=summary,
        metadata={
            'movimiento_id': movimiento.pk,
            'conexion_bancaria_id': movimiento.conexion_bancaria_id,
        },
    )


def close_manual_resolutions_for_movement(movimiento):
    ManualResolution.objects.filter(
        scope_type='movimiento_bancario',
        scope_reference=str(movimiento.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).update(status=ManualResolution.Status.RESOLVED, resolved_at=timezone.now())


def resolve_unknown_income_if_present(movimiento):
    if hasattr(movimiento, 'ingreso_desconocido'):
        movimiento.ingreso_desconocido.estado = EstadoIngresoDesconocido.RESOLVED
        movimiento.ingreso_desconocido.save(update_fields=['estado', 'updated_at'])


@transaction.atomic
def handle_unknown_income(movimiento, suggestion=None):
    unknown, _ = IngresoDesconocido.objects.update_or_create(
        movimiento_bancario=movimiento,
        defaults={
            'cuenta_recaudadora': movimiento.conexion_bancaria.cuenta_recaudadora,
            'monto': movimiento.monto,
            'fecha_movimiento': movimiento.fecha_movimiento,
            'descripcion_origen': movimiento.descripcion_origen,
            'estado': EstadoIngresoDesconocido.OPEN,
            'sugerencia_asistida': suggestion or {},
        },
    )
    movimiento.estado_conciliacion = EstadoConciliacionMovimiento.UNKNOWN_INCOME
    movimiento.pago_mensual = None
    movimiento.codigo_cobro_residual = None
    movimiento.save(update_fields=['estado_conciliacion', 'pago_mensual', 'codigo_cobro_residual', 'updated_at'])
    resolution = ensure_manual_resolution_for_movement(
        movimiento,
        'conciliacion.ingreso_desconocido',
        'Ingreso sin match exacto requiere clasificacion manual.',
    )
    resolution.metadata = {
        **(resolution.metadata or {}),
        'unknown_income_id': unknown.pk,
        'payment_candidate_ids': (suggestion or {}).get('payment_candidate_ids', []),
    }
    resolution.save(update_fields=['metadata'])
    return unknown


@transaction.atomic
def reconcile_exact_movement(movimiento):
    if movimiento.tipo_movimiento == TipoMovimientoBancario.DEBIT:
        movimiento.estado_conciliacion = EstadoConciliacionMovimiento.MANUAL_REQUIRED
        movimiento.save(update_fields=['estado_conciliacion', 'updated_at'])
        resolution = ensure_manual_resolution_for_movement(
            movimiento,
            'conciliacion.movimiento_cargo',
            'Movimiento de cargo requiere clasificacion manual.',
        )
        return {'status': 'manual_required', 'resolution_id': str(resolution.pk)}

    if movimiento.referencia:
        residual_matches = list(
            CodigoCobroResidual.objects.filter(
                referencia_visible=movimiento.referencia,
                saldo_actual=movimiento.monto,
                estado=EstadoCobroResidual.ACTIVE,
            )
        )
        if len(residual_matches) == 1:
            residual = residual_matches[0]
            residual.estado = EstadoCobroResidual.PAID
            residual.saldo_actual = 0
            residual.save(update_fields=['estado', 'saldo_actual', 'updated_at'])
            movimiento.codigo_cobro_residual = residual
            movimiento.pago_mensual = None
            movimiento.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
            movimiento.save(
                update_fields=['codigo_cobro_residual', 'pago_mensual', 'estado_conciliacion', 'updated_at']
            )
            resolve_unknown_income_if_present(movimiento)
            close_manual_resolutions_for_movement(movimiento)
            return {'status': 'matched_residual', 'codigo_cobro_residual_id': residual.pk}

    payment_matches = list(
        PagoMensual.objects.filter(
            contrato__mandato_operacion__cuenta_recaudadora=movimiento.conexion_bancaria.cuenta_recaudadora,
            monto_calculado_clp=movimiento.monto,
            estado_pago__in=[EstadoPago.PENDING, EstadoPago.OVERDUE],
        ).select_related('contrato')
    )
    if len(payment_matches) == 1:
        payment = payment_matches[0]
        payment.monto_pagado_clp = movimiento.monto
        payment.fecha_deposito_banco = movimiento.fecha_movimiento
        payment.fecha_deteccion_sistema = timezone.localdate()
        payment.estado_pago = EstadoPago.PAID
        sync_payment_state(payment)
        payment.save(
            update_fields=[
                'monto_pagado_clp',
                'fecha_deposito_banco',
                'fecha_deteccion_sistema',
                'estado_pago',
                'dias_mora',
                'updated_at',
            ]
        )
        from cobranza.services import sync_payment_distribution

        sync_payment_distribution(payment)
        movimiento.pago_mensual = payment
        movimiento.codigo_cobro_residual = None
        movimiento.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
        movimiento.save(
            update_fields=['pago_mensual', 'codigo_cobro_residual', 'estado_conciliacion', 'updated_at']
        )
        resolve_unknown_income_if_present(movimiento)
        close_manual_resolutions_for_movement(movimiento)
        from contabilidad.services import create_payment_reconciled_event

        create_payment_reconciled_event(payment, movimiento)
        return {'status': 'matched_payment', 'pago_mensual_id': payment.pk}

    suggestion = {'payment_candidate_ids': [payment.pk for payment in payment_matches]}
    unknown = handle_unknown_income(movimiento, suggestion=suggestion)
    return {'status': 'unknown_income', 'ingreso_desconocido_id': unknown.pk}


@transaction.atomic
def resolve_unknown_income_manual_resolution(*, resolution, payment, rationale='', actor_user=None, ip_address=None):
    if resolution.category != 'conciliacion.ingreso_desconocido':
        raise ValueError('La resolucion indicada no corresponde a ingreso desconocido de conciliacion.')
    if resolution.status == ManualResolution.Status.RESOLVED:
        raise ValueError('La resolucion ya fue marcada como resuelta.')

    movimiento = MovimientoBancarioImportado.objects.select_related('conexion_bancaria').get(pk=resolution.scope_reference)
    if movimiento.tipo_movimiento != TipoMovimientoBancario.CREDIT:
        raise ValueError('Solo se puede regularizar manualmente un abono bancario.')
    if movimiento.estado_conciliacion != EstadoConciliacionMovimiento.UNKNOWN_INCOME:
        raise ValueError('El movimiento ya no se encuentra en estado de ingreso desconocido.')

    if payment.contrato.mandato_operacion.cuenta_recaudadora_id != movimiento.conexion_bancaria.cuenta_recaudadora_id:
        raise ValueError('El pago seleccionado no pertenece a la misma cuenta recaudadora del movimiento.')
    if payment.estado_pago not in {EstadoPago.PENDING, EstadoPago.OVERDUE}:
        raise ValueError('Solo se puede regularizar manualmente un pago pendiente o atrasado.')

    payment.monto_pagado_clp = movimiento.monto
    payment.fecha_deposito_banco = movimiento.fecha_movimiento
    payment.fecha_deteccion_sistema = timezone.localdate()
    payment.estado_pago = EstadoPago.PAID
    sync_payment_state(payment)
    payment.save(
        update_fields=[
            'monto_pagado_clp',
            'fecha_deposito_banco',
            'fecha_deteccion_sistema',
            'estado_pago',
            'dias_mora',
            'updated_at',
        ]
    )
    sync_payment_distribution(payment)

    movimiento.pago_mensual = payment
    movimiento.codigo_cobro_residual = None
    movimiento.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
    movimiento.save(update_fields=['pago_mensual', 'codigo_cobro_residual', 'estado_conciliacion', 'updated_at'])

    resolve_unknown_income_if_present(movimiento)
    from contabilidad.services import create_payment_reconciled_event

    create_payment_reconciled_event(payment, movimiento)

    resolved_at = timezone.now()
    ManualResolution.objects.filter(
        scope_type='movimiento_bancario',
        scope_reference=str(movimiento.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    ).exclude(pk=resolution.pk).update(status=ManualResolution.Status.RESOLVED, resolved_at=resolved_at)

    resolution.status = ManualResolution.Status.RESOLVED
    resolution.resolved_at = resolved_at
    resolution.resolved_by = actor_user
    resolution.rationale = rationale
    resolution.metadata = {
        **(resolution.metadata or {}),
        'resolved_payment_id': payment.pk,
        'resolved_contract_id': payment.contrato_id,
        'resolved_with': 'payment_manual_assignment',
    }
    resolution.save(update_fields=['status', 'resolved_at', 'resolved_by', 'rationale', 'metadata'])

    from audit.services import create_audit_event

    create_audit_event(
        event_type='audit.manual_resolution.resolved',
        entity_type='manual_resolution',
        entity_id=str(resolution.pk),
        summary='Se regularizo manualmente un ingreso desconocido de conciliacion.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'resolution_category': resolution.category,
            'movimiento_bancario_id': movimiento.pk,
            'pago_mensual_id': payment.pk,
            'contrato_id': payment.contrato_id,
        },
    )

    return {'resolution': resolution, 'movimiento': movimiento, 'payment': payment}
