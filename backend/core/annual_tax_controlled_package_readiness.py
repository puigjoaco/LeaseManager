from __future__ import annotations

from datetime import date
import json
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError

from core.annual_tax_controlled_db_load import (
    CONTROLLED_DB_LOAD_SCHEMA_VERSION,
    FORBIDDEN_EXPECTED_OUTPUT_KEYS,
)
from core.annual_tax_controlled_package_template import (
    CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
    CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
)
from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from patrimonio.validators import validate_rut


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


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _date_value(value: Any) -> date | None:
    if value in (None, ''):
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _normalized_rut(value: Any) -> str | None:
    try:
        return validate_rut(str(value or '').strip())
    except ValidationError:
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


def _validate_ownership_for_annual_generation(
    *,
    package: dict[str, Any],
    commercial_year: int,
    missing_paths: list[str],
    invalid_paths: list[str],
    blockers: set[str],
) -> dict[str, Any]:
    ownership = package.get('ownership')
    if not isinstance(ownership, dict) or not ownership:
        blockers.add('ownership_snapshot_missing')
        _add_missing(missing_paths, '$.ownership')
        return {'present': False, 'participants_count': 0}

    if not _non_sensitive_text(ownership.get('source_ref')):
        blockers.add('ownership_snapshot_invalid')
        _add_missing(missing_paths, '$.ownership.source_ref')
    as_of = _date_value(ownership.get('as_of'))
    if as_of is None:
        blockers.add('ownership_snapshot_invalid')
        _add_missing(missing_paths, '$.ownership.as_of')
    elif commercial_year >= 2000 and as_of.year != commercial_year:
        blockers.add('ownership_snapshot_invalid')
        _add_invalid(invalid_paths, '$.ownership.as_of')

    participants = ownership.get('participants')
    if not isinstance(participants, list) or not participants:
        blockers.add('ownership_snapshot_missing')
        _add_missing(missing_paths, '$.ownership.participants')
        return {'present': True, 'participants_count': 0}

    period_start = date(commercial_year, 1, 1) if commercial_year >= 2000 else None
    period_end = date(commercial_year, 12, 31) if commercial_year >= 2000 else None
    total_percentage = Decimal('0.00')
    seen_ruts: set[str] = set()
    valid_participants = 0
    for index, participant in enumerate(participants):
        participant_path = f'$.ownership.participants[{index}]'
        if not isinstance(participant, dict):
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, participant_path)
            continue
        if str(participant.get('participant_type') or 'socio').strip().lower() != 'socio':
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, f'{participant_path}.participant_type')
        for field_name in ('participant_ref', 'evidence_ref'):
            if not _non_sensitive_text(participant.get(field_name)):
                blockers.add('ownership_snapshot_invalid')
                _add_missing(missing_paths, f'{participant_path}.{field_name}')
        if not str(participant.get('name') or '').strip():
            blockers.add('ownership_snapshot_invalid')
            _add_missing(missing_paths, f'{participant_path}.name')
        rut = _normalized_rut(participant.get('rut'))
        if rut is None:
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, f'{participant_path}.rut')
        elif rut in seen_ruts:
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, f'{participant_path}.rut')
        else:
            seen_ruts.add(rut)
        percentage = _decimal(participant.get('percentage'))
        if percentage is None or percentage <= Decimal('0.00') or percentage > Decimal('100.00'):
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, f'{participant_path}.percentage')
        else:
            total_percentage += percentage
        starts_on = _date_value(participant.get('vigente_desde') or (period_start.isoformat() if period_start else None))
        raw_ends_on = participant.get('vigente_hasta')
        ends_on = _date_value(raw_ends_on)
        if starts_on is None:
            blockers.add('ownership_snapshot_invalid')
            _add_missing(missing_paths, f'{participant_path}.vigente_desde')
        elif raw_ends_on not in (None, '') and ends_on is None:
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, f'{participant_path}.vigente_hasta')
        elif ends_on and ends_on < starts_on:
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, f'{participant_path}.vigente_hasta')
        elif period_start and period_end and (starts_on > period_end or (ends_on and ends_on < period_start)):
            blockers.add('ownership_snapshot_invalid')
            _add_invalid(invalid_paths, participant_path)
        valid_participants += 1

    if total_percentage != Decimal('100.00'):
        blockers.add('ownership_snapshot_invalid')
        _add_invalid(invalid_paths, '$.ownership.participants')
    return {'present': True, 'participants_count': valid_participants}


