import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_db_load import apply_annual_tax_controlled_db_load
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)
from patrimonio.models import Empresa


def _read_package(path: Path) -> dict:
    if not path.exists() or not path.is_file():
        raise CommandError('No existe package JSON o no es un archivo legible.')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise CommandError(f'Package JSON invalido: line {error.lineno}, column {error.colno}.') from error
    except OSError as error:
        raise CommandError('No se pudo leer package JSON.') from error
    if not isinstance(payload, dict):
        raise CommandError('Package JSON debe ser un objeto.')
    return payload


def _write_result(path: Path, *, rendered: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding='utf-8')
    except OSError as error:
        raise CommandError('No se pudo escribir resultado de carga controlada.') from error


class Command(BaseCommand):
    help = (
        'Valida o aplica una carga DB local controlada AC/AT desde un paquete JSON '
        'normalizado; no lee PDFs, no copia fuentes y no usa salidas finales como inputs.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--package', required=True, help='JSON normalizado annual-tax-controlled-db-load.v1.')
        parser.add_argument('--empresa-id', required=True, type=int, help='Empresa destino en DB local/controlada.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de resultado.')
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Escribe DB local/controlada. Sin este flag solo valida el paquete y no escribe.',
        )
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si el paquete no queda listo para generacion anual.',
        )

    def handle(self, *args, **options):
        package_path = resolve_command_path(options['package'])

        output_path = None
        if options['output']:
            output_path = resolve_command_path(options['output'])
            validate_local_evidence_output_path(output_path)

        package = _read_package(package_path)
        if isinstance(package, dict) and isinstance(package.get('package_draft'), dict):
            package = package['package_draft']

        try:
            empresa = Empresa.objects.get(pk=options['empresa_id'])
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe empresa_id={options["empresa_id"]}.') from error

        try:
            result = apply_annual_tax_controlled_db_load(
                empresa=empresa,
                package=package,
                write_database=bool(options['apply']),
            )
        except ValueError as error:
            raise CommandError(f'Carga controlada invalida: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            _write_result(output_path, rendered=rendered)
        else:
            self.stdout.write(rendered)

        if options['fail_on_blocking'] and not result['ready_for_annual_generation']:
            blockers = ','.join(result['blockers'])
            raise CommandError(f'Carga controlada no lista para generacion anual: blockers={blockers}.')
