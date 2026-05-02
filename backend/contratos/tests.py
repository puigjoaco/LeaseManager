from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import Arrendatario, AvisoTermino, Contrato, EstadoAvisoTermino, EstadoContrato


class ContratosAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='contracts', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre, rut):
        socio_1 = self._create_socio(f'{nombre} Socio 1', f'{rut[:-1]}1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', f'{rut[:-1]}2')
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

    def _create_active_mandato(self, codigo='MAND-001', owner_rut='11111111-1'):
        propietario = self._create_socio(f'Prop {codigo}', owner_rut)
        admin_company = self._create_active_empresa(f'Admin {codigo}', '88888888-8')
        property_obj = Propiedad.objects.create(
            direccion=f'Av {codigo}',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=codigo,
            estado='activa',
            socio_owner=propietario,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=admin_company,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{codigo}',
            tipo_cuenta='corriente',
            titular_nombre=admin_company.razon_social,
            titular_rut=admin_company.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=property_obj,
            propietario_socio_owner=propietario,
            administrador_empresa_owner=admin_company,
            recaudador_empresa_owner=admin_company,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        return mandato

    def _create_arrendatario(self, rut='12345678-5'):
        return Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Uno',
            rut=rut,
            email='tenant@example.com',
            telefono='999',
            domicilio_notificaciones='Notificaciones 123',
            estado_contacto='activo',
        )

    def _base_contract_payload(self, mandato, arrendatario, codigo='CTR-001'):
        return {
            'codigo_contrato': codigo,
            'mandato_operacion': mandato.id,
            'arrendatario': arrendatario.id,
            'fecha_inicio': '2026-01-01',
            'fecha_fin_vigente': '2026-12-31',
            'fecha_entrega': '2026-01-01',
            'dia_pago_mensual': 5,
            'plazo_notificacion_termino_dias': 60,
            'dias_prealerta_admin': 90,
            'estado': EstadoContrato.ACTIVE,
            'tiene_tramos': False,
            'tiene_gastos_comunes': False,
            'snapshot_representante_legal': {'nombre': 'Rep Legal'},
            'contrato_propiedades': [
                {
                    'propiedad_id': mandato.propiedad_id,
                    'rol_en_contrato': 'principal',
                    'porcentaje_distribucion_interna': '100.00',
                    'codigo_conciliacion_efectivo_snapshot': '123',
                }
            ],
            'periodos_contractuales': [
                {
                    'numero_periodo': 1,
                    'fecha_inicio': '2026-01-01',
                    'fecha_fin': '2026-12-31',
                    'monto_base': '1000000.00',
                    'moneda_base': 'CLP',
                    'tipo_periodo': 'inicial',
                    'origen_periodo': 'manual',
                }
            ],
            'codeudores_solidarios': [
                {
                    'snapshot_identidad': {'nombre': 'Codeudor Uno', 'rut': '22222222-2'},
                    'fecha_inclusion': '2026-01-01',
                    'estado': 'activo',
                }
            ],
        }

    def test_auth_is_required_for_contract_list_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('contratos-arrendatario-list'),
            reverse('contratos-contrato-list'),
            reverse('contratos-aviso-list'),
            reverse('contratos-contrato-propiedad-list'),
            reverse('contratos-periodo-list'),
            reverse('contratos-codeudor-list'),
        ]

        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_arrendatario_normalizes_rut_and_rejects_duplicate(self):
        payload = {
            'tipo_arrendatario': 'persona_natural',
            'nombre_razon_social': 'Arrendatario API',
            'rut': '12.345.678-5',
            'email': 'api@example.com',
            'telefono': '999',
            'domicilio_notificaciones': 'Direccion API',
            'estado_contacto': 'activo',
            'whatsapp_bloqueado': False,
        }
        response = self.client.post(reverse('contratos-arrendatario-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rut'], '12345678-5')

        duplicate_response = self.client.post(reverse('contratos-arrendatario-list'), payload, format='json')
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_active_contract_with_nested_children_succeeds(self):
        mandato = self._create_active_mandato(codigo='MAND-101', owner_rut='11111111-1')
        arrendatario = self._create_arrendatario()
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['contrato_propiedades_detail']), 1)
        self.assertEqual(len(response.data['periodos_contractuales_detail']), 1)
        self.assertEqual(len(response.data['codeudores_solidarios_detail']), 1)
        self.assertTrue(AuditEvent.objects.filter(event_type='contratos.contrato.created').exists())

    def test_create_contract_with_principal_and_linked_property_succeeds(self):
        mandato = self._create_active_mandato(codigo='MAND-102', owner_rut='33333333-3')
        vinculada = Propiedad.objects.create(
            direccion='Av Vinculada',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='MAND-102-V',
            estado='activa',
            socio_owner=mandato.propietario_socio_owner,
        )
        arrendatario = self._create_arrendatario(rut='44444444-4')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-102')
        payload['contrato_propiedades'] = [
            {
                'propiedad_id': mandato.propiedad_id,
                'rol_en_contrato': 'principal',
                'porcentaje_distribucion_interna': '50.00',
                'codigo_conciliacion_efectivo_snapshot': '321',
            },
            {
                'propiedad_id': vinculada.id,
                'rol_en_contrato': 'vinculada',
                'porcentaje_distribucion_interna': '50.00',
                'codigo_conciliacion_efectivo_snapshot': '321',
            },
        ]

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['contrato_propiedades_detail']), 2)

    def test_contract_rejects_when_principal_property_differs_from_mandato(self):
        mandato = self._create_active_mandato(codigo='MAND-103', owner_rut='55555555-5')
        other_property = Propiedad.objects.create(
            direccion='Otra Av',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='OTHER-103',
            estado='activa',
            socio_owner=mandato.propietario_socio_owner,
        )
        arrendatario = self._create_arrendatario(rut='66666666-6')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-103')
        payload['contrato_propiedades'][0]['propiedad_id'] = other_property.id

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_contract_rejects_second_active_contract_for_same_property(self):
        mandato = self._create_active_mandato(codigo='MAND-104', owner_rut='77777777-7')
        arrendatario = self._create_arrendatario(rut='88888888-8')
        first_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-104-A')
        first_response = self.client.post(reverse('contratos-contrato-list'), first_payload, format='json')
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        second_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-104-B')
        second_response = self.client.post(reverse('contratos-contrato-list'), second_payload, format='json')
        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_future_contract_requires_registered_notice(self):
        mandato = self._create_active_mandato(codigo='MAND-105', owner_rut='12121212-4')
        arrendatario = self._create_arrendatario(rut='13131313-1')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-105')
        payload['estado'] = EstadoContrato.FUTURE
        payload['fecha_inicio'] = '2027-01-01'
        payload['fecha_fin_vigente'] = '2027-12-31'
        payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_future_contract_succeeds_after_registered_notice(self):
        mandato = self._create_active_mandato(codigo='MAND-106', owner_rut='14141414-7')
        arrendatario = self._create_arrendatario(rut='15151515-4')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        current_contract = current_response.data['id']
        AvisoTermino.objects.create(
            contrato_id=current_contract,
            fecha_efectiva='2026-12-31',
            causal='No renovacion',
            estado=EstadoAvisoTermino.REGISTERED,
            registrado_por=self.user,
        )

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-F')
        future_payload['estado'] = EstadoContrato.FUTURE
        future_payload['fecha_inicio'] = '2027-01-01'
        future_payload['fecha_fin_vigente'] = '2027-12-31'
        future_payload['fecha_entrega'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'

        future_response = self.client.post(reverse('contratos-contrato-list'), future_payload, format='json')
        self.assertEqual(future_response.status_code, status.HTTP_201_CREATED)

    def test_future_contract_succeeds_after_executed_early_termination(self):
        mandato = self._create_active_mandato(codigo='MAND-106-ET', owner_rut='14141414-9')
        arrendatario = self._create_arrendatario(rut='15151515-6')

        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-ET-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        current_contract = Contrato.objects.get(pk=current_response.data['id'])
        current_contract.estado = EstadoContrato.EARLY_TERMINATED
        current_contract.fecha_fin_vigente = '2026-12-31'
        current_contract.save(update_fields=['estado', 'fecha_fin_vigente', 'updated_at'])

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-ET-F')
        future_payload['estado'] = EstadoContrato.FUTURE
        future_payload['fecha_inicio'] = '2027-01-01'
        future_payload['fecha_fin_vigente'] = '2027-12-31'
        future_payload['fecha_entrega'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'

        future_response = self.client.post(reverse('contratos-contrato-list'), future_payload, format='json')
        self.assertEqual(future_response.status_code, status.HTTP_201_CREATED)

    def test_future_contract_rejects_notice_from_non_current_contract(self):
        mandato = self._create_active_mandato(codigo='MAND-106-X', owner_rut='14141414-8')
        arrendatario = self._create_arrendatario(rut='15151515-5')

        old_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-OLD')
        old_response = self.client.post(reverse('contratos-contrato-list'), old_payload, format='json')
        self.assertEqual(old_response.status_code, status.HTTP_201_CREATED)

        old_contract = Contrato.objects.get(pk=old_response.data['id'])
        old_contract.estado = EstadoContrato.FINISHED
        old_contract.save(update_fields=['estado', 'updated_at'])

        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-CURRENT')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        AvisoTermino.objects.create(
            contrato=old_contract,
            fecha_efectiva='2026-12-31',
            causal='No renovacion antigua',
            estado=EstadoAvisoTermino.REGISTERED,
            registrado_por=self.user,
        )

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-FUTURE-FAIL')
        future_payload['estado'] = EstadoContrato.FUTURE
        future_payload['fecha_inicio'] = '2027-01-01'
        future_payload['fecha_fin_vigente'] = '2027-12-31'
        future_payload['fecha_entrega'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'

        future_response = self.client.post(reverse('contratos-contrato-list'), future_payload, format='json')
        self.assertEqual(future_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registered_notice_cannot_be_canceled_when_future_contract_exists(self):
        mandato = self._create_active_mandato(codigo='MAND-107', owner_rut='16161616-1')
        arrendatario = self._create_arrendatario(rut='17171717-9')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-107-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        aviso_response = self.client.post(
            reverse('contratos-aviso-list'),
            {
                'contrato': current_response.data['id'],
                'fecha_efectiva': '2026-12-31',
                'causal': 'No renovacion',
                'estado': EstadoAvisoTermino.REGISTERED,
            },
            format='json',
        )
        self.assertEqual(aviso_response.status_code, status.HTTP_201_CREATED)

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-107-F')
        future_payload['estado'] = EstadoContrato.FUTURE
        future_payload['fecha_inicio'] = '2027-01-01'
        future_payload['fecha_fin_vigente'] = '2027-12-31'
        future_payload['fecha_entrega'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'
        future_response = self.client.post(reverse('contratos-contrato-list'), future_payload, format='json')
        self.assertEqual(future_response.status_code, status.HTTP_201_CREATED)

        cancel_response = self.client.patch(
            reverse('contratos-aviso-detail', args=[aviso_response.data['id']]),
            {'estado': EstadoAvisoTermino.CANCELED},
            format='json',
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_notice_to_future_contract_workflow_preserves_registered_notice(self):
        mandato = self._create_active_mandato(codigo='MAND-109', owner_rut='20202020-2')
        arrendatario = self._create_arrendatario(rut='21212121-0')

        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-109-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        aviso_response = self.client.post(
            reverse('contratos-aviso-list'),
            {
                'contrato': current_response.data['id'],
                'fecha_efectiva': '2026-12-31',
                'causal': 'No renovacion',
                'estado': EstadoAvisoTermino.REGISTERED,
            },
            format='json',
        )
        self.assertEqual(aviso_response.status_code, status.HTTP_201_CREATED)

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-109-F')
        future_payload['estado'] = EstadoContrato.FUTURE
        future_payload['fecha_inicio'] = '2027-01-01'
        future_payload['fecha_fin_vigente'] = '2027-12-31'
        future_payload['fecha_entrega'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'

        future_response = self.client.post(reverse('contratos-contrato-list'), future_payload, format='json')
        self.assertEqual(future_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(future_response.data['estado'], EstadoContrato.FUTURE)

        cancel_response = self.client.patch(
            reverse('contratos-aviso-detail', args=[aviso_response.data['id']]),
            {'estado': EstadoAvisoTermino.CANCELED},
            format='json',
        )
        self.assertEqual(cancel_response.status_code, status.HTTP_400_BAD_REQUEST)

        aviso = AvisoTermino.objects.get(pk=aviso_response.data['id'])
        future_contract = Contrato.objects.get(pk=future_response.data['id'])
        self.assertEqual(aviso.estado, EstadoAvisoTermino.REGISTERED)
        self.assertEqual(future_contract.estado, EstadoContrato.FUTURE)

    def test_contract_update_emits_update_and_state_change_audit_events(self):
        mandato = self._create_active_mandato(codigo='MAND-108', owner_rut='18181818-6')
        arrendatario = self._create_arrendatario(rut='19191919-3')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-108')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        patch_response = self.client.patch(
            reverse('contratos-contrato-detail', args=[create_response.data['id']]),
            {'estado': EstadoContrato.FINISHED},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertTrue(AuditEvent.objects.filter(event_type='contratos.contrato.updated').exists())
        self.assertTrue(AuditEvent.objects.filter(event_type='contratos.contrato.state_changed').exists())
