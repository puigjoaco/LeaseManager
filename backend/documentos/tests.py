from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from core.models import Role, Scope, UserScopeAssignment
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import DocumentoEmitido, EstadoDocumento, ExpedienteDocumental, PoliticaFirmaYNotaria


class DocumentosAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='docs',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _create_expediente(self, entidad_tipo='manual', entidad_id='1', owner_operativo='manual:1'):
        response = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': entidad_tipo,
                'entidad_id': entidad_id,
                'estado': 'abierto',
                'owner_operativo': owner_operativo,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _create_politica(self, **overrides):
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

    def _create_documento(self, expediente_id, **overrides):
        payload = {
            'expediente': expediente_id,
            'tipo_documental': 'contrato_principal',
            'version_plantilla': 'v1',
            'checksum': 'abc123',
            'fecha_carga': '2026-03-18T10:00:00-03:00',
            'origen': 'generado_sistema',
            'estado': 'emitido',
            'storage_ref': 'storage/contracts/contrato-1.pdf',
            'firma_arrendador_registrada': False,
            'firma_arrendatario_registrada': False,
            'firma_codeudor_registrada': False,
            'recepcion_notarial_registrada': False,
            'comprobante_notarial': None,
        }
        payload.update(overrides)
        response = self.client.post(reverse('documentos-documento-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data

    def _create_active_company(self, nombre, rut, socio_ruts):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=socio_ruts[0], activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=socio_ruts[1], activo=True)
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(participante_socio=socio_1, empresa_owner=empresa, porcentaje='60.00', vigente_desde='2026-01-01', activo=True)
        ParticipacionPatrimonial.objects.create(participante_socio=socio_2, empresa_owner=empresa, porcentaje='40.00', vigente_desde='2026-01-01', activo=True)
        return empresa

    def _create_contract_context(self, empresa, codigo, arr_rut):
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo} 123',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=codigo,
            estado='activa',
            empresa_owner=empresa,
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
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arr {codigo}',
            rut=arr_rut,
            email=f'{codigo.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Dir {codigo}',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'CTR-{codigo}',
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
        return {'mandato': mandato, 'contrato': contrato, 'propiedad': propiedad}

    def test_auth_is_required_for_document_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('documentos-expediente-list'),
            reverse('documentos-politica-list'),
            reverse('documentos-documento-list'),
        ]
        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_expediente_and_document_registers_user(self):
        expediente = self._create_expediente()
        self._create_politica()
        documento = self._create_documento(expediente['id'])

        detail = self.client.get(reverse('documentos-documento-detail', args=[documento['id']]))
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data['usuario'], self.user.id)
        self.assertTrue(AuditEvent.objects.filter(event_type='documentos.documento_emitido.created').exists())

    def test_main_contract_policy_requires_both_signatures(self):
        response = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'contrato_principal',
                'requiere_firma_arrendador': False,
                'requiere_firma_arrendatario': True,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_cannot_be_formalized_without_required_signatures(self):
        expediente = self._create_expediente(entidad_id='2')
        self._create_politica()
        documento = self._create_documento(expediente['id'])

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_with_notary_policy_requires_notary_receipt(self):
        expediente = self._create_expediente(entidad_id='3')
        self._create_politica(requiere_notaria=True)
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {'recepcion_notarial_registrada': True},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_document_can_be_formalized_when_policy_is_satisfied(self):
        expediente = self._create_expediente(entidad_id='4')
        self._create_politica(requiere_notaria=True)
        receipt = self._create_documento(
            expediente['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='notary-v1',
            checksum='notary123',
            storage_ref='storage/contracts/notary.pdf',
        )
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_200_OK)
        self.assertEqual(formalize.data['estado'], EstadoDocumento.FORMALIZED)
        self.assertTrue(AuditEvent.objects.filter(event_type='documentos.documento_emitido.formalized').exists())

    def test_document_cannot_be_formalized_with_notary_receipt_from_other_expediente(self):
        expediente_a = self._create_expediente(entidad_id='4A')
        expediente_b = self._create_expediente(entidad_id='4B')
        self._create_politica(requiere_notaria=True)
        receipt = self._create_documento(
            expediente_b['id'],
            tipo_documental='comprobante_notarial',
            version_plantilla='notary-v1',
            checksum='notary-other-exp',
            storage_ref='storage/contracts/notary-other.pdf',
        )
        documento = self._create_documento(
            expediente_a['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {
                'recepcion_notarial_registrada': True,
                'comprobante_notarial': receipt['id'],
            },
            format='json',
        )

        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_codeudor_signature_is_enforced_by_policy(self):
        expediente = self._create_expediente(entidad_id='5')
        self._create_politica(requiere_codeudor=True)
        documento = self._create_documento(
            expediente['id'],
            firma_arrendador_registrada=True,
            firma_arrendatario_registrada=True,
        )

        formalize = self.client.post(
            reverse('documentos-documento-formalizar', args=[documento['id']]),
            {},
            format='json',
        )
        self.assertEqual(formalize.status_code, status.HTTP_400_BAD_REQUEST)

    def test_contract_expediente_rejects_owner_operativo_from_another_mandate(self):
        company_a = self._create_active_company('Docs API A', '88888888-8', ('11111111-1', '22222222-2'))
        company_b = self._create_active_company('Docs API B', '99999999-9', ('33333333-3', '44444444-4'))
        context_a = self._create_contract_context(company_a, 'DOC-API-A', '55555555-5')
        context_b = self._create_contract_context(company_b, 'DOC-API-B', '66666666-6')

        response = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(context_a['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{context_b['mandato'].id}",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DocumentosScopeAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.user = user_model.objects.create_user(
            username='docs-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.company_a = self._create_active_company('Docs A', '76.311.245-4', ('11.111.111-1', '22.222.222-2'))
        self.company_b = self._create_active_company('Docs B', '76.390.560-8', ('33.333.333-3', '44.444.444-4'))
        self.context_a = self._create_contract_context(self.company_a, 'DOC-A', '55.555.555-5')
        self.context_b = self._create_contract_context(self.company_b, 'DOC-B', '66.666.666-6')
        scope = Scope.objects.create(
            code=f'company-{self.company_a.id}',
            name=f'Empresa {self.company_a.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(self.company_a.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=self.user, role=self.operator_role, scope=scope, is_primary=True)
        self.client.force_authenticate(self.user)

        self.policy = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'contrato_principal',
                'requiere_firma_arrendador': True,
                'requiere_firma_arrendatario': True,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(self.policy.status_code, status.HTTP_403_FORBIDDEN)
        PoliticaFirmaYNotaria.objects.create(
            tipo_documental='contrato_principal',
            requiere_firma_arrendador=True,
            requiere_firma_arrendatario=True,
            requiere_codeudor=False,
            requiere_notaria=False,
            modo_firma_permitido='firma_simple',
            estado='activa',
        )

        self.expediente_a = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(self.context_a['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{self.context_a['mandato'].id}",
            },
            format='json',
        )
        self.assertEqual(self.expediente_a.status_code, status.HTTP_201_CREATED)

        admin_user = user_model.objects.create_user(
            username='docs-admin',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(admin_user)
        self.expediente_b = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(self.context_b['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{self.context_b['mandato'].id}",
            },
            format='json',
        )
        self.assertEqual(self.expediente_b.status_code, status.HTTP_201_CREATED)
        self.client.force_authenticate(self.user)

        self.documento_a = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': self.expediente_a.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': 'doc-a',
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'generado_sistema',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/doc-a.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )
        self.assertEqual(self.documento_a.status_code, status.HTTP_201_CREATED)

    def _create_active_company(self, nombre, rut, socio_ruts):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=socio_ruts[0], activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=socio_ruts[1], activo=True)
        empresa = Empresa.objects.create(razon_social=nombre, rut=rut, estado='activa')
        ParticipacionPatrimonial.objects.create(participante_socio=socio_1, empresa_owner=empresa, porcentaje='60.00', vigente_desde='2026-01-01', activo=True)
        ParticipacionPatrimonial.objects.create(participante_socio=socio_2, empresa_owner=empresa, porcentaje='40.00', vigente_desde='2026-01-01', activo=True)
        return empresa

    def _create_contract_context(self, empresa, codigo, arr_rut):
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo} 123',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=codigo,
            estado='activa',
            empresa_owner=empresa,
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
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arr {codigo}',
            rut=arr_rut,
            email=f'{codigo.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Dir {codigo}',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'CTR-{codigo}',
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
        return {'mandato': mandato, 'contrato': contrato, 'propiedad': propiedad}

    def test_operator_company_scope_limits_document_lists(self):
        expedientes = self.client.get(reverse('documentos-expediente-list'))
        documentos = self.client.get(reverse('documentos-documento-list'))

        self.assertEqual(expedientes.status_code, status.HTTP_200_OK)
        self.assertEqual(documentos.status_code, status.HTTP_200_OK)
        self.assertEqual(len(expedientes.data), 1)
        self.assertEqual(expedientes.data[0]['id'], self.expediente_a.data['id'])
        self.assertEqual(len(documentos.data), 1)
        self.assertEqual(documentos.data[0]['id'], self.documento_a.data['id'])

    def test_operator_cannot_create_document_for_expediente_outside_scope(self):
        response = self.client.post(
            reverse('documentos-documento-list'),
            {
                'expediente': self.expediente_b.data['id'],
                'tipo_documental': 'contrato_principal',
                'version_plantilla': 'v1',
                'checksum': 'doc-b',
                'fecha_carga': '2026-03-18T10:00:00-03:00',
                'origen': 'generado_sistema',
                'estado': 'emitido',
                'storage_ref': 'storage/docs/doc-b.pdf',
                'firma_arrendador_registrada': False,
                'firma_arrendatario_registrada': False,
                'firma_codeudor_registrada': False,
                'recepcion_notarial_registrada': False,
                'comprobante_notarial': None,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_create_expediente_for_contract_outside_scope(self):
        response = self.client.post(
            reverse('documentos-expediente-list'),
            {
                'entidad_tipo': 'contrato',
                'entidad_id': str(self.context_b['contrato'].id),
                'estado': 'abierto',
                'owner_operativo': f"mandato:{self.context_b['mandato'].id}",
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_list_hides_mismatched_contract_and_owner_expediente(self):
        context_c = self._create_contract_context(self.company_a, 'DOC-C', '77.777.777-7')
        ExpedienteDocumental.objects.create(
            entidad_tipo='contrato',
            entidad_id=str(context_c['contrato'].id),
            estado='abierto',
            owner_operativo=f"mandato:{self.context_b['mandato'].id}",
        )

        response = self.client.get(reverse('documentos-expediente-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.expediente_a.data['id'])

    def test_operator_cannot_create_or_update_global_signature_policy(self):
        create_response = self.client.post(
            reverse('documentos-politica-list'),
            {
                'tipo_documental': 'anexo',
                'requiere_firma_arrendador': True,
                'requiere_firma_arrendatario': True,
                'requiere_codeudor': False,
                'requiere_notaria': False,
                'modo_firma_permitido': 'firma_simple',
                'estado': 'activa',
            },
            format='json',
        )
        existing_policy = PoliticaFirmaYNotaria.objects.get(tipo_documental='contrato_principal')
        update_response = self.client.patch(
            reverse('documentos-politica-detail', args=[existing_policy.id]),
            {'requiere_notaria': True},
            format='json',
        )

        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)
