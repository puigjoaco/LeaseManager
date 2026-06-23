import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)
from sii.models import ProcesoRentaAnual
from sii.services import mark_annual_tax_generated_warnings_reviewed


def _resolve_path(raw_path: str) -> Path:
    return resolve_command_path(raw_path)


def _validate_output_path(output_path: Path) -> None:
    validate_local_evidence_output_path(output_path)


class Command(BaseCommand):
    help = (
        'Registra una revision responsable no sensible sobre warnings generados '
        'de workbooks, registros empresariales y matriz DDJJ/F22 anual. '
        'Sin --apply solo informa conteos y no escribe DB.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--process-id', required=True, type=int, help='ProcesoRentaAnual destino.')
        parser.add_argument(
            '--warning-review-ref',
            required=True,
            help='Referencia no sensible de la revision responsable ya realizada.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de resultado.')
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Escribe DB local/controlada. Sin este flag el comando es dry-run.',
        )
        parser.add_argument(
            '--fail-on-pending',
            action='store_true',
            help='Sale con error si despues de aplicar quedan warnings generados pendientes.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            process = ProcesoRentaAnual.objects.get(pk=options['process_id'])
        except ProcesoRentaAnual.DoesNotExist as error:
            raise CommandError(f'No existe process_id={options["process_id"]}.') from error

        try:
            result = mark_annual_tax_generated_warnings_reviewed(
                process,
                warning_review_ref=options['warning_review_ref'],
                apply=bool(options['apply']),
            )
        except ValueError as error:
            raise CommandError(str(error)) from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_pending'] and int(result['after']['pending_warnings_total'] or 0):
            raise CommandError(
                'Persisten warnings generados pendientes: '
                f'{result["after"]["pending_warnings_total"]}.'
            )
