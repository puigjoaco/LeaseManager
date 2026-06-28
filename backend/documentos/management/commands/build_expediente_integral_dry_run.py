from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.management.local_evidence_paths import (
    local_evidence_root,
    resolve_command_path,
    validate_local_evidence_output_dir_path,
)
from core.reference_validation import is_non_sensitive_control_reference


DEFAULT_AUDIT_REL = Path('revisar-document-audit') / '2026-06-21'
DEFAULT_ORDER_REL = (
    Path('patrimonial-order-audit-pass5389') / 'patrimonial_order_audit_private_pass5389.csv'
)
DEFAULT_OUTPUT_REL = DEFAULT_AUDIT_REL / 'expediente-integral-dry-run-pass5390'
PUBLIC_SCAN_PATTERNS = {
    'absolute_path_hits': re.compile(r'(?:[A-Za-z]:[\\/]|\\\\|/Users/|/home/)', re.IGNORECASE),
    'email_hits': re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', re.IGNORECASE),
    'rut_hits': re.compile(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b'),
    'url_hits': re.compile(r'https?://', re.IGNORECASE),
}

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.tif', '.tiff', '.bmp'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
SPREADSHEET_EXTENSIONS = {'.xlsx', '.xls', '.csv', '.tsv'}
TEXT_EXTENSIONS = {'.txt', '.md'}
WORD_EXTENSIONS = {'.docx', '.doc', '.rtf'}
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z'}
DOCUMENT_EXTENSIONS = {'.pdf'} | WORD_EXTENSIONS | TEXT_EXTENSIONS

SECTION_MAP = {
    '01_societario_por_acto': '00_societario',
    '02_propiedades_por_activo': '01_propiedades_y_locales',
    '03_contratos_por_propiedad_local': '02_contratos_por_local',
    '04_tributario_contable': '03_tributario_contable',
    '05_revision_manual': '99_revision_manual',
    '06_persona_natural_renta': '06_persona_natural',
}


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise CommandError(f'No existe archivo requerido: {path}')
    with path.open(newline='', encoding='utf-8-sig') as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def safe_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha256(str(value or '').encode('utf-8', errors='ignore')).hexdigest()[:16]
    return f'{prefix}-{digest}'


def norm(value: str) -> str:
    return ' '.join(str(value or '').lower().replace('\\', '/').split())


def extension_of(row: dict) -> str:
    value = str(row.get('extension') or Path(row.get('relative_path') or row.get('file_name') or '').suffix)
    value = value.strip().lower()
    if value and not value.startswith('.'):
        value = f'.{value}'
    return value or '.sin_extension'


def source_ref(row: dict, source_kind: str) -> str:
    return safe_ref(source_kind, row.get('sha256') or row.get('relative_path') or row.get('absolute_path'))


def category_for_extension(extension: str) -> str:
    if extension in IMAGE_EXTENSIONS:
        return 'imagen'
    if extension in VIDEO_EXTENSIONS:
        return 'video'
    if extension in SPREADSHEET_EXTENSIONS:
        return 'planilla'
    if extension in TEXT_EXTENSIONS:
        return 'texto'
    if extension in WORD_EXTENSIONS or extension == '.pdf':
        return 'documento_fuente'
    if extension in ARCHIVE_EXTENSIONS:
        return 'comprimido'
    return 'otro'


def subcategory_for_path(relative_path: str, extension: str) -> str:
    text = norm(relative_path)
    if 'foto' in text or extension in IMAGE_EXTENSIONS or extension in VIDEO_EXTENSIONS:
        return '05_fotos_y_videos'
    if 'contrato' in text or 'arriendo' in text or 'arrendamiento' in text:
        return '06_contratos'
    if any(token in text for token in ['escritura', 'constitucion', 'modificacion', 'diario oficial']):
        return '00_societario'
    if any(token in text for token in ['avaluo', 'tasacion', 'dominio', 'conservador', 'inscripcion', 'cbr']):
        return '01_titulos_cbr_dominio'
    if any(token in text for token in ['plano', 'recepcion']):
        return '04_planos_y_recepcion'
    if any(token in text for token in ['renta', 'tributario', 'contable', 'impuesto']):
        return '09_tributario_contable'
    if any(token in text for token in ['banco', 'mutuo', 'financiamiento']):
        return '04_bancario_financiamiento_mutuos'
    if any(token in text for token in ['sucesion', 'testamento', 'posesion efectiva', 'particion']):
        return '00_sucesion_base'
    return '00_ficha_general'


def infer_titular(relative_path: str, source_top_folder: str, order_row: dict | None) -> str:
    if order_row and order_row.get('proposed_titular'):
        proposed_titular = str(order_row['proposed_titular']).strip()
        if 'herencia papa' in norm(proposed_titular):
            return 'Requiere clasificacion titular'
        return proposed_titular
    text = norm(f'{source_top_folder} {relative_path}')
    if 'persona natural' in text:
        return 'Joaquin Puig Persona Natural'
    if 'inmobiliaria puig spa' in text:
        return 'Inmobiliaria Puig SPA'
    if 'santa maria' in text or 'santamaria' in text:
        return 'Sociedad Inmobiliaria Santa Maria Ltda'
    if 'san cristobal' in text or 'sancristobal' in text:
        return 'Sociedad Inmobiliaria San Cristobal Ltda'
    if 'quepe' in text:
        return 'Sociedad Inmobiliaria Quepe Ltda'
    if any(token in text for token in ['sucesion', 'testamento', 'posesion efectiva', 'particion', 'usufructo']):
        return 'Sucesion / patrimonio familiar'
    if 'herencia papa' in text:
        return 'Requiere clasificacion titular'
    return 'Requiere clasificacion titular'


def infer_section(relative_path: str, extension: str, order_row: dict | None, titular: str) -> str:
    if order_row and order_row.get('proposed_section'):
        return SECTION_MAP.get(order_row['proposed_section'], order_row['proposed_section'])
    if titular == 'Joaquin Puig Persona Natural':
        return '06_persona_natural'
    text = norm(relative_path)
    if any(token in text for token in ['escritura', 'constitucion', 'modificacion', 'diario oficial']):
        return '00_societario'
    if any(token in text for token in ['contrato', 'arriendo', 'arrendamiento', 'resiliacion', 'anexo']):
        return '02_contratos_por_local'
    if any(token in text for token in ['renta', 'tributario', 'contable', 'impuesto']):
        return '03_tributario_contable'
    if any(token in text for token in ['banco', 'mutuo', 'financiamiento']):
        return '04_bancario_financiamiento_mutuos'
    if extension in IMAGE_EXTENSIONS or extension in VIDEO_EXTENSIONS:
        return '01_propiedades_y_locales'
    if any(token in text for token in ['propiedad', 'local', 'avaluo', 'tasacion', 'dominio', 'inscripcion']):
        return '01_propiedades_y_locales'
    if 'camioneta' in text:
        return '05_activos_no_inmobiliarios'
    return '99_revision_manual'


def decision_for_row(row: dict, extension: str, order_row: dict | None, is_duplicate_alias: bool) -> str:
    if is_duplicate_alias:
        return 'duplicado_exactamente'
    if extension != '.pdf':
        return 'archivo_expediente_nuevo'
    if order_row:
        db_status = order_row.get('db_status', '')
        if db_status == 'loaded_in_documentoemitido':
            return 'documento_emitido_existente'
        return 'documento_emitido_nuevo'
    return 'requiere_revision_manual'


def storage_ref_for(row: dict, category: str, extension: str) -> str:
    checksum = str(row.get('sha256') or '').strip().lower()
    digest = checksum[:24] if checksum else safe_ref('sha', row.get('relative_path', ''))
    safe_extension = extension if re.fullmatch(r'\.[a-z0-9]+', extension) else '.bin'
    return f'storage/expedientes/{category}/{digest}{safe_extension}'


def archive_status(extension: str, source_path: str) -> tuple[str, int]:
    if extension == '.zip':
        try:
            with zipfile.ZipFile(source_path) as archive:
                return 'zip_inventariado', len(archive.infolist())
        except (OSError, zipfile.BadZipFile):
            return 'zip_no_abrible_requiere_revision', 0
    if extension == '.rar':
        return 'rar_requiere_extractor_externo', 0
    if extension in ARCHIVE_EXTENSIONS:
        return 'comprimido_requiere_revision', 0
    return '', 0


def scan_public_files(paths: list[Path]) -> dict:
    hit_counts = Counter()
    hit_files = []
    for path in paths:
        text = path.read_text(encoding='utf-8', errors='replace')
        file_hits = {}
        for label, pattern in PUBLIC_SCAN_PATTERNS.items():
            count = len(pattern.findall(text))
            if count:
                hit_counts[label] += count
                file_hits[label] = count
        if file_hits:
            hit_files.append({'file': path.name, 'hits': file_hits})
    return {
        'files_scanned': len(paths),
        'hit_counts': {label: hit_counts.get(label, 0) for label in PUBLIC_SCAN_PATTERNS},
        'hit_files': hit_files,
        'total_hits': sum(hit_counts.values()),
    }


class Command(BaseCommand):
    help = 'Genera dry-run integral de expedientes desde inventarios Revisar, Persona Natural y matriz patrimonial.'

    def add_arguments(self, parser):
        default_audit_base = local_evidence_root() / DEFAULT_AUDIT_REL
        parser.add_argument('--audit-base', default=str(default_audit_base))
        parser.add_argument('--company-inventory', default='')
        parser.add_argument('--persona-inventory', default='')
        parser.add_argument('--order-matrix', default='')
        parser.add_argument('--output-dir', default=str(local_evidence_root() / DEFAULT_OUTPUT_REL))
        parser.add_argument('--expected-total', type=int, default=2182)

    def handle(self, *args, **options):
        audit_base = resolve_command_path(options['audit_base'])
        company_inventory = resolve_command_path(options['company_inventory']) if options['company_inventory'] else audit_base / 'revisar_inventory_sha256.csv'
        persona_inventory = resolve_command_path(options['persona_inventory']) if options['persona_inventory'] else audit_base / 'persona_natural_inventory_sha256_pass7.csv'
        order_matrix = resolve_command_path(options['order_matrix']) if options['order_matrix'] else audit_base / DEFAULT_ORDER_REL
        output_dir = resolve_command_path(options['output_dir'])
        validate_local_evidence_output_dir_path(
            output_dir,
            option_name='--output-dir',
            artifact_description='matriz integral de expedientes',
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        source_rows = []
        for row in read_csv(company_inventory):
            source_rows.append({**row, '_source_kind': 'revisar-empresas', '_source_top_folder': row.get('source_top_folder', '')})
        for row in read_csv(persona_inventory):
            source_rows.append({**row, '_source_kind': 'persona-natural', '_source_top_folder': '1. Persona Natural'})

        order_rows = read_csv(order_matrix)
        order_by_checksum = {row.get('checksum', '').lower(): row for row in order_rows if row.get('checksum')}
        sha_groups = defaultdict(list)
        for index, row in enumerate(source_rows):
            sha_groups[str(row.get('sha256') or '').lower()].append(index)
        canonical_by_sha = {
            sha: indexes[0]
            for sha, indexes in sha_groups.items()
            if sha
        }

        output_rows = []
        for index, row in enumerate(source_rows, start=1):
            checksum = str(row.get('sha256') or '').lower()
            ext = extension_of(row)
            order_row = order_by_checksum.get(checksum)
            relpath = row.get('relative_path', '')
            source_top = row.get('_source_top_folder') or row.get('source_top_folder') or ''
            canonical_index = canonical_by_sha.get(checksum, index - 1)
            is_duplicate_alias = checksum and canonical_index != index - 1
            canonical_row = source_rows[canonical_index] if checksum else row
            category = category_for_extension(ext)
            titular = infer_titular(relpath, source_top, order_row)
            section = infer_section(relpath, ext, order_row, titular)
            subcategory = subcategory_for_path(relpath, ext)
            decision = decision_for_row(row, ext, order_row, is_duplicate_alias)
            storage_ref = storage_ref_for(row, category, ext)
            mime_type = mimetypes.guess_type(f'file{ext}')[0] or 'application/octet-stream'
            source_file_ref = source_ref(row, row['_source_kind'])
            canonical_source_ref = source_ref(canonical_row, canonical_row.get('_source_kind', row['_source_kind']))
            asset_seed = order_row.get('proposed_asset_group_ref', '') if order_row else row.get('inferred_asset_folder', '')
            expediente_ref = safe_ref('expediente', f'{titular}|{section}|{asset_seed or subcategory}')
            archive_audit_status, archive_internal_entries = archive_status(ext, row.get('absolute_path', ''))
            state = 'confirmado'
            if decision == 'duplicado_exactamente':
                state = 'duplicado_exactamente'
            elif decision == 'requiere_revision_manual':
                state = 'requiere_revision_manual'
            elif 'Requiere clasificacion' in titular:
                state = 'requiere_revision_manual'
            public_path = f'{titular}/{section}/{subcategory}/{source_file_ref}{ext}'
            if not is_non_sensitive_control_reference(public_path):
                public_path = f'{titular}/{section}/{subcategory}/{source_file_ref}'

            output_rows.append(
                {
                    'integral_audit_ref': f'INT5390-{index:05d}',
                    'source_file_ref': source_file_ref,
                    'canonical_source_file_ref': canonical_source_ref,
                    'checksum_sha256': checksum,
                    'extension': ext,
                    'mime_type': mime_type,
                    'size_bytes': row.get('size_bytes', ''),
                    'source_kind': row['_source_kind'],
                    'source_top_folder': source_top,
                    'final_titular': titular,
                    'final_section': section,
                    'final_subcategory': subcategory,
                    'expediente_destino_ref': expediente_ref,
                    'archivo_categoria': category,
                    'decision': decision,
                    'estado_clasificacion': state,
                    'storage_ref_propuesto': storage_ref,
                    'duplicate_of_source_ref': '' if not is_duplicate_alias else canonical_source_ref,
                    'documento_emitido_ref': order_row.get('safe_document_ref', '') if order_row else '',
                    'documento_emitido_status': order_row.get('db_status', '') if order_row else '',
                    'persona_natural_boundary': str(titular == 'Joaquin Puig Persona Natural'),
                    'origen_auditoria': 'Persona Natural' if row['_source_kind'] == 'persona-natural' else source_top,
                    'archive_audit_status': archive_audit_status,
                    'archive_internal_entries': archive_internal_entries,
                    'proposed_public_order_path': public_path,
                    'source_relative_path_private': relpath,
                    'source_absolute_path_private': row.get('absolute_path', ''),
                    'proposed_private_order_path': order_row.get('proposed_order_path_private', '') if order_row else '',
                }
            )

        public_fields = [
            'integral_audit_ref',
            'source_file_ref',
            'canonical_source_file_ref',
            'checksum_sha256',
            'extension',
            'mime_type',
            'size_bytes',
            'source_kind',
            'source_top_folder',
            'final_titular',
            'final_section',
            'final_subcategory',
            'expediente_destino_ref',
            'archivo_categoria',
            'decision',
            'estado_clasificacion',
            'storage_ref_propuesto',
            'duplicate_of_source_ref',
            'documento_emitido_ref',
            'documento_emitido_status',
            'persona_natural_boundary',
            'origen_auditoria',
            'archive_audit_status',
            'archive_internal_entries',
            'proposed_public_order_path',
        ]
        private_fields = public_fields + [
            'source_relative_path_private',
            'source_absolute_path_private',
            'proposed_private_order_path',
        ]
        public_csv = output_dir / 'expediente_integral_dry_run_public_pass5390.csv'
        private_csv = output_dir / 'expediente_integral_dry_run_private_pass5390.csv'
        summary_json = output_dir / 'expediente_integral_dry_run_public_summary_pass5390.json'
        validation_json = output_dir / 'expediente_integral_dry_run_private_validation_pass5390.json'
        write_csv(public_csv, output_rows, public_fields)
        write_csv(private_csv, output_rows, private_fields)

        public_scan = scan_public_files([public_csv])
        by_decision = Counter(row['decision'] for row in output_rows)
        by_titular = Counter(row['final_titular'] for row in output_rows)
        by_extension = Counter(row['extension'] for row in output_rows)
        by_category = Counter(row['archivo_categoria'] for row in output_rows)
        loaded_order_rows = sum(1 for row in order_rows if row.get('db_status') == 'loaded_in_documentoemitido')
        persona_prepared_rows = sum(1 for row in order_rows if row.get('persona_natural_boundary') == 'True')
        summary = {
            'scope': 'expediente_integral_dry_run_pass5390',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'source_rows_total': len(output_rows),
            'expected_total': options['expected_total'],
            'unique_sha256_total': len([sha for sha in sha_groups if sha]),
            'duplicate_sha256_groups': sum(1 for items in sha_groups.values() if len(items) > 1),
            'duplicate_file_entries': sum(len(items) - 1 for items in sha_groups.values() if len(items) > 1),
            'loaded_company_document_rows_from_order_matrix': loaded_order_rows,
            'persona_natural_prepared_rows_from_order_matrix': persona_prepared_rows,
            'herencia_papa_as_final_titular_rows': sum(
                count
                for titular, count in by_titular.items()
                if 'herencia papa' in norm(titular)
            ),
            'by_decision': dict(sorted(by_decision.items())),
            'by_titular': dict(sorted(by_titular.items())),
            'by_extension': dict(sorted(by_extension.items())),
            'by_archivo_categoria': dict(sorted(by_category.items())),
            'public_csv': public_csv.name,
            'private_csv': private_csv.name,
            'db_write_performed': False,
            'storage_move_performed': False,
            'desktop_folder_mutation_performed': False,
            'public_sensitive_scan': public_scan,
            'public_sensitive_scan_clear': public_scan['total_hits'] == 0,
        }
        summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        final_scan = scan_public_files([public_csv, summary_json])
        summary['public_sensitive_scan'] = final_scan
        summary['public_sensitive_scan_clear'] = final_scan['total_hits'] == 0
        summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

        validation_errors = []
        if options['expected_total'] and len(output_rows) != options['expected_total']:
            validation_errors.append('source_total_mismatch')
        if summary['herencia_papa_as_final_titular_rows'] != 0:
            validation_errors.append('herencia_papa_used_as_final_titular')
        if not summary['public_sensitive_scan_clear']:
            validation_errors.append('public_output_contains_sensitive_reference')
        invalid_non_pdf = [
            row for row in output_rows
            if row['extension'] != '.pdf'
            and row['decision'] not in {'archivo_expediente_nuevo', 'duplicado_exactamente'}
        ]
        if invalid_non_pdf:
            validation_errors.append('non_pdf_not_routed_to_archivo_expediente')
        validation = {
            'scope': 'expediente_integral_dry_run_validation_pass5390',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'validation_passed': not validation_errors,
            'validation_errors': validation_errors,
            'source_rows_total': len(output_rows),
            'expected_total': options['expected_total'],
            'invalid_non_pdf_rows': len(invalid_non_pdf),
            'db_write_performed': False,
            'storage_move_performed': False,
            'desktop_folder_mutation_performed': False,
        }
        validation_json.write_text(json.dumps(validation, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        self.stdout.write(json.dumps(summary, ensure_ascii=False))
