import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_load_plan import load_manifest_json
from core.annual_tax_ownership_visual_review_packet import build_annual_tax_ownership_visual_review_packet


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _validate_local_evidence_path(path: Path) -> None:
    repo_root = Path(settings.PROJECT_ROOT).resolve()
    local_evidence_root = (repo_root / 'local-evidence').resolve()

    try:
        path.relative_to(local_evidence_root)
    except ValueError as error:
        raise CommandError(
            'La salida visual contiene imagenes potencialmente sensibles y debe quedar bajo local-evidence/.'
        ) from error


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
        manifest_path = _resolve_path(options['manifest'])
        review_path = _resolve_path(options['review'])
        source_root = _resolve_path(options['source_root'])
        output_dir = _resolve_path(options['output_dir'])
        output_path = _resolve_path(options['output'])
        _validate_local_evidence_path(output_dir)
        _validate_local_evidence_path(output_path)

        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f'No existe manifest JSON: {manifest_path}')
        if not review_path.exists() or not review_path.is_file():
            raise CommandError(f'No existe review JSON: {review_path}')

        try:
            manifest = load_manifest_json(manifest_path.read_text(encoding='utf-8'))
            review = json.loads(review_path.read_text(encoding='utf-8'))
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
        except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
            raise CommandError(f'Paquete visual ownership invalido: {error}') from error

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(packet, indent=2, ensure_ascii=True), encoding='utf-8')
        self.stdout.write(json.dumps(packet['summary'], ensure_ascii=True))

        if options['fail_if_no_render'] and not packet['summary']['rendered_pages_total']:
            raise CommandError('No se renderizo ninguna pagina de candidatos ownership.')
