from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.services import create_audit_event
from core.management.local_evidence_paths import (
    local_evidence_root,
    resolve_command_path,
    validate_local_evidence_output_path,
)
from core.reference_validation import is_non_sensitive_control_reference, normalize_reference

from documentos.models import (
    ArchivoExpediente,
    DocumentoEmitido,
    EstadoClasificacionArchivoExpediente,
    EstadoExpediente,
    ExpedienteDocumental,
)


DEFAULT_AUDIT_REL = Path('revisar-document-audit') / '2026-06-21'
DEFAULT_DRY_RUN_REL = DEFAULT_AUDIT_REL / 'expediente-integral-dry-run-pass5390'
DEFAULT_MATRIX_NAME = 'expediente_integral_dry_run_private_pass5390.csv'
DEFAULT_VALIDATION_NAME = 'expediente_integral_dry_run_private_validation_pass5390.json'
DEFAULT_OUTPUT_NAME = 'expediente_integral_materialization_result_pass5391.json'
RUN_REF = 'expediente-integral-materialization-pass5391'
MATERIALIZABLE_DECISIONS = {'archivo_expediente_nuevo', 'duplicado_exactamente'}
LEGACY_REVISAR_EMPRESAS_SOURCE_PREFIX_RE = re.compile(r'revisar-empresas-([0-9a-f]{16})-', re.IGNORECASE)
INGESTED_STORAGE_PREFIX = 'expediente_integral/sha256'


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise CommandError(f'No existe matriz requerida: {path}')
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def load_validation(path: Path) -> dict:
    if not path.exists():
        raise CommandError(f'No existe validacion requerida: {path}')
    return json.loads(path.read_text(encoding='utf-8'))


def safe_value(value: str, fallback: str, max_length: int) -> str:
    normalized = normalize_reference(value)
    if normalized and len(normalized) <= max_length and is_non_sensitive_control_reference(normalized):
        return normalized
    fallback_normalized = normalize_reference(fallback)
    if not fallback_normalized:
        fallback_normalized = 'referencia-controlada'
    return fallback_normalized[:max_length]


def title_from_row(row: dict) -> str:
    private_path = str(row.get('source_relative_path_private') or '').replace('\\', '/')
    raw_name = Path(private_path).name if private_path else ''
    source_ref = row.get('source_file_ref') or row.get('integral_audit_ref') or 'archivo'
    fallback = f"Archivo {source_ref}"
    return safe_value(raw_name, fallback, 255)


def description_from_row(row: dict) -> str:
    category = safe_value(row.get('archivo_categoria', ''), 'archivo', 32)
    section = safe_value(row.get('final_section', ''), '99_revision_manual', 64)
    subcategory = safe_value(row.get('final_subcategory', ''), '00_ficha_general', 64)
    decision = safe_value(row.get('decision', ''), 'archivo_expediente_nuevo', 64)
    return (
        f'Archivo {category} materializado desde auditoria integral; '
        f'seccion {section}; subcategoria {subcategory}; decision {decision}.'
    )


def owner_from_row(row: dict) -> str:
    return safe_value(row.get('final_titular', ''), 'Requiere clasificacion titular', 128)


def origin_from_row(row: dict) -> str:
    origin = row.get('origen_auditoria') or row.get('source_top_folder') or row.get('source_kind')
    return safe_value(origin, 'auditoria-integral-controlada', 128)


def estado_from_row(row: dict, *, duplicate: bool) -> str:
    if duplicate:
        return EstadoClasificacionArchivoExpediente.EXACT_DUPLICATE
    raw_state = str(row.get('estado_clasificacion') or '').strip()
    allowed = set(EstadoClasificacionArchivoExpediente.values)
    if raw_state in allowed:
        return raw_state
    return EstadoClasificacionArchivoExpediente.CONFIRMED


def materializable_source_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if row.get('decision') in MATERIALIZABLE_DECISIONS
        and row.get('extension') != '.pdf'
    ]


def ingested_storage_ref(row: dict) -> str:
    checksum = normalize_reference(row.get('checksum_sha256', '')).lower()
    extension = safe_value(row.get('extension', ''), '.bin', 16)
    if extension and not extension.startswith('.'):
        extension = f'.{extension}'
    return f'{INGESTED_STORAGE_PREFIX}/{checksum[:2]}/{checksum[2:4]}/{checksum}{extension}'