def _ownership_review_handoff_summary(package: dict[str, Any], warnings: list[str]) -> dict[str, Any]:
    review = package.get('ownership_review')
    if review in (None, {}):
        return {'present': False}
    if not isinstance(review, dict):
        warning = 'ownership_review_handoff_invalid'
        if warning not in warnings:
            warnings.append(warning)
        return {'present': True, 'valid': False}

    valid = review.get('schema_version') == CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION
    if not valid:
        warning = 'ownership_review_handoff_invalid'
        if warning not in warnings:
            warnings.append(warning)

    ready_for_controlled_db_load = bool(review.get('ready_for_controlled_db_load'))
    if ready_for_controlled_db_load and not isinstance(package.get('ownership'), dict):
        warning = 'ownership_review_ready_requires_package_ownership'
        if warning not in warnings:
            warnings.append(warning)

    return {
        'present': True,
        'valid': valid,
        'source_checklist_hash_present': bool(str(review.get('source_checklist_hash') or '').strip()),
        'reviewable_candidates_total': _int_value(review.get('reviewable_candidates_total')),
        'rendered_candidates_total': _int_value(review.get('rendered_candidates_total')),
        'validation_present': bool(review.get('validation_present')),
        'participants_count': _int_value(review.get('participants_count')),
        'blocking_items_total': _int_value(review.get('blocking_items_total')),
        'validation_blockers': list(review.get('validation_blockers') or []),
        'ready_for_manual_review': bool(review.get('ready_for_manual_review')),
        'ready_for_controlled_db_load': ready_for_controlled_db_load,
        'can_inject_ownership_into_controlled_package': bool(
            review.get('can_inject_ownership_into_controlled_package')
        ),
        'next_action': str(review.get('next_action') or ''),
        'replaces_ownership_snapshot': False,
    }


def _validate_labor_previsional_source(
    *,
    package: dict[str, Any],
    missing_paths: list[str],
    invalid_paths: list[str],
    blockers: set[str],
) -> dict[str, Any]:
    labor = package.get('labor_previsional')
    if labor in (None, {}):
        return {'present': False, 'required': False, 'required_by_ddjj_forms': []}
    if not isinstance(labor, dict):
        blockers.add('labor_previsional_source_invalid')
        _add_invalid(invalid_paths, '$.labor_previsional')
        return {'present': False, 'required': False, 'required_by_ddjj_forms': []}

    required = labor.get('required') is True
    forms = [
        str(form or '').strip()
        for form in (labor.get('required_by_ddjj_forms') or [])
        if str(form or '').strip()
    ]
    if required:
        if '1887' not in forms:
            blockers.add('labor_previsional_source_invalid')
            _add_invalid(invalid_paths, '$.labor_previsional.required_by_ddjj_forms')
        if not _non_sensitive_text(labor.get('source_ref')):
            blockers.add('labor_previsional_source_missing')
            _add_missing(missing_paths, '$.labor_previsional.source_ref')
    elif labor.get('source_ref') not in (None, '') and not _non_sensitive_text(labor.get('source_ref')):
        blockers.add('labor_previsional_source_invalid')
        _add_invalid(invalid_paths, '$.labor_previsional.source_ref')

    return {
        'present': True,
        'required': required,
        'required_by_ddjj_forms': forms,
        'source_ref_present': _non_sensitive_text(labor.get('source_ref')),
        'monthly_support_months': labor.get('monthly_support_months') or [],
        'source_refs_count': len(labor.get('source_refs') or []) if isinstance(labor.get('source_refs'), list) else 0,
    }


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
    annual_generation_missing_paths: list[str] = []
    annual_generation_invalid_paths: list[str] = []
    annual_generation_blockers: set[str] = set()
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
    ownership_summary = _validate_ownership_for_annual_generation(
        package=package,
        commercial_year=commercial_year,
        missing_paths=annual_generation_missing_paths,
        invalid_paths=annual_generation_invalid_paths,
        blockers=annual_generation_blockers,
    )
    labor_previsional_summary = _validate_labor_previsional_source(
        package=package,
        missing_paths=missing_paths,
        invalid_paths=invalid_paths,
        blockers=blockers,
    )
    ownership_review_summary = _ownership_review_handoff_summary(package, warnings)

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
    ready_for_annual_generation = ready_for_db_writer and not annual_generation_blockers

    return {
        'schema_version': CONTROLLED_PACKAGE_READINESS_SCHEMA_VERSION,
        'input_schema_version': input_schema_version,
        'package_schema_version': package.get('schema_version'),
        'company_ref': package.get('company_ref', ''),
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'ready_for_db_writer': ready_for_db_writer,
        'ready_for_annual_generation': ready_for_annual_generation,
        'ready_for_mirror_comparison': ready_for_annual_generation and comparison_targets_present,
        'blockers': sorted(blockers),
        'annual_generation_blockers': sorted(annual_generation_blockers),
        'warnings': warnings,
        'missing_value_paths': missing_paths,
        'invalid_paths': invalid_paths,
        'annual_generation_missing_paths': annual_generation_missing_paths,
        'annual_generation_invalid_paths': annual_generation_invalid_paths,
        'summary': {
            'complete_12_months': complete_12_months,
            'months_present': valid_months_present,
            'missing_months': missing_months,
            'missing_paths_count': len(missing_paths),
            'invalid_paths_count': len(invalid_paths),
            'annual_generation_missing_paths_count': len(annual_generation_missing_paths),
            'annual_generation_invalid_paths_count': len(annual_generation_invalid_paths),
            'comparison_targets_present': comparison_targets_present,
            'ownership_snapshot': ownership_summary,
            'ownership_review_handoff': ownership_review_summary,
            'labor_previsional_source': labor_previsional_summary,
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
