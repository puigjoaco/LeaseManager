import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from sii.services import (
    verify_annual_tax_sii_certification_readiness_packet,
    write_annual_tax_sii_certification_readiness_packet,
)


def _resolve_dir(raw_dir: str) -> Path:
    path = Path(raw_dir).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


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
            'para no versionar paquetes de certificacion tributaria.'
        ) from error


def _default_output_dir(controlled_package_dir: Path) -> Path:
    manifest_path = controlled_package_dir / 'annual-tax-controlled-presentation-package.json'
    try:
        manifest_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        suffix = controlled_package_dir.name
    else:
        package_hash = str((manifest_payload.get('summary') or {}).get('package_hash') or '')
        suffix = package_hash[:12] if package_hash else controlled_package_dir.name
    return (
        Path(settings.PROJECT_ROOT).resolve()
        / 'local-evidence'
        / 'stage6'
        / 'sii-certification-readiness'
        / suffix
    )


def _require_non_sensitive_reference(value, field_name: str) -> str:
    normalized = str(value or '').strip()
    if not normalized or not is_non_sensitive_reference(normalized):
        raise CommandError(f'{field_name} debe ser una referencia trazable no sensible.')
    return normalized


def _optional_non_sensitive_reference(value, field_name: str) -> str:
    normalized = str(value or '').strip()
    if normalized and not is_non_sensitive_reference(normalized):
        raise CommandError(f'{field_name} debe ser una referencia trazable no sensible.')
    return normalized


def _validate_non_sensitive_text(value, field_name: str) -> str:
    normalized = str(value or '').strip()
    if normalized and contains_sensitive_reference(normalized):
        raise CommandError(f'{field_name} no debe contener URLs, tokens, credenciales ni correos.')
    return normalized


class Command(BaseCommand):
    help = (
        'Materializa un readiness packet de certificacion/presentacion SII a partir de un '
        'paquete anual controlado. No habilita envio SII, formato oficial ni calculo final.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--controlled-package-dir',
            required=True,
            help='Directorio que contiene annual-tax-controlled-presentation-package.json.',
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--certification-review-ref',
            required=True,
            help='Referencia no sensible de la revision de readiness/certificacion.',
        )
        parser.add_argument(
            '--responsible-ref',
            required=True,
            help='Referencia no sensible del responsable de la revision de certificacion.',
        )
        parser.add_argument(
            '--official-format-authorization-ref',
            default='',
            help='Referencia no sensible del formato/certificacion oficial aplicable, si existe.',
        )
        parser.add_argument(
            '--f22-certification-authorization-ref',
            default='',
            help='Referencia no sensible de certificacion/autorizacion F22, si existe.',
        )
        parser.add_argument(
            '--ddjj-certification-authorization-ref',
            default='',
            help='Referencia no sensible de certificacion/upload DDJJ, si existe.',
        )
        parser.add_argument(
            '--sii-environment-ref',
            default='',
            help='Referencia no sensible del ambiente SII autenticado/supervisado, si existe.',
        )
        parser.add_argument(
            '--submission-authorization-ref',
            default='',
            help='Referencia no sensible de autorizacion explicita de presentacion, si existe.',
        )
        parser.add_argument(
            '--responsible-tax-signoff-ref',
            default='',
            help='Referencia no sensible de visto bueno tributario responsable, si existe.',
        )
        parser.add_argument(
            '--rollback-plan-ref',
            default='',
            help='Referencia no sensible del plan de rollback/rectificacion, si existe.',
        )
        parser.add_argument(
            '--evidence-archive-ref',
            default='',
            help='Referencia no sensible del archivo de evidencia, si existe.',
        )
        parser.add_argument(
            '--packet-note',
            default='',
            help='Nota no sensible para el readiness packet.',
        )

    def handle(self, *args, **options):
        controlled_package_dir = _resolve_dir(options['controlled_package_dir'])
        certification_review_ref = _require_non_sensitive_reference(
            options['certification_review_ref'],
            'certification_review_ref',
        )
        responsible_ref = _require_non_sensitive_reference(options['responsible_ref'], 'responsible_ref')
        optional_refs = {
            'official_format_authorization_ref': _optional_non_sensitive_reference(
                options['official_format_authorization_ref'],
                'official_format_authorization_ref',
            ),
            'f22_certification_authorization_ref': _optional_non_sensitive_reference(
                options['f22_certification_authorization_ref'],
                'f22_certification_authorization_ref',
            ),
            'ddjj_certification_authorization_ref': _optional_non_sensitive_reference(
                options['ddjj_certification_authorization_ref'],
                'ddjj_certification_authorization_ref',
            ),
            'sii_environment_ref': _optional_non_sensitive_reference(
                options['sii_environment_ref'],
                'sii_environment_ref',
            ),
            'submission_authorization_ref': _optional_non_sensitive_reference(
                options['submission_authorization_ref'],
                'submission_authorization_ref',
            ),
            'responsible_tax_signoff_ref': _optional_non_sensitive_reference(
                options['responsible_tax_signoff_ref'],
                'responsible_tax_signoff_ref',
            ),
            'rollback_plan_ref': _optional_non_sensitive_reference(
                options['rollback_plan_ref'],
                'rollback_plan_ref',
            ),
            'evidence_archive_ref': _optional_non_sensitive_reference(
                options['evidence_archive_ref'],
                'evidence_archive_ref',
            ),
        }
        packet_note = _validate_non_sensitive_text(options['packet_note'], 'packet_note')
        output_dir = (
            _resolve_dir(options['output_dir'])
            if options['output_dir']
            else _default_output_dir(controlled_package_dir).resolve()
        )
        _validate_output_dir(output_dir)

        try:
            written = write_annual_tax_sii_certification_readiness_packet(
                controlled_package_dir,
                output_dir,
                certification_review_ref=certification_review_ref,
                responsible_ref=responsible_ref,
                packet_note=packet_note,
                **optional_refs,
            )
            verification = verify_annual_tax_sii_certification_readiness_packet(
                controlled_package_dir,
                output_dir,
                certification_review_ref=certification_review_ref,
                responsible_ref=responsible_ref,
                packet_note=packet_note,
                **optional_refs,
            )
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar readiness de certificacion SII: {error}') from error

        result = {
            'materialized': True,
            'packet_version': verification['packet_version'],
            'packet_hash': verification['packet_hash'],
            'controlled_package_hash': verification['controlled_package_hash'],
            'classification': verification['classification'],
            'output_dir': str(output_dir),
            'manifest_file': Path(written['manifest_file']).name,
            'external_requirements_total': verification['external_requirements_total'],
            'external_requirements_provided_total': verification['external_requirements_provided_total'],
            'missing_external_gate_keys': verification['missing_external_gate_keys'],
            'ready_for_external_certification_review': verification[
                'ready_for_external_certification_review'
            ],
            'ready_for_sii_submission': False,
            'official_format': False,
            'official_submission_allowed': False,
            'sii_submission': False,
            'sii_submission_attempted': False,
            'final_tax_calculation': False,
            'requires_external_sii_certification': True,
            'requires_explicit_submission_authorization': True,
            'requires_manual_sii_step': True,
            'certification_review_ref_hash': hashlib.sha256(
                certification_review_ref.encode('utf-8')
            ).hexdigest(),
            'responsible_ref_hash': hashlib.sha256(responsible_ref.encode('utf-8')).hexdigest(),
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))
