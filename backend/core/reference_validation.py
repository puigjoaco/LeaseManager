import re


SENSITIVE_REFERENCE_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
)
REDACTED_SENSITIVE_REFERENCE = '<redacted-sensitive-reference>'


def normalize_reference(value):
    return str(value or '').strip()


def is_non_sensitive_reference(value):
    normalized = normalize_reference(value)
    return bool(normalized) and not SENSITIVE_REFERENCE_PATTERN.search(normalized)


def redact_sensitive_reference(value):
    normalized = normalize_reference(value)
    if not normalized:
        return ''
    if SENSITIVE_REFERENCE_PATTERN.search(normalized):
        return REDACTED_SENSITIVE_REFERENCE
    return normalized


def contains_sensitive_reference(value):
    if isinstance(value, str):
        return bool(SENSITIVE_REFERENCE_PATTERN.search(value))
    if isinstance(value, dict):
        return any(contains_sensitive_reference(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(contains_sensitive_reference(item) for item in value)
    return False
