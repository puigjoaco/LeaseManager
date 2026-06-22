import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.reference_validation import (
    contains_chilean_rut_reference,
    contains_local_absolute_path_reference,
    contains_sensitive_reference,
    is_non_sensitive_reference,
)
from sii.models import (
    AnnualTaxArtifactMatrixItem,
    AnnualTaxExport,
    AnnualTaxReviewChecklist,
    EstadoRegistro,
    EstadoAnnualTaxReviewChecklist,
    EstadoAnnualTaxReviewDecision,
    SourceKindAnnualTaxArtifact,
    TipoAnnualTaxArtifactTarget,
)
from sii.services import (
    build_annual_tax_ddjj_ascii_export_candidate,
    build_annual_tax_ddjj_zip_export_candidate,
    build_annual_tax_f22_fixed_width_export_candidate,
    build_f22_fixed_width_entries_from_artifact_matrix,
    verify_annual_tax_ddjj_ascii_export_candidate,
    verify_annual_tax_ddjj_zip_export_candidate,
    verify_annual_tax_export_file_package,
    verify_annual_tax_f22_fixed_width_export_candidate,
    verify_annual_tax_controlled_presentation_package,
    verify_annual_tax_presentation_review_bundle,
    write_annual_tax_ddjj_ascii_export_candidate,
    write_annual_tax_ddjj_zip_export_candidate,
    write_annual_tax_export_file_package,
    write_annual_tax_f22_fixed_width_export_candidate,
    write_annual_tax_controlled_presentation_package,
    write_annual_tax_presentation_review_bundle,
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
        / 'controlled-presentation-packages'
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
            'para no versionar paquetes tributarios de presentacion.'
        ) from error


