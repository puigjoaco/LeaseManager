import re


SENSITIVE_REFERENCE_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
)
SENSITIVE_REFERENCE_KEY_ALIASES = {
    'authorization',
    'authorizationheader',
    'authheader',
    'privatekey',
}
CHILEAN_RUT_REFERENCE_PATTERN = re.compile(r'(?<!\d)\d{1,2}\.?\d{3}\.?\d{3}-[\dkK](?!\d)')
LOCAL_ABSOLUTE_PATH_REFERENCE_PATTERN = re.compile(r'(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\)')
REDACTED_SENSITIVE_REFERENCE = '<redacted-sensitive-reference>'


def normalize_reference(value):
    return str(value or '').strip()


def is_non_sensitive_reference(value):
    normalized = normalize_reference(value)
    return bool(normalized) and not SENSITIVE_REFERENCE_PATTERN.search(normalized)


def key_looks_sensitive(value):
    normalized = normalize_reference(value)
    compact = re.sub(r'[\s_-]+', '', normalized.lower())
    return bool(normalized) and (
        bool(SENSITIVE_REFERENCE_PATTERN.search(normalized))
        or compact in SENSITIVE_REFERENCE_KEY_ALIASES
    )


def contains_chilean_rut_reference(value):
    return bool(CHILEAN_RUT_REFERENCE_PATTERN.search(normalize_reference(value)))


def count_chilean_rut_references(value):
    return len(CHILEAN_RUT_REFERENCE_PATTERN.findall(normalize_reference(value)))


def contains_local_absolute_path_reference(value):
    return bool(LOCAL_ABSOLUTE_PATH_REFERENCE_PATTERN.search(normalize_reference(value)))


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
                or bool(isinstance(key, str) and key_looks_sensitive(key)),
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [redact_sensitive_payload(item, _sensitive_key=_sensitive_key) for item in value]
    if _sensitive_key and value is not None:
        return REDACTED_SENSITIVE_REFERENCE
    return value


def redact_sensitive_payload_values(value):
    if isinstance(value, str):
        if SENSITIVE_REFERENCE_PATTERN.search(value):
            return REDACTED_SENSITIVE_REFERENCE
        return value
    if isinstance(value, dict):
        return {key: redact_sensitive_payload_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [redact_sensitive_payload_values(item) for item in value]
    return value


def contains_sensitive_reference(
    value,
    *,
    include_sensitive_keys=False,
    allowed_sensitive_keys=(),
    _sensitive_key=False,
):
    allowed_sensitive_keys = {str(key) for key in allowed_sensitive_keys}
    if isinstance(value, str):
        return _sensitive_key or bool(SENSITIVE_REFERENCE_PATTERN.search(value))
    if isinstance(value, dict):
        return any(
            contains_sensitive_reference(
                item,
                include_sensitive_keys=include_sensitive_keys,
                allowed_sensitive_keys=allowed_sensitive_keys,
                _sensitive_key=_sensitive_key
                or bool(
                    include_sensitive_keys
                    and isinstance(key, str)
                    and key not in allowed_sensitive_keys
                    and key_looks_sensitive(key)
                ),
            )
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple, set)):
        return any(
            contains_sensitive_reference(
                item,
                include_sensitive_keys=include_sensitive_keys,
                allowed_sensitive_keys=allowed_sensitive_keys,
                _sensitive_key=_sensitive_key,
            )
            for item in value
        )
    if _sensitive_key:
        return True
    return False
