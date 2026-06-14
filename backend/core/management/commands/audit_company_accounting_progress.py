import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_progress import collect_company_accounting_progress
from patrimonio.models import Empresa


def _resolve_output_path(raw_output_path: str) -> Path:
    output_path = Path(raw_output_path).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    return output_path.resolve()


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
        'Audita avance contable/renta por empresa y ano comercial sin leer fuentes externas '
        'ni ejecutar integraciones.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True, help='ID interno de Empresa a auditar.')
        parser.add_argument('--fiscal-year', type=int, required=True, help='Ano comercial a auditar, por ejemplo 2025.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de progreso.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si la empresa/ano no esta lista para revision hasta dossier/export local.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_company_accounting_progress(
                empresa_id=options['empresa_id'],
                fiscal_year=options['fiscal_year'],
            )
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe Empresa con id={options["empresa_id"]}.') from error
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar avance contable porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not result['ready_for_company_accounting_review']:
            raise CommandError(
                'Avance contable/renta incompleto: '
                f'classification={result["classification"]}, '
                f'progress={result["progress_percent"]}%, '
                f'next={result["next_blocking_phase"]}.'
            )
