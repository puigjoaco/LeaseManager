import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_mirror_proof import audit_annual_tax_mirror_proof
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
        'Audita la prueba espejo AC/AT como una unica senal: fuentes documentadas, '
        'comparacion contra outputs esperados, readiness Etapa 6 y boundary de seguridad.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', required=True, type=int, help='Empresa destino en DB local/controlada.')
        parser.add_argument('--commercial-year', required=True, type=int, help='Ano comercial fuente.')
        parser.add_argument('--tax-year', required=True, type=int, help='Ano tributario destino.')
        parser.add_argument('--manifest', required=True, help='Ruta al manifiesto annual-tax-source-manifest.v1.')
        parser.add_argument(
            '--source-root',
            default='',
            help='Root externo read-only para extraer senales de outputs esperados. Omitir deja solo cobertura.',
        )
        parser.add_argument('--source-label', required=True, help='Etiqueta no sensible de la fuente auditada.')
        parser.add_argument('--authorization-ref', required=True, help='Referencia no sensible de autorizacion.')
        parser.add_argument('--stage5-evidence-ref', required=True, help='Referencia no sensible a cierres/ledger.')
        parser.add_argument('--stage4-sii-evidence-ref', required=True, help='Referencia no sensible a readiness SII anual.')
        parser.add_argument('--fiscal-rule-ref', required=True, help='Referencia no sensible a regla fiscal validada.')
        parser.add_argument('--certificates-proof-ref', required=True, help='Referencia no sensible a certificados/respaldos.')
        parser.add_argument('--responsible-ref', required=True, help='Referencia no sensible a responsable del frente.')
        parser.add_argument(
            '--source-kind',
            default='snapshot_controlado',
            choices=['snapshot_controlado', 'real_autorizado', 'local', 'fixture', 'demo'],
            help='Tipo de fuente. local/fixture/demo solo diagnostican; snapshot_controlado o real_autorizado prueban cierre controlado.',
        )
        parser.add_argument(
            '--ownership-evidence',
            default='',
            help=(
                'JSON redactado de validate_annual_tax_ownership_patch o '
                'build_annual_tax_ownership_review_checklist para confirmar ownership sin PII.'
            ),
        )
        parser.add_argument(
            '--mirror-run',
            default='',
            help=(
                'JSON redactado de run_annual_tax_controlled_mirror para confirmar que la capa anual '
                'se genero con ownership completo y sin blockers.'
            ),
        )
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de auditoria.')
        parser.add_argument(
            '--fail-on-incomplete',
            action='store_true',
            help='Sale con error si no queda lista la prueba completa fuente+arquitectura+comparacion+readiness.',
        )

    def handle(self, *args, **options):
        manifest_path = _resolve_path(options['manifest'])
        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError('No existe manifest JSON o no es un archivo legible.')
        source_root = _resolve_path(options['source_root']) if options['source_root'] else None
        if source_root is not None and not source_root.is_dir():
            raise CommandError('No existe source-root o no es un directorio legible.')

        output_path = None
        if options['output']:
            output_path = _resolve_path(options['output'])
            _validate_output_path(output_path)

        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError as error:
            raise CommandError(f'Manifest JSON invalido: line {error.lineno}, column {error.colno}.') from error
        except OSError as error:
            raise CommandError('No se pudo leer manifest JSON.') from error
        ownership_evidence = None
        if options['ownership_evidence']:
            ownership_evidence_path = _resolve_path(options['ownership_evidence'])
            if not ownership_evidence_path.exists() or not ownership_evidence_path.is_file():
                raise CommandError('No existe ownership evidence JSON o no es un archivo legible.')
            try:
                ownership_evidence = json.loads(ownership_evidence_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as error:
                raise CommandError(
                    f'Ownership evidence JSON invalida: line {error.lineno}, column {error.colno}.'
                ) from error
            except OSError as error:
                raise CommandError('No se pudo leer ownership evidence JSON.') from error
        mirror_run = None
        if options['mirror_run']:
            mirror_run_path = _resolve_path(options['mirror_run'])
            if not mirror_run_path.exists() or not mirror_run_path.is_file():
                raise CommandError('No existe mirror run JSON o no es un archivo legible.')
            try:
                mirror_run = json.loads(mirror_run_path.read_text(encoding='utf-8'))
            except json.JSONDecodeError as error:
                raise CommandError(
                    f'Mirror run JSON invalido: line {error.lineno}, column {error.colno}.'
                ) from error
            except OSError as error:
                raise CommandError('No se pudo leer mirror run JSON.') from error

        try:
            empresa = Empresa.objects.get(pk=options['empresa_id'])
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe empresa_id={options["empresa_id"]}.') from error

        result = audit_annual_tax_mirror_proof(
            empresa=empresa,
            commercial_year=options['commercial_year'],
            tax_year=options['tax_year'],
            manifest=manifest,
            source_root=source_root,
            stage5_evidence_ref=options['stage5_evidence_ref'],
            stage4_sii_evidence_ref=options['stage4_sii_evidence_ref'],
            fiscal_rule_ref=options['fiscal_rule_ref'],
            certificates_proof_ref=options['certificates_proof_ref'],
            responsible_ref=options['responsible_ref'],
            source_label=options['source_label'],
            authorization_ref=options['authorization_ref'],
            source_kind=options['source_kind'],
            ownership_evidence=ownership_evidence,
            mirror_run=mirror_run,
        )

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
            except OSError as error:
                raise CommandError('No se pudo escribir auditoria de prueba espejo anual.') from error
        else:
            self.stdout.write(rendered)

        if options['fail_on_incomplete'] and not result['summary']['ready_for_objective_completion']:
            blockers = ','.join(result['summary']['blockers'])
            raise CommandError(f'Prueba espejo anual incompleta: blockers={blockers}.')
