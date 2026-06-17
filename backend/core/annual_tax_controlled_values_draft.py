from __future__ import annotations

import copy
import json
import re
import subprocess
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_template import CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import is_non_sensitive_reference


CONTROLLED_VALUES_DRAFT_SCHEMA_VERSION = 'annual-tax-controlled-values-draft.v1'

MONTH_NAMES = {
    'ENERO': 1,
    'FEBRERO': 2,
    'MARZO': 3,
    'ABRIL': 4,
    'MAYO': 5,
    'JUNIO': 6,
    'JULIO': 7,
    'AGOSTO': 8,
    'SEPTIEMBRE': 9,
    'OCTUBRE': 10,
    'NOVIEMBRE': 11,
    'DICIEMBRE': 12,
}

MONTH_NAME_PATTERN = '|'.join(MONTH_NAMES)
INVENTORY_SECTION_LABELS = {
    'DETALLE DE ACTIVOS': 'activo',
    'DETALLE DE PASIVOS': 'pasivo',
}
REGION_BY_COMUNA = {
    'PROVIDENCIA': 'Metropolitana',
    'SANTIAGO': 'Metropolitana',
    'TEMUCO': 'La Araucania',
}


def _parse_int_amount(raw: str) -> int:
    text = str(raw or '').strip().replace('.', '').replace(',', '.')
    if not text:
        return 0
    return int(Decimal(text))


def _money(value: int) -> str:
    return f'{int(value)}.00'


def _normal_text(value: Any) -> str:
    return ' '.join(str(value or '').strip().split())


def _normalized_upper(value: Any) -> str:
    return _normal_text(value).upper()


def _hash_ref(prefix: str, payload: Any, *, length: int = 16) -> str:
    return f'{prefix}-{payload_hash(payload)[:length]}'


def _last_amounts(line: str, count: int) -> list[int]:
    values = re.findall(r'(?<!\d)(?:\d{1,3}(?:\.\d{3})+|\d+)(?!\d)', line)
    return [_parse_int_amount(value) for value in values[-count:]]


def parse_libro_diario_text(text: str) -> dict[int, dict[str, Any]]:
    current_month: int | None = None
    by_month: dict[int, dict[str, Any]] = defaultdict(
        lambda: {'asientos_count': 0, 'total_debe': None, 'total_haber': None}
    )
    for raw_line in text.splitlines():
        line = ' '.join(raw_line.strip().split())
        upper = line.upper()
        month_match = re.search(rf'COMPROBANTES\s+MES\s+DE\s+({MONTH_NAME_PATTERN})', upper)
        if month_match:
            current_month = MONTH_NAMES[month_match.group(1)]
            continue
        if current_month and re.search(r'TOTAL\s+COMPROBANTE\s+N[ºO]', upper):
            by_month[current_month]['asientos_count'] += 1
            continue
        total_match = re.search(rf'^TOTAL\s+({MONTH_NAME_PATTERN})\s+', upper)
        if total_match:
            month = MONTH_NAMES[total_match.group(1)]
            amounts = _last_amounts(line, 2)
            if len(amounts) == 2:
                by_month[month]['total_debe'] = amounts[0]
                by_month[month]['total_haber'] = amounts[1]
    return dict(by_month)


def parse_libro_mayor_text(text: str) -> dict[int, dict[str, Any]]:
    current_account = ''
    accounts_by_month: dict[int, set[str]] = defaultdict(set)
    totals_by_month: dict[int, dict[str, int]] = defaultdict(lambda: {'total_debe': 0, 'total_haber': 0})
    for raw_line in text.splitlines():
        line = ' '.join(raw_line.strip().split())
        upper = line.upper()
        account_match = re.match(r'^(\d{6,10})\s+(.+)$', line)
        if account_match and not upper.startswith(('TOTAL ', 'DIA ', 'DÍA ')):
            current_account = account_match.group(1)
            continue
        total_match = re.search(rf'^TOTAL\s+MES\s+DE\s+({MONTH_NAME_PATTERN})\s+\.', upper)
        if not total_match:
            continue
        month = MONTH_NAMES[total_match.group(1)]
        amounts = _last_amounts(line, 3)
        if len(amounts) < 3:
            continue
        debit, credit = amounts[0], amounts[1]
        totals_by_month[month]['total_debe'] += debit
        totals_by_month[month]['total_haber'] += credit
        if current_account and (debit or credit):
            accounts_by_month[month].add(current_account)
    return {
        month: {
            'cuentas_count': len(accounts_by_month.get(month, set())),
            'total_debe': totals['total_debe'],
            'total_haber': totals['total_haber'],
        }
        for month, totals in totals_by_month.items()
    }


def parse_libro_mayor_annual_trial_balance_lines(text: str) -> dict[str, dict[str, Any]]:
    lines: dict[str, dict[str, Any]] = {}
    for raw_line in text.splitlines():
        line = ' '.join(raw_line.strip().split())
        if not line:
            continue
        total_match = re.match(r'^TOTAL\s+(\d{6,10})\s+(.+?)\s+(DB|CR)$', line, re.IGNORECASE)
        if not total_match:
            continue
        amounts = _last_amounts(line, 3)
        if len(amounts) != 3:
            continue
        debit, credit, balance = amounts
        code = total_match.group(1)
        side = total_match.group(3).upper()
        payload = {
            'codigo_cuenta': code,
            'sumas_debe_clp': _money(debit),
            'sumas_haber_clp': _money(credit),
            'formula_ref': 'libro-mayor-total-cuenta',
            'evidencia_ref': 'libro-mayor-2024-controlled',
            'source_payload': {
                'source': 'libro_mayor',
                'section': 'annual_account_total',
                'final_tax_calculation': False,
            },
        }
        if side == 'DB':
            payload['saldo_deudor_clp'] = _money(balance)
        else:
            payload['saldo_acreedor_clp'] = _money(balance)
        lines[code] = payload
    return lines


