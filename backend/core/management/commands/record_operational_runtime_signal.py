import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import (
    OperationalRuntimeSignal,
    RuntimeSignalKey,
    RuntimeSignalSourceKind,
    RuntimeSignalStatus,
)


class Command(BaseCommand):
    help = 'Registra o actualiza una senal runtime de observabilidad operativa.'

    def add_arguments(self, parser):
        parser.add_argument('--signal-key', required=True, choices=RuntimeSignalKey.values)
        parser.add_argument('--status', required=True, choices=RuntimeSignalStatus.values)
        parser.add_argument('--source-kind', default=RuntimeSignalSourceKind.LOCAL, choices=RuntimeSignalSourceKind.values)
        parser.add_argument('--evidence-ref', default='', help='Referencia trazable no sensible de la medicion.')
        parser.add_argument('--value-json', default='{}', help='Payload JSON no sensible con el resultado observado.')
        parser.add_argument('--notes', default='', help='Nota operativa no sensible.')

    def handle(self, *args, **options):
        try:
            value = json.loads(options['value_json'])
        except json.JSONDecodeError as error:
            raise CommandError('--value-json debe ser JSON valido.') from error

        if not isinstance(value, dict):
            raise CommandError('--value-json debe ser un objeto JSON.')

        signal = OperationalRuntimeSignal.objects.filter(signal_key=options['signal_key']).first()
        if signal is None:
            signal = OperationalRuntimeSignal(signal_key=options['signal_key'])
        signal.status = options['status']
        signal.source_kind = options['source_kind']
        signal.value = value
        signal.evidence_ref = options['evidence_ref']
        signal.notes = options['notes']
        signal.observed_at = timezone.now()
        try:
            signal.full_clean()
        except ValidationError as error:
            raise CommandError(error.message_dict) from error
        signal.save()

        self.stdout.write(
            json.dumps(
                {
                    'signal_key': signal.signal_key,
                    'status': signal.status,
                    'source_kind': signal.source_kind,
                    'observed_at': signal.observed_at.isoformat(),
                    'evidence_ref': signal.evidence_ref,
                    'value': signal.value,
                },
                indent=2,
                ensure_ascii=True,
            )
        )
