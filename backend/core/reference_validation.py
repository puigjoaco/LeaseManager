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
