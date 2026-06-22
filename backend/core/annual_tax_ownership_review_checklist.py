from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.annual_tax_ownership_patch_validator import OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION
from core.annual_tax_ownership_snapshot_template import OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION
from core.annual_tax_ownership_visual_review_packet import OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import is_non_sensitive_control_reference


OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION = 'annual-tax-ownership-review-checklist.v1'
OWNERSHIP_VISUAL_INDEX_SCHEMA_VERSION = 'ownership-visual-index.v1'


def _hash_value(value: Any) -> str:
    return payload_hash(str(value or '').strip())


def _required_control_ref(value: Any, *, field_name: str) -> str:
    text = str(value or '').strip()
    if not is_non_sensitive_control_reference(text):
        raise ValueError(f'{field_name} debe ser una referencia no sensible.')
    return text


def _optional_control_ref(value: Any, *, field_name: str) -> str:
    text = str(value or '').strip()
    if text and not is_non_sensitive_control_reference(text):
        raise ValueError(f'{field_name} debe ser una referencia no sensible.')
    return text


def _required_int(value: Any, *, field_name: str) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError) as error:
        raise ValueError(f'{field_name} debe ser numerico.') from error


def _candidate_key(candidate: dict[str, Any]) -> str:
    return _required_control_ref(candidate.get('path_ref'), field_name='candidate_sources[].path_ref')


def _validate_context(
    payload: dict[str, Any],
    *,
    payload_name: str,
    company_ref: str,
    commercial_year: int,
    tax_year: int,
) -> None:
    payload_company_ref = payload.get('company_ref')
    if payload_company_ref in (None, ''):
        raise ValueError(f'{payload_name}.company_ref debe ser una referencia no sensible.')
    if _required_control_ref(payload_company_ref, field_name=f'{payload_name}.company_ref') != company_ref:
        raise ValueError(f'{payload_name}.company_ref no coincide con template.company_ref.')
    payload_commercial_year = payload.get('commercial_year')
    if (
        payload_commercial_year not in (None, '')
        and _required_int(payload_commercial_year, field_name=f'{payload_name}.commercial_year') != commercial_year
    ):
        raise ValueError(f'{payload_name}.commercial_year no coincide con template.commercial_year.')
    payload_tax_year = payload.get('tax_year')
    if (
        payload_tax_year not in (None, '')
        and _required_int(payload_tax_year, field_name=f'{payload_name}.tax_year') != tax_year
    ):
        raise ValueError(f'{payload_name}.tax_year no coincide con template.tax_year.')


