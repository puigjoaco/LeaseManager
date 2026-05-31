import hashlib
import json
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.reference_validation import contains_sensitive_reference
from reporting.services import (
    build_annual_tax_summary,
    build_financial_monthly_summary,
    build_operational_dashboard,
    build_partner_summary,
    build_period_books_summary,
)

from .audit import EXPORT_PREPARED_EVENT_TYPE, EXPORT_REVOKED_EVENT_TYPE, create_export_audit_event
from .models import (
    CategoriaDato,
    EstadoExportacionSensible,
    EstadoRegistro,
    EXPORT_CREATED_BY_REQUIRED_ERROR,
    EXPORT_MOTIVE_REQUIRED_ERROR,
    ExportacionSensible,
    SENSITIVE_EXPORT_MAX_DAYS,
    PoliticaRetencionDatos,
    SECRET_EXPORT_ERROR,
)


MAX_EXPORT_DAYS = SENSITIVE_EXPORT_MAX_DAYS
SENSITIVE_EXPORT_METADATA_ERROR = 'La metadata visible de exportacion no puede contener referencias sensibles.'
ACTIVE_RETENTION_POLICY_ERROR = 'No existe una politica de retencion activa para la categoria indicada.'
PAYLOAD_HASH_MISMATCH_ERROR = 'La integridad de la exportacion no coincide con su payload_hash.'
PAYLOAD_UNREADABLE_ERROR = 'El payload cifrado de la exportacion sensible no puede descifrarse.'
EXPORT_ALREADY_REVOKED_ERROR = 'La exportacion ya fue revocada y no puede revocarse nuevamente.'
EXPIRED_EXPORT_REVOKE_ERROR = 'La exportacion expirada es terminal y no puede revocarse.'
REVOCATION_REASON_REQUIRED_ERROR = 'La revocacion de exportaciones sensibles requiere un motivo trazable.'
REVOCATION_REASON_SENSITIVE_ERROR = (
    'El motivo de revocacion no puede contener URLs, correos, tokens, bearer, claves ni credenciales.'
)
EXPORT_KIND_CATEGORY_MAP = {
    'dashboard_operativo': CategoriaDato.OPERATIONAL,
    'financiero_mensual': CategoriaDato.FINANCIAL,
    'tributario_anual': CategoriaDato.TAX,
    'socio_resumen': CategoriaDato.DOCUMENT,
    'libros_periodo': CategoriaDato.FINANCIAL,
}


def build_encrypted_export_ref(export_kind, payload_hash):
    return f'export-ref-{export_kind}-{payload_hash[:12]}'


def _choice_value(value):
    return getattr(value, 'value', value)


def get_fernet():
    return Fernet(settings.DATA_EXPORT_ENCRYPTION_KEY.encode('ascii'))


def _canonical_payload_bytes(payload):
    return json.dumps(payload, sort_keys=True, ensure_ascii=True).encode('utf-8')


def _payload_hash(payload):
    return hashlib.sha256(_canonical_payload_bytes(payload)).hexdigest()


def render_export_payload(export_kind, params, access=None):
    if export_kind == 'dashboard_operativo':
        return build_operational_dashboard(access=access)
    if export_kind == 'financiero_mensual':
        return build_financial_monthly_summary(params['anio'], params['mes'], params.get('empresa_id'), access=access)
    if export_kind == 'tributario_anual':
        return build_annual_tax_summary(params['anio_tributario'], params.get('empresa_id'), access=access)
    if export_kind == 'socio_resumen':
        return build_partner_summary(params['socio_id'], access=access)
    if export_kind == 'libros_periodo':
        return build_period_books_summary(params['empresa_id'], params['periodo'], access=access)
    raise ValueError('Tipo de exportacion no soportado.')


def encrypt_payload(payload):
    raw = _canonical_payload_bytes(payload)
    token = get_fernet().encrypt(raw).decode('ascii')
    payload_hash = hashlib.sha256(raw).hexdigest()
    return token, payload_hash


def decrypt_payload(token):
    raw = get_fernet().decrypt(token.encode('ascii'))
    return json.loads(raw.decode('utf-8'))


def payload_hash_matches(payload, expected_hash):
    return _payload_hash(payload) == expected_hash.strip().lower()


def inspect_export_payload_integrity(export):
    try:
        payload = decrypt_payload(export.encrypted_payload)
    except (InvalidToken, TypeError, ValueError, UnicodeError):
        return 'unreadable'
    if not payload_hash_matches(payload, export.payload_hash):
        return 'mismatch'
    return 'ok'


def export_payload_hash_matches(export):
    return inspect_export_payload_integrity(export) == 'ok'


def ensure_export_metadata_is_non_sensitive(*, scope_resumen, motivo):
    if contains_sensitive_reference(motivo, include_sensitive_keys=True) or contains_sensitive_reference(
        scope_resumen,
        include_sensitive_keys=True,
    ):
        raise ValueError(SENSITIVE_EXPORT_METADATA_ERROR)


