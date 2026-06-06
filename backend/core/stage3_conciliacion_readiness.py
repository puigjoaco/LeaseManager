from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import F, Q
from django.utils import timezone

from audit.models import AuditEvent, ManualResolution
from cobranza.models import PagoMensual
from conciliacion.models import (
    CategoriaMovimiento,
    ConexionBancaria,
    CuadraturaBancaria,
    EstadoCuadraturaBancaria,
    EstadoConciliacionMovimiento,
    EstadoConexionBancaria,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    OrigenImportacionMovimiento,
    TipoMovimientoBancario,
    TransferenciaIntercuenta,
    bank_provider_sync_blocking_reason,
    has_text,
)
from contabilidad.models import EventoContable
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from core.state_transition_audit_readiness import count_state_changed_events_without_transition_metadata


AUTHORIZED_STAGE3_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
STAGE3_STATE_CHANGE_EVENT_PREFIXES = ('conciliacion',)
CONNECTION_REFERENCE_FIELDS = (
    'credencial_ref',
    'evidencia_gate_ref',
    'prueba_conectividad_ref',
    'prueba_movimientos_ref',
    'prueba_saldos_ref',
)
MOVEMENT_REFERENCE_FIELDS = ('evidencia_importacion_ref', 'referencia', 'transaction_id_banco')
BALANCE_SQUARE_REFERENCE_FIELDS = ('evidencia_cuadratura_ref', 'responsable_ref', 'rationale')
TRANSFER_REFERENCE_FIELDS = (
    'criterio_conciliacion',
    'evidencia_transferencia_ref',
    'responsable_ref',
    'rationale',
)
STAGE3_MANUAL_RESOLUTION_CATEGORIES = (
    'conciliacion.ingreso_desconocido',
    'conciliacion.movimiento_cargo',
)
MOVEMENT_MATCH_AUDIT_EVENT_TYPES = (
    'conciliacion.movimiento_bancario.match_attempted',
    'conciliacion.movimiento_bancario.match_retried',
)
CHARGE_MANUAL_CLASSIFICATION_REQUIRED_METADATA_FIELDS = (
    'categoria_movimiento',
    'entidad_afectada_tipo',
    'entidad_afectada_id',
    'periodo_economico',
    'criterio_reparto',
    'evidencia_clasificacion_ref',
    'resolved_with',
    'resolved_event_id',
    'resolved_empresa_id',
)
INTERNAL_TRANSFER_REQUIRED_METADATA_FIELDS = (
    'transferencia_intercuenta_id',
    'movimiento_origen_id',
    'movimiento_destino_id',
    'entidad_origen_tipo',
    'entidad_origen_id',
    'entidad_destino_tipo',
    'entidad_destino_id',
    'periodo_economico',
    'criterio_conciliacion',
    'evidencia_transferencia_ref',
    'responsable_ref',
    'resolved_with',
    'evento_contable_ids',
    'empresa_evento_ids',
)
UNKNOWN_INCOME_MANUAL_RESOLUTION_REQUIRED_METADATA_FIELDS = (
    'resolved_payment_id',
    'resolved_contract_id',
    'periodo_economico',
    'criterio_aplicado',
    'evidencia_regularizacion_ref',
)
SUPERSEDED_MANUAL_RESOLUTION_REQUIRED_METADATA_FIELDS = (
    'superseded_by',
    'movimiento_id',
)
ALLOWED_MANUAL_RESOLUTION_SUPERSEDERS = {
    'conciliacion.exact_match',
    'conciliacion.manual_resolution',
}
SUPERSEDED_MANUAL_RESOLUTION_EVENT_TYPE = 'audit.manual_resolution.superseded'
ECONOMIC_PERIOD_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


def _non_sensitive_reference(value: str) -> bool:
    return is_non_sensitive_reference(value)


