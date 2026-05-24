import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.stage2_cobranza_readiness import collect_stage2_cobranza_readiness


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
            'para no versionar evidencia o metadatos de cobranza/canales.'
        ) from error


class Command(BaseCommand):
    help = 'Audita readiness de Etapa 2 Cobranza/Canales sin ejecutar proveedores externos.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default='', help='Ruta opcional para escribir el JSON de auditoria.')
        parser.add_argument(
            '--source-kind',
            default='local',
            choices=['local', 'fixture', 'demo', 'snapshot_controlado', 'real_autorizado'],
            help='Tipo de fuente auditada; solo snapshot_controlado o real_autorizado pueden cerrar Etapa 2.',
        )
        parser.add_argument('--source-label', default='', help='Etiqueta no sensible de la fuente auditada.')
        parser.add_argument(
            '--authorization-ref',
            default='',
            help='Referencia no sensible a la autorizacion de uso de la fuente evidencial.',
        )
        parser.add_argument('--stage1-evidence-ref', default='', help='Referencia no sensible a evidencia Etapa 1.')
        parser.add_argument('--email-proof-ref', default='', help='Referencia no sensible a prueba controlada Email.')
        parser.add_argument('--webpay-proof-ref', default='', help='Referencia no sensible a prueba controlada WebPay.')
        parser.add_argument('--responsible-ref', default='', help='Referencia no sensible a responsables del frente.')
        parser.add_argument(
            '--reference-date',
            default='',
            help='Fecha de corte YYYY-MM-DD para auditar mora de pagos abiertos vencidos.',
        )
        parser.add_argument(
            '--fail-on-attention',
            action='store_true',
            help='Sale con error si readiness Etapa 2 no queda lista para cierre.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            reference_date = None
            if options['reference_date']:
                reference_date = date.fromisoformat(options['reference_date'])
            result = collect_stage2_cobranza_readiness(
                source_kind=options['source_kind'],
                stage1_evidence_ref=options['stage1_evidence_ref'],
                email_proof_ref=options['email_proof_ref'],
                webpay_proof_ref=options['webpay_proof_ref'],
                responsible_ref=options['responsible_ref'],
                source_label=options['source_label'],
                authorization_ref=options['authorization_ref'],
                reference_date=reference_date,
            )
        except ValueError as error:
            raise CommandError('--reference-date debe usar formato YYYY-MM-DD.') from error
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo auditar readiness Etapa 2 porque la base configurada no esta migrada o no es accesible.'
            ) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_attention'] and not result['ready_for_stage2_cobranza']:
            raise CommandError(
                'Readiness Etapa 2 no cerrada: '
                f'classification={result["classification"]}, '
                f'blocking={result["issue_counts"].get("blocking", 0)}.'
            )
