import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_package_template import (
    build_annual_tax_controlled_db_load_template,
    load_manifest_json,
)
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)


def _resolve_path(raw_path: str) -> Path:
    return resolve_command_path(raw_path)


def _validate_output_path(output_path: Path) -> None:
    validate_local_evidence_output_path(output_path)


def _load_optional_json(path_option: str) -> dict | None:
    if not path_option:
        return None
    path = _resolve_path(path_option)
    if not path.exists() or not path.is_file():
        raise CommandError(f'No existe JSON opcional: {path}')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise CommandError(f'No se pudo leer JSON opcional: {error}') from error
    if not isinstance(payload, dict):
        raise CommandError(f'JSON opcional debe ser objeto: {path}')
    return payload


class Command(BaseCommand):
    help = (
        'Construye un template seguro para completar una carga DB local AC/AT; '
        'no escribe DB, no copia documentos y mantiene outputs esperados separados.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON de build_annual_tax_source_manifest.')
        parser.add_argument(
            '--ownership-review-checklist',
            default='',
            help='JSON annual-tax-ownership-review-checklist.v1 para adjuntar handoff ownership redactado.',
        )
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
            ownership_review_checklist = _load_optional_json(options.get('ownership_review_checklist') or '')
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CommandError(f'Manifest invalido: {error}') from error

        template = build_annual_tax_controlled_db_load_template(
            manifest=manifest,
            ownership_review_checklist=ownership_review_checklist,
        )
        rendered = json.dumps(template, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not template['summary']['source_documentation_confirmed_for_ac2024_at2025']:
            raise CommandError('El manifiesto no confirma fuentes minimas AC2024/AT2025 para la prueba espejo.')