def _sensitive_reference(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and not _non_sensitive_reference(normalized)


def _contains_sensitive(value) -> bool:
    return has_text(value) and contains_sensitive_reference(value)


def _valid_economic_period(value) -> bool:
    return ECONOMIC_PERIOD_RE.fullmatch(str(value or '').strip()) is not None


def _period_from_date(value) -> str:
    if not all(hasattr(value, attribute) for attribute in ('year', 'month', 'day')):
        return ''
    return f'{value.year:04d}-{value.month:02d}'


def _metadata_int(metadata: dict[str, Any], key: str) -> int | None:
    try:
        return int(str(metadata.get(key) or '').strip())
    except (TypeError, ValueError):
        return None


def _metadata_int_set(metadata: dict[str, Any], key: str) -> set[int] | None:
    raw_value = metadata.get(key)
    if raw_value is None:
        return None
    if isinstance(raw_value, (list, tuple, set)):
        values = raw_value
    else:
        values = [value.strip() for value in str(raw_value).split(',')]

    result: set[int] = set()
    for value in values:
        if not has_text(value):
            continue
        try:
            result.add(int(str(value).strip()))
        except (TypeError, ValueError):
            return None
    return result


def _metadata_text(metadata: dict[str, Any], key: str) -> str:
    return str(metadata.get(key) or '').strip()


def _expected_payment_period(payment: PagoMensual) -> str:
    return f'{payment.anio:04d}-{payment.mes:02d}'


def _get_resolution_movement(resolution: ManualResolution) -> MovimientoBancarioImportado | None:
    try:
        movement_id = int(str(resolution.scope_reference or '').strip())
    except (TypeError, ValueError):
        return None
    try:
        return MovimientoBancarioImportado.objects.select_related(
            'conexion_bancaria__cuenta_recaudadora',
            'pago_mensual',
        ).get(pk=movement_id)
    except MovimientoBancarioImportado.DoesNotExist:
        return None


def _unknown_income_target_matches(resolution: ManualResolution, metadata: dict[str, Any]) -> bool:
    payment_id = _metadata_int(metadata, 'resolved_payment_id')
    contract_id = _metadata_int(metadata, 'resolved_contract_id')
    if payment_id is None or contract_id is None:
        return False
    try:
        payment = PagoMensual.objects.select_related('contrato__mandato_operacion').get(pk=payment_id)
    except PagoMensual.DoesNotExist:
        return False

    if payment.contrato_id != contract_id:
        return False
    if str(metadata.get('periodo_economico') or '').strip() != _expected_payment_period(payment):
        return False

    movement = _get_resolution_movement(resolution)
    if movement is None:
        return False
    if movement.tipo_movimiento != TipoMovimientoBancario.CREDIT:
        return False
    if movement.estado_conciliacion != EstadoConciliacionMovimiento.EXACT_MATCH:
        return False
    if movement.pago_mensual_id != payment.pk:
        return False
    return (
        payment.contrato.mandato_operacion.cuenta_recaudadora_id
        == movement.conexion_bancaria.cuenta_recaudadora_id
    )


def _has_resolved_payment_manual_assignment(movement: MovimientoBancarioImportado) -> bool:
    if not movement.pk or not movement.pago_mensual_id:
        return False

    resolutions = ManualResolution.objects.filter(
        category='conciliacion.ingreso_desconocido',
        scope_type='movimiento_bancario',
        scope_reference=str(movement.pk),
        status=ManualResolution.Status.RESOLVED,
    )
    for resolution in resolutions:
        metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
        if metadata.get('resolved_with') != 'payment_manual_assignment':
            continue
        if _metadata_int(metadata, 'resolved_payment_id') != movement.pago_mensual_id:
            continue
        if _unknown_income_target_matches(resolution, metadata):
            return True
    return False


def _charge_classification_target_matches(resolution: ManualResolution, metadata: dict[str, Any]) -> bool:
    if metadata.get('resolved_with') != 'charge_manual_classification':
        return False
    movement = _get_resolution_movement(resolution)
    if movement is None:
        return False
    if movement.tipo_movimiento != TipoMovimientoBancario.DEBIT:
        return False
    if movement.estado_conciliacion != EstadoConciliacionMovimiento.EXACT_MATCH:
        return False
    if str(metadata.get('periodo_economico') or '').strip() != _period_from_date(movement.fecha_movimiento):
        return False

    empresa_id = movement.conexion_bancaria.cuenta_recaudadora.empresa_owner_id
    if empresa_id is None:
        return False
    if _metadata_int(metadata, 'entidad_afectada_id') != empresa_id:
        return False

    resolved_empresa_id = _metadata_int(metadata, 'resolved_empresa_id')
    if resolved_empresa_id != empresa_id:
        return False
    resolved_event_id = _metadata_int(metadata, 'resolved_event_id')
    if resolved_event_id is None:
        return False
    try:
        event = EventoContable.objects.get(pk=resolved_event_id)
    except EventoContable.DoesNotExist:
        return False
    if event.empresa_id != empresa_id:
        return False
    if event.evento_tipo != 'ComisionBancaria':
        return False
    if event.entidad_origen_tipo != 'movimiento_bancario':
        return False
    if str(event.entidad_origen_id) != str(movement.pk):
        return False
    if event.fecha_operativa != movement.fecha_movimiento:
        return False
    if event.moneda != 'CLP':
        return False
    if Decimal(event.monto_base) != Decimal(movement.monto):
        return False
    return True


def _internal_transfer_target_matches(resolution: ManualResolution, metadata: dict[str, Any]) -> bool:
    if metadata.get('resolved_with') != 'internal_transfer':
        return False
    movement = _get_resolution_movement(resolution)
    if movement is None:
        return False
    transfer_id = _metadata_int(metadata, 'transferencia_intercuenta_id')
    if transfer_id is None:
        return False
    try:
        transfer = TransferenciaIntercuenta.objects.select_related(
            'movimiento_origen__conexion_bancaria__cuenta_recaudadora',
            'movimiento_destino__conexion_bancaria__cuenta_recaudadora',
        ).get(pk=transfer_id)
    except TransferenciaIntercuenta.DoesNotExist:
        return False

    if transfer.movimiento_origen_id != movement.pk:
        return False
    if _metadata_int(metadata, 'movimiento_origen_id') != transfer.movimiento_origen_id:
        return False
    if _metadata_int(metadata, 'movimiento_destino_id') != transfer.movimiento_destino_id:
        return False
    if metadata.get('entidad_origen_tipo') != transfer.entidad_origen_tipo:
        return False
    if _metadata_int(metadata, 'entidad_origen_id') != transfer.entidad_origen_id:
        return False
    if metadata.get('entidad_destino_tipo') != transfer.entidad_destino_tipo:
        return False
    if _metadata_int(metadata, 'entidad_destino_id') != transfer.entidad_destino_id:
        return False
    if _metadata_text(metadata, 'periodo_economico') != transfer.periodo_economico:
        return False
    if _metadata_text(metadata, 'criterio_conciliacion') != transfer.criterio_conciliacion:
        return False
    if _metadata_text(metadata, 'evidencia_transferencia_ref') != transfer.evidencia_transferencia_ref:
        return False
    if _metadata_text(metadata, 'responsable_ref') != transfer.responsable_ref:
        return False
    try:
        transfer.full_clean()
    except ValidationError:
        return False

    event_ids = _metadata_int_set(metadata, 'evento_contable_ids')
    company_ids = _metadata_int_set(metadata, 'empresa_evento_ids')
    if event_ids is None or company_ids is None:
        return False

    expected_specs = []
    origin = transfer.movimiento_origen
    destination = transfer.movimiento_destino
    origin_account = origin.conexion_bancaria.cuenta_recaudadora
    destination_account = destination.conexion_bancaria.cuenta_recaudadora
    if origin_account.empresa_owner_id:
        expected_specs.append((
            'TransferenciaIntercuentaSalida',
            origin_account.empresa_owner_id,
            origin.fecha_movimiento,
            origin.monto,
        ))
    if destination_account.empresa_owner_id:
        expected_specs.append((
            'TransferenciaIntercuentaEntrada',
            destination_account.empresa_owner_id,
            destination.fecha_movimiento,
            destination.monto,
        ))

    expected_events = []
    for event_type, company_id, event_date, amount in expected_specs:
        event = EventoContable.objects.filter(
            pk__in=event_ids,
            empresa_id=company_id,
            evento_tipo=event_type,
            entidad_origen_tipo='transferencia_intercuenta',
            entidad_origen_id=str(transfer.pk),
            fecha_operativa=event_date,
            moneda='CLP',
            monto_base=amount,
        ).first()
        if event is None:
            return False
        expected_events.append(event)

    if {event.pk for event in expected_events} != event_ids:
        return False
    if {event.empresa_id for event in expected_events if event.empresa_id} != company_ids:
        return False
    return True


def _superseded_audit_event_matches_resolution(
    resolution: ManualResolution,
    metadata: dict[str, Any],
    audit_events_by_resolution: dict[str, list[AuditEvent]],
) -> bool:
    resolution_id = str(resolution.pk)
    expected_movement_id = str(metadata.get('movimiento_id') or '').strip()
    expected_superseder = str(metadata.get('superseded_by') or '').strip()
    expected_match_type = str(metadata.get('superseded_match_type') or '').strip()
    for event in audit_events_by_resolution.get(resolution_id, []):
        event_metadata = event.metadata if isinstance(event.metadata, dict) else {}
        event_movement_id = str(event_metadata.get('movimiento_id') or '').strip()
        event_superseder = str(event_metadata.get('superseded_by') or '').strip()
        event_match_type = str(event_metadata.get('superseded_match_type') or '').strip()
        if event_metadata.get('resolution_category') != resolution.category:
            continue
        if event_movement_id != expected_movement_id:
            continue
        if event_superseder != expected_superseder:
            continue
        if expected_match_type and event_match_type != expected_match_type:
            continue
        if not (event.actor_user_id or has_text(event.actor_identifier)):
            continue
        return True
    return False


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


def _count_by(queryset, field_name: str) -> dict[str, int]:
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _has_sensitive_reference(instance, field_names) -> bool:
    return any(
        has_text(getattr(instance, field_name, '')) and not _non_sensitive_reference(getattr(instance, field_name, ''))
        for field_name in field_names
    )


def _balance_connection_ready(connection: ConexionBancaria) -> bool:
    if not connection.primaria_saldos:
        return False
    if connection.estado_conexion != EstadoConexionBancaria.ACTIVE:
        return False
    if not has_text(connection.prueba_saldos_ref):
        return False
    try:
        connection.full_clean()
    except ValidationError:
        return False
    return True


def _collect_movement_issues(
    movements,
    *,
    internal_transfer_destination_ids=None,
    resolved_charge_movement_ids=None,
    match_audit_events_by_movement=None,
) -> dict[str, int]:
    counts = Counter()
    transaction_keys = Counter()
    internal_transfer_destination_ids = internal_transfer_destination_ids or set()
    resolved_charge_movement_ids = resolved_charge_movement_ids or set()
    match_audit_events_by_movement = match_audit_events_by_movement or {}
    for movement in movements:
        try:
            movement.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        if has_text(movement.transaction_id_banco):
            transaction_keys[(movement.conexion_bancaria_id, movement.transaction_id_banco)] += 1

        if _has_sensitive_reference(movement, MOVEMENT_REFERENCE_FIELDS):
            counts['sensitive_reference'] += 1
        if _contains_sensitive(movement.notas_admin):
            counts['sensitive_admin_notes'] += 1

        if movement.origen_importacion == OrigenImportacionMovimiento.MANUAL_CONTROLLED:
            if not has_text(movement.evidencia_importacion_ref):
                counts['manual_import_evidence_missing'] += 1

        if movement.origen_importacion == OrigenImportacionMovimiento.PROVIDER_SYNC:
            if not has_text(movement.transaction_id_banco):
                counts['provider_sync_transaction_missing'] += 1
            if bank_provider_sync_blocking_reason(movement.conexion_bancaria):
                counts['provider_sync_connection_not_ready'] += 1

        if movement.estado_conciliacion in {
            EstadoConciliacionMovimiento.UNKNOWN_INCOME,
            EstadoConciliacionMovimiento.MANUAL_REQUIRED,
            EstadoConciliacionMovimiento.EXACT_MATCH,
        }:
            audit_events = match_audit_events_by_movement.get(str(movement.pk), [])
            if not audit_events:
                counts['match_audit_missing'] += 1
            elif any(
                has_text((event.metadata or {}).get('movimiento_id'))
                and str((event.metadata or {}).get('movimiento_id')) != str(movement.pk)
                for event in audit_events
            ):
                counts['match_audit_metadata_mismatch'] += 1

        if (
            movement.tipo_movimiento == TipoMovimientoBancario.CREDIT
            and movement.estado_conciliacion == EstadoConciliacionMovimiento.EXACT_MATCH
            and not movement.pago_mensual_id
            and not movement.codigo_cobro_residual_id
            and movement.pk not in internal_transfer_destination_ids
        ):
            counts['credit_exact_match_without_target'] += 1

        if (
            movement.tipo_movimiento == TipoMovimientoBancario.CREDIT
            and movement.estado_conciliacion == EstadoConciliacionMovimiento.EXACT_MATCH
            and movement.pago_mensual_id
        ):
            try:
                payment = movement.pago_mensual
            except PagoMensual.DoesNotExist:
                payment = None
            if (
                payment is not None
                and Decimal(str(movement.monto)) != Decimal(str(payment.monto_calculado_clp))
                and not _has_resolved_payment_manual_assignment(movement)
            ):
                counts['payment_partial_without_manual_resolution'] += 1

        if (
            movement.tipo_movimiento == TipoMovimientoBancario.DEBIT
            and movement.estado_conciliacion == EstadoConciliacionMovimiento.EXACT_MATCH
            and movement.pk not in resolved_charge_movement_ids
        ):
            counts['debit_exact_match_without_manual_resolution'] += 1

    duplicate_transaction_rows = sum(count for count in transaction_keys.values() if count > 1)
    if duplicate_transaction_rows:
        counts['transaction_id_duplicate'] = duplicate_transaction_rows

    return dict(sorted(counts.items()))


def _collect_unknown_income_issues(unknown_income) -> dict[str, int]:
    counts = Counter()
    for item in unknown_income:
        if contains_sensitive_reference(item.sugerencia_asistida or {}, include_sensitive_keys=True):
            counts['sensitive_suggestion'] += 1
    return dict(sorted(counts.items()))


def _collect_internal_transfer_issues(transfers) -> dict[str, int]:
    counts = Counter()
    for transfer in transfers:
        try:
            transfer.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        if _has_sensitive_reference(transfer, TRANSFER_REFERENCE_FIELDS):
            counts['sensitive_reference'] += 1

    return dict(sorted(counts.items()))


def _collect_reported_balance_issues(movements) -> dict[str, int]:
    counts = Counter()
    by_connection: dict[int, list[MovimientoBancarioImportado]] = {}
    for movement in movements.order_by('conexion_bancaria_id', 'fecha_movimiento', 'id'):
        by_connection.setdefault(movement.conexion_bancaria_id, []).append(movement)

    for connection_movements in by_connection.values():
        last_reported_balance = None
        accumulated_delta = Decimal('0.00')

        for movement in connection_movements:
            if last_reported_balance is None:
                if movement.saldo_reportado is not None:
                    counts['reported_balance_points'] += 1
                    last_reported_balance = movement.saldo_reportado
                continue

            if movement.tipo_movimiento == TipoMovimientoBancario.CREDIT:
                accumulated_delta += movement.monto
            else:
                accumulated_delta -= movement.monto

            if movement.saldo_reportado is None:
                continue

            counts['reported_balance_points'] += 1
            counts['reported_balance_continuity_checks'] += 1
            expected_balance = last_reported_balance + accumulated_delta
            if movement.saldo_reportado != expected_balance:
                counts['reported_balance_continuity_mismatch'] += 1

            last_reported_balance = movement.saldo_reportado
            accumulated_delta = Decimal('0.00')

    return dict(sorted(counts.items()))


def _collect_balance_square_issues(balance_squares) -> dict[str, int]:
    counts = Counter()
    for balance_square in balance_squares:
        try:
            balance_square.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        if _has_sensitive_reference(balance_square, BALANCE_SQUARE_REFERENCE_FIELDS):
            counts['sensitive_reference'] += 1

        if _valid_economic_period(balance_square.periodo_economico) and (
            str(balance_square.periodo_economico).strip() != _period_from_date(balance_square.fecha_cuadratura)
        ):
            counts['period_date_mismatch'] += 1

        if Decimal(str(balance_square.diferencia_clp)) != Decimal('0.00'):
            counts['nonzero_difference'] += 1

        if balance_square.estado != EstadoCuadraturaBancaria.SQUARED:
            counts['not_squared'] += 1

    return dict(sorted(counts.items()))


def _collect_balance_square_coverage_issues(movements, balance_squares) -> dict[str, int]:
    required_pairs = set()
    for movement in movements:
        account_id = getattr(getattr(movement, 'conexion_bancaria', None), 'cuenta_recaudadora_id', None)
        period = _period_from_date(movement.fecha_movimiento)
        if account_id and period:
            required_pairs.add((account_id, period))

    if not required_pairs:
        return {}

    existing_pairs = {
        (account_id, str(period or '').strip())
        for account_id, period in balance_squares.values_list('cuenta_recaudadora_id', 'periodo_economico')
    }
    missing_pairs = required_pairs - existing_pairs
    if not missing_pairs:
        return {}
    return {'missing_account_period': len(missing_pairs)}


def _collect_manual_resolution_issues(
    resolutions,
    *,
    superseded_audit_events_by_resolution: dict[str, list[AuditEvent]] | None = None,
) -> dict[str, int]:
    counts = Counter()
    superseded_audit_events_by_resolution = superseded_audit_events_by_resolution or {}
    for resolution in resolutions:
        if resolution.status == ManualResolution.Status.RESOLVED and not has_text(resolution.rationale):
            counts['resolved_without_rationale'] += 1
        if resolution.status == ManualResolution.Status.RESOLVED and _contains_sensitive(resolution.rationale):
            counts['resolved_sensitive_rationale'] += 1
        if resolution.status == ManualResolution.Status.SUPERSEDED:
            metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
            missing_trace = any(
                not has_text(metadata.get(field_name))
                for field_name in SUPERSEDED_MANUAL_RESOLUTION_REQUIRED_METADATA_FIELDS
            )
            if metadata.get('superseded_by') not in ALLOWED_MANUAL_RESOLUTION_SUPERSEDERS:
                missing_trace = True
            if not has_text(resolution.rationale):
                missing_trace = True
            if missing_trace:
                counts['superseded_without_trace'] += 1
            if not _superseded_audit_event_matches_resolution(
                resolution,
                metadata,
                superseded_audit_events_by_resolution,
            ):
                counts['superseded_without_audit_event'] += 1
        if (
            resolution.status == ManualResolution.Status.RESOLVED
            and resolution.category == 'conciliacion.ingreso_desconocido'
        ):
            metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
            missing_context = any(
                not has_text(metadata.get(field_name))
                for field_name in UNKNOWN_INCOME_MANUAL_RESOLUTION_REQUIRED_METADATA_FIELDS
            )
            if metadata.get('resolved_with') != 'payment_manual_assignment':
                missing_context = True
            if missing_context:
                counts['unknown_income_resolution_context_missing'] += 1
            else:
                if not _valid_economic_period(metadata.get('periodo_economico')):
                    counts['unknown_income_resolution_period_invalid'] += 1
                elif not _unknown_income_target_matches(resolution, metadata):
                    counts['unknown_income_resolution_target_mismatch'] += 1
                if not _non_sensitive_reference(metadata.get('evidencia_regularizacion_ref')):
                    counts['unknown_income_resolution_evidence_sensitive'] += 1
                if _contains_sensitive(metadata.get('criterio_aplicado')):
                    counts['unknown_income_resolution_context_sensitive'] += 1
        if (
            resolution.status == ManualResolution.Status.RESOLVED
            and resolution.category == 'conciliacion.movimiento_cargo'
        ):
            metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
            if metadata.get('categoria_movimiento') == CategoriaMovimiento.BANK_COMMISSION:
                missing_context = any(
                    not has_text(metadata.get(field_name))
                    for field_name in CHARGE_MANUAL_CLASSIFICATION_REQUIRED_METADATA_FIELDS
                )
                if metadata.get('entidad_afectada_tipo') != 'empresa':
                    missing_context = True
                if missing_context:
                    counts['charge_classification_context_missing'] += 1
                else:
                    if not _valid_economic_period(metadata.get('periodo_economico')):
                        counts['charge_classification_period_invalid'] += 1
                    elif not _charge_classification_target_matches(resolution, metadata):
                        counts['charge_classification_target_mismatch'] += 1
                    if not _non_sensitive_reference(metadata.get('evidencia_clasificacion_ref')):
                        counts['charge_classification_evidence_sensitive'] += 1
                    if _contains_sensitive(metadata.get('criterio_reparto')):
                        counts['charge_classification_context_sensitive'] += 1
            elif metadata.get('categoria_movimiento') == CategoriaMovimiento.INTERNAL_TRANSFER:
                missing_context = any(
                    not has_text(metadata.get(field_name))
                    for field_name in INTERNAL_TRANSFER_REQUIRED_METADATA_FIELDS
                )
                if missing_context:
                    counts['internal_transfer_context_missing'] += 1
                else:
                    if not _valid_economic_period(metadata.get('periodo_economico')):
                        counts['internal_transfer_period_invalid'] += 1
                    elif not _internal_transfer_target_matches(resolution, metadata):
                        counts['internal_transfer_target_mismatch'] += 1
                    if not _non_sensitive_reference(metadata.get('evidencia_transferencia_ref')):
                        counts['internal_transfer_evidence_sensitive'] += 1
                    if not _non_sensitive_reference(metadata.get('responsable_ref')):
                        counts['internal_transfer_evidence_sensitive'] += 1
                    if _contains_sensitive(metadata.get('criterio_conciliacion')):
                        counts['internal_transfer_context_sensitive'] += 1
            else:
                counts['charge_classification_context_missing'] += 1
    return dict(sorted(counts.items()))


def collect_stage3_conciliacion_readiness(
    *,
    stage2_evidence_ref: str = '',
    bank_proof_ref: str = '',
    balance_square_ref: str = '',
    responsible_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
    bank_connections = ConexionBancaria.objects.select_related('cuenta_recaudadora').all()
    operational_connections = bank_connections.filter(
        Q(estado_conexion=EstadoConexionBancaria.ACTIVE)
        | Q(primaria_movimientos=True)
        | Q(primaria_saldos=True)
        | Q(primaria_conectividad=True)
    )
    invalid_operational_connections = _count_invalid(operational_connections)
    sensitive_connection_refs = sum(
        1 for connection in bank_connections if _has_sensitive_reference(connection, CONNECTION_REFERENCE_FIELDS)
    )
    ready_primary_movements = sum(
        1
        for connection in bank_connections
        if connection.primaria_movimientos and not bank_provider_sync_blocking_reason(connection)
    )
    ready_primary_balances = sum(1 for connection in bank_connections if _balance_connection_ready(connection))
    bank_recent_errors = bank_connections.filter(ultimo_error_at__isnull=False).filter(
        Q(ultimo_exito_at__isnull=True) | Q(ultimo_error_at__gt=F('ultimo_exito_at'))
    ).count()

    movements = MovimientoBancarioImportado.objects.select_related(
        'conexion_bancaria',
        'pago_mensual',
        'codigo_cobro_residual',
    ).all()
    internal_transfers = TransferenciaIntercuenta.objects.select_related(
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora',
    ).all()
    manual_resolutions = ManualResolution.objects.filter(
        category__in=STAGE3_MANUAL_RESOLUTION_CATEGORIES,
        scope_type='movimiento_bancario',
    )
    resolved_charge_movement_ids = set()
    for scope_reference in manual_resolutions.filter(
        category='conciliacion.movimiento_cargo',
        status=ManualResolution.Status.RESOLVED,
    ).values_list('scope_reference', flat=True):
        try:
            resolved_charge_movement_ids.add(int(str(scope_reference or '').strip()))
        except (TypeError, ValueError):
            continue

    internal_transfer_issues = _collect_internal_transfer_issues(internal_transfers)
    internal_transfer_destination_ids = set(internal_transfers.values_list('movimiento_destino_id', flat=True))
    movement_ids = [str(pk) for pk in movements.values_list('pk', flat=True)]
    match_audit_events_by_movement: dict[str, list[AuditEvent]] = {}
    if movement_ids:
        for event in AuditEvent.objects.filter(
            event_type__in=MOVEMENT_MATCH_AUDIT_EVENT_TYPES,
            entity_type='movimiento_bancario',
            entity_id__in=movement_ids,
        ):
            match_audit_events_by_movement.setdefault(event.entity_id, []).append(event)
    movement_issues = _collect_movement_issues(
        movements,
        internal_transfer_destination_ids=internal_transfer_destination_ids,
        resolved_charge_movement_ids=resolved_charge_movement_ids,
        match_audit_events_by_movement=match_audit_events_by_movement,
    )
    reported_balance_issues = _collect_reported_balance_issues(movements)
    balance_squares = CuadraturaBancaria.objects.select_related('cuenta_recaudadora').all()
    balance_square_issues = _collect_balance_square_issues(balance_squares)
    balance_square_coverage_issues = _collect_balance_square_coverage_issues(movements, balance_squares)
    unresolved_movements = movements.filter(
        estado_conciliacion__in=[
            EstadoConciliacionMovimiento.PENDING,
            EstadoConciliacionMovimiento.UNKNOWN_INCOME,
            EstadoConciliacionMovimiento.MANUAL_REQUIRED,
        ]
    ).count()
    exact_matched_movements = movements.filter(estado_conciliacion=EstadoConciliacionMovimiento.EXACT_MATCH).count()
    movements_with_reported_balance = movements.filter(saldo_reportado__isnull=False).count()

    unknown_income = IngresoDesconocido.objects.select_related('movimiento_bancario', 'cuenta_recaudadora').all()
    invalid_unknown_income = _count_invalid(unknown_income)
    open_unknown_income = unknown_income.filter(estado=EstadoIngresoDesconocido.OPEN).count()
    unknown_income_issues = _collect_unknown_income_issues(unknown_income)
    balance_signal_available = ready_primary_balances > 0 or movements_with_reported_balance > 0
    superseded_resolution_ids = [
        str(pk)
        for pk in manual_resolutions.filter(status=ManualResolution.Status.SUPERSEDED).values_list('pk', flat=True)
    ]
    superseded_audit_events_by_resolution: dict[str, list[AuditEvent]] = {}
    if superseded_resolution_ids:
        for event in AuditEvent.objects.filter(
            event_type=SUPERSEDED_MANUAL_RESOLUTION_EVENT_TYPE,
            entity_type='manual_resolution',
            entity_id__in=superseded_resolution_ids,
        ):
            superseded_audit_events_by_resolution.setdefault(event.entity_id, []).append(event)

    manual_resolution_issues = _collect_manual_resolution_issues(
        manual_resolutions,
        superseded_audit_events_by_resolution=superseded_audit_events_by_resolution,
    )

    final_evidence = {
        'stage2_evidence_ref': _non_sensitive_reference(stage2_evidence_ref),
        'bank_proof_ref': _non_sensitive_reference(bank_proof_ref),
        'balance_square_ref': _non_sensitive_reference(balance_square_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    final_evidence_sensitive = {
        'stage2_evidence_ref': _sensitive_reference(stage2_evidence_ref),
        'bank_proof_ref': _sensitive_reference(bank_proof_ref),
        'balance_square_ref': _sensitive_reference(balance_square_ref),
        'responsible_ref': _sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_trace_sensitive = {
        'source_label': _sensitive_reference(source_label),
        'authorization_ref': _sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE3_SOURCE_KINDS
    state_transition_metadata_missing = count_state_changed_events_without_transition_metadata(
        STAGE3_STATE_CHANGE_EVENT_PREFIXES
    )

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage3.source_kind_not_authorized',
                'La readiness local de Etapa 3 no puede cerrar Conciliacion sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, missing_code, sensitive_code, missing_message, sensitive_message in [
            (
                'source_label',
                'stage3.source_label_missing',
                'stage3.source_label_sensitive',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 3.',
                'La etiqueta de fuente autorizada de Etapa 3 contiene una referencia sensible.',
            ),
            (
                'authorization_ref',
                'stage3.authorization_ref_missing',
                'stage3.authorization_ref_sensitive',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 3.',
                'La referencia de autorizacion de Etapa 3 contiene valores sensibles.',
            ),
        ]:
            if source_trace_sensitive[key]:
                issues.append(_issue(sensitive_code, sensitive_message))
            elif not source_trace[key]:
                issues.append(_issue(missing_code, missing_message))
    if state_transition_metadata_missing:
        issues.append(
            _issue(
                'stage3.audit.state_transition_metadata_missing',
                'Existen eventos state_changed de Conciliacion sin campo_estado, estado_anterior o estado_nuevo.',
                count=state_transition_metadata_missing,
            )
        )
    if bank_connections.count() == 0:
        issues.append(
            _issue(
                'stage3.bank_connection_missing',
                'Etapa 3 requiere al menos una conexion bancaria local trazable para auditar conciliacion.',
            )
        )
    if ready_primary_movements <= 0:
        issues.append(
            _issue(
                'stage3.bank_connection.primary_movements_missing',
                'Etapa 3 requiere una conexion activa y primaria de movimientos con readiness trazable.',
            )
        )
    if invalid_operational_connections:
        issues.append(
            _issue(
                'stage3.bank_connection.invalid_operational',
                'Existen conexiones bancarias operativas o primarias que no pasan validacion de dominio.',
                count=invalid_operational_connections,
            )
        )
    if sensitive_connection_refs:
        issues.append(
            _issue(
                'stage3.bank_connection.sensitive_reference',
                'Existen conexiones bancarias con referencias operativas sensibles.',
                count=sensitive_connection_refs,
            )
        )
    if bank_recent_errors:
        issues.append(
            _issue(
                'stage3.bank_connection.recent_error',
                'Existen conexiones bancarias con error posterior al ultimo exito conocido.',
                count=bank_recent_errors,
            )
        )
    if movements.count() == 0:
        issues.append(
            _issue(
                'stage3.movements_missing',
                'No existen movimientos bancarios locales para validar conciliacion.',
            )
        )
    if movement_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage3.movement.invalid_model',
                'Existen movimientos bancarios que no pasan validacion de dominio.',
                count=movement_issues['invalid_model'],
            )
        )
    if movement_issues.get('manual_import_evidence_missing'):
        issues.append(
            _issue(
                'stage3.movement.manual_import_evidence_missing',
                'Existen cargas manuales bancarias sin evidencia de importacion controlada.',
                count=movement_issues['manual_import_evidence_missing'],
            )
        )
    if movement_issues.get('provider_sync_transaction_missing'):
        issues.append(
            _issue(
                'stage3.movement.provider_sync_transaction_missing',
                'Existen movimientos provider_sync sin transaction_id_banco trazable.',
                count=movement_issues['provider_sync_transaction_missing'],
            )
        )
    if movement_issues.get('transaction_id_duplicate'):
        issues.append(
            _issue(
                'stage3.movement.transaction_id_duplicate',
                'Existen movimientos bancarios con transaction_id_banco duplicado dentro de una misma conexion.',
                count=movement_issues['transaction_id_duplicate'],
            )
        )
    if movement_issues.get('provider_sync_connection_not_ready'):
        issues.append(
            _issue(
                'stage3.movement.provider_sync_connection_not_ready',
                'Existen movimientos provider_sync asociados a conexion bancaria no lista.',
                count=movement_issues['provider_sync_connection_not_ready'],
            )
        )
    if movement_issues.get('sensitive_reference'):
        issues.append(
            _issue(
                'stage3.movement.sensitive_reference',
                'Existen movimientos bancarios con referencias de importacion, banco o proveedor sensibles.',
                count=movement_issues['sensitive_reference'],
            )
        )
    if movement_issues.get('sensitive_admin_notes'):
        issues.append(
            _issue(
                'stage3.movement.sensitive_admin_notes',
                'Existen movimientos bancarios con notas administrativas sensibles.',
                count=movement_issues['sensitive_admin_notes'],
            )
        )
    if movement_issues.get('match_audit_missing'):
        issues.append(
            _issue(
                'stage3.movement.match_audit_missing',
                'Existen movimientos conciliados o clasificados sin auditoria de intento/reintento de match exacto.',
                count=movement_issues['match_audit_missing'],
            )
        )
    if movement_issues.get('match_audit_metadata_mismatch'):
        issues.append(
            _issue(
                'stage3.movement.match_audit_metadata_mismatch',
                'Existen auditorias de match exacto con metadata de movimiento desalineada.',
                count=movement_issues['match_audit_metadata_mismatch'],
            )
        )
    if movement_issues.get('credit_exact_match_without_target'):
        issues.append(
            _issue(
                'stage3.movement.credit_exact_match_without_target',
                'Existen abonos conciliados exactos sin pago mensual ni codigo residual trazable.',
                count=movement_issues['credit_exact_match_without_target'],
            )
        )
    if movement_issues.get('payment_partial_without_manual_resolution'):
        issues.append(
            _issue(
                'stage3.movement.payment_partial_without_manual_resolution',
                'Existen abonos parciales o complementarios conciliados a pagos sin resolucion manual auditada.',
                count=movement_issues['payment_partial_without_manual_resolution'],
            )
        )
    if movement_issues.get('debit_exact_match_without_manual_resolution'):
        issues.append(
            _issue(
                'stage3.movement.debit_exact_match_without_manual_resolution',
                'Existen cargos conciliados exactos sin resolucion manual trazable.',
                count=movement_issues['debit_exact_match_without_manual_resolution'],
            )
        )
    if unresolved_movements:
        issues.append(
            _issue(
                'stage3.movements_unresolved',
                'Existen movimientos pendientes, ingresos desconocidos o cargos que requieren resolucion manual.',
                count=unresolved_movements,
            )
        )
    if open_unknown_income:
        issues.append(
            _issue(
                'stage3.unknown_income_open',
                'Existen ingresos desconocidos abiertos.',
                count=open_unknown_income,
            )
        )
    if invalid_unknown_income:
        issues.append(
            _issue(
                'stage3.unknown_income.invalid_model',
                'Existen ingresos desconocidos que no coinciden con su movimiento bancario.',
                count=invalid_unknown_income,
            )
        )
    if unknown_income_issues.get('sensitive_suggestion'):
        issues.append(
            _issue(
                'stage3.unknown_income.sensitive_suggestion',
                'Existen ingresos desconocidos con sugerencias asistidas que contienen claves o valores sensibles.',
                count=unknown_income_issues['sensitive_suggestion'],
            )
        )
    if not balance_signal_available:
        issues.append(
            _issue(
                'stage3.balance_signal_missing',
                'No existe senal local de saldo bancario reportado o conexion primaria de saldos lista.',
            )
        )
    if reported_balance_issues.get('reported_balance_continuity_mismatch'):
        issues.append(
            _issue(
                'stage3.balance_reported_continuity_mismatch',
                'Existen saldos reportados que no continuan segun los movimientos importados intermedios.',
                count=reported_balance_issues['reported_balance_continuity_mismatch'],
            )
        )
    if balance_squares.count() == 0:
        issues.append(
            _issue(
                'stage3.balance_square_record_missing',
                'No existe registro local de cuadratura sistema/banco por cuenta y periodo.',
            )
        )
    if balance_square_coverage_issues.get('missing_account_period'):
        issues.append(
            _issue(
                'stage3.balance_square.account_period_missing',
                'Faltan cuadraturas banco/sistema para cuentas y periodos con movimientos bancarios.',
                count=balance_square_coverage_issues['missing_account_period'],
            )
        )
    if balance_square_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage3.balance_square.invalid_model',
                'Existen registros de cuadratura banco/sistema invalidos.',
                count=balance_square_issues['invalid_model'],
            )
        )
    if balance_square_issues.get('sensitive_reference'):
        issues.append(
            _issue(
                'stage3.balance_square.sensitive_reference',
                'Existen cuadraturas banco/sistema con referencias sensibles.',
                count=balance_square_issues['sensitive_reference'],
            )
        )
    if balance_square_issues.get('period_date_mismatch'):
        issues.append(
            _issue(
                'stage3.balance_square.period_date_mismatch',
                'Existen cuadraturas banco/sistema cuyo periodo economico no coincide con la fecha de cuadratura.',
                count=balance_square_issues['period_date_mismatch'],
            )
        )
    if balance_square_issues.get('nonzero_difference'):
        issues.append(
            _issue(
                'stage3.balance_square.nonzero_difference',
                'Existen cuadraturas banco/sistema con diferencia distinta de cero.',
                count=balance_square_issues['nonzero_difference'],
            )
        )
    if balance_square_issues.get('not_squared'):
        issues.append(
            _issue(
                'stage3.balance_square.not_squared',
                'Existen cuadraturas banco/sistema que no estan en estado cuadrada.',
                count=balance_square_issues['not_squared'],
            )
        )
    if internal_transfer_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage3.internal_transfer.invalid_model',
                'Existen transferencias internas que no pasan validacion de dominio.',
                count=internal_transfer_issues['invalid_model'],
            )
        )
    if internal_transfer_issues.get('sensitive_reference'):
        issues.append(
            _issue(
                'stage3.internal_transfer.sensitive_reference',
                'Existen transferencias internas con evidencia o responsable sensible.',
                count=internal_transfer_issues['sensitive_reference'],
            )
        )
    if manual_resolution_issues.get('resolved_without_rationale'):
        issues.append(
            _issue(
                'stage3.manual_resolution.rationale_missing',
                'Existen resoluciones manuales de conciliacion cerradas sin motivo auditable.',
                count=manual_resolution_issues['resolved_without_rationale'],
            )
        )
    if manual_resolution_issues.get('resolved_sensitive_rationale'):
        issues.append(
            _issue(
                'stage3.manual_resolution.rationale_sensitive',
                'Existen resoluciones manuales de conciliacion cerradas con motivo sensible.',
                count=manual_resolution_issues['resolved_sensitive_rationale'],
            )
        )
    if manual_resolution_issues.get('superseded_without_trace'):
        issues.append(
            _issue(
                'stage3.manual_resolution.superseded_trace_missing',
                'Existen resoluciones manuales de conciliacion supersedidas sin traza auditable suficiente.',
                count=manual_resolution_issues['superseded_without_trace'],
            )
        )
    if manual_resolution_issues.get('superseded_without_audit_event'):
        issues.append(
            _issue(
                'stage3.manual_resolution.superseded_audit_event_missing',
                'Existen resoluciones manuales de conciliacion supersedidas sin evento de auditoria alineado.',
                count=manual_resolution_issues['superseded_without_audit_event'],
            )
        )
    if manual_resolution_issues.get('unknown_income_resolution_context_missing'):
        issues.append(
            _issue(
                'stage3.manual_resolution.unknown_income_resolution_context_missing',
                'Existen ingresos desconocidos resueltos manualmente sin pago, contrato, periodo, criterio o evidencia trazable.',
                count=manual_resolution_issues['unknown_income_resolution_context_missing'],
            )
        )
    if manual_resolution_issues.get('unknown_income_resolution_evidence_sensitive'):
        issues.append(
            _issue(
                'stage3.manual_resolution.unknown_income_resolution_evidence_sensitive',
                'Existen ingresos desconocidos resueltos con evidencia de regularizacion sensible.',
                count=manual_resolution_issues['unknown_income_resolution_evidence_sensitive'],
            )
        )
    if manual_resolution_issues.get('unknown_income_resolution_context_sensitive'):
        issues.append(
            _issue(
                'stage3.manual_resolution.unknown_income_resolution_context_sensitive',
                'Existen ingresos desconocidos resueltos con criterio de regularizacion sensible.',
                count=manual_resolution_issues['unknown_income_resolution_context_sensitive'],
            )
        )
    if manual_resolution_issues.get('unknown_income_resolution_period_invalid'):
        issues.append(
            _issue(
                'stage3.manual_resolution.unknown_income_resolution_period_invalid',
                'Existen ingresos desconocidos resueltos con periodo economico invalido.',
                count=manual_resolution_issues['unknown_income_resolution_period_invalid'],
            )
        )
    if manual_resolution_issues.get('unknown_income_resolution_target_mismatch'):
        issues.append(
            _issue(
                'stage3.manual_resolution.unknown_income_resolution_target_mismatch',
                'Existen ingresos desconocidos resueltos cuya traza no coincide con el pago mensual target.',
                count=manual_resolution_issues['unknown_income_resolution_target_mismatch'],
            )
        )
    if manual_resolution_issues.get('charge_classification_context_missing'):
        issues.append(
            _issue(
                'stage3.manual_resolution.charge_classification_context_missing',
                'Existen cargos bancarios resueltos manualmente sin categoria, entidad, periodo, criterio, evidencia o traza contable.',
                count=manual_resolution_issues['charge_classification_context_missing'],
            )
        )
    if manual_resolution_issues.get('charge_classification_evidence_sensitive'):
        issues.append(
            _issue(
                'stage3.manual_resolution.charge_classification_evidence_sensitive',
                'Existen cargos bancarios resueltos con evidencia de clasificacion sensible.',
                count=manual_resolution_issues['charge_classification_evidence_sensitive'],
            )
        )
    if manual_resolution_issues.get('charge_classification_context_sensitive'):
        issues.append(
            _issue(
                'stage3.manual_resolution.charge_classification_context_sensitive',
                'Existen cargos bancarios resueltos con criterio de reparto sensible.',
                count=manual_resolution_issues['charge_classification_context_sensitive'],
            )
        )
    if manual_resolution_issues.get('charge_classification_period_invalid'):
        issues.append(
            _issue(
                'stage3.manual_resolution.charge_classification_period_invalid',
                'Existen cargos bancarios resueltos con periodo economico invalido.',
                count=manual_resolution_issues['charge_classification_period_invalid'],
            )
        )
    if manual_resolution_issues.get('charge_classification_target_mismatch'):
        issues.append(
            _issue(
                'stage3.manual_resolution.charge_classification_target_mismatch',
                'Existen cargos bancarios resueltos cuya traza no coincide con la entidad afectada o evento contable.',
                count=manual_resolution_issues['charge_classification_target_mismatch'],
            )
        )
    if manual_resolution_issues.get('internal_transfer_context_missing'):
        issues.append(
            _issue(
                'stage3.manual_resolution.internal_transfer_context_missing',
                'Existen transferencias internas resueltas sin par de movimientos, entidades, periodo, criterio, evidencia o traza contable.',
                count=manual_resolution_issues['internal_transfer_context_missing'],
            )
        )
    if manual_resolution_issues.get('internal_transfer_evidence_sensitive'):
        issues.append(
            _issue(
                'stage3.manual_resolution.internal_transfer_evidence_sensitive',
                'Existen transferencias internas resueltas con evidencia o responsable sensible.',
                count=manual_resolution_issues['internal_transfer_evidence_sensitive'],
            )
        )
    if manual_resolution_issues.get('internal_transfer_context_sensitive'):
        issues.append(
            _issue(
                'stage3.manual_resolution.internal_transfer_context_sensitive',
                'Existen transferencias internas resueltas con criterio de conciliacion sensible.',
                count=manual_resolution_issues['internal_transfer_context_sensitive'],
            )
        )
    if manual_resolution_issues.get('internal_transfer_period_invalid'):
        issues.append(
            _issue(
                'stage3.manual_resolution.internal_transfer_period_invalid',
                'Existen transferencias internas resueltas con periodo economico invalido.',
                count=manual_resolution_issues['internal_transfer_period_invalid'],
            )
        )
    if manual_resolution_issues.get('internal_transfer_target_mismatch'):
        issues.append(
            _issue(
                'stage3.manual_resolution.internal_transfer_target_mismatch',
                'Existen transferencias internas resueltas cuya traza no coincide con el par cargo/abono, la metadata registrada o los eventos contables.',
                count=manual_resolution_issues['internal_transfer_target_mismatch'],
            )
        )

    for key, missing_code, sensitive_code, missing_message, sensitive_message in [
        (
            'stage2_evidence_ref',
            'stage3.stage2_evidence_ref_missing',
            'stage3.stage2_evidence_ref_sensitive',
            'Falta referencia no sensible a cierre/evidencia de Etapa 2.',
            'La referencia a cierre/evidencia de Etapa 2 contiene valores sensibles.',
        ),
        (
            'bank_proof_ref',
            'stage3.bank_proof_ref_missing',
            'stage3.bank_proof_ref_sensitive',
            'Falta referencia no sensible a prueba controlada de banco o snapshot autorizado.',
            'La referencia a prueba controlada de banco o snapshot autorizado contiene valores sensibles.',
        ),
        (
            'balance_square_ref',
            'stage3.balance_square_ref_missing',
            'stage3.balance_square_ref_sensitive',
            'Falta referencia no sensible a cuadratura sistema/banco.',
            'La referencia a cuadratura sistema/banco contiene valores sensibles.',
        ),
        (
            'responsible_ref',
            'stage3.responsible_ref_missing',
            'stage3.responsible_ref_sensitive',
            'Falta referencia no sensible a responsables de conciliacion.',
            'La referencia a responsables de conciliacion contiene valores sensibles.',
        ),
    ]:
        if final_evidence_sensitive[key]:
            issues.append(_issue(sensitive_code, sensitive_message))
        elif not final_evidence[key]:
            issues.append(_issue(missing_code, missing_message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 3 - Banco y conciliacion',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_STAGE3_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage3_conciliacion': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'bank_connections': {
                'total': bank_connections.count(),
                'by_provider': _count_by(bank_connections, 'provider_key'),
                'by_state': _count_by(bank_connections, 'estado_conexion'),
                'ready_primary_movements': ready_primary_movements,
                'ready_primary_balances': ready_primary_balances,
                'invalid_operational_connections': invalid_operational_connections,
                'sensitive_references': sensitive_connection_refs,
                'recent_error_after_success': bank_recent_errors,
            },
            'movements': {
                'total': movements.count(),
                'by_import_origin': _count_by(movements, 'origen_importacion'),
                'by_reconciliation_state': _count_by(movements, 'estado_conciliacion'),
                'exact_matched': exact_matched_movements,
                'unresolved': unresolved_movements,
                'with_reported_balance': movements_with_reported_balance,
                **movement_issues,
                **reported_balance_issues,
            },
            'unknown_income': {
                'total': unknown_income.count(),
                'by_state': _count_by(unknown_income, 'estado'),
                'open': open_unknown_income,
                'invalid_model': invalid_unknown_income,
                **unknown_income_issues,
            },
            'balance_squares': {
                'total': balance_squares.count(),
                'by_status': _count_by(balance_squares, 'estado'),
                **balance_square_coverage_issues,
                **balance_square_issues,
            },
            'internal_transfers': {
                'total': internal_transfers.count(),
                'by_period': _count_by(internal_transfers, 'periodo_economico'),
                **internal_transfer_issues,
            },
            'manual_resolutions': {
                'total': manual_resolutions.count(),
                'by_category': _count_by(manual_resolutions, 'category'),
                'by_status': _count_by(manual_resolutions, 'status'),
                **manual_resolution_issues,
            },
            'audit': {
                'state_transition_metadata_missing': state_transition_metadata_missing,
            },
            'final_evidence': final_evidence,
            'final_evidence_sensitive': final_evidence_sensitive,
            'source_trace': source_trace,
            'source_trace_sensitive': source_trace_sensitive,
        },
        'limitations': [
            'Auditoria local de solo lectura; no conecta bancos ni consulta proveedores externos.',
            'No usa secretos, .env, datos reales ni snapshots externos.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No cierra Etapa 3 sin banco real o snapshot autorizado, continuidad de saldos reportados y cuadratura sistema/banco evidenciada.',
        ],
    }
