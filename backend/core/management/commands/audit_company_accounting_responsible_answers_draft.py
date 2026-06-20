import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
    validate_company_accounting_responsible_answers,
    verify_company_accounting_responsible_handoff_packet,
)


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


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


def _read_questions_from_handoff_packet(package_dir: Path) -> dict:
    try:
        verify_company_accounting_responsible_handoff_packet(package_dir=package_dir)
    except ValueError as error:
        raise CommandError(f'No se pudo verificar handoff responsable: {error}') from error
    return _read_json(
        package_dir / COMPANY_ACCOUNTING_RESPONSIBLE_QUESTIONS_MANIFEST,
        label='questions_packet',
    )


class Command(BaseCommand):
    help = (
        'Audita un borrador de respuestas responsables contra preguntas o un '
        'handoff packet verificado, sin escribir manifests de review.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--questions-packet', default='', help='JSON company-accounting-responsible-questions.v1.')
        parser.add_argument(
            '--handoff-packet-dir',
            default='',
            help='Directorio company-accounting-responsible-handoff-packet verificable.',
        )
        parser.add_argument('--answers', required=True, help='JSON company-accounting-responsible-answers.v1.')
        parser.add_argument(
            '--allow-incomplete',
            action='store_true',
            help='Permite auditar borradores con preguntas faltantes, que siguen reportandose como blockers.',
        )
        parser.add_argument(
            '--require-ready',
            action='store_true',
            help='Sale con error si el borrador no queda listo para handoff responsable.',
        )

    def handle(self, *args, **options):
        has_questions_packet = bool(options.get('questions_packet'))
        has_handoff_packet_dir = bool(options.get('handoff_packet_dir'))
        if has_questions_packet == has_handoff_packet_dir:
            raise CommandError('Debe informar exactamente una fuente de preguntas: --questions-packet o --handoff-packet-dir.')

        source_kind = 'handoff_packet' if has_handoff_packet_dir else 'questions_packet'
        questions_packet = (
            _read_questions_from_handoff_packet(_resolve_path(options['handoff_packet_dir']))
            if has_handoff_packet_dir
            else _read_json(_resolve_path(options['questions_packet']), label='questions_packet')
        )
        answers_payload = _read_json(_resolve_path(options['answers']), label='answers')

        try:
            review = validate_company_accounting_responsible_answers(
                questions_packet=questions_packet,
                answers_payload=answers_payload,
                require_complete=not options['allow_incomplete'],
            )
        except ValueError as error:
            raise CommandError(f'No se pudo validar borrador de respuestas responsables: {error}') from error

        issue_codes = sorted({issue['code'] for issue in review['issues']})
        summary = {
            'schema_version': 'company-accounting-responsible-answers-draft-audit.v1',
            'source_kind': source_kind,
            'handoff_packet_verified': has_handoff_packet_dir,
            'company_ref': review['company_ref'],
            'fiscal_year': review['fiscal_year'],
            'tax_year': review['tax_year'],
            'questions_total': review['summary']['questions_total'],
            'answers_total': review['summary']['answers_total'],
            'missing_questions_total': review['summary']['missing_questions_total'],
            'blocking_issues_total': review['summary']['blocking_issues_total'],
            'issue_codes': issue_codes,
            'ready_for_responsible_decision_handoff': review['summary']['ready_for_responsible_decision_handoff'],
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
            'raw_paths_returned': False,
            'writes_review_manifest': False,
        }

        if options['require_ready'] and not summary['ready_for_responsible_decision_handoff']:
            self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True, default=str))
            raise CommandError('El borrador de respuestas responsables no esta listo para handoff.')

        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True, default=str))