def _visual_index(visual_packet: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(visual_packet, dict):
        return {}
    if visual_packet.get('schema_version') == OWNERSHIP_VISUAL_INDEX_SCHEMA_VERSION:
        return {
            _required_control_ref(item.get('path_ref'), field_name='visual_packet.records[].path_ref'): {
                'rendered_pages': list(item.get('rendered_pages') or []),
            }
            for item in visual_packet.get('records') or []
            if isinstance(item, dict) and item.get('path_ref')
        }
    return {
        _required_control_ref(item.get('path_ref'), field_name='visual_packet.items[].path_ref'): item
        for item in visual_packet.get('items') or []
        if isinstance(item, dict) and item.get('path_ref')
    }


def _reviewable_candidates(
    *,
    template: dict[str, Any],
    visual_packet: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    visual_by_ref = _visual_index(visual_packet)
    candidates = []
    for index, candidate in enumerate(template.get('candidate_sources') or [], start=1):
        if not isinstance(candidate, dict):
            continue
        key = _candidate_key(candidate)
        evidence_ref_suggestion = _optional_control_ref(
            candidate.get('evidence_ref_suggestion'),
            field_name='candidate_sources[].evidence_ref_suggestion',
        )
        visual = visual_by_ref.get(key) or {}
        rendered_pages = visual.get('rendered_pages') if isinstance(visual, dict) else []
        candidates.append(
            {
                'index': index,
                'candidate_ref_hash': _hash_value(
                    {
                        'path_ref': candidate.get('path_ref', ''),
                        'sha256': candidate.get('sha256', ''),
                    }
                ),
                'document_kind': str(candidate.get('document_kind') or ''),
                'review_status': str(candidate.get('review_status') or ''),
                'path_context_tags': list(candidate.get('path_context_tags') or []),
                'evidence_ref_suggestion': evidence_ref_suggestion,
                'requires_ocr_or_manual_read': bool(candidate.get('requires_ocr_or_manual_read')),
                'rendered_pages_count': len(rendered_pages) if isinstance(rendered_pages, list) else 0,
                'ready_for_reviewer': bool(key),
            }
        )
    return candidates


def _validation_summary(validation: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(validation, dict):
        return {
            'validation_present': False,
            'ready_for_controlled_db_load': False,
            'blockers': ['ownership_patch_validation_missing'],
            'missing_paths': ['$.validation'],
            'invalid_paths': [],
            'participants_count': 0,
            'percentage_total': '0.00',
            'outputs_redacted': False,
        }
    if validation.get('schema_version') != OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION:
        raise ValueError(f'validation.schema_version debe ser {OWNERSHIP_PATCH_VALIDATION_SCHEMA_VERSION}.')
    summary = validation.get('summary') or {}
    safety = validation.get('safety') or {}
    return {
        'validation_present': True,
        'ready_for_controlled_db_load': bool(validation.get('ready_for_controlled_db_load')),
        'blockers': list(validation.get('blockers') or []),
        'missing_paths': list(validation.get('missing_paths') or []),
        'invalid_paths': list(validation.get('invalid_paths') or []),
        'participants_count': int(summary.get('participants_count') or 0),
        'percentage_total': str(summary.get('percentage_total') or '0.00'),
        'percentage_total_is_100': bool(summary.get('percentage_total_is_100')),
        'outputs_redacted': bool(safety.get('outputs_redacted')),
        'stores_rut_values': bool(safety.get('stores_rut_values')),
        'stores_person_names': bool(safety.get('stores_person_names')),
    }


def build_annual_tax_ownership_review_checklist(
    *,
    template: dict[str, Any],
    validation: dict[str, Any] | None = None,
    visual_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if template.get('schema_version') != OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION:
        raise ValueError(f'template.schema_version debe ser {OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION}.')
    company_ref = _required_control_ref(template.get('company_ref'), field_name='template.company_ref')
    commercial_year = _required_int(template.get('commercial_year'), field_name='template.commercial_year')
    tax_year = _required_int(template.get('tax_year'), field_name='template.tax_year')
    if (
        isinstance(visual_packet, dict)
        and visual_packet.get('schema_version')
        not in {OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION, OWNERSHIP_VISUAL_INDEX_SCHEMA_VERSION}
    ):
        raise ValueError(
            'visual_packet.schema_version debe ser '
            f'{OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION} o {OWNERSHIP_VISUAL_INDEX_SCHEMA_VERSION}.'
        )
    if isinstance(visual_packet, dict):
        _validate_context(
            visual_packet,
            payload_name='visual_packet',
            company_ref=company_ref,
            commercial_year=commercial_year,
            tax_year=tax_year,
        )
    if isinstance(validation, dict):
        _validate_context(
            validation,
            payload_name='validation',
            company_ref=company_ref,
            commercial_year=commercial_year,
            tax_year=tax_year,
        )

    candidates = _reviewable_candidates(template=template, visual_packet=visual_packet)
    validation_state = _validation_summary(validation)
    missing_paths = set(validation_state['missing_paths'])
    invalid_paths = set(validation_state['invalid_paths'])
    blockers = set(validation_state['blockers'])

    checklist_items = [
        {
            'key': 'candidate_sources_reviewed',
            'status': 'ready' if candidates else 'blocked',
            'blocking_paths': [] if candidates else ['$.candidate_sources'],
        },
        {
            'key': 'ownership_source_ref_non_sensitive',
            'status': 'pending'
            if '$.ownership.source_ref' in missing_paths or '$.ownership' in invalid_paths
            else 'ready',
            'blocking_paths': [
                path
                for path in ('$.ownership.source_ref', '$.ownership')
                if path in missing_paths or path in invalid_paths
            ],
        },
        {
            'key': 'ownership_as_of_confirmed',
            'status': 'pending' if '$.ownership.as_of' in missing_paths or '$.ownership.as_of' in invalid_paths else 'ready',
            'blocking_paths': [
                path
                for path in ('$.ownership.as_of',)
                if path in missing_paths or path in invalid_paths
            ],
        },
        {
            'key': 'participants_completed_from_legal_review',
            'status': 'pending'
            if '$.ownership.participants' in missing_paths or 'ownership_patch_missing' in blockers
            else 'ready',
            'blocking_paths': [
                path
                for path in ('$.ownership.participants',)
                if path in missing_paths or path in invalid_paths
            ],
        },
        {
            'key': 'participants_total_percentage_100',
            'status': 'ready' if validation_state.get('percentage_total_is_100') else 'pending',
            'blocking_paths': ['$.ownership.participants']
            if not validation_state.get('percentage_total_is_100')
            else [],
        },
        {
            'key': 'validation_output_redacted',
            'status': 'ready' if validation_state['outputs_redacted'] else 'pending',
            'blocking_paths': [] if validation_state['outputs_redacted'] else ['$.validation.safety.outputs_redacted'],
        },
    ]
    blocking_items = [item for item in checklist_items if item['status'] != 'ready']
    ready = bool(candidates) and not blocking_items and validation_state['ready_for_controlled_db_load']

    return {
        'schema_version': OWNERSHIP_REVIEW_CHECKLIST_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_template_hash': payload_hash(
            {
                'schema_version': template.get('schema_version'),
                'company_ref': company_ref,
                'commercial_year': commercial_year,
                'tax_year': tax_year,
                'source_review_hash': template.get('source_review_hash'),
                'candidate_sources': template.get('candidate_sources'),
            }
        ),
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'stores_raw_text': False,
            'stores_rut_values': False,
            'stores_person_names': False,
            'stores_source_paths': False,
            'auto_generates_socios_or_percentages': False,
            'ready_to_version_output': True,
        },
        'summary': {
            'reviewable_candidates_total': len(candidates),
            'rendered_candidates_total': sum(1 for item in candidates if item['rendered_pages_count'] > 0),
            'validation_present': validation_state['validation_present'],
            'participants_count': validation_state['participants_count'],
            'percentage_total': validation_state['percentage_total'],
            'blocking_items_total': len(blocking_items),
            'ready_for_manual_review': bool(candidates),
            'ready_for_controlled_db_load': ready,
            'ready_for_annual_generation_patch': ready,
        },
        'validation_summary': validation_state,
        'candidate_review_queue': candidates,
        'checklist_items': checklist_items,
        'decision': {
            'can_continue_manual_ownership_review': bool(candidates),
            'can_inject_ownership_into_controlled_package': ready,
            'reason': (
                'Patch ownership validado y checklist sin pendientes; puede inyectarse en package.ownership local/controlado.'
                if ready
                else 'Ownership sigue pendiente; completar checklist antes de inyectar package.ownership.'
            ),
            'next_actions': [
                'Revisar/OCR candidatos en la cola sin versionar nombres ni RUTs.',
                'Completar patch local bajo local-evidence/ con participantes y evidencia no sensible.',
                'Reejecutar validate_annual_tax_ownership_patch y este checklist hasta quedar ready.',
                'Inyectar ownership validado solo en paquete DB local/controlado y reauditar readiness.',
            ],
        },
    }
