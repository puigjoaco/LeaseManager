import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.management.local_evidence_paths import (
    repo_root,
    resolve_command_path,
    validate_local_evidence_output_dir_path,
)
from sii.models import AnnualTaxExport
from sii.services import (
    verify_annual_tax_presentation_review_bundle,
    write_annual_tax_presentation_review_bundle,
)


def _resolve_output_dir(raw_output_dir: str) -> Path:
    return resolve_command_path(raw_output_dir)


def _default_output_dir(export: AnnualTaxExport) -> Path:
    return (
        repo_root()
        / 'local-evidence'
        / 'stage6'
        / 'presentation-review-bundles'
        / f'export-{export.pk}-at{export.anio_tributario}'
    )


def _validate_output_dir(output_dir: Path) -> None:
    validate_local_evidence_output_dir_path(
        output_dir,
        artifact_description='bundles tributarios de revision',
    )


class Command(BaseCommand):
    help = (
        'Materializa y verifica un bundle local de revision de presentacion desde '
        'AnnualTaxReviewChecklist; no declara formato oficial, no presenta SII y no calcula renta final.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--export-id', required=True, type=int, help='ID del AnnualTaxExport preparado.')
        parser.add_argument('--export-package-dir', default='', help='Directorio del paquete local AnnualTaxExport.')
        parser.add_argument('--f22-candidate-dir', default='', help='Directorio del candidato F22 materializado.')
        parser.add_argument(
            '--ddjj-ascii-candidate-dir',
            action='append',
            default=[],
            help='Directorio de un candidato DDJJ ASCII materializado. Puede repetirse.',
        )
        parser.add_argument(
            '--ddjj-zip-candidate-dir',
            action='append',
            default=[],
            help='Directorio de un candidato DDJJ ZIP materializado. Puede repetirse.',
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )

    def handle(self, *args, **options):
        try:
            export = AnnualTaxExport.objects.select_related(
                'empresa',
                'proceso_renta_anual',
            ).get(pk=options['export_id'])
        except AnnualTaxExport.DoesNotExist as error:
            raise CommandError(f'No existe AnnualTaxExport id={options["export_id"]}.') from error
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo leer AnnualTaxExport porque la base no esta migrada o accesible.'
            ) from error

        output_dir = (
            _resolve_output_dir(options['output_dir'])
            if options['output_dir']
            else _default_output_dir(export).resolve()
        )
        _validate_output_dir(output_dir)
        export_package_dir = _resolve_output_dir(options['export_package_dir']) if options['export_package_dir'] else None
        f22_candidate_dir = _resolve_output_dir(options['f22_candidate_dir']) if options['f22_candidate_dir'] else None
        ddjj_ascii_candidate_dirs = [
            _resolve_output_dir(path)
            for path in options['ddjj_ascii_candidate_dir']
            if path
        ]
        ddjj_zip_candidate_dirs = [
            _resolve_output_dir(path)
            for path in options['ddjj_zip_candidate_dir']
            if path
        ]

        try:
            written = write_annual_tax_presentation_review_bundle(
                export,
                output_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_candidate_dir,
                ddjj_ascii_candidate_dirs=ddjj_ascii_candidate_dirs,
                ddjj_zip_candidate_dirs=ddjj_zip_candidate_dirs,
            )
            verification = verify_annual_tax_presentation_review_bundle(
                export,
                output_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_candidate_dir,
                ddjj_ascii_candidate_dirs=ddjj_ascii_candidate_dirs,
                ddjj_zip_candidate_dirs=ddjj_zip_candidate_dirs,
            )
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar bundle de revision anual: {error}') from error

        result = {
            'materialized': True,
            'annual_tax_export_id': export.pk,
            'empresa_id': export.empresa_id,
            'proceso_renta_anual_id': export.proceso_renta_anual_id,
            'anio_tributario': export.anio_tributario,
            'anio_comercial': export.anio_comercial,
            'bundle_version': written['summary']['bundle_version'],
            'classification': verification['classification'],
            'review_decision_state': verification['review_decision_state'],
            'output_dir': str(Path(written['output_dir']).resolve()),
            'manifest_file': Path(written['manifest_file']).name,
            'bundle_hash': verification['bundle_hash'],
            'artifacts_total': verification['artifacts_total'],
            'artifacts_verified_total': verification['artifacts_verified_total'],
            'artifact_kinds': written['summary']['artifact_kinds'],
            'verification': verification,
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'ready_for_controlled_presentation_review': verification['ready_for_controlled_presentation_review'],
            'ready_for_sii_submission': False,
            'requires_official_format_gate': True,
            'requires_explicit_submission_authorization': True,
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))