def validate_sensitive_export_controls(*, categoria_dato, export_kind):
    category_value = _choice_value(categoria_dato)
    if category_value == _choice_value(CategoriaDato.SECRET):
        raise ValidationError({'categoria_dato': SECRET_EXPORT_ERROR})

    expected_category = EXPORT_KIND_CATEGORY_MAP.get(export_kind)
    if expected_category is None:
        raise ValueError('Tipo de exportacion no soportado.')

    expected_value = _choice_value(expected_category)
    if category_value != expected_value:
        raise ValidationError(
            {'categoria_dato': f'La categoria_dato debe ser {expected_value} para export_kind={export_kind}.'}
        )

    if not PoliticaRetencionDatos.objects.filter(
        categoria_dato=category_value,
        estado=EstadoRegistro.ACTIVE,
    ).exists():
        raise ValidationError({'categoria_dato': ACTIVE_RETENTION_POLICY_ERROR})


def prepare_sensitive_export(
    *,
    categoria_dato,
    export_kind,
    scope_resumen,
    motivo,
    payload,
    created_by,
    hold_activo=False,
    actor_user=None,
    ip_address=None,
):
    motivo = str(motivo or '').strip()
    if not motivo:
        raise ValueError(EXPORT_MOTIVE_REQUIRED_ERROR)
    if not getattr(created_by, 'pk', None):
        raise ValueError(EXPORT_CREATED_BY_REQUIRED_ERROR)
    actor_user = actor_user or created_by
    ensure_export_metadata_is_non_sensitive(scope_resumen=scope_resumen, motivo=motivo)
    validate_sensitive_export_controls(categoria_dato=categoria_dato, export_kind=export_kind)
    encrypted_payload, payload_hash = encrypt_payload(payload)
    expires_at = timezone.now() + timedelta(days=MAX_EXPORT_DAYS)
    with transaction.atomic():
        export = ExportacionSensible(
            categoria_dato=categoria_dato,
            export_kind=export_kind,
            scope_resumen=scope_resumen,
            motivo=motivo,
            encrypted_payload=encrypted_payload,
            payload_hash=payload_hash,
            encrypted_ref=build_encrypted_export_ref(export_kind, payload_hash),
            expires_at=expires_at,
            hold_activo=hold_activo,
            created_by=created_by,
        )
        export.full_clean()
        export.save()
        create_export_audit_event(
            event_type=EXPORT_PREPARED_EVENT_TYPE,
            export=export,
            summary='Exportacion sensible preparada y cifrada',
            actor_user=actor_user,
            ip_address=ip_address,
        )
        return export


def get_export_payload(export):
    if export.estado == EstadoExportacionSensible.REVOKED:
        raise ValueError('La exportacion fue revocada.')
    if export.estado == EstadoExportacionSensible.EXPIRED:
        raise ValueError('La exportacion expiro y ya no puede descargarse.')
    if not export.hold_activo and export.expires_at <= timezone.now():
        export.estado = EstadoExportacionSensible.EXPIRED
        export.save(update_fields=['estado', 'updated_at'])
        raise ValueError('La exportacion expiro y ya no puede descargarse.')
    try:
        payload = decrypt_payload(export.encrypted_payload)
    except (InvalidToken, TypeError, ValueError, UnicodeError) as error:
        raise ValueError(PAYLOAD_UNREADABLE_ERROR) from error
    if not payload_hash_matches(payload, export.payload_hash):
        raise ValueError(PAYLOAD_HASH_MISMATCH_ERROR)
    return payload


def revoke_export(export, *, actor_user=None, ip_address=None, revocation_reason=''):
    if export.estado == EstadoExportacionSensible.REVOKED:
        raise ValueError(EXPORT_ALREADY_REVOKED_ERROR)
    if export.estado == EstadoExportacionSensible.EXPIRED:
        raise ValueError(EXPIRED_EXPORT_REVOKE_ERROR)
    if not export.hold_activo and export.expires_at <= timezone.now():
        export.estado = EstadoExportacionSensible.EXPIRED
        export.save(update_fields=['estado', 'updated_at'])
        raise ValueError(EXPIRED_EXPORT_REVOKE_ERROR)
    revocation_reason = revocation_reason.strip()
    if not revocation_reason:
        raise ValueError(REVOCATION_REASON_REQUIRED_ERROR)
    if contains_sensitive_reference(revocation_reason, include_sensitive_keys=True):
        raise ValueError(REVOCATION_REASON_SENSITIVE_ERROR)
    with transaction.atomic():
        export.estado = EstadoExportacionSensible.REVOKED
        export.save(update_fields=['estado', 'updated_at'])
        create_export_audit_event(
            event_type=EXPORT_REVOKED_EVENT_TYPE,
            export=export,
            summary='Exportacion sensible revocada',
            actor_user=actor_user,
            ip_address=ip_address,
            extra_metadata={'revocation_reason': revocation_reason},
        )
        return export

