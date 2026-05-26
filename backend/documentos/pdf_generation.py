import hashlib
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from audit.services import create_audit_event

from .models import DocumentoEmitido, EstadoDocumento, OrigenDocumento


GENERATED_PDF_AUDIT_EVENT_TYPE = 'documentos.documento_emitido.generated_pdf'


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
    pdf_bytes = render_canonical_pdf_bytes(
        title=titulo,
        version_plantilla=version_plantilla,
        lineas=lineas,
    )
    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    document = DocumentoEmitido(
        expediente=expediente,
        tipo_documental=tipo_documental,
        version_plantilla=version_plantilla,
        checksum=checksum,
        fecha_carga=timezone.now(),
        usuario=actor_user if getattr(actor_user, 'is_authenticated', False) else None,
        origen=OrigenDocumento.GENERATED,
        estado=EstadoDocumento.ISSUED,
        storage_ref=build_generated_storage_ref(
            tipo_documental=tipo_documental,
            version_plantilla=version_plantilla,
            checksum=checksum,
        ),
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
        metadata={
            'checksum_sha256': checksum,
            'storage_ref': document.storage_ref,
            'pdf_size_bytes': len(pdf_bytes),
            'version_plantilla': version_plantilla,
            'tipo_documental': tipo_documental,
        },
    )
    return document, pdf_bytes
