import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from sii.models import AnnualTaxExport
from sii.services import (
    build_annual_tax_ddjj_ascii_export_candidate,
    build_annual_tax_ddjj_zip_export_candidate,
    verify_annual_tax_ddjj_zip_export_candidate,
    write_annual_tax_ddjj_zip_export_candidate,
)


def _resolve_output_dir(raw_output_dir: str) -> Path:
    output_dir = Path(raw_output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = Path.cwd() / output_dir
    return output_dir.resolve()


def _default_output_dir(export: AnnualTaxExport, form_code: str) -> Path:
    return (
        Path(settings.PROJECT_ROOT).resolve()
        / 'local-evidence'
        / 'stage6'
        / 'ddjj-zip-candidates'
        / f'export-{export.pk}-form-{form_code}-at{export.anio_tributario}'
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
            'para no versionar ZIP DDJJ ni identificadores tributarios.'
        ) from error


def _load_json_option(*, inline_json: str, json_file: str, label: str):
    if bool(inline_json) == bool(json_file):
        raise CommandError(f'Indica exactamente una fuente para {label}: JSON inline o archivo JSON.')
    try:
        raw_payload = Path(json_file).expanduser().read_text(encoding='utf-8') if json_file else inline_json
        return json.loads(raw_payload)
    except OSError as error:
        raise CommandError(f'No se pudo leer archivo JSON para {label}.') from error
    except json.JSONDecodeError as error:
        raise CommandError(f'{label} debe contener JSON valido.') from error


class Command(BaseCommand):
    help = (
        'Materializa y verifica un ZIP candidato DDJJ local desde un AnnualTaxExport preparado, '
        'registros ASCII revisados y registro de control; no imprime RUT ni registros crudos.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--export-id', required=True, type=int, help='ID del AnnualTaxExport preparado.')
        parser.add_argument('--form-code', required=True, help='Codigo numerico del formulario DDJJ.')
        parser.add_argument('--rut-number', required=True, help='RUT declarante sin DV, usado solo en archivo local.')
        parser.add_argument('--records-json', default='', help='Lista JSON de registros DDJJ ASCII revisados.')
        parser.add_argument('--records-file', default='', help='Archivo JSON con registros DDJJ ASCII revisados.')
        parser.add_argument('--transfer-control-json', default='', help='JSON del registro de control tipo 0 revisado.')
        parser.add_argument('--transfer-control-file', default='', help='Archivo JSON con registro de control tipo 0.')
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )

    def handle(self, *args, **options):
        form_code = str(options['form_code']).strip()
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
            else _default_output_dir(export, form_code).resolve()
        )
        _validate_output_dir(output_dir)
        records = _load_json_option(
            inline_json=options['records_json'],
            json_file=options['records_file'],
            label='records DDJJ ASCII',
        )
        transfer_control_record = _load_json_option(
            inline_json=options['transfer_control_json'],
            json_file=options['transfer_control_file'],
            label='registro de control DDJJ ZIP',
        )

        try:
            ascii_candidate = build_annual_tax_ddjj_ascii_export_candidate(
                export,
                form_code=form_code,
                rut_number=options['rut_number'],
                records=records,
            )
            zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
                ascii_candidate,
                transfer_control_record=transfer_control_record,
            )
            written = write_annual_tax_ddjj_zip_export_candidate(zip_candidate, output_dir)
            verification = verify_annual_tax_ddjj_zip_export_candidate(zip_candidate, output_dir)
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar ZIP candidato DDJJ: {error}') from error

        summary = zip_candidate['summary']
        zip_file_name = str(summary.get('zip_file_name') or '')
        result = {
            'materialized': True,
            'annual_tax_export_id': export.pk,
            'empresa_id': export.empresa_id,
            'proceso_renta_anual_id': export.proceso_renta_anual_id,
            'anio_tributario': export.anio_tributario,
            'anio_comercial': export.anio_comercial,
            'form_code': summary['form_code'],
            'output_dir': str(Path(written['output_dir']).resolve()),
            'manifest_file': Path(written['manifest_file']).name,
            'candidate_version': summary['candidate_version'],
            'source_candidate_version': summary['source_candidate_version'],
            'record_format_version': summary['record_format_version'],
            'zip_file_name_hash': hashlib.sha256(zip_file_name.encode('utf-8')).hexdigest(),
            'zip_file_hash': verification['zip_file_hash'],
            'records_total': verification['records_total'],
            'record_length': verification['record_length'],
            'record_type_counts': verification['record_type_counts'],
            'content_hash': verification['content_hash'],
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'ready_for_responsible_review': True,
            'ready_for_submission': False,
            'requires_official_zip_gate': True,
            'requires_explicit_submission_authorization': True,
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))