def parse_f29_text(text: str) -> dict[str, Any]:
    normalized = '\n'.join(' '.join(line.split()) for line in text.splitlines())
    period_match = re.search(r'PERIODO\s+\[15\]\s+(\d{6})', normalized, re.IGNORECASE)
    codes: dict[str, int] = {}
    for line in normalized.splitlines():
        matches = list(
            re.finditer(
                r'(?<!\d)(\d{2,3})\s+([A-ZÁÉÍÓÚÑÜ][^\n]*?)(?=(?<!\d)\d{2,3}\s+[A-ZÁÉÍÓÚÑÜ]|$)',
                line,
                re.IGNORECASE,
            )
        )
        for match in matches:
            code = match.group(1).zfill(3)
            amounts = _last_amounts(match.group(2), 1)
            if amounts:
                codes[code] = amounts[-1]
    return {
        'periodo': period_match.group(1) if period_match else '',
        'codes': codes,
    }


def parse_payroll_text(text: str) -> dict[str, Any]:
    upper = text.upper()
    total_general_detected = 'TOTAL GENERAL' in upper
    numbers_after_total = []
    if total_general_detected:
        _, after = upper.split('TOTAL GENERAL', 1)
        numbers_after_total = _last_amounts(after[:600], 20)
    return {
        'has_movements': any(value > 0 for value in numbers_after_total),
        'total_general_detected': total_general_detected,
        'numbers_detected': len(numbers_after_total),
    }


def _inventory_amount(raw: str) -> int:
    text = str(raw or '').strip()
    if not text:
        return 0
    sign = -1 if '(' in text and ')' in text else 1
    cleaned = text.replace('(', '').replace(')', '')
    return sign * _parse_int_amount(cleaned)


def _inventory_classifier(*, section: str, account_name: str) -> str:
    normalized = ' '.join(str(account_name or '').upper().split())
    if section == 'activo':
        if 'CAJA' in normalized or 'BANCO' in normalized:
            return 'CPT-CASH-ASSET'
        return 'CPT-ASSET'
    if 'UTILIDAD' in normalized:
        return 'RLI-BOOK-PROFIT'
    if 'PERDIDA' in normalized or 'PÉRDIDA' in normalized:
        return 'RLI-BOOK-LOSS'
    if 'CAPITAL' in normalized:
        return 'CPT-EQUITY'
    return 'CPT-LIABILITY-EQUITY'


def parse_libro_inventario_text(text: str) -> dict[str, Any]:
    current_section = ''
    current_account: dict[str, str] | None = None
    lines: list[dict[str, Any]] = []
    totals = {'activos': 0, 'pasivos': 0, 'perdida_ejercicio': 0}

    for raw_line in text.splitlines():
        line = ' '.join(raw_line.strip().split())
        upper = line.upper()
        if not line:
            continue
        for label, section in INVENTORY_SECTION_LABELS.items():
            if upper.startswith(label):
                current_section = section
                current_account = None
                break
        if upper.startswith('TOTAL DETALLE DE ACTIVOS'):
            amounts = _last_amounts(line, 1)
            totals['activos'] = amounts[-1] if amounts else 0
            current_account = None
            continue
        if upper.startswith('TOTAL DETALLE DE PASIVOS'):
            amounts = _last_amounts(line, 1)
            totals['pasivos'] = amounts[-1] if amounts else 0
            current_account = None
            continue
        if 'PERDIDA DEL EJERCICIO' in upper or 'PÉRDIDA DEL EJERCICIO' in upper:
            amount_match = re.search(r'(\(?[\d.]+\)?)\s*$', line)
            amount = _inventory_amount(amount_match.group(1)) if amount_match else 0
            totals['perdida_ejercicio'] = abs(amount)
            lines.append(
                {
                    'codigo_cuenta': 'RESULTADO-EJERCICIO',
                    'nombre_cuenta': 'Perdida del ejercicio',
                    'clasificador_dj1847': 'RLI-BOOK-LOSS',
                    'resultado_perdida_clp': _money(abs(amount)),
                    'formula_ref': 'libro-inventario-resultado-ejercicio',
                    'evidencia_ref': 'libro-inventario-2024-controlled',
                    'source_payload': {
                        'source': 'libro_inventario',
                        'section': 'resultado',
                        'final_tax_calculation': False,
                    },
                }
            )
            current_account = None
            continue
        account_match = re.match(r'^(\d{6,10})\s+(.+)$', line)
        if account_match and current_section:
            current_account = {
                'codigo_cuenta': account_match.group(1),
                'nombre_cuenta': account_match.group(2).strip(),
                'section': current_section,
            }
            continue
        if not current_account or 'SALDO CONTABLE AL' not in upper:
            continue
        amount_match = re.search(r'(\(?[\d.]+\)?)\s*$', line)
        if not amount_match:
            continue
        amount_abs = abs(_inventory_amount(amount_match.group(1)))
        if amount_abs == 0:
            current_account = None
            continue
        section = current_account['section']
        payload = {
            'codigo_cuenta': current_account['codigo_cuenta'],
            'nombre_cuenta': current_account['nombre_cuenta'],
            'clasificador_dj1847': _inventory_classifier(
                section=section,
                account_name=current_account['nombre_cuenta'],
            ),
            'formula_ref': 'libro-inventario-saldo-contable',
            'evidencia_ref': 'libro-inventario-2024-controlled',
            'source_payload': {
                'source': 'libro_inventario',
                'section': section,
                'final_tax_calculation': False,
            },
        }
        if section == 'activo':
            payload.update(
                {
                    'sumas_debe_clp': _money(amount_abs),
                    'saldo_deudor_clp': _money(amount_abs),
                    'inventario_activo_clp': _money(amount_abs),
                }
            )
        else:
            payload.update(
                {
                    'sumas_haber_clp': _money(amount_abs),
                    'saldo_acreedor_clp': _money(amount_abs),
                    'inventario_pasivo_clp': _money(amount_abs),
                }
            )
        lines.append(payload)
        current_account = None

    return {
        'lines': lines,
        'totals': totals,
    }


