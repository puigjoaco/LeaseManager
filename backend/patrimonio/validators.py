import re

from django.core.exceptions import ValidationError


RUT_BODY_RE = re.compile(r'^\d+$')


def normalize_rut(value):
    if value is None:
        raise ValidationError('El RUT es obligatorio.')

    normalized = re.sub(r'[^0-9kK]', '', str(value)).upper()
    if len(normalized) < 2:
        raise ValidationError('El RUT debe incluir cuerpo y digito verificador.')

    body = normalized[:-1]
    verifier = normalized[-1]

    if not RUT_BODY_RE.match(body):
        raise ValidationError('El cuerpo del RUT debe contener solo numeros.')

    return f'{int(body)}-{verifier}'


def validate_rut(value):
    normalized = normalize_rut(value)
    body, verifier = normalized.split('-')

    reversed_digits = map(int, reversed(body))
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    factor_index = 0

    for digit in reversed_digits:
        total += digit * factors[factor_index]
        factor_index = (factor_index + 1) % len(factors)

    remainder = 11 - (total % 11)
    if remainder == 11:
        expected_verifier = '0'
    elif remainder == 10:
        expected_verifier = 'K'
    else:
        expected_verifier = str(remainder)

    if verifier != expected_verifier:
        raise ValidationError('El RUT no es valido.')

    return normalized
