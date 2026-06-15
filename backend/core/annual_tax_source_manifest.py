from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.reference_validation import contains_sensitive_reference, redact_sensitive_reference


MANIFEST_SCHEMA_VERSION = 'annual-tax-source-manifest.v1'
EXPECTED_DDJJ_FORMS = ('1835', '1837', '1847', '1887', '1926', '1948')
MONTHS = tuple(range(1, 13))
SUPPORTED_EXTENSIONS = {
    '.csv',
    '.htm',
    '.html',
    '.json',
    '.md',
    '.pdf',
    '.txt',
    '.xls',
    '.xlsx',
}

MONTH_PATTERN = re.compile(r'(?<!\d)(20\d{2})[-_ ]?(0[1-9]|1[0-2])(?=\D|$)')
DDJJ_PATTERN = re.compile(r'DJ[_ -]?(\d{4})(?!\d)', re.IGNORECASE)


CATEGORY_META = {
    'rcv_structured_input': {
        'role': 'input',
        'layer': 'SII / RCV / soporte DTE',
    },
    'f29_support_input': {
        'role': 'input',
        'layer': 'SII / F29 / obligaciones mensuales',
    },
    'annual_books_input': {
        'role': 'input',
        'layer': 'Contabilidad / libros anuales / balance',
    },
    'purchase_sales_books_support': {
        'role': 'support',
        'layer': 'Contabilidad / libros compra-venta',
    },
    'payroll_support': {
        'role': 'support',
        'layer': 'Remuneraciones / DJ1887',
    },
    'real_estate_support': {
        'role': 'support',
        'layer': 'Bienes raices / contribuciones / arriendos',
    },
    'bank_reconciliation_candidate': {
        'role': 'support',
        'layer': 'Conciliacion bancaria',
    },
    'ddjj_expected_output': {
        'role': 'expected_output',
        'layer': 'Renta anual / DDJJ',
    },
    'f22_expected_output': {
        'role': 'expected_output',
        'layer': 'Renta anual / F22',
    },
    'tax_certificate_support': {
        'role': 'support',
        'layer': 'SII / certificados y respaldos tributarios',
    },
    'unclassified_support': {
        'role': 'support',
        'layer': 'Soporte externo no clasificado',
    },
}


@dataclass(frozen=True)
class SourceFile:
    relative_path: str
    path_ref: str
    extension: str
    size_bytes: int
    sha256: str
    category: str
    role: str
    layer: str
    months: tuple[int, ...]
    ddjj_forms: tuple[str, ...]

    def as_dict(self, *, include_relative_path: bool) -> dict[str, Any]:
        payload = {
            'path_ref': self.path_ref,
            'extension': self.extension,
            'size_bytes': self.size_bytes,
            'sha256': self.sha256,
            'category': self.category,
            'role': self.role,
            'layer': self.layer,
            'months': list(self.months),
            'ddjj_forms': list(self.ddjj_forms),
        }
        if include_relative_path:
            payload['relative_path'] = self.relative_path
        return payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def payload_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode('utf-8')).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_path(relative: str) -> tuple[str, str]:
    path_ref = f'file-path-sha256:{hashlib.sha256(relative.encode("utf-8")).hexdigest()}'
    if contains_sensitive_reference(relative):
        return redact_sensitive_reference(relative), path_ref
    return relative, path_ref


def _extract_months(text: str, commercial_year: int) -> tuple[int, ...]:
    months = set()
    for year, month in MONTH_PATTERN.findall(text):
        if int(year) == commercial_year:
            months.add(int(month))
    return tuple(sorted(months))


def _extract_ddjj_forms(text: str) -> tuple[str, ...]:
    return tuple(sorted(set(DDJJ_PATTERN.findall(text))))


def _category_for(relative_path: str) -> str:
    normalized = relative_path.lower().replace('\\', '/')
    file_name = Path(relative_path).name.lower()

    if 'formulario_22' in normalized or 'f22' in normalized:
        return 'f22_expected_output'
    if 'ddjj' in normalized or DDJJ_PATTERN.search(file_name):
        return 'ddjj_expected_output'
    if 'f29' in normalized:
        return 'f29_support_input'
    if 'rcv' in normalized:
        return 'rcv_structured_input'
    if any(
        token in normalized
        for token in (
            'libros_anuales',
            'libro_diario',
            'libro_mayor',
            'inventario',
            'balance',
            'capital_propio',
            'renta_liquida',
            'determinacion_rai',
            'razonabilidad_cpt',
            'rentas_empresariales',
        )
    ):
        return 'annual_books_input'
    if 'libro_compra' in normalized or 'libro_venta' in normalized:
        return 'purchase_sales_books_support'
    if 'remuneracion' in normalized or 'honorario' in normalized:
        return 'payroll_support'
    if any(token in normalized for token in ('bienes_raices', 'bien_raiz', 'contribucion', 'vica')):
        return 'real_estate_support'
    if any(token in normalized for token in ('banco', 'cartola', 'conciliacion', 'leasing')):
        return 'bank_reconciliation_candidate'
    if 'certificado' in normalized or 'sii' in normalized or 'tributario' in normalized:
        return 'tax_certificate_support'
    return 'unclassified_support'