def _merge_inventory_with_mayor_lines(
    inventario: dict[str, Any],
    mayor_annual_lines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not mayor_annual_lines:
        return inventario
    merged = copy.deepcopy(inventario)
    merged_lines = []
    for line in merged.get('lines') or []:
        if not isinstance(line, dict):
            continue
        code = str(line.get('codigo_cuenta') or '').strip()
        mayor_line = mayor_annual_lines.get(code)
        if mayor_line:
            for field in (
                'sumas_debe_clp',
                'sumas_haber_clp',
                'saldo_deudor_clp',
                'saldo_acreedor_clp',
            ):
                value = mayor_line.get(field)
                if value is not None:
                    line[field] = value
            source_payload = line.get('source_payload') if isinstance(line.get('source_payload'), dict) else {}
            sources = []
            for source in (
                source_payload.get('source'),
                'libro_inventario',
                'libro_mayor',
            ):
                text = str(source or '').strip()
                if text and text not in sources:
                    sources.append(text)
            line['source_payload'] = {
                **source_payload,
                'source': 'libro_inventario+libro_mayor',
                'sources': sources,
                'annual_mayor_account_total': True,
                'final_tax_calculation': False,
            }
        merged_lines.append(line)
    merged['lines'] = merged_lines
    merged['annual_mayor_lines_matched'] = sum(
        1
        for line in merged_lines
        if isinstance(line.get('source_payload'), dict)
        and line['source_payload'].get('annual_mayor_account_total')
    )
    return merged


def _extract_text(path: Path) -> str:
    if path.suffix.lower() in {'.txt', '.csv', '.json', '.md', '.html', '.htm'}:
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
    raise ValueError(f'Extension no soportada para extraccion controlada: {path.suffix}')


def _load_json_source(path: Path) -> Any:
    if path.suffix.lower() != '.json':
        raise ValueError(f'Fuente JSON esperada para bienes raices: {path.name}')
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except json.JSONDecodeError as error:
        raise ValueError(f'JSON invalido en fuente controlada: {path.name}') from error


def _manifest_file_index(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get('path_ref') or ''): item
        for item in manifest.get('files') or []
        if isinstance(item, dict) and item.get('path_ref')
    }


def _source_path(source_root: Path, file_index: dict[str, dict[str, Any]], path_ref: str) -> Path:
    item = file_index.get(path_ref)
    if not item:
        raise ValueError(f'No existe path_ref en manifiesto: {path_ref}')
    relative_path = str(item.get('relative_path') or '').strip()
    if not relative_path:
        raise ValueError(f'path_ref sin relative_path en manifiesto: {path_ref}')
    path = (source_root / relative_path).resolve()
    try:
        path.relative_to(source_root.resolve())
    except ValueError as error:
        raise ValueError('relative_path escapa del source_root controlado.') from error
    if not path.exists() or not path.is_file():
        raise ValueError(f'No existe fuente controlada: {relative_path}')
    return path


def _first_ref(refs: list[dict[str, Any]]) -> dict[str, Any] | None:
    return refs[0] if refs else None


def _normalized_manifest_path(item: dict[str, Any]) -> str:
    return str(item.get('relative_path') or '').strip().replace('\\', '/').casefold()


def _explicit_ano_years(path: str) -> set[int]:
    return {int(year) for year in re.findall(r'(?:^|/)ano_(\d{4})(?:/|$)', path)}


def _candidate_matches_commercial_year(item: dict[str, Any], commercial_year: int) -> bool:
    if not commercial_year:
        return True
    path = _normalized_manifest_path(item)
    explicit_years = _explicit_ano_years(path)
    if explicit_years:
        return commercial_year in explicit_years
    candidate_years = {int(year) for year in re.findall(r'(?<!\d)(20\d{2})(?!\d)', path)}
    return not candidate_years or commercial_year in candidate_years


def _annual_ledger_candidate_score(item: dict[str, Any], commercial_year: int) -> tuple[int, str]:
    path = _normalized_manifest_path(item)
    score = 0
    if commercial_year and f'ano_{commercial_year}/' in path:
        score += 1000
    if '01_libros_anuales/' in path:
        score += 300
    elif 'libros_anuales/' in path:
        score += 200
    if commercial_year and str(commercial_year) in Path(path).name:
        score += 100
    if any(marker in path for marker in ('pendiente_auditoria', 'ano_historico', 'no_presentar')):
        score -= 500
    if any(marker in path for marker in ('gmail', 'documentacion_modificada', 'respaldo')):
        score -= 100
    return score, path


