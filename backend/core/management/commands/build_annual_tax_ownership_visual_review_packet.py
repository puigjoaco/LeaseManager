import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_load_plan import load_manifest_json
from core.annual_tax_ownership_visual_review_packet import build_annual_tax_ownership_visual_review_packet
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_required_local_evidence_output_dir_path,
    validate_required_local_evidence_output_path,
)


def _validate_local_evidence_path(path: Path) -> None:
    validate_required_local_evidence_output_path(
        path,
        artifact_description='imagenes e indices ownership potencialmente sensibles',
    )


def _validate_local_evidence_dir(path: Path) -> None:
    validate_required_local_evidence_output_dir_path(
        path,
        artifact_description='imagenes ownership potencialmente sensibles',
    )


def _read_text(path: Path, *, label: str) -> str:
    if not path.exists() or not path.is_file():
        raise CommandError(f'No existe {label} JSON o no es un archivo legible.')
    try:
        return path.read_text(encoding='utf-8')
    except OSError as error:
        raise CommandError(f'No se pudo leer {label} JSON.') from error


def _read_review_json(path: Path) -> dict:
    try:
        payload = json.loads(_read_text(path, label='review'))
    except json.JSONDecodeError as error:
        raise CommandError(f'review JSON invalido: line {error.lineno}, column {error.colno}.') from error
    if not isinstance(payload, dict):
        raise CommandError('review JSON debe ser un objeto.')
    return payload


class Command(BaseCommand):
    help = (
        'Renderiza paginas iniciales de candidatos ownership a imagenes locales '
        'para OCR/revision manual; no escribe DB ni guarda texto crudo.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON de build_annual_tax_source_manifest.')
        parser.add_argument('--review', required=True, help='JSON de review_annual_tax_ownership_candidates.')
        parser.add_argument('--source-root', required=True, help='Carpeta externa usada por el manifiesto.')
        parser.add_argument('--company-ref', required=True, help='Referencia no sensible de empresa.')
        parser.add_argument('--commercial-year', type=int, required=True, help='Ano comercial fuente.')
        parser.add_argument('--tax-year', type=int, default=None, help='Ano tributario destino.')
        parser.add_argument('--output-dir', required=True, help='Directorio bajo local-evidence/ para las imagenes renderizadas.')
        parser.add_argument('--output', required=True, help='JSON de indice bajo local-evidence/.')
        parser.add_argument('--max-pages-per-candidate', type=int, default=2)
        parser.add_argument('--resolution', type=int, default=150)
        parser.add_argument(
            '--fail-if-no-render',
            action='store_true',
            help='Sale con error si no se renderiza ninguna pagina.',
        )

    def handle(self, *args, **options):
        manifest_path = resolve_command_path(options['manifest'])
        review_path = resolve_command_path(options['review'])
        source_root = resolve_command_path(options['source_root'])
        output_dir = resolve_command_path(options['output_dir'])
        output_path = resolve_command_path(options['output'])
        _validate_local_evidence_dir(output_dir)
        _validate_local_evidence_path(output_path)

        try:
            manifest = load_manifest_json(_read_text(manifest_path, label='manifest'))
            review = _read_review_json(review_path)
            packet = build_annual_tax_ownership_visual_review_packet(
                manifest=manifest,
                review=review,
                source_root=source_root,
                output_dir=output_dir,
                company_ref=options['company_ref'],
                commercial_year=options['commercial_year'],
                tax_year=options.get('tax_year'),
                max_pages_per_candidate=options['max_pages_per_candidate'],
                resolution=options['resolution'],
            )
        except (ValueError, FileNotFoundError) as error:
            raise CommandError(f'Paquete visual ownership invalido: {error}') from error

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(packet, indent=2, ensure_ascii=True), encoding='utf-8')
        except OSError as error:
            raise CommandError('No se pudo escribir el indice visual ownership.') from error
        self.stdout.write(json.dumps(packet['summary'], ensure_ascii=True))

        if options['fail_if_no_render'] and not packet['summary']['rendered_pages_total']:
            raise CommandError('No se renderizo ninguna pagina de candidatos ownership.')
