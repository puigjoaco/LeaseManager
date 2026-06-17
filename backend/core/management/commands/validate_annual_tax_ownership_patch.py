import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_ownership_patch_validator import validate_annual_tax_ownership_patch


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
            'Si --output queda dentro del repo, debe estar bajo local-evidence/ '
            'para no versionar evidencia contable o tributaria.'
        )


def _validate_patch_path(patch_path: Path) -> None:
    if _is_inside(patch_path, _repo_root()) and not _is_inside(patch_path, _local_evidence_root()):
        raise CommandError(
            'El ownership patch puede contener nombres y RUTs; si --patch queda dentro del repo, '
            'debe estar bajo local-evidence/ para no versionar PII.'
        )


class Command(BaseCommand):
    help = (
        'Valida un patch local de ownership AC/AT contra el template controlado; '
        'no escribe DB y emite solo reporte redactado sin nombres ni RUTs.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--template', required=True, help='JSON annual-tax-ownership-snapshot-template.v1.')
        parser.add_argument(
            '--patch',
            required=True,
            help='JSON annual-tax-ownership-controlled-patch.v1 o ownership object completado localmente.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de validacion redactada.')
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si el patch no queda listo para inyectarse al paquete controlado.',
        )

    def handle(self, *args, **options):
        template_path = _resolve_path(options['template'])
        patch_path = _resolve_path(options['patch'])
        if not template_path.exists() or not template_path.is_file():
            raise CommandError(f'No existe template JSON: {template_path}')
        if not patch_path.exists() or not patch_path.is_file():
            raise CommandError(f'No existe patch JSON: {patch_path}')
        _validate_patch_path(patch_path)

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            template = json.loads(template_path.read_text(encoding='utf-8'))
            patch = json.loads(patch_path.read_text(encoding='utf-8'))
            result = validate_annual_tax_ownership_patch(template=template, patch=patch)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CommandError(f'Ownership patch invalido: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_blocking'] and not result['ready_for_controlled_db_load']:
            blockers = ','.join(result['blockers'])
            raise CommandError(f'Ownership patch no listo para paquete controlado: blockers={blockers}.')
