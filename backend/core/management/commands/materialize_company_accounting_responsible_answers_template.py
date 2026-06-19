import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
    build_company_accounting_responsible_answers_template,
    write_company_accounting_responsible_answers_template,
)


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _repo_root() -> Path:
    return Path(settings.PROJECT_ROOT).resolve()


def _local_evidence_root() -> Path:
    return (_repo_root() / 'local-evidence').resolve()


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _validate_output_dir(output_dir: Path) -> None:
    if _is_inside(output_dir, _repo_root()) and not _is_inside(output_dir, _local_evidence_root()):
        raise CommandError(
            'Si --output-dir queda dentro del repo, debe estar bajo local-evidence/ '
            'para no versionar respuestas privadas o evidencia contable/tributaria.'
        )


def _safe_path_component(value) -> str:
    raw_value = str(value or '').strip()
    if re.search(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b', raw_value) or '://' in raw_value or '@' in raw_value:
        return 'sensitive-ref'
    normalized = raw_value.lower()
    normalized = re.sub(r'[^a-z0-9_.-]+', '-', normalized).strip('-._')
    return normalized or 'sin-ref'


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


def _default_output_dir(*, company_ref: str, fiscal_year: int, tax_year: int) -> Path:
    return (
        _repo_root()
        / 'local-evidence'
        / 'stage6'
        / 'responsible-answer-templates'
        / f'{_safe_path_component(company_ref)}-ac{_safe_path_component(fiscal_year)}-at{_safe_path_component(tax_year)}'
    )


class Command(BaseCommand):
    help = (
        'Materializa un template seguro de respuestas responsables para un paquete '
        'company-accounting-responsible-questions.v1.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--questions-packet', required=True, help='JSON company-accounting-responsible-questions.v1.')
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument('--responsible-ref', default='responsible-ref-pending')
        parser.add_argument('--decision-ref', default='decision-ref-pending')
        parser.add_argument('--evidence-ref', default='evidence-ref-pending')
        parser.add_argument('--next-action-ref', default='next-action-pending')

    def handle(self, *args, **options):
        questions_packet = _read_json(_resolve_path(options['questions_packet']), label='questions_packet')
        try:
            template = build_company_accounting_responsible_answers_template(
                questions_packet=questions_packet,
                responsible_ref=options['responsible_ref'],
                decision_ref=options['decision_ref'],
                evidence_ref=options['evidence_ref'],
                next_action_ref=options['next_action_ref'],
            )
        except ValueError as error:
            raise CommandError(f'No se pudo construir template de respuestas responsables: {error}') from error

        output_dir = (
            _resolve_path(options['output_dir'])
            if options.get('output_dir')
            else _default_output_dir(
                company_ref=template['company_ref'],
                fiscal_year=template['fiscal_year'],
                tax_year=template['tax_year'],
            )
        )
        _validate_output_dir(output_dir)
        try:
            written = write_company_accounting_responsible_answers_template(template=template, output_dir=output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo escribir template de respuestas responsables: {error}') from error

        summary = {
            'schema_version': template['schema_version'],
            'template_schema_version': template['template_schema_version'],
            'materialized': True,
            'manifest_file': Path(written['manifest_file']).name,
            'expected_manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_TEMPLATE_MANIFEST,
            'company_ref': template['company_ref'],
            'fiscal_year': template['fiscal_year'],
            'tax_year': template['tax_year'],
            'questions_total': template['template_summary']['questions_total'],
            'answers_total': template['template_summary']['answers_total'],
            'ready_for_responsible_decision_handoff': False,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        }
        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, default=str))
