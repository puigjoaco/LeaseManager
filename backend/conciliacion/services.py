import re

from django.db import transaction
from django.utils import timezone

from audit.models import ManualResolution
from cobranza.models import CodigoCobroResidual, EstadoCobroResidual, EstadoPago, PagoMensual
from cobranza.services import sync_payment_distribution, sync_payment_state
from core.reference_validation import is_non_sensitive_reference

from .models import (
    CategoriaMovimiento,
    EstadoConciliacionMovimiento,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    TipoMovimientoBancario,
    TransferenciaIntercuenta,
)


RETRIABLE_EXACT_MATCH_STATES = {
    EstadoConciliacionMovimiento.PENDING,
    EstadoConciliacionMovimiento.UNKNOWN_INCOME,
}
ECONOMIC_PERIOD_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


def require_manual_resolution_rationale(rationale):
    clean_rationale = str(rationale or '').strip()
    if not clean_rationale:
        raise ValueError('La resolucion manual requiere un motivo auditable.')
    return clean_rationale


def require_economic_period(periodo_economico):
    clean_period = str(periodo_economico or '').strip()
    if not ECONOMIC_PERIOD_RE.fullmatch(clean_period):
        raise ValueError('periodo_economico debe usar formato YYYY-MM.')
    return clean_period


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


def supersede_manual_resolutions_for_movement(
    movimiento,
    *,
    superseded_by,
    rationale,
    match_type='',
    target_metadata=None,
    exclude_resolution=None,
    actor_user=None,
    ip_address=None,
):
    resolutions = ManualResolution.objects.filter(
        scope_type='movimiento_bancario',
        scope_reference=str(movimiento.pk),
        status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW],
    )
    if exclude_resolution is not None:
        resolutions = resolutions.exclude(pk=exclude_resolution.pk)

    resolutions = list(resolutions)
    if not resolutions:
        return 0

    from audit.services import create_audit_event

    resolved_at = timezone.now()
    target_metadata = target_metadata or {}
    for resolution in resolutions:
        supersede_context = {
            'superseded_by': superseded_by,
            'superseded_match_type': match_type,
            'movimiento_id': movimiento.pk,
            'conexion_bancaria_id': movimiento.conexion_bancaria_id,
            'cuenta_recaudadora_id': movimiento.conexion_bancaria.cuenta_recaudadora_id,
            **target_metadata,
        }
        resolution.status = ManualResolution.Status.SUPERSEDED
        resolution.resolved_at = resolved_at
        resolution.resolved_by = actor_user
        resolution.rationale = str(rationale or '').strip()
        resolution.metadata = {
            **(resolution.metadata or {}),
            **supersede_context,
        }
        resolution.save(update_fields=['status', 'resolved_at', 'resolved_by', 'rationale', 'metadata'])

        create_audit_event(
            event_type='audit.manual_resolution.superseded',
            entity_type='manual_resolution',
            entity_id=str(resolution.pk),
            summary='Se cerro una resolucion manual por supersesion auditable de conciliacion.',
            actor_user=actor_user,
            actor_identifier='' if actor_user else 'system.conciliacion',
            ip_address=ip_address,
            metadata={
                'resolution_category': resolution.category,
                **supersede_context,
            },
        )
    return len(resolutions)


def resolve_unknown_income_if_present(movimiento):
    if hasattr(movimiento, 'ingreso_desconocido'):
        movimiento.ingreso_desconocido.estado = EstadoIngresoDesconocido.RESOLVED
        movimiento.ingreso_desconocido.save(update_fields=['estado', 'updated_at'])


