import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_review_package import build_company_accounting_review_package
from patrimonio.models import Empresa


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
            'para no versionar evidencia bancaria, contable o tributaria.'
        ) from error


class Command(BaseCommand):
    help = (
        'Construye un paquete redactado de revision contable/renta por empresa y ano, '
        'combinando avance anual local y cobertura bancaria/leasing sin leer adjuntos reales.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True, help='ID interno de Empresa a auditar.')
        parser.add_argument('--fiscal-year', type=int, required=True, help='Ano comercial a auditar.')
        parser.add_argument(
            '--bank-support-manifest',
            required=True,
            help='JSON redactado company-bank-support-coverage-manifest.v1.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de paquete.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el paquete no queda listo para revision productiva responsable.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['bank_support_manifest'])
        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f'No existe manifest JSON: {manifest_path}')

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            bank_support_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise CommandError(f'Manifest invalido: {error}') from error
        if not isinstance(bank_support_payload, dict):
            raise CommandError('Manifest invalido: la raiz debe ser un objeto JSON.')

        try:
            result = build_company_accounting_review_package(
                empresa_id=options['empresa_id'],
                fiscal_year=options['fiscal_year'],
                bank_support_payload=bank_support_payload,
            )
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe Empresa con id={options["empresa_id"]}.') from error
        except ValueError as error:
            raise CommandError(f'No se pudo construir paquete de revision contable/renta: {error}') from error
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar paquete contable/renta porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not result['ready_for_productive_accounting_review']:
            raise CommandError(
                'Paquete de revision contable/renta incompleto: '
                f'classification={result["classification"]}, '
                f'accounting={result["summary"]["accounting_progress_classification"]}, '
                f'bank_support={result["summary"]["bank_support_classification"]}.'
            )
