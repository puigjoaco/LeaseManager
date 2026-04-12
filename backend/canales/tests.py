from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import ManualResolution
from core.models import Role, Scope, UserScopeAssignment
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from documentos.models import DocumentoEmitido, ExpedienteDocumental
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

from .models import CanalMensajeria, EstadoMensajeSaliente, MensajeSaliente


class CanalesAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='channels', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='ChannelCo', rut='88888888-8'):
        socio_1 = self._create_socio(f'{nombre} Socio 1', '11111111-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', '22222222-2')
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
        empresa = self._create_active_empresa(nombre=f'Empresa {codigo}', rut='88888888-8')
        propietario = self._create_socio(f'Prop {codigo}', '33333333-3')
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
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut='44444444-4',
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

    def _create_gate(self, canal='email', estado_gate='condicionado'):
        response = self.client.post(
            reverse('canales-gate-list'),
            {
                'canal': canal,
                'provider_key': 'gmail_api' if canal == 'email' else 'twilio_whatsapp',
                'estado_gate': estado_gate,
                'restricciones_operativas': {},
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

    def test_auth_is_required_for_channel_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('canales-gate-list'),
            reverse('canales-mensaje-list'),
            reverse('canales-mensaje-preparar'),
        ]
        for url in urls:
            response = client.get(url) if 'preparar' not in url else client.post(url, {}, format='json')
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
        empresa, contrato = self._create_contract_context(codigo='CH-BLOCK', whatsapp_blocked=True)
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

        self.gate = CanalMensajeria.objects.create(canal='email', provider_key='gmail_api', estado_gate='condicionado')
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
            checksum='scope-a',
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
