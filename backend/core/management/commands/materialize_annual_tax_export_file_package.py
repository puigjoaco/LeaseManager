import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from sii.models import AnnualTaxExport
from sii.services import (
    verify_annual_tax_export_file_package,
    write_annual_tax_export_file_package,
)


def _resolve_output_dir(raw_output_dir: str) -> Path:
    output_dir = Path(raw_output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    return output_dir.resolve()


def _default_output_dir(export: AnnualTaxExport) -> Path:
    return (
        Path(settings.PROJECT_ROOT).resolve()
        / 'local-evidence'
        / 'stage6'
        / 'annual-tax-exports'
        / f'export-{export.pk}-at{export.anio_tributario}'
    )


def _validate_output_dir(output_dir: Path) -> None:
    repo_root = Path(settings.PROJECT_ROOT).resolve()
    local_evidence_root = (repo_root / 'local-evidence').resolve()

    try:
        output_dir.relative_to(repo_root)
    except ValueError:
        return

    try:
        output_dir.relative_to(local_evidence_root)
    except ValueError as error:
        raise CommandError(
            'Si --output-dir queda dentro del repo, debe estar bajo local-evidence/ '
            'para no versionar archivos tributarios anuales.'
        ) from error


class Command(BaseCommand):
    help = (
        'Materializa y verifica el paquete local de archivos de un AnnualTaxExport preparado; '
        'no declara formato oficial, no presenta SII y no calcula renta final.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--export-id', required=True, type=int, help='ID del AnnualTaxExport preparado.')
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )

    def handle(self, *args, **options):
        try:
            export = AnnualTaxExport.objects.select_related('empresa', 'proceso_renta_anual').get(
                pk=options['export_id']
            )
        except AnnualTaxExport.DoesNotExist as error:
            raise CommandError(f'No existe AnnualTaxExport id={options["export_id"]}.') from error
        except (OperationalError, ProgrammingError) as error:
            raise CommandError('No se pudo leer AnnualTaxExport porque la base no esta migrada o accesible.') from error

        output_dir = (
            _resolve_output_dir(options['output_dir'])
            if options['output_dir']
            else _default_output_dir(export).resolve()
        )
        _validate_output_dir(output_dir)

        try:
            written = write_annual_tax_export_file_package(export, output_dir)
            verification = verify_annual_tax_export_file_package(export, output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar AnnualTaxExport: {error}') from error

        result = {
            'materialized': True,
            'annual_tax_export_id': export.pk,
            'empresa_id': export.empresa_id,
            'proceso_renta_anual_id': export.proceso_renta_anual_id,
            'anio_tributario': export.anio_tributario,
            'anio_comercial': export.anio_comercial,
            'output_dir': str(Path(written['output_dir']).resolve()),
            'manifest_file': str(Path(written['manifest_file']).resolve()),
            'written_files': [Path(path).name for path in written['written_files']],
            'files_total': verification['files_total'],
            'package_hash': verification['package_hash'],
            'hash_export': verification['hash_export'],
            'verification': verification,
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'ready_for_responsible_review': True,
            'requires_official_format_gate': True,
            'requires_explicit_submission_authorization': True,
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))