class Command(BaseCommand):
    help = 'Materializa en DB el dry-run integral validado de expedientes documentales.'

    def add_arguments(self, parser):
        default_base = local_evidence_root() / DEFAULT_DRY_RUN_REL
        parser.add_argument('--matrix', default=str(default_base / DEFAULT_MATRIX_NAME))
        parser.add_argument('--validation', default=str(default_base / DEFAULT_VALIDATION_NAME))
        parser.add_argument('--output', default=str(default_base / DEFAULT_OUTPUT_NAME))
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Escribe DB. Sin esta bandera solo valida y calcula conteos.',
        )
        parser.add_argument('--actor-identifier', default=RUN_REF)

    def handle(self, *args, **options):
        matrix_path = resolve_command_path(options['matrix'])
        validation_path = resolve_command_path(options['validation'])
        output_path = resolve_command_path(options['output'])
        validate_local_evidence_output_path(
            output_path,
            option_name='--output',
            artifact_description='resultado de materializacion documental integral',
        )

        validation = load_validation(validation_path)
        if not validation.get('validation_passed'):
            raise CommandError('La matriz no tiene validation_passed=true; no se materializa.')
        if validation.get('source_rows_total') != validation.get('expected_total'):
            raise CommandError('La validacion no confirma conteo fuente completo.')

        rows = read_csv(matrix_path)
        by_source_ref = {row.get('source_file_ref'): row for row in rows if row.get('source_file_ref')}
        by_checksum_prefix, ambiguous_checksum_prefixes = self._rows_by_checksum_prefix(rows)
        materializable_rows = materializable_source_rows(rows)
        primary_rows = [row for row in materializable_rows if row.get('decision') == 'archivo_expediente_nuevo']
        duplicate_rows = [row for row in materializable_rows if row.get('decision') == 'duplicado_exactamente']
        manual_review_rows = [row for row in rows if row.get('decision') == 'requiere_revision_manual']
        existing_document_rows = [
            row
            for row in rows
            if row.get('decision') == 'documento_emitido_existente'
            and row.get('documento_emitido_ref')
        ]

        result = {
            'scope': RUN_REF,
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'apply_requested': bool(options['apply']),
            'db_write_performed': False,
            'matrix_file': matrix_path.name,
            'validation_file': validation_path.name,
            'source_rows_total': len(rows),
            'materializable_rows_total': len(materializable_rows),
            'primary_archivo_rows': len(primary_rows),
            'duplicate_archivo_rows': len(duplicate_rows),
            'documento_emitido_existing_rows': sum(
                1 for row in rows if row.get('decision') == 'documento_emitido_existente'
            ),
            'documento_emitido_existing_rows_with_ref': len(existing_document_rows),
            'documentos_emitidos_rehomed': 0,
            'documentos_emitidos_already_in_destination': 0,
            'documentos_emitidos_missing': 0,
            'documentos_emitidos_ambiguous': 0,
            'legacy_documentos_rehomed_by_source_checksum': 0,
            'legacy_documentos_already_in_destination': 0,
            'legacy_documentos_missing_source_checksum': 0,
            'legacy_documentos_ambiguous_source_checksum': 0,
            'manual_review_rows': sum(1 for row in rows if row.get('decision') == 'requiere_revision_manual'),
            'created_manual_review_archivos': 0,
            'existing_manual_review_archivos': 0,
            'skipped_pdf_duplicates': sum(
                1
                for row in rows
                if row.get('decision') == 'duplicado_exactamente'
                and row.get('extension') == '.pdf'
            ),
            'created_expedientes': 0,
            'existing_expedientes': 0,
            'created_archivos_expediente': 0,
            'existing_archivos_expediente': 0,
            'created_duplicate_aliases': 0,
            'skipped_duplicate_aliases_without_canonical': 0,
            'skipped_duplicate_aliases_existing': 0,
            'by_categoria_materialized': {},
            'by_estado_materialized': {},
            'created_archivo_ids': [],
            'audit_event_id': None,
        }

        if not options['apply']:
            result['dry_run_only'] = True
            self._write_result(output_path, result)
            self.stdout.write(json.dumps(result, ensure_ascii=False))
            return

        source_to_archivo: dict[str, ArchivoExpediente] = {}
        by_categoria = Counter()
        by_estado = Counter()

        try:
            with transaction.atomic():
                for row in existing_document_rows:
                    documento, lookup_status = self._find_existing_documento_for_row(row)
                    if documento is None:
                        result[
                            'documentos_emitidos_ambiguous'
                            if lookup_status == 'ambiguous'
                            else 'documentos_emitidos_missing'
                        ] += 1
                        continue
                    expediente, expediente_created = self._get_or_create_expediente(row)
                    result['created_expedientes' if expediente_created else 'existing_expedientes'] += 1
                    if documento.expediente_id == expediente.id:
                        result['documentos_emitidos_already_in_destination'] += 1
                        continue
                    documento.expediente = expediente
                    documento.save(update_fields=['expediente', 'updated_at'])
                    result['documentos_emitidos_rehomed'] += 1

                for documento in self._legacy_herencia_documentos():
                    source_prefix = self._legacy_source_checksum_prefix(documento)
                    if not source_prefix:
                        result['legacy_documentos_missing_source_checksum'] += 1
                        continue
                    if source_prefix in ambiguous_checksum_prefixes:
                        result['legacy_documentos_ambiguous_source_checksum'] += 1
                        continue
                    row = by_checksum_prefix.get(source_prefix)
                    if not row:
                        result['legacy_documentos_missing_source_checksum'] += 1
                        continue
                    expediente, expediente_created = self._get_or_create_expediente(row)
                    result['created_expedientes' if expediente_created else 'existing_expedientes'] += 1
                    if documento.expediente_id == expediente.id:
                        result['legacy_documentos_already_in_destination'] += 1
                        continue
                    documento.expediente = expediente
                    documento.save(update_fields=['expediente', 'updated_at'])
                    result['legacy_documentos_rehomed_by_source_checksum'] += 1

                for row in manual_review_rows:
                    expediente, expediente_created = self._get_or_create_expediente(row)
                    result['created_expedientes' if expediente_created else 'existing_expedientes'] += 1
                    archivo, archivo_created = self._get_or_create_archivo(
                        row,
                        expediente,
                        duplicate_of=None,
                        storage_ref=ingested_storage_ref(row),
                        estado=EstadoClasificacionArchivoExpediente.NEEDS_MANUAL_REVIEW,
                    )
                    result['created_manual_review_archivos' if archivo_created else 'existing_manual_review_archivos'] += 1
                    if archivo_created:
                        result['created_archivos_expediente'] += 1
                        result['created_archivo_ids'].append(archivo.id)
                    else:
                        result['existing_archivos_expediente'] += 1
                    by_categoria[archivo.categoria] += 1
                    by_estado[archivo.estado_clasificacion] += 1

                for row in primary_rows:
                    expediente, expediente_created = self._get_or_create_expediente(row)
                    result['created_expedientes' if expediente_created else 'existing_expedientes'] += 1
                    archivo, archivo_created = self._get_or_create_archivo(row, expediente, duplicate_of=None)
                    result['created_archivos_expediente' if archivo_created else 'existing_archivos_expediente'] += 1
                    source_to_archivo[row['source_file_ref']] = archivo
                    by_categoria[archivo.categoria] += 1
                    by_estado[archivo.estado_clasificacion] += 1
                    if archivo_created:
                        result['created_archivo_ids'].append(archivo.id)

                for row in duplicate_rows:
                    canonical_ref = row.get('duplicate_of_source_ref') or row.get('canonical_source_file_ref')
                    canonical = source_to_archivo.get(canonical_ref)
                    if canonical is None:
                        canonical_row = by_source_ref.get(canonical_ref)
                        canonical = self._find_existing_archivo_for_row(canonical_row) if canonical_row else None
                    if canonical is None:
                        result['skipped_duplicate_aliases_without_canonical'] += 1
                        continue
                    expediente, expediente_created = self._get_or_create_expediente(row)
                    result['created_expedientes' if expediente_created else 'existing_expedientes'] += 1
                    archivo, archivo_created = self._get_or_create_archivo(row, expediente, duplicate_of=canonical)
                    if archivo_created:
                        result['created_duplicate_aliases'] += 1
                        result['created_archivos_expediente'] += 1
                        result['created_archivo_ids'].append(archivo.id)
                    else:
                        result['skipped_duplicate_aliases_existing'] += 1
                        result['existing_archivos_expediente'] += 1
                    source_to_archivo[row['source_file_ref']] = archivo
                    by_categoria[archivo.categoria] += 1
                    by_estado[archivo.estado_clasificacion] += 1

                result['by_categoria_materialized'] = dict(sorted(by_categoria.items()))
                result['by_estado_materialized'] = dict(sorted(by_estado.items()))
                result['db_write_performed'] = True
                event = create_audit_event(
                    event_type='documentos.expediente_integral.materialized',
                    entity_type='expediente_integral_materialization',
                    entity_id=RUN_REF,
                    summary='Materializacion controlada de expediente integral documental',
                    actor_identifier=options['actor_identifier'],
                    metadata={
                        'source_rows_total': result['source_rows_total'],
                        'materializable_rows_total': result['materializable_rows_total'],
                        'created_expedientes': result['created_expedientes'],
                        'existing_expedientes': result['existing_expedientes'],
                        'created_archivos_expediente': result['created_archivos_expediente'],
                        'existing_archivos_expediente': result['existing_archivos_expediente'],
                        'created_duplicate_aliases': result['created_duplicate_aliases'],
                        'documentos_emitidos_rehomed': result['documentos_emitidos_rehomed'],
                        'documentos_emitidos_missing': result['documentos_emitidos_missing'],
                        'documentos_emitidos_ambiguous': result['documentos_emitidos_ambiguous'],
                        'legacy_documentos_rehomed_by_source_checksum': result[
                            'legacy_documentos_rehomed_by_source_checksum'
                        ],
                        'legacy_documentos_missing_source_checksum': result[
                            'legacy_documentos_missing_source_checksum'
                        ],
                        'legacy_documentos_ambiguous_source_checksum': result[
                            'legacy_documentos_ambiguous_source_checksum'
                        ],
                        'created_manual_review_archivos': result['created_manual_review_archivos'],
                        'existing_manual_review_archivos': result['existing_manual_review_archivos'],
                        'skipped_duplicate_aliases_without_canonical': result[
                            'skipped_duplicate_aliases_without_canonical'
                        ],
                        'matrix_file': matrix_path.name,
                        'validation_file': validation_path.name,
                    },
                )
                result['audit_event_id'] = event.id
        except ValidationError as error:
            raise CommandError(f'La materializacion no paso validacion de dominio: {error}') from error

        self._write_result(output_path, result)
        self.stdout.write(json.dumps(result, ensure_ascii=False))

    def _rows_by_checksum_prefix(self, rows: list[dict]) -> tuple[dict[str, dict], set[str]]:
        buckets: dict[str, list[dict]] = {}
        by_prefix: dict[str, dict] = {}
        ambiguous = set()
        for row in rows:
            checksum = normalize_reference(row.get('checksum_sha256', '')).lower()
            if len(checksum) < 16:
                continue
            prefix = checksum[:16]
            buckets.setdefault(prefix, []).append(row)

        for prefix, prefix_rows in buckets.items():
            primary_rows = [
                row
                for row in prefix_rows
                if row.get('decision') != 'duplicado_exactamente'
                and not row.get('duplicate_of_source_ref')
            ]
            candidates = primary_rows or prefix_rows
            destination_refs = {row.get('expediente_destino_ref') for row in candidates}
            if len(destination_refs) == 1:
                by_prefix[prefix] = candidates[0]
                continue
            ambiguous.add(prefix)

        return by_prefix, ambiguous

    def _get_or_create_expediente(self, row: dict) -> tuple[ExpedienteDocumental, bool]:
        expediente_ref = safe_value(row.get('expediente_destino_ref', ''), 'expediente-integral-sin-ref', 64)
        owner = owner_from_row(row)
        expediente, created = ExpedienteDocumental.objects.get_or_create(
            entidad_tipo='expediente_integral',
            entidad_id=expediente_ref,
            defaults={
                'estado': EstadoExpediente.OPEN,
                'owner_operativo': owner,
            },
        )
        current_owner = str(expediente.owner_operativo or '').lower()
        if (
            not created
            and expediente.owner_operativo != owner
            and (
                expediente.owner_operativo == 'Requiere clasificacion titular'
                or 'herencia_papa' in current_owner
            )
        ):
            expediente.owner_operativo = owner
            expediente.full_clean()
            expediente.save(update_fields=['owner_operativo', 'updated_at'])
        if created:
            expediente.full_clean()
            expediente.save()
        return expediente, created

    def _find_existing_documento_for_row(self, row: dict) -> tuple[DocumentoEmitido | None, str]:
        ref = normalize_reference(row.get('documento_emitido_ref', ''))
        if ref:
            matches = list(DocumentoEmitido.objects.filter(storage_ref__icontains=ref).order_by('id')[:2])
            if len(matches) == 1:
                return matches[0], 'found'
            if len(matches) > 1:
                return None, 'ambiguous'

        checksum = normalize_reference(row.get('checksum_sha256', '')).lower()
        if checksum:
            matches = list(DocumentoEmitido.objects.filter(checksum=checksum).order_by('id')[:2])
            if len(matches) == 1:
                return matches[0], 'found'
            if len(matches) > 1:
                return None, 'ambiguous'

        return None, 'missing'

    def _legacy_herencia_documentos(self):
        return DocumentoEmitido.objects.select_related('expediente').filter(
            expediente__owner_operativo__icontains='herencia_papa',
        ).order_by('id')

    def _legacy_source_checksum_prefix(self, documento: DocumentoEmitido) -> str:
        match = LEGACY_REVISAR_EMPRESAS_SOURCE_PREFIX_RE.search(str(documento.storage_ref or ''))
        return match.group(1).lower() if match else ''

    def _find_existing_archivo_for_row(self, row: dict | None) -> ArchivoExpediente | None:
        if not row:
            return None
        checksum = normalize_reference(row.get('checksum_sha256', '')).lower()
        storage_ref = normalize_reference(row.get('storage_ref_propuesto', ''))
        if not checksum or not storage_ref:
            return None
        existing = ArchivoExpediente.objects.filter(
            checksum_sha256=checksum,
            storage_ref=storage_ref,
        ).order_by('id').first()
        if existing:
            return existing
        return ArchivoExpediente.objects.filter(checksum_sha256=checksum).order_by('id').first()

    def _get_or_create_archivo(
        self,
        row: dict,
        expediente: ExpedienteDocumental,
        *,
        duplicate_of: ArchivoExpediente | None,
        storage_ref: str | None = None,
        estado: str | None = None,
    ) -> tuple[ArchivoExpediente, bool]:
        checksum = normalize_reference(row.get('checksum_sha256', '')).lower()
        storage_ref = normalize_reference(storage_ref or row.get('storage_ref_propuesto', ''))
        existing = ArchivoExpediente.objects.filter(
            expediente=expediente,
            checksum_sha256=checksum,
            storage_ref=storage_ref,
        ).order_by('id').first()
        if existing:
            return existing, False
        existing = ArchivoExpediente.objects.filter(
            expediente=expediente,
            checksum_sha256=checksum,
        ).order_by('id').first()
        if existing:
            return existing, False

        is_duplicate = duplicate_of is not None
        archivo = ArchivoExpediente(
            expediente=expediente,
            categoria=safe_value(row.get('archivo_categoria', ''), 'otro', 32),
            subcategoria=safe_value(row.get('final_subcategory', ''), '00_ficha_general', 64),
            titulo_operativo=title_from_row(row),
            descripcion_objetiva=description_from_row(row),
            extension=safe_value(row.get('extension', ''), '.bin', 16),
            mime_type=safe_value(row.get('mime_type', ''), 'application/octet-stream', 128),
            checksum_sha256=checksum,
            size_bytes=int(str(row.get('size_bytes') or '0').strip() or 0),
            storage_ref=storage_ref,
            origen_auditoria=origin_from_row(row),
            estado_clasificacion=estado or estado_from_row(row, duplicate=is_duplicate),
            duplicate_of=duplicate_of,
        )
        archivo.full_clean()
        archivo.save()
        return archivo, True

    def _write_result(self, output_path: Path, result: dict) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
