import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.company_document_intake import (
    verify_company_document_intake_package,
    write_company_document_intake_package,
)


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
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
            'para no versionar evidencia documental, bancaria, contable o tributaria.'
        ) from error


def _safe_path_component(value) -> str:
    raw_value = str(value or '').strip()
    if re.search(r'\b\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]\b', raw_value) or '://' in raw_value or '@' in raw_value:
        return 'sensitive-ref'
    normalized = raw_value.lower()
    normalized = re.sub(r'[^a-z0-9_.-]+', '-', normalized).strip('-._')
    return normalized or 'sin-ref'


def _default_output_dir(payload: dict) -> Path:
    company_ref = _safe_path_component(payload.get('company_ref'))
    fiscal_year = _safe_path_component(payload.get('fiscal_year'))
    return (
        Path(settings.PROJECT_ROOT).resolve()
        / 'local-evidence'
        / 'stage6'
        / 'company-document-intake'
        / f'{company_ref}-fy{fiscal_year}'
    )


class Command(BaseCommand):
    help = (
        'Materializa un paquete local verificable de intake documental redactado para contabilidad/renta. '
        'No lee adjuntos reales, no abre correos/banco/SII y no habilita contabilidad autonoma.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON redactado company-document-intake-manifest.v1.')
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el intake documental no queda listo para revision productiva responsable.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])
        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f'No existe manifest JSON: {manifest_path}')

        try:
            payload = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise CommandError(f'Manifest invalido: {error}') from error
        if not isinstance(payload, dict):
            raise CommandError('Manifest invalido: la raiz debe ser un objeto JSON.')

        output_dir = _resolve_path(options['output_dir']) if options['output_dir'] else _default_output_dir(payload)
        _validate_output_dir(output_dir)

        try:
            written = write_company_document_intake_package(
                payload=payload,
                output_dir=output_dir,
            )
            verification = verify_company_document_intake_package(
                payload=payload,
                package_dir=output_dir,
            )
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar intake documental: {error}') from error

        result = {
            'materialized': True,
            'schema_version': verification['schema_version'],
            'package_hash': verification['package_hash'],
            'classification': verification['classification'],
            'ready_for_document_intake_review': verification['ready_for_document_intake_review'],
            'ready_for_bank_support_manifest': verification['ready_for_bank_support_manifest'],
            'ready_for_source_manifest_reconciliation': verification['ready_for_source_manifest_reconciliation'],
            'ready_for_productive_document_review': verification['ready_for_productive_document_review'],
            'output_dir': str(output_dir),
            'package_manifest_file': Path(written['package_manifest_file']).name,
            'audit_file': Path(written['audit_file']).name,
            'bank_support_manifest_file': Path(written['bank_support_manifest_file']).name,
            'annual_source_bridge_file': Path(written['annual_source_bridge_file']).name,
            'company_ref': verification['summary']['company_ref'],
            'fiscal_year': verification['summary']['fiscal_year'],
            'tax_year': verification['summary']['tax_year'],
            'documents_total': verification['summary']['documents_total'],
            'source_batches_total': verification['summary']['source_batches_total'],
            'annual_source_documents_total': verification['summary']['annual_source_documents_total'],
            'blocking_issues_total': verification['issue_counts']['blocking'],
            'bank_support_blocking_issues_total': verification['issue_counts']['bank_support_blocking'],
            'warnings_total': verification['issue_counts']['warning'],
            'reads_real_documents': False,
            'stores_real_attachments': False,
            'uses_email_connector': False,
            'opens_bank_gate': False,
            'opens_sii_gate': False,
            'autonomous_accounting': False,
            'final_tax_calculation': False,
            'sii_submission': False,
            'requires_responsible_review': True,
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))

        if options['fail_on_incomplete'] and not result['ready_for_productive_document_review']:
            raise CommandError(
                'Paquete de intake documental incompleto: '
                f'classification={result["classification"]}, '
                f'documents={result["documents_total"]}, '
                f'blocking_issues={result["blocking_issues_total"]}, '
                f'bank_support_blocking={result["bank_support_blocking_issues_total"]}.'
            )
