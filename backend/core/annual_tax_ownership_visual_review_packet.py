from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.annual_tax_ownership_candidate_review import OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION
from core.annual_tax_source_manifest import payload_hash


OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION = 'annual-tax-ownership-visual-review-packet.v1'
REVIEWABLE_STATUSES = {
    'candidate_for_controlled_snapshot_review',
    'manual_review_required_legal_candidate',
}


def _manifest_by_path_ref(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get('path_ref') or ''): item
        for item in manifest.get('files') or []
        if isinstance(item, dict) and item.get('path_ref')
    }


def _reviewable_candidates(review: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in review.get('review_items') or []
        if isinstance(item, dict) and item.get('review_status') in REVIEWABLE_STATUSES
    ]


def _source_path(source_root: Path, manifest_item: dict[str, Any]) -> Path:
    relative_path = str(manifest_item.get('relative_path') or '').strip()
    if not relative_path:
        raise ValueError('Candidato visual sin relative_path en manifiesto.')
    path = (source_root / relative_path).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError as error:
        raise ValueError('relative_path escapa del source_root controlado.') from error
    if not path.exists() or not path.is_file():
        raise ValueError('No existe candidato visual controlado.')
    return path


def _safe_id(path_ref: str, index: int) -> str:
    digest = hashlib.sha256(path_ref.encode('utf-8')).hexdigest()[:12]
    return f'candidate-{index:02d}-{digest}'


def _render_pdf_pages(
    *,
    source_path: Path,
    output_dir: Path,
    safe_id: str,
    max_pages: int,
    resolution: int,
) -> list[dict[str, Any]]:
    if max_pages < 1:
        raise ValueError('max_pages debe ser mayor o igual a 1.')
    if resolution < 72 or resolution > 300:
        raise ValueError('resolution debe estar entre 72 y 300 dpi.')

    with tempfile.TemporaryDirectory(prefix='lm-ownership-render-') as temp_dir:
        temp_root = Path(temp_dir)
        temp_pdf = temp_root / 'source.pdf'
        shutil.copyfile(source_path, temp_pdf)
        prefix = temp_root / 'page'
        command = [
            'pdftoppm',
            '-png',
            '-f',
            '1',
            '-l',
            str(max_pages),
            '-r',
            str(resolution),
            str(temp_pdf),
            str(prefix),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError('No se pudo renderizar PDF candidato con pdftoppm.') from error

        rendered = []
        for page_index, png_path in enumerate(sorted(temp_root.glob('page-*.png')), start=1):
            target_name = f'{safe_id}-page-{page_index:02d}.png'
            target_path = output_dir / target_name
            shutil.move(str(png_path), target_path)
            data = target_path.read_bytes()
            rendered.append(
                {
                    'page': page_index,
                    'file_name': target_name,
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'size_bytes': len(data),
                }
            )
    return rendered


def build_annual_tax_ownership_visual_review_packet(
    *,
    manifest: dict[str, Any],
    review: dict[str, Any],
    source_root: Path,
    output_dir: Path,
    company_ref: str,
    commercial_year: int,
    tax_year: int | None = None,
    max_pages_per_candidate: int = 2,
    resolution: int = 150,
) -> dict[str, Any]:
    if review.get('schema_version') != OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION:
        raise ValueError(f'review.schema_version debe ser {OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION}.')
    source_root = source_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f'source_root does not exist or is not a directory: {source_root}')
    output_dir.mkdir(parents=True, exist_ok=True)
    tax_year = tax_year or commercial_year + 1
    manifest_index = _manifest_by_path_ref(manifest)
    candidates = _reviewable_candidates(review)
    items = []
    render_errors = []
    for index, item in enumerate(candidates, start=1):
        path_ref = str(item.get('path_ref') or '')
        manifest_item = manifest_index.get(path_ref)
        safe_id = _safe_id(path_ref, index)
        base_payload = {
            'candidate_id': safe_id,
            'path_ref': path_ref,
            'source_sha256': str(item.get('sha256') or ''),
            'document_kind': str(item.get('document_kind') or ''),
            'review_status': str(item.get('review_status') or ''),
            'path_context_tags': list(item.get('path_context_tags') or []),
        }
        if not manifest_item:
            render_errors.append({**base_payload, 'error_ref': 'manifest_item_missing'})
            continue
        try:
            source_path = _source_path(source_root, manifest_item)
            if source_path.suffix.lower() != '.pdf':
                render_errors.append({**base_payload, 'error_ref': 'non_pdf_candidate'})
                continue
            pages = _render_pdf_pages(
                source_path=source_path,
                output_dir=output_dir,
                safe_id=safe_id,
                max_pages=max_pages_per_candidate,
                resolution=resolution,
            )
        except ValueError as error:
            render_errors.append(
                {
                    **base_payload,
                    'error_ref': hashlib.sha256(str(error).encode('utf-8')).hexdigest(),
                }
            )
            continue
        items.append({**base_payload, 'rendered_pages': pages})

    rendered_pages_total = sum(len(item.get('rendered_pages') or []) for item in items)
    source_payload = {
        'manifest_schema_version': manifest.get('schema_version', ''),
        'manifest_source_root_ref': manifest.get('source_root_ref', ''),
        'review_schema_version': review.get('schema_version', ''),
        'review_summary': review.get('summary', {}),
    }
    return {
        'schema_version': OWNERSHIP_VISUAL_REVIEW_PACKET_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_hash': payload_hash(source_payload),
        'render_settings': {
            'max_pages_per_candidate': max_pages_per_candidate,
            'resolution': resolution,
        },
        'safety': {
            'writes_database': False,
            'copies_source_files_persistently': False,
            'stores_raw_text': False,
            'stores_rut_values': False,
            'stores_person_names': False,
            'rendered_images_may_contain_sensitive_data': True,
            'output_must_remain_under_local_evidence': True,
        },
        'summary': {
            'reviewable_candidates_total': len(candidates),
            'rendered_candidates_total': len(items),
            'rendered_pages_total': rendered_pages_total,
            'render_errors_total': len(render_errors),
            'ready_for_manual_visual_review': rendered_pages_total > 0,
            'ready_for_controlled_db_load': False,
        },
        'items': items,
        'render_errors': render_errors,
        'next_actions': [
            'Revisar/OCR localmente las imagenes renderizadas bajo local-evidence.',
            'Completar annual_tax_ownership_snapshot_template con socios/participaciones solo desde evidencia suficiente.',
            'Validar que ownership.participants sume 100.00 antes del writer anual.',
        ],
    }
