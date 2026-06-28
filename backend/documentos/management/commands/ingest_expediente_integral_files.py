from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.services import create_audit_event
from core.management.local_evidence_paths import (
    local_evidence_root,
    resolve_command_path,
    validate_local_evidence_output_path,
)
from core.reference_validation import normalize_reference
from documentos.models import ArchivoExpediente, DocumentoEmitido


DEFAULT_AUDIT_REL = Path('revisar-document-audit') / '2026-06-21'
DEFAULT_DRY_RUN_REL = DEFAULT_AUDIT_REL / 'expediente-integral-dry-run-pass5390'
DEFAULT_MATRIX_NAME = 'expediente_integral_dry_run_private_pass5390.csv'
DEFAULT_OUTPUT_NAME = 'expediente_integral_file_ingest_private_pass5395.json'
DEFAULT_PUBLIC_OUTPUT_NAME = 'expediente_integral_file_ingest_public_pass5395.json'
RUN_REF = 'expediente-integral-file-ingest-pass5395'
STORAGE_PREFIX = Path('expediente_integral') / 'sha256'


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise CommandError(f'No existe matriz requerida: {path}')
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def normalize_checksum(value: str) -> str:
    checksum = normalize_reference(value).lower()
    if len(checksum) == 64 and all(char in '0123456789abcdef' for char in checksum):
        return checksum
    return ''


def normalize_extension(value: str, fallback: str = '.bin') -> str:
    extension = normalize_reference(value).lower()
    if not extension:
        extension = fallback
    if not extension.startswith('.'):
        extension = f'.{extension}'
    if len(extension) > 16 or any(char in extension for char in ('/', '\\', ':')):
        return fallback
    return extension


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


