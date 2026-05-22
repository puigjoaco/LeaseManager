import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from documentos.readiness import (
    AUTHORIZED_DOCUMENT_SOURCE_KINDS,
    collect_document_readiness,
)


LOCAL_DIAGNOSTIC_SOURCE_KINDS = {'demo', 'fixture', 'local'}


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
            'para no versionar evidencia o metadatos documentales.'
        ) from error


class Command(BaseCommand):
    help = 'Audita readiness documental local de Etapa 5 sin leer storage ni datos externos.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='', help='Ruta opcional para escribir el JSON de auditoria.')
        parser.add_argument('--final-policy-ref', default='', help='Referencia no sensible a la politica final aprobada.')
        parser.add_argument('--responsible-ref', default='', help='Referencia no sensible a responsables del proceso documental.')
        parser.add_argument('--controlled-pdf-ref', default='', help='Referencia no sensible a prueba PDF controlada.')
        parser.add_argument(
            '--source-kind',
            default='local',
            choices=sorted(LOCAL_DIAGNOSTIC_SOURCE_KINDS | AUTHORIZED_DOCUMENT_SOURCE_KINDS),
            help=(
                'Tipo de fuente auditada. local, fixture y demo diagnostican; '
                'solo snapshot_controlado o real_autorizado permiten cierre.'
            ),
        )
        parser.add_argument(
            '--fail-on-attention',
            action='store_true',
            help='Sale con error si readiness documental no queda lista para cierre.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_document_readiness(
                final_policy_ref=options['final_policy_ref'],
                responsible_ref=options['responsible_ref'],
                controlled_pdf_ref=options['controlled_pdf_ref'],
                source_kind=options['source_kind'],
            )
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar readiness documental porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_attention'] and not result['ready_for_stage5_documents']:
            raise CommandError(
                'Readiness documental Etapa 5 no cerrada: '
                f'classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