def _iter_source_files(source_root: Path) -> list[Path]:
    files = []
    for path in sorted(source_root.rglob('*'), key=lambda item: item.as_posix().lower()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        files.append(path)
    return files


def _normalize_months(values: tuple[int, ...] | list[int] | None) -> list[int]:
    months = set()
    for value in values or []:
        try:
            month = int(value)
        except (TypeError, ValueError):
            continue
        if month in MONTHS:
            months.add(month)
    return sorted(months)


def _coverage(files: list[SourceFile], *, f29_no_declaration_months: tuple[int, ...]) -> dict[str, Any]:
    by_category: dict[str, list[SourceFile]] = defaultdict(list)
    for item in files:
        by_category[item.category].append(item)

    def months_for(category: str) -> list[int]:
        months = set()
        for item in by_category.get(category, []):
            months.update(item.months)
        return sorted(months)

    ddjj_forms = sorted(
        {
            form
            for item in by_category.get('ddjj_expected_output', [])
            for form in item.ddjj_forms
        }
    )
    missing_ddjj = [form for form in EXPECTED_DDJJ_FORMS if form not in ddjj_forms]
    rcv_months = months_for('rcv_structured_input')
    f29_months = months_for('f29_support_input')
    f29_no_declaration = _normalize_months(f29_no_declaration_months)
    f29_controlled_months = sorted(set(f29_months).union(f29_no_declaration))
    purchase_sales_months = months_for('purchase_sales_books_support')

    checks = [
        {
            'key': 'rcv_12_months',
            'status': 'ready' if rcv_months == list(MONTHS) else 'partial',
            'months': rcv_months,
            'missing_months': [month for month in MONTHS if month not in rcv_months],
        },
        {
            'key': 'f29_periods',
            'status': 'ready' if f29_controlled_months == list(MONTHS) else 'needs_mapping',
            'months': f29_months,
            'no_declaration_months': f29_no_declaration,
            'controlled_months': f29_controlled_months,
            'missing_months': [month for month in MONTHS if month not in f29_controlled_months],
        },
        {
            'key': 'annual_books',
            'status': 'ready' if by_category.get('annual_books_input') else 'missing',
            'files': len(by_category.get('annual_books_input', [])),
        },
        {
            'key': 'purchase_sales_books',
            'status': 'ready' if purchase_sales_months == list(MONTHS) else 'partial',
            'months': purchase_sales_months,
            'missing_months': [month for month in MONTHS if month not in purchase_sales_months],
        },
        {
            'key': 'ddjj_expected_outputs',
            'status': 'ready' if not missing_ddjj else 'partial',
            'forms': ddjj_forms,
            'missing_forms': missing_ddjj,
        },
        {
            'key': 'f22_expected_output',
            'status': 'ready' if by_category.get('f22_expected_output') else 'missing',
            'files': len(by_category.get('f22_expected_output', [])),
        },
        {
            'key': 'bank_reconciliation',
            'status': 'candidate_found' if by_category.get('bank_reconciliation_candidate') else 'not_ready',
            'files': len(by_category.get('bank_reconciliation_candidate', [])),
        },
        {
            'key': 'internal_monthly_closes',
            'status': 'requires_db_load',
            'note': 'El manifiesto no crea cierres mensuales; prepara la carga controlada hacia DB local.',
        },
    ]

    ready_for_mirror_source_bundle = all(
        check['status'] == 'ready'
        for check in checks
        if check['key'] in {'rcv_12_months', 'annual_books', 'ddjj_expected_outputs', 'f22_expected_output'}
    )

    return {
        'checks': checks,
        'ready_for_mirror_source_bundle': ready_for_mirror_source_bundle,
        'rcv_months': rcv_months,
        'f29_months': f29_months,
        'f29_no_declaration_months': f29_no_declaration,
        'f29_controlled_months': f29_controlled_months,
        'purchase_sales_months': purchase_sales_months,
        'ddjj_forms': ddjj_forms,
        'missing_ddjj_forms': missing_ddjj,
    }


def build_annual_tax_source_manifest(
    *,
    source_root: Path,
    company_ref: str,
    commercial_year: int,
    tax_year: int | None = None,
    source_label: str = '',
    authorization_ref: str = 'user-authorized-local-source-review',
    responsible_ref: str = 'codex-local-review',
    include_file_list: bool = True,
    f29_no_declaration_months: tuple[int, ...] | list[int] | None = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    if not source_root.exists() or not source_root.is_dir():
        raise FileNotFoundError(f'source_root does not exist or is not a directory: {source_root}')

    tax_year = tax_year or commercial_year + 1
    source_label = source_label or f'{company_ref}-AC{commercial_year}-AT{tax_year}-mirror-source'
    root_ref = f'source-root-sha256:{hashlib.sha256(str(source_root).encode("utf-8")).hexdigest()}'

    source_files = []
    for path in _iter_source_files(source_root):
        raw_relative_path = path.relative_to(source_root).as_posix()
        relative_path, path_ref = _safe_relative_path(raw_relative_path)
        category = _category_for(raw_relative_path)
        meta = CATEGORY_META[category]
        source_files.append(
            SourceFile(
                relative_path=relative_path,
                path_ref=path_ref,
                extension=path.suffix.lower(),
                size_bytes=path.stat().st_size,
                sha256=_file_hash(path),
                category=category,
                role=meta['role'],
                layer=meta['layer'],
                months=_extract_months(raw_relative_path, commercial_year),
                ddjj_forms=_extract_ddjj_forms(raw_relative_path),
            )
        )

    category_counts = {
        category: len([item for item in source_files if item.category == category])
        for category in sorted(CATEGORY_META)
    }
    category_bytes = {
        category: sum(item.size_bytes for item in source_files if item.category == category)
        for category in sorted(CATEGORY_META)
    }
    role_counts = {
        role: len([item for item in source_files if item.role == role])
        for role in ('input', 'support', 'expected_output')
    }
    coverage = _coverage(
        source_files,
        f29_no_declaration_months=tuple(_normalize_months(f29_no_declaration_months)),
    )

    source_refs = [
        {
            'path_ref': item.path_ref,
            'sha256': item.sha256,
            'category': item.category,
            'role': item.role,
            'months': list(item.months),
            'ddjj_forms': list(item.ddjj_forms),
        }
        for item in source_files
    ]
    source_refs_hash = payload_hash(source_refs)

    bundle_summary = {
        'schema_version': MANIFEST_SCHEMA_VERSION,
        'company_ref': company_ref,
        'anio_comercial': commercial_year,
        'anio_tributario': tax_year,
        'source_root_ref': root_ref,
        'files_total': len(source_files),
        'bytes_total': sum(item.size_bytes for item in source_files),
        'category_counts': category_counts,
        'category_bytes': category_bytes,
        'role_counts': role_counts,
        'coverage': {
            'rcv_months': coverage['rcv_months'],
            'f29_months': coverage['f29_months'],
            'f29_no_declaration_months': coverage['f29_no_declaration_months'],
            'f29_controlled_months': coverage['f29_controlled_months'],
            'purchase_sales_months': coverage['purchase_sales_months'],
            'ddjj_forms': coverage['ddjj_forms'],
            'missing_ddjj_forms': coverage['missing_ddjj_forms'],
        },
        'source_refs_hash': source_refs_hash,
        'approved_close_months': [],
        'obligation_months': coverage['f29_controlled_months'],
        'manual_review_required': [
            'internal_monthly_closes',
            'annual_books_pdf_extraction_or_controlled_manual_load',
            'expert_tax_review_before_final_close',
        ],
    }
    bundle_payload = {
        'anio_tributario': tax_year,
        'anio_comercial': commercial_year,
        'source_kind': 'snapshot_controlado',
        'source_label': source_label,
        'authorization_ref': authorization_ref,
        'responsible_ref': responsible_ref,
        'estado_sugerido': 'borrador',
        'resumen_fuentes': bundle_summary,
        'hash_fuentes': payload_hash(bundle_summary),
        'freeze_blockers': [
            'AnnualTaxSourceBundle congelado requiere doce cierres mensuales aprobados en DB local/controlada.',
            'El manifiesto no reemplaza revision experta ni gate SII.',
        ],
    }

    manifest = {
        'schema_version': MANIFEST_SCHEMA_VERSION,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'source_root_ref': root_ref,
        'company_ref': company_ref,
        'commercial_year': commercial_year,
        'tax_year': tax_year,
        'safety': {
            'read_only_source_scan': True,
            'copied_source_files': False,
            'uses_sii_real': False,
            'uses_credentials': False,
            'contains_absolute_source_paths': False,
            'expected_outputs_used_as_inputs': False,
        },
        'summary': {
            'files_total': len(source_files),
            'bytes_total': sum(item.size_bytes for item in source_files),
            'category_counts': category_counts,
            'role_counts': role_counts,
        },
        'coverage': coverage,
        'annual_tax_source_bundle_draft': bundle_payload,
    }
    if include_file_list:
        manifest['files'] = [item.as_dict(include_relative_path=True) for item in source_files]
    return manifest
