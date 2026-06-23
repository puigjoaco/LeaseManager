import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_ownership_snapshot_template import build_annual_tax_ownership_snapshot_template
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)


def _resolve_path(raw_path: str) -> Path:
    return resolve_command_path(raw_path)


def _validate_output_path(output_path: Path) -> None:
    validate_local_evidence_output_path(output_path)


def _read_json(path: Path, *, label: str) -> dict:
    if not path.exists() or not path.is_file():
        raise CommandError(f'No existe {label} JSON o no es un archivo legible.')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        raise CommandError(f'{label} JSON invalido: line {error.lineno}, column {error.colno}.') from error
    except OSError as error:
        raise CommandError(f'No se pudo leer {label} JSON.') from error
    if not isinstance(payload, dict):
        raise CommandError(f'{label} JSON debe ser un objeto.')
    return payload


class Command(BaseCommand):
    help = (
        'Construye un template controlado para completar ownership desde '
        'candidatos legales revisados; no escribe DB ni infiere socios.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--review', required=True, help='JSON de review_annual_tax_ownership_candidates.')
        parser.add_argument('--company-ref', required=True, help='Referencia no sensible de empresa.')
        parser.add_argument('--commercial-year', type=int, required=True, help='Ano comercial fuente.')
        parser.add_argument('--tax-year', type=int, default=None, help='Ano tributario destino.')
        parser.add_argument(
            '--responsible-ref',
            default='codex-local-review',
            help='Referencia no sensible del responsable de preparar el template.',
        )
        parser.add_argument(
            '--approval-ref',
            default='',
            help='Referencia no sensible de aprobacion para completar luego el paquete.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON del template.')
        parser.add_argument(
            '--fail-if-no-candidates',
            action='store_true',
            help='Sale con error si no hay candidatos legales revisables para el template.',
        )

    def handle(self, *args, **options):
        review_path = _resolve_path(options['review'])

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            review = _read_json(review_path, label='review')
            template = build_annual_tax_ownership_snapshot_template(
                review=review,
                company_ref=options['company_ref'],
                commercial_year=options['commercial_year'],
                tax_year=options.get('tax_year'),
                responsible_ref=options['responsible_ref'],
                approval_ref=options['approval_ref'],
            )
        except ValueError as error:
            raise CommandError(f'Template ownership invalido: {error}') from error

        rendered = json.dumps(template, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if (
            options['fail_if_no_candidates']
            and not template['decision']['can_patch_controlled_db_load_package_after_manual_completion']
        ):
            raise CommandError('No hay candidatos ownership revisables para completar el template.')
