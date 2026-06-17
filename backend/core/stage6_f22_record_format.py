from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sii.models import is_safe_public_sii_source_url


F22_RECORD_FORMAT_VERSION = 'f22-at2026-fixed-width-record-v1'
F22_RECORD_FORMAT_SOURCE_URL = 'https://alerce.sii.cl/dior/ren_mp/pdf/6_Formato_de_Registro_F22_AT2026.pdf'
F22_RECORD_LENGTH = 90


@dataclass(frozen=True)
class F22FieldSpec:
    key: str
    start: int
    end: int
    kind: str
    required_value: str | None = None
    allowed_values: tuple[str, ...] = ()

    @property
    def length(self) -> int:
        return self.end - self.start + 1


TYPE0_FIELDS = (
    F22FieldSpec('record_type', 1, 1, 'numeric', required_value='0'),
    F22FieldSpec('tax_year', 2, 5, 'numeric'),
    F22FieldSpec('form_number', 6, 9, 'numeric', required_value='0022'),
    F22FieldSpec('rut_number', 10, 17, 'numeric'),
    F22FieldSpec('rut_dv', 18, 18, 'char'),
    F22FieldSpec('total_records', 19, 23, 'numeric'),
    F22FieldSpec('company_code', 24, 25, 'char'),
    F22FieldSpec('client_number', 26, 31, 'numeric'),
    F22FieldSpec('declarant_checksum', 32, 41, 'numeric'),
    F22FieldSpec('sii_checksum', 42, 51, 'numeric', required_value='0000000000'),
    F22FieldSpec('presentation_code', 52, 52, 'char', allowed_values=('F', 'I')),
    F22FieldSpec('declaration_type', 53, 53, 'char', allowed_values=('O', 'R')),
    F22FieldSpec('folio', 54, 62, 'numeric'),
    F22FieldSpec('send_day', 63, 64, 'numeric'),
    F22FieldSpec('send_month', 65, 66, 'numeric'),
    F22FieldSpec('send_year', 67, 70, 'numeric'),
    F22FieldSpec('send_hour', 71, 72, 'numeric'),
    F22FieldSpec('send_minute', 73, 74, 'numeric'),
    F22FieldSpec('send_second', 75, 78, 'numeric'),
    F22FieldSpec('version_number', 79, 81, 'numeric'),
    F22FieldSpec('attention_number', 82, 89, 'numeric'),
    F22FieldSpec('filler', 90, 90, 'char', required_value='0'),
)

TYPE1_FIELDS = (
    F22FieldSpec('record_type', 1, 1, 'numeric', required_value='1'),
    F22FieldSpec('entry_1_code', 2, 5, 'numeric'),
    F22FieldSpec('entry_1_sign', 6, 6, 'char'),
    F22FieldSpec('entry_1_value', 7, 21, 'char'),
    F22FieldSpec('entry_2_code', 22, 25, 'numeric'),
    F22FieldSpec('entry_2_sign', 26, 26, 'char'),
    F22FieldSpec('entry_2_value', 27, 41, 'char'),
    F22FieldSpec('entry_3_code', 42, 45, 'numeric'),
    F22FieldSpec('entry_3_sign', 46, 46, 'char'),
    F22FieldSpec('entry_3_value', 47, 61, 'char'),
    F22FieldSpec('entry_4_code', 62, 65, 'numeric'),
    F22FieldSpec('entry_4_sign', 66, 66, 'char'),
    F22FieldSpec('entry_4_value', 67, 81, 'char'),
    F22FieldSpec('filler', 82, 90, 'char'),
)


def _field_payload(field: F22FieldSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'key': field.key,
        'start': field.start,
        'end': field.end,
        'length': field.length,
        'kind': field.kind,
    }
    if field.required_value is not None:
        payload['required_value'] = field.required_value
    if field.allowed_values:
        payload['allowed_values'] = list(field.allowed_values)
    return payload


def build_f22_record_format_contract(*, anio_tributario: int = 2026) -> dict[str, Any]:
    return {
        'schema_version': F22_RECORD_FORMAT_VERSION,
        'anio_tributario': int(anio_tributario),
        'source_url': F22_RECORD_FORMAT_SOURCE_URL,
        'record_length': F22_RECORD_LENGTH,
        'boundary': {
            'fixed_width_record_contract': True,
            'official_submission_allowed': False,
            'final_tax_calculation': False,
            'requires_certification_code': True,
            'requires_responsible_review': True,
        },
        'records': {
            '0': {
                'description': 'Datos para internet y cabecera de envio F22.',
                'fields': [_field_payload(field) for field in TYPE0_FIELDS],
            },
            '1': {
                'description': 'Datos de la declaracion y del declarante, cuatro codigos por registro.',
                'fields': [_field_payload(field) for field in TYPE1_FIELDS],
            },
        },
    }


