import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.stage1_matrix_audit import collect_stage1_matrix_audit


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
            'para no versionar evidencia o metadatos de auditoria.'
        ) from error


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
            '--authorization-ref',
            default='',
            help='Referencia no sensible a la autorizacion de uso de la fuente evidencial.',
        )
        parser.add_argument(
            '--responsible-ref',
            default='',
            help='Referencia no sensible al responsable de la fuente o ejecucion del gate.',
        )
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
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_stage1_matrix_audit(
                source_kind=options['source_kind'],
                source_label=options['source_label'],
                authorization_ref=options['authorization_ref'],
                responsible_ref=options['responsible_ref'],
                require_data=options['require_data'],
            )
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar Etapa 1 porque la base configurada no esta migrada o no es accesible. '
                'Ejecuta migrate contra un entorno autorizado antes de este gate.'
            ) from error
        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_violations'] and not result['ready_for_stage1_close']:
            raise CommandError(
                f'Etapa 1 no cerrada: classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
