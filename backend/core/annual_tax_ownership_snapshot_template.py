from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from core.annual_tax_ownership_candidate_review import OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION
from core.annual_tax_source_manifest import payload_hash


OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION = 'annual-tax-ownership-snapshot-template.v1'


def _reviewable_candidates(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in review.get('review_items') or []
        if isinstance(item, dict)
        and item.get('review_status')
        in {
            'candidate_for_controlled_snapshot_review',
            'manual_review_required_legal_candidate',
        }
    ]


def _candidate_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        'path_ref': str(item.get('path_ref') or ''),
        'sha256': str(item.get('sha256') or ''),
        'document_kind': str(item.get('document_kind') or ''),
        'review_status': str(item.get('review_status') or ''),
        'path_context_tags': list(item.get('path_context_tags') or []),
        'evidence_ref_suggestion': f"ownership-evidence-{str(item.get('sha256') or '')[:12]}",
        'requires_ocr_or_manual_read': item.get('review_status') == 'manual_review_required_legal_candidate',
    }


def build_annual_tax_ownership_snapshot_template(
    *,
    review: dict[str, Any],
    company_ref: str,
    commercial_year: int,
    tax_year: int | None = None,
    responsible_ref: str = 'codex-local-review',
    approval_ref: str = '',
) -> dict[str, Any]:
    if review.get('schema_version') != OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION:
        raise ValueError(f'review.schema_version debe ser {OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION}.')
    tax_year = tax_year or commercial_year + 1
    candidates = _reviewable_candidates(review)
    review_hash = payload_hash(
        {
            'schema_version': review.get('schema_version'),
            'company_ref': review.get('company_ref'),
            'commercial_year': review.get('commercial_year'),
            'tax_year': review.get('tax_year'),
            'summary': review.get('summary', {}),
            'decision': review.get('decision', {}),
            'review_items': [
                {
                    'path_ref': item.get('path_ref'),
                    'sha256': item.get('sha256'),
                    'document_kind': item.get('document_kind'),
                    'review_status': item.get('review_status'),
                }
                for item in review.get('review_items') or []
                if isinstance(item, dict)
            ],
        }
    )
    return {
        'schema_version': OWNERSHIP_SNAPSHOT_TEMPLATE_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_review_hash': review_hash,
        'responsible_ref': responsible_ref,
        'approval_ref': approval_ref,
        'safety': {
            'writes_database': False,
            'copies_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'stores_raw_text': False,
            'stores_rut_values': False,
            'stores_person_names': False,
            'auto_generates_socios_or_percentages': False,
            'ready_for_controlled_db_load': False,
        },
        'candidate_sources': [_candidate_payload(item) for item in candidates],
        'ownership_patch_template': {
            'source_ref': f'ownership-review-{commercial_year}-controlled',
            'as_of': f'{commercial_year}-12-31',
            'participants': [],
        },
        'participant_template': {
            'participant_type': 'socio',
            'participant_ref': '',
            'name': '',
            'rut': '',
            'percentage': '',
            'vigente_desde': f'{commercial_year}-01-01',
            'vigente_hasta': None,
            'evidence_ref': '',
        },
        'validation_rules': [
            'Completar participantes solo desde fuente legal revisada/OCR o decision responsable.',
            'Usar RUT valido y nombre legal del socio; no guardar RUT/nombre en evidencia markdown.',
            'La suma de percentage debe ser 100.00.',
            f'ownership.as_of debe pertenecer a {commercial_year}.',
            'Cada participant.evidence_ref debe apuntar a evidencia no sensible.',
            'No usar F22/DDJJ/RLI/CPT/RAI finales para inferir socios o porcentajes.',
        ],
        'decision': {
            'can_patch_controlled_db_load_package_after_manual_completion': bool(candidates),
            'ready_for_controlled_db_load': False,
            'reason': (
                'Template listo para completar manualmente desde candidatos legales revisables; '
                'aun no contiene participantes ni porcentajes.'
            )
            if candidates
            else 'No hay candidatos revisables para construir ownership.',
        },
    }