def _select_annual_ledger_ref(manifest: dict[str, Any], artifact_key: str) -> str:
    commercial_year = int(manifest.get('commercial_year') or 0)
    candidates = [
        item
        for item in manifest.get('files') or []
        if isinstance(item, dict)
        and item.get('category') == 'annual_ledger_input'
        and item.get('artifact_key') == artifact_key
        and item.get('path_ref')
    ]
    if not candidates:
        return ''
    compatible = [item for item in candidates if _candidate_matches_commercial_year(item, commercial_year)]
    if not compatible and commercial_year:
        return ''
    ranked = sorted(
        compatible or candidates,
        key=lambda item: _annual_ledger_candidate_score(item, commercial_year),
        reverse=True,
    )
    return str(ranked[0].get('path_ref') or '')


def _real_estate_support_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in manifest.get('files') or []
        if isinstance(item, dict)
        and item.get('category') == 'real_estate_support'
        and item.get('path_ref')
    ]


def _select_real_estate_registry_ref(manifest: dict[str, Any]) -> str:
    candidates = []
    for item in _real_estate_support_items(manifest):
        path = _normalized_manifest_path(item)
        if not path.endswith('.json') or 'registro_bienes_raices' not in path:
            continue
        score = 0
        if 'documentos' not in path:
            score += 100
        if '03_bienes_raices_y_contribuciones/' in path:
            score += 50
        candidates.append((score, path, str(item.get('path_ref') or '')))
    if not candidates:
        return ''
    candidates.sort(reverse=True)
    return candidates[0][2]


def _real_estate_contribution_source_refs(manifest: dict[str, Any]) -> list[str]:
    refs = []
    for item in _real_estate_support_items(manifest):
        path = _normalized_manifest_path(item)
        if any(marker in path for marker in ('contribuciones_y_pagos_sii', 'certificados_pago_pdf', 'detalle_pago_pdf')):
            refs.append(str(item.get('path_ref') or ''))
    return sorted(set(ref for ref in refs if ref))


def _property_key(*, comuna: Any, manzana: Any, predio: Any, rol: Any = '') -> str:
    rol_text = _normal_text(rol)
    if rol_text:
        return rol_text
    comuna_int = str(comuna or '').strip()
    manzana_int = str(manzana or '').strip()
    predio_int = str(predio or '').strip()
    if comuna_int and manzana_int and predio_int:
        return f'{comuna_int}-{manzana_int}-{predio_int}'
    return ''


def _role_tail_key(value: Any) -> str:
    numbers = re.findall(r'\d+', str(value or ''))
    if len(numbers) >= 2:
        return f'{int(numbers[-2])}-{int(numbers[-1])}'
    return ''


def _tipo_inmueble_from_destino(destino: Any) -> str:
    text = _normalized_upper(destino)
    if any(token in text for token in ('LOCAL', 'COMERCIO', 'COMERCIAL')):
        return 'local'
    if any(token in text for token in ('DEPARTAMENTO', 'DEPTO', 'DP ')):
        return 'departamento'
    if 'CASA' in text:
        return 'casa'
    if 'OFICINA' in text:
        return 'oficina'
    if any(token in text for token in ('BODEGA', 'BD ', 'BX ')):
        return 'bodega'
    if any(token in text for token in ('ESTACIONAMIENTO', 'PARKING')):
        return 'estacionamiento'
    return 'otro'


def _real_estate_property_from_row(row: list[Any], *, registry_ref: str, index: int) -> dict[str, Any] | None:
    if len(row) < 10:
        return None
    comuna = _normal_text(row[1])
    rol = _normal_text(row[2])
    direccion = _normal_text(row[3])
    destino = _normal_text(row[4])
    if not comuna or not rol or not direccion:
        return None
    digest_payload = {
        'comuna': comuna,
        'rol': rol,
        'direccion': direccion,
        'destino': destino,
    }
    digest = payload_hash(digest_payload)[:8].upper()
    return {
        'property_ref': _hash_ref('real-estate-property', digest_payload),
        'codigo_propiedad': f'BR-{digest}',
        'rol_avaluo': rol,
        'direccion': direccion,
        'comuna': comuna.title(),
        'region': REGION_BY_COMUNA.get(_normalized_upper(comuna), 'Region no clasificada'),
        'tipo_inmueble': _tipo_inmueble_from_destino(destino),
        'evidence_ref': f'{registry_ref}#property={index + 1}',
        'contribuciones_clp': '0.00',
        'contribuciones_evidence_ref': '',
        'codigo_f22': 'F22-BIENES-RAICES',
        'source_payload': {
            'source': 'real_estate_registry',
            'rol': rol,
            'rol_tail_key': _role_tail_key(rol),
            'destino': destino,
            'derechos': _normal_text(row[8]),
            'avaluo_fiscal_ref': f'{registry_ref}#property={index + 1}#avaluo',
            'final_tax_calculation': False,
        },
    }


