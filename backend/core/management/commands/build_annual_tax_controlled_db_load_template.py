import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_package_template import (
    build_annual_tax_controlled_db_load_template,
    load_manifest_json,
)


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
        'Construye un template seguro para completar una carga DB local AC/AT; '
        'no escribe DB, no copia documentos y mantiene outputs esperados separados.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON de build_annual_tax_source_manifest.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON del template.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el manifiesto no confirma las fuentes minimas de prueba espejo.',
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
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CommandError(f'Manifest invalido: {error}') from error

        template = build_annual_tax_controlled_db_load_template(manifest=manifest)
        rendered = json.dumps(template, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not template['summary']['source_documentation_confirmed_for_ac2024_at2025']:
            raise CommandError('El manifiesto no confirma fuentes minimas AC2024/AT2025 para la prueba espejo.')
