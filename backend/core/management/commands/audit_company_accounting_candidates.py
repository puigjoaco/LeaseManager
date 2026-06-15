import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_progress import collect_company_accounting_candidates


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
            'para no versionar candidatos contables o tributarios.'
        ) from error


class Command(BaseCommand):
    help = (
        'Lista candidatos empresa/ano comercial para ejecutar auditoria de avance contable/renta, '
        'sin leer fuentes externas ni ejecutar integraciones.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=int,
            action='append',
            dest='empresa_ids',
            help='ID interno de Empresa a incluir. Puede repetirse.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de candidatos.')
        parser.add_argument(
            '--fail-on-empty',
            action='store_true',
            help='Sale con error si no hay empresas/anos candidatos en la base consultada.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_company_accounting_candidates(empresa_ids=options.get('empresa_ids'))
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudieron listar candidatos contables porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_empty'] and result['summary']['candidate_companies'] == 0:
            raise CommandError('No hay candidatos empresa/ano comercial para medir avance contable/renta.')
