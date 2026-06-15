from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.annual_tax_source_manifest import EXPECTED_DDJJ_FORMS, EXPECTED_ANNUAL_TAX_REGISTER_KEYS


EXPECTED_OUTPUT_CONTENT_SCHEMA_VERSION = 'annual-tax-expected-output-content.v1'
TEXT_EXTENSIONS = {'.txt', '.csv', '.json', '.md', '.html', '.htm'}

FORM_PATTERN = re.compile(r'(?i)(?:DJ|declaraci[oó]n\s+jurada|formulario)\D{0,40}(1835|1837|1847|1887|1926|1948|22)')
FOLIO_PATTERN = re.compile(r'(?i)folio\D{0,40}(\d{5,})')


def _extract_text(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return path.read_text(encoding='utf-8-sig', errors='replace')
    if path.suffix.lower() == '.pdf':
        command = ['pdftotext', '-layout', '-nopgbrk', str(path), '-']
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError(f'No se pudo extraer texto PDF con pdftotext: {path.name}') from error
        return completed.stdout
    raise ValueError(f'Extension no soportada para extraccion de output esperado: {path.suffix}')


def _source_path(source_root: Path, item: dict[str, Any]) -> Path:
    relative_path = str(item.get('relative_path') or '').strip()
    if not relative_path:
        raise ValueError('Output esperado sin relative_path en manifiesto.')
    path = (source_root / relative_path).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError as error:
        raise ValueError('relative_path escapa del source_root controlado.') from error
    if not path.exists() or not path.is_file():
        raise ValueError(f'No existe output esperado controlado: {relative_path}')
    return path


def _status_from_text_or_path(*, text: str, item: dict[str, Any], path: Path) -> str:
    manifest_status = str(item.get('output_status') or '').strip()
    haystack = f'{path.name}\n{text}'.lower()
    if 'rechazad' in haystack:
        return 'rejected'
    if 'anulad' in haystack:
        return 'annulled'
    if 'aceptad' in haystack:
        return 'accepted'
    if manifest_status:
        return manifest_status
    return 'unknown'


def _forms_from_text_or_path(*, text: str, item: dict[str, Any], path: Path) -> list[str]:
    forms = {
        str(form or '').strip()
        for form in item.get('ddjj_forms') or []
        if str(form or '').strip()
    }
    for haystack in (path.name, text):
        for match in FORM_PATTERN.finditer(haystack):
            form = match.group(1)
            forms.add('F22' if form == '22' else form)
    if item.get('category') == 'f22_expected_output':
        forms.add('F22')
    return sorted(forms)


def _folio_from_text_or_path(*, text: str, path: Path) -> str:
    for haystack in (text, path.name):
        match = FOLIO_PATTERN.search(haystack)
        if match:
            return match.group(1)
    return ''


def _numeric_token_count(text: str) -> int:
    return len(re.findall(r'(?<!\d)(?:\d{1,3}(?:\.\d{3})+|\d+)(?!\d)', text))


def _expected_files(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in manifest.get('files') or []
        if isinstance(item, dict) and str(item.get('category') or '').strip() in COMPARISON_ONLY_CATEGORIES
    ]


def extract_expected_output_content_signals(*, source_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f'source_root no existe o no es directorio: {source_root}')

    signals: list[dict[str, Any]] = []
    extraction_errors: list[dict[str, str]] = []
    for item in _expected_files(manifest):
        path_ref = str(item.get('path_ref') or '').strip()
        category = str(item.get('category') or '').strip()
        artifact_key = str(item.get('artifact_key') or '').strip()
        try:
            path = _source_path(source_root, item)
            text = _extract_text(path)
            normalized_text = ' '.join(text.split())
            forms = _forms_from_text_or_path(text=normalized_text, item=item, path=path)
            status = _status_from_text_or_path(text=normalized_text, item=item, path=path)
            folio = _folio_from_text_or_path(text=normalized_text, path=path)
            signals.append(
                {
                    'path_ref': path_ref,
                    'category': category,
                    'artifact_key': artifact_key,
                    'extension': path.suffix.lower(),
                    'text_extractable': bool(normalized_text),
                    'text_length': len(normalized_text),
                    'numeric_token_count': _numeric_token_count(normalized_text),
                    'forms': forms,
                    'status': status,
                    'folio_present': bool(folio),
                    'folio': folio,
                    'signal_sources': ['manifest', 'relative_path', 'text'],
                }
            )
        except (OSError, ValueError) as error:
            extraction_errors.append(
                {
                    'path_ref': path_ref,
                    'category': category,
                    'artifact_key': artifact_key,
                    'error': str(error),
                }
            )

    accepted_ddjj_forms = sorted(
        {
            form
            for signal in signals
            if signal['category'] == 'ddjj_expected_output' and signal['status'] == 'accepted'
            for form in signal['forms']
            if form in EXPECTED_DDJJ_FORMS
        }
    )
    accepted_ddjj_folios_by_form = {
        form: sorted(
            {
                signal['folio']
                for signal in signals
                if signal['category'] == 'ddjj_expected_output'
                and signal['status'] == 'accepted'
                and form in signal['forms']
                and signal['folio']
            }
        )
        for form in accepted_ddjj_forms
    }
    f22_folios = sorted(
        {
            signal['folio']
            for signal in signals
            if signal['category'] == 'f22_expected_output' and signal['folio']
        }
    )
    register_keys_with_text = sorted(
        {
            signal['artifact_key']
            for signal in signals
            if signal['category'] == 'annual_tax_register_expected_output' and signal['text_extractable']
        }
    )
    balance_text_extractable = any(
        signal['category'] == 'annual_balance_expected_output' and signal['text_extractable']
        for signal in signals
    )
    identity_ready = (
        not extraction_errors
        and set(accepted_ddjj_forms) >= set(EXPECTED_DDJJ_FORMS)
        and bool(f22_folios)
        and balance_text_extractable
        and set(register_keys_with_text) >= set(EXPECTED_ANNUAL_TAX_REGISTER_KEYS)
    )

    return {
        'schema_version': EXPECTED_OUTPUT_CONTENT_SCHEMA_VERSION,
        'source_root_ref': manifest.get('source_root_ref', ''),
        'commercial_year': manifest.get('commercial_year'),
        'tax_year': manifest.get('tax_year'),
        'signals': signals,
        'summary': {
            'files_total': len(signals),
            'extraction_errors_total': len(extraction_errors),
            'accepted_ddjj_forms_from_content': accepted_ddjj_forms,
            'accepted_ddjj_folios_by_form': accepted_ddjj_folios_by_form,
            'f22_folios_from_content': f22_folios,
            'annual_tax_register_keys_with_text': register_keys_with_text,
            'balance_text_extractable': balance_text_extractable,
            'identity_signals_ready': identity_ready,
            'value_equality_extractors_ready': False,
        },
        'extraction_errors': extraction_errors,
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'stores_raw_text': False,
        },
    }
