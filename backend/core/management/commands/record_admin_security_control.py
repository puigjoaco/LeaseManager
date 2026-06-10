import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.admin_security_control import ADMIN_SECURITY_SETTING_KEY, evaluate_admin_security_control
from core.models import PlatformSetting


class Command(BaseCommand):
    help = 'Registra o actualiza el control administrativo MFA/riesgo para observabilidad productiva.'

    def add_arguments(self, parser):
        parser.add_argument('--mode', required=True, choices=('mfa_enforced', 'risk_accepted'))
        parser.add_argument('--mfa-evidence-ref', default='', help='Referencia no sensible a evidencia MFA.')
        parser.add_argument(
            '--risk-acceptance-ref',
            default='',
            help='Referencia no sensible a la aceptacion formal de riesgo MFA.',
        )
        parser.add_argument(
            '--authorization-ref',
            required=True,
            help='Referencia no sensible a la autorizacion del control administrativo.',
        )
        parser.add_argument(
            '--responsible-ref',
            required=True,
            help='Referencia no sensible al responsable del control administrativo.',
        )
        parser.add_argument('--valid-until', default='', help='Fecha ISO vigente para aceptacion formal de riesgo.')
        parser.add_argument('--description', default='', help='Descripcion operativa no sensible del setting.')

    def handle(self, *args, **options):
        mode = options['mode']
        value = {
            'mode': mode,
            'authorization_ref': options['authorization_ref'],
            'responsible_ref': options['responsible_ref'],
        }
        if mode == 'mfa_enforced':
            value['mfa_enforced'] = True
            value['mfa_evidence_ref'] = options['mfa_evidence_ref']
        if mode == 'risk_accepted':
            value['risk_accepted'] = True
            value['risk_acceptance_ref'] = options['risk_acceptance_ref']
            value['valid_until'] = options['valid_until']

        setting = PlatformSetting.objects.filter(key=ADMIN_SECURITY_SETTING_KEY).first()
        if setting is None:
            setting = PlatformSetting(key=ADMIN_SECURITY_SETTING_KEY)

        setting.value = value
        setting.description = options['description']
        setting.is_active = True

        try:
            setting.full_clean()
        except ValidationError as error:
            raise CommandError(error.message_dict) from error

        setting.save()
        payload, _issues = evaluate_admin_security_control(setting.value, setting_present=True)

        self.stdout.write(
            json.dumps(
                {
                    'setting_key': ADMIN_SECURITY_SETTING_KEY,
                    'mode': mode,
                    'is_active': setting.is_active,
                    'mfa_enforced': payload['mfa_enforced'],
                    'risk_accepted': payload['risk_accepted'],
                    'risk_acceptance_current': payload['risk_acceptance_current'],
                    'valid_until': payload['valid_until'],
                    'authorized_for_stage7_close': payload['authorized_for_stage7_close'],
                    'refs': payload['refs'],
                    'payload_sensitive': payload['payload_sensitive'],
                },
                indent=2,
                ensure_ascii=True,
            )
        )
