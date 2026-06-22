import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.company_accounting_responsible_answers import (
    audit_company_accounting_responsible_answers_review_presence,
)
from core.reference_validation import is_non_sensitive_control_reference


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


def _validate_local_evidence_path(path: Path, *, option_name: str) -> None:
    if not _is_inside(path, _local_evidence_root()):
        raise CommandError(f'{option_name} debe quedar bajo local-evidence/.')
    relative_path = path.resolve().relative_to(_local_evidence_root()).as_posix()
    if not is_non_sensitive_control_reference(relative_path):
        raise CommandError(f'{option_name} debe usar una ruta relativa no sensible bajo local-evidence/.')


class Command(BaseCommand):
    help = (
        'Audita si existe un company-accounting-responsible-answers-review.json listo '
        'bajo local-evidence sin imprimir rutas, nombres, RUTs ni respuestas crudas.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--search-root',
            default='',
            help='Raiz de busqueda. Debe quedar bajo local-evidence/. Por defecto usa local-evidence/.',
        )
        parser.add_argument(
            '--output',
            default='',
            help='Archivo JSON opcional. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--require-ready',
            action='store_true',
            help='Falla si no hay exactamente un review responsable listo.',
        )

    def handle(self, *args, **options):
        search_root = _resolve_path(options['search_root']) if options.get('search_root') else _local_evidence_root()
        _validate_local_evidence_path(search_root, option_name='--search-root')
        audit = audit_company_accounting_responsible_answers_review_presence(search_root=search_root)

        if options['require_ready'] and not audit['summary']['ready_for_responsible_decision_handoff']:
            raise CommandError('No existe exactamente un review responsable listo bajo local-evidence/.')

        output = options.get('output') or ''
        if output:
            output_path = _resolve_path(output)
            if _is_inside(output_path, _repo_root()):
                _validate_local_evidence_path(output_path, option_name='--output')
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(audit, indent=2, ensure_ascii=True, sort_keys=True, default=str),
                    encoding='utf-8',
                )
            except OSError as error:
                raise CommandError('No se pudo escribir auditoria de review responsable.') from error

        self.stdout.write(json.dumps(audit, indent=2, ensure_ascii=True, sort_keys=True, default=str))
