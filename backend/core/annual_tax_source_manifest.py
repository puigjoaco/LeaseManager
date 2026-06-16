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
EXPECTED_ANNUAL_TAX_REGISTER_KEYS = (
    'capital_propio',
    'determinacion_rai',
    'razonabilidad_cpt',
    'renta_liquida',
    'rentas_empresariales',
)
REQUIRED_MIRROR_ARCHITECTURE_CAPABILITIES = (
    {
        'key': 'source_inventory',
        'label': 'Inventario externo AC/AT read-only',
        'status': 'implemented',
        'evidence': 'build_annual_tax_source_manifest',
    },
    {
        'key': 'input_output_boundary',
        'label': 'Separacion de insumos de calculo y outputs esperados',
        'status': 'implemented',
        'evidence': 'manifest.roles + expected_outputs_used_as_inputs=false',
    },
    {
        'key': 'controlled_accounting_loader',
        'label': 'Carga controlada de libros/cierres/hechos 2024 a DB local',
        'status': 'implemented',
        'evidence': 'apply_annual_tax_controlled_db_load',
    },
    {
        'key': 'monthly_tax_fact_normalization',
        'label': 'Normalizacion mensual anualizable',
        'status': 'implemented',
        'evidence': 'MonthlyTaxFact + sync_monthly_tax_facts',
    },
    {
        'key': 'annual_tax_generation_pipeline',
        'label': 'Pipeline LeaseManager para balance tributario, workbooks, DDJJ, F22, dossier y export local',
        'status': 'implemented',
        'evidence': 'generate_annual_preparation',
    },
    {
        'key': 'expected_output_comparator',
        'label': 'Comparador de cobertura LeaseManager vs Balance/RLI/CPT/DDJJ/F22 definitivos',
        'status': 'implemented',
        'evidence': 'compare_annual_tax_expected_outputs',
    },
    {
        'key': 'expected_output_identity_extractors',
        'label': 'Extractores de identidad de outputs definitivos',
        'status': 'implemented',
        'evidence': 'extract_expected_output_content_signals',
    },
    {
        'key': 'expected_output_value_extractors',
        'label': 'Extractores de valores para presencia numerica contra outputs definitivos',
        'status': 'partial',
        'evidence': 'extract_expected_output_value_signals',
    },
    {
        'key': 'expected_output_value_equality_completion',
        'label': 'Igualdad semantica completa de valores contra outputs definitivos',
        'status': 'missing',
        'evidence': 'pendiente DDJJ/F22 y reconciliacion semantica',
    },
)
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
LEADING_MONTH_NAME_PATTERN = re.compile(
    r'(?<!\d)(0[1-9]|1[0-2])\s+'
    r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b',
    re.IGNORECASE,
)
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
    'annual_ledger_input': {
        'role': 'input',
        'layer': 'Contabilidad / libros anuales transaccionales',
    },
    'annual_balance_expected_output': {
        'role': 'expected_output',
        'layer': 'Contabilidad / balance anual a comparar',
    },
    'annual_tax_register_expected_output': {
        'role': 'expected_output',
        'layer': 'Renta anual / RLI / CPT / RAI / registros empresariales',
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
    artifact_key: str
    output_status: str

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
            'artifact_key': self.artifact_key,
            'output_status': self.output_status,
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
    if str(commercial_year) in text:
        for month, _month_name in LEADING_MONTH_NAME_PATTERN.findall(text):
            months.add(int(month))
    return tuple(sorted(months))


def _extract_ddjj_forms(text: str) -> tuple[str, ...]:
    return tuple(sorted(set(DDJJ_PATTERN.findall(text))))


def _normalize_for_match(value: str) -> str:
    return (
        value.lower()
        .replace('\\', '/')
        .replace(' ', '_')
        .replace('-', '_')
    )


def _annual_tax_register_key(normalized_path: str) -> str:
    if 'capital_propio' in normalized_path:
        return 'capital_propio'
    if 'determinacion_rai' in normalized_path or 'determinacion_de_rai' in normalized_path:
        return 'determinacion_rai'
    if 'razonabilidad_cpt' in normalized_path:
        return 'razonabilidad_cpt'
    if 'renta_liquida' in normalized_path:
        return 'renta_liquida'
    if 'rentas_empresariales' in normalized_path:
        return 'rentas_empresariales'
    return ''


def _category_for(relative_path: str) -> str:
    normalized = _normalize_for_match(relative_path)
    file_name = Path(relative_path).name.lower()

    if 'formulario_22' in normalized or 'f22' in normalized:
        return 'f22_expected_output'
    if 'ddjj' in normalized or DDJJ_PATTERN.search(file_name):
        return 'ddjj_expected_output'
    if 'f29' in normalized:
        return 'f29_support_input'
    if 'rcv' in normalized:
        return 'rcv_structured_input'
    if _annual_tax_register_key(normalized):
        return 'annual_tax_register_expected_output'
    if 'balance' in normalized:
        return 'annual_balance_expected_output'
    if 'libro_diario' in normalized or 'libro_mayor' in normalized or 'inventario' in normalized:
        return 'annual_ledger_input'
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


def _artifact_key_for(category: str, relative_path: str, ddjj_forms: tuple[str, ...]) -> str:
    normalized = _normalize_for_match(relative_path)
    if category == 'ddjj_expected_output':
        return f'dj_{ddjj_forms[0]}' if ddjj_forms else 'ddjj_metadata'
    if category == 'f22_expected_output':
        return 'f22'
    if category == 'annual_balance_expected_output':
        return 'balance_general'
    if category == 'annual_tax_register_expected_output':
        return _annual_tax_register_key(normalized) or 'annual_tax_register'
    if category == 'annual_ledger_input':
        if 'libro_diario' in normalized:
            return 'libro_diario'
        if 'libro_mayor' in normalized:
            return 'libro_mayor'
        if 'inventario' in normalized:
            return 'libro_inventario'
    return category


def _output_status_for(category: str, relative_path: str) -> str:
    normalized = _normalize_for_match(relative_path)
    if category not in {
        'ddjj_expected_output',
        'f22_expected_output',
        'annual_balance_expected_output',
        'annual_tax_register_expected_output',
    }:
        return ''
    if 'rechazada' in normalized or 'rechazado' in normalized:
        return 'rejected'
    if 'anulada' in normalized or 'anulado' in normalized:
        return 'annulled'
    if 'aceptada' in normalized or 'aceptado' in normalized:
        return 'accepted'
    if category == 'f22_expected_output':
        return 'final'
    return 'baseline'


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
            if item.output_status == 'accepted'
            for form in item.ddjj_forms
        }
    )
    missing_ddjj = [form for form in EXPECTED_DDJJ_FORMS if form not in ddjj_forms]
    rcv_months = months_for('rcv_structured_input')
    f29_months = months_for('f29_support_input')
    f29_no_declaration = _normalize_months(f29_no_declaration_months)
    f29_controlled_months = sorted(set(f29_months).union(f29_no_declaration))
    purchase_sales_months = months_for('purchase_sales_books_support')
    annual_ledger_keys = sorted({item.artifact_key for item in by_category.get('annual_ledger_input', []) if item.artifact_key})
    missing_ledger_keys = [key for key in ('libro_diario', 'libro_mayor', 'libro_inventario') if key not in annual_ledger_keys]
    annual_tax_register_keys = sorted(
        {
            item.artifact_key
            for item in by_category.get('annual_tax_register_expected_output', [])
            if item.artifact_key in EXPECTED_ANNUAL_TAX_REGISTER_KEYS
        }
    )
    missing_tax_register_keys = [
        key for key in EXPECTED_ANNUAL_TAX_REGISTER_KEYS if key not in annual_tax_register_keys
    ]

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
            'key': 'annual_ledger_inputs',
            'status': 'ready' if not missing_ledger_keys else 'partial',
            'artifact_keys': annual_ledger_keys,
            'missing_artifact_keys': missing_ledger_keys,
            'files': len(by_category.get('annual_ledger_input', [])),
        },
        {
            'key': 'annual_balance_expected_output',
            'status': 'ready' if by_category.get('annual_balance_expected_output') else 'missing',
            'files': len(by_category.get('annual_balance_expected_output', [])),
        },
        {
            'key': 'annual_tax_register_expected_outputs',
            'status': 'ready' if not missing_tax_register_keys else 'partial',
            'artifact_keys': annual_tax_register_keys,
            'missing_artifact_keys': missing_tax_register_keys,
            'files': len(by_category.get('annual_tax_register_expected_output', [])),
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
        if check['key'] in {
            'rcv_12_months',
            'annual_ledger_inputs',
            'annual_balance_expected_output',
            'annual_tax_register_expected_outputs',
            'ddjj_expected_outputs',
            'f22_expected_output',
        }
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
        'annual_ledger_keys': annual_ledger_keys,
        'missing_annual_ledger_keys': missing_ledger_keys,
        'annual_tax_register_keys': annual_tax_register_keys,
        'missing_annual_tax_register_keys': missing_tax_register_keys,
    }


