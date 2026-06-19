import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_ownership_patch_injector import (
    inject_annual_tax_ownership_patch_into_controlled_package,
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


def _validate_local_evidence_path(path: Path, *, label: str, reason: str) -> None:
    if _is_inside(path, _repo_root()) and not _is_inside(path, _local_evidence_root()):
        raise CommandError(
            f'{label} {reason}; si queda dentro del repo, debe estar bajo local-evidence/ '
            'para no versionar evidencia contable, tributaria o PII.'
        )


def _read_json(path: Path, *, label: str) -> dict:
    if not path.exists() or not path.is_file():
        raise CommandError(f'No existe {label} JSON: {path}')
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise CommandError(f'{label} JSON invalido: {error}') from error
    if not isinstance(payload, dict):
        raise CommandError(f'{label} JSON debe ser un objeto.')
    return payload


class Command(BaseCommand):
    help = (
        'Inyecta un ownership patch validado en un paquete controlado AC/AT; '
        'no escribe DB y nunca imprime nombres/RUTs a stdout.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--package',
            required=True,
            help='JSON annual-tax-controlled-db-load.v1 o annual-tax-controlled-db-load-template.v1.',
        )
        parser.add_argument('--template', required=True, help='JSON annual-tax-ownership-snapshot-template.v1.')
        parser.add_argument(
            '--patch',
            required=True,
            help='JSON annual-tax-ownership-controlled-patch.v1 u ownership object completado localmente.',
        )
        parser.add_argument(
            '--output',
            required=True,
            help='Ruta obligatoria para escribir el paquete resultante; contiene nombres/RUTs.',
        )
        parser.add_argument(
            '--replace-existing',
            action='store_true',
            help='Permite reemplazar package.ownership existente solo con decision controlada.',
        )

    def handle(self, *args, **options):
        package_path = _resolve_path(options['package'])
        template_path = _resolve_path(options['template'])
        patch_path = _resolve_path(options['patch'])
        output_path = _resolve_path(options['output'])

        _validate_local_evidence_path(
            patch_path,
            label='El ownership patch',
            reason='puede contener nombres y RUTs',
        )
        _validate_local_evidence_path(
            output_path,
            label='El output',
            reason='contiene package.ownership con nombres y RUTs',
        )

        package_payload = _read_json(package_path, label='package')
        template = _read_json(template_path, label='template')
        patch = _read_json(patch_path, label='patch')

        try:
            result = inject_annual_tax_ownership_patch_into_controlled_package(
                package_payload=package_payload,
                template=template,
                patch=patch,
                replace_existing=bool(options['replace_existing']),
            )
        except ValueError as error:
            raise CommandError(f'No se pudo inyectar ownership patch: {error}') from error

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=True, default=str), encoding='utf-8')

        summary = {
            'schema_version': result['schema_version'],
            'company_ref': result['company_ref'],
            'commercial_year': result['commercial_year'],
            'tax_year': result['tax_year'],
            'output_written': True,
            'ownership_injected': True,
            'participants_count': result['summary']['participants_count'],
            'ready_for_db_writer': result['summary']['ready_for_db_writer'],
            'ready_for_annual_generation': result['summary']['ready_for_annual_generation'],
            'annual_generation_blockers': result['summary']['annual_generation_blockers'],
            'blockers': result['summary']['blockers'],
            'output_contains_ownership_pii': True,
            'writes_database': False,
            'final_tax_calculation': False,
            'sii_submission': False,
        }
        self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=True, default=str))
