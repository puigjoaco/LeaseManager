import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_values_draft import (
    build_annual_tax_controlled_values_draft,
    load_values_draft_json,
)


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
            'para no versionar evidencia contable o tributaria.'
        ) from error


class Command(BaseCommand):
    help = (
        'Construye un draft de valores para el paquete controlado AC/AT desde fuentes permitidas; '
        'no escribe DB, no copia documentos y no usa Balance/RLI/CPT/RAI/DDJJ/F22 como input.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--manifest', required=True, help='JSON de build_annual_tax_source_manifest.')
        parser.add_argument('--template', required=True, help='JSON de build_annual_tax_controlled_db_load_template.')
        parser.add_argument('--source-root', required=True, help='Root externo read-only correspondiente al manifiesto.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON del draft.')
        parser.add_argument('--responsible-ref', default='', help='Referencia no sensible de responsable.')
        parser.add_argument('--approval-ref', default='', help='Referencia no sensible de autorizacion/aprobacion.')
        parser.add_argument(
            '--fail-on-extraction-error',
            action='store_true',
            help='Sale con error si alguna extraccion permitida falla.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])
        template_path = _resolve_path(options['template'])
        source_root = _resolve_path(options['source_root'])
        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f'No existe manifest JSON: {manifest_path}')
        if not template_path.exists() or not template_path.is_file():
            raise CommandError(f'No existe template JSON: {template_path}')
        if not source_root.exists() or not source_root.is_dir():
            raise CommandError(f'No existe source-root: {source_root}')

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            manifest = load_values_draft_json(manifest_path.read_text(encoding='utf-8'))
            template = load_values_draft_json(template_path.read_text(encoding='utf-8'))
            result = build_annual_tax_controlled_values_draft(
                manifest=manifest,
                template=template,
                source_root=source_root,
                responsible_ref=options['responsible_ref'],
                approval_ref=options['approval_ref'],
            )
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CommandError(f'Draft de valores invalido: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        errors = result.get('values_draft_summary', {}).get('extraction_errors') or []
        if options['fail_on_extraction_error'] and errors:
            raise CommandError(f'Extraccion controlada con errores: {len(errors)}.')
