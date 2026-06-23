import json

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_progress import collect_company_accounting_candidates
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)


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
            output_path = resolve_command_path(options['output'])
            validate_local_evidence_output_path(
                output_path,
                artifact_description='candidatos contables o tributarios',
            )

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
