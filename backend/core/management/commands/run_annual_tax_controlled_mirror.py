import json

from django.core.management.base import BaseCommand, CommandError

from core.annual_tax_controlled_mirror_run import run_annual_tax_controlled_mirror
from core.management.local_evidence_paths import (
    resolve_command_path,
    validate_local_evidence_output_path,
)
from patrimonio.models import Empresa


class Command(BaseCommand):
    help = (
        'Genera la capa anual controlada AC/AT desde MonthlyTaxFact ya cargados; '
        'no usa SII real, credenciales ni salidas finales como input.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--empresa-id', required=True, type=int, help='Empresa destino en DB local/controlada.')
        parser.add_argument('--commercial-year', required=True, type=int, help='Año comercial fuente.')
        parser.add_argument('--tax-year', required=True, type=int, help='Año tributario destino.')
        parser.add_argument('--source-label', required=True, help='Etiqueta no sensible del snapshot controlado.')
        parser.add_argument('--authorization-ref', required=True, help='Referencia no sensible de autorizacion local/controlada.')
        parser.add_argument('--responsible-ref', required=True, help='Responsable no sensible del run controlado.')
        parser.add_argument('--fiscal-rule-ref', required=True, help='Referencia no sensible de regla fiscal revisable.')
        parser.add_argument('--certificates-proof-ref', required=True, help='Referencia no sensible de pruebas/capacidades.')
        parser.add_argument('--ddjj', action='append', dest='ddjj_codes', help='Codigo DDJJ a preparar. Repetible.')
        parser.add_argument('--output', default='', help='Ruta opcional para escribir JSON de resultado.')
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Escribe DB local/controlada. Sin este flag solo valida precondiciones y no escribe.',
        )
        parser.add_argument(
            '--fail-on-blocking',
            action='store_true',
            help='Sale con error si faltan los 12 MonthlyTaxFact normalizados.',
        )

    def handle(self, *args, **options):
        output_path = None
        if options['output']:
            output_path = resolve_command_path(options['output'])
            validate_local_evidence_output_path(output_path)

        try:
            empresa = Empresa.objects.get(pk=options['empresa_id'])
        except Empresa.DoesNotExist as error:
            raise CommandError(f'No existe empresa_id={options["empresa_id"]}.') from error

        try:
            result = run_annual_tax_controlled_mirror(
                empresa=empresa,
                commercial_year=options['commercial_year'],
                tax_year=options['tax_year'],
                source_label=options['source_label'],
                authorization_ref=options['authorization_ref'],
                responsible_ref=options['responsible_ref'],
                fiscal_rule_ref=options['fiscal_rule_ref'],
                certificates_proof_ref=options['certificates_proof_ref'],
                ddjj_codes=tuple(options.get('ddjj_codes') or ()),
                write_database=bool(options['apply']),
            )
        except ValueError as error:
            raise CommandError(f'Run anual controlado invalido: {error}') from error

        rendered = json.dumps(result, indent=2, ensure_ascii=True, default=str)
        if output_path is not None:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered, encoding='utf-8')
            except OSError as error:
                raise CommandError('No se pudo escribir resultado de run anual controlado.') from error
        else:
            self.stdout.write(rendered)

        if options['fail_on_blocking'] and not result['ready_for_generation']:
            blockers = ','.join(result['blockers'])
            raise CommandError(f'Run anual controlado no listo: blockers={blockers}.')
