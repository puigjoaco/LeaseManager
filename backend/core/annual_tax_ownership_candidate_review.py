from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.annual_tax_source_manifest import payload_hash


OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION = 'annual-tax-ownership-candidate-review.v1'
TEXT_EXTENSIONS = {'.txt', '.csv', '.json', '.md', '.html', '.htm'}
RUT_PATTERN = re.compile(r'(?<!\d)\d{1,2}\.?\d{3}\.?\d{3}-[\dkK](?!\d)')
YEAR_PATTERN = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)')


def _normalize_for_match(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', value or '')
    ascii_value = ''.join(char for char in normalized if not unicodedata.combining(char))
    return ascii_value.lower().replace('\\', '/').replace(' ', '_').replace('-', '_')


def _extract_text(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return path.read_text(encoding='utf-8-sig', errors='replace')
    if path.suffix.lower() == '.pdf':
        return _extract_pdf_text(path)
    raise ValueError(f'Extension no soportada para revision ownership: {path.suffix}')


def _run_pdftotext(path: Path) -> str:
    command = ['pdftotext', '-layout', '-nopgbrk', str(path), '-']
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=60,
    )
    return completed.stdout


def _extract_pdf_text(path: Path) -> str:
    try:
        return _run_pdftotext(path)
    except (OSError, subprocess.SubprocessError):
        pass

    with tempfile.TemporaryDirectory(prefix='lm-ownership-pdf-') as temp_dir:
        short_path = Path(temp_dir) / f'source{path.suffix.lower()}'
        try:
            os.link(path, short_path)
        except OSError:
            try:
                short_path.symlink_to(path)
            except OSError as error:
                raise ValueError(f'No se pudo crear enlace temporal para PDF: {path.name}') from error
        try:
            return _run_pdftotext(short_path)
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError(f'No se pudo extraer texto PDF con pdftotext: {path.name}') from error


def _source_path(source_root: Path, item: dict[str, Any]) -> Path:
    relative_path = str(item.get('relative_path') or '').strip()
    if not relative_path:
        raise ValueError('Candidato ownership sin relative_path en manifiesto.')
    path = (source_root / relative_path).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError as error:
        raise ValueError('relative_path escapa del source_root controlado.') from error
    if not path.exists() or not path.is_file():
        raise ValueError(f'No existe candidato ownership controlado: {relative_path}')
    return path


def _document_kind(path: Path) -> str:
    normalized = _normalize_for_match(path.as_posix())
    if 'nula' in normalized:
        return 'void_modification_support'
    if 'aporte_inicial' in normalized or 'policentro' in normalized:
        return 'property_contribution_support'
    if 'constitucion' in normalized and 'escritura' in normalized:
        return 'constitution_deed'
    if 'constitucion' in normalized and 'inscripcion' in normalized:
        return 'constitution_registration'
    if 'constitucion' in normalized and 'extracto' in normalized:
        return 'constitution_extract'
    if 'diario_oficial' in normalized or 'publicacion_diario_oficial' in normalized:
        return 'official_gazette_publication'
    if 'transformacion' in normalized:
        return 'transformation_support'
    if 'modificacion' in normalized:
        return 'modification_support'
    return 'legal_support_candidate'


def _path_context_tags(path: Path) -> list[str]:
    normalized = _normalize_for_match(path.as_posix())
    tags = []
    for token, tag in (
        ('constitucion', 'constitution'),
        ('extracto', 'extract'),
        ('inscripcion', 'registration'),
        ('diario_oficial', 'official_gazette'),
        ('modificacion', 'modification'),
        ('transformacion', 'transformation'),
        ('aporte_inicial', 'initial_contribution'),
        ('nula', 'void_or_superseded'),
    ):
        if token in normalized:
            tags.append(tag)
    return tags


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _signals(text: str, path: Path) -> dict[str, Any]:
    normalized_text = _normalize_for_match(text)
    normalized_path = _normalize_for_match(path.as_posix())
    years = sorted({int(match) for match in YEAR_PATTERN.findall(text)})
    return {
        'text_extractable': True,
        'text_sha256': hashlib.sha256(text.encode('utf-8', errors='replace')).hexdigest(),
        'text_chars': len(text),
        'rut_like_tokens_count': len(RUT_PATTERN.findall(text)),
        'years_detected': years,
        'company_ref_mentioned': _contains_any(
            f'{normalized_path}\n{normalized_text}',
            ('inmobiliaria_puig', 'puig_spa', 'puig_s_p_a', 'puig_sociedad_por_acciones'),
        ),
        'spa_or_society_mentioned': _contains_any(
            normalized_text,
            ('sociedad_por_acciones', '_spa', 's.p.a', 'sociedad', 'sociedades'),
        ),
        'capital_mentioned': _contains_any(
            normalized_text,
            ('capital', 'capital_social', 'aporte_de_capital', 'aportes_de_capital'),
        ),
        'shares_or_participation_mentioned': _contains_any(
            normalized_text,
            ('accion', 'acciones', 'accionista', 'accionistas', 'participacion', 'participaciones', 'derechos_sociales'),
        ),
        'percentages_mentioned': '%' in text or 'por_ciento' in normalized_text,
        'modification_mentioned': _contains_any(normalized_text, ('modificacion', 'transformacion', 'reforma')),
        'void_or_superseded_mentioned': _contains_any(normalized_text, ('nula', 'anulada', 'sin_efecto')),
    }


def _classification(*, document_kind: str, signals: dict[str, Any]) -> dict[str, Any]:
    if document_kind == 'void_modification_support' or signals.get('void_or_superseded_mentioned'):
        return {
            'review_status': 'excluded_void_or_superseded',
            'can_seed_controlled_snapshot': False,
            'can_generate_controlled_snapshot_without_review': False,
            'reason': 'Documento marcado como nulo, anulado o sin efecto.',
        }
    if document_kind == 'property_contribution_support':
        return {
            'review_status': 'support_only_property_contribution',
            'can_seed_controlled_snapshot': False,
            'can_generate_controlled_snapshot_without_review': False,
            'reason': 'Aporte o respaldo de propiedad; no prueba por si solo socios/porcentajes vigentes.',
        }
    if signals.get('company_ref_mentioned') and (
        signals.get('shares_or_participation_mentioned') or signals.get('capital_mentioned')
    ):
        return {
            'review_status': 'candidate_for_controlled_snapshot_review',
            'can_seed_controlled_snapshot': True,
            'can_generate_controlled_snapshot_without_review': False,
            'reason': 'Contiene senales societarias utiles, pero requiere revision de vigencia y extraccion controlada.',
        }
    return {
        'review_status': 'support_only_not_enough_for_ownership',
        'can_seed_controlled_snapshot': False,
        'can_generate_controlled_snapshot_without_review': False,
        'reason': 'No contiene senales suficientes para construir ownership controlado.',
    }


def _path_only_classification(document_kind: str, *, empty_text_layer: bool = False) -> dict[str, Any]:
    if document_kind == 'void_modification_support':
        return {
            'review_status': 'excluded_void_or_superseded',
            'can_seed_controlled_snapshot': False,
            'can_generate_controlled_snapshot_without_review': False,
            'reason': 'La ruta identifica un documento nulo, anulado o sin efecto.',
        }
    if document_kind == 'property_contribution_support':
        return {
            'review_status': 'support_only_property_contribution',
            'can_seed_controlled_snapshot': False,
            'can_generate_controlled_snapshot_without_review': False,
            'reason': 'La ruta identifica aporte o respaldo de propiedad; no prueba socios/porcentajes vigentes.',
        }
    if document_kind in {
        'constitution_deed',
        'constitution_registration',
        'constitution_extract',
        'official_gazette_publication',
        'transformation_support',
        'modification_support',
        'legal_support_candidate',
    }:
        return {
            'review_status': 'manual_review_required_legal_candidate',
            'can_seed_controlled_snapshot': False,
            'can_generate_controlled_snapshot_without_review': False,
            'reason': (
                'La ruta identifica fuente legal societaria, pero no hay texto extraible; '
                'requiere OCR o revision manual controlada antes de extraer ownership.'
            )
            if empty_text_layer
            else (
                'La ruta identifica fuente legal societaria, pero la extraccion fallo; '
                'requiere OCR o revision manual controlada antes de extraer ownership.'
            ),
        }
    return {
        'review_status': 'manual_review_required_unextractable',
        'can_seed_controlled_snapshot': False,
        'can_generate_controlled_snapshot_without_review': False,
        'reason': 'No se pudo extraer texto; requiere revision manual controlada.',
    }


def _candidate_review_item(*, source_root: Path, item: dict[str, Any]) -> dict[str, Any]:
    path = _source_path(source_root, item)
    document_kind = _document_kind(path)
    base_payload = {
        'path_ref': item.get('path_ref', ''),
        'sha256': item.get('sha256', ''),
        'extension': item.get('extension', ''),
        'size_bytes': item.get('size_bytes', 0),
        'document_kind': document_kind,
        'path_context_tags': _path_context_tags(path),
    }
    try:
        text = _extract_text(path)
    except ValueError as error:
        return {
            **base_payload,
            'signals': {
                'text_extractable': False,
                'extraction_error_ref': hashlib.sha256(str(error).encode('utf-8')).hexdigest(),
            },
            **_path_only_classification(document_kind),
        }
    if not text.strip():
        return {
            **base_payload,
            'signals': {
                'text_extractable': False,
                'empty_text_layer': True,
                'text_sha256': hashlib.sha256(b'').hexdigest(),
                'text_chars': 0,
            },
            **_path_only_classification(document_kind, empty_text_layer=True),
        }

    signals = _signals(text, path)
    return {
        **base_payload,
        'signals': signals,
        **_classification(document_kind=document_kind, signals=signals),
    }


def review_annual_tax_ownership_candidates(
    *,
    manifest: dict[str, Any],
    source_root: Path,
    company_ref: str,
    commercial_year: int,
    tax_year: int | None = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f'source_root does not exist or is not a directory: {source_root}')
    tax_year = tax_year or commercial_year + 1
    candidates = [
        item
        for item in manifest.get('files') or []
        if isinstance(item, dict) and item.get('category') == 'ownership_source_candidate'
    ]
    reviewed = [
        _candidate_review_item(source_root=source_root, item=item)
        for item in candidates
    ]
    ready_candidates = [
        item for item in reviewed if item.get('review_status') == 'candidate_for_controlled_snapshot_review'
    ]
    manual_review_candidates = [
        item for item in reviewed if item.get('review_status') == 'manual_review_required_legal_candidate'
    ]
    excluded = [
        item
        for item in reviewed
        if str(item.get('review_status') or '').startswith('excluded_')
        or item.get('review_status') == 'support_only_property_contribution'
    ]
    support_only = [
        item for item in reviewed if str(item.get('review_status') or '').startswith('support_only_')
    ]
    summary = {
        'candidate_files_total': len(candidates),
        'reviewed_files_total': len(reviewed),
        'text_extractable_files_total': sum(
            1 for item in reviewed if item.get('signals', {}).get('text_extractable')
        ),
        'candidate_for_controlled_snapshot_review_count': len(ready_candidates),
        'manual_review_legal_candidate_count': len(manual_review_candidates),
        'support_only_count': len(support_only),
        'excluded_or_property_support_count': len(excluded),
        'controlled_snapshot_ready': False,
        'auto_generates_socios_or_percentages': False,
        'requires_manual_controlled_extraction': bool(ready_candidates or manual_review_candidates),
        'requires_current_vigency_confirmation': bool(ready_candidates or manual_review_candidates),
    }
    return {
        'schema_version': OWNERSHIP_CANDIDATE_REVIEW_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'source_manifest_hash': payload_hash(
            {
                'schema_version': manifest.get('schema_version', ''),
                'source_root_ref': manifest.get('source_root_ref', ''),
                'coverage': manifest.get('coverage', {}),
                'summary': manifest.get('summary', {}),
            }
        ),
        'safety': {
            'read_only_source_review': True,
            'copied_source_files': False,
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'stores_raw_text': False,
            'stores_rut_values': False,
            'stores_person_names': False,
            'uses_temporary_short_path_links': True,
            'can_generate_controlled_snapshot_without_review': False,
        },
        'summary': summary,
        'review_items': reviewed,
        'decision': {
            'architecture_can_continue_to_controlled_snapshot': bool(ready_candidates or manual_review_candidates),
            'architecture_can_close_ownership_source': False,
            'reason': (
                'Hay documentos con senales societarias para revision controlada, '
                f'pero ninguno se transforma automaticamente en ownership vigente AC{commercial_year}.'
            )
            if ready_candidates
            else (
                'Hay documentos legales candidatos por ruta, pero requieren OCR o revision manual controlada '
                'antes de extraer socios/participaciones.'
            )
            if manual_review_candidates
            else 'No hay documentos suficientes para preparar snapshot ownership controlado.',
            'required_next_data': [
                'socios o accionistas vigentes al cierre AC2024',
                'porcentajes o numero de acciones/participaciones vigentes',
                'fecha de vigencia/as_of de la estructura',
                'evidencia legal no sensible y revision responsable',
            ],
        },
    }
