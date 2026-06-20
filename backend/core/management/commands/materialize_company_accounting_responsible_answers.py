import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
    validate_company_accounting_responsible_answers,
    write_company_accounting_responsible_answers_review,
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
        / 'responsible-answers'
        / f'{_safe_path_component(company_ref)}-ac{_safe_path_component(fiscal_year)}-at{_safe_path_component(tax_year)}'
    )


class Command(BaseCommand):
    help = (
        'Materializa una revision redactada de respuestas responsables para contabilidad/renta. '
        'No guarda texto libre, PII ni adjuntos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--questions-packet', required=True, help='JSON company-accounting-responsible-questions.v1.')
        parser.add_argument('--answers', required=True, help='JSON company-accounting-responsible-answers.v1.')
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--allow-incomplete',
            action='store_true',
            help=(
                'Permite materializar revision observada con preguntas sin responder; '
                'las preguntas faltantes siguen siendo bloqueantes.'
            ),
        )
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si la revision conserva issues bloqueantes.',
        )

    def handle(self, *args, **options):
        questions_packet = _read_json(_resolve_path(options['questions_packet']), label='questions_packet')
        answers_payload = _read_json(_resolve_path(options['answers']), label='answers')
        try:
            review = validate_company_accounting_responsible_answers(
                questions_packet=questions_packet,
                answers_payload=answers_payload,
                require_complete=not options['allow_incomplete'],
            )
        except ValueError as error:
            raise CommandError(f'No se pudo validar respuestas responsables: {error}') from error

        output_dir = (
            _resolve_path(options['output_dir'])
            if options.get('output_dir')
            else _default_output_dir(
                company_ref=review['company_ref'],
                fiscal_year=review['fiscal_year'],
                tax_year=review['tax_year'],
            )
        )
        _validate_output_dir(output_dir)
        try:
            written = write_company_accounting_responsible_answers_review(review=review, output_dir=output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo escribir revision de respuestas responsables: {error}') from error
        except OSError as error:
            raise CommandError('No se pudo escribir revision de respuestas responsables.') from error

        summary = {
            'schema_version': review['schema_version'],
            'materialized': True,
            'manifest_file': Path(written['manifest_file']).name,
            'expected_manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_ANSWERS_MANIFEST,
            'company_ref': review['company_ref'],
            'fiscal_year': review['fiscal_year'],
            'tax_year': review['tax_year'],
            'questions_total': review['summary']['questions_total'],
            'answers_total': review['summary']['answers_total'],
            'missing_questions_total': review['summary']['missing_questions_total'],
            'blocking_issues_total': review['summary']['blocking_issues_total'],
            'ready_for_responsible_decision_handoff': review['summary']['ready_for_responsible_decision_handoff'],
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        }
        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, default=str))

        if options['fail_on_blocking'] and review['summary']['blocking_issues_total']:
            raise CommandError('La revision de respuestas responsables conserva issues bloqueantes.')
