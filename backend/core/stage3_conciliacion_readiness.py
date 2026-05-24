from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import F, Q
from django.utils import timezone

from audit.models import ManualResolution
from conciliacion.models import (
    CategoriaMovimiento,
    ConexionBancaria,
    EstadoConciliacionMovimiento,
    EstadoConexionBancaria,
    EstadoIngresoDesconocido,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    OrigenImportacionMovimiento,
    TipoMovimientoBancario,
    bank_provider_sync_blocking_reason,
    has_text,
)
from core.reference_validation import is_non_sensitive_reference


AUTHORIZED_STAGE3_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
CONNECTION_REFERENCE_FIELDS = (
    'credencial_ref',
    'evidencia_gate_ref',
    'prueba_conectividad_ref',
    'prueba_movimientos_ref',
    'prueba_saldos_ref',
)
MOVEMENT_REFERENCE_FIELDS = ('evidencia_importacion_ref', 'transaction_id_banco')
STAGE3_MANUAL_RESOLUTION_CATEGORIES = (
    'conciliacion.ingreso_desconocido',
    'conciliacion.movimiento_cargo',
)
CHARGE_MANUAL_CLASSIFICATION_REQUIRED_METADATA_FIELDS = (
    'categoria_movimiento',
    'entidad_afectada_tipo',
    'entidad_afectada_id',
    'periodo_economico',
    'criterio_reparto',
    'evidencia_clasificacion_ref',
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


def _collect_movement_issues(movements) -> dict[str, int]:
    counts = Counter()
    transaction_keys = Counter()
    for movement in movements:
        try:
            movement.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        if has_text(movement.transaction_id_banco):
            transaction_keys[(movement.conexion_bancaria_id, movement.transaction_id_banco)] += 1

        if _has_sensitive_reference(movement, MOVEMENT_REFERENCE_FIELDS):
            counts['sensitive_reference'] += 1

        if movement.origen_importacion == OrigenImportacionMovimiento.MANUAL_CONTROLLED:
            if not has_text(movement.evidencia_importacion_ref):
                counts['manual_import_evidence_missing'] += 1

        if movement.origen_importacion == OrigenImportacionMovimiento.PROVIDER_SYNC:
            if not has_text(movement.transaction_id_banco):
                counts['provider_sync_transaction_missing'] += 1
            if bank_provider_sync_blocking_reason(movement.conexion_bancaria):
                counts['provider_sync_connection_not_ready'] += 1

        if (
            movement.tipo_movimiento == TipoMovimientoBancario.CREDIT
            and movement.estado_conciliacion == EstadoConciliacionMovimiento.EXACT_MATCH
            and not movement.pago_mensual_id
            and not movement.codigo_cobro_residual_id
        ):
            counts['credit_exact_match_without_target'] += 1

    duplicate_transaction_rows = sum(count for count in transaction_keys.values() if count > 1)
    if duplicate_transaction_rows:
        counts['transaction_id_duplicate'] = duplicate_transaction_rows

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


def _collect_manual_resolution_issues(resolutions) -> dict[str, int]:
    counts = Counter()
    for resolution in resolutions:
        if resolution.status == ManualResolution.Status.RESOLVED and not has_text(resolution.rationale):
            counts['resolved_without_rationale'] += 1
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
            elif not _non_sensitive_reference(metadata.get('evidencia_regularizacion_ref')):
                counts['unknown_income_resolution_evidence_sensitive'] += 1
        if (
            resolution.status == ManualResolution.Status.RESOLVED
            and resolution.category == 'conciliacion.movimiento_cargo'
        ):
            metadata = resolution.metadata if isinstance(resolution.metadata, dict) else {}
            missing_context = any(
                not has_text(metadata.get(field_name))
                for field_name in CHARGE_MANUAL_CLASSIFICATION_REQUIRED_METADATA_FIELDS
            )
            if metadata.get('categoria_movimiento') != CategoriaMovimiento.BANK_COMMISSION:
                missing_context = True
            if metadata.get('entidad_afectada_tipo') != 'empresa':
                missing_context = True
            if missing_context:
                counts['charge_classification_context_missing'] += 1
            elif not _non_sensitive_reference(metadata.get('evidencia_clasificacion_ref')):
                counts['charge_classification_evidence_sensitive'] += 1
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
    movement_issues = _collect_movement_issues(movements)
    reported_balance_issues = _collect_reported_balance_issues(movements)
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
    balance_signal_available = ready_primary_balances > 0 or movements_with_reported_balance > 0
    manual_resolutions = ManualResolution.objects.filter(
        category__in=STAGE3_MANUAL_RESOLUTION_CATEGORIES,
        scope_type='movimiento_bancario',
    )
    manual_resolution_issues = _collect_manual_resolution_issues(manual_resolutions)

    final_evidence = {
        'stage2_evidence_ref': _non_sensitive_reference(stage2_evidence_ref),
        'bank_proof_ref': _non_sensitive_reference(bank_proof_ref),
        'balance_square_ref': _non_sensitive_reference(balance_square_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE3_SOURCE_KINDS

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage3.source_kind_not_authorized',
                'La readiness local de Etapa 3 no puede cerrar Conciliacion sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, code, message in [
            (
                'source_label',
                'stage3.source_label_missing',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 3.',
            ),
            (
                'authorization_ref',
                'stage3.authorization_ref_missing',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 3.',
            ),
        ]:
            if not source_trace[key]:
                issues.append(_issue(code, message))
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
                'Existen movimientos bancarios con referencias de importacion o proveedor sensibles.',
                count=movement_issues['sensitive_reference'],
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
    if manual_resolution_issues.get('resolved_without_rationale'):
        issues.append(
            _issue(
                'stage3.manual_resolution.rationale_missing',
                'Existen resoluciones manuales de conciliacion cerradas sin motivo auditable.',
                count=manual_resolution_issues['resolved_without_rationale'],
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
    if manual_resolution_issues.get('charge_classification_context_missing'):
        issues.append(
            _issue(
                'stage3.manual_resolution.charge_classification_context_missing',
                'Existen cargos bancarios resueltos manualmente sin categoria, entidad, periodo, criterio o evidencia trazable.',
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

    for key, code, message in [
        (
            'stage2_evidence_ref',
            'stage3.stage2_evidence_ref_missing',
            'Falta referencia no sensible a cierre/evidencia de Etapa 2.',
        ),
        (
            'bank_proof_ref',
            'stage3.bank_proof_ref_missing',
            'Falta referencia no sensible a prueba controlada de banco o snapshot autorizado.',
        ),
        (
            'balance_square_ref',
            'stage3.balance_square_ref_missing',
            'Falta referencia no sensible a cuadratura sistema/banco.',
        ),
        (
            'responsible_ref',
            'stage3.responsible_ref_missing',
            'Falta referencia no sensible a responsables de conciliacion.',
        ),
    ]:
        if not final_evidence[key]:
            issues.append(_issue(code, message))

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
            },
            'manual_resolutions': {
                'total': manual_resolutions.count(),
                'by_category': _count_by(manual_resolutions, 'category'),
                'by_status': _count_by(manual_resolutions, 'status'),
                **manual_resolution_issues,
            },
            'final_evidence': final_evidence,
            'source_trace': source_trace,
        },
        'limitations': [
            'Auditoria local de solo lectura; no conecta bancos ni consulta proveedores externos.',
            'No usa secretos, .env, datos reales ni snapshots externos.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No cierra Etapa 3 sin banco real o snapshot autorizado, continuidad de saldos reportados y cuadratura sistema/banco evidenciada.',
        ],
    }