def _mirror_proof_readiness(coverage: dict[str, Any]) -> dict[str, Any]:
    source_ready = bool(coverage.get('ready_for_mirror_source_bundle'))
    implemented_capabilities = [
        item['key']
        for item in REQUIRED_MIRROR_ARCHITECTURE_CAPABILITIES
        if item['status'] in {'implemented', 'partial'}
    ]
    missing_capabilities = [
        item['key'] for item in REQUIRED_MIRROR_ARCHITECTURE_CAPABILITIES if item['status'] == 'missing'
    ]
    return {
        'source_documentation_confirmed_for_ac2024_at2025': source_ready,
        'architecture_complete_for_mirror_run': source_ready and not missing_capabilities,
        'ready_to_start_controlled_processing': source_ready and 'controlled_accounting_loader' not in missing_capabilities,
        'implemented_capabilities': implemented_capabilities,
        'missing_capabilities': missing_capabilities,
        'capabilities': list(REQUIRED_MIRROR_ARCHITECTURE_CAPABILITIES),
        'input_policy': {
            'calculation_inputs': [
                'annual_ledger_input',
                'rcv_structured_input',
                'f29_support_input',
                'purchase_sales_books_support',
                'payroll_support',
                'real_estate_support',
                'tax_certificate_support',
            ],
            'comparison_only_outputs': [
                'annual_balance_expected_output',
                'annual_tax_register_expected_output',
                'ddjj_expected_output',
                'f22_expected_output',
            ],
            'expected_outputs_used_as_inputs': False,
        },
        'next_actions': [
            'Construir paquete normalizado desde libros/F29/remuneraciones por parser o carga manual controlada.',
            'Aplicar writer DB local controlado sin copiar documentos al repo ni usar outputs esperados como input.',
            'Generar artefactos LeaseManager AT2025 desde inputs AC2024 cargados.',
            'Implementar extractores de valores contra outputs esperados sin usarlos como insumo de calculo.',
        ]
        if source_ready
        else [
            'Completar fuentes AC2024/AT2025 minimas antes de iniciar procesamiento.',
        ],
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
        ddjj_forms = _extract_ddjj_forms(raw_relative_path)
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
                ddjj_forms=ddjj_forms,
                artifact_key=_artifact_key_for(category, raw_relative_path, ddjj_forms),
                output_status=_output_status_for(category, raw_relative_path),
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
        'calculation_input_categories': [
            category
            for category, meta in sorted(CATEGORY_META.items())
            if meta['role'] == 'input'
        ],
        'comparison_target_categories': [
            category
            for category, meta in sorted(CATEGORY_META.items())
            if meta['role'] == 'expected_output'
        ],
        'expected_outputs_used_as_inputs': False,
        'manual_review_required': [
            'internal_monthly_closes',
            'annual_ledger_pdf_extraction_or_controlled_manual_load',
            'comparison_against_expected_outputs_without_using_them_as_inputs',
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
        'mirror_proof_readiness': _mirror_proof_readiness(coverage),
        'annual_tax_source_bundle_draft': bundle_payload,
    }
    if include_file_list:
        manifest['files'] = [item.as_dict(include_relative_path=True) for item in source_files]
    return manifest
