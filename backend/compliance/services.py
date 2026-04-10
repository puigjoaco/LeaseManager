import hashlib
import json
from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.utils import timezone

from reporting.services import (
    build_annual_tax_summary,
    build_financial_monthly_summary,
    build_operational_dashboard,
    build_partner_summary,
    build_period_books_summary,
)

from .models import CategoriaDato, EstadoExportacionSensible, ExportacionSensible


MAX_EXPORT_DAYS = 30


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


def prepare_sensitive_export(*, categoria_dato, export_kind, scope_resumen, motivo, payload, created_by, hold_activo=False):
    encrypted_payload, payload_hash = encrypt_payload(payload)
    expires_at = timezone.now() + timedelta(days=MAX_EXPORT_DAYS)
    export = ExportacionSensible.objects.create(
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
    return export


def get_export_payload(export):
    if export.estado == EstadoExportacionSensible.REVOKED:
        raise ValueError('La exportacion fue revocada.')
    if not export.hold_activo and export.expires_at <= timezone.now():
        export.estado = EstadoExportacionSensible.EXPIRED
        export.save(update_fields=['estado', 'updated_at'])
        raise ValueError('La exportacion expiro y ya no puede descargarse.')
    return decrypt_payload(export.encrypted_payload)


def revoke_export(export):
    export.estado = EstadoExportacionSensible.REVOKED
    export.save(update_fields=['estado', 'updated_at'])
    return export

