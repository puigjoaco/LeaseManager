import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.stage3_conciliacion_readiness import collect_stage3_conciliacion_readiness


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
            'para no versionar evidencia o metadatos de conciliacion/banco.'
        ) from error


class Command(BaseCommand):
    help = 'Audita readiness local de Etapa 3 Banco/Conciliacion sin conectar proveedores bancarios.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='', help='Ruta opcional para escribir el JSON de auditoria.')
        parser.add_argument('--stage2-evidence-ref', default='', help='Referencia no sensible a evidencia Etapa 2.')
        parser.add_argument('--bank-proof-ref', default='', help='Referencia no sensible a prueba banco/snapshot.')
        parser.add_argument('--balance-square-ref', default='', help='Referencia no sensible a cuadratura sistema/banco.')
        parser.add_argument('--responsible-ref', default='', help='Referencia no sensible a responsables del frente.')
        parser.add_argument(
            '--fail-on-attention',
            action='store_true',
            help='Sale con error si readiness Etapa 3 no queda lista para cierre.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_stage3_conciliacion_readiness(
                stage2_evidence_ref=options['stage2_evidence_ref'],
                bank_proof_ref=options['bank_proof_ref'],
                balance_square_ref=options['balance_square_ref'],
                responsible_ref=options['responsible_ref'],
            )
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar readiness Etapa 3 porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_attention'] and not result['ready_for_stage3_conciliacion']:
            raise CommandError(
                'Readiness Etapa 3 no cerrada: '
                f'classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
