import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.stage1_matrix_audit import collect_stage1_matrix_audit


class Command(BaseCommand):
    help = 'Audita la matriz Etapa 1 contrato-propiedad-cuenta-facturacion sobre la base configurada.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source-kind',
            default='local',
            choices=['local', 'fixture', 'demo', 'snapshot_controlado', 'real_autorizado'],
            help='Tipo de fuente auditada; solo snapshot_controlado o real_autorizado pueden cerrar evidencia.',
        )
        parser.add_argument('--source-label', default='', help='Etiqueta no sensible de la fuente auditada.')
        parser.add_argument(
            '--require-data',
            action='store_true',
            help='Exige que existan los agregados minimos de Etapa 1.',
        )
        parser.add_argument(
            '--fail-on-violations',
            action='store_true',
            help='Sale con error si la matriz no esta lista para cerrar Etapa 1.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir el JSON de auditoria.')

    def handle(self, *args, **options):
        try:
            result = collect_stage1_matrix_audit(
                source_kind=options['source_kind'],
                source_label=options['source_label'],
                require_data=options['require_data'],
            )
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar Etapa 1 porque la base configurada no esta migrada o no es accesible. '
                'Ejecuta migrate contra un entorno autorizado antes de este gate.'
            ) from error
        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if options['output']:
            output_path = Path(options['output'])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_violations'] and not result['ready_for_stage1_close']:
            raise CommandError(
                f'Etapa 1 no cerrada: classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
