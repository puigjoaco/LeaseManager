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


def redact_sensitive_payload(value, *, _sensitive_key=False):
    if isinstance(value, str):
        if _sensitive_key or SENSITIVE_REFERENCE_PATTERN.search(value):
            return REDACTED_SENSITIVE_REFERENCE
        return value
    if isinstance(value, dict):
        return {
            key: redact_sensitive_payload(
                item,
                _sensitive_key=_sensitive_key
                or bool(isinstance(key, str) and SENSITIVE_REFERENCE_PATTERN.search(key)),
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact_sensitive_payload(item, _sensitive_key=_sensitive_key) for item in value]
    if _sensitive_key and value is not None:
        return REDACTED_SENSITIVE_REFERENCE
    return value


def contains_sensitive_reference(value, *, include_sensitive_keys=False, _sensitive_key=False):
    if isinstance(value, str):
        return _sensitive_key or bool(SENSITIVE_REFERENCE_PATTERN.search(value))
    if isinstance(value, dict):
        return any(
            contains_sensitive_reference(
                item,
                include_sensitive_keys=include_sensitive_keys,
                _sensitive_key=_sensitive_key
                or bool(include_sensitive_keys and isinstance(key, str) and SENSITIVE_REFERENCE_PATTERN.search(key)),
            )
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(
            contains_sensitive_reference(
                item,
                include_sensitive_keys=include_sensitive_keys,
                _sensitive_key=_sensitive_key,
            )
            for item in value
        )
    if _sensitive_key and value is not None:
        return True
    return False
