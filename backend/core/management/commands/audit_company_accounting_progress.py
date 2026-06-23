import json

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_progress import collect_company_accounting_progress
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)
from patrimonio.models import Empresa


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
            output_path = resolve_command_path(options['output'])
            validate_local_evidence_output_path(output_path)

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
