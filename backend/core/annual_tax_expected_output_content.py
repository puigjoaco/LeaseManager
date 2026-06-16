from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from core.annual_tax_controlled_load_plan import COMPARISON_ONLY_CATEGORIES
from core.annual_tax_source_manifest import EXPECTED_DDJJ_FORMS, EXPECTED_ANNUAL_TAX_REGISTER_KEYS


EXPECTED_OUTPUT_CONTENT_SCHEMA_VERSION = 'annual-tax-expected-output-content.v1'
TEXT_EXTENSIONS = {'.txt', '.csv', '.json', '.md', '.html', '.htm'}
VALUE_EXTRACTABLE_CATEGORIES = {
    'annual_balance_expected_output',
    'annual_tax_register_expected_output',
}
DOCUMENT_SEMANTIC_CATEGORIES = {
    'ddjj_expected_output',
    'f22_expected_output',
}

FORM_PATTERN = re.compile(r'(?i)(?:DJ|declaraci[oó]n\s+jurada|formulario)\D{0,40}(1835|1837|1847|1887|1926|1948|22)')
FOLIO_PATTERN = re.compile(r'(?i)folio\D{0,40}(\d{5,})')
AMOUNT_TOKEN_PATTERN = re.compile(r'(?<![\w])[-+]?\(?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d{1,2})?\)?(?![\w])')


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


def _canonical_expected_amount_tokens(text: str) -> set[str]:
    tokens = set()
    for match in AMOUNT_TOKEN_PATTERN.finditer(text):
        raw_value = match.group(0).strip().replace(' ', '')
        if not raw_value:
            continue
        if ',' in raw_value:
            raw_value = raw_value.rsplit(',', 1)[0]
        normalized = raw_value.replace('.', '').replace('+', '').replace('-', '').replace('(', '').replace(')', '')
        if not normalized.isdigit():
            continue
        try:
            tokens.add(str(int(normalized)))
        except ValueError:
            continue
    return tokens


def canonical_generated_clp_amount_token(value: Any) -> str:
    try:
        amount = Decimal(str(value if value is not None else '0'))
    except (InvalidOperation, ValueError):
        return ''
    if amount == 0:
        return ''
    integral = amount.to_integral_value()
    if amount != integral:
        return ''
    return str(abs(int(integral)))


def value_ref_for_clp_amount_token(amount_token: str) -> str:
    return hashlib.sha256(f'clp-integer:{amount_token}'.encode('utf-8')).hexdigest()


def _folio_ref(folio: str) -> str:
    return hashlib.sha256(f'folio:{folio}'.encode('utf-8')).hexdigest() if folio else ''


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


