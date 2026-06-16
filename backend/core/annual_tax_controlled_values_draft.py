from __future__ import annotations

import copy
import re
import subprocess
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.annual_tax_controlled_db_load import CONTROLLED_DB_LOAD_SCHEMA_VERSION
from core.annual_tax_controlled_package_template import CONTROLLED_DB_LOAD_TEMPLATE_SCHEMA_VERSION
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


def _parse_int_amount(raw: str) -> int:
    text = str(raw or '').strip().replace('.', '').replace(',', '.')
    if not text:
        return 0
    return int(Decimal(text))


def _money(value: int) -> str:
    return f'{int(value)}.00'


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
        item.get('artifact_key'): item.get('path_ref')
        for item in manifest.get('files') or []
        if item.get('category') == 'annual_ledger_input'
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
                filled_paths.extend([f'{month_path}.payroll.source_ref', f'{month_path}.payroll.has_movements'])
            except ValueError as error:
                extraction_errors.append(f'{month_path}.payroll:{error}')

    draft['values_draft_summary'] = {
        'schema_version': CONTROLLED_VALUES_DRAFT_SCHEMA_VERSION,
        'source_root_ref': manifest.get('source_root_ref', ''),
        'filled_paths_count': len(set(filled_paths)),
        'filled_paths_sample': sorted(set(filled_paths))[:30],
        'extraction_warnings': extraction_warnings,
        'extraction_errors': extraction_errors,
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
