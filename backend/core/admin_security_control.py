from datetime import date

from django.utils import timezone

from .reference_validation import contains_sensitive_reference, is_non_sensitive_reference


ADMIN_SECURITY_SETTING_KEY = 'security.admin_mfa_control'


def _truthy(value):
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'si', 'sí'}
    return False


def _parse_iso_date(value):
    if isinstance(value, date):
        return value
    raw_value = str(value or '').strip()
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _sensitive_reference(value):
    normalized = str(value or '').strip()
    return bool(normalized) and not is_non_sensitive_reference(normalized)


def _issue(code, message):
    return {
        'code': code,
        'message': message,
    }


def evaluate_admin_security_control(value, *, setting_present=True, today=None):
    payload = value if isinstance(value, dict) else {}
    current_date = today or timezone.localdate()

    mode = str(payload.get('mode') or '').strip().lower()
    mfa_enforced = _truthy(payload.get('mfa_enforced')) or mode == 'mfa_enforced'
    risk_accepted = _truthy(payload.get('risk_accepted')) or mode == 'risk_accepted'

    mfa_evidence_ref = payload.get('mfa_evidence_ref') or payload.get('evidence_ref')
    risk_acceptance_ref = payload.get('risk_acceptance_ref') or payload.get('evidence_ref')
    authorization_ref = payload.get('authorization_ref')
    responsible_ref = payload.get('responsible_ref')
    valid_until = _parse_iso_date(payload.get('valid_until') or payload.get('risk_valid_until'))

    refs = {
        'mfa_evidence_ref': is_non_sensitive_reference(mfa_evidence_ref),
        'risk_acceptance_ref': is_non_sensitive_reference(risk_acceptance_ref),
        'authorization_ref': is_non_sensitive_reference(authorization_ref),
        'responsible_ref': is_non_sensitive_reference(responsible_ref),
    }
    refs_sensitive = {
        'mfa_evidence_ref': _sensitive_reference(mfa_evidence_ref),
        'risk_acceptance_ref': _sensitive_reference(risk_acceptance_ref),
        'authorization_ref': _sensitive_reference(authorization_ref),
        'responsible_ref': _sensitive_reference(responsible_ref),
    }
    payload_sensitive = contains_sensitive_reference(payload, include_sensitive_keys=True)
    risk_acceptance_current = bool(valid_until and valid_until >= current_date)

    issues = []
    if not setting_present:
        issues.append(
            _issue(
                'observability.admin_security_mfa_or_risk_acceptance_missing',
                'Operacion productiva requiere MFA administrativo probado o aceptacion formal de riesgo vigente.',
            )
        )
    elif payload_sensitive:
        issues.append(
            _issue(
                'observability.admin_security_payload_sensitive',
                'El control de seguridad administrativa contiene payload sensible.',
            )
        )
    elif not (mfa_enforced or risk_accepted):
        issues.append(
            _issue(
                'observability.admin_security_mfa_or_risk_acceptance_missing',
                'Operacion productiva requiere MFA administrativo probado o aceptacion formal de riesgo vigente.',
            )
        )

    if setting_present and not payload_sensitive and mfa_enforced:
        for key, missing_code, sensitive_code, missing_message, sensitive_message in [
            (
                'mfa_evidence_ref',
                'observability.admin_security_mfa_evidence_ref_missing',
                'observability.admin_security_mfa_evidence_ref_sensitive',
                'MFA administrativo requiere evidencia_ref no sensible.',
                'MFA administrativo contiene evidencia_ref sensible.',
            ),
            (
                'authorization_ref',
                'observability.admin_security_authorization_ref_missing',
                'observability.admin_security_authorization_ref_sensitive',
                'MFA administrativo requiere authorization_ref no sensible.',
                'MFA administrativo contiene authorization_ref sensible.',
            ),
            (
                'responsible_ref',
                'observability.admin_security_responsible_ref_missing',
                'observability.admin_security_responsible_ref_sensitive',
                'MFA administrativo requiere responsible_ref no sensible.',
                'MFA administrativo contiene responsible_ref sensible.',
            ),
        ]:
            if refs_sensitive[key]:
                issues.append(_issue(sensitive_code, sensitive_message))
            elif not refs[key]:
                issues.append(_issue(missing_code, missing_message))

    if setting_present and not payload_sensitive and risk_accepted:
        for key, missing_code, sensitive_code, missing_message, sensitive_message in [
            (
                'risk_acceptance_ref',
                'observability.admin_security_risk_acceptance_ref_missing',
                'observability.admin_security_risk_acceptance_ref_sensitive',
                'La aceptacion formal de riesgo MFA requiere risk_acceptance_ref no sensible.',
                'La aceptacion formal de riesgo MFA contiene risk_acceptance_ref sensible.',
            ),
            (
                'authorization_ref',
                'observability.admin_security_authorization_ref_missing',
                'observability.admin_security_authorization_ref_sensitive',
                'La aceptacion formal de riesgo MFA requiere authorization_ref no sensible.',
                'La aceptacion formal de riesgo MFA contiene authorization_ref sensible.',
            ),
            (
                'responsible_ref',
                'observability.admin_security_responsible_ref_missing',
                'observability.admin_security_responsible_ref_sensitive',
                'La aceptacion formal de riesgo MFA requiere responsible_ref no sensible.',
                'La aceptacion formal de riesgo MFA contiene responsible_ref sensible.',
            ),
        ]:
            if refs_sensitive[key]:
                issues.append(_issue(sensitive_code, sensitive_message))
            elif not refs[key]:
                issues.append(_issue(missing_code, missing_message))
        if valid_until is None:
            issues.append(
                _issue(
                    'observability.admin_security_risk_acceptance_expiry_missing',
                    'La aceptacion formal de riesgo MFA requiere valid_until ISO vigente.',
                )
            )
        elif not risk_acceptance_current:
            issues.append(
                _issue(
                    'observability.admin_security_risk_acceptance_expired',
                    'La aceptacion formal de riesgo MFA esta vencida.',
                )
            )

    authorized = (
        not issues
        and (
            (
                mfa_enforced
                and refs['mfa_evidence_ref']
                and refs['authorization_ref']
                and refs['responsible_ref']
            )
            or (
                risk_accepted
                and refs['risk_acceptance_ref']
                and refs['authorization_ref']
                and refs['responsible_ref']
                and risk_acceptance_current
            )
        )
    )

    return {
        'setting_key': ADMIN_SECURITY_SETTING_KEY,
        'setting_present': setting_present,
        'mfa_enforced': mfa_enforced,
        'risk_accepted': risk_accepted,
        'risk_acceptance_current': risk_acceptance_current,
        'valid_until': valid_until.isoformat() if valid_until else None,
        'authorized_for_stage7_close': authorized,
        'refs': refs,
        'refs_sensitive': refs_sensitive,
        'payload_sensitive': payload_sensitive,
    }, issues
