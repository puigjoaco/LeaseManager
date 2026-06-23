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
    build_annual_tax_f22_fixed_width_export_candidate,
    build_f22_fixed_width_entries_from_artifact_matrix,
    verify_annual_tax_f22_fixed_width_export_candidate,
    write_annual_tax_f22_fixed_width_export_candidate,
)


def _resolve_output_dir(raw_output_dir: str) -> Path:
    return resolve_command_path(raw_output_dir)


def _default_output_dir(export: AnnualTaxExport) -> Path:
    return (
        repo_root()
        / 'local-evidence'
        / 'stage6'
        / 'f22-fixed-width-candidates'
        / f'export-{export.pk}-at{export.anio_tributario}'
    )


def _validate_output_dir(output_dir: Path) -> None:
    validate_local_evidence_output_dir_path(
        output_dir,
        artifact_description='archivos F22 ni identificadores tributarios',
    )


class Command(BaseCommand):
    help = (
        'Materializa y verifica un candidato F22 fixed-width local desde un AnnualTaxExport '
        'preparado y su matriz F22 revisada; no imprime RUT ni codigos de certificacion crudos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--export-id', required=True, type=int, help='ID del AnnualTaxExport preparado.')
        parser.add_argument('--rut-number', required=True, help='RUT declarante sin DV, usado solo en archivo local.')
        parser.add_argument('--rut-dv', required=True, help='DV del RUT declarante, usado solo en archivo local.')
        parser.add_argument('--company-code', required=True, help='Codigo empresa/certificacion F22, no se imprime crudo.')
        parser.add_argument('--client-number', required=True, help='Numero cliente/certificacion F22, no se imprime crudo.')
        parser.add_argument(
            '--certification-code-source-ref',
            required=True,
            help='Referencia no sensible de la fuente del codigo de certificacion.',
        )
        parser.add_argument(
            '--certification-responsible-review-ref',
            required=True,
            help='Referencia no sensible del responsable que reviso el codigo de certificacion.',
        )
        parser.add_argument(
            '--certification-code-review-state',
            default='synthetic_for_local_candidate',
            help='Estado revisado del codigo: sintetico local u oficial autorizado revisado.',
        )
        parser.add_argument(
            '--certification-authorized-by-sii',
            action='store_true',
            help='Marca que el codigo esta autorizado por SII. Requiere authorization ref no sensible.',
        )
        parser.add_argument(
            '--certification-authorization-ref',
            default='',
            help='Referencia no sensible de autorizacion SII cuando aplica.',
        )
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
            entries = build_f22_fixed_width_entries_from_artifact_matrix(export)
            candidate = build_annual_tax_f22_fixed_width_export_candidate(
                export,
                rut_number=options['rut_number'],
                rut_dv=options['rut_dv'],
                company_code=options['company_code'],
                client_number=options['client_number'],
                certification_code_source_ref=options['certification_code_source_ref'],
                certification_responsible_review_ref=options['certification_responsible_review_ref'],
                certification_code_review_state=options['certification_code_review_state'],
                certification_authorized_by_sii=options['certification_authorized_by_sii'],
                certification_authorization_ref=options['certification_authorization_ref'],
                entries=entries,
            )
            written = write_annual_tax_f22_fixed_width_export_candidate(candidate, output_dir)
            verification = verify_annual_tax_f22_fixed_width_export_candidate(candidate, output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar candidato F22 fixed-width: {error}') from error

        summary = candidate['summary']
        certification_evidence = summary['certification_code_evidence']
        result = {
            'materialized': True,
            'annual_tax_export_id': export.pk,
            'empresa_id': export.empresa_id,
            'proceso_renta_anual_id': export.proceso_renta_anual_id,
            'anio_tributario': export.anio_tributario,
            'anio_comercial': export.anio_comercial,
            'output_dir': str(Path(written['output_dir']).resolve()),
            'written_file': Path(written['written_file']).name,
            'manifest_file': Path(written['manifest_file']).name,
            'candidate_version': summary['candidate_version'],
            'record_format_version': summary['record_format_version'],
            'record_format_source_url': summary['record_format_source_url'],
            'records_total': verification['records_total'],
            'f22_codes_total': verification['f22_codes_total'],
            'f22_entry_review_evidence_total': verification['f22_entry_review_evidence_total'],
            'content_hash': verification['content_hash'],
            'certification_code_review_state': verification['certification_code_review_state'],
            'certification_code_authorized_by_sii': verification['certification_code_authorized_by_sii'],
            'certification_code_evidence_hash': summary['certification_code_evidence_hash'],
            'company_code_hash': certification_evidence['company_code_hash'],
            'client_number_hash': certification_evidence['client_number_hash'],
            'verification': verification,
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'ready_for_responsible_review': True,
            'ready_for_certification_review': True,
            'ready_for_certification_submission': False,
            'requires_explicit_submission_authorization': True,
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))