def extract_expected_output_value_signals(
    *,
    source_root: Path,
    manifest: dict[str, Any],
    generated_targets: list[dict[str, Any]],
    semantic_supported_categories: set[str] | None = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f'source_root no existe o no es directorio: {source_root}')
    semantic_supported_categories = {
        str(category or '').strip()
        for category in semantic_supported_categories or set()
        if str(category or '').strip()
    }

    expected_files = _expected_files(manifest)
    expected_by_key: dict[tuple[str, str], set[str]] = {}
    file_signals: list[dict[str, Any]] = []
    extraction_errors: list[dict[str, str]] = []
    for item in expected_files:
        category = str(item.get('category') or '').strip()
        if category not in VALUE_EXTRACTABLE_CATEGORIES:
            continue
        path_ref = str(item.get('path_ref') or '').strip()
        artifact_key = str(item.get('artifact_key') or '').strip()
        try:
            path = _source_path(source_root, item)
            text = _extract_text(path)
            normalized_text = ' '.join(text.split())
            tokens = _canonical_expected_amount_tokens(normalized_text)
            expected_by_key[(category, artifact_key)] = tokens
            file_signals.append(
                {
                    'path_ref': path_ref,
                    'category': category,
                    'artifact_key': artifact_key,
                    'extension': path.suffix.lower(),
                    'numeric_token_count': _numeric_token_count(normalized_text),
                    'unique_amount_token_count': len(tokens),
                    'signal_sources': ['relative_path', 'text'],
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

    comparisons: list[dict[str, Any]] = []
    skipped_generated_targets = 0
    for target in generated_targets:
        category = str(target.get('category') or '').strip()
        artifact_key = str(target.get('artifact_key') or '').strip()
        amount_token = str(target.get('amount_token') or '').strip()
        if category not in VALUE_EXTRACTABLE_CATEGORIES:
            skipped_generated_targets += 1
            continue
        if not amount_token:
            skipped_generated_targets += 1
            continue
        expected_tokens = expected_by_key.get((category, artifact_key), set())
        comparisons.append(
            {
                'target_key': str(target.get('target_key') or '').strip(),
                'category': category,
                'artifact_key': artifact_key,
                'amount_ref': value_ref_for_clp_amount_token(amount_token),
                'expected_file_numeric_token_count': len(expected_tokens),
                'matched': amount_token in expected_tokens,
                'signal_sources': ['generated_artifact', 'expected_output_text'],
            }
        )

    missing_targets = [item for item in comparisons if not item['matched']]
    expected_categories = {
        str(item.get('category') or '').strip()
        for item in expected_files
        if str(item.get('category') or '').strip()
    }
    unsupported_expected_categories = sorted(
        expected_categories - VALUE_EXTRACTABLE_CATEGORIES - semantic_supported_categories
    )
    target_value_presence_ready = bool(comparisons) and not missing_targets and not extraction_errors

    return {
        'schema_version': 'annual-tax-expected-output-values.v1',
        'source_root_ref': manifest.get('source_root_ref', ''),
        'commercial_year': manifest.get('commercial_year'),
        'tax_year': manifest.get('tax_year'),
        'supported_categories': sorted(VALUE_EXTRACTABLE_CATEGORIES),
        'semantic_supported_categories': sorted(semantic_supported_categories),
        'unsupported_expected_categories': unsupported_expected_categories,
        'file_signals': file_signals,
        'comparisons': comparisons,
        'summary': {
            'files_total': len(file_signals),
            'extraction_errors_total': len(extraction_errors),
            'generated_targets_total': len(generated_targets),
            'compared_targets_total': len(comparisons),
            'matched_targets_total': len(comparisons) - len(missing_targets),
            'missing_targets_total': len(missing_targets),
            'skipped_generated_targets_total': skipped_generated_targets,
            'target_value_presence_ready': target_value_presence_ready,
            'value_equality_extractors_ready': target_value_presence_ready and not unsupported_expected_categories,
        },
        'extraction_errors': extraction_errors,
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'stores_raw_text': False,
            'stores_raw_numeric_tokens': False,
            'stores_raw_amounts': False,
        },
    }


def extract_expected_output_document_semantic_signals(
    *,
    source_root: Path,
    manifest: dict[str, Any],
    generated_targets: list[dict[str, Any]],
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f'source_root no existe o no es directorio: {source_root}')

    expected_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    file_signals: list[dict[str, Any]] = []
    extraction_errors: list[dict[str, str]] = []
    for item in _expected_files(manifest):
        category = str(item.get('category') or '').strip()
        if category not in DOCUMENT_SEMANTIC_CATEGORIES:
            continue
        path_ref = str(item.get('path_ref') or '').strip()
        artifact_key = str(item.get('artifact_key') or '').strip()
        try:
            path = _source_path(source_root, item)
            text = _extract_text(path)
            normalized_text = ' '.join(text.split())
            forms = _forms_from_text_or_path(text=normalized_text, item=item, path=path)
            status = _status_from_text_or_path(text=normalized_text, item=item, path=path)
            folio = _folio_from_text_or_path(text=normalized_text, path=path)
            signal = {
                'path_ref': path_ref,
                'category': category,
                'artifact_key': artifact_key,
                'extension': path.suffix.lower(),
                'forms': forms,
                'status': status,
                'folio_present': bool(folio),
                'folio_ref': _folio_ref(folio),
                'signal_sources': ['manifest', 'relative_path', 'text'],
            }
            file_signals.append(signal)
            for form in forms:
                if category == 'ddjj_expected_output' and form not in EXPECTED_DDJJ_FORMS:
                    continue
                if category == 'f22_expected_output' and form != 'F22':
                    continue
                expected_ready = bool(folio) and (
                    status == 'accepted'
                    if category == 'ddjj_expected_output'
                    else status not in {'rejected', 'annulled'}
                )
                if not expected_ready:
                    continue
                expected_by_key.setdefault(
                    (category, form),
                    {
                        'category': category,
                        'artifact_key': artifact_key,
                        'form': form,
                        'expected_status': status,
                        'expected_folio_present': True,
                        'expected_ready': True,
                    },
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

    generated_by_key = {
        (
            str(target.get('category') or '').strip(),
            str(target.get('form') or '').strip(),
        ): target
        for target in generated_targets
    }
    comparisons: list[dict[str, Any]] = []
    expected_documents = list(expected_by_key.values())
    for expected in expected_documents:
        key = (expected['category'], expected['form'])
        generated = generated_by_key.get(key) or {}
        generated_prepared = bool(generated.get('prepared'))
        layout_prepared = bool(generated.get('layout_prepared'))
        comparisons.append(
            {
                'target_key': str(generated.get('target_key') or f'{expected["category"]}:{expected["form"]}'),
                'category': expected['category'],
                'artifact_key': expected['artifact_key'],
                'form': expected['form'],
                'expected_status': expected['expected_status'],
                'expected_folio_present': expected['expected_folio_present'],
                'generated_prepared': generated_prepared,
                'layout_prepared': layout_prepared,
                'matched': bool(expected['expected_ready']) and generated_prepared and layout_prepared,
                'signal_sources': ['generated_artifact', 'expected_output_text'],
            }
        )

    missing_documents = [item for item in comparisons if not item['matched']]
    expected_ddjj_forms = sorted(
        {
            item['form']
            for item in expected_documents
            if item['category'] == 'ddjj_expected_output' and item['expected_ready']
        }
    )
    f22_expected_ready = any(
        item['category'] == 'f22_expected_output' and item['expected_ready']
        for item in expected_documents
    )
    document_semantic_ready = (
        bool(comparisons)
        and not extraction_errors
        and not missing_documents
        and set(expected_ddjj_forms) >= set(EXPECTED_DDJJ_FORMS)
        and f22_expected_ready
    )

    return {
        'schema_version': 'annual-tax-expected-output-document-semantics.v1',
        'source_root_ref': manifest.get('source_root_ref', ''),
        'commercial_year': manifest.get('commercial_year'),
        'tax_year': manifest.get('tax_year'),
        'supported_categories': sorted(DOCUMENT_SEMANTIC_CATEGORIES),
        'file_signals': file_signals,
        'comparisons': comparisons,
        'summary': {
            'files_total': len(file_signals),
            'extraction_errors_total': len(extraction_errors),
            'generated_targets_total': len(generated_targets),
            'compared_documents_total': len(comparisons),
            'matched_documents_total': len(comparisons) - len(missing_documents),
            'missing_documents_total': len(missing_documents),
            'expected_ddjj_forms_ready': expected_ddjj_forms,
            'f22_expected_ready': f22_expected_ready,
            'document_semantic_ready': document_semantic_ready,
        },
        'extraction_errors': extraction_errors,
        'safety': {
            'writes_database': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'uses_expected_outputs_as_inputs': False,
            'expected_outputs_used_as_comparison_only': True,
            'stores_raw_text': False,
            'stores_raw_folios': False,
            'stores_raw_numeric_tokens': False,
            'stores_raw_amounts': False,
        },
    }