class Command(BaseCommand):
    help = 'Copia archivos auditados a MEDIA_ROOT y actualiza storage_ref verificado por SHA-256.'

    def add_arguments(self, parser):
        default_base = local_evidence_root() / DEFAULT_DRY_RUN_REL
        parser.add_argument('--matrix', default=str(default_base / DEFAULT_MATRIX_NAME))
        parser.add_argument('--output', default=str(default_base / DEFAULT_OUTPUT_NAME))
        parser.add_argument('--public-output', default=str(default_base / DEFAULT_PUBLIC_OUTPUT_NAME))
        parser.add_argument('--storage-root', default=str(settings.MEDIA_ROOT))
        parser.add_argument(
            '--source-root',
            action='append',
            default=[],
            help='Raiz adicional para resolver storage_ref relativos existentes.',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Copia archivos y actualiza DB. Sin esta bandera solo calcula plan.',
        )
        parser.add_argument('--actor-identifier', default=RUN_REF)

    def handle(self, *args, **options):
        matrix_path = resolve_command_path(options['matrix'])
        output_path = resolve_command_path(options['output'])
        public_output_path = resolve_command_path(options['public_output'])
        validate_local_evidence_output_path(
            output_path,
            option_name='--output',
            artifact_description='manifiesto privado de ingesta fisica documental',
        )
        validate_local_evidence_output_path(
            public_output_path,
            option_name='--public-output',
            artifact_description='manifiesto publico de ingesta fisica documental',
        )
        storage_root = Path(options['storage_root']).expanduser().resolve()
        source_roots = self._source_roots(options['source_root'])
        if storage_root not in source_roots:
            source_roots.append(storage_root)

        rows = read_csv(matrix_path)
        matrix_jobs, matrix_rows_missing = self._build_matrix_jobs(rows)
        document_jobs, document_rows_missing = self._build_document_jobs(source_roots)

        all_jobs = {}
        for job in [*matrix_jobs.values(), *document_jobs.values()]:
            all_jobs.setdefault(job['checksum'], job)

        result = {
            'scope': RUN_REF,
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'apply_requested': bool(options['apply']),
            'db_write_performed': False,
            'matrix_file': matrix_path.name,
            'storage_root': str(storage_root),
            'source_roots': [str(path) for path in source_roots],
            'matrix_rows_total': len(rows),
            'matrix_unique_checksums': len(matrix_jobs),
            'document_unique_checksums': len(document_jobs),
            'unique_file_jobs': len(all_jobs),
            'matrix_rows_missing_source': matrix_rows_missing,
            'documentos_missing_source': document_rows_missing,
            'copied_files': 0,
            'already_verified_files': 0,
            'copy_failures': [],
            'documentos_updated': 0,
            'documentos_already_internal': 0,
            'archivos_updated': 0,
            'archivos_already_internal': 0,
            'db_storage_refs_pointing_to_desktop': 0,
            'safe_to_delete_source': False,
            'private_manifest': [],
            'public_manifest': [],
            'audit_event_id': None,
        }

        if options['apply']:
            storage_root.mkdir(parents=True, exist_ok=True)

        for checksum, job in sorted(all_jobs.items()):
            destination_ref = self._destination_ref(checksum, job['extension'])
            destination_path = storage_root / destination_ref
            job_result = {
                'checksum_sha256': checksum,
                'extension': job['extension'],
                'storage_ref': destination_ref.as_posix(),
                'source_path_private': str(job['source_path']),
                'source_kind': job['source_kind'],
                'copied': False,
                'already_verified': False,
                'verified': False,
                'error': '',
            }
            if options['apply']:
                try:
                    copy_state = self._copy_verified(job['source_path'], destination_path, checksum)
                    job_result[copy_state] = True
                    job_result['verified'] = True
                    if copy_state == 'copied':
                        result['copied_files'] += 1
                    else:
                        result['already_verified_files'] += 1
                except CommandError as error:
                    job_result['error'] = str(error)
                    result['copy_failures'].append(
                        {
                            'checksum_sha256': checksum,
                            'storage_ref': destination_ref.as_posix(),
                            'error': str(error),
                        }
                    )
            result['private_manifest'].append(job_result)
            result['public_manifest'].append(
                {
                    'checksum_sha256': checksum,
                    'extension': job['extension'],
                    'storage_ref': destination_ref.as_posix(),
                    'source_kind': job['source_kind'],
                    'verified': job_result['verified'],
                    'error': job_result['error'],
                }
            )

        if options['apply'] and result['copy_failures']:
            self._write_outputs(output_path, public_output_path, result)
            raise CommandError('La ingesta fisica tuvo errores de copia/verificacion; DB no fue actualizada.')

        if options['apply']:
            copied_refs = {
                item['checksum_sha256']: item['storage_ref']
                for item in result['private_manifest']
                if item['verified']
            }
            with transaction.atomic():
                doc_updated, doc_already = self._update_documentos(copied_refs)
                archivo_updated, archivo_already = self._update_archivos(copied_refs)
                result['documentos_updated'] = doc_updated
                result['documentos_already_internal'] = doc_already
                result['archivos_updated'] = archivo_updated
                result['archivos_already_internal'] = archivo_already
                result['db_write_performed'] = True
                result['db_storage_refs_pointing_to_desktop'] = self._desktop_storage_ref_count()
                result['safe_to_delete_source'] = (
                    result['matrix_rows_missing_source'] == 0
                    and result['documentos_missing_source'] == 0
                    and not result['copy_failures']
                    and result['db_storage_refs_pointing_to_desktop'] == 0
                    and self._all_documents_internal(copied_refs)
                    and self._all_archivos_internal(copied_refs)
                )
                event = create_audit_event(
                    event_type='documentos.expediente_integral.files_ingested',
                    entity_type='expediente_integral_file_ingest',
                    entity_id=RUN_REF,
                    summary='Ingesta fisica verificada de expediente integral',
                    actor_identifier=options['actor_identifier'],
                    metadata={
                        'unique_file_jobs': result['unique_file_jobs'],
                        'copied_files': result['copied_files'],
                        'already_verified_files': result['already_verified_files'],
                        'documentos_updated': result['documentos_updated'],
                        'archivos_updated': result['archivos_updated'],
                        'safe_to_delete_source': result['safe_to_delete_source'],
                    },
                )
                result['audit_event_id'] = event.id

        self._write_outputs(output_path, public_output_path, result)
        self.stdout.write(json.dumps(self._summary(result), ensure_ascii=False))

    def _source_roots(self, configured_roots: list[str]) -> list[Path]:
        roots = [Path(settings.PROJECT_ROOT)]
        for raw_root in configured_roots:
            root = Path(raw_root).expanduser().resolve()
            if root not in roots:
                roots.append(root)
        return roots

    def _build_matrix_jobs(self, rows: list[dict]) -> tuple[dict[str, dict], int]:
        grouped = defaultdict(list)
        missing = 0
        for row in rows:
            checksum = normalize_checksum(row.get('checksum_sha256', ''))
            if not checksum:
                continue
            grouped[checksum].append(row)

        jobs = {}
        for checksum, checksum_rows in grouped.items():
            candidates = [
                row
                for row in checksum_rows
                if row.get('decision') != 'duplicado_exactamente'
                and not row.get('duplicate_of_source_ref')
            ] or checksum_rows
            selected = None
            for row in candidates:
                source_path = Path(row.get('source_absolute_path_private') or '')
                if source_path.exists() and source_path.is_file():
                    selected = row
                    break
            if selected is None:
                for row in checksum_rows:
                    source_path = Path(row.get('source_absolute_path_private') or '')
                    if source_path.exists() and source_path.is_file():
                        selected = row
                        break
            if selected is None:
                missing += len(checksum_rows)
                continue
            source_path = Path(selected.get('source_absolute_path_private') or '').resolve()
            extension = normalize_extension(selected.get('extension', ''), source_path.suffix or '.bin')
            jobs[checksum] = {
                'checksum': checksum,
                'extension': extension,
                'source_path': source_path,
                'source_kind': selected.get('source_kind') or 'matrix',
            }
        return jobs, missing

    def _build_document_jobs(self, source_roots: list[Path]) -> tuple[dict[str, dict], int]:
        jobs = {}
        missing = 0
        for document in DocumentoEmitido.objects.all().order_by('id'):
            checksum = normalize_checksum(document.checksum)
            if not checksum or checksum in jobs:
                continue
            source_path = self._resolve_existing_ref(document.storage_ref, source_roots)
            if source_path is None:
                missing += 1
                continue
            jobs[checksum] = {
                'checksum': checksum,
                'extension': normalize_extension(source_path.suffix, '.pdf'),
                'source_path': source_path,
                'source_kind': 'documento_emitido',
            }
        return jobs, missing

    def _resolve_existing_ref(self, storage_ref: str, source_roots: list[Path]) -> Path | None:
        ref = normalize_reference(storage_ref)
        if not ref:
            return None
        raw_path = Path(ref)
        if raw_path.is_absolute() and raw_path.exists() and raw_path.is_file():
            return raw_path.resolve()
        for root in source_roots:
            candidate = (root / ref).resolve()
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _destination_ref(self, checksum: str, extension: str) -> Path:
        return STORAGE_PREFIX / checksum[:2] / checksum[2:4] / f'{checksum}{extension}'

    def _copy_verified(self, source_path: Path, destination_path: Path, expected_checksum: str) -> str:
        source_checksum = sha256_file(source_path)
        if source_checksum != expected_checksum:
            raise CommandError(
                f'Checksum de fuente no coincide para {source_path.name}: {source_checksum} != {expected_checksum}'
            )
        if destination_path.exists():
            destination_checksum = sha256_file(destination_path)
            if destination_checksum != expected_checksum:
                raise CommandError(f'Destino existente con checksum distinto: {destination_path}')
            return 'already_verified'

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = destination_path.with_suffix(destination_path.suffix + '.tmp')
        try:
            with source_path.open('rb') as source, temp_path.open('wb') as target:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    target.write(chunk)
            temp_checksum = sha256_file(temp_path)
            if temp_checksum != expected_checksum:
                raise CommandError(f'Copia temporal con checksum distinto: {temp_path}')
            os.replace(temp_path, destination_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()
        return 'copied'

    def _update_documentos(self, copied_refs: dict[str, str]) -> tuple[int, int]:
        updated = 0
        already = 0
        for document in DocumentoEmitido.objects.all().order_by('id'):
            storage_ref = copied_refs.get(normalize_checksum(document.checksum))
            if not storage_ref:
                continue
            if document.storage_ref == storage_ref:
                already += 1
                continue
            document.storage_ref = storage_ref
            document.save(update_fields=['storage_ref', 'updated_at'])
            updated += 1
        return updated, already

    def _update_archivos(self, copied_refs: dict[str, str]) -> tuple[int, int]:
        updated = 0
        already = 0
        for archivo in ArchivoExpediente.objects.all().order_by('id'):
            storage_ref = copied_refs.get(normalize_checksum(archivo.checksum_sha256))
            if not storage_ref:
                continue
            if archivo.storage_ref == storage_ref:
                already += 1
                continue
            archivo.storage_ref = storage_ref
            archivo.save(update_fields=['storage_ref', 'updated_at'])
            updated += 1
        return updated, already

    def _desktop_storage_ref_count(self) -> int:
        return (
            DocumentoEmitido.objects.filter(storage_ref__icontains='Desktop\\Revisar').count()
            + ArchivoExpediente.objects.filter(storage_ref__icontains='Desktop\\Revisar').count()
            + DocumentoEmitido.objects.filter(storage_ref__icontains='Desktop/Revisar').count()
            + ArchivoExpediente.objects.filter(storage_ref__icontains='Desktop/Revisar').count()
        )

    def _all_documents_internal(self, copied_refs: dict[str, str]) -> bool:
        for document in DocumentoEmitido.objects.all():
            storage_ref = copied_refs.get(normalize_checksum(document.checksum))
            if storage_ref and document.storage_ref != storage_ref:
                return False
        return True

    def _all_archivos_internal(self, copied_refs: dict[str, str]) -> bool:
        for archivo in ArchivoExpediente.objects.all():
            storage_ref = copied_refs.get(normalize_checksum(archivo.checksum_sha256))
            if storage_ref and archivo.storage_ref != storage_ref:
                return False
        return True

    def _write_outputs(self, output_path: Path, public_output_path: Path, result: dict) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        public_output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        public_payload = {
            key: value
            for key, value in result.items()
            if key not in {'private_manifest'}
        }
        public_output_path.write_text(
            json.dumps(public_payload, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )

    def _summary(self, result: dict) -> dict:
        return {
            key: result[key]
            for key in [
                'scope',
                'apply_requested',
                'db_write_performed',
                'unique_file_jobs',
                'copied_files',
                'already_verified_files',
                'matrix_rows_missing_source',
                'documentos_missing_source',
                'documentos_updated',
                'archivos_updated',
                'db_storage_refs_pointing_to_desktop',
                'safe_to_delete_source',
                'audit_event_id',
            ]
        }