def _prepare_output_root(output_dir: Path) -> Path:
    _validate_output_dir(output_dir)
    if output_dir.exists() and not output_dir.is_dir():
        raise CommandError('El destino del paquete controlado debe ser un directorio.')
    if output_dir.exists() and any(output_dir.iterdir()):
        raise CommandError(
            'El directorio destino del paquete controlado debe estar vacio antes de materializar artefactos.'
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


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


def _normalize_form_code(value) -> str:
    return str(value or '').strip()


def _ddjj_input_for_form(ddjj_inputs, form_code: str):
    if not isinstance(ddjj_inputs, dict):
        raise CommandError('ddjj-inputs debe ser un objeto JSON indexado por codigo de formulario.')
    entry = ddjj_inputs.get(form_code)
    if not isinstance(entry, dict):
        raise CommandError(f'Falta entrada DDJJ para formulario {form_code}.')
    records = entry.get('records')
    transfer_control_record = entry.get('transfer_control_record')
    if not isinstance(records, list):
        raise CommandError(f'La entrada DDJJ {form_code} requiere records como lista.')
    if not isinstance(transfer_control_record, dict):
        raise CommandError(f'La entrada DDJJ {form_code} requiere transfer_control_record como objeto.')
    return records, transfer_control_record


def _require_non_sensitive_reference(value, field_name: str) -> str:
    normalized = str(value or '').strip()
    if (
        not normalized
        or not is_non_sensitive_reference(normalized)
        or contains_chilean_rut_reference(normalized)
        or contains_local_absolute_path_reference(normalized)
    ):
        raise CommandError(f'{field_name} debe ser una referencia trazable no sensible.')
    return normalized


def _validate_non_sensitive_text(value, field_name: str) -> str:
    normalized = str(value or '').strip()
    if normalized and (
        contains_sensitive_reference(normalized)
        or contains_chilean_rut_reference(normalized)
        or contains_local_absolute_path_reference(normalized)
    ):
        raise CommandError(f'{field_name} no debe contener URLs, tokens, credenciales, correos, RUTs ni rutas locales.')
    return normalized


class Command(BaseCommand):
    help = (
        'Materializa en una sola corrida el paquete local de presentacion controlada: '
        'AnnualTaxExport, candidato F22, candidatos DDJJ ASCII/ZIP y bundle verificable. '
        'No declara formato oficial, no presenta SII y no calcula renta final.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--export-id', required=True, type=int, help='ID del AnnualTaxExport preparado.')
        parser.add_argument('--rut-number', required=True, help='RUT declarante sin DV, usado solo en archivos locales.')
        parser.add_argument('--rut-dv', required=True, help='DV del RUT declarante, usado solo en archivo F22 local.')
        parser.add_argument('--company-code', required=True, help='Codigo empresa/certificacion F22; no se imprime crudo.')
        parser.add_argument('--client-number', required=True, help='Numero cliente/certificacion F22; no se imprime crudo.')
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
            '--ddjj-inputs-json',
            default='',
            help=(
                'Objeto JSON por formulario DDJJ. Ejemplo: '
                '{"1887":{"records":[...],"transfer_control_record":{...}}}.'
            ),
        )
        parser.add_argument(
            '--ddjj-inputs-file',
            default='',
            help='Archivo JSON con entradas DDJJ por formulario.',
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio raiz destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--handoff-authorization-ref',
            required=True,
            help='Referencia no sensible que autoriza preparar el paquete de entrega controlada.',
        )
        parser.add_argument(
            '--responsible-ref',
            required=True,
            help='Referencia no sensible del responsable de la entrega controlada.',
        )
        parser.add_argument(
            '--presentation-window-ref',
            required=True,
            help='Referencia no sensible de la ventana o instancia de presentacion controlada.',
        )
        parser.add_argument(
            '--package-note',
            default='',
            help='Nota no sensible para el handoff del paquete controlado.',
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

        handoff_authorization_ref = _require_non_sensitive_reference(
            options['handoff_authorization_ref'],
            'handoff_authorization_ref',
        )
        responsible_ref = _require_non_sensitive_reference(options['responsible_ref'], 'responsible_ref')
        presentation_window_ref = _require_non_sensitive_reference(
            options['presentation_window_ref'],
            'presentation_window_ref',
        )
        package_note = _validate_non_sensitive_text(options['package_note'], 'package_note')
        try:
            checklist = AnnualTaxReviewChecklist.objects.get(
                annual_export=export,
                estado=EstadoAnnualTaxReviewChecklist.PREPARED,
            )
        except AnnualTaxReviewChecklist.DoesNotExist as error:
            raise CommandError(
                'El paquete controlado requiere AnnualTaxReviewChecklist preparado.'
            ) from error
        if checklist.review_decision_state != EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION:
            raise CommandError(
                'El paquete controlado requiere checklist anual aprobado para presentacion controlada.'
            )

        output_root = (
            _resolve_output_dir(options['output_dir'])
            if options['output_dir']
            else _default_output_dir(export).resolve()
        )
        ddjj_inputs = _load_json_option(
            inline_json=options['ddjj_inputs_json'],
            json_file=options['ddjj_inputs_file'],
            label='ddjj-inputs',
        )
        expected_forms = []
        expected_ddjj_layout_items = AnnualTaxArtifactMatrixItem.objects.filter(
            matrix=export.artifact_matrix,
            estado=EstadoRegistro.ACTIVE,
            target_kind=TipoAnnualTaxArtifactTarget.DDJJ,
            source_kind=SourceKindAnnualTaxArtifact.DDJJ_LAYOUT,
            source_model='AnnualTaxDDJJFormLayout',
        ).order_by('target_code', 'id')
        for item in expected_ddjj_layout_items:
            target_code = str(item.target_code or '').strip().upper()
            if target_code.startswith('DDJJ-'):
                expected_forms.append(_normalize_form_code(target_code[5:]))
        expected_forms = sorted(set(form_code for form_code in expected_forms if form_code))
        if not expected_forms:
            raise CommandError('El paquete controlado requiere al menos un formulario DDJJ esperado.')
        ddjj_inputs_by_form = {
            form_code: _ddjj_input_for_form(ddjj_inputs, form_code)
            for form_code in expected_forms
        }
        _prepare_output_root(output_root)

        try:
            export_package_dir = output_root / 'annual-tax-export-package'
            export_written = write_annual_tax_export_file_package(export, export_package_dir)
            export_verification = verify_annual_tax_export_file_package(export, export_package_dir)

            f22_dir = output_root / 'f22-fixed-width-candidate'
            f22_entries = build_f22_fixed_width_entries_from_artifact_matrix(export)
            f22_candidate = build_annual_tax_f22_fixed_width_export_candidate(
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
                entries=f22_entries,
            )
            f22_written = write_annual_tax_f22_fixed_width_export_candidate(f22_candidate, f22_dir)
            f22_verification = verify_annual_tax_f22_fixed_width_export_candidate(f22_candidate, f22_dir)

            ddjj_ascii_dirs = []
            ddjj_zip_dirs = []
            ddjj_results = []

            for form_code in expected_forms:
                records, transfer_control_record = ddjj_inputs_by_form[form_code]
                ascii_candidate = build_annual_tax_ddjj_ascii_export_candidate(
                    export,
                    form_code=form_code,
                    rut_number=options['rut_number'],
                    records=records,
                )
                ascii_dir = output_root / f'ddjj-{form_code}-ascii-candidate'
                ascii_written = write_annual_tax_ddjj_ascii_export_candidate(ascii_candidate, ascii_dir)
                ascii_verification = verify_annual_tax_ddjj_ascii_export_candidate(ascii_candidate, ascii_dir)
                zip_candidate = build_annual_tax_ddjj_zip_export_candidate(
                    ascii_candidate,
                    transfer_control_record=transfer_control_record,
                )
                zip_dir = output_root / f'ddjj-{form_code}-zip-candidate'
                zip_written = write_annual_tax_ddjj_zip_export_candidate(zip_candidate, zip_dir)
                zip_verification = verify_annual_tax_ddjj_zip_export_candidate(zip_candidate, zip_dir)
                ddjj_ascii_dirs.append(ascii_dir)
                ddjj_zip_dirs.append(zip_dir)
                ddjj_results.append(
                    {
                        'form_code': form_code,
                        'ascii_dir': ascii_dir.name,
                        'ascii_manifest_file': Path(ascii_written['manifest_file']).name,
                        'ascii_content_hash': ascii_verification['content_hash'],
                        'zip_dir': zip_dir.name,
                        'zip_manifest_file': Path(zip_written['manifest_file']).name,
                        'zip_file_hash': zip_verification['zip_file_hash'],
                        'records_total': zip_verification['records_total'],
                    }
                )

            bundle_dir = output_root / 'presentation-review-bundle'
            bundle_written = write_annual_tax_presentation_review_bundle(
                export,
                bundle_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_dir,
                ddjj_ascii_candidate_dirs=ddjj_ascii_dirs,
                ddjj_zip_candidate_dirs=ddjj_zip_dirs,
            )
            bundle_verification = verify_annual_tax_presentation_review_bundle(
                export,
                bundle_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_dir,
                ddjj_ascii_candidate_dirs=ddjj_ascii_dirs,
                ddjj_zip_candidate_dirs=ddjj_zip_dirs,
            )
            controlled_package_dir = output_root / 'controlled-presentation-handoff'
            controlled_written = write_annual_tax_controlled_presentation_package(
                export,
                controlled_package_dir,
                presentation_review_bundle_dir=bundle_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_dir,
                ddjj_ascii_candidate_dirs=ddjj_ascii_dirs,
                ddjj_zip_candidate_dirs=ddjj_zip_dirs,
                handoff_authorization_ref=handoff_authorization_ref,
                responsible_ref=responsible_ref,
                presentation_window_ref=presentation_window_ref,
                package_note=package_note,
            )
            controlled_verification = verify_annual_tax_controlled_presentation_package(
                export,
                controlled_package_dir,
                presentation_review_bundle_dir=bundle_dir,
                export_package_dir=export_package_dir,
                f22_candidate_dir=f22_dir,
                ddjj_ascii_candidate_dirs=ddjj_ascii_dirs,
                ddjj_zip_candidate_dirs=ddjj_zip_dirs,
                handoff_authorization_ref=handoff_authorization_ref,
                responsible_ref=responsible_ref,
                presentation_window_ref=presentation_window_ref,
                package_note=package_note,
            )
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar paquete controlado: {error}') from error

        f22_summary = f22_candidate['summary']
        certification_evidence = f22_summary['certification_code_evidence']
        result = {
            'materialized': True,
            'annual_tax_export_id': export.pk,
            'empresa_id': export.empresa_id,
            'proceso_renta_anual_id': export.proceso_renta_anual_id,
            'anio_tributario': export.anio_tributario,
            'anio_comercial': export.anio_comercial,
            'output_dir': str(output_root),
            'export_package_dir': Path(export_written['output_dir']).name,
            'export_package_hash': export_verification['package_hash'],
            'f22_candidate_dir': Path(f22_written['output_dir']).name,
            'f22_content_hash': f22_verification['content_hash'],
            'f22_codes_total': f22_verification['f22_codes_total'],
            'f22_certification_code_review_state': f22_verification['certification_code_review_state'],
            'f22_certification_code_authorized_by_sii': f22_verification['certification_code_authorized_by_sii'],
            'f22_certification_code_evidence_hash': f22_summary['certification_code_evidence_hash'],
            'company_code_hash': certification_evidence['company_code_hash'],
            'client_number_hash': certification_evidence['client_number_hash'],
            'ddjj_forms': [item['form_code'] for item in ddjj_results],
            'ddjj_results': ddjj_results,
            'presentation_bundle_dir': Path(bundle_written['output_dir']).name,
            'presentation_bundle_manifest_file': Path(bundle_written['manifest_file']).name,
            'presentation_bundle_hash': bundle_verification['bundle_hash'],
            'controlled_package_dir': Path(controlled_written['output_dir']).name,
            'controlled_package_manifest_file': Path(controlled_written['manifest_file']).name,
            'controlled_package_hash': controlled_verification['package_hash'],
            'classification': controlled_verification['classification'],
            'artifact_coverage_ready': bundle_verification['artifact_coverage_ready'],
            'artifact_coverage_issue_codes': bundle_verification['artifact_coverage_issue_codes'],
            'official_compatibility_ready': bundle_verification['official_compatibility_ready'],
            'official_compatibility_issue_codes': bundle_verification['official_compatibility_issue_codes'],
            'ready_for_controlled_presentation_review': controlled_verification['ready_for_controlled_presentation_review'],
            'ready_for_controlled_presentation_package': controlled_verification['ready_for_controlled_presentation_package'],
            'official_format': False,
            'sii_submission': False,
            'sii_submission_attempted': False,
            'final_tax_calculation': False,
            'ready_for_sii_submission': False,
            'package_summary_hash': hashlib.sha256(
                json.dumps(
                    {
                        'annual_tax_export_id': export.pk,
                        'export_package_hash': export_verification['package_hash'],
                        'f22_content_hash': f22_verification['content_hash'],
                        'ddjj_results': ddjj_results,
                        'presentation_bundle_hash': bundle_verification['bundle_hash'],
                    },
                    sort_keys=True,
                    separators=(',', ':'),
                    ensure_ascii=True,
                    default=str,
                ).encode('utf-8')
            ).hexdigest(),
            'requires_official_format_gate': True,
            'requires_explicit_submission_authorization': True,
            'requires_manual_sii_step': True,
            'requires_responsible_review': controlled_verification['requires_responsible_review'],
            'handoff_authorization_ref_hash': controlled_verification['handoff_authorization_ref_hash'],
            'responsible_ref_hash': controlled_verification['responsible_ref_hash'],
            'presentation_window_ref_hash': controlled_verification['presentation_window_ref_hash'],
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))
