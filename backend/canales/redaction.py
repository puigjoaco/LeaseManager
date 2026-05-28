from core.reference_validation import (
    REDACTED_SENSITIVE_REFERENCE,
    SENSITIVE_REFERENCE_PATTERN,
    key_looks_sensitive,
)

from .models import CHANNEL_GATE_ALLOWED_SENSITIVE_REF_KEYS


def redact_channel_gate_restrictions(value, *, _sensitive_key=False):
    allowed_sensitive_keys = set(CHANNEL_GATE_ALLOWED_SENSITIVE_REF_KEYS)
    if isinstance(value, str):
        if _sensitive_key or SENSITIVE_REFERENCE_PATTERN.search(value):
            return REDACTED_SENSITIVE_REFERENCE
        return value
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            key_is_sensitive = (
                isinstance(key, str)
                and key not in allowed_sensitive_keys
                and key_looks_sensitive(key)
            )
            redacted[key] = redact_channel_gate_restrictions(
                item,
                _sensitive_key=_sensitive_key or key_is_sensitive,
            )
        return redacted
    if isinstance(value, (list, tuple, set)):
        return [redact_channel_gate_restrictions(item, _sensitive_key=_sensitive_key) for item in value]
    if _sensitive_key and value is not None:
        return REDACTED_SENSITIVE_REFERENCE
    return value
