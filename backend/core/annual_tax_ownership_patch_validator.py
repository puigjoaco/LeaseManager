from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError

from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from patrimonio.validators import validate_rut


OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION = 'annual-tax-ownership-controlled-patch.v1'
OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION = 'annual-tax-ownership-patch-validation.v1'


def _date_value(value: Any) -> date | None:
    if value in (None, ''):
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _decimal_value(value: Any) -> Decimal | None:
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _normalized_rut(value: Any) -> str | None:
    try:
        return validate_rut(str(value or '').strip())
    except ValidationError:
        return None


def _non_sensitive_text(value: Any) -> bool:
    return is_non_sensitive_reference(value)


def _add_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _hash_value(value: Any) -> str:
    text = str(value or '').strip()
    return payload_hash(text) if _non_sensitive_text(text) else ''


def _extract_ownership(patch: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(patch.get('ownership'), dict):
        return patch['ownership']
    if {'source_ref', 'as_of', 'participants'}.intersection(patch.keys()):
        return patch
    return None


def _redacted_participant(
    *,
    participant: dict[str, Any],
    index: int,
    commercial_year: int,
    blockers: set[str],
    missing_paths: list[str],
    invalid_paths: list[str],
    seen_ruts: set[str],
) -> tuple[dict[str, Any], Decimal]:
    participant_path = f'$.ownership.participants[{index}]'
    period_start = date(commercial_year, 1, 1)
    period_end = date(commercial_year, 12, 31)

    participant_type = str(participant.get('participant_type') or 'socio').strip().lower()
    participant_ref = str(participant.get('participant_ref') or '').strip()
    evidence_ref = str(participant.get('evidence_ref') or '').strip()
    name_present = bool(str(participant.get('name') or '').strip())
    rut = _normalized_rut(participant.get('rut'))
    raw_rut_present = bool(str(participant.get('rut') or '').strip())
    percentage = _decimal_value(participant.get('percentage'))
    starts_on = _date_value(participant.get('vigente_desde') or period_start.isoformat())
    raw_ends_on = participant.get('vigente_hasta')
    ends_on = _date_value(raw_ends_on)

    if participant_type != 'socio':
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, f'{participant_path}.participant_type')
    if not _non_sensitive_text(participant_ref):
        blockers.add('ownership_patch_invalid')
        _add_once(missing_paths, f'{participant_path}.participant_ref')
    if not _non_sensitive_text(evidence_ref):
        blockers.add('ownership_patch_invalid')
        _add_once(missing_paths, f'{participant_path}.evidence_ref')
    if not name_present:
        blockers.add('ownership_patch_invalid')
        _add_once(missing_paths, f'{participant_path}.name')
    if rut is None:
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, f'{participant_path}.rut')
    elif rut in seen_ruts:
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, f'{participant_path}.rut')
    else:
        seen_ruts.add(rut)
    if percentage is None or percentage <= Decimal('0.00') or percentage > Decimal('100.00'):
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, f'{participant_path}.percentage')
        percentage = Decimal('0.00')
    if starts_on is None:
        blockers.add('ownership_patch_invalid')
        _add_once(missing_paths, f'{participant_path}.vigente_desde')
    elif raw_ends_on not in (None, '') and ends_on is None:
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, f'{participant_path}.vigente_hasta')
    elif ends_on and ends_on < starts_on:
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, f'{participant_path}.vigente_hasta')
    elif starts_on > period_end or (ends_on and ends_on < period_start):
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, participant_path)

    participant_summary = {
        'index': index,
        'participant_type': participant_type,
        'participant_ref_present': bool(participant_ref),
        'participant_ref_hash': _hash_value(participant_ref),
        'evidence_ref_present': bool(evidence_ref),
        'evidence_ref_hash': _hash_value(evidence_ref),
        'name_present': name_present,
        'rut_present': raw_rut_present,
        'rut_valid': rut is not None,
        'percentage': f'{percentage:.2f}',
        'vigente_desde': starts_on.isoformat() if starts_on else '',
        'vigente_hasta': ends_on.isoformat() if ends_on else None,
        'overlaps_commercial_year': bool(
            starts_on and starts_on <= period_end and not (ends_on and ends_on < period_start)
        ),
    }
    return participant_summary, percentage


