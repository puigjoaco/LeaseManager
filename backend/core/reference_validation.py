import re


SENSITIVE_REFERENCE_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
)


def normalize_reference(value):
    return str(value or '').strip()


def is_non_sensitive_reference(value):
    normalized = normalize_reference(value)
    return bool(normalized) and not SENSITIVE_REFERENCE_PATTERN.search(normalized)


def contains_sensitive_reference(value):
    if isinstance(value, str):
        return bool(SENSITIVE_REFERENCE_PATTERN.search(value))
    if isinstance(value, dict):
        return any(contains_sensitive_reference(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(contains_sensitive_reference(item) for item in value)
    return False
