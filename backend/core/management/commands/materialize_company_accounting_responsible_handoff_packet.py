import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.company_accounting_responsible_answers import (
    COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
    write_company_accounting_responsible_handoff_packet,
    verify_company_accounting_responsible_handoff_packet,
)
from core.management.local_evidence_paths import (
    repo_root,
    resolve_command_path,
    validate_local_evidence_output_dir_path,
)


def _resolve_path(raw_path: str) -> Path:
    return resolve_command_path(raw_path)


def _validate_output_dir(output_dir: Path) -> None:
    validate_local_evidence_output_dir_path(
        output_dir,
        artifact_description='handoffs privados o evidencia contable/tributaria',
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
        repo_root()
        / 'local-evidence'
        / 'stage6'
        / 'responsible-handoff-packets'
        / f'{_safe_path_component(company_ref)}-ac{_safe_path_component(fiscal_year)}-at{_safe_path_component(tax_year)}'
    )


class Command(BaseCommand):
    help = (
        'Materializa un paquete seguro de handoff responsable con preguntas y '
        'template de respuestas, sin completar respuestas ni abrir gates.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--questions-packet', required=True, help='JSON company-accounting-responsible-questions.v1.')
        parser.add_argument(
            '--answers-template',
            required=True,
            help='JSON company-accounting-responsible-answers.template.json.',
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )

    def handle(self, *args, **options):
        questions_packet = _read_json(_resolve_path(options['questions_packet']), label='questions_packet')
        answers_template = _read_json(_resolve_path(options['answers_template']), label='answers_template')

        output_dir = (
            _resolve_path(options['output_dir'])
            if options.get('output_dir')
            else _default_output_dir(
                company_ref=answers_template.get('company_ref') or questions_packet.get('company_ref'),
                fiscal_year=answers_template.get('fiscal_year') or questions_packet.get('fiscal_year'),
                tax_year=answers_template.get('tax_year') or questions_packet.get('tax_year'),
            )
        )
        _validate_output_dir(output_dir)

        try:
            written = write_company_accounting_responsible_handoff_packet(
                questions_packet=questions_packet,
                answers_template=answers_template,
                output_dir=output_dir,
            )
            verification = verify_company_accounting_responsible_handoff_packet(package_dir=output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo materializar handoff responsable: {error}') from error
        except OSError as error:
            raise CommandError('No se pudo escribir handoff responsable.') from error

        summary = {
            'schema_version': verification['schema_version'],
            'materialized': True,
            'verified': verification['verified'],
            'manifest_file': Path(written['manifest_file']).name,
            'expected_manifest_file': COMPANY_ACCOUNTING_RESPONSIBLE_HANDOFF_PACKET_MANIFEST,
            'questions_file': Path(written['questions_file']).name,
            'answers_template_file': Path(written['answers_template_file']).name,
            'company_ref': verification['company_ref'],
            'fiscal_year': verification['fiscal_year'],
            'tax_year': verification['tax_year'],
            'package_hash': verification['package_hash'],
            'questions_total': verification['summary']['questions_total'],
            'answers_total': verification['summary']['answers_total'],
            'pending_answers_total': verification['summary']['pending_answers_total'],
            'readiness_sources_total': verification['summary'].get('readiness_sources_total', 0),
            'ready_for_responsible_answer_completion': verification['summary'][
                'ready_for_responsible_answer_completion'
            ],
            'ready_for_responsible_decision_handoff': False,
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
            'raw_paths_returned': False,
        }
        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, sort_keys=True, default=str))
