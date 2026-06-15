from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from typing import Any

from core.annual_tax_controlled_db_load import (
    CONTROLLED_DB_LOAD_SCHEMA_VERSION,
    FORBIDDEN_EXPECTED_OUTPUT_KEYS,
)
from core.annual_tax_controlled_package_template import CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION
from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference


CONTROLLED_PACKAGE_READINESS_SCHEMA_VERSION = 'annual-tax-controlled-package-readiness.v1'
MONTHS = tuple(range(1, 13))

PACKAGE_REFERENCE_FIELDS = (
    'company_ref',
    'source_manifest_hash',
    'responsible_ref',
    'approval_ref',
)


def _find_forbidden_expected_output_paths(value: Any, path: str = '$') -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            item_path = f'{path}.{key_text}'
            if key_text in FORBIDDEN_EXPECTED_OUTPUT_KEYS:
                paths.append(item_path)
            if key_text == 'category' and str(item) in COMPARISON_ONLY_CATEGORIES:
                paths.append(item_path)
            paths.extend(_find_forbidden_expected_output_paths(item, item_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_find_forbidden_expected_output_paths(item, f'{path}[{index}]'))
    return paths


def _decimal(value: Any) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _non_sensitive_text(value: Any) -> bool:
    return is_non_sensitive_reference(value)


def _completed_reference(value: Any) -> bool:
    text = str(value or '').strip().lower()
    return _non_sensitive_text(value) and not text.startswith('pending-')


def _add_missing(paths: list[str], path: str) -> None:
    if path not in paths:
        paths.append(path)


def _add_invalid(paths: list[str], path: str) -> None:
    if path not in paths:
        paths.append(path)


def _extract_package(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    schema_version = str(payload.get('schema_version') or '')
    if schema_version == CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION:
        package = payload.get('package_draft')
        return package if isinstance(package, dict) else None, schema_version
    return payload, schema_version


def _validate_top_level(
    *,
    package: dict[str, Any],
    missing_paths: list[str],
    invalid_paths: list[str],
    blockers: set[str],
) -> tuple[int, int]:
    if package.get('schema_version') != CONTROLLED_DB_LOAD_SCHEMA_VERSION:
        blockers.add('schema_version_invalid')
        _add_invalid(invalid_paths, '$.schema_version')

    if package.get('expected_outputs_used_as_inputs') is True:
        blockers.add('expected_outputs_present')
        _add_invalid(invalid_paths, '$.expected_outputs_used_as_inputs')

    forbidden_paths = _find_forbidden_expected_output_paths(package)
    if forbidden_paths:
        blockers.add('expected_outputs_present')
        for path in forbidden_paths[:20]:
            _add_invalid(invalid_paths, path)

    if contains_sensitive_reference(package, include_sensitive_keys=True):
        blockers.add('sensitive_reference_present')
        _add_invalid(invalid_paths, '$')

    for field_name in PACKAGE_REFERENCE_FIELDS:
        if not _completed_reference(package.get(field_name)):
            blockers.add('missing_control_refs')
            _add_missing(missing_paths, f'$.{field_name}')

    commercial_year = int(package.get('commercial_year') or 0)
    tax_year = int(package.get('tax_year') or 0)
    if commercial_year < 2000 or tax_year != commercial_year + 1:
        blockers.add('invalid_ac_at_pair')
        _add_invalid(invalid_paths, '$.commercial_year')
        _add_invalid(invalid_paths, '$.tax_year')

    return commercial_year, tax_year


def _validate_month(
    *,
    month_payload: dict[str, Any],
    month_index: int,
    missing_paths: list[str],
    invalid_paths: list[str],
    warnings: list[str],
    blockers: set[str],
) -> None:
    path = f'$.months[{month_index}]'
    month = int(month_payload.get('month') or 0)
    if month < 1 or month > 12:
        blockers.add('invalid_months')
        _add_invalid(invalid_paths, f'{path}.month')

    if not _non_sensitive_text(month_payload.get('source_ref')):
        blockers.add('monthly_source_refs_missing')
        _add_missing(missing_paths, f'{path}.source_ref')

    ledger = month_payload.get('ledger')
    if not isinstance(ledger, dict):
        blockers.add('monthly_value_placeholders')
        _add_missing(missing_paths, f'{path}.ledger')
        ledger = {}
    for field_name in ('libro_diario_ref', 'libro_mayor_ref'):
        if not _non_sensitive_text(ledger.get(field_name)):
            blockers.add('monthly_value_placeholders')
            _add_missing(missing_paths, f'{path}.ledger.{field_name}')
    for field_name in ('asientos_count', 'cuentas_count'):
        value = ledger.get(field_name)
        if not isinstance(value, int) or value <= 0:
            blockers.add('monthly_value_placeholders')
            _add_missing(missing_paths, f'{path}.ledger.{field_name}')
    ledger_total_debe = _decimal(ledger.get('total_debe'))
    ledger_total_haber = _decimal(ledger.get('total_haber'))
    if ledger_total_debe is None or ledger_total_haber is None:
        blockers.add('monthly_value_placeholders')
        _add_missing(missing_paths, f'{path}.ledger.total_debe')
        _add_missing(missing_paths, f'{path}.ledger.total_haber')
    elif ledger_total_debe != ledger_total_haber:
        blockers.add('ledger_totals_not_squared')
        _add_invalid(invalid_paths, f'{path}.ledger')

    balance = month_payload.get('balance')
    if not isinstance(balance, dict):
        blockers.add('monthly_value_placeholders')
        _add_missing(missing_paths, f'{path}.balance')
        balance = {}
    if not _non_sensitive_text(balance.get('balance_ref')):
        blockers.add('monthly_value_placeholders')
        _add_missing(missing_paths, f'{path}.balance.balance_ref')
    balance_total_debe = _decimal(balance.get('total_debe'))
    balance_total_haber = _decimal(balance.get('total_haber'))
    if balance_total_debe is None or balance_total_haber is None:
        blockers.add('monthly_value_placeholders')
        _add_missing(missing_paths, f'{path}.balance.total_debe')
        _add_missing(missing_paths, f'{path}.balance.total_haber')
    elif balance_total_debe != balance_total_haber or balance.get('cuadrado') is not True:
        blockers.add('balance_not_squared')
        _add_invalid(invalid_paths, f'{path}.balance')

    obligations = month_payload.get('obligations')
    if obligations is None:
        obligations = []
    if not isinstance(obligations, list):
        blockers.add('monthly_obligations_invalid')
        _add_invalid(invalid_paths, f'{path}.obligations')
    elif not obligations:
        warning = f'{path}.obligations empty'
        if warning not in warnings:
            warnings.append(warning)
    else:
        for obligation_index, item in enumerate(obligations):
            item_path = f'{path}.obligations[{obligation_index}]'
            if not isinstance(item, dict):
                blockers.add('monthly_obligations_invalid')
                _add_invalid(invalid_paths, item_path)
                continue
            if not str(item.get('tipo') or item.get('obligacion_tipo') or '').strip():
                blockers.add('monthly_obligations_invalid')
                _add_missing(missing_paths, f'{item_path}.tipo')
            for field_name in ('base_imponible', 'monto_calculado'):
                if _decimal(item.get(field_name)) is None:
                    blockers.add('monthly_obligations_invalid')
                    _add_missing(missing_paths, f'{item_path}.{field_name}')

    f29 = month_payload.get('f29')
    if not isinstance(f29, dict):
        blockers.add('f29_status_missing')
        _add_missing(missing_paths, f'{path}.f29')
        f29 = {}
    estado_f29 = str(f29.get('estado_preparacion') or '').strip()
    no_declaration = bool((f29.get('resumen') or {}).get('no_declaration')) if isinstance(f29.get('resumen'), dict) else False
    if estado_f29 == 'no_aplica' and no_declaration:
        pass
    elif not _non_sensitive_text(f29.get('borrador_ref')):
        blockers.add('f29_status_missing')
        _add_missing(missing_paths, f'{path}.f29.borrador_ref')

    payroll = month_payload.get('payroll')
    if not isinstance(payroll, dict):
        blockers.add('payroll_status_missing')
        _add_missing(missing_paths, f'{path}.payroll')
    elif payroll.get('has_movements') is None:
        blockers.add('payroll_status_missing')
        _add_missing(missing_paths, f'{path}.payroll.has_movements')
    elif payroll.get('has_movements') is True and not _non_sensitive_text(payroll.get('source_ref')):
        blockers.add('payroll_status_missing')
        _add_missing(missing_paths, f'{path}.payroll.source_ref')


def audit_annual_tax_controlled_package_readiness(*, payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError('El payload debe ser un objeto JSON.')

    missing_paths: list[str] = []
    invalid_paths: list[str] = []
    warnings: list[str] = []
    blockers: set[str] = set()
    package, input_schema_version = _extract_package(payload)
    if package is None:
        return {
            'schema_version': CONTROLLED_PACKAGE_READINESS_SCHEMA_VERSION,
            'input_schema_version': input_schema_version,
            'ready_for_db_writer': False,
            'ready_for_annual_generation': False,
            'blockers': ['invalid_package_shape'],
            'warnings': [],
            'missing_value_paths': ['$.package_draft'],
            'invalid_paths': [],
            'summary': {
                'complete_12_months': False,
                'months_present': [],
                'missing_months': list(MONTHS),
                'missing_paths_count': 1,
                'invalid_paths_count': 0,
                'comparison_targets_present': False,
            },
            'safety': {
                'writes_database': False,
                'uses_sii_real': False,
                'uses_credentials': False,
                'uses_expected_outputs_as_inputs': False,
            },
        }

    commercial_year, tax_year = _validate_top_level(
        package=package,
        missing_paths=missing_paths,
        invalid_paths=invalid_paths,
        blockers=blockers,
    )

    annual_refs = package.get('annual_input_source_refs')
    if not isinstance(annual_refs, dict) or not annual_refs.get('annual_ledger_input'):
        blockers.add('annual_ledger_source_refs_missing')
        _add_missing(missing_paths, '$.annual_input_source_refs.annual_ledger_input')

    months_payload = package.get('months')
    months_present: list[int] = []
    duplicate_months: set[int] = set()
    if not isinstance(months_payload, list):
        blockers.add('incomplete_12_months')
        _add_missing(missing_paths, '$.months')
        months_payload = []
    for index, month_payload in enumerate(months_payload):
        if not isinstance(month_payload, dict):
            blockers.add('invalid_months')
            _add_invalid(invalid_paths, f'$.months[{index}]')
            continue
        month = int(month_payload.get('month') or 0)
        if month in months_present:
            duplicate_months.add(month)
        months_present.append(month)
        _validate_month(
            month_payload=month_payload,
            month_index=index,
            missing_paths=missing_paths,
            invalid_paths=invalid_paths,
            warnings=warnings,
            blockers=blockers,
        )

    valid_months_present = sorted(month for month in months_present if 1 <= month <= 12)
    missing_months = [month for month in MONTHS if month not in valid_months_present]
    complete_12_months = valid_months_present == list(MONTHS) and not duplicate_months
    if not complete_12_months:
        blockers.add('incomplete_12_months')
        for month in missing_months:
            _add_missing(missing_paths, f'$.months[month={month}]')
        for month in sorted(duplicate_months):
            _add_invalid(invalid_paths, f'$.months[month={month}]')

    comparison_targets = payload.get('comparison_targets') if isinstance(payload, dict) else None
    comparison_targets_present = isinstance(comparison_targets, dict) and any(comparison_targets.values())
    ready_for_db_writer = complete_12_months and not blockers

    return {
        'schema_version': CONTROLLED_PACKAGE_READINESS_SCHEMA_VERSION,
        'input_schema_version': input_schema_version,
        'package_schema_version': package.get('schema_version'),
        'company_ref': package.get('company_ref', ''),
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'ready_for_db_writer': ready_for_db_writer,
        'ready_for_annual_generation': ready_for_db_writer,
        'ready_for_mirror_comparison': ready_for_db_writer and comparison_targets_present,
        'blockers': sorted(blockers),
        'warnings': warnings,
        'missing_value_paths': missing_paths,
        'invalid_paths': invalid_paths,
        'summary': {
            'complete_12_months': complete_12_months,
            'months_present': valid_months_present,
            'missing_months': missing_months,
            'missing_paths_count': len(missing_paths),
            'invalid_paths_count': len(invalid_paths),
            'comparison_targets_present': comparison_targets_present,
        },
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
        },
    }


def load_package_readiness_json(raw: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('El JSON debe ser un objeto.')
    return payload
