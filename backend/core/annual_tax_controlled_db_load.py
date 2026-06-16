from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    LibroDiario,
    LibroMayor,
    ObligacionTributariaMensual,
)
from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from sii.models import (
    CapacidadSII,
    EstadoMonthlyTaxFact,
    F29PreparacionMensual,
    MonthlyTaxFact,
)


CONTROLLED_DB_LOAD_SCHEMA_VERSION = 'annual-tax-controlled-db-load.v1'

FORBIDDEN_EXPECTED_OUTPUT_KEYS = {
    'expected_outputs',
    'comparison_outputs_as_inputs',
    'annual_balance_expected_outputs',
    'annual_tax_register_expected_outputs',
    'ddjj_expected_outputs',
    'f22_expected_outputs',
    *COMPARISON_ONLY_CATEGORIES,
}

REFERENCE_FIELDS = (
    'company_ref',
    'source_manifest_hash',
    'responsible_ref',
    'approval_ref',
)


def _required_text(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or '').strip()
    if not value:
        raise ValueError(f'{key} es obligatorio.')
    if key != 'source_manifest_hash' and not is_non_sensitive_reference(value):
        raise ValueError(f'{key} debe ser una referencia no sensible.')
    return value


def _decimal(value: Any, *, field_name: str) -> Decimal:
    try:
        return Decimal(str(value if value is not None else '0.00'))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f'{field_name} debe ser decimal.') from error


