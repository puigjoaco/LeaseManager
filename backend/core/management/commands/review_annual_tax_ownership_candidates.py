import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_load_plan import load_manifest_json
from core.annual_tax_ownership_candidate_review import review_annual_tax_ownership_candidates


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _validate_output_path(output_path: Path) -> None:
    repo_root = Path(settings.PROJECT_ROOT).resolve()
    local_evidence_root = (repo_root / 'local-evidence').resolve()

    try:
        output_path.relative_to(repo_root)
    except ValueError:
        return

    try:
        output_path.relative_to(local_evidence_root)
    except ValueError as error:
        raise CommandError(
            'Si --output queda dentro del repo, debe estar bajo local-evidence/ '
            'para no versionar evidencia contable o tributaria.'
        ) from error


class Command(BaseCommand):
    help = (
        'Revisa candidatos legales de ownership AC/AT desde un manifiesto; '
        'no escribe DB, no copia documentos y no guarda texto crudo ni RUTs.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON de build_annual_tax_source_manifest.')
        parser.add_argument('--source-root', required=True, help='Carpeta externa usada por el manifiesto.')
        parser.add_argument('--company-ref', required=True, help='Referencia no sensible de empresa.')
        parser.add_argument('--commercial-year', type=int, required=True, help='Ano comercial fuente.')
        parser.add_argument('--tax-year', type=int, default=None, help='Ano tributario destino.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de revision.')
        parser.add_argument(
            '--fail-if-no-reviewable-candidate',
            action='store_true',
            help='Sale con error si no hay candidatos utiles para revision controlada.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])
        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f'No existe manifest JSON: {manifest_path}')

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            manifest = load_manifest_json(manifest_path.read_text(encoding='utf-8'))
            review = review_annual_tax_ownership_candidates(
                manifest=manifest,
                source_root=_resolve_path(options['source_root']),
                company_ref=options['company_ref'],
                commercial_year=options['commercial_year'],
                tax_year=options.get('tax_year'),
            )
        except (OSError, ValueError, FileNotFoundError, json.JSONDecodeError) as error:
            raise CommandError(f'Revision ownership invalida: {error}') from error

        rendered = json.dumps(review, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if (
            options['fail_if_no_reviewable_candidate']
            and not review['summary']['candidate_for_controlled_snapshot_review_count']
        ):
            raise CommandError('No hay candidatos ownership utiles para revision controlada.')
