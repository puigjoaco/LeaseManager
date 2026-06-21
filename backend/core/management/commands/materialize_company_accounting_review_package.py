import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError, ProgrammingError

from core.company_accounting_review_package import (
    verify_company_accounting_review_package,
    write_company_accounting_review_package,
)
from core.company_document_intake import verify_company_document_intake_package_from_disk
from patrimonio.models import Empresa


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
            'para no versionar evidencia bancaria, contable o tributaria.'
        ) from error


def _default_output_dir(*, empresa_id: int, fiscal_year: int) -> Path:
    return (
        Path(settings.PROJECT_ROOT).resolve()
        / 'local-evidence'
        / 'stage6'
        / 'company-accounting-review-package'
        / f'company-{int(empresa_id)}-fy{int(fiscal_year)}'
    )


class Command(BaseCommand):
    help = (
        'Materializa un paquete local verificable de revision contable/renta por empresa y ano. '
        'No lee adjuntos reales, no abre banco/SII y no habilita contabilidad autonoma.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', type=int, required=True, help='ID interno de Empresa a auditar.')
        parser.add_argument('--fiscal-year', type=int, required=True, help='Ano comercial a auditar.')
        parser.add_argument(
            '--bank-support-manifest',
            default='',
            help='JSON redactado company-bank-support-coverage-manifest.v1.',
        )
        parser.add_argument(
            '--document-intake-package-dir',
            default='',
            help=(
                'Directorio materializado por materialize_company_document_intake. '
                'Si se usa, el manifiesto bancario/leasing se toma del paquete verificado.'
            ),
        )
        parser.add_argument(
            '--output-dir',
            default='',
            help='Directorio destino. Si queda dentro del repo debe estar bajo local-evidence/.',
        )
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si el paquete no queda listo para revision productiva responsable.',
        )

    def handle(self, *args, **options):
        if bool(options['bank_support_manifest']) == bool(options['document_intake_package_dir']):
            raise CommandError(
                'Debe indicar exactamente una fuente: --bank-support-manifest o --document-intake-package-dir.'
            )

        output_dir = (
            _resolve_path(options['output_dir'])
            if options['output_dir']
            else _default_output_dir(
                empresa_id=options['empresa_id'],
                fiscal_year=options['fiscal_year'],
            )
        )
        _validate_output_dir(output_dir)

        intake_package = None
        if options['document_intake_package_dir']:
            intake_dir = _resolve_path(options['document_intake_package_dir'])
            try:
                intake_package = verify_company_document_intake_package_from_disk(package_dir=intake_dir)
            except ValueError as error:
                raise CommandError(f'Paquete de intake documental invalido: {error}') from error
            bank_support_payload = intake_package['bank_support_manifest']
        else:
            manifest_path = _resolve_path(options['bank_support_manifest'])
            if not manifest_path.exists() or not manifest_path.is_file():
                raise CommandError('No existe manifest JSON o no es un archivo legible.')
            try:
                bank_support_payload = json.loads(manifest_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as error:
                raise CommandError(f'Manifest JSON invalido: line {error.lineno}, column {error.colno}.') from error
            except OSError as error:
                raise CommandError('No se pudo leer manifest JSON.') from error
            if not isinstance(bank_support_payload, dict):
                raise CommandError('Manifest invalido: la raiz debe ser un objeto JSON.')

        try:
            written = write_company_accounting_review_package(
                empresa_id=options['empresa_id'],
                fiscal_year=options['fiscal_year'],
                bank_support_payload=bank_support_payload,
                document_intake_package=intake_package,
                output_dir=output_dir,
            )
            verification = verify_company_accounting_review_package(
                empresa_id=options['empresa_id'],
                fiscal_year=options['fiscal_year'],
                bank_support_payload=bank_support_payload,
                document_intake_package=intake_package,
                package_dir=output_dir,
            )
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe Empresa con id={options["empresa_id"]}.') from error
        except ValueError as error:
            raise CommandError(f'No se pudo materializar/verificar paquete contable/renta: {error}') from error
        except OSError as error:
            raise CommandError('No se pudo escribir/verificar paquete contable/renta.') from error
        except (OperationalError, ProgrammingError) as error:
            raise CommandError(
                'No se pudo materializar paquete contable/renta porque la base configurada no esta migrada o no es accesible.'
            ) from error

        result = {
            'materialized': True,
            'schema_version': verification['schema_version'],
            'package_hash': verification['package_hash'],
            'classification': verification['classification'],
            'ready_for_productive_accounting_review': verification[
                'ready_for_productive_accounting_review'
            ],
            'output_dir': str(output_dir),
            'manifest_file': Path(written['manifest_file']).name,
            'empresa_id': verification['summary']['empresa_id'],
            'fiscal_year': verification['summary']['fiscal_year'],
            'tax_year': verification['summary']['tax_year'],
            'expected_company_ref': verification['summary']['expected_company_ref'],
            'bank_support_company_ref': verification['summary']['bank_support_company_ref'],
            'accounting_progress_percent': verification['summary']['accounting_progress_percent'],
            'bank_support_coverage_percent': verification['summary']['bank_support_coverage_percent'],
            'issues_total': verification['issues_total'],
            'warnings_total': verification['warnings_total'],
            'source_kind': 'document_intake_package' if intake_package else 'bank_support_manifest',
            'document_intake_package_hash': intake_package['package_hash'] if intake_package else '',
            'document_intake_ready_for_productive_review': verification['summary'][
                'document_intake_ready_for_productive_review'
            ],
            'document_intake_ready_for_formal_bank_support_manifest': verification['summary'][
                'document_intake_ready_for_formal_bank_support_manifest'
            ],
            'autonomous_accounting': False,
            'final_tax_calculation': False,
            'sii_submission': False,
            'requires_responsible_review': True,
            'requires_expert_or_official_validation': True,
        }
        self.stdout.write(json.dumps(result, indent=2, ensure_ascii=True, default=str))

        if options['fail_on_incomplete'] and not result['ready_for_productive_accounting_review']:
            raise CommandError(
                'Paquete de revision contable/renta incompleto: '
                f'classification={result["classification"]}, '
                f'accounting_progress={result["accounting_progress_percent"]}, '
                f'bank_support={result["bank_support_coverage_percent"]}.'
            )