def _forbidden_expected_output_paths(value: Any, path: str = '$') -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            item_path = f'{path}.{key_text}'
            if key_text in FORBIDDEN_EXPECTED_OUTPUT_KEYS:
                paths.append(item_path)
            if key_text == 'category' and str(item) in COMPARISON_ONLY_CATEGORIES:
                paths.append(item_path)
            paths.extend(_forbidden_expected_output_paths(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_forbidden_expected_output_paths(item, f'{path}[{index}]'))
    return paths


def _validate_package(payload: dict[str, Any]) -> tuple[int, int, str, str, str]:
    if not isinstance(payload, dict):
        raise ValueError('El paquete de carga debe ser un objeto JSON.')
    if payload.get('schema_version') != CONTROLLED_DB_LOAD_SCHEMA_VERSION:
        raise ValueError(f'schema_version debe ser {CONTROLLED_DB_LOAD_SCHEMA_VERSION}.')
    if payload.get('expected_outputs_used_as_inputs') is True:
        raise ValueError('El paquete no puede usar salidas esperadas como insumos.')
    forbidden_paths = _forbidden_expected_output_paths(payload)
    if forbidden_paths:
        raise ValueError(
            'El paquete no puede incluir salidas esperadas Balance/RLI/CPT/RAI/DDJJ/F22 finales como insumos: '
            + ', '.join(forbidden_paths[:5])
        )
    if contains_sensitive_reference(payload, include_sensitive_keys=True):
        raise ValueError('El paquete contiene referencias sensibles o claves no permitidas.')

    for field_name in REFERENCE_FIELDS:
        _required_text(payload, field_name)

    commercial_year = int(payload.get('commercial_year') or 0)
    tax_year = int(payload.get('tax_year') or 0)
    if commercial_year < 2000 or tax_year != commercial_year + 1:
        raise ValueError('commercial_year y tax_year deben formar un par AC/AT valido.')

    months = payload.get('months')
    if not isinstance(months, list) or not months:
        raise ValueError('months debe contener al menos un mes normalizado.')
    seen = set()
    for item in months:
        if not isinstance(item, dict):
            raise ValueError('Cada mes debe ser un objeto JSON.')
        month = int(item.get('month') or 0)
        if month < 1 or month > 12:
            raise ValueError('month debe estar entre 1 y 12.')
        if month in seen:
            raise ValueError(f'Mes duplicado en paquete controlado: {month}.')
        seen.add(month)
        if not isinstance(item.get('ledger'), dict):
            raise ValueError(f'Mes {month} requiere ledger normalizado.')
        if not isinstance(item.get('balance'), dict):
            raise ValueError(f'Mes {month} requiere balance normalizado.')
        _required_text(item, 'source_ref')

    return (
        commercial_year,
        tax_year,
        _required_text(payload, 'source_manifest_hash'),
        _required_text(payload, 'responsible_ref'),
        _required_text(payload, 'approval_ref'),
    )


def _get_existing_or_new(model, **lookup):
    try:
        return model.objects.get(**lookup), False
    except model.DoesNotExist:
        return model(**lookup), True


def _mark_count(counts: dict[str, dict[str, int]], model_name: str, created: bool) -> None:
    bucket = counts.setdefault(model_name, {'created': 0, 'updated': 0})
    bucket['created' if created else 'updated'] += 1


def _save_validated(obj) -> None:
    try:
        obj.full_clean()
    except ValidationError as error:
        raise ValueError(error.message_dict if hasattr(error, 'message_dict') else error.messages) from error
    obj.save()


def _snapshot_summary(
    *,
    package: dict[str, Any],
    month_payload: dict[str, Any],
    source_manifest_hash: str,
    responsible_ref: str,
) -> dict[str, Any]:
    ledger = month_payload['ledger']
    balance = month_payload['balance']
    obligations = month_payload.get('obligations') or []
    balance_summary = {
        'total_debe': str(_decimal(balance.get('total_debe'), field_name='balance.total_debe')),
        'total_haber': str(_decimal(balance.get('total_haber'), field_name='balance.total_haber')),
        'cuadrado': bool(balance.get('cuadrado')),
    }
    if isinstance(balance.get('lineas_balance_8_columnas'), list):
        balance_summary['lineas_balance_8_columnas'] = balance['lineas_balance_8_columnas']
        balance_summary['lineas_balance_8_columnas_source'] = str(
            balance.get('lineas_balance_8_columnas_source') or 'controlled_package'
        )
    if isinstance(balance.get('annual_inventory_totals'), dict):
        balance_summary['annual_inventory_totals'] = balance['annual_inventory_totals']
    if balance.get('annual_inventory_ref'):
        balance_summary['annual_inventory_ref'] = str(balance.get('annual_inventory_ref') or '').strip()

    return {
        'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
        'company_ref': package['company_ref'],
        'source_manifest_hash': source_manifest_hash,
        'responsible_ref': responsible_ref,
        'source_ref': month_payload['source_ref'],
        'ledger': {
            'asientos_count': int(ledger.get('asientos_count') or 0),
            'cuentas_count': int(ledger.get('cuentas_count') or 0),
            'total_debe': str(_decimal(ledger.get('total_debe'), field_name='ledger.total_debe')),
            'total_haber': str(_decimal(ledger.get('total_haber'), field_name='ledger.total_haber')),
        },
        'balance': balance_summary,
        'obligations': [
            {
                'tipo': str(item.get('tipo') or item.get('obligacion_tipo') or '').strip(),
                'base_imponible': str(_decimal(item.get('base_imponible'), field_name='obligation.base_imponible')),
                'monto_calculado': str(_decimal(item.get('monto_calculado'), field_name='obligation.monto_calculado')),
            }
            for item in obligations
            if isinstance(item, dict)
        ],
        'f29': month_payload.get('f29') or {},
        'payroll': month_payload.get('payroll') or {},
        'expected_outputs_used_as_inputs': False,
        'final_tax_calculation': False,
    }


def _apply_month(
    *,
    empresa,
    package: dict[str, Any],
    month_payload: dict[str, Any],
    commercial_year: int,
    source_manifest_hash: str,
    responsible_ref: str,
    approval_ref: str,
    counts: dict[str, dict[str, int]],
) -> None:
    month = int(month_payload['month'])
    period = f'{commercial_year}-{month:02d}'
    now = timezone.now()
    summary = _snapshot_summary(
        package=package,
        month_payload=month_payload,
        source_manifest_hash=source_manifest_hash,
        responsible_ref=responsible_ref,
    )
    ledger = month_payload['ledger']
    balance = month_payload['balance']

    close, created = _get_existing_or_new(
        CierreMensualContable,
        empresa=empresa,
        anio=commercial_year,
        mes=month,
    )
    close.estado = EstadoCierreMensual.APPROVED
    close.fecha_preparacion = close.fecha_preparacion or now
    close.fecha_aprobacion = now
    close.resumen_obligaciones = {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
        'source_ref': month_payload['source_ref'],
        'approval_ref': approval_ref,
        'obligations_count': len(month_payload.get('obligations') or []),
    }
    _save_validated(close)
    _mark_count(counts, 'CierreMensualContable', created)

    diario, created = _get_existing_or_new(LibroDiario, empresa=empresa, periodo=period)
    diario.estado_snapshot = EstadoCierreMensual.APPROVED
    diario.storage_ref = str(ledger.get('libro_diario_ref') or month_payload['source_ref']).strip()
    diario.resumen = summary['ledger'] | {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
    }
    _save_validated(diario)
    _mark_count(counts, 'LibroDiario', created)

    mayor, created = _get_existing_or_new(LibroMayor, empresa=empresa, periodo=period)
    mayor.estado_snapshot = EstadoCierreMensual.APPROVED
    mayor.storage_ref = str(ledger.get('libro_mayor_ref') or month_payload['source_ref']).strip()
    mayor.resumen = summary['ledger'] | {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
    }
    _save_validated(mayor)
    _mark_count(counts, 'LibroMayor', created)

    balance_obj, created = _get_existing_or_new(BalanceComprobacion, empresa=empresa, periodo=period)
    balance_obj.estado_snapshot = EstadoCierreMensual.APPROVED
    balance_obj.storage_ref = str(balance.get('balance_ref') or month_payload['source_ref']).strip()
    balance_obj.resumen = summary['balance'] | {
        'controlled_load': True,
        'source_manifest_hash': source_manifest_hash,
    }
    _save_validated(balance_obj)
    _mark_count(counts, 'BalanceComprobacion', created)

    for obligation_payload in month_payload.get('obligations') or []:
        if not isinstance(obligation_payload, dict):
            raise ValueError(f'Mes {month} contiene obligacion invalida.')
        obligation_type = str(
            obligation_payload.get('tipo') or obligation_payload.get('obligacion_tipo') or ''
        ).strip()
        if not obligation_type:
            raise ValueError(f'Mes {month} contiene obligacion sin tipo.')
        obligation, created = _get_existing_or_new(
            ObligacionTributariaMensual,
            empresa=empresa,
            anio=commercial_year,
            mes=month,
            obligacion_tipo=obligation_type,
        )
        obligation.base_imponible = _decimal(
            obligation_payload.get('base_imponible'),
            field_name='obligation.base_imponible',
        )
        obligation.monto_calculado = _decimal(
            obligation_payload.get('monto_calculado'),
            field_name='obligation.monto_calculado',
        )
        obligation.estado_preparacion = obligation_payload.get(
            'estado_preparacion',
            EstadoPreparacionTributaria.PREPARED,
        )
        obligation.detalle_calculo = {
            'controlled_load': True,
            'source_ref': obligation_payload.get('source_ref') or month_payload['source_ref'],
            'source_manifest_hash': source_manifest_hash,
        }
        _save_validated(obligation)
        _mark_count(counts, 'ObligacionTributariaMensual', created)

    f29_obj = None
    f29_payload = month_payload.get('f29')
    f29_no_declaration = (
        isinstance(f29_payload, dict)
        and f29_payload.get('estado_preparacion') == EstadoPreparacionTributaria.NOT_APPLICABLE
        and isinstance(f29_payload.get('resumen'), dict)
        and f29_payload['resumen'].get('no_declaration') is True
    )
    if isinstance(f29_payload, dict) and f29_payload and not f29_no_declaration:
        capability = empresa.capacidades_sii.filter(capacidad_key=CapacidadSII.F29_PREPARACION).first()
        if capability is None:
            raise ValueError(f'Mes {month} requiere CapacidadTributariaSII F29_PREPARACION para cargar F29.')
        f29_obj, created = _get_existing_or_new(
            F29PreparacionMensual,
            empresa=empresa,
            anio=commercial_year,
            mes=month,
        )
        f29_obj.capacidad_tributaria = capability
        f29_obj.cierre_mensual = close
        f29_obj.estado_preparacion = f29_payload.get(
            'estado_preparacion',
            EstadoPreparacionTributaria.PREPARED,
        )
        f29_obj.resumen_formulario = {
            'controlled_load': True,
            'source_manifest_hash': source_manifest_hash,
            **(f29_payload.get('resumen') if isinstance(f29_payload.get('resumen'), dict) else {}),
        }
        f29_obj.borrador_ref = str(f29_payload.get('borrador_ref') or '').strip()
        f29_obj.responsable_revision_ref = str(f29_payload.get('responsable_revision_ref') or responsible_ref).strip()
        f29_obj.observaciones = str(f29_payload.get('observaciones') or '').strip()
        _save_validated(f29_obj)
        _mark_count(counts, 'F29PreparacionMensual', created)

    fact, created = _get_existing_or_new(MonthlyTaxFact, empresa=empresa, anio=commercial_year, mes=month)
    fact.cierre_mensual = close
    fact.f29_preparacion = f29_obj
    fact.source_ref = month_payload['source_ref']
    fact.responsible_ref = responsible_ref
    fact.resumen_hecho = {
        'empresa_id': empresa.id,
        'anio': commercial_year,
        'mes': month,
        **summary,
    }
    fact.hash_hecho = payload_hash(fact.resumen_hecho)
    fact.estado = EstadoMonthlyTaxFact.NORMALIZED
    _save_validated(fact)
    _mark_count(counts, 'MonthlyTaxFact', created)


def apply_annual_tax_controlled_db_load(*, empresa, package: dict[str, Any], write_database: bool = False) -> dict[str, Any]:
    commercial_year, tax_year, source_manifest_hash, responsible_ref, approval_ref = _validate_package(package)
    months = sorted(int(item['month']) for item in package['months'])
    complete_12_months = months == list(range(1, 13))
    counts: dict[str, dict[str, int]] = {}

    if write_database:
        with transaction.atomic():
            for month_payload in sorted(package['months'], key=lambda item: int(item['month'])):
                _apply_month(
                    empresa=empresa,
                    package=package,
                    month_payload=month_payload,
                    commercial_year=commercial_year,
                    source_manifest_hash=source_manifest_hash,
                    responsible_ref=responsible_ref,
                    approval_ref=approval_ref,
                    counts=counts,
                )

    blockers = []
    if not complete_12_months:
        blockers.append('controlled_package_incomplete_12_months')

    return {
        'schema_version': CONTROLLED_DB_LOAD_SCHEMA_VERSION,
        'writes_database': write_database,
        'empresa_id': empresa.id,
        'company_ref': package['company_ref'],
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': source_manifest_hash,
        'months_loaded': months if write_database else [],
        'months_validated': months,
        'complete_12_months': complete_12_months,
        'expected_outputs_used_as_inputs': False,
        'created_updated': counts,
        'ready_for_annual_generation': write_database and complete_12_months and not blockers,
        'blockers': blockers,
        'safety': {
            'copies_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
        },
    }
