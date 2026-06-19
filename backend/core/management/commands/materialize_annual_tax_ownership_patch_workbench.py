import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_ownership_patch_workbench import (
    build_annual_tax_ownership_patch_workbench,
    write_annual_tax_ownership_patch_workbench,
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
            'El workbench ownership crea un patch privado rellenable; si --output-dir queda dentro '
            'del repo, debe estar bajo local-evidence/ para no versionar nombres o RUTs.'
        )


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


def _safe_path_component(value) -> str:
    raw_value = str(value or '').strip()
    if re.search(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b', raw_value) or '://' in raw_value or '@' in raw_value:
        return 'sensitive-ref'
    normalized = raw_value.lower()
    normalized = re.sub(r'[^a-z0-9_.-]+', '-', normalized).strip('-._')
    return normalized or 'sin-ref'


def _default_output_dir(template: dict) -> Path:
    company_ref = _safe_path_component(template.get('company_ref'))
    commercial_year = _safe_path_component(template.get('commercial_year'))
    tax_year = _safe_path_component(template.get('tax_year'))
    return (
        _repo_root()
        / 'local-evidence'
        / 'stage6'
        / 'ownership-patch-workbench'
        / f'{company_ref}-ac{commercial_year}-at{tax_year}'
    )


class Command(BaseCommand):
    help = (
        'Materializa un workbench local para completar ownership patch privado. '
        'No lee documentos reales, no escribe DB y no imprime nombres/RUTs.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--template', required=True, help='JSON annual-tax-ownership-snapshot-template.v1.')
        parser.add_argument('--checklist', default='', help='JSON annual-tax-ownership-review-checklist.v1 opcional.')
        parser.add_argument(
            '--responsible-answers-review',
            default='',
            help='JSON company-accounting-responsible-answers-review.v1 opcional y redactado.',
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--responsible-ref',
            default='pending-responsible-review',
            help='Ref no sensible por defecto para el patch privado.',
        )
        parser.add_argument(
            '--approval-ref',
            default='pending-approval',
            help='Ref no sensible por defecto para el patch privado.',
        )

    def handle(self, *args, **options):
        template_path = _resolve_path(options['template'])
        template = _read_json(template_path, label='template')
        checklist = None
        if options.get('checklist'):
            checklist = _read_json(_resolve_path(options['checklist']), label='checklist')
        responsible_answers_review = None
        if options.get('responsible_answers_review'):
            responsible_answers_review = _read_json(
                _resolve_path(options['responsible_answers_review']),
                label='responsible_answers_review',
            )

        output_dir = _resolve_path(options['output_dir']) if options.get('output_dir') else _default_output_dir(template)
        _validate_output_dir(output_dir)

        try:
            workbench = build_annual_tax_ownership_patch_workbench(
                template=template,
                checklist=checklist,
                responsible_answers_review=responsible_answers_review,
                responsible_ref=options['responsible_ref'],
                approval_ref=options['approval_ref'],
            )
            written = write_annual_tax_ownership_patch_workbench(workbench=workbench, output_dir=output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo materializar ownership patch workbench: {error}') from error
        except OSError as error:
            raise CommandError('No se pudo escribir ownership patch workbench.') from error

        manifest = workbench['manifest']
        summary = {
            'schema_version': manifest['schema_version'],
            'company_ref': manifest['company_ref'],
            'commercial_year': manifest['commercial_year'],
            'tax_year': manifest['tax_year'],
            'materialized': True,
            'manifest_file': Path(written['manifest_file']).name,
            'private_patch_draft_file': Path(written['private_patch_draft_file']).name,
            'draft_ready_for_manual_completion': manifest['summary']['draft_ready_for_manual_completion'],
            'reviewable_candidates_total': manifest['summary']['reviewable_candidates_total'],
            'rendered_candidates_total': manifest['summary']['rendered_candidates_total'],
            'responsible_answers_present': manifest['summary']['responsible_answers_present'],
            'responsible_answers_ready': manifest['summary']['responsible_answers_ready'],
            'questions_total': manifest['summary']['questions_total'],
            'private_questions_total': manifest['summary']['private_questions_total'],
            'writes_database': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        }
        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, default=str))
