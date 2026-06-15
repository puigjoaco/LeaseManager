import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_expected_output_comparator import compare_annual_tax_expected_outputs
from patrimonio.models import Empresa


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
        'Compara cobertura/trazabilidad de outputs esperados AC/AT contra artefactos anuales '
        'generados en DB local/controlada; no usa esos outputs como insumos de calculo.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', required=True, type=int, help='Empresa destino en DB local/controlada.')
        parser.add_argument('--commercial-year', required=True, type=int, help='Año comercial fuente.')
        parser.add_argument('--tax-year', required=True, type=int, help='Año tributario destino.')
        parser.add_argument('--manifest', required=True, help='Ruta al manifiesto annual-tax-source-manifest.v1.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de comparacion.')
        parser.add_argument(
            '--fail-on-coverage-mismatch',
            action='store_true',
            help='Sale con error si la cobertura esperada no esta representada por artefactos generados.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])
        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except OSError as error:
            raise CommandError(f'No se pudo leer manifest={manifest_path}: {error}') from error
        except json.JSONDecodeError as error:
            raise CommandError(f'Manifest JSON invalido={manifest_path}: {error}') from error

        try:
            empresa = Empresa.objects.get(pk=options['empresa_id'])
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe empresa_id={options["empresa_id"]}.') from error

        try:
            result = compare_annual_tax_expected_outputs(
                empresa=empresa,
                commercial_year=options['commercial_year'],
                tax_year=options['tax_year'],
                manifest=manifest,
            )
        except ValueError as error:
            raise CommandError(f'Comparacion anual invalida: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding='utf-8')
        else:
            self.stdout.write(rendered)

        if options['fail_on_coverage_mismatch'] and not result['summary']['coverage_ready_for_content_comparison']:
            blockers = ','.join(result['summary']['blockers'])
            raise CommandError(f'Comparacion anual no tiene cobertura completa: blockers={blockers}.')
