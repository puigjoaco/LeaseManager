import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_source_manifest import build_annual_tax_source_manifest


def _resolve_output_path(raw_output_path: str) -> Path:
    output_path = Path(raw_output_path).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
    return output_path.resolve()


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
        'Construye un manifiesto read-only de fuentes AC/AT para preparar '
        'AnnualTaxSourceBundle sin copiar documentos ni ejecutar integraciones.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--source-root', required=True, help='Carpeta externa a inventariar en modo read-only.')
        parser.add_argument('--company-ref', required=True, help='Referencia no sensible de empresa, por ejemplo inmobiliaria-puig.')
        parser.add_argument('--commercial-year', type=int, required=True, help='Ano comercial fuente, por ejemplo 2024.')
        parser.add_argument('--tax-year', type=int, default=None, help='Ano tributario destino. Default: commercial-year + 1.')
        parser.add_argument('--source-label', default='', help='source_label no sensible sugerido para AnnualTaxSourceBundle.')
        parser.add_argument(
            '--authorization-ref',
            default='user-authorized-local-source-review',
            help='authorization_ref no sensible para fuente snapshot/controlada.',
        )
        parser.add_argument(
            '--responsible-ref',
            default='codex-local-review',
            help='responsible_ref no sensible del responsable de revision.',
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON del manifiesto.')
        parser.add_argument(
            '--summary-only',
            action='store_true',
            help='Omite la lista de archivos y deja solo resumen, cobertura y bundle draft.',
        )
        parser.add_argument(
            '--f29-no-declaration-month',
            type=int,
            action='append',
            dest='f29_no_declaration_months',
            default=[],
            help='Mes AC sin F29 por ausencia declarada/registrada. Puede repetirse.',
        )
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si faltan insumos minimos para iniciar la prueba espejo.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = _resolve_output_path(options['output'])
            _validate_output_path(output_path)

        try:
            manifest = build_annual_tax_source_manifest(
                source_root=Path(options['source_root']),
                company_ref=options['company_ref'],
                commercial_year=options['commercial_year'],
                tax_year=options.get('tax_year'),
                source_label=options.get('source_label') or '',
                authorization_ref=options['authorization_ref'],
                responsible_ref=options['responsible_ref'],
                include_file_list=not options['summary_only'],
                f29_no_declaration_months=options['f29_no_declaration_months'],
            )
        except FileNotFoundError as error:
            raise CommandError(str(error)) from error

        rendered = json.dumps(manifest, indent=2, ensure_ascii=True)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not manifest['coverage']['ready_for_mirror_source_bundle']:
            missing = [
                check['key']
                for check in manifest['coverage']['checks']
                if check['key'] in {'rcv_12_months', 'annual_books', 'ddjj_expected_outputs', 'f22_expected_output'}
                and check['status'] != 'ready'
            ]
            raise CommandError(
                'Manifiesto incompleto para prueba espejo: '
                f'missing_or_partial={",".join(missing)}.'
            )
