import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.stage7_reporting_readiness import collect_stage7_reporting_readiness


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
            'para no versionar evidencia o metadatos de reporting.'
        ) from error


class Command(BaseCommand):
    help = 'Audita readiness local de Etapa 7 Reporting trazable sin usar datos reales ni servicios externos.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='', help='Ruta opcional para escribir el JSON de auditoria.')
        parser.add_argument('--stage5-evidence-ref', default='', help='Referencia no sensible a ledger/cierres.')
        parser.add_argument('--stage6-evidence-ref', default='', help='Referencia no sensible a renta anual.')
        parser.add_argument('--reporting-api-proof-ref', default='', help='Referencia no sensible a prueba API reporting.')
        parser.add_argument('--backoffice-visual-ref', default='', help='Referencia no sensible a prueba visual backoffice.')
        parser.add_argument('--responsible-ref', default='', help='Referencia no sensible a responsables del frente.')
        parser.add_argument(
            '--fail-on-attention',
            action='store_true',
            help='Sale con error si readiness Etapa 7 Reporting no queda lista para cierre.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_stage7_reporting_readiness(
                stage5_evidence_ref=options['stage5_evidence_ref'],
                stage6_evidence_ref=options['stage6_evidence_ref'],
                reporting_api_proof_ref=options['reporting_api_proof_ref'],
                backoffice_visual_ref=options['backoffice_visual_ref'],
                responsible_ref=options['responsible_ref'],
            )
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar readiness Etapa 7 Reporting porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_attention'] and not result['ready_for_stage7_reporting']:
            raise CommandError(
                'Readiness Etapa 7 Reporting no cerrada: '
                f'classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