def ensure_movement_can_attempt_exact_match(movimiento):
    if movimiento.estado_conciliacion in RETRIABLE_EXACT_MATCH_STATES:
        if movimiento.pago_mensual_id or movimiento.codigo_cobro_residual_id:
            raise ValueError('El movimiento ya mantiene una referencia de conciliacion y no admite reintento.')
        return

    if movimiento.estado_conciliacion == EstadoConciliacionMovimiento.MANUAL_REQUIRED:
        raise ValueError('El movimiento requiere clasificacion manual y no admite reintento automatico.')
    raise ValueError('El movimiento ya fue conciliado y no admite reintento.')


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
    ensure_movement_can_attempt_exact_match(movimiento)

    if movimiento.tipo_movimiento == TipoMovimientoBancario.DEBIT:
        movimiento.estado_conciliacion = EstadoConciliacionMovimiento.MANUAL_REQUIRED
        movimiento.save(update_fields=['estado_conciliacion', 'updated_at'])
        resolution = ensure_manual_resolution_for_movement(
            movimiento,
            'conciliacion.movimiento_cargo',
            'Movimiento de cargo requiere clasificacion manual.',
        )
        resolution.metadata = {
            **(resolution.metadata or {}),
            'cuenta_recaudadora_id': movimiento.conexion_bancaria.cuenta_recaudadora_id,
            'cuenta_owner_tipo': movimiento.conexion_bancaria.cuenta_recaudadora.owner_tipo,
            'cuenta_owner_display': movimiento.conexion_bancaria.cuenta_recaudadora.owner_display,
            'empresa_owner_id': movimiento.conexion_bancaria.cuenta_recaudadora.empresa_owner_id,
        }
        resolution.save(update_fields=['metadata'])
        return {'status': 'manual_required', 'resolution_id': str(resolution.pk)}

    if movimiento.referencia:
        residual_matches = list(
            CodigoCobroResidual.objects.filter(
                contrato_origen__mandato_operacion__cuenta_recaudadora=movimiento.conexion_bancaria.cuenta_recaudadora,
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
            movimiento.full_clean()
            movimiento.save(
                update_fields=['codigo_cobro_residual', 'pago_mensual', 'estado_conciliacion', 'updated_at']
            )
            resolve_unknown_income_if_present(movimiento)
            supersede_manual_resolutions_for_movement(
                movimiento,
                superseded_by='conciliacion.exact_match',
                match_type='residual_collection',
                rationale='Supersedida porque el movimiento obtuvo match exacto con codigo residual trazable.',
                target_metadata={
                    'codigo_cobro_residual_id': residual.pk,
                    'contrato_id': residual.contrato_origen_id,
                },
            )
            return {'status': 'matched_residual', 'codigo_cobro_residual_id': residual.pk}

    payment_matches = list(
        PagoMensual.objects.filter(
            contrato__mandato_operacion__cuenta_recaudadora=movimiento.conexion_bancaria.cuenta_recaudadora,
            anio=movimiento.fecha_movimiento.year,
            mes=movimiento.fecha_movimiento.month,
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
        sync_payment_distribution(payment)
        movimiento.pago_mensual = payment
        movimiento.codigo_cobro_residual = None
        movimiento.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
        movimiento.full_clean()
        movimiento.save(
            update_fields=['pago_mensual', 'codigo_cobro_residual', 'estado_conciliacion', 'updated_at']
        )
        resolve_unknown_income_if_present(movimiento)
        supersede_manual_resolutions_for_movement(
            movimiento,
            superseded_by='conciliacion.exact_match',
            match_type='payment',
            rationale='Supersedida porque el movimiento obtuvo match exacto con pago mensual trazable.',
            target_metadata={
                'pago_mensual_id': payment.pk,
                'contrato_id': payment.contrato_id,
            },
        )
        from contabilidad.services import create_payment_reconciled_event

        create_payment_reconciled_event(payment, movimiento)
        return {'status': 'matched_payment', 'pago_mensual_id': payment.pk}

    suggestion = {'payment_candidate_ids': [payment.pk for payment in payment_matches]}
    unknown = handle_unknown_income(movimiento, suggestion=suggestion)
    return {'status': 'unknown_income', 'ingreso_desconocido_id': unknown.pk}


@transaction.atomic
def resolve_unknown_income_manual_resolution(
    *,
    resolution,
    payment,
    periodo_economico,
    criterio_aplicado,
    evidencia_regularizacion_ref,
    rationale='',
    actor_user=None,
    ip_address=None,
):
    if resolution.category != 'conciliacion.ingreso_desconocido':
        raise ValueError('La resolucion indicada no corresponde a ingreso desconocido de conciliacion.')
    if resolution.status == ManualResolution.Status.RESOLVED:
        raise ValueError('La resolucion ya fue marcada como resuelta.')
    rationale = require_manual_resolution_rationale(rationale)
    periodo_economico = require_economic_period(periodo_economico)
    criterio_aplicado = str(criterio_aplicado or '').strip()
    evidencia_regularizacion_ref = str(evidencia_regularizacion_ref or '').strip()
    if not criterio_aplicado:
        raise ValueError('La regularizacion manual requiere criterio aplicado.')
    if not is_non_sensitive_reference(evidencia_regularizacion_ref):
        raise ValueError('La regularizacion manual requiere evidencia no sensible.')

    movimiento = MovimientoBancarioImportado.objects.select_related('conexion_bancaria').get(pk=resolution.scope_reference)
    if movimiento.tipo_movimiento != TipoMovimientoBancario.CREDIT:
        raise ValueError('Solo se puede regularizar manualmente un abono bancario.')
    if movimiento.estado_conciliacion != EstadoConciliacionMovimiento.UNKNOWN_INCOME:
        raise ValueError('El movimiento ya no se encuentra en estado de ingreso desconocido.')

    if payment.contrato.mandato_operacion.cuenta_recaudadora_id != movimiento.conexion_bancaria.cuenta_recaudadora_id:
        raise ValueError('El pago seleccionado no pertenece a la misma cuenta recaudadora del movimiento.')
    expected_period = f'{payment.anio:04d}-{payment.mes:02d}'
    if periodo_economico != expected_period:
        raise ValueError('El periodo economico debe coincidir con el mes y anio del pago mensual seleccionado.')
    if payment.estado_pago not in {EstadoPago.PENDING, EstadoPago.OVERDUE}:
        raise ValueError('Solo se puede regularizar manualmente un pago pendiente o atrasado.')
    pending_amount = payment.monto_calculado_clp - payment.monto_pagado_clp
    if pending_amount <= 0:
        raise ValueError('El pago seleccionado ya no tiene saldo pendiente por regularizar.')
    if movimiento.monto != pending_amount:
        raise ValueError(
            'El monto del movimiento debe coincidir exactamente con el saldo pendiente del pago seleccionado.'
        )

    resolution_context = {
        'periodo_economico': periodo_economico,
        'criterio_aplicado': criterio_aplicado,
        'evidencia_regularizacion_ref': evidencia_regularizacion_ref,
    }

    payment.monto_pagado_clp = payment.monto_pagado_clp + movimiento.monto
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
    movimiento.full_clean()
    movimiento.save(update_fields=['pago_mensual', 'codigo_cobro_residual', 'estado_conciliacion', 'updated_at'])

    resolve_unknown_income_if_present(movimiento)
    from contabilidad.services import create_payment_reconciled_event

    create_payment_reconciled_event(payment, movimiento)

    resolved_at = timezone.now()
    supersede_manual_resolutions_for_movement(
        movimiento,
        superseded_by='conciliacion.manual_resolution',
        match_type='payment_manual_assignment',
        rationale='Supersedida porque otra resolucion manual cerro el ingreso desconocido.',
        target_metadata={
            'superseded_by_resolution_id': str(resolution.pk),
            'pago_mensual_id': payment.pk,
            'contrato_id': payment.contrato_id,
        },
        exclude_resolution=resolution,
        actor_user=actor_user,
        ip_address=ip_address,
    )

    resolution.status = ManualResolution.Status.RESOLVED
    resolution.resolved_at = resolved_at
    resolution.resolved_by = actor_user
    resolution.rationale = rationale
    resolution.metadata = {
        **(resolution.metadata or {}),
        'resolved_payment_id': payment.pk,
        'resolved_contract_id': payment.contrato_id,
        'resolved_with': 'payment_manual_assignment',
        **resolution_context,
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
            **resolution_context,
        },
    )

    return {'resolution': resolution, 'movimiento': movimiento, 'payment': payment}


@transaction.atomic
def resolve_charge_movement_manual_resolution(
    *,
    resolution,
    categoria_movimiento,
    entidad_afectada_tipo,
    entidad_afectada_id,
    periodo_economico,
    criterio_reparto,
    evidencia_clasificacion_ref,
    rationale='',
    actor_user=None,
    ip_address=None,
):
    if resolution.category != 'conciliacion.movimiento_cargo':
        raise ValueError('La resolucion indicada no corresponde a movimiento cargo de conciliacion.')
    if resolution.status == ManualResolution.Status.RESOLVED:
        raise ValueError('La resolucion ya fue marcada como resuelta.')
    rationale = require_manual_resolution_rationale(rationale)
    categoria_movimiento = str(categoria_movimiento or '').strip()
    entidad_afectada_tipo = str(entidad_afectada_tipo or '').strip()
    periodo_economico = require_economic_period(periodo_economico)
    criterio_reparto = str(criterio_reparto or '').strip()
    evidencia_clasificacion_ref = str(evidencia_clasificacion_ref or '').strip()

    movimiento = MovimientoBancarioImportado.objects.select_related(
        'conexion_bancaria__cuenta_recaudadora__empresa_owner',
        'conexion_bancaria__cuenta_recaudadora__socio_owner',
    ).get(pk=resolution.scope_reference)
    if movimiento.tipo_movimiento != TipoMovimientoBancario.DEBIT:
        raise ValueError('Solo se puede clasificar manualmente un cargo bancario.')
    if movimiento.estado_conciliacion != EstadoConciliacionMovimiento.MANUAL_REQUIRED:
        raise ValueError('El movimiento ya no se encuentra pendiente de clasificacion manual.')

    empresa = movimiento.conexion_bancaria.cuenta_recaudadora.empresa_owner
    if empresa is None:
        raise ValueError('La cuenta recaudadora del cargo no pertenece a una empresa contable.')
    if categoria_movimiento != CategoriaMovimiento.BANK_COMMISSION:
        raise ValueError('La categoria de movimiento indicada aun no tiene flujo de cierre seguro.')
    if entidad_afectada_tipo != 'empresa':
        raise ValueError('La entidad afectada indicada no es soportada para este cierre.')
    try:
        entidad_afectada_id = int(entidad_afectada_id)
    except (TypeError, ValueError) as error:
        raise ValueError('La clasificacion manual requiere entidad afectada.') from error
    if entidad_afectada_id != empresa.pk:
        raise ValueError('La entidad afectada debe coincidir con la empresa duena de la cuenta recaudadora.')
    if not criterio_reparto:
        raise ValueError('La clasificacion manual requiere criterio de reparto.')
    if not is_non_sensitive_reference(evidencia_clasificacion_ref):
        raise ValueError('La clasificacion manual requiere evidencia no sensible.')

    classification_context = {
        'categoria_movimiento': categoria_movimiento,
        'entidad_afectada_tipo': entidad_afectada_tipo,
        'entidad_afectada_id': entidad_afectada_id,
        'cuenta_recaudadora_id': movimiento.conexion_bancaria.cuenta_recaudadora_id,
        'fecha_movimiento': movimiento.fecha_movimiento.isoformat(),
        'periodo_economico': periodo_economico,
        'criterio_reparto': criterio_reparto,
        'evidencia_clasificacion_ref': evidencia_clasificacion_ref,
    }

    from contabilidad.services import create_accounting_event

    event, _ = create_accounting_event(
        empresa=empresa,
        evento_tipo='ComisionBancaria',
        entidad_origen_tipo='movimiento_bancario',
        entidad_origen_id=movimiento.pk,
        fecha_operativa=movimiento.fecha_movimiento,
        moneda='CLP',
        monto_base=movimiento.monto,
        payload_resumen={
            'movimiento_bancario_id': movimiento.pk,
            'cuenta_recaudadora_id': movimiento.conexion_bancaria.cuenta_recaudadora_id,
            'descripcion_origen': movimiento.descripcion_origen,
            **classification_context,
        },
        idempotency_key=f'ComisionBancaria:{movimiento.pk}',
    )

    movimiento.notas_admin = rationale
    movimiento.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
    movimiento.full_clean()
    movimiento.save(update_fields=['notas_admin', 'estado_conciliacion', 'updated_at'])

    resolved_at = timezone.now()
    supersede_manual_resolutions_for_movement(
        movimiento,
        superseded_by='conciliacion.manual_resolution',
        match_type='charge_manual_classification',
        rationale='Supersedida porque otra resolucion manual clasifico el cargo bancario.',
        target_metadata={
            'superseded_by_resolution_id': str(resolution.pk),
            'evento_contable_id': event.pk,
            'empresa_id': empresa.pk,
        },
        exclude_resolution=resolution,
        actor_user=actor_user,
        ip_address=ip_address,
    )

    resolution.status = ManualResolution.Status.RESOLVED
    resolution.resolved_at = resolved_at
    resolution.resolved_by = actor_user
    resolution.rationale = rationale
    resolution.metadata = {
        **(resolution.metadata or {}),
        'resolved_event_id': event.pk,
        'resolved_empresa_id': empresa.pk,
        'resolved_with': 'charge_manual_classification',
        **classification_context,
    }
    resolution.save(update_fields=['status', 'resolved_at', 'resolved_by', 'rationale', 'metadata'])

    from audit.services import create_audit_event

    create_audit_event(
        event_type='audit.manual_resolution.resolved',
        entity_type='manual_resolution',
        entity_id=str(resolution.pk),
        summary='Se clasifico manualmente un cargo bancario en conciliacion.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'resolution_category': resolution.category,
            'movimiento_bancario_id': movimiento.pk,
            'evento_contable_id': event.pk,
            'empresa_id': empresa.pk,
            **classification_context,
        },
    )

    return {'resolution': resolution, 'movimiento': movimiento, 'event': event, 'empresa': empresa}


@transaction.atomic
def resolve_internal_transfer_manual_resolution(
    *,
    resolution,
    movimiento_destino,
    periodo_economico,
    criterio_conciliacion,
    evidencia_transferencia_ref,
    responsable_ref,
    rationale='',
    actor_user=None,
    ip_address=None,
):
    if resolution.category != 'conciliacion.movimiento_cargo':
        raise ValueError('La resolucion indicada no corresponde a movimiento cargo de conciliacion.')
    if resolution.status == ManualResolution.Status.RESOLVED:
        raise ValueError('La resolucion ya fue marcada como resuelta.')

    rationale = require_manual_resolution_rationale(rationale)
    periodo_economico = require_economic_period(periodo_economico)
    criterio_conciliacion = str(criterio_conciliacion or '').strip()
    evidencia_transferencia_ref = str(evidencia_transferencia_ref or '').strip()
    responsable_ref = str(responsable_ref or '').strip()

    if not criterio_conciliacion:
        raise ValueError('La transferencia interna requiere criterio de conciliacion.')
    if not is_non_sensitive_reference(evidencia_transferencia_ref):
        raise ValueError('La transferencia interna requiere evidencia no sensible.')
    if not is_non_sensitive_reference(responsable_ref):
        raise ValueError('La transferencia interna requiere responsable_ref no sensible.')

    movimiento_origen = MovimientoBancarioImportado.objects.select_related(
        'conexion_bancaria__cuenta_recaudadora',
    ).get(pk=resolution.scope_reference)
    movimiento_destino = MovimientoBancarioImportado.objects.select_related(
        'conexion_bancaria__cuenta_recaudadora',
    ).get(pk=movimiento_destino.pk)

    if movimiento_origen.tipo_movimiento != TipoMovimientoBancario.DEBIT:
        raise ValueError('Solo se puede cerrar como transferencia interna un cargo bancario.')
    if movimiento_origen.estado_conciliacion != EstadoConciliacionMovimiento.MANUAL_REQUIRED:
        raise ValueError('El movimiento origen no se encuentra pendiente de clasificacion manual.')
    if movimiento_destino.tipo_movimiento != TipoMovimientoBancario.CREDIT:
        raise ValueError('El movimiento destino de transferencia debe ser un abono bancario.')
    if movimiento_destino.estado_conciliacion not in {
        EstadoConciliacionMovimiento.PENDING,
        EstadoConciliacionMovimiento.UNKNOWN_INCOME,
    }:
        raise ValueError('El movimiento destino debe estar pendiente o como ingreso desconocido.')
    if movimiento_destino.pago_mensual_id or movimiento_destino.codigo_cobro_residual_id:
        raise ValueError('El movimiento destino de transferencia no puede tener target de cobro.')
    if movimiento_origen.conexion_bancaria.cuenta_recaudadora_id == movimiento_destino.conexion_bancaria.cuenta_recaudadora_id:
        raise ValueError('La transferencia interna requiere cuentas recaudadoras distintas.')
    if movimiento_origen.monto != movimiento_destino.monto:
        raise ValueError('El cargo y el abono de transferencia deben tener el mismo monto.')

    transfer = TransferenciaIntercuenta(
        movimiento_origen=movimiento_origen,
        movimiento_destino=movimiento_destino,
        periodo_economico=periodo_economico,
        criterio_conciliacion=criterio_conciliacion,
        evidencia_transferencia_ref=evidencia_transferencia_ref,
        responsable_ref=responsable_ref,
        rationale=rationale,
    )
    transfer.full_clean()
    transfer.save()

    from contabilidad.services import create_internal_transfer_events

    accounting_events = create_internal_transfer_events(transfer)

    movimiento_origen.notas_admin = rationale
    movimiento_origen.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
    movimiento_origen.full_clean()
    movimiento_origen.save(update_fields=['notas_admin', 'estado_conciliacion', 'updated_at'])

    movimiento_destino.estado_conciliacion = EstadoConciliacionMovimiento.EXACT_MATCH
    movimiento_destino.full_clean()
    movimiento_destino.save(update_fields=['estado_conciliacion', 'updated_at'])
    resolve_unknown_income_if_present(movimiento_destino)

    transfer_metadata = {
        'transferencia_intercuenta_id': transfer.pk,
        'movimiento_origen_id': movimiento_origen.pk,
        'movimiento_destino_id': movimiento_destino.pk,
        'entidad_origen_tipo': transfer.entidad_origen_tipo,
        'entidad_origen_id': transfer.entidad_origen_id,
        'entidad_destino_tipo': transfer.entidad_destino_tipo,
        'entidad_destino_id': transfer.entidad_destino_id,
        'periodo_economico': periodo_economico,
        'criterio_conciliacion': criterio_conciliacion,
        'criterio_reparto': criterio_conciliacion,
        'evidencia_transferencia_ref': evidencia_transferencia_ref,
        'responsable_ref': responsable_ref,
        'evento_contable_ids': [event.pk for event in accounting_events],
        'empresa_evento_ids': [event.empresa_id for event in accounting_events if event.empresa_id],
    }

    supersede_manual_resolutions_for_movement(
        movimiento_origen,
        superseded_by='conciliacion.manual_resolution',
        match_type='internal_transfer',
        rationale='Supersedida porque otra resolucion manual registro la transferencia interna.',
        target_metadata={
            'superseded_by_resolution_id': str(resolution.pk),
            **transfer_metadata,
        },
        exclude_resolution=resolution,
        actor_user=actor_user,
        ip_address=ip_address,
    )
    supersede_manual_resolutions_for_movement(
        movimiento_destino,
        superseded_by='conciliacion.manual_resolution',
        match_type='internal_transfer',
        rationale='Supersedida porque el abono destino quedo vinculado a transferencia interna trazada.',
        target_metadata={
            'superseded_by_resolution_id': str(resolution.pk),
            **transfer_metadata,
        },
        actor_user=actor_user,
        ip_address=ip_address,
    )

    resolved_at = timezone.now()
    resolution.status = ManualResolution.Status.RESOLVED
    resolution.resolved_at = resolved_at
    resolution.resolved_by = actor_user
    resolution.rationale = rationale
    resolution.metadata = {
        **(resolution.metadata or {}),
        'categoria_movimiento': CategoriaMovimiento.INTERNAL_TRANSFER,
        'resolved_with': 'internal_transfer',
        **transfer_metadata,
    }
    resolution.save(update_fields=['status', 'resolved_at', 'resolved_by', 'rationale', 'metadata'])

    from audit.services import create_audit_event

    create_audit_event(
        event_type='audit.manual_resolution.resolved',
        entity_type='manual_resolution',
        entity_id=str(resolution.pk),
        summary='Se registro manualmente una transferencia interna de conciliacion.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata={
            'resolution_category': resolution.category,
            'categoria_movimiento': CategoriaMovimiento.INTERNAL_TRANSFER,
            **transfer_metadata,
        },
    )

    return {
        'resolution': resolution,
        'transferencia': transfer,
        'eventos_contables': accounting_events,
        'movimiento_origen': movimiento_origen,
        'movimiento_destino': movimiento_destino,
    }
