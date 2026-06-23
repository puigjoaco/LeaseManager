import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_load_plan import (
    build_annual_tax_controlled_load_plan,
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


def _read_manifest(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        raise CommandError('No existe manifest JSON o no es un archivo legible.')
    try:
        return load_manifest_json(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise CommandError(f'Manifest JSON invalido: line {error.lineno}, column {error.colno}.') from error
    except OSError as error:
        raise CommandError('No se pudo leer manifest JSON.') from error
    except ValueError as error:
        raise CommandError(f'Manifest invalido: {error}') from error


def _write_plan(path: Path, *, rendered: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding='utf-8')
    except OSError as error:
        raise CommandError('No se pudo escribir plan de carga controlada.') from error


class Command(BaseCommand):
    help = (
        'Construye un plan read-only de carga controlada desde un manifiesto AC/AT; '
        'no escribe DB, no copia documentos y no usa outputs esperados como input.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON de build_annual_tax_source_manifest.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON del plan.')
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si el plan todavia no esta listo para carga DB local.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        manifest = _read_manifest(manifest_path)

        try:
            plan = build_annual_tax_controlled_load_plan(manifest=manifest)
        except ValueError as error:
            raise CommandError('Plan de carga controlada invalido; revisar entradas controladas.') from error
        rendered = json.dumps(plan, indent=2, ensure_ascii=True)
        if output_path is not None:
            _write_plan(output_path, rendered=rendered)
        else:
            self.stdout.write(rendered)

        if options['fail_on_blocking'] and not plan['summary']['ready_for_db_load']:
            blockers = ','.join(plan['blockers'])
            raise CommandError(f'Plan de carga controlada no listo para DB: blockers={blockers}.')