def validate_annual_tax_ownership_patch(*, template: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(template, dict):
        raise ValueError('template debe ser un objeto JSON.')
    if not isinstance(patch, dict):
        raise ValueError('patch debe ser un objeto JSON.')
    if template.get('schema_version') != OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION:
        raise ValueError(f'template.schema_version debe ser {OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION}.')

    missing_paths: list[str] = []
    invalid_paths: list[str] = []
    blockers: set[str] = set()
    warnings: list[str] = []

    schema_version = str(patch.get('schema_version') or '').strip()
    if schema_version and schema_version != OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION:
        blockers.add('ownership_patch_schema_invalid')
        _add_once(invalid_paths, '$.schema_version')

    company_ref = str(patch.get('company_ref') or template.get('company_ref') or '').strip()
    commercial_year = int(patch.get('commercial_year') or template.get('commercial_year') or 0)
    tax_year = int(patch.get('tax_year') or template.get('tax_year') or 0)

    if company_ref != str(template.get('company_ref') or '').strip():
        blockers.add('ownership_patch_context_mismatch')
        _add_once(invalid_paths, '$.company_ref')
    if commercial_year != int(template.get('commercial_year') or 0):
        blockers.add('ownership_patch_context_mismatch')
        _add_once(invalid_paths, '$.commercial_year')
    if tax_year != int(template.get('tax_year') or 0):
        blockers.add('ownership_patch_context_mismatch')
        _add_once(invalid_paths, '$.tax_year')
    if commercial_year < 2000 or tax_year != commercial_year + 1:
        blockers.add('ownership_patch_context_invalid')
        _add_once(invalid_paths, '$.commercial_year')
        _add_once(invalid_paths, '$.tax_year')

    candidate_sources = template.get('candidate_sources')
    if not isinstance(candidate_sources, list) or not candidate_sources:
        blockers.add('ownership_template_without_reviewable_candidates')
        _add_once(missing_paths, '$.candidate_sources')

    for field_name in ('responsible_ref', 'approval_ref'):
        value = patch.get(field_name) or template.get(field_name)
        if value not in (None, '') and not _non_sensitive_text(value):
            blockers.add('ownership_patch_sensitive_reference')
            _add_once(invalid_paths, f'$.{field_name}')

    ownership = _extract_ownership(patch)
    if not isinstance(ownership, dict):
        blockers.add('ownership_patch_missing')
        _add_once(missing_paths, '$.ownership')
        ownership = {}

    if contains_sensitive_reference(ownership, include_sensitive_keys=True, allowed_sensitive_keys={'rut'}):
        blockers.add('ownership_patch_sensitive_reference')
        _add_once(invalid_paths, '$.ownership')

    source_ref = str(ownership.get('source_ref') or '').strip()
    if not _non_sensitive_text(source_ref):
        blockers.add('ownership_patch_invalid')
        _add_once(missing_paths, '$.ownership.source_ref')

    as_of = _date_value(ownership.get('as_of'))
    if as_of is None:
        blockers.add('ownership_patch_invalid')
        _add_once(missing_paths, '$.ownership.as_of')
    elif commercial_year >= 2000 and as_of.year != commercial_year:
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, '$.ownership.as_of')

    participants = ownership.get('participants')
    redacted_participants: list[dict[str, Any]] = []
    total_percentage = Decimal('0.00')
    seen_ruts: set[str] = set()
    if not isinstance(participants, list) or not participants:
        blockers.add('ownership_patch_missing')
        _add_once(missing_paths, '$.ownership.participants')
        participants = []

    for index, participant in enumerate(participants):
        participant_path = f'$.ownership.participants[{index}]'
        if not isinstance(participant, dict):
            blockers.add('ownership_patch_invalid')
            _add_once(invalid_paths, participant_path)
            continue
        summary, percentage = _redacted_participant(
            participant=participant,
            index=index,
            commercial_year=commercial_year,
            blockers=blockers,
            missing_paths=missing_paths,
            invalid_paths=invalid_paths,
            seen_ruts=seen_ruts,
        )
        redacted_participants.append(summary)
        total_percentage += percentage

    if participants and total_percentage != Decimal('100.00'):
        blockers.add('ownership_patch_invalid')
        _add_once(invalid_paths, '$.ownership.participants')

    redacted_patch_fingerprint_payload = {
        'schema_version': schema_version or OWNERSHIP_CONTROLLED_PATCH_SCHEMA_VERSION,
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_ref_hash': _hash_value(source_ref),
        'as_of': as_of.isoformat() if as_of else '',
        'participants': redacted_participants,
    }
    ready = not blockers
    if not ready and not redacted_participants:
        _add_once(warnings, 'ownership_patch_pending_manual_completion')

    return {
        'schema_version': OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'input_schema_version': schema_version or 'ownership-object',
        'template_schema_version': template.get('schema_version'),
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'template_hash': payload_hash(
            {
                'schema_version': template.get('schema_version'),
                'company_ref': template.get('company_ref'),
                'commercial_year': template.get('commercial_year'),
                'tax_year': template.get('tax_year'),
                'source_review_hash': template.get('source_review_hash'),
                'candidate_sources': template.get('candidate_sources'),
            }
        ),
        'redacted_patch_hash': payload_hash(redacted_patch_fingerprint_payload),
        'ready_for_controlled_db_load': ready,
        'ready_for_annual_generation_patch': ready,
        'blockers': sorted(blockers),
        'warnings': warnings,
        'missing_paths': missing_paths,
        'invalid_paths': invalid_paths,
        'summary': {
            'template_candidates_count': len(candidate_sources) if isinstance(candidate_sources, list) else 0,
            'source_ref_present': bool(source_ref),
            'source_ref_hash': _hash_value(source_ref),
            'as_of': as_of.isoformat() if as_of else '',
            'participants_count': len(participants),
            'valid_participants_count': sum(
                1
                for item in redacted_participants
                if item['name_present'] and item['rut_valid'] and item['overlaps_commercial_year']
            ),
            'percentage_total': f'{total_percentage:.2f}',
            'percentage_total_is_100': total_percentage == Decimal('100.00'),
            'redacted_participants': redacted_participants,
        },
        'safety': {
            'writes_database': False,
            'copies_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'stores_raw_text': False,
            'stores_rut_values': False,
            'stores_person_names': False,
            'outputs_redacted': True,
            'validates_local_patch_only': True,
            'can_generate_controlled_snapshot_without_review': False,
        },
        'decision': {
            'can_inject_ownership_into_controlled_package': ready,
            'reason': (
                'Ownership patch local validado; puede inyectarse en el paquete controlado y reauditar readiness.'
                if ready
                else 'Ownership patch incompleto o invalido; corregir rutas indicadas antes de inyectarlo.'
            ),
            'next_actions': [
                'Inyectar ownership validado en package.ownership solo dentro de evidencia local/controlada.',
                'Ejecutar audit_annual_tax_controlled_package_readiness sobre el paquete con ownership.',
                'Aplicar writer y mirror anual solo en DB local/controlada, sin SII real ni calculo tributario final.',
            ]
            if ready
            else [
                'Completar participants desde OCR/revision legal controlada y aprobacion responsable.',
                'Mantener el patch con nombres/RUTs fuera de Git o bajo local-evidence/ ignorado.',
                'Reejecutar validate_annual_tax_ownership_patch hasta que quede ready.',
            ],
        },
    }
