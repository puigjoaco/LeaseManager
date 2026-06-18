import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.company_bank_support_coverage import audit_company_bank_support_coverage


def _resolve_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _validate_output_path(output_path: Path) -> None:
    repo_root = Path(settings.PROJECT_ROOT).resolve()
    local_evidence_root = (repo_root / 'local-evidence').resolve()

    try:
        output_path.relative_to(repo_root)
    except ValueError:
        return

    try:
        output_path.relative_to(local_evidence_root)
    except ValueError as error:
        raise CommandError(
            'Si --output queda dentro del repo, debe estar bajo local-evidence/ '
            'para no versionar evidencia bancaria, contable o tributaria.'
        ) from error


class Command(BaseCommand):
    help = (
        'Audita cobertura redactada de respaldos bancarios/leasing para revision contable, '
        'sin leer adjuntos reales ni abrir integraciones externas.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON redactado company-bank-support-coverage-manifest.v1.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de auditoria.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el respaldo bancario/leasing no queda listo para revision contable.',
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

        result = audit_company_bank_support_coverage(payload=payload)
        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not result['ready_for_accounting_document_review']:
            raise CommandError(
                'Cobertura bancaria/leasing incompleta: '
                f'classification={result["classification"]}, '
                f'coverage={result["coverage_percent"]}%, '
                f'next={result["next_blocking_operation"]}.'
            )
