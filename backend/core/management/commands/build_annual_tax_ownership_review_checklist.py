import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_ownership_review_checklist import build_annual_tax_ownership_review_checklist


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


def _validate_output_path(output_path: Path) -> None:
    if _is_inside(output_path, _repo_root()) and not _is_inside(output_path, _local_evidence_root()):
        raise CommandError(
            'El checklist deriva de evidencia societaria; si --output queda dentro del repo, '
            'debe estar bajo local-evidence/.'
        )


def _read_json_object(path: Path, *, label: str) -> dict:
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


def _load_optional_json(path_option: str, *, label: str) -> dict | None:
    if not path_option:
        return None
    return _read_json_object(_resolve_path(path_option), label=label)


class Command(BaseCommand):
    help = (
        'Construye un checklist no sensible para completar ownership AC/AT desde '
        'template, validacion redactada y paquete visual opcional.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--template', required=True, help='JSON annual-tax-ownership-snapshot-template.v1.')
        parser.add_argument('--validation', default='', help='JSON redactado de validate_annual_tax_ownership_patch.')
        parser.add_argument(
            '--visual-packet',
            default='',
            help='JSON annual-tax-ownership-visual-review-packet.v1 u ownership-visual-index.v1 opcional.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir checklist JSON.')
        parser.add_argument(
            '--fail-on-not-ready',
            action='store_true',
            help='Sale con error si el checklist aun no queda listo para inyectar ownership.',
        )

    def handle(self, *args, **options):
        template_path = _resolve_path(options['template'])
        output_path = _resolve_path(options['output']) if options.get('output') else None
        if output_path is not None:
            _validate_output_path(output_path)

        try:
            template = _read_json_object(template_path, label='template')
            validation = _load_optional_json(options.get('validation') or '', label='validation')
            visual_packet = _load_optional_json(options.get('visual_packet') or '', label='visual_packet')
            result = build_annual_tax_ownership_review_checklist(
                template=template,
                validation=validation,
                visual_packet=visual_packet,
            )
        except ValueError as error:
            raise CommandError(f'Checklist ownership invalido: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
            except OSError as error:
                raise CommandError('No se pudo escribir checklist ownership.') from error
        else:
            self.stdout.write(rendered)

        if options['fail_on_not_ready'] and not result['summary']['ready_for_controlled_db_load']:
            blockers = ','.join(result['validation_summary']['blockers'])
            raise CommandError(f'Checklist ownership no listo para paquete controlado: blockers={blockers}.')
