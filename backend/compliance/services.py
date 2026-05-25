import hashlib
import json
from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

from core.reference_validation import contains_sensitive_reference
from reporting.services import (
    build_annual_tax_summary,
    build_financial_monthly_summary,
    build_operational_dashboard,
    build_partner_summary,
    build_period_books_summary,
)

from .models import (
    CategoriaDato,
    EstadoExportacionSensible,
    EstadoRegistro,
    ExportacionSensible,
    PoliticaRetencionDatos,
    SECRET_EXPORT_ERROR,
)


MAX_EXPORT_DAYS = 30
SENSITIVE_EXPORT_METADATA_ERROR = 'La metadata visible de exportacion no puede contener referencias sensibles.'
ACTIVE_RETENTION_POLICY_ERROR = 'No existe una politica de retencion activa para la categoria indicada.'
EXPORT_KIND_CATEGORY_MAP = {
    'dashboard_operativo': CategoriaDato.OPERATIONAL,
    'financiero_mensual': CategoriaDato.FINANCIAL,
    'tributario_anual': CategoriaDato.TAX,
    'socio_resumen': CategoriaDato.DOCUMENT,
    'libros_periodo': CategoriaDato.FINANCIAL,
}


def _choice_value(value):
    return getattr(value, 'value', value)


def get_fernet():
    return Fernet(settings.DATA_EXPORT_ENCRYPTION_KEY.encode('ascii'))


def render_export_payload(export_kind, params):
    if export_kind == 'dashboard_operativo':
        return build_operational_dashboard()
    if export_kind == 'financiero_mensual':
        return build_financial_monthly_summary(params['anio'], params['mes'], params.get('empresa_id'))
    if export_kind == 'tributario_anual':
        return build_annual_tax_summary(params['anio_tributario'], params.get('empresa_id'))
    if export_kind == 'socio_resumen':
        return build_partner_summary(params['socio_id'])
    if export_kind == 'libros_periodo':
        return build_period_books_summary(params['empresa_id'], params['periodo'])
    raise ValueError('Tipo de exportacion no soportado.')


def encrypt_payload(payload):
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode('utf-8')
    token = get_fernet().encrypt(raw).decode('ascii')
    payload_hash = hashlib.sha256(raw).hexdigest()
    return token, payload_hash


def decrypt_payload(token):
    raw = get_fernet().decrypt(token.encode('ascii'))
    return json.loads(raw.decode('utf-8'))


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


def prepare_sensitive_export(*, categoria_dato, export_kind, scope_resumen, motivo, payload, created_by, hold_activo=False):
    ensure_export_metadata_is_non_sensitive(scope_resumen=scope_resumen, motivo=motivo)
    validate_sensitive_export_controls(categoria_dato=categoria_dato, export_kind=export_kind)
    encrypted_payload, payload_hash = encrypt_payload(payload)
    expires_at = timezone.now() + timedelta(days=MAX_EXPORT_DAYS)
    export = ExportacionSensible(
        categoria_dato=categoria_dato,
        export_kind=export_kind,
        scope_resumen=scope_resumen,
        motivo=motivo,
        encrypted_payload=encrypted_payload,
        payload_hash=payload_hash,
        encrypted_ref=f'export://{export_kind}/{payload_hash[:12]}',
        expires_at=expires_at,
        hold_activo=hold_activo,
        created_by=created_by,
    )
    export.full_clean()
    export.save()
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
    return decrypt_payload(export.encrypted_payload)


def revoke_export(export):
    export.estado = EstadoExportacionSensible.REVOKED
    export.save(update_fields=['estado', 'updated_at'])
    return export

