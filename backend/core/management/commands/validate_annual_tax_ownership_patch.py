import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_ownership_patch_validator import validate_annual_tax_ownership_patch
from core.management.local_evidence_paths import (
    is_inside,
    local_evidence_root,
    repo_root,
    resolve_command_path,
    validate_local_evidence_output_path,
)


def _resolve_path(raw_path: str) -> Path:
    return resolve_command_path(raw_path)


def _validate_output_path(output_path: Path) -> None:
    validate_local_evidence_output_path(output_path)


def _validate_patch_path(patch_path: Path) -> None:
    if is_inside(patch_path, repo_root()) and not is_inside(patch_path, local_evidence_root()):
        raise CommandError(
            'El ownership patch puede contener nombres y RUTs; si --patch queda dentro del repo, '
            'debe estar bajo local-evidence/ para no versionar PII.'
        )


def _read_json(path: Path, *, label: str) -> dict:
    if not path.exists() or not path.is_file():
        raise CommandError(f'No existe {label} JSON o no es un archivo legible.')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise CommandError(f'{label} JSON invalido: line {error.lineno}, column {error.colno}.') from error
    except OSError as error:
        raise CommandError(f'No se pudo leer {label} JSON.') from error
    if not isinstance(payload, dict):
        raise CommandError(f'{label} JSON debe ser un objeto.')
    return payload


def _write_json(path: Path, *, rendered: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding='utf-8')
    except OSError as error:
        raise CommandError('No se pudo escribir la validacion redactada.') from error


class Command(BaseCommand):
    help = (
        'Valida un patch local de ownership AC/AT contra el template controlado; '
        'no escribe DB y emite solo reporte redactado sin nombres ni RUTs.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--template', required=True, help='JSON annual-tax-ownership-snapshot-template.v1.')
        parser.add_argument(
            '--patch',
            required=True,
            help='JSON annual-tax-ownership-controlled-patch.v1 o ownership object completado localmente.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de validacion redactada.')
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si el patch no queda listo para inyectarse al paquete controlado.',
        )

    def handle(self, *args, **options):
        template_path = _resolve_path(options['template'])
        patch_path = _resolve_path(options['patch'])
        _validate_patch_path(patch_path)

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            template = _read_json(template_path, label='template')
            patch = _read_json(patch_path, label='patch')
            result = validate_annual_tax_ownership_patch(template=template, patch=patch)
        except ValueError as error:
            raise CommandError(f'Ownership patch invalido: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            _write_json(output_path, rendered=rendered)
        else:
            self.stdout.write(rendered)

        if options['fail_on_blocking'] and not result['ready_for_controlled_db_load']:
            blockers = ','.join(result['blockers'])
            raise CommandError(f'Ownership patch no listo para paquete controlado: blockers={blockers}.')
