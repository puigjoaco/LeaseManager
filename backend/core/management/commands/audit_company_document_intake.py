import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.company_document_intake import audit_company_document_intake
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)


def _resolve_path(raw_path: str) -> Path:
    return resolve_command_path(raw_path)


def _validate_output_path(output_path: Path) -> None:
    validate_local_evidence_output_path(
        output_path,
        artifact_description='evidencia documental, bancaria, contable o tributaria',
    )


class Command(BaseCommand):
    help = (
        'Audita un manifiesto redactado de documentos contables/renta y deriva '
        'cobertura bancaria/leasing y puente anual sin leer adjuntos reales.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON redactado company-document-intake-manifest.v1.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de auditoria.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el intake documental no queda listo para revision productiva responsable.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])
        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f'No existe manifest JSON: {manifest_path}')

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            payload = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            raise CommandError(f'Manifest invalido: {error}') from error
        if not isinstance(payload, dict):
            raise CommandError('Manifest invalido: la raiz debe ser un objeto JSON.')

        result = audit_company_document_intake(payload=payload)
        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not result['ready_for_productive_document_review']:
            raise CommandError(
                'Intake documental contable/renta incompleto: '
                f'classification={result["classification"]}, '
                f'bank_ready={result["ready_for_bank_support_manifest"]}, '
                f'formal_bank_ready={result["ready_for_formal_bank_support_manifest"]}, '
                f'annual_bridge_ready={result["ready_for_source_manifest_reconciliation"]}.'
            )
