import hashlib
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.models import AuditEvent
from audit.services import create_audit_event

from .models import DocumentoEmitido, EstadoDocumento, OrigenDocumento


GENERATED_PDF_AUDIT_EVENT_TYPE = 'documentos.documento_emitido.generated_pdf'
PREVIEW_PDF_AUDIT_EVENT_TYPE = 'documentos.documento_emitido.previewed_pdf'
PDF_PREVIEW_ENTITY_TYPE = 'documento_pdf_preview'


def _escape_pdf_text(value):
    return (
        str(value or '')
        .replace('\\', '\\\\')
        .replace('(', '\\(')
        .replace(')', '\\)')
        .encode('latin-1', errors='replace')
        .decode('latin-1')
    )


def _pdf_object(number, body):
    return f'{number} 0 obj\n'.encode('latin-1') + body + b'\nendobj\n'


def render_canonical_pdf_bytes(*, title, version_plantilla, lineas):
    safe_title = _escape_pdf_text(title)
    safe_lines = [_escape_pdf_text(item) for item in lineas]
    safe_template = _escape_pdf_text(f'Plantilla {version_plantilla}')
    stream_rows = [
        'BT',
        '/F1 16 Tf',
        '72 780 Td',
        f'({safe_title}) Tj',
        '/F1 10 Tf',
        '0 -24 Td',
        f'({safe_template}) Tj',
    ]
    for line in safe_lines[:36]:
        stream_rows.append('0 -16 Td')
        stream_rows.append(f'({line}) Tj')
    stream_rows.append('ET')
    stream = '\n'.join(stream_rows).encode('latin-1')

    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        (
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            b'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>'
        ),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream',
    ]

    chunks = [b'%PDF-1.4\n']
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(_pdf_object(index, body))
    xref_offset = sum(len(chunk) for chunk in chunks)
    xref = [f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode('ascii')]
    xref.extend(f'{offset:010d} 00000 n \n'.encode('ascii') for offset in offsets[1:])
    trailer = (
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref_offset}\n%%EOF\n'
    ).encode('ascii')
    return b''.join(chunks + xref + [trailer])


def build_generated_storage_ref(*, tipo_documental, version_plantilla, checksum):
    safe_version = re.sub(r'[^a-zA-Z0-9_-]+', '-', str(version_plantilla or '').strip()).strip('-') or 'v1'
    return f'storage/generated-documents/{tipo_documental}/{safe_version}-{checksum[:16]}.pdf'


def build_generated_pdf_payload(*, tipo_documental, version_plantilla, titulo, lineas):
    pdf_bytes = render_canonical_pdf_bytes(
        title=titulo,
        version_plantilla=version_plantilla,
        lineas=lineas,
    )
    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    storage_ref = build_generated_storage_ref(
        tipo_documental=tipo_documental,
        version_plantilla=version_plantilla,
        checksum=checksum,
    )
    return {
        'pdf_bytes': pdf_bytes,
        'checksum': checksum,
        'storage_ref': storage_ref,
    }


def _event_has_actor(event):
    return bool(event.actor_user_id or str(event.actor_identifier or '').strip())


def build_pdf_preview_audit_metadata(*, payload, expediente, tipo_documental, version_plantilla, lineas):
    return {
        'checksum_sha256': payload['checksum'],
        'storage_ref': payload['storage_ref'],
        'pdf_size_bytes': len(payload['pdf_bytes']),
        'version_plantilla': version_plantilla,
        'tipo_documental': tipo_documental,
        'expediente_id': str(expediente.pk),
        'line_count': len(lineas),
    }


def build_generated_pdf_audit_metadata(document, *, pdf_size_bytes=None):
    metadata = {
        'checksum_sha256': str(document.checksum or '').strip(),
        'storage_ref': str(document.storage_ref or '').strip(),
        'version_plantilla': str(document.version_plantilla or '').strip(),
        'tipo_documental': document.tipo_documental,
        'expediente_id': str(document.expediente_id),
    }
    if pdf_size_bytes is not None:
        metadata['pdf_size_bytes'] = int(pdf_size_bytes)
    return metadata


