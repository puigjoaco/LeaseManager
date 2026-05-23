import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.compliance_data_readiness import collect_compliance_data_readiness


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
            'para no versionar evidencia o metadatos de Compliance.'
        ) from error


def _parse_as_of_date(raw_value: str):
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError as error:
        raise CommandError('--as-of-date debe usar formato ISO YYYY-MM-DD.') from error


class Command(BaseCommand):
    help = 'Audita readiness de Compliance.DatosPersonalesChile2026 sin usar secretos ni datos reales.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='', help='Ruta opcional para escribir el JSON de auditoria.')
        parser.add_argument(
            '--source-kind',
            default='local',
            choices=['local', 'fixture', 'demo', 'snapshot_controlado', 'real_autorizado'],
            help='Tipo de fuente auditada; solo snapshot_controlado o real_autorizado pueden cerrar Compliance.',
        )
        parser.add_argument('--source-label', default='', help='Etiqueta no sensible de la fuente auditada.')
        parser.add_argument(
            '--authorization-ref',
            default='',
            help='Referencia no sensible a la autorizacion de uso de la fuente evidencial.',
        )
        parser.add_argument(
            '--policy-approval-ref',
            default='',
            help='Referencia no sensible a politica de datos personales aprobada.',
        )
        parser.add_argument('--responsible-ref', default='', help='Referencia no sensible a responsables designados.')
        parser.add_argument(
            '--controls-evidence-ref',
            default='',
            help='Referencia no sensible a controles implementados y verificados.',
        )
        parser.add_argument(
            '--archived-evidence-ref',
            default='',
            help='Referencia no sensible a evidencia archivada del checklist formal.',
        )
        parser.add_argument(
            '--legal-review-ref',
            default='',
            help='Referencia no sensible a validacion legal-operativa vigente.',
        )
        parser.add_argument(
            '--as-of-date',
            default='',
            help='Fecha ISO para evaluar la regla de suspension posterior al 2026-12-01.',
        )
        parser.add_argument(
            '--fail-on-attention',
            action='store_true',
            help='Sale con error si readiness Compliance no queda lista para cierre.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            result = collect_compliance_data_readiness(
                source_kind=options['source_kind'],
                source_label=options['source_label'],
                authorization_ref=options['authorization_ref'],
                policy_approval_ref=options['policy_approval_ref'],
                responsible_ref=options['responsible_ref'],
                controls_evidence_ref=options['controls_evidence_ref'],
                archived_evidence_ref=options['archived_evidence_ref'],
                legal_review_ref=options['legal_review_ref'],
                as_of_date=_parse_as_of_date(options['as_of_date']),
            )
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar readiness Compliance porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_attention'] and not result['ready_for_compliance_data']:
            raise CommandError(
                'Readiness Compliance no cerrada: '
                f'classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
