import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.company_accounting_responsible_questions import (
    build_company_accounting_responsible_questions,
    write_company_accounting_responsible_questions,
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
            'para no versionar evidencia contable, tributaria o respuestas privadas.'
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
        / 'responsible-questions'
        / f'{_safe_path_component(company_ref)}-ac{_safe_path_component(fiscal_year)}-at{_safe_path_component(tax_year)}'
    )


class Command(BaseCommand):
    help = (
        'Materializa un paquete redactado de preguntas concretas para revision responsable '
        'desde artefactos locales ya redactados. No lee documentos reales ni PII.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--company-ref', default='', help='Ref no sensible opcional de empresa.')
        parser.add_argument('--fiscal-year', type=int, default=0, help='Ano comercial opcional.')
        parser.add_argument('--tax-year', type=int, default=0, help='Ano tributario opcional.')
        parser.add_argument('--company-review-package', default='', help='JSON company-accounting-review-package.v1.')
        parser.add_argument('--bank-support-coverage', default='', help='JSON company-bank-support auditado/redactado.')
        parser.add_argument('--ownership-validation', default='', help='JSON annual-tax-ownership-patch-validation.v1.')
        parser.add_argument(
            '--controlled-package-readiness',
            default='',
            help='JSON audit_annual_tax_controlled_package_readiness redactado.',
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--fail-on-empty',
            action='store_true',
            help='Sale con error si no se generan preguntas responsables.',
        )

    def handle(self, *args, **options):
        source_specs = {
            'company_review_package': options.get('company_review_package') or '',
            'bank_support_coverage': options.get('bank_support_coverage') or '',
            'ownership_validation': options.get('ownership_validation') or '',
            'controlled_package_readiness': options.get('controlled_package_readiness') or '',
        }
        source_payloads = {
            label: _read_json(_resolve_path(raw_path), label=label)
            for label, raw_path in source_specs.items()
            if raw_path
        }
        if not source_payloads:
            raise CommandError('Debe entregar al menos un artefacto JSON redactado para generar preguntas.')

        try:
            packet = build_company_accounting_responsible_questions(
                source_payloads=source_payloads,
                company_ref=options.get('company_ref') or '',
                fiscal_year=options.get('fiscal_year') or None,
                tax_year=options.get('tax_year') or None,
            )
        except ValueError as error:
            raise CommandError(f'No se pudo construir paquete de preguntas responsables: {error}') from error

        output_dir = (
            _resolve_path(options['output_dir'])
            if options.get('output_dir')
            else _default_output_dir(
                company_ref=packet['company_ref'],
                fiscal_year=packet['fiscal_year'],
                tax_year=packet['tax_year'],
            )
        )
        _validate_output_dir(output_dir)
        try:
            written = write_company_accounting_responsible_questions(packet=packet, output_dir=output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo escribir paquete de preguntas responsables: {error}') from error

        summary = {
            'schema_version': packet['schema_version'],
            'materialized': True,
            'manifest_file': Path(written['manifest_file']).name,
            'company_ref': packet['company_ref'],
            'fiscal_year': packet['fiscal_year'],
            'tax_year': packet['tax_year'],
            'questions_total': packet['summary']['questions_total'],
            'categories': packet['summary']['categories'],
            'ready_for_responsible_review': packet['summary']['ready_for_responsible_review'],
            'ready_for_productive_accounting_review': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        }
        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, default=str))

        if options['fail_on_empty'] and not packet['summary']['questions_total']:
            raise CommandError('No se generaron preguntas responsables desde los artefactos entregados.')
