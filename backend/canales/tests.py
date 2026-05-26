from datetime import date, datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent, ManualResolution
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from cobranza.models import PagoMensual
from documentos.models import DocumentoEmitido, EstadoDocumento, ExpedienteDocumental
from operacion.models import (
    AsignacionCanalOperacion,
    CuentaRecaudadora,
    EstadoCuentaRecaudadora,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
)
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import (
    CanalMensajeria,
    ConfiguracionNotificacionContrato,
    EstadoGateCanal,
    EstadoMensajeSaliente,
    MensajeSaliente,
    NotificacionCobranzaProgramada,
)
from .services import mark_message_as_sent, materialize_payment_notification_schedule


VALID_DOCUMENT_SHA256 = 'c' * 64


class CanalesAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='channels',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='ChannelCo', rut='88888888-8', socio_ruts=('11111111-1', '22222222-2')):
        socio_1 = self._create_socio(f'{nombre} Socio 1', socio_ruts[0])
        socio_2 = self._create_socio(f'{nombre} Socio 2', socio_ruts[1])
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        return empresa

    def _create_contract_context(
        self,
        codigo='CH-001',
        whatsapp_blocked=False,
        *,
        empresa_rut='88888888-8',
        propietario_rut='33333333-3',
        arrendatario_rut='44444444-4',
        socio_ruts=('11111111-1', '22222222-2'),
        whatsapp_opt_in=False,
        whatsapp_opt_in_evidencia_ref='',
    ):
        empresa = self._create_active_empresa(nombre=f'Empresa {codigo}', rut=empresa_rut, socio_ruts=socio_ruts)
        propietario = self._create_socio(f'Prop {codigo}', propietario_rut)
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo}',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=f'PROP-{codigo}'[:16],
            estado='activa',
            socio_owner=propietario,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_socio_owner=propietario,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut=arrendatario_rut,
            email='tenant@example.com',
            telefono='+56912345678',
            domicilio_notificaciones='Dir 123',
            estado_contacto='activo',
            whatsapp_opt_in=whatsapp_opt_in,
            whatsapp_opt_in_evidencia_ref=whatsapp_opt_in_evidencia_ref,
            whatsapp_bloqueado=whatsapp_blocked,
        )
        contrato = Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        return empresa, contrato

    def _create_gate(self, canal='email', estado_gate='abierto', restricciones_operativas=None):
        if restricciones_operativas is None and canal == 'email':
            restricciones_operativas = {
                'prueba_aislada_ref': 'email-readiness-controlled',
                'oauth_validado_ref': 'oauth-readiness-controlled',
            }
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': canal,
                'provider_key': 'gmail_api' if canal == 'email' else 'twilio_whatsapp',
                'estado_gate': estado_gate,
                'restricciones_operativas': restricciones_operativas or {},
                'evidencia_ref': 'evidence-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _create_identity(self, empresa, canal='email', direccion=None):
        if direccion is None:
            direccion = 'sender@example.com' if canal == 'email' else '+56900000000'
        return IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=canal,
            remitente_visible=empresa.razon_social,
            direccion_o_numero=direccion,
            credencial_ref=f'cred-{canal}',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

    def _enable_channel_for_contract(self, empresa, contrato, canal='email'):
        identity = self._create_identity(empresa, canal=canal)
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal=canal,
            identidad_envio=identity,
            prioridad=1,
        )
        return identity

    def _create_payment_for_contract(self, contrato, *, mes=1, anio=2026):
        period = contrato.periodos_contractuales.get(numero_periodo=1)
        return PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=period,
            mes=mes,
            anio=anio,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_pagado_clp='0.00',
            fecha_vencimiento=date(anio, mes, contrato.dia_pago_mensual),
            codigo_conciliacion_efectivo='111',
        )

    def _create_policy(self, **overrides):
        payload = {
            'tipo_documental': 'contrato_principal',
            'requiere_firma_arrendador': True,
            'requiere_firma_arrendatario': True,
            'requiere_codeudor': False,
            'requiere_notaria': False,
            'modo_firma_permitido': 'firma_simple',
            'estado': 'activa',
        }
        payload.update(overrides)
        response = self.client.post(reverse('documentos-politica-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def test_auth_is_required_for_channel_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('canales-gate-list'),
            reverse('canales-notificacion-contrato-list'),
            reverse('canales-mensaje-list'),
            reverse('canales-mensaje-preparar'),
        ]
        for url in urls:
            response = client.get(url) if 'preparar' not in url else client.post(url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_open_email_gate_requires_readiness_references(self):
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': 'email',
                'provider_key': 'gmail_api',
                'estado_gate': 'abierto',
                'restricciones_operativas': {},
                'evidencia_ref': 'email-evidence-only',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('restricciones_operativas', response.data)

    def test_open_email_gate_rejects_sensitive_evidence_reference(self):
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': 'email',
                'provider_key': 'gmail_api',
                'estado_gate': 'abierto',
                'restricciones_operativas': {
                    'prueba_aislada_ref': 'email-readiness-controlled',
                    'oauth_validado_ref': 'oauth-readiness-controlled',
                },
                'evidencia_ref': 'https://mail.example.test/token/secret',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_ref', response.data)

    def test_open_email_gate_rejects_sensitive_operational_references(self):
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': 'email',
                'provider_key': 'gmail_api',
                'estado_gate': 'abierto',
                'restricciones_operativas': {
                    'prueba_aislada_ref': 'https://mail.example.test/proof?token=secret',
                    'oauth_validado_ref': 'oauth-readiness-controlled',
                },
                'evidencia_ref': 'email-gate-evidence-controlled',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('restricciones_operativas', response.data)

    def test_open_email_gate_rejects_sensitive_operational_keys(self):
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': 'email',
                'provider_key': 'gmail_api',
                'estado_gate': 'abierto',
                'restricciones_operativas': {
                    'prueba_aislada_ref': 'email-readiness-controlled',
                    'oauth_validado_ref': 'oauth-readiness-controlled',
                    'api_key': 'email-api-key-controlled',
                },
                'evidencia_ref': 'email-gate-evidence-controlled',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('restricciones_operativas', response.data)

    def test_open_email_gate_allows_canonical_credential_reference_key(self):
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': 'email',
                'provider_key': 'gmail_api',
                'estado_gate': 'abierto',
                'restricciones_operativas': {
                    'prueba_aislada_ref': 'email-readiness-controlled',
                    'credencial_validada_ref': 'email-readiness-validado-controlled',
                },
                'evidencia_ref': 'email-gate-evidence-controlled',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data['restricciones_operativas']['credencial_validada_ref'],
            'email-readiness-validado-controlled',
        )

    def test_notification_config_requires_enabled_channel_and_normalizes_days(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-001')
        self._enable_channel_for_contract(empresa, contrato, canal='email')

        response = self.client.post(
            reverse('canales-notificacion-contrato-list'),
            {
                'contrato': contrato.pk,
                'canal': 'email',
                'dias_notificacion': [5, '1', 3],
                'activa': True,
                'evidencia_configuracion_ref': 'notification-cadence-custom-001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['dias_notificacion'], [1, 3, 5])

    def test_notification_config_rejects_channel_without_active_assignment(self):
        _, contrato = self._create_contract_context(codigo='NTF-002')

        response = self.client.post(
            reverse('canales-notificacion-contrato-list'),
            {
                'contrato': contrato.pk,
                'canal': 'email',
                'dias_notificacion': [1, 3, 5, 10, 15, 20, 25],
                'activa': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('canal', response.data)

    def test_notification_config_non_base_days_require_non_sensitive_evidence(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-003')
        self._enable_channel_for_contract(empresa, contrato, canal='email')

        missing_evidence = self.client.post(
            reverse('canales-notificacion-contrato-list'),
            {
                'contrato': contrato.pk,
                'canal': 'email',
                'dias_notificacion': [1, 4, 8],
                'activa': True,
            },
            format='json',
        )
        sensitive_evidence = self.client.post(
            reverse('canales-notificacion-contrato-list'),
            {
                'contrato': contrato.pk,
                'canal': 'email',
                'dias_notificacion': [1, 4, 8],
                'activa': True,
                'evidencia_configuracion_ref': 'https://evidence.example.test/token/secret',
            },
            format='json',
        )

        self.assertEqual(missing_evidence.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sensitive_evidence.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_configuracion_ref', missing_evidence.data)
        self.assertIn('evidencia_configuracion_ref', sensitive_evidence.data)

    def test_notification_config_snapshot_redacts_legacy_sensitive_evidence(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-004')
        self._enable_channel_for_contract(empresa, contrato, canal='email')
        ConfiguracionNotificacionContrato.objects.create(
            contrato=contrato,
            canal='email',
            dias_notificacion=[1, 3, 5, 10, 15, 20, 25],
            activa=True,
            evidencia_configuracion_ref='https://evidence.example.test/token/secret',
        )

        response = self.client.get(reverse('canales-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['configuraciones_notificacion'][0]['evidencia_configuracion_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertNotIn('evidence.example.test', str(response.data))

    def test_notification_config_blocks_duplicate_active_channel_per_contract(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-005')
        self._enable_channel_for_contract(empresa, contrato, canal='email')
        payload = {
            'contrato': contrato.pk,
            'canal': 'email',
            'dias_notificacion': [1, 3, 5, 10, 15, 20, 25],
            'activa': True,
        }

        first = self.client.post(reverse('canales-notificacion-contrato-list'), payload, format='json')
        duplicate = self.client.post(reverse('canales-notificacion-contrato-list'), payload, format='json')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

    def test_materialize_payment_notification_schedule_is_idempotent_and_visible_in_snapshot(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-SCH')
        self._enable_channel_for_contract(empresa, contrato, canal='email')
        payment = self._create_payment_for_contract(contrato)
        configuration = ConfiguracionNotificacionContrato.objects.create(
            contrato=contrato,
            canal='email',
            dias_notificacion=[1, 3, 5, 10, 15, 20, 25],
            activa=True,
        )

        first = materialize_payment_notification_schedule(payment)
        second = materialize_payment_notification_schedule(payment)

        self.assertEqual(first['created_count'], 7)
        self.assertEqual(second['created_count'], 0)
        self.assertEqual(NotificacionCobranzaProgramada.objects.count(), 7)
        self.assertEqual(
            list(
                NotificacionCobranzaProgramada.objects.order_by('dia_notificacion').values_list(
                    'dia_notificacion',
                    'fecha_programada',
                )
            ),
            [
                (1, date(2026, 1, 1)),
                (3, date(2026, 1, 3)),
                (5, date(2026, 1, 5)),
                (10, date(2026, 1, 10)),
                (15, date(2026, 1, 15)),
                (20, date(2026, 1, 20)),
                (25, date(2026, 1, 25)),
            ],
        )
        self.assertTrue(
            NotificacionCobranzaProgramada.objects.filter(
                pago_mensual=payment,
                configuracion=configuration,
                estado='programada',
            ).exists()
        )

        list_response = self.client.get(reverse('canales-notificacion-cobranza-list'))
        snapshot_response = self.client.get(reverse('canales-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 7)
        self.assertEqual(len(snapshot_response.data['notificaciones_cobranza']), 7)
        self.assertEqual(snapshot_response.data['notificaciones_cobranza'][0]['canal'], 'email')
        self.assertEqual(snapshot_response.data['notificaciones_cobranza'][0]['pago_mensual'], payment.id)

    def test_notification_schedule_rejects_inactive_configuration(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-INACTIVE')
        self._enable_channel_for_contract(empresa, contrato, canal='email')
        payment = self._create_payment_for_contract(contrato)
        configuration = ConfiguracionNotificacionContrato.objects.create(
            contrato=contrato,
            canal='email',
            dias_notificacion=[1, 3, 5, 10, 15, 20, 25],
            activa=False,
        )
        notification = NotificacionCobranzaProgramada(
            pago_mensual=payment,
            configuracion=configuration,
            canal='email',
            dia_notificacion=5,
            fecha_programada=date(2026, 1, 5),
        )

        with self.assertRaises(ValidationError) as error:
            notification.full_clean()

        self.assertIn('configuracion', error.exception.message_dict)

    def test_skipped_notification_requires_non_sensitive_reason(self):
        empresa, contrato = self._create_contract_context(codigo='NTF-SKIPPED')
        self._enable_channel_for_contract(empresa, contrato, canal='email')
        payment = self._create_payment_for_contract(contrato)
        configuration = ConfiguracionNotificacionContrato.objects.create(
            contrato=contrato,
            canal='email',
            dias_notificacion=[1, 3, 5, 10, 15, 20, 25],
            activa=True,
        )
        notification = NotificacionCobranzaProgramada(
            pago_mensual=payment,
            configuracion=configuration,
            canal='email',
            dia_notificacion=5,
            fecha_programada=date(2026, 1, 5),
            estado='omitida',
        )

        with self.assertRaises(ValidationError) as missing_error:
            notification.full_clean()
        self.assertIn('motivo_estado', missing_error.exception.message_dict)

        notification.motivo_estado = 'https://mail.example.test/token/secret'
        with self.assertRaises(ValidationError) as sensitive_error:
            notification.full_clean()
        self.assertIn('motivo_estado', sensitive_error.exception.message_dict)

        notification.motivo_estado = 'arrendatario-contactado-por-canal-alternativo'
        notification.full_clean()

    def test_channel_apis_redact_inherited_sensitive_references(self):
        _, contrato = self._create_contract_context(codigo='CH-API-REDACT')
        gate = CanalMensajeria.objects.create(
            canal='email',
            provider_key='gmail_api',
            estado_gate=EstadoGateCanal.OPEN,
            evidencia_ref='https://mail.example.test/token/secret',
            restricciones_operativas={
                'prueba_aislada_ref': 'email-readiness-controlled',
                'credencial_validada_ref': 'email-ref-validado-v1',
                'callback_ref': 'https://mail.example.test/proof?token=secret',
                'headers': {'authorization': 'Bearer inherited-channel-value'},
            },
        )
        expediente = ExpedienteDocumental.objects.create(
            entidad_tipo='contrato',
            entidad_id=str(contrato.id),
            estado='abierto',
            owner_operativo=f'mandato:{contrato.mandato_operacion.id}',
        )
        DocumentoEmitido.objects.create(
            expediente=expediente,
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            checksum=VALID_DOCUMENT_SHA256,
            fecha_carga=datetime(2026, 3, 18, 10, 0, tzinfo=ZoneInfo('America/Santiago')),
            usuario=self.user,
            origen='generado_sistema',
            estado=EstadoDocumento.ISSUED,
            storage_ref='https://storage.example.test/contracts/contrato-1.pdf?token=secret',
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )
        MensajeSaliente.objects.create(
            canal='email',
            canal_mensajeria=gate,
            contrato=contrato,
            destinatario='tenant@example.com',
            asunto='Cobro mensual',
            cuerpo='Mensaje heredado',
            estado=EstadoMensajeSaliente.SENT,
            external_ref='https://provider.example.test/token/secret',
            usuario=self.user,
            provider_payload={
                'provider_message_id': 'MSG-SAFE-001',
                'callback': 'https://provider.example.test/token/secret',
                'headers': {'authorization': 'Bearer inherited-channel-value'},
                'attempts': [{'response_ref': 'controlled-response-1'}],
            },
        )

        gates_response = self.client.get(reverse('canales-gate-list'))
        messages_response = self.client.get(reverse('canales-mensaje-list'))
        snapshot_response = self.client.get(reverse('canales-snapshot'))

        self.assertEqual(gates_response.status_code, status.HTTP_200_OK)
        self.assertEqual(messages_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(gates_response.data[0]['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(messages_response.data[0]['external_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['gates'][0]['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['mensajes'][0]['external_ref'], REDACTED_SENSITIVE_REFERENCE)
        gate_restrictions = gates_response.data[0]['restricciones_operativas']
        self.assertEqual(gate_restrictions['prueba_aislada_ref'], 'email-readiness-controlled')
        self.assertEqual(gate_restrictions['credencial_validada_ref'], 'email-ref-validado-v1')
        self.assertEqual(gate_restrictions['callback_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(gate_restrictions['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        snapshot_gate_restrictions = snapshot_response.data['gates'][0]['restricciones_operativas']
        self.assertEqual(snapshot_gate_restrictions['credencial_validada_ref'], 'email-ref-validado-v1')
        self.assertEqual(snapshot_gate_restrictions['callback_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(snapshot_response.data['documentos_emitidos'][0]['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        payload = messages_response.data[0]['provider_payload']
        self.assertEqual(payload['provider_message_id'], 'MSG-SAFE-001')
        self.assertEqual(payload['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(payload['headers']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(payload['attempts'][0]['response_ref'], 'controlled-response-1')

        for response in (gates_response, messages_response, snapshot_response):
            body = response.content.decode()
            self.assertNotIn('mail.example.test', body)
            self.assertNotIn('provider.example.test', body)
            self.assertNotIn('storage.example.test', body)
            self.assertNotIn('token', body)
            self.assertNotIn('secret', body)

    def test_message_rejects_sensitive_provider_payload_on_full_clean(self):
        _, contrato = self._create_contract_context(codigo='CH-PAYLOAD-GUARD')
        gate_data = self._create_gate(canal='email')
        gate = CanalMensajeria.objects.get(pk=gate_data['id'])

        message = MensajeSaliente(
            canal='email',
            canal_mensajeria=gate,
            contrato=contrato,
            destinatario='tenant@example.com',
            asunto='Cobro mensual',
            cuerpo='Mensaje con payload proveedor',
            estado=EstadoMensajeSaliente.SENT,
            external_ref='provider-controlled-001',
            usuario=self.user,
            provider_payload={
                'provider_message_id': 'MSG-SAFE-002',
                'callback': 'https://provider.example.test/callback?token=secret',
            },
        )

        with self.assertRaises(ValidationError) as error:
            message.full_clean()

        self.assertIn('provider_payload', error.exception.message_dict)

    def test_prepared_message_full_clean_requires_open_gate_and_identity(self):
        _, contrato = self._create_contract_context(codigo='CH-PREP-DOMAIN')
        gate_data = self._create_gate(canal='email', estado_gate='suspendido')
        gate = CanalMensajeria.objects.get(pk=gate_data['id'])

        message = MensajeSaliente(
            canal='email',
            canal_mensajeria=gate,
            contrato=contrato,
            destinatario=contrato.arrendatario.email,
            asunto='Cobro mensual',
            cuerpo='Mensaje preparado heredado',
            estado=EstadoMensajeSaliente.PREPARED,
            usuario=self.user,
        )

        with self.assertRaises(ValidationError) as error:
            message.full_clean()

        self.assertIn('canal_mensajeria', error.exception.message_dict)
        self.assertIn('identidad_envio', error.exception.message_dict)

    def test_sent_message_full_clean_requires_traceable_external_ref(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENT-DOMAIN')
        gate_data = self._create_gate(canal='email')
        gate = CanalMensajeria.objects.get(pk=gate_data['id'])
        identity = self._create_identity(empresa, canal='email')

        message = MensajeSaliente(
            canal='email',
            canal_mensajeria=gate,
            identidad_envio=identity,
            contrato=contrato,
            arrendatario=contrato.arrendatario,
            destinatario=contrato.arrendatario.email,
            asunto='Cobro mensual',
            cuerpo='Mensaje enviado heredado',
            estado=EstadoMensajeSaliente.SENT,
            usuario=self.user,
        )

        with self.assertRaises(ValidationError) as error:
            message.full_clean()

        self.assertIn('external_ref', error.exception.message_dict)

    def test_sent_message_full_clean_requires_sent_timestamp(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENT-TS')
        gate_data = self._create_gate(canal='email')
        gate = CanalMensajeria.objects.get(pk=gate_data['id'])
        identity = self._create_identity(empresa, canal='email')

        message = MensajeSaliente(
            canal='email',
            canal_mensajeria=gate,
            identidad_envio=identity,
            contrato=contrato,
            arrendatario=contrato.arrendatario,
            destinatario=contrato.arrendatario.email,
            asunto='Cobro mensual',
            cuerpo='Mensaje enviado heredado',
            estado=EstadoMensajeSaliente.SENT,
            external_ref='email-provider-controlled-001',
            usuario=self.user,
        )

        with self.assertRaises(ValidationError) as error:
            message.full_clean()

        self.assertIn('enviado_at', error.exception.message_dict)

        message.enviado_at = timezone.now()
        message.full_clean()

    def test_prepare_email_message_uses_mandate_identity_assignment(self):
        empresa, contrato = self._create_contract_context(codigo='CH-EMAIL')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Cobro mensual',
                'cuerpo': 'Su pago esta listo.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.PREPARED)
        self.assertEqual(response.data['identidad_envio'], identidad.id)
        self.assertEqual(response.data['destinatario'], contrato.arrendatario.email)

    def test_prepare_email_message_uses_contract_identity_override_before_mandate_assignment(self):
        empresa, contrato = self._create_contract_context(codigo='CH-CONTRACT-OVERRIDE')
        gate = self._create_gate(canal='email')
        identity_default = self._create_identity(empresa, canal='email', direccion='contract-default@example.com')
        identity_override = self._create_identity(empresa, canal='email', direccion='contract-override@example.com')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identity_default,
            prioridad=1,
            estado='activa',
        )
        contrato.identidad_envio_override = identity_override
        contrato.save(update_fields=['identidad_envio_override', 'updated_at'])

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Cobro mensual',
                'cuerpo': 'Su pago esta listo.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.PREPARED)
        self.assertEqual(response.data['identidad_envio'], identity_override.id)

    def test_prepare_message_blocks_when_gate_is_suspended(self):
        empresa, contrato = self._create_contract_context(codigo='CH-WA')
        gate = self._create_gate(canal='whatsapp', estado_gate='suspendido')
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'whatsapp',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'cuerpo': 'Recordatorio',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertTrue(
            ManualResolution.objects.filter(
                category='canales.whatsapp.bloqueado',
                scope_reference=str(response.data['id']),
            ).exists()
        )
        fallback = ManualResolution.objects.get(
            category='canales.whatsapp.fallback_requerido',
            scope_reference=str(response.data['id']),
        )
        self.assertEqual(fallback.metadata['fallback_canal_base'], 'email')
        self.assertEqual(fallback.metadata['canal'], 'whatsapp')

    def test_prepare_message_blocks_when_gate_is_only_conditioned(self):
        empresa, contrato = self._create_contract_context(codigo='CH-COND')
        gate = self._create_gate(canal='email', estado_gate='condicionado')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Gate condicionado',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('no permite envio automatico', response.data['motivo_bloqueo'].lower())

    def test_prepare_email_message_blocks_without_isolated_readiness_refs(self):
        empresa, contrato = self._create_contract_context(codigo='CH-EMAIL-NOREADY')
        gate = CanalMensajeria.objects.create(
            canal='email',
            provider_key='gmail_api',
            estado_gate=EstadoGateCanal.OPEN,
            evidencia_ref='email-evidence-only',
            restricciones_operativas={},
        )
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate.id,
                'contrato': contrato.id,
                'asunto': 'Sin prueba aislada',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('prueba aislada', response.data['motivo_bloqueo'].lower())

    def test_prepare_message_blocks_when_no_identity_is_available(self):
        _, contrato = self._create_contract_context(codigo='CH-NOIDENT')
        gate = self._create_gate(canal='email')

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Sin identidad',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('identidad', response.data['motivo_bloqueo'].lower())

    def test_prepare_whatsapp_message_blocks_when_tenant_has_whatsapp_blocked(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-BLOCK',
            whatsapp_blocked=True,
            whatsapp_opt_in=False,
        )
        gate = self._create_gate(canal='whatsapp')
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'whatsapp',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'cuerpo': 'No deberia salir',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('bloqueado', response.data['motivo_bloqueo'].lower())

    def test_prepare_whatsapp_message_blocks_without_opt_in(self):
        empresa, contrato = self._create_contract_context(codigo='CH-NOOPTIN')
        gate = self._create_gate(canal='whatsapp', restricciones_operativas={'templates_aprobados': True})
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'whatsapp',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'cuerpo': 'Recordatorio',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('opt-in', response.data['motivo_bloqueo'].lower())

    def test_prepare_whatsapp_message_blocks_sensitive_opt_in_evidence(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-OPTIN-SENSITIVE',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='https://wa.example.test/optin?token=secret',
        )
        gate = self._create_gate(canal='whatsapp', restricciones_operativas={'templates_aprobados': True})
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        with patch(
            'canales.services.timezone.localtime',
            return_value=datetime(2026, 5, 21, 10, 0, tzinfo=ZoneInfo('America/Santiago')),
        ):
            response = self.client.post(
                reverse('canales-mensaje-preparar'),
                {
                    'canal': 'whatsapp',
                    'canal_mensajeria': gate['id'],
                    'contrato': contrato.id,
                    'cuerpo': 'Recordatorio',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('opt-in no sensible', response.data['motivo_bloqueo'].lower())

    def test_prepare_whatsapp_message_blocks_non_international_phone(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-WA-BADPHONE',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='optin-controlled-phone',
        )
        Arrendatario.objects.filter(pk=contrato.arrendatario_id).update(telefono='912345678')
        gate = self._create_gate(canal='whatsapp', restricciones_operativas={'templates_aprobados': True})
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        with patch(
            'canales.services.timezone.localtime',
            return_value=datetime(2026, 5, 21, 10, 0, tzinfo=ZoneInfo('America/Santiago')),
        ):
            response = self.client.post(
                reverse('canales-mensaje-preparar'),
                {
                    'canal': 'whatsapp',
                    'canal_mensajeria': gate['id'],
                    'contrato': contrato.id,
                    'cuerpo': 'Recordatorio',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('telefono operativo', response.data['motivo_bloqueo'].lower())

    def test_prepare_whatsapp_message_blocks_without_approved_template(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-NOTEMPLATE',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='optin-controlled-1',
        )
        gate = self._create_gate(canal='whatsapp')
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'whatsapp',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'cuerpo': 'Recordatorio',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('template aprobado', response.data['motivo_bloqueo'].lower())

    def test_prepare_whatsapp_message_blocks_outside_allowed_window(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-WINDOW',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='optin-controlled-2',
        )
        gate = self._create_gate(canal='whatsapp', restricciones_operativas={'templates_aprobados': True})
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        with patch(
            'canales.services.timezone.localtime',
            return_value=datetime(2026, 5, 21, 22, 0, tzinfo=ZoneInfo('America/Santiago')),
        ):
            response = self.client.post(
                reverse('canales-mensaje-preparar'),
                {
                    'canal': 'whatsapp',
                    'canal_mensajeria': gate['id'],
                    'contrato': contrato.id,
                    'cuerpo': 'Recordatorio',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.BLOCKED)
        self.assertIn('08:00-21:00', response.data['motivo_bloqueo'])

    def test_prepare_whatsapp_message_with_opt_in_template_and_window_is_prepared(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-WA-READY',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='optin-controlled-3',
        )
        gate = self._create_gate(canal='whatsapp', restricciones_operativas={'templates_aprobados': True})
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        with patch(
            'canales.services.timezone.localtime',
            return_value=datetime(2026, 5, 21, 10, 0, tzinfo=ZoneInfo('America/Santiago')),
        ):
            response = self.client.post(
                reverse('canales-mensaje-preparar'),
                {
                    'canal': 'whatsapp',
                    'canal_mensajeria': gate['id'],
                    'contrato': contrato.id,
                    'cuerpo': 'Recordatorio',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], EstadoMensajeSaliente.PREPARED)
        self.assertEqual(response.data['destinatario'], contrato.arrendatario.telefono)

    def test_register_manual_whatsapp_send_rechecks_allowed_window(self):
        empresa, contrato = self._create_contract_context(
            codigo='CH-WA-SEND-WIN',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='optin-controlled-4',
        )
        gate = self._create_gate(canal='whatsapp', restricciones_operativas={'templates_aprobados': True})
        identidad = self._create_identity(empresa, canal='whatsapp')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='whatsapp',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )

        with patch(
            'canales.services.timezone.localtime',
            return_value=datetime(2026, 5, 21, 10, 0, tzinfo=ZoneInfo('America/Santiago')),
        ):
            prepared = self.client.post(
                reverse('canales-mensaje-preparar'),
                {
                    'canal': 'whatsapp',
                    'canal_mensajeria': gate['id'],
                    'contrato': contrato.id,
                    'cuerpo': 'Recordatorio',
                },
                format='json',
            )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        self.assertEqual(prepared.data['estado'], EstadoMensajeSaliente.PREPARED)

        with patch(
            'canales.services.timezone.localtime',
            return_value=datetime(2026, 5, 21, 22, 0, tzinfo=ZoneInfo('America/Santiago')),
        ):
            response = self.client.post(
                reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
                {'external_ref': 'manual-wa-1'},
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('WhatsApp', response.data['detail'])
        self.assertEqual(MensajeSaliente.objects.get(pk=prepared.data['id']).estado, EstadoMensajeSaliente.PREPARED)

    def test_explicit_identity_override_is_used_when_valid(self):
        empresa, contrato = self._create_contract_context(codigo='CH-OVERRIDE')
        gate = self._create_gate(canal='email')
        identity_default = self._create_identity(empresa, canal='email', direccion='default@example.com')
        identity_override = self._create_identity(empresa, canal='email', direccion='override@example.com')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identity_default,
            prioridad=1,
            estado='activa',
        )

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'identidad_envio': identity_override.id,
                'asunto': 'Override',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['identidad_envio'], identity_override.id)

    def test_register_manual_send_marks_prepared_message_as_sent(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SEND')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        sent = self.client.post(
            reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
            {'external_ref': 'manual-123'},
            format='json',
        )
        self.assertEqual(sent.status_code, status.HTTP_200_OK)
        self.assertEqual(sent.data['estado'], EstadoMensajeSaliente.SENT)
        self.assertEqual(sent.data['external_ref'], 'manual-123')
        audit_event = AuditEvent.objects.get(
            event_type='canales.mensaje_saliente.sent_manually',
            entity_type='mensaje_saliente',
            entity_id=str(sent.data['id']),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.metadata['external_ref'], 'manual-123')

    def test_mark_manual_send_service_creates_audit_event(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENDSERVICE')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar desde servicio',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        message = MensajeSaliente.objects.get(pk=prepared.data['id'])
        sent = mark_message_as_sent(
            message,
            external_ref='manual-service-001',
            actor_user=self.user,
            ip_address='127.0.0.1',
        )

        self.assertEqual(sent.estado, EstadoMensajeSaliente.SENT)
        self.assertEqual(sent.external_ref, 'manual-service-001')
        audit_event = AuditEvent.objects.get(
            event_type='canales.mensaje_saliente.sent_manually',
            entity_type='mensaje_saliente',
            entity_id=str(sent.pk),
        )
        self.assertEqual(audit_event.actor_user, self.user)
        self.assertEqual(audit_event.ip_address, '127.0.0.1')
        self.assertEqual(audit_event.metadata['external_ref'], 'manual-service-001')

    def test_mark_manual_send_service_requires_actor(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENDACTOR')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar sin actor',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        message = MensajeSaliente.objects.get(pk=prepared.data['id'])
        with self.assertRaisesRegex(ValueError, 'actor trazable'):
            mark_message_as_sent(message, external_ref='manual-service-002')

        message.refresh_from_db()
        self.assertEqual(message.estado, EstadoMensajeSaliente.PREPARED)
        self.assertFalse(
            AuditEvent.objects.filter(
                event_type='canales.mensaje_saliente.sent_manually',
                entity_type='mensaje_saliente',
                entity_id=str(message.pk),
            ).exists()
        )

    def test_register_manual_send_requires_external_reference(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENDREF')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
            {'external_ref': '   '},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('external_ref', response.data)

    def test_register_manual_send_rejects_sensitive_external_reference(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENDSECRET')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
            {'external_ref': 'https://provider.example.test/token/secret'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no sensible', response.data['detail'])
        message = MensajeSaliente.objects.get(pk=prepared.data['id'])
        self.assertEqual(message.estado, EstadoMensajeSaliente.PREPARED)
        self.assertEqual(message.external_ref, '')

    def test_register_manual_send_rechecks_gate_state(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENDGATE')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        CanalMensajeria.objects.filter(pk=gate['id']).update(estado_gate=EstadoGateCanal.SUSPENDED)

        response = self.client.post(
            reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
            {'external_ref': 'manual-after-gate-close'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('gate del canal', response.data['detail'])
        self.assertEqual(MensajeSaliente.objects.get(pk=prepared.data['id']).estado, EstadoMensajeSaliente.PREPARED)

    def test_register_manual_email_send_rechecks_readiness_refs(self):
        empresa, contrato = self._create_contract_context(codigo='CH-SENDREADY')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Enviar',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        CanalMensajeria.objects.filter(pk=gate['id']).update(restricciones_operativas={})

        response = self.client.post(
            reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
            {'external_ref': 'manual-after-readiness-close'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('prueba aislada', response.data['detail'].lower())
        self.assertEqual(MensajeSaliente.objects.get(pk=prepared.data['id']).estado, EstadoMensajeSaliente.PREPARED)

    def test_prepare_message_rejects_document_requiring_formalization(self):
        empresa, contrato = self._create_contract_context(codigo='CH-DOCUNFORM')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        self._create_policy()

        expediente = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(contrato.id),
                'estado': 'abierto',
                'owner_operativo': f'mandato:{contrato.mandato_operacion.id}',
            },
            format='json',
        )
        self.assertEqual(expediente.status_code, status.HTTP_201_CREATED)

        documento = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_DOCUMENT_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/unformalized-contract.pdf',
                'firma_arrendador_registrada': True,
                'firma_arrendatario_registrada': True,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )
        self.assertEqual(documento.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'documento_emitido': documento.data['id'],
                'asunto': 'Contrato sin formalizar',
                'cuerpo': 'No debe salir por canales.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('documento_emitido', response.data)
        self.assertFalse(MensajeSaliente.objects.exists())

    def test_formalized_document_can_be_prepared_and_sent_via_channel_workflow(self):
        empresa, contrato = self._create_contract_context(codigo='CH-DOCSEND')
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        self._create_policy()

        expediente = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(contrato.id),
                'estado': 'abierto',
                'owner_operativo': f'mandato:{contrato.mandato_operacion.id}',
            },
            format='json',
        )
        self.assertEqual(expediente.status_code, status.HTTP_201_CREATED)

        documento = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_DOCUMENT_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/contract-send.pdf',
                'firma_arrendador_registrada': True,
                'firma_arrendatario_registrada': True,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )
        self.assertEqual(documento.status_code, status.HTTP_201_CREATED)

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento.data['id']]),
            {'evidencia_formalizacion_ref': 'formalizacion-canal-doc-001'},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self.assertEqual(formalize.data['estado'], EstadoDocumento.FORMALIZED)

        prepared = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'documento_emitido': documento.data['id'],
                'asunto': 'Contrato formalizado',
                'cuerpo': 'Documento listo para revisión.',
            },
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_201_CREATED)
        self.assertEqual(prepared.data['estado'], EstadoMensajeSaliente.PREPARED)
        self.assertEqual(prepared.data['documento_emitido'], documento.data['id'])
        self.assertEqual(prepared.data['destinatario'], contrato.arrendatario.email)

        sent = self.client.post(
            reverse('canales-mensaje-enviar', args=[prepared.data['id']]),
            {'external_ref': 'doc-send-123'},
            format='json',
        )
        self.assertEqual(sent.status_code, status.HTTP_200_OK)
        self.assertEqual(sent.data['estado'], EstadoMensajeSaliente.SENT)
        self.assertEqual(sent.data['external_ref'], 'doc-send-123')

    def test_prepare_message_rejects_document_from_another_contract(self):
        empresa_a, contrato_a = self._create_contract_context(
            codigo='CH-DOC-A',
            empresa_rut='88888888-8',
            propietario_rut='55555555-5',
            arrendatario_rut='77777777-7',
            socio_ruts=('11111111-1', '22222222-2'),
        )
        empresa_b, contrato_b = self._create_contract_context(
            codigo='CH-DOC-B',
            empresa_rut='99999999-9',
            propietario_rut='66666666-6',
            arrendatario_rut='88888888-8',
            socio_ruts=('33333333-3', '44444444-4'),
        )
        gate = self._create_gate(canal='email')
        identidad = self._create_identity(empresa_b, canal='email')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=contrato_b.mandato_operacion,
            canal='email',
            identidad_envio=identidad,
            prioridad=1,
            estado='activa',
        )
        self._create_policy()

        expediente = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(contrato_a.id),
                'estado': 'abierto',
                'owner_operativo': f'mandato:{contrato_a.mandato_operacion.id}',
            },
            format='json',
        )
        self.assertEqual(expediente.status_code, status.HTTP_201_CREATED)

        documento = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': expediente.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': VALID_DOCUMENT_SHA256,
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'carga_externa_controlada',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/doc-mismatch.pdf',
                'firma_arrendador_registrada': True,
                'firma_arrendatario_registrada': True,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )
        self.assertEqual(documento.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato_b.id,
                'documento_emitido': documento.data['id'],
                'asunto': 'Contrato equivocado',
                'cuerpo': 'No deberia mezclarse.',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_manual_send_rejects_blocked_message(self):
        empresa, contrato = self._create_contract_context(codigo='CH-BLOCKSEND')
        gate = self._create_gate(canal='email', estado_gate='cerrado')
        self._create_identity(empresa, canal='email')

        blocked = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': gate['id'],
                'contrato': contrato.id,
                'asunto': 'Bloqueado',
            },
            format='json',
        )
        self.assertEqual(blocked.status_code, status.HTTP_201_CREATED)
        self.assertEqual(blocked.data['estado'], EstadoMensajeSaliente.BLOCKED)

        sent = self.client.post(
            reverse('canales-mensaje-enviar', args=[blocked.data['id']]),
            {'external_ref': 'manual-999'},
            format='json',
        )
        self.assertEqual(sent.status_code, status.HTTP_400_BAD_REQUEST)


class CanalesScopeAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.user = user_model.objects.create_user(
            username='channels-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.client.force_authenticate(self.user)

        self.gate = CanalMensajeria.objects.create(
            canal='email',
            provider_key='gmail_api',
            estado_gate='abierto',
            evidencia_ref='scope-gate',
            restricciones_operativas={
                'prueba_aislada_ref': 'scope-email-readiness',
                'oauth_validado_ref': 'scope-oauth-readiness',
            },
        )
        self.company_a, self.contract_a = self._create_contract_context(codigo='CH-SCOPE-A')
        self.company_b, self.contract_b = self._create_contract_context(codigo='CH-SCOPE-B')
        self.identity_a = self._create_identity(self.company_a, canal='email', direccion='scope-a@example.com')
        self.identity_b = self._create_identity(self.company_b, canal='email', direccion='scope-b@example.com')
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=self.contract_a.mandato_operacion,
            canal='email',
            identidad_envio=self.identity_a,
            prioridad=1,
            estado='activa',
        )
        AsignacionCanalOperacion.objects.create(
            mandato_operacion=self.contract_b.mandato_operacion,
            canal='email',
            identidad_envio=self.identity_b,
            prioridad=1,
            estado='activa',
        )

        expediente_a = ExpedienteDocumental.objects.create(
            entidad_tipo='contrato',
            entidad_id=str(self.contract_a.id),
            estado='abierto',
            owner_operativo=f'mandato:{self.contract_a.mandato_operacion.id}',
        )
        self.documento_a = DocumentoEmitido.objects.create(
            expediente=expediente_a,
            tipo_documental='contrato_principal',
            version_plantilla='v1',
            checksum=VALID_DOCUMENT_SHA256,
            fecha_carga='2026-03-18T10:00:00-03:00',
            usuario=self.user,
            origen='generado_sistema',
            estado='emitido',
            storage_ref='storage/docs/scope-a.pdf',
        )

        scope = Scope.objects.create(
            code=f'company-{self.company_a.id}',
            name=f'Empresa {self.company_a.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(self.company_a.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=self.user, role=self.operator_role, scope=scope, is_primary=True)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='ChannelCo', rut='88888888-8', socio_ruts=('11111111-1', '22222222-2')):
        socio_1 = self._create_socio(f'{nombre} Socio 1', socio_ruts[0])
        socio_2 = self._create_socio(f'{nombre} Socio 2', socio_ruts[1])
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            empresa_owner=empresa,
            porcentaje='60.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            empresa_owner=empresa,
            porcentaje='40.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        return empresa

    def _create_contract_context(self, codigo='CH-001', whatsapp_blocked=False):
        socio_ruts = ('11111111-1', '22222222-2') if codigo.endswith('A') else ('33333333-3', '44444444-4')
        empresa_rut = '88888888-8' if codigo.endswith('A') else '99999999-9'
        propietario_rut = '55555555-5' if codigo.endswith('A') else '66666666-6'
        arr_rut = '77777777-7' if codigo.endswith('A') else '12121212-2'
        empresa = self._create_active_empresa(nombre=f'Empresa {codigo}', rut=empresa_rut, socio_ruts=socio_ruts)
        propietario = self._create_socio(f'Prop {codigo}', propietario_rut)
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo}',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=f'PROP-{codigo}'[:16],
            estado='activa',
            socio_owner=propietario,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_socio_owner=propietario,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut=arr_rut,
            email='tenant@example.com',
            telefono='+56912345678',
            domicilio_notificaciones='Dir 123',
            estado_contacto='activo',
            whatsapp_bloqueado=whatsapp_blocked,
        )
        contrato = Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        return empresa, contrato

    def _create_identity(self, empresa, canal='email', direccion=None):
        if direccion is None:
            direccion = 'sender@example.com' if canal == 'email' else '+56900000000'
        return IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal=canal,
            remitente_visible=empresa.razon_social,
            direccion_o_numero=direccion,
            credencial_ref=f'cred-{canal}',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

    def test_operator_company_scope_limits_message_list(self):
        self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': self.gate.id,
                'contrato': self.contract_a.id,
                'asunto': 'Scope A',
            },
            format='json',
        )
        admin_user = get_user_model().objects.create_user(
            username='channels-admin',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(admin_user)
        self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': self.gate.id,
                'contrato': self.contract_b.id,
                'asunto': 'Scope B',
            },
            format='json',
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse('canales-mensaje-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['contrato'], self.contract_a.id)

    def test_operator_cannot_prepare_message_for_contract_outside_scope(self):
        response = self.client.post(
            reverse('canales-mensaje-preparar'),
            {
                'canal': 'email',
                'canal_mensajeria': self.gate.id,
                'contrato': self.contract_b.id,
                'asunto': 'Fuera de scope',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_create_or_update_global_gate_configuration(self):
        create_response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': 'whatsapp',
                'provider_key': 'twilio_whatsapp',
                'estado_gate': 'abierto',
                'restricciones_operativas': {},
                'evidencia_ref': 'scope-gate',
            },
            format='json',
        )
        update_response = self.client.patch(
            reverse('canales-gate-detail', args=[self.gate.id]),
            {'estado_gate': 'cerrado'},
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