def _preview_metadata_matches(metadata, *, expediente, tipo_documental, version_plantilla, checksum, storage_ref):
    return (
        str(metadata.get('checksum_sha256') or '').strip() == str(checksum or '').strip()
        and str(metadata.get('expediente_id')) == str(expediente.pk)
        and metadata.get('tipo_documental') == tipo_documental
        and metadata.get('version_plantilla') == version_plantilla
        and metadata.get('storage_ref') == storage_ref
    )


def has_matching_pdf_preview(*, expediente, tipo_documental, version_plantilla, checksum, storage_ref):
    for event in AuditEvent.objects.filter(
        event_type=PREVIEW_PDF_AUDIT_EVENT_TYPE,
        entity_type=PDF_PREVIEW_ENTITY_TYPE,
        entity_id=checksum,
    ):
        if not _event_has_actor(event):
            continue
        if _preview_metadata_matches(
            event.metadata or {},
            expediente=expediente,
            tipo_documental=tipo_documental,
            version_plantilla=version_plantilla,
            checksum=checksum,
            storage_ref=storage_ref,
        ):
            return True
    return False


def preview_generated_pdf_document(
    *,
    expediente,
    tipo_documental,
    version_plantilla,
    titulo,
    lineas,
    actor_user,
    ip_address=None,
):
    payload = build_generated_pdf_payload(
        tipo_documental=tipo_documental,
        version_plantilla=version_plantilla,
        titulo=titulo,
        lineas=lineas,
    )
    create_audit_event(
        event_type=PREVIEW_PDF_AUDIT_EVENT_TYPE,
        entity_type=PDF_PREVIEW_ENTITY_TYPE,
        entity_id=payload['checksum'],
        summary='Vista previa PDF generada sin persistir documento.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata=build_pdf_preview_audit_metadata(
            payload=payload,
            expediente=expediente,
            tipo_documental=tipo_documental,
            version_plantilla=version_plantilla,
            lineas=lineas,
        ),
    )
    return payload


@transaction.atomic
def emit_generated_pdf_document(
    *,
    expediente,
    tipo_documental,
    version_plantilla,
    titulo,
    lineas,
    actor_user,
    ip_address=None,
):
    payload = build_generated_pdf_payload(
        tipo_documental=tipo_documental,
        version_plantilla=version_plantilla,
        titulo=titulo,
        lineas=lineas,
    )
    checksum = payload['checksum']
    storage_ref = payload['storage_ref']
    pdf_bytes = payload['pdf_bytes']
    if not has_matching_pdf_preview(
        expediente=expediente,
        tipo_documental=tipo_documental,
        version_plantilla=version_plantilla,
        checksum=checksum,
        storage_ref=storage_ref,
    ):
        raise ValidationError(
            {'preview': 'La emision PDF generada requiere vista previa auditada del mismo contenido.'}
        )
    document = DocumentoEmitido(
        expediente=expediente,
        tipo_documental=tipo_documental,
        version_plantilla=version_plantilla,
        checksum=checksum,
        fecha_carga=timezone.now(),
        usuario=actor_user if getattr(actor_user, 'is_authenticated', False) else None,
        origen=OrigenDocumento.GENERATED,
        estado=EstadoDocumento.ISSUED,
        storage_ref=storage_ref,
    )
    try:
        document.full_clean()
    except ValidationError:
        raise
    document.save()
    create_audit_event(
        event_type=GENERATED_PDF_AUDIT_EVENT_TYPE,
        entity_type='documento_emitido',
        entity_id=str(document.pk),
        summary='Documento PDF generado por sistema con checksum derivado del contenido.',
        actor_user=actor_user,
        ip_address=ip_address,
        metadata=build_generated_pdf_audit_metadata(document, pdf_size_bytes=len(pdf_bytes)),
    )
    return document, pdf_bytes
