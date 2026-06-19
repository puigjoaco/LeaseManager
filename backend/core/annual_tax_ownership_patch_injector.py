from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_readiness import audit_annual_tax_controlled_package_readiness
from core.annual_tax_controlled_package_template import (
    CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
    CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
)
from core.annual_tax_ownership_patch_validator import (
    OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
    validate_annual_tax_ownership_patch,
)


OWNERSHIP_PATCH_INJECTION_SCHEMA_VERSION = 'annual-tax-ownership-patch-injection.v1'


def _extract_package(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    schema_version = str(payload.get('schema_version') or '')
    if schema_version == CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION:
        package = payload.get('package_draft')
        if not isinstance(package, dict):
            raise ValueError('package_draft debe ser un objeto JSON.')
        comparison_targets = payload.get('comparison_targets') if isinstance(payload.get('comparison_targets'), dict) else None
        return deepcopy(package), deepcopy(comparison_targets), schema_version
    if schema_version != CONTROLLED_DB_LOAD_SCHEMA_VERSION:
        raise ValueError(
            f'package.schema_version debe ser {CONTROLLED_DB_LOAD_SCHEMA_VERSION} '
            f'o {CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION}.'
        )
    return deepcopy(payload), None, schema_version


def _extract_ownership(patch: dict[str, Any]) -> dict[str, Any]:
    ownership = patch.get('ownership') if isinstance(patch.get('ownership'), dict) else patch
    if not isinstance(ownership, dict):
        raise ValueError('patch ownership debe ser un objeto JSON.')
    return deepcopy(ownership)


def _context_matches(*, package: dict[str, Any], validation: dict[str, Any]) -> None:
    for field_name in ('company_ref', 'commercial_year', 'tax_year'):
        if str(package.get(field_name) or '') != str(validation.get(field_name) or ''):
            raise ValueError(f'El patch ownership validado no coincide con package.{field_name}.')


def _updated_ownership_review(
    *,
    existing_review: Any,
    validation: dict[str, Any],
) -> dict[str, Any]:
    review = deepcopy(existing_review) if isinstance(existing_review, dict) else {}
    review.update(
        {
            'schema_version': CONTROLLED_OWNERSHIP_REVIEW_HANDOFF_SCHEMA_VERSION,
            'validation_present': True,
            'participants_count': int((validation.get('summary') or {}).get('participants_count') or 0),
            'percentage_total': str((validation.get('summary') or {}).get('percentage_total') or '0.00'),
            'blocking_items_total': 0,
            'blocking_item_keys': [],
            'validation_blockers': [],
            'ready_for_manual_review': True,
            'ready_for_controlled_db_load': True,
            'can_inject_ownership_into_controlled_package': True,
            'next_action': 'package_ownership_injected_reaudit_readiness',
            'writes_database': False,
            'stores_source_paths': False,
            'stores_person_names': False,
            'stores_rut_values': False,
            'auto_generates_ownership': False,
            'redacted_patch_hash': validation.get('redacted_patch_hash', ''),
        }
    )
    return review


def inject_annual_tax_ownership_patch_into_controlled_package(
    *,
    package_payload: dict[str, Any],
    template: dict[str, Any],
    patch: dict[str, Any],
    replace_existing: bool = False,
) -> dict[str, Any]:
    if not isinstance(package_payload, dict):
        raise ValueError('package_payload debe ser un objeto JSON.')
    if not isinstance(template, dict):
        raise ValueError('template debe ser un objeto JSON.')
    if not isinstance(patch, dict):
        raise ValueError('patch debe ser un objeto JSON.')

    package, comparison_targets, input_schema_version = _extract_package(package_payload)
    if package.get('ownership') not in (None, {}) and not replace_existing:
        raise ValueError('package.ownership ya existe; use replace_existing solo con decision controlada.')

    validation = validate_annual_tax_ownership_patch(template=template, patch=patch)
    if not validation.get('ready_for_controlled_db_load'):
        blockers = ','.join(validation.get('blockers') or [])
        raise ValueError(f'Ownership patch no listo para inyectar: blockers={blockers}.')
    _context_matches(package=package, validation=validation)

    package['ownership'] = _extract_ownership(patch)
    package['ownership_review'] = _updated_ownership_review(
        existing_review=package.get('ownership_review'),
        validation=validation,
    )

    readiness_payload: dict[str, Any] = deepcopy(package)
    if comparison_targets is not None:
        readiness_payload = {
            'schema_version': CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION,
            'package_draft': deepcopy(package),
            'comparison_targets': comparison_targets,
        }
    readiness = audit_annual_tax_controlled_package_readiness(payload=readiness_payload)

    return {
        'schema_version': OWNERSHIP_PATCH_INJECTION_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'input_schema_version': input_schema_version,
        'package_schema_version': package.get('schema_version'),
        'ownership_patch_schema_version': str(patch.get('schema_version') or OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION),
        'company_ref': package.get('company_ref', ''),
        'commercial_year': package.get('commercial_year'),
        'tax_year': package.get('tax_year'),
        'validation': validation,
        'readiness': readiness,
        'package': package,
        'comparison_targets': comparison_targets or {},
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'opens_external_auth': False,
            'uses_expected_outputs_as_inputs': False,
            'validates_patch_before_injection': True,
            'output_contains_ownership_pii': True,
            'ready_to_version_output': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        },
        'summary': {
            'ownership_injected': True,
            'participants_count': int((validation.get('summary') or {}).get('participants_count') or 0),
            'ready_for_db_writer': bool(readiness.get('ready_for_db_writer')),
            'ready_for_annual_generation': bool(readiness.get('ready_for_annual_generation')),
            'annual_generation_blockers': list(readiness.get('annual_generation_blockers') or []),
            'blockers': list(readiness.get('blockers') or []),
        },
    }
