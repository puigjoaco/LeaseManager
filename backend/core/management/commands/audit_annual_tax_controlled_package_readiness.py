import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_package_readiness import (
    audit_annual_tax_controlled_package_readiness,
    load_package_readiness_json,
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
        'Audita si un template/paquete AC/AT normalizado esta completo para entrar al writer DB; '
        'no escribe DB, no lee documentos fuente y no usa outputs finales como inputs.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--package',
            required=True,
            help='JSON annual-tax-controlled-db-load.v1 o annual-tax-controlled-db-load-template.v1.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de auditoria.')
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si el paquete no queda listo para el writer DB.',
        )

    def handle(self, *args, **options):
        package_path = _resolve_path(options['package'])
        if not package_path.exists() or not package_path.is_file():
            raise CommandError('No existe package JSON o no es un archivo legible.')

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            payload = load_package_readiness_json(package_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as error:
            raise CommandError(f'Package JSON invalido: line {error.lineno}, column {error.colno}.') from error
        except OSError as error:
            raise CommandError('No se pudo leer package JSON.') from error
        except ValueError as error:
            raise CommandError(f'Package invalido: {error}') from error

        result = audit_annual_tax_controlled_package_readiness(payload=payload)
        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
            except OSError as error:
                raise CommandError('No se pudo escribir auditoria de paquete controlado.') from error
        else:
            self.stdout.write(rendered)

        if options['fail_on_blocking'] and not result['ready_for_db_writer']:
            blockers = ','.join(result['blockers'])
            raise CommandError(f'Paquete controlado no listo para writer DB: blockers={blockers}.')