def parse_real_estate_registry_json(data: Any, *, registry_ref: str) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    properties = data.get('properties')
    if not isinstance(properties, list):
        return []
    parsed: list[dict[str, Any]] = []
    seen_codes: set[str] = set()
    for index, row in enumerate(properties):
        if not isinstance(row, list):
            continue
        item = _real_estate_property_from_row(row, registry_ref=registry_ref, index=index)
        if not item or item['codigo_propiedad'] in seen_codes:
            continue
        parsed.append(item)
        seen_codes.add(item['codigo_propiedad'])
    return parsed


def _payment_year(value: Any) -> int:
    match = re.search(r'(?<!\d)(20\d{2})(?!\d)', str(value or ''))
    return int(match.group(1)) if match else 0


def _extract_payment_rows(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    response = data.get('response') if isinstance(data.get('response'), dict) else {}
    body = response.get('body') if isinstance(response.get('body'), dict) else {}
    rows = body.get('data')
    return rows if isinstance(rows, list) else []


def parse_real_estate_contribution_history_json(
    data: Any,
    *,
    commercial_year: int,
    source_ref: str,
) -> dict[str, dict[str, Any]]:
    totals: dict[str, dict[str, Any]] = {}
    for row in _extract_payment_rows(data):
        if not isinstance(row, dict) or _payment_year(row.get('fechaPago')) != commercial_year:
            continue
        for item in row.get('propiedad') or []:
            if not isinstance(item, dict):
                continue
            key = _property_key(
                comuna=item.get('comuna'),
                manzana=item.get('manzana'),
                predio=item.get('predio'),
                rol=item.get('rol'),
            )
            if not key:
                continue
            amount = _parse_int_amount(item.get('valorCuota') or item.get('totalCuota') or 0)
            bucket = totals.setdefault(key, {'amount': 0, 'source_refs': set()})
            bucket['amount'] += amount
            bucket['source_refs'].add(source_ref)
    return {
        key: {
            'amount': value['amount'],
            'source_refs': sorted(value['source_refs']),
        }
        for key, value in totals.items()
    }


def _contribution_totals_by_property_key(
    *,
    manifest: dict[str, Any],
    source_root: Path,
    file_index: dict[str, dict[str, Any]],
    commercial_year: int,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    totals: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for item in _real_estate_support_items(manifest):
        path = _normalized_manifest_path(item)
        if 'historial_pagos' not in path or not path.endswith('.json'):
            continue
        source_ref = str(item.get('path_ref') or '')
        try:
            data = _load_json_source(_source_path(source_root, file_index, source_ref))
            parsed = parse_real_estate_contribution_history_json(
                data,
                commercial_year=commercial_year,
                source_ref=source_ref,
            )
        except ValueError as error:
            errors.append(f'real_estate_contributions:{error}')
            continue
        for key, value in parsed.items():
            bucket = totals.setdefault(key, {'amount': 0, 'source_refs': set()})
            bucket['amount'] += int(value.get('amount') or 0)
            bucket['source_refs'].update(value.get('source_refs') or [])
    return {
        key: {
            'amount': value['amount'],
            'source_refs': sorted(value['source_refs']),
        }
        for key, value in totals.items()
    }, errors


def _complete_real_estate_source(
    *,
    package: dict[str, Any],
    manifest: dict[str, Any],
    source_root: Path,
    file_index: dict[str, dict[str, Any]],
    filled_paths: list[str],
) -> list[str]:
    errors: list[str] = []
    registry_ref = _select_real_estate_registry_ref(manifest)
    if not registry_ref:
        return errors
    commercial_year = int(package.get('commercial_year') or manifest.get('commercial_year') or 0)
    tax_year = int(package.get('tax_year') or manifest.get('tax_year') or commercial_year + 1)
    try:
        registry_data = _load_json_source(_source_path(source_root, file_index, registry_ref))
    except ValueError as error:
        return [f'real_estate_registry:{error}']
    properties = parse_real_estate_registry_json(registry_data, registry_ref=registry_ref)
    if not properties:
        return errors

    contribution_totals, contribution_errors = _contribution_totals_by_property_key(
        manifest=manifest,
        source_root=source_root,
        file_index=file_index,
        commercial_year=commercial_year,
    )
    errors.extend(contribution_errors)
    contribution_source_refs = _real_estate_contribution_source_refs(manifest)
    fallback_contribution_ref = (
        contribution_source_refs[0]
        if contribution_source_refs
        else _hash_ref(
            f'real-estate-contributions-not-found-ac{commercial_year}',
            {
                'registry_ref': registry_ref,
                'commercial_year': commercial_year,
                'tax_year': tax_year,
            },
        )
    )

    for property_payload in properties:
        key_candidates = [
            _normal_text(property_payload.get('rol_avaluo')),
            _normal_text(property_payload.get('source_payload', {}).get('rol_tail_key')),
        ]
        contribution = None
        for key in key_candidates:
            if not key:
                continue
            if key in contribution_totals:
                contribution = contribution_totals[key]
                break
            matches = [
                value
                for contribution_key, value in contribution_totals.items()
                if str(contribution_key).endswith(f'-{key}')
            ]
            if matches:
                contribution = {
                    'amount': sum(int(item.get('amount') or 0) for item in matches),
                    'source_refs': sorted(
                        {
                            source_ref
                            for item in matches
                            for source_ref in (item.get('source_refs') or [])
                        }
                    ),
                }
                break
        if contribution:
            property_payload['contribuciones_clp'] = _money(int(contribution.get('amount') or 0))
            property_payload['contribuciones_evidence_ref'] = str((contribution.get('source_refs') or [''])[0])
            property_payload['source_payload']['contribuciones_source'] = 'historial_pagos_sii'
        else:
            property_payload['contribuciones_clp'] = '0.00'
            property_payload['contribuciones_evidence_ref'] = fallback_contribution_ref
            property_payload['source_payload']['contribuciones_source'] = 'not_found_for_commercial_year'
        property_payload['source_payload']['commercial_year'] = commercial_year
        property_payload['source_payload']['tax_year'] = tax_year

    source_ref = _hash_ref(
        'real-estate-reviewed',
        {
            'registry_ref': registry_ref,
            'contribution_source_refs': contribution_source_refs,
            'property_refs': [item['property_ref'] for item in properties],
            'commercial_year': commercial_year,
            'tax_year': tax_year,
        },
    )
    package['real_estate'] = {
        'source_ref': source_ref,
        'as_of': f'{commercial_year}-12-31',
        'properties': properties,
        'source_payload': {
            'registry_ref': registry_ref,
            'contribution_source_refs_count': len(contribution_source_refs),
            'contribution_history_matches_ac': len(contribution_totals),
            'final_tax_calculation': False,
        },
    }
    filled_paths.extend(
        [
            '$.real_estate',
            '$.real_estate.source_ref',
            '$.real_estate.properties',
        ]
    )
    return errors


def _obligations_from_f29(*, codes: dict[str, int], source_ref: str) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    ppm = codes.get('062')
    if ppm is not None:
        obligations.append(
            {
                'tipo': 'PPM',
                'base_imponible': _money(codes.get('563', 0)),
                'monto_calculado': _money(ppm),
                'source_ref': source_ref,
            }
        )
    retencion = codes.get('048')
    if retencion is not None and retencion > 0:
        obligations.append(
            {
                'tipo': 'RETENCION_IMPUESTO_UNICO',
                'base_imponible': '0.00',
                'monto_calculado': _money(retencion),
                'source_ref': source_ref,
            }
        )
    return obligations


def _extract_annual_ledger_sources(
    *,
    manifest: dict[str, Any],
    source_root: Path,
    file_index: dict[str, dict[str, Any]],
) -> tuple[dict[int, dict[str, Any]], dict[int, dict[str, Any]], dict[str, Any], dict[str, str], list[str]]:
    errors: list[str] = []
    ledger_refs = {
        'libro_diario': _select_annual_ledger_ref(manifest, 'libro_diario'),
        'libro_mayor': _select_annual_ledger_ref(manifest, 'libro_mayor'),
        'libro_inventario': _select_annual_ledger_ref(manifest, 'libro_inventario'),
    }
    diario_by_month: dict[int, dict[str, Any]] = {}
    mayor_by_month: dict[int, dict[str, Any]] = {}
    mayor_annual_lines: dict[str, dict[str, Any]] = {}
    inventario: dict[str, Any] = {'lines': [], 'totals': {}}
    source_refs: dict[str, str] = {}
    diario_ref = str(ledger_refs.get('libro_diario') or '')
    mayor_ref = str(ledger_refs.get('libro_mayor') or '')
    inventario_ref = str(ledger_refs.get('libro_inventario') or '')
    if diario_ref:
        try:
            diario_by_month = parse_libro_diario_text(_extract_text(_source_path(source_root, file_index, diario_ref)))
            source_refs['libro_diario'] = diario_ref
        except ValueError as error:
            errors.append(f'libro_diario:{error}')
    if mayor_ref:
        try:
            mayor_text = _extract_text(_source_path(source_root, file_index, mayor_ref))
            mayor_by_month = parse_libro_mayor_text(mayor_text)
            mayor_annual_lines = parse_libro_mayor_annual_trial_balance_lines(mayor_text)
            source_refs['libro_mayor'] = mayor_ref
        except ValueError as error:
            errors.append(f'libro_mayor:{error}')
    if inventario_ref:
        try:
            inventario = parse_libro_inventario_text(
                _extract_text(_source_path(source_root, file_index, inventario_ref))
            )
            inventario = _merge_inventory_with_mayor_lines(inventario, mayor_annual_lines)
            source_refs['libro_inventario'] = inventario_ref
        except ValueError as error:
            errors.append(f'libro_inventario:{error}')
    return diario_by_month, mayor_by_month, inventario, source_refs, errors


def _labor_previsional_expected_refs(labor: dict[str, Any]) -> list[str]:
    refs = []
    for item in labor.get('source_refs') or []:
        if not isinstance(item, dict):
            continue
        path_ref = str(item.get('path_ref') or '').strip()
        if path_ref and is_non_sensitive_reference(path_ref):
            refs.append(path_ref)
    return sorted(set(refs))


def _complete_labor_previsional_source_ref(
    *,
    package: dict[str, Any],
    reviewed_payroll_refs: set[str],
    filled_paths: list[str],
) -> None:
    labor = package.get('labor_previsional')
    if not isinstance(labor, dict) or labor.get('required') is not True:
        return
    if is_non_sensitive_reference(labor.get('source_ref')):
        return

    expected_refs = _labor_previsional_expected_refs(labor)
    if not expected_refs or not set(expected_refs).issubset(reviewed_payroll_refs):
        return

    source_hash = payload_hash(
        {
            'schema_version': CONTROLLED_VALUES_DRAFT_SCHEMA_VERSION,
            'company_ref': package.get('company_ref', ''),
            'commercial_year': package.get('commercial_year'),
            'tax_year': package.get('tax_year'),
            'labor_previsional_source_refs': expected_refs,
        }
    )[:16]
    labor['source_ref'] = f'labor-previsional-reviewed-{source_hash}'
    labor['status'] = 'reviewed_source_ref_ready'
    labor['reviewed_source_refs_count'] = len(expected_refs)
    labor['final_tax_calculation'] = False
    filled_paths.extend(
        [
            '$.labor_previsional.source_ref',
            '$.labor_previsional.status',
            '$.labor_previsional.reviewed_source_refs_count',
            '$.labor_previsional.final_tax_calculation',
        ]
    )


def _review_labor_previsional_expected_refs(
    *,
    package: dict[str, Any],
    source_root: Path,
    file_index: dict[str, dict[str, Any]],
    reviewed_payroll_refs: set[str],
    extraction_errors: list[str],
) -> None:
    labor = package.get('labor_previsional')
    if not isinstance(labor, dict) or labor.get('required') is not True:
        return

    for path_ref in _labor_previsional_expected_refs(labor):
        if path_ref in reviewed_payroll_refs:
            continue
        try:
            parse_payroll_text(_extract_text(_source_path(source_root, file_index, path_ref)))
        except ValueError as error:
            extraction_errors.append(f'$.labor_previsional.source_refs:{path_ref}:{error}')
            continue
        reviewed_payroll_refs.add(path_ref)


def build_annual_tax_controlled_values_draft(
    *,
    manifest: dict[str, Any],
    template: dict[str, Any],
    source_root: Path,
    responsible_ref: str = '',
    approval_ref: str = '',
) -> dict[str, Any]:
    if not isinstance(manifest, dict) or not isinstance(template, dict):
        raise ValueError('manifest y template deben ser objetos JSON.')
    if template.get('schema_version') != CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION:
        raise ValueError(f'template.schema_version debe ser {CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION}.')
    package = template.get('package_draft')
    if not isinstance(package, dict) or package.get('schema_version') != CONTROLLED_DB_LOAD_SCHEMA_VERSION:
        raise ValueError(f'package_draft.schema_version debe ser {CONTROLLED_DB_LOAD_SCHEMA_VERSION}.')

    draft = copy.deepcopy(template)
    package = draft['package_draft']
    filled_paths: list[str] = []
    extraction_warnings: list[str] = []
    extraction_errors: list[str] = []
    reviewed_payroll_refs: set[str] = set()
    file_index = _manifest_file_index(manifest)
    source_root = source_root.resolve()

    if responsible_ref:
        if not is_non_sensitive_reference(responsible_ref):
            raise ValueError('responsible_ref debe ser una referencia no sensible.')
        package['responsible_ref'] = responsible_ref
        filled_paths.append('$.responsible_ref')
    if approval_ref:
        if not is_non_sensitive_reference(approval_ref):
            raise ValueError('approval_ref debe ser una referencia no sensible.')
        package['approval_ref'] = approval_ref
        filled_paths.append('$.approval_ref')

    diario_by_month, mayor_by_month, inventario, ledger_source_refs, ledger_errors = _extract_annual_ledger_sources(
        manifest=manifest,
        source_root=source_root,
        file_index=file_index,
    )
    extraction_errors.extend(ledger_errors)

    for index, month_payload in enumerate(package.get('months') or []):
        month = int(month_payload.get('month') or 0)
        month_path = f'$.months[{index}]'
        diario = diario_by_month.get(month) or {}
        mayor = mayor_by_month.get(month) or {}

        if diario:
            ledger = month_payload.setdefault('ledger', {})
            if ledger_source_refs.get('libro_diario'):
                ledger['libro_diario_ref'] = f'{ledger_source_refs["libro_diario"]}#month={month:02d}'
                filled_paths.append(f'{month_path}.ledger.libro_diario_ref')
            if ledger_source_refs.get('libro_mayor'):
                ledger['libro_mayor_ref'] = f'{ledger_source_refs["libro_mayor"]}#month={month:02d}'
                filled_paths.append(f'{month_path}.ledger.libro_mayor_ref')
            if diario.get('asientos_count'):
                ledger['asientos_count'] = diario['asientos_count']
                filled_paths.append(f'{month_path}.ledger.asientos_count')
            if diario.get('total_debe') is not None and diario.get('total_haber') is not None:
                ledger['total_debe'] = _money(diario['total_debe'])
                ledger['total_haber'] = _money(diario['total_haber'])
                filled_paths.extend([f'{month_path}.ledger.total_debe', f'{month_path}.ledger.total_haber'])

        if mayor:
            ledger = month_payload.setdefault('ledger', {})
            if mayor.get('cuentas_count'):
                ledger['cuentas_count'] = mayor['cuentas_count']
                filled_paths.append(f'{month_path}.ledger.cuentas_count')
            balance = month_payload.setdefault('balance', {})
            if ledger_source_refs.get('libro_mayor'):
                balance['balance_ref'] = f'{ledger_source_refs["libro_mayor"]}#month={month:02d}'
                filled_paths.append(f'{month_path}.balance.balance_ref')
            balance['total_debe'] = _money(mayor['total_debe'])
            balance['total_haber'] = _money(mayor['total_haber'])
            balance['cuadrado'] = mayor['total_debe'] == mayor['total_haber']
            filled_paths.extend(
                [
                    f'{month_path}.balance.total_debe',
                    f'{month_path}.balance.total_haber',
                    f'{month_path}.balance.cuadrado',
                ]
            )
            if diario and (
                int(diario.get('total_debe') or 0) != int(mayor.get('total_debe') or 0)
                or int(diario.get('total_haber') or 0) != int(mayor.get('total_haber') or 0)
            ):
                extraction_warnings.append(f'{month_path}.ledger_mayor_diario_totals_mismatch')

        if month == 12 and inventario.get('lines'):
            balance = month_payload.setdefault('balance', {})
            if ledger_source_refs.get('libro_inventario'):
                balance['annual_inventory_ref'] = ledger_source_refs['libro_inventario']
                filled_paths.append(f'{month_path}.balance.annual_inventory_ref')
            balance['lineas_balance_8_columnas'] = inventario['lines']
            balance['annual_inventory_totals'] = inventario.get('totals') or {}
            balance['lineas_balance_8_columnas_source'] = 'libro_inventario'
            filled_paths.extend(
                [
                    f'{month_path}.balance.lineas_balance_8_columnas',
                    f'{month_path}.balance.annual_inventory_totals',
                    f'{month_path}.balance.lineas_balance_8_columnas_source',
                ]
            )

        f29_ref = _first_ref((month_payload.get('input_source_refs') or {}).get('f29_support_input') or [])
        if f29_ref:
            path_ref = str(f29_ref.get('path_ref') or '')
            try:
                f29_data = parse_f29_text(_extract_text(_source_path(source_root, file_index, path_ref)))
                f29 = month_payload.setdefault('f29', {})
                f29['estado_preparacion'] = 'preparado'
                f29['borrador_ref'] = path_ref
                f29['resumen'] = {
                    'source_ref': path_ref,
                    'periodo': f29_data.get('periodo', ''),
                    'codes': {code: _money(value) for code, value in sorted((f29_data.get('codes') or {}).items())},
                    'extraction': 'pdftotext-controlled',
                }
                month_payload['obligations'] = _obligations_from_f29(
                    codes=f29_data.get('codes') or {},
                    source_ref=path_ref,
                )
                filled_paths.extend([f'{month_path}.f29.borrador_ref', f'{month_path}.f29.resumen'])
                if month_payload['obligations']:
                    filled_paths.append(f'{month_path}.obligations')
            except ValueError as error:
                extraction_errors.append(f'{month_path}.f29:{error}')

        payroll_ref = _first_ref((month_payload.get('input_source_refs') or {}).get('payroll_support') or [])
        if payroll_ref:
            path_ref = str(payroll_ref.get('path_ref') or '')
            try:
                payroll_data = parse_payroll_text(_extract_text(_source_path(source_root, file_index, path_ref)))
                payroll = month_payload.setdefault('payroll', {})
                payroll['source_ref'] = path_ref
                payroll['has_movements'] = bool(payroll_data['has_movements'])
                payroll['resumen'] = {
                    'source_ref': path_ref,
                    'total_general_detected': payroll_data['total_general_detected'],
                    'numbers_detected': payroll_data['numbers_detected'],
                    'extraction': 'pdftotext-controlled',
                }
                reviewed_payroll_refs.add(path_ref)
                filled_paths.extend([f'{month_path}.payroll.source_ref', f'{month_path}.payroll.has_movements'])
            except ValueError as error:
                extraction_errors.append(f'{month_path}.payroll:{error}')

    _review_labor_previsional_expected_refs(
        package=package,
        source_root=source_root,
        file_index=file_index,
        reviewed_payroll_refs=reviewed_payroll_refs,
        extraction_errors=extraction_errors,
    )
    _complete_labor_previsional_source_ref(
        package=package,
        reviewed_payroll_refs=reviewed_payroll_refs,
        filled_paths=filled_paths,
    )
    extraction_errors.extend(
        _complete_real_estate_source(
            package=package,
            manifest=manifest,
            source_root=source_root,
            file_index=file_index,
            filled_paths=filled_paths,
        )
    )
    labor_previsional = package.get('labor_previsional') if isinstance(package.get('labor_previsional'), dict) else {}
    real_estate = package.get('real_estate') if isinstance(package.get('real_estate'), dict) else {}
    draft['values_draft_summary'] = {
        'schema_version': CONTROLLED_VALUES_DRAFT_SCHEMA_VERSION,
        'source_root_ref': manifest.get('source_root_ref', ''),
        'filled_paths_count': len(set(filled_paths)),
        'filled_paths_sample': sorted(set(filled_paths))[:30],
        'extraction_warnings': extraction_warnings,
        'extraction_errors': extraction_errors,
        'labor_previsional_source_ref_ready': is_non_sensitive_reference(labor_previsional.get('source_ref')),
        'labor_previsional_reviewed_source_refs_count': len(reviewed_payroll_refs),
        'real_estate_source_ref_ready': is_non_sensitive_reference(real_estate.get('source_ref')),
        'real_estate_properties_count': len(real_estate.get('properties') or []),
        'writes_database': False,
        'uses_expected_outputs_as_inputs': False,
        'uses_sii_real': False,
        'copies_source_files': False,
    }
    return draft


def load_values_draft_json(raw: str) -> dict[str, Any]:
    import json

    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('El JSON debe ser un objeto.')
    return payload
