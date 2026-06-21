import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_review_package import build_company_accounting_review_package
from core.company_document_intake import verify_company_document_intake_package_from_disk
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
            default='',
            help='JSON redactado company-bank-support-coverage-manifest.v1.',
        )
        parser.add_argument(
            '--document-intake-package-dir',
            default='',
            help=(
                'Directorio materializado por materialize_company_document_intake. '
                'Si se usa, el manifiesto bancario/leasing se toma del paquete verificado.'
            ),
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de paquete.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el paquete no queda listo para revision productiva responsable.',
        )

    def handle(self, *args, **options):
        if bool(options['bank_support_manifest']) == bool(options['document_intake_package_dir']):
            raise CommandError(
                'Debe indicar exactamente una fuente: --bank-support-manifest o --document-intake-package-dir.'
            )

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        intake_package = None
        if options['document_intake_package_dir']:
            intake_dir = _resolve_path(options['document_intake_package_dir'])
            try:
                intake_package = verify_company_document_intake_package_from_disk(package_dir=intake_dir)
            except ValueError as error:
                raise CommandError(f'Paquete de intake documental invalido: {error}') from error
            bank_support_payload = intake_package['bank_support_manifest']
        else:
            manifest_path = _resolve_path(options['bank_support_manifest'])
            if not manifest_path.exists() or not manifest_path.is_file():
                raise CommandError('No existe manifest JSON o no es un archivo legible.')
            try:
                bank_support_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as error:
                raise CommandError(f'Manifest JSON invalido: line {error.lineno}, column {error.colno}.') from error
            except OSError as error:
                raise CommandError('No se pudo leer manifest JSON.') from error
            if not isinstance(bank_support_payload, dict):
                raise CommandError('Manifest invalido: la raiz debe ser un objeto JSON.')

        try:
            result = build_company_accounting_review_package(
                empresa_id=options['empresa_id'],
                fiscal_year=options['fiscal_year'],
                bank_support_payload=bank_support_payload,
                document_intake_package=intake_package,
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
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
            except OSError as error:
                raise CommandError('No se pudo escribir paquete de revision contable/renta.') from error
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not result['ready_for_productive_accounting_review']:
            raise CommandError(
                'Paquete de revision contable/renta incompleto: '
                f'classification={result["classification"]}, '
                f'accounting={result["summary"]["accounting_progress_classification"]}, '
                f'bank_support={result["summary"]["bank_support_classification"]}, '
                f'document_intake_ready={result["summary"]["document_intake_ready_for_productive_review"]}.'
            )