def validate_f22_record_format_contract(contract: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if contract.get('schema_version') != F22_RECORD_FORMAT_VERSION:
        issues.append('schema_version_mismatch')
    if contract.get('record_length') != F22_RECORD_LENGTH:
        issues.append('record_length_mismatch')
    if not is_safe_public_sii_source_url(contract.get('source_url')):
        issues.append('source_url_not_safe_public_sii')

    boundary = contract.get('boundary') or {}
    if boundary.get('official_submission_allowed') is True:
        issues.append('official_submission_must_remain_blocked')
    if boundary.get('final_tax_calculation') is True:
        issues.append('final_tax_calculation_must_remain_blocked')

    for record_type, expected_specs in {'0': TYPE0_FIELDS, '1': TYPE1_FIELDS}.items():
        record = (contract.get('records') or {}).get(record_type) or {}
        fields = record.get('fields') or []
        if len(fields) != len(expected_specs):
            issues.append(f'record_{record_type}.field_count_mismatch')
            continue
        expected_start = 1
        for field, expected in zip(fields, expected_specs):
            if field.get('key') != expected.key:
                issues.append(f"record_{record_type}.{expected.key}.key_mismatch")
            if field.get('start') != expected.start or field.get('end') != expected.end:
                issues.append(f"record_{record_type}.{expected.key}.position_mismatch")
            if field.get('start') != expected_start:
                issues.append(f"record_{record_type}.{expected.key}.gap_or_overlap")
            if field.get('length') != expected.length:
                issues.append(f"record_{record_type}.{expected.key}.length_mismatch")
            expected_start = expected.end + 1
        if expected_start - 1 != F22_RECORD_LENGTH:
            issues.append(f'record_{record_type}.record_length_not_covered')

    return issues


def _slice(line: str, field: F22FieldSpec) -> str:
    return line[field.start - 1:field.end]


def validate_f22_fixed_width_record(line: str) -> list[str]:
    value = str(line)
    issues: list[str] = []
    if len(value) != F22_RECORD_LENGTH:
        return [f'length_mismatch:{len(value)}']
    record_type = value[0]
    if record_type == '0':
        fields = TYPE0_FIELDS
    elif record_type == '1':
        fields = TYPE1_FIELDS
    else:
        return [f'unknown_record_type:{record_type}']

    for field in fields:
        raw = _slice(value, field)
        if len(raw) != field.length:
            issues.append(f'{field.key}.length_mismatch')
        if field.required_value is not None and raw != field.required_value:
            issues.append(f'{field.key}.required_value_mismatch')
        if field.allowed_values and raw not in field.allowed_values:
            issues.append(f'{field.key}.invalid_value')
        if field.kind == 'numeric' and not raw.isdigit():
            issues.append(f'{field.key}.not_numeric')

    if record_type == '0':
        rut_number = _slice(value, TYPE0_FIELDS[3])
        rut_dv = _slice(value, TYPE0_FIELDS[4]).upper()
        if int(rut_number) <= 0:
            issues.append('rut_number.must_be_positive')
        if rut_dv not in '0123456789K':
            issues.append('rut_dv.invalid_mod11_character')

    return issues


def _numeric(value: int | str, length: int) -> str:
    text = str(value).strip()
    if not text.isdigit():
        raise ValueError('numeric field requires digits')
    if len(text) > length:
        raise ValueError(f'numeric field exceeds length {length}')
    return text.zfill(length)


def _text(value: str, length: int, *, pad: str = ' ') -> str:
    text = str(value or '').strip().upper()
    if len(text) > length:
        raise ValueError(f'text field exceeds length {length}')
    return text.ljust(length, pad)


def build_f22_type0_record(
    *,
    anio_tributario: int,
    rut_number: int | str,
    rut_dv: str,
    total_records: int,
    company_code: str,
    client_number: int | str,
    declarant_checksum: int | str = 0,
    presentation_code: str = 'I',
    declaration_type: str = 'O',
    folio: int | str = 0,
    send_day: int | str = 0,
    send_month: int | str = 0,
    send_year: int | str = 0,
    send_hour: int | str = 0,
    send_minute: int | str = 0,
    send_second: int | str = 0,
    version_number: int | str = 0,
    attention_number: int | str = 0,
) -> str:
    parts = [
        '0',
        _numeric(anio_tributario, 4),
        '0022',
        _numeric(rut_number, 8),
        _text(rut_dv, 1),
        _numeric(total_records, 5),
        _text(company_code, 2),
        _numeric(client_number, 6),
        _numeric(declarant_checksum, 10),
        '0000000000',
        _text(presentation_code, 1),
        _text(declaration_type, 1),
        _numeric(folio, 9),
        _numeric(send_day, 2),
        _numeric(send_month, 2),
        _numeric(send_year, 4),
        _numeric(send_hour, 2),
        _numeric(send_minute, 2),
        _numeric(send_second, 4),
        _numeric(version_number, 3),
        _numeric(attention_number, 8),
        '0',
    ]
    line = ''.join(parts)
    issues = validate_f22_fixed_width_record(line)
    if issues:
        raise ValueError('; '.join(issues))
    return line


def build_f22_type1_record(entries: list[dict[str, Any]]) -> str:
    if len(entries) > 4:
        raise ValueError('type 1 record accepts at most 4 entries')
    parts = ['1']
    for index in range(4):
        entry = entries[index] if index < len(entries) else {}
        code = entry.get('code', 0)
        sign = entry.get('sign', '')
        value = entry.get('value', '')
        parts.append(_numeric(code, 4))
        parts.append(_text(sign, 1))
        parts.append(_text(str(value), 15))
    parts.append(_text('', 9))
    line = ''.join(parts)
    issues = validate_f22_fixed_width_record(line)
    if issues:
        raise ValueError('; '.join(issues))
    return line
