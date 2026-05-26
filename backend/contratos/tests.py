from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent, ManualResolution
from cobranza.models import EstadoGarantia, GarantiaContractual, PagoMensual
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from documentos.models import EstadoPoliticaFirma, PoliticaFirmaYNotaria, TipoDocumental
from operacion.models import (
    CuentaRecaudadora,
    EstadoCuentaRecaudadora,
    EstadoIdentidadEnvio,
    EstadoMandatoOperacion,
    IdentidadDeEnvio,
    MandatoOperacion,
)
from patrimonio.models import (
    Empresa,
    ParticipacionPatrimonial,
    Propiedad,
    ServicioPropiedad,
    Socio,
    TipoInmueble,
    TipoServicioPropiedad,
)

from .models import (
    AUTOMATIC_RENEWAL_EVENT_TYPE,
    Arrendatario,
    AvisoTermino,
    ContactoPagoArrendatario,
    Contrato,
    ContratoPropiedad,
    EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE,
    EstadoAvisoTermino,
    EstadoContrato,
    PeriodoContractual,
    RolContratoPropiedad,
    TENANT_REPLACEMENT_EVENT_TYPE,
)


class ContratosAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='contracts', password='secret123')
        self.client.force_authenticate(self.user)
        self.contract_policy = self._create_document_policy()

    def _create_document_policy(
        self,
        *,
        tipo_documental=TipoDocumental.MAIN_CONTRACT,
        estado=EstadoPoliticaFirma.ACTIVE,
        **overrides,
    ):
        payload = {
            'tipo_documental': tipo_documental,
            'requiere_firma_arrendador': tipo_documental == TipoDocumental.MAIN_CONTRACT,
            'requiere_firma_arrendatario': tipo_documental == TipoDocumental.MAIN_CONTRACT,
            'estado': estado,
        }
        payload.update(overrides)
        return PoliticaFirmaYNotaria.objects.create(
            **payload,
        )

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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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

    def _create_document_ready_arrendatario(self, rut='12345671-8'):
        return Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Documental',
            rut=rut,
            email='tenant-doc@example.com',
            telefono='999',
            domicilio_notificaciones='Notificaciones 456',
            estado_contacto='activo',
            nacionalidad='chilena',
            estado_civil='soltero',
            profesion='arquitecto',
        )

    def _create_active_identity(self, empresa, *, direccion='contrato-override@example.com'):
        return IdentidadDeEnvio.objects.create(
            empresa_owner=empresa,
            canal='email',
            remitente_visible=empresa.razon_social,
            direccion_o_numero=direccion,
            credencial_ref='cred-contrato-override',
            estado=EstadoIdentidadEnvio.ACTIVE,
        )

    def _create_company_arrendatario(self, rut='22222222-2'):
        return Arrendatario.objects.create(
            tipo_arrendatario='empresa',
            nombre_razon_social='Arrendatario Empresa SpA',
            rut=rut,
            email='tenant-company@example.com',
            telefono='999',
            domicilio_notificaciones='Notificaciones Empresa 123',
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
            'politica_documental': self.contract_policy.id,
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
            reverse('contratos-contacto-pago-list'),
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

    def test_create_arrendatario_requires_whatsapp_opt_in_evidence(self):
        payload = {
            'tipo_arrendatario': 'persona_natural',
            'nombre_razon_social': 'Arrendatario WhatsApp',
            'rut': '22.222.222-2',
            'email': 'wa@example.com',
            'telefono': '+56912345678',
            'domicilio_notificaciones': 'Direccion WA',
            'estado_contacto': 'activo',
            'whatsapp_opt_in': True,
            'whatsapp_opt_in_evidencia_ref': '',
            'whatsapp_bloqueado': False,
        }

        response = self.client.post(reverse('contratos-arrendatario-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('whatsapp_opt_in_evidencia_ref', response.data)

    def test_create_arrendatario_rejects_whatsapp_opt_in_without_international_phone(self):
        payload = {
            'tipo_arrendatario': 'persona_natural',
            'nombre_razon_social': 'Arrendatario WhatsApp Telefono',
            'rut': '66.666.666-6',
            'email': 'waphone@example.com',
            'telefono': '912345678',
            'domicilio_notificaciones': 'Direccion WA',
            'estado_contacto': 'activo',
            'whatsapp_opt_in': True,
            'whatsapp_opt_in_evidencia_ref': 'optin-phone-controlled',
            'whatsapp_bloqueado': False,
        }

        response = self.client.post(reverse('contratos-arrendatario-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('telefono', response.data)

    def test_create_arrendatario_rejects_sensitive_whatsapp_opt_in_evidence(self):
        payload = {
            'tipo_arrendatario': 'persona_natural',
            'nombre_razon_social': 'Arrendatario WhatsApp Sensible',
            'rut': '33.333.333-3',
            'email': 'wasensitive@example.com',
            'telefono': '+56912345678',
            'domicilio_notificaciones': 'Direccion WA',
            'estado_contacto': 'activo',
            'whatsapp_opt_in': True,
            'whatsapp_opt_in_evidencia_ref': 'https://wa.example.test/optin?token=secret',
            'whatsapp_bloqueado': False,
        }

        response = self.client.post(reverse('contratos-arrendatario-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('whatsapp_opt_in_evidencia_ref', response.data)

    def test_arrendatario_apis_redact_inherited_sensitive_whatsapp_opt_in_evidence(self):
        tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Arrendatario Opt In Heredado',
            rut='55.555.555-5',
            email='optin-inherited@example.com',
            telefono='+56912345678',
            domicilio_notificaciones='Direccion Opt In',
            estado_contacto='activo',
            whatsapp_opt_in=True,
            whatsapp_opt_in_evidencia_ref='https://wa.example.test/optin?token=secret',
            whatsapp_bloqueado=False,
            whatsapp_bloqueo_evidencia_ref='https://wa.example.test/block?token=secret',
            whatsapp_rehabilitacion_ref='https://wa.example.test/rehab?token=secret',
        )

        list_response = self.client.get(reverse('contratos-arrendatario-list'))
        detail_response = self.client.get(reverse('contratos-arrendatario-detail', args=[tenant.id]))
        snapshot_response = self.client.get(reverse('contratos-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['whatsapp_opt_in_evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['whatsapp_opt_in_evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            snapshot_response.data['arrendatarios'][0]['whatsapp_opt_in_evidencia_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(list_response.data[0]['whatsapp_bloqueo_evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['whatsapp_rehabilitacion_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            snapshot_response.data['arrendatarios'][0]['whatsapp_bloqueo_evidencia_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('wa.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

    def test_create_arrendatario_rejects_opt_in_when_whatsapp_blocked(self):
        payload = {
            'tipo_arrendatario': 'persona_natural',
            'nombre_razon_social': 'Arrendatario Bloqueado',
            'rut': '44.444.444-4',
            'email': 'wablock@example.com',
            'telefono': '+56912345678',
            'domicilio_notificaciones': 'Direccion WA',
            'estado_contacto': 'activo',
            'whatsapp_opt_in': True,
            'whatsapp_opt_in_evidencia_ref': 'optin-test-1',
            'whatsapp_bloqueado': True,
        }

        response = self.client.post(reverse('contratos-arrendatario-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('whatsapp_opt_in', response.data)

    def test_block_whatsapp_requires_non_sensitive_evidence(self):
        arrendatario = self._create_arrendatario(rut='12345676-9')

        response = self.client.post(
            reverse('contratos-arrendatario-whatsapp-bloquear', args=[arrendatario.id]),
            {
                'motivo': 'Rebote definitivo proveedor controlado',
                'evidencia_ref': 'https://wa.example.test/block?token=secret',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidencia_ref', response.data)

    def test_block_whatsapp_records_trace_event_and_admin_alert(self):
        arrendatario = self._create_arrendatario(rut='12345677-7')
        arrendatario.telefono = '+56912345678'
        arrendatario.whatsapp_opt_in = True
        arrendatario.whatsapp_opt_in_evidencia_ref = 'optin-before-block'
        arrendatario.full_clean()
        arrendatario.save()

        response = self.client.post(
            reverse('contratos-arrendatario-whatsapp-bloquear', args=[arrendatario.id]),
            {
                'motivo': 'Proveedor reporto bloqueo definitivo del contacto.',
                'evidencia_ref': 'wa-block-controlled-001',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        arrendatario.refresh_from_db()
        self.assertTrue(arrendatario.whatsapp_bloqueado)
        self.assertFalse(arrendatario.whatsapp_opt_in)
        self.assertEqual(arrendatario.whatsapp_bloqueo_motivo, 'Proveedor reporto bloqueo definitivo del contacto.')
        self.assertEqual(arrendatario.whatsapp_bloqueo_evidencia_ref, 'wa-block-controlled-001')
        self.assertIsNotNone(arrendatario.whatsapp_bloqueado_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='contratos.arrendatario.whatsapp_blocked',
                entity_type='arrendatario',
                entity_id=str(arrendatario.id),
            ).exists()
        )
        alert = ManualResolution.objects.get(
            category='canales.whatsapp.bloqueo_definitivo',
            scope_type='arrendatario',
            scope_reference=str(arrendatario.id),
        )
        self.assertEqual(alert.status, ManualResolution.Status.OPEN)
        self.assertEqual(alert.metadata['evidencia_ref'], 'wa-block-controlled-001')

    def test_rehabilitate_whatsapp_clears_block_without_erasing_block_trace(self):
        arrendatario = self._create_arrendatario(rut='12345680-7')
        block_response = self.client.post(
            reverse('contratos-arrendatario-whatsapp-bloquear', args=[arrendatario.id]),
            {
                'motivo': 'Bloqueo definitivo controlado.',
                'evidencia_ref': 'wa-block-controlled-002',
            },
            format='json',
        )
        self.assertEqual(block_response.status_code, status.HTTP_200_OK, block_response.data)
        arrendatario.refresh_from_db()
        self.assertFalse(arrendatario.whatsapp_opt_in)

        response = self.client.post(
            reverse('contratos-arrendatario-whatsapp-rehabilitar', args=[arrendatario.id]),
            {'rehabilitacion_ref': 'wa-rehab-controlled-001'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        arrendatario.refresh_from_db()
        self.assertFalse(arrendatario.whatsapp_bloqueado)
        self.assertEqual(arrendatario.whatsapp_bloqueo_evidencia_ref, 'wa-block-controlled-002')
        self.assertEqual(arrendatario.whatsapp_rehabilitacion_ref, 'wa-rehab-controlled-001')
        self.assertIsNotNone(arrendatario.whatsapp_rehabilitado_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='contratos.arrendatario.whatsapp_rehabilitated',
                entity_type='arrendatario',
                entity_id=str(arrendatario.id),
            ).exists()
        )
        alert = ManualResolution.objects.get(
            category='canales.whatsapp.bloqueo_definitivo',
            scope_type='arrendatario',
            scope_reference=str(arrendatario.id),
        )
        self.assertEqual(alert.status, ManualResolution.Status.RESOLVED)
        self.assertEqual(alert.metadata['rehabilitacion_ref'], 'wa-rehab-controlled-001')

    def test_rehabilitate_whatsapp_rejects_sensitive_reference(self):
        arrendatario = self._create_arrendatario(rut='12345679-3')
        arrendatario.block_whatsapp(
            motivo='Bloqueo definitivo controlado.',
            evidencia_ref='wa-block-controlled-003',
        )
        arrendatario.save()

        response = self.client.post(
            reverse('contratos-arrendatario-whatsapp-rehabilitar', args=[arrendatario.id]),
            {'rehabilitacion_ref': 'https://wa.example.test/rehab?token=secret'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rehabilitacion_ref', response.data)

    def test_generic_update_cannot_rehabilitate_whatsapp_without_reference(self):
        arrendatario = self._create_arrendatario(rut='12345681-5')
        arrendatario.block_whatsapp(
            motivo='Bloqueo definitivo controlado.',
            evidencia_ref='wa-block-controlled-004',
        )
        arrendatario.save()

        response = self.client.patch(
            reverse('contratos-arrendatario-detail', args=[arrendatario.id]),
            {'whatsapp_bloqueado': False},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('whatsapp_rehabilitacion_ref', response.data)

    def test_generic_update_rehabilitates_whatsapp_with_audit_trace(self):
        arrendatario = self._create_arrendatario(rut='12345682-3')
        block_response = self.client.post(
            reverse('contratos-arrendatario-whatsapp-bloquear', args=[arrendatario.id]),
            {
                'motivo': 'Bloqueo definitivo controlado.',
                'evidencia_ref': 'wa-block-controlled-005',
            },
            format='json',
        )
        self.assertEqual(block_response.status_code, status.HTTP_200_OK, block_response.data)

        response = self.client.patch(
            reverse('contratos-arrendatario-detail', args=[arrendatario.id]),
            {
                'whatsapp_bloqueado': False,
                'whatsapp_rehabilitacion_ref': 'wa-rehab-controlled-002',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        arrendatario.refresh_from_db()
        self.assertFalse(arrendatario.whatsapp_bloqueado)
        self.assertEqual(arrendatario.whatsapp_rehabilitacion_ref, 'wa-rehab-controlled-002')
        self.assertIsNotNone(arrendatario.whatsapp_rehabilitado_at)
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='contratos.arrendatario.whatsapp_rehabilitated',
                entity_type='arrendatario',
                entity_id=str(arrendatario.id),
            ).exists()
        )
        self.assertEqual(
            ManualResolution.objects.get(
                category='canales.whatsapp.bloqueo_definitivo',
                scope_type='arrendatario',
                scope_reference=str(arrendatario.id),
            ).status,
            ManualResolution.Status.RESOLVED,
        )

    def test_create_payment_contact_requires_structured_contact_method(self):
        arrendatario = self._create_arrendatario(rut='12345670-K')
        payload = {
            'arrendatario': arrendatario.id,
            'nombre': 'Contacto Pago',
            'rol_operativo': 'contacto_pago',
            'email': '',
            'telefono': '',
            'evidencia_autorizacion_ref': 'contact-payment-ref-v1',
            'es_principal': True,
            'estado': 'activo',
        }

        response = self.client.post(reverse('contratos-contacto-pago-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_create_payment_contact_structured_succeeds_and_audits(self):
        arrendatario = self._create_arrendatario(rut='12345671-8')
        payload = {
            'arrendatario': arrendatario.id,
            'nombre': 'Contacto Pago Principal',
            'rol_operativo': 'pago_arriendo',
            'email': 'pagos@example.com',
            'telefono': '+56912345678',
            'evidencia_autorizacion_ref': 'contact-payment-controlled-v1',
            'es_principal': True,
            'estado': 'activo',
        }

        response = self.client.post(reverse('contratos-contacto-pago-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['arrendatario'], arrendatario.id)
        self.assertEqual(response.data['nombre'], 'Contacto Pago Principal')
        self.assertTrue(
            AuditEvent.objects.filter(event_type='contratos.contacto_pago_arrendatario.created').exists()
        )

    def test_payment_contact_apis_and_snapshot_redact_sensitive_evidence(self):
        arrendatario = self._create_arrendatario(rut='12345674-2')
        contact = ContactoPagoArrendatario.objects.create(
            arrendatario=arrendatario,
            nombre='Contacto Pago Heredado',
            rol_operativo='pago_arriendo',
            email='pagos-heredado@example.com',
            evidencia_autorizacion_ref='https://payments.example.test/evidence?token=secret',
            es_principal=True,
            estado='activo',
        )

        list_response = self.client.get(reverse('contratos-contacto-pago-list'))
        detail_response = self.client.get(reverse('contratos-contacto-pago-detail', args=[contact.id]))
        snapshot_response = self.client.get(reverse('contratos-snapshot'))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]['evidencia_autorizacion_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(detail_response.data['evidencia_autorizacion_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            snapshot_response.data['arrendatarios'][0]['contactos_pago'][0]['evidencia_autorizacion_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        rendered = f'{list_response.data}{detail_response.data}{snapshot_response.data}'
        self.assertNotIn('payments.example.test', rendered)
        self.assertNotIn('token=secret', rendered)

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

    def test_update_delivery_date_requires_guarantee_or_authorization(self):
        mandato = self._create_active_mandato(codigo='MAND-101-DEL-BLOCK', owner_rut='11111111-1')
        arrendatario = self._create_arrendatario()
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-DEL-BLOCK')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        contrato_id = create_response.data['id']

        response = self.client.patch(
            reverse('contratos-contrato-detail', args=[contrato_id]),
            {'fecha_entrega': '2026-01-02'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('entrega_llaves_autorizacion_ref', response.data)

    def test_update_delivery_date_accepts_audited_authorization(self):
        mandato = self._create_active_mandato(codigo='MAND-101-DEL-AUTH', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario()
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-DEL-AUTH')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        contrato_id = create_response.data['id']

        response = self.client.patch(
            reverse('contratos-contrato-detail', args=[contrato_id]),
            {
                'fecha_entrega': '2026-01-02',
                'entrega_llaves_autorizacion_ref': 'acta-entrega-llaves-001',
                'entrega_llaves_autorizacion_motivo': 'Autorizacion operativa aprobada por administracion.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contrato = Contrato.objects.get(pk=contrato_id)
        self.assertEqual(contrato.entrega_llaves_autorizacion_ref, 'acta-entrega-llaves-001')
        self.assertEqual(contrato.fecha_entrega, date(2026, 1, 2))

    def test_update_delivery_date_accepts_covered_guarantee(self):
        mandato = self._create_active_mandato(codigo='MAND-101-DEL-GAR', owner_rut='11111113-8')
        arrendatario = self._create_arrendatario()
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-DEL-GAR')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        contrato = Contrato.objects.get(pk=create_response.data['id'])
        GarantiaContractual.objects.create(
            contrato=contrato,
            monto_pactado=Decimal('500000.00'),
            monto_recibido=Decimal('500000.00'),
            estado_garantia=EstadoGarantia.HELD,
            fecha_recepcion=date(2026, 1, 1),
        )

        response = self.client.patch(
            reverse('contratos-contrato-detail', args=[contrato.pk]),
            {'fecha_entrega': '2026-01-02'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_delivery_authorization_rejects_sensitive_reference(self):
        mandato = self._create_active_mandato(codigo='MAND-101-DEL-SENS', owner_rut='11111114-6')
        arrendatario = self._create_arrendatario()
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-DEL-SENS')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        response = self.client.patch(
            reverse('contratos-contrato-detail', args=[create_response.data['id']]),
            {
                'fecha_entrega': '2026-01-02',
                'entrega_llaves_autorizacion_ref': 'https://secreto.local/token=abc',
                'entrega_llaves_autorizacion_motivo': 'Autorizacion operativa.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('entrega_llaves_autorizacion_ref', response.data)

    def test_create_active_contract_requires_document_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-POL-MISS', owner_rut='11111114-6')
        arrendatario = self._create_arrendatario(rut='12345675-0')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-POL-MISS')
        payload.pop('politica_documental')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('politica_documental', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-POL-MISS').exists())

    def test_create_active_contract_rejects_non_main_document_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-POL-TYPE', owner_rut='11111113-8')
        arrendatario = self._create_arrendatario(rut='12345676-9')
        addendum_policy = self._create_document_policy(tipo_documental=TipoDocumental.ADDENDUM)
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-POL-TYPE')
        payload['politica_documental'] = addendum_policy.id

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('politica_documental', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-POL-TYPE').exists())

    def test_create_active_contract_rejects_inactive_document_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-POL-INACT', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='12345677-7')
        self.contract_policy.estado = EstadoPoliticaFirma.INACTIVE
        self.contract_policy.save(update_fields=['estado', 'updated_at'])
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-POL-INACT')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('politica_documental', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-POL-INACT').exists())

    def test_create_active_natural_contract_requires_document_profile_when_policy_demands_it(self):
        mandato = self._create_active_mandato(codigo='MAND-101-POL-PROFILE', owner_rut='11111110-3')
        arrendatario = self._create_arrendatario(rut='12345674-2')
        self.contract_policy.requiere_nacionalidad_arrendatario = True
        self.contract_policy.requiere_estado_civil_arrendatario = True
        self.contract_policy.requiere_profesion_arrendatario = True
        self.contract_policy.save(
            update_fields=[
                'requiere_nacionalidad_arrendatario',
                'requiere_estado_civil_arrendatario',
                'requiere_profesion_arrendatario',
                'updated_at',
            ]
        )
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-POL-PROFILE')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('arrendatario', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-POL-PROFILE').exists())

    def test_create_active_natural_contract_accepts_required_document_profile(self):
        mandato = self._create_active_mandato(codigo='MAND-101-POL-PROFILE-OK', owner_rut='11111109-K')
        arrendatario = self._create_document_ready_arrendatario(rut='12345673-4')
        self.contract_policy.requiere_nacionalidad_arrendatario = True
        self.contract_policy.requiere_estado_civil_arrendatario = True
        self.contract_policy.requiere_profesion_arrendatario = True
        self.contract_policy.save(
            update_fields=[
                'requiere_nacionalidad_arrendatario',
                'requiere_estado_civil_arrendatario',
                'requiere_profesion_arrendatario',
                'updated_at',
            ]
        )
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-POL-PROFILE-OK')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        snapshot_response = self.client.get(reverse('contratos-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        tenant_snapshot = snapshot_response.data['arrendatarios'][0]
        self.assertEqual(tenant_snapshot['nacionalidad'], 'chilena')
        self.assertEqual(tenant_snapshot['estado_civil'], 'soltero')
        self.assertEqual(tenant_snapshot['profesion'], 'arquitecto')

    def test_contract_snapshot_exposes_document_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-POL-SNAP', owner_rut='11111110-3')
        arrendatario = self._create_arrendatario(rut='12345674-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-POL-SNAP')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        snapshot_response = self.client.get(reverse('contratos-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(snapshot_response.status_code, status.HTTP_200_OK)
        contract_snapshot = snapshot_response.data['contratos'][0]
        self.assertEqual(contract_snapshot['politica_documental'], self.contract_policy.id)
        self.assertEqual(contract_snapshot['politica_documental_tipo'], TipoDocumental.MAIN_CONTRACT)
        self.assertEqual(contract_snapshot['politica_documental_estado'], EstadoPoliticaFirma.ACTIVE)

    def test_create_retroactive_contract_after_cutoff_records_manual_notification_alert(self):
        mandato = self._create_active_mandato(codigo='MAND-101-RETRO', owner_rut='11111119-7')
        arrendatario = self._create_arrendatario(rut='12345672-6')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-RETRO')

        with patch('contratos.serializers.timezone.localdate', return_value=date(2026, 1, 10)):
            response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['fecha_registro_operativo'], '2026-01-10')
        self.assertTrue(response.data['requiere_notificacion_manual_retroactiva'])
        self.assertIn('notificacion manual', response.data['alerta_notificacion_manual_retroactiva'])
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type='contratos.contrato.retroactive_manual_notification_alert',
                entity_id=str(response.data['id']),
            ).exists()
        )

    def test_create_contract_accepts_authorized_identity_override(self):
        mandato = self._create_active_mandato(codigo='MAND-101-ID-OK', owner_rut='11111115-4')
        arrendatario = self._create_arrendatario(rut='12345679-3')
        identidad = self._create_active_identity(mandato.administrador_empresa_owner)
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-ID-OK')
        payload['identidad_envio_override'] = identidad.id

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['identidad_envio_override'], identidad.id)
        self.assertEqual(response.data['identidad_envio_override_display'], identidad.remitente_visible)
        self.assertTrue(AuditEvent.objects.filter(event_type='contratos.contrato.created').exists())

    def test_create_contract_rejects_unauthorized_identity_override_owner(self):
        mandato = self._create_active_mandato(codigo='MAND-101-ID-BAD', owner_rut='11111116-2')
        arrendatario = self._create_arrendatario(rut='12345670-K')
        unrelated = self._create_active_empresa('Override No Autorizada', '99999999-9')
        identidad = self._create_active_identity(unrelated, direccion='override-bad@example.com')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-ID-BAD')
        payload['identidad_envio_override'] = identidad.id

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('identidad_envio_override', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-ID-BAD').exists())

    def test_create_contract_rejects_inactive_identity_override(self):
        mandato = self._create_active_mandato(codigo='MAND-101-ID-INACTIVE', owner_rut='11111117-0')
        arrendatario = self._create_arrendatario(rut='12345671-8')
        identidad = self._create_active_identity(
            mandato.administrador_empresa_owner,
            direccion='override-inactive@example.com',
        )
        identidad.estado = EstadoIdentidadEnvio.SUSPENDED
        identidad.save(update_fields=['estado', 'updated_at'])
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-ID-INACTIVE')
        payload['identidad_envio_override'] = identidad.id

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('identidad_envio_override', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-ID-INACTIVE').exists())

    def test_create_company_contract_requires_representative_snapshot(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REP-MISS', owner_rut='11111116-2')
        arrendatario = self._create_company_arrendatario(rut='22222226-5')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REP-MISS')
        payload['snapshot_representante_legal'] = {}

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('snapshot_representante_legal', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-REP-MISS').exists())

    def test_create_company_contract_rejects_invalid_representative_rut(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REP-RUT', owner_rut='11111117-0')
        arrendatario = self._create_company_arrendatario(rut='22222227-3')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REP-RUT')
        payload['snapshot_representante_legal'] = {
            'nombre': 'Representante Legal',
            'rut': '12.345.678-9',
        }

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('snapshot_representante_legal', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-REP-RUT').exists())

    def test_create_company_contract_normalizes_representative_snapshot(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REP-OK', owner_rut='11111118-9')
        arrendatario = self._create_company_arrendatario(rut='22222228-1')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REP-OK')
        payload['snapshot_representante_legal'] = {
            'nombre': ' Representante Legal ',
            'rut': '12.345.678-5',
        }

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['snapshot_representante_legal']['nombre'], 'Representante Legal')
        self.assertEqual(response.data['snapshot_representante_legal']['rut'], '12345678-5')
        self.assertTrue(AuditEvent.objects.filter(event_type='contratos.contrato.created').exists())

    def test_create_contract_rejects_nested_codebtor_without_identity_name(self):
        mandato = self._create_active_mandato(codigo='MAND-101-CB', owner_rut='11111116-2')
        arrendatario = self._create_arrendatario(rut='22222226-5')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-CB')
        payload['codeudores_solidarios'][0]['snapshot_identidad'] = {
            'nombre': ' ',
            'rut': '22222222-2',
        }

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('codeudores_solidarios', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-CB').exists())

    def test_contract_rejects_period_gaps_inside_current_validity(self):
        mandato = self._create_active_mandato(codigo='MAND-101-GAP', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-GAP')
        payload['periodos_contractuales'] = [
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-01-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 2,
                'fecha_inicio': '2026-03-01',
                'fecha_fin': '2026-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'manual',
            },
        ]

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodos_contractuales', response.data)

    def test_contract_rejects_period_numbers_outside_chronological_order(self):
        mandato = self._create_active_mandato(codigo='MAND-101-PER-NUM', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-PER-NUM')
        payload['periodos_contractuales'] = [
            {
                'numero_periodo': 2,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-06-30',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-07-01',
                'fecha_fin': '2026-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'manual',
            },
        ]

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodos_contractuales', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-PER-NUM').exists())

    def test_renewal_period_with_changed_base_requires_policy_trace(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-BASE', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-BASE')
        payload['tiene_tramos'] = True
        payload['periodos_contractuales'] = [
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-06-30',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 2,
                'fecha_inicio': '2026-07-01',
                'fecha_fin': '2026-12-31',
                'monto_base': '1100000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'renovacion_automatica',
            },
        ]

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodos_contractuales', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-REN-BASE').exists())

    def test_renewal_period_with_changed_base_accepts_documented_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-POL', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-POL')
        payload['tiene_tramos'] = True
        payload['periodos_contractuales'] = [
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-06-30',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 2,
                'fecha_inicio': '2026-07-01',
                'fecha_fin': '2026-12-31',
                'monto_base': '1100000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'renovacion_automatica',
                'politica_base_renovacion_ref': 'renewal-base-policy-001',
                'politica_base_renovacion_motivo': (
                    'Politica documentada permite reajustar la base de renovacion del tramo.'
                ),
            },
        ]

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contrato = Contrato.objects.get(codigo_contrato='CTR-101-REN-POL')
        renewal = contrato.periodos_contractuales.get(numero_periodo=2)
        self.assertEqual(renewal.politica_base_renovacion_ref, 'renewal-base-policy-001')

    def test_automatic_renewal_endpoint_appends_period_and_audit_event(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-AUTO', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-AUTO')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('contratos-contrato-renovacion-automatica', args=[create_response.data['id']]),
            {'fecha_fin': '2027-12-31'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contrato = Contrato.objects.get(pk=create_response.data['id'])
        self.assertEqual(contrato.fecha_fin_vigente, date(2027, 12, 31))
        self.assertTrue(contrato.tiene_tramos)
        renewal = contrato.periodos_contractuales.get(numero_periodo=2)
        self.assertEqual(renewal.fecha_inicio, date(2027, 1, 1))
        self.assertEqual(renewal.fecha_fin, date(2027, 12, 31))
        self.assertEqual(renewal.monto_base, Decimal('1000000.00'))
        self.assertEqual(renewal.tipo_periodo, 'renovacion')
        self.assertEqual(renewal.origen_periodo, 'renovacion_automatica')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=AUTOMATIC_RENEWAL_EVENT_TYPE,
                entity_type='periodo_contractual',
                entity_id=str(renewal.pk),
            ).exists()
        )
        self.assertEqual(response.data['periodo_renovacion']['id'], renewal.pk)

    def test_automatic_renewal_endpoint_rejects_registered_notice(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-NOT', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-NOT')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        contrato = Contrato.objects.get(pk=create_response.data['id'])
        AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=date(2026, 12, 31),
            causal='No renovacion',
            estado=EstadoAvisoTermino.REGISTERED,
        )

        response = self.client.post(
            reverse('contratos-contrato-renovacion-automatica', args=[contrato.pk]),
            {'fecha_fin': '2027-12-31'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('aviso_termino', response.data)

    def test_automatic_renewal_endpoint_rejects_uncovered_current_end(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-GAP', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-GAP')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        contrato = Contrato.objects.get(pk=create_response.data['id'])
        first_period = contrato.periodos_contractuales.get(numero_periodo=1)
        first_period.fecha_fin = date(2026, 11, 30)
        first_period.save(update_fields=['fecha_fin', 'updated_at'])

        response = self.client.post(
            reverse('contratos-contrato-renovacion-automatica', args=[contrato.pk]),
            {'fecha_fin': '2027-12-31'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodos_contractuales', response.data)

    def test_automatic_renewal_endpoint_rejects_changed_base_without_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-BASE-AUTO', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-BASE-AUTO')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('contratos-contrato-renovacion-automatica', args=[create_response.data['id']]),
            {
                'fecha_fin': '2027-12-31',
                'monto_base': '1100000.00',
                'moneda_base': 'CLP',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('politica_base_renovacion_ref', response.data)

    def test_automatic_renewal_endpoint_accepts_changed_base_with_policy(self):
        mandato = self._create_active_mandato(codigo='MAND-101-REN-POL-AUTO', owner_rut='11111112-K')
        arrendatario = self._create_arrendatario(rut='22222222-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-REN-POL-AUTO')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('contratos-contrato-renovacion-automatica', args=[create_response.data['id']]),
            {
                'fecha_fin': '2027-12-31',
                'monto_base': '1100000.00',
                'moneda_base': 'CLP',
                'politica_base_renovacion_ref': 'renewal-base-policy-automatic-001',
                'politica_base_renovacion_motivo': 'Politica documentada autoriza nueva base de renovacion.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        renewal = PeriodoContractual.objects.get(
            contrato_id=create_response.data['id'],
            numero_periodo=2,
        )
        self.assertEqual(renewal.monto_base, Decimal('1100000.00'))
        self.assertEqual(renewal.politica_base_renovacion_ref, 'renewal-base-policy-automatic-001')

    def test_active_contract_rejects_non_month_boundary_dates(self):
        mandato = self._create_active_mandato(codigo='MAND-101-DATES', owner_rut='11111113-8')
        arrendatario = self._create_arrendatario(rut='22222223-0')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-DATES')
        payload['fecha_inicio'] = '2026-01-02'
        payload['fecha_entrega'] = '2026-01-02'
        payload['periodos_contractuales'][0]['fecha_inicio'] = '2026-01-02'

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-DATES').exists())

    def test_contract_rejects_period_non_month_boundary_dates(self):
        mandato = self._create_active_mandato(codigo='MAND-101-PER-DATES', owner_rut='11111118-9')
        arrendatario = self._create_arrendatario(rut='22222228-1')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-PER-DATES')
        payload['periodos_contractuales'] = [
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-01-15',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 2,
                'fecha_inicio': '2026-01-16',
                'fecha_fin': '2026-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'manual',
            },
        ]

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodos_contractuales', response.data)
        self.assertFalse(Contrato.objects.filter(codigo_contrato='CTR-101-PER-DATES').exists())

    def test_active_contract_rejects_mandate_outside_contract_validity(self):
        mandato = self._create_active_mandato(codigo='MAND-101-VIG', owner_rut='11111115-4')
        mandato.vigencia_desde = '2026-02-01'
        mandato.vigencia_hasta = '2026-11-30'
        mandato.save(update_fields=['vigencia_desde', 'vigencia_hasta', 'updated_at'])
        arrendatario = self._create_arrendatario(rut='22222225-7')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-VIG')

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mandato_operacion', response.data)

    def test_contract_rejects_period_below_operational_minimum(self):
        mandato = self._create_active_mandato(codigo='MAND-101-MIN', owner_rut='11111114-6')
        arrendatario = self._create_arrendatario(rut='22222224-9')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-MIN')
        payload['periodos_contractuales'][0]['monto_base'] = '999.00'

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodos_contractuales', response.data)

    def test_period_full_clean_rejects_range_outside_contract_validity(self):
        mandato = self._create_active_mandato(codigo='MAND-101-PER-WIN', owner_rut='11111117-0')
        arrendatario = self._create_arrendatario(rut='22222227-3')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-101-PER-WIN')
        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contrato = Contrato.objects.get(pk=response.data['id'])

        starts_before = PeriodoContractual(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2025, 12, 1),
            fecha_fin=date(2026, 1, 31),
            monto_base=Decimal('100000.00'),
            moneda_base='CLP',
            tipo_periodo='fixture',
            origen_periodo='test',
        )
        ends_after = PeriodoContractual(
            contrato=contrato,
            numero_periodo=3,
            fecha_inicio=date(2026, 12, 1),
            fecha_fin=date(2027, 1, 31),
            monto_base=Decimal('100000.00'),
            moneda_base='CLP',
            tipo_periodo='fixture',
            origen_periodo='test',
        )

        with self.assertRaises(ValidationError) as start_error:
            starts_before.full_clean()
        self.assertIn('fecha_inicio', start_error.exception.message_dict)

        with self.assertRaises(ValidationError) as end_error:
            ends_after.full_clean()
        self.assertIn('fecha_fin', end_error.exception.message_dict)

    def test_period_full_clean_rejects_number_outside_chronological_order(self):
        mandato = self._create_active_mandato(codigo='MAND-101-PER-NUM-MODEL', owner_rut='11111117-0')
        arrendatario = self._create_arrendatario(rut='22222227-3')
        contrato = Contrato.objects.create(
            codigo_contrato='CTR-101-PER-NUM-MODEL',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
            politica_documental=self.contract_policy,
        )
        later_period = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 12, 31),
            monto_base=Decimal('100000.00'),
            moneda_base='CLP',
            tipo_periodo='renovacion',
            origen_periodo='test',
        )
        PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=2,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 6, 30),
            monto_base=Decimal('100000.00'),
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='test',
        )

        with self.assertRaises(ValidationError) as error:
            later_period.full_clean()
        self.assertIn('numero_periodo', error.exception.message_dict)

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

    def test_create_active_contract_with_common_expenses_requires_structured_service(self):
        mandato = self._create_active_mandato(codigo='MAND-GC-001', owner_rut='33333335-K')
        arrendatario = self._create_arrendatario(rut='44444446-0')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-GC-001')
        payload['tiene_gastos_comunes'] = True

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tiene_gastos_comunes', response.data)

    def test_create_active_contract_with_common_expenses_accepts_structured_service(self):
        mandato = self._create_active_mandato(codigo='MAND-GC-002', owner_rut='33333336-8')
        arrendatario = self._create_arrendatario(rut='44444447-9')
        ServicioPropiedad.objects.create(
            propiedad=mandato.propiedad,
            tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
            proveedor_nombre='Administracion Edificio',
            numero_cliente='GC-100',
            administrador_nombre='Administracion Edificio',
            evidencia_ref='gasto-comun-contrato-001',
            activo=True,
        )
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-GC-002')
        payload['tiene_gastos_comunes'] = True

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['tiene_gastos_comunes'])

    def test_existing_active_contract_rejects_common_expenses_without_structured_service(self):
        mandato = self._create_active_mandato(codigo='MAND-GC-003', owner_rut='33333337-6')
        arrendatario = self._create_arrendatario(rut='44444448-7')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-GC-003')
        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        contrato = Contrato.objects.get(codigo_contrato='CTR-GC-003')
        contrato.tiene_gastos_comunes = True

        with self.assertRaises(ValidationError) as error:
            contrato.full_clean()

        self.assertIn('tiene_gastos_comunes', error.exception.message_dict)

    def test_update_active_contract_rejects_common_expenses_without_structured_service(self):
        mandato = self._create_active_mandato(codigo='MAND-GC-004', owner_rut='33333338-4')
        arrendatario = self._create_arrendatario(rut='44444449-5')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-GC-004')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        update_response = self.client.patch(
            reverse('contratos-contrato-detail', args=[create_response.data['id']]),
            {'tiene_gastos_comunes': True},
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tiene_gastos_comunes', update_response.data)

    def test_active_contract_rejects_inactive_linked_property(self):
        mandato = self._create_active_mandato(codigo='MAND-102-INACT', owner_rut='33333334-1')
        vinculada = Propiedad.objects.create(
            direccion='Av Vinculada Inactiva',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='MAND-102-I',
            estado='inactiva',
            socio_owner=mandato.propietario_socio_owner,
        )
        arrendatario = self._create_arrendatario(rut='44444445-2')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-102-INACT')
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

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contrato_propiedades', response.data)

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

    def test_contract_property_full_clean_rejects_linked_property_with_active_contract(self):
        mandato_a = self._create_active_mandato(codigo='MAND-LINK-A', owner_rut='77777778-5')
        arrendatario_a = self._create_arrendatario(rut='88888889-6')
        first_payload = self._base_contract_payload(mandato_a, arrendatario_a, codigo='CTR-LINK-A')
        first_response = self.client.post(reverse('contratos-contrato-list'), first_payload, format='json')
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        propietario_b = self._create_socio('Prop MAND-LINK-B', '77777779-3')
        admin_company = mandato_a.administrador_empresa_owner
        propiedad_b = Propiedad.objects.create(
            direccion='Av MAND-LINK-B',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='MAND-LINK-B',
            estado='activa',
            socio_owner=propietario_b,
        )
        mandato_b = MandatoOperacion.objects.create(
            propiedad=propiedad_b,
            propietario_socio_owner=propietario_b,
            administrador_empresa_owner=admin_company,
            recaudador_empresa_owner=admin_company,
            cuenta_recaudadora=mandato_a.cuenta_recaudadora,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario_b = self._create_arrendatario(rut='88888890-K')
        second_payload = self._base_contract_payload(mandato_b, arrendatario_b, codigo='CTR-LINK-B')
        second_payload['contrato_propiedades'][0]['codigo_conciliacion_efectivo_snapshot'] = '789'
        second_response = self.client.post(reverse('contratos-contrato-list'), second_payload, format='json')
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)

        conflict = ContratoPropiedad(
            contrato=Contrato.objects.get(pk=second_response.data['id']),
            propiedad=mandato_a.propiedad,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='50.00',
            codigo_conciliacion_efectivo_snapshot='123',
        )

        with self.assertRaises(ValidationError):
            conflict.full_clean()

    def test_contract_property_full_clean_rejects_linked_property_with_different_effective_code(self):
        mandato = self._create_active_mandato(codigo='MAND-LINK-CODE', owner_rut='77777780-7')
        arrendatario = self._create_arrendatario(rut='88888891-8')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-LINK-CODE')
        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        linked_property = Propiedad.objects.create(
            direccion='Av Linked Code',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='LINK-CODE',
            estado='activa',
            socio_owner=mandato.propietario_socio_owner,
        )
        linked = ContratoPropiedad(
            contrato=Contrato.objects.get(pk=response.data['id']),
            propiedad=linked_property,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='50.00',
            codigo_conciliacion_efectivo_snapshot='999',
        )

        with self.assertRaises(ValidationError):
            linked.full_clean()

    def test_contract_property_full_clean_rejects_duplicate_primary_role(self):
        mandato = self._create_active_mandato(codigo='MAND-DUP-PRIMARY', owner_rut='11111111-1')
        arrendatario = self._create_arrendatario(rut='12345678-5')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-DUP-PRIMARY')
        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        other_property = Propiedad.objects.create(
            direccion='Av Duplicate Primary',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='DUP-PRIMARY',
            estado='activa',
            socio_owner=mandato.propietario_socio_owner,
        )
        duplicate_primary = ContratoPropiedad(
            contrato=Contrato.objects.get(pk=response.data['id']),
            propiedad=other_property,
            rol_en_contrato=RolContratoPropiedad.PRIMARY,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='123',
        )

        with self.assertRaises(ValidationError) as error:
            duplicate_primary.full_clean()
        self.assertIn('rol_en_contrato', error.exception.message_dict)

    def test_contract_property_full_clean_rejects_linked_role_without_primary(self):
        mandato = self._create_active_mandato(codigo='MAND-LINK-ONLY', owner_rut='11111111-1')
        arrendatario = self._create_arrendatario(rut='12345678-5')
        contrato = Contrato.objects.create(
            codigo_contrato='CTR-LINK-ONLY',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio=date(2026, 1, 1),
            fecha_fin_vigente=date(2026, 12, 31),
            dia_pago_mensual=5,
            estado=EstadoContrato.ACTIVE,
            politica_documental=self.contract_policy,
        )
        linked_only = ContratoPropiedad(
            contrato=contrato,
            propiedad=mandato.propiedad,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='123',
        )

        with self.assertRaises(ValidationError) as error:
            linked_only.full_clean()
        self.assertIn('rol_en_contrato', error.exception.message_dict)

    def test_contract_property_full_clean_rejects_more_than_principal_and_linked_pair(self):
        mandato = self._create_active_mandato(codigo='MAND-LINK-LIMIT', owner_rut='77777781-5')
        linked_a = Propiedad.objects.create(
            direccion='Av Linked Limit A',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='LINK-LIMIT-A',
            estado='activa',
            socio_owner=mandato.propietario_socio_owner,
        )
        arrendatario = self._create_arrendatario(rut='88888892-6')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-LINK-LIMIT')
        payload['contrato_propiedades'] = [
            {
                'propiedad_id': mandato.propiedad_id,
                'rol_en_contrato': 'principal',
                'porcentaje_distribucion_interna': '50.00',
                'codigo_conciliacion_efectivo_snapshot': '321',
            },
            {
                'propiedad_id': linked_a.id,
                'rol_en_contrato': 'vinculada',
                'porcentaje_distribucion_interna': '50.00',
                'codigo_conciliacion_efectivo_snapshot': '321',
            },
        ]
        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        linked_b = Propiedad.objects.create(
            direccion='Av Linked Limit B',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='LINK-LIMIT-B',
            estado='activa',
            socio_owner=mandato.propietario_socio_owner,
        )
        extra_link = ContratoPropiedad(
            contrato=Contrato.objects.get(pk=response.data['id']),
            propiedad=linked_b,
            rol_en_contrato=RolContratoPropiedad.LINKED,
            porcentaje_distribucion_interna='10.00',
            codigo_conciliacion_efectivo_snapshot='321',
        )

        with self.assertRaises(ValidationError):
            extra_link.full_clean()

    def test_contract_rejects_duplicate_effective_code_in_same_account_namespace(self):
        mandato_a = self._create_active_mandato(codigo='MAND-CODE-A', owner_rut='71717171-7')
        arrendatario_a = self._create_arrendatario(rut='72727272-4')
        first_payload = self._base_contract_payload(mandato_a, arrendatario_a, codigo='CTR-CODE-A')
        first_payload['contrato_propiedades'][0]['codigo_conciliacion_efectivo_snapshot'] = '456'
        first_response = self.client.post(reverse('contratos-contrato-list'), first_payload, format='json')
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        propietario_b = self._create_socio('Prop MAND-CODE-B', '73737373-1')
        admin_company = mandato_a.administrador_empresa_owner
        propiedad_b = Propiedad.objects.create(
            direccion='Av MAND-CODE-B',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='MAND-CODE-B',
            estado='activa',
            socio_owner=propietario_b,
        )
        mandato_b = MandatoOperacion.objects.create(
            propiedad=propiedad_b,
            propietario_socio_owner=propietario_b,
            administrador_empresa_owner=admin_company,
            recaudador_empresa_owner=admin_company,
            cuenta_recaudadora=mandato_a.cuenta_recaudadora,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario_b = self._create_arrendatario(rut='74747474-9')
        second_payload = self._base_contract_payload(mandato_b, arrendatario_b, codigo='CTR-CODE-B')
        second_payload['contrato_propiedades'][0]['codigo_conciliacion_efectivo_snapshot'] = '456'

        second_response = self.client.post(reverse('contratos-contrato-list'), second_payload, format='json')

        self.assertEqual(second_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contrato_propiedades', second_response.data)

    def test_contract_rejects_zero_effective_code(self):
        mandato = self._create_active_mandato(codigo='MAND-CODE-ZERO', owner_rut='75757575-6')
        arrendatario = self._create_arrendatario(rut='76767676-3')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-CODE-ZERO')
        payload['contrato_propiedades'][0]['codigo_conciliacion_efectivo_snapshot'] = '000'

        response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('contrato_propiedades', response.data)

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

    def test_future_contract_rejects_notice_with_executed_renewal_without_guided_resolution(self):
        mandato = self._create_active_mandato(codigo='MAND-106-REN-CONF', owner_rut='14141414-5')
        arrendatario = self._create_arrendatario(rut='15151515-2')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-REN-C')
        current_payload['fecha_fin_vigente'] = '2027-12-31'
        current_payload['periodos_contractuales'] = [
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 2,
                'fecha_inicio': '2027-01-01',
                'fecha_fin': '2027-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'renovacion_automatica',
            },
        ]
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        aviso_response = self.client.post(
            reverse('contratos-aviso-list'),
            {
                'contrato': current_response.data['id'],
                'fecha_efectiva': '2026-12-31',
                'causal': 'No renovacion con renovacion ya ejecutada',
                'estado': EstadoAvisoTermino.REGISTERED,
            },
            format='json',
        )
        self.assertEqual(aviso_response.status_code, status.HTTP_201_CREATED)

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-REN-F')
        future_payload['estado'] = EstadoContrato.FUTURE
        future_payload['fecha_inicio'] = '2027-01-01'
        future_payload['fecha_fin_vigente'] = '2027-12-31'
        future_payload['fecha_entrega'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_inicio'] = '2027-01-01'
        future_payload['periodos_contractuales'][0]['fecha_fin'] = '2027-12-31'

        future_response = self.client.post(reverse('contratos-contrato-list'), future_payload, format='json')
        self.assertEqual(future_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('resolucion guiada', str(future_response.data))

    def test_future_contract_succeeds_after_guided_renewal_conflict_resolution(self):
        mandato = self._create_active_mandato(codigo='MAND-106-REN-OK', owner_rut='14141414-6')
        arrendatario = self._create_arrendatario(rut='15151515-3')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-REN-OK-C')
        current_payload['fecha_fin_vigente'] = '2027-12-31'
        current_payload['periodos_contractuales'] = [
            {
                'numero_periodo': 1,
                'fecha_inicio': '2026-01-01',
                'fecha_fin': '2026-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'inicial',
                'origen_periodo': 'manual',
            },
            {
                'numero_periodo': 2,
                'fecha_inicio': '2027-01-01',
                'fecha_fin': '2027-12-31',
                'monto_base': '1000000.00',
                'moneda_base': 'CLP',
                'tipo_periodo': 'renovacion',
                'origen_periodo': 'renovacion_automatica',
            },
        ]
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        aviso_response = self.client.post(
            reverse('contratos-aviso-list'),
            {
                'contrato': current_response.data['id'],
                'fecha_efectiva': '2026-12-31',
                'causal': 'No renovacion con resolucion guiada',
                'estado': EstadoAvisoTermino.REGISTERED,
                'resolucion_conflicto_renovacion_ref': 'renewal-conflict-resolution-001',
                'resolucion_conflicto_renovacion_motivo': 'Resolucion guiada mantiene renovacion ejecutada y habilita contrato futuro trazado.',
            },
            format='json',
        )
        self.assertEqual(aviso_response.status_code, status.HTTP_201_CREATED)

        future_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-REN-OK-F')
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

    def test_early_termination_partial_month_requires_proration_decision(self):
        mandato = self._create_active_mandato(codigo='MAND-106-PR', owner_rut='14141410-6')
        arrendatario = self._create_arrendatario(rut='15151510-3')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-PR')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('contratos-contrato-detail', args=[create_response.data['id']]),
            {
                'estado': EstadoContrato.EARLY_TERMINATED,
                'fecha_fin_vigente': '2026-06-15',
                'periodos_contractuales': [
                    {
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-06-15',
                        'monto_base': '1000000.00',
                        'moneda_base': 'CLP',
                        'tipo_periodo': 'terminacion_anticipada',
                        'origen_periodo': 'decision_controlada',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('terminacion_anticipada_prorrata_ref', response.data)
        self.assertIn('terminacion_anticipada_prorrata_motivo', response.data)

    def test_early_termination_partial_month_records_proration_audit_event(self):
        mandato = self._create_active_mandato(codigo='MAND-106-PRA', owner_rut='14141411-4')
        arrendatario = self._create_arrendatario(rut='15151511-1')
        payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-106-PRA')
        create_response = self.client.post(reverse('contratos-contrato-list'), payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        response = self.client.patch(
            reverse('contratos-contrato-detail', args=[create_response.data['id']]),
            {
                'estado': EstadoContrato.EARLY_TERMINATED,
                'fecha_fin_vigente': '2026-06-15',
                'terminacion_anticipada_prorrata_ref': 'early-term-proration-act-001',
                'terminacion_anticipada_prorrata_motivo': 'Prorrata aprobada por termino anticipado controlado.',
                'periodos_contractuales': [
                    {
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-06-15',
                        'monto_base': '1000000.00',
                        'moneda_base': 'CLP',
                        'tipo_periodo': 'terminacion_anticipada',
                        'origen_periodo': 'decision_controlada',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['fecha_fin_vigente'], '2026-06-15')
        self.assertEqual(response.data['terminacion_anticipada_prorrata_ref'], 'early-term-proration-act-001')
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=EARLY_TERMINATION_PARTIAL_MONTH_EVENT_TYPE,
                entity_type='contrato',
                entity_id=str(create_response.data['id']),
            ).exists()
        )

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

    def test_notice_rejects_effective_date_after_contract_end(self):
        mandato = self._create_active_mandato(codigo='MAND-107-LATE', owner_rut='16161617-K')
        arrendatario = self._create_arrendatario(rut='17171718-7')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-107-LATE')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        aviso_response = self.client.post(
            reverse('contratos-aviso-list'),
            {
                'contrato': current_response.data['id'],
                'fecha_efectiva': '2027-01-31',
                'causal': 'No renovacion fuera de rango',
                'estado': EstadoAvisoTermino.REGISTERED,
            },
            format='json',
        )

        self.assertEqual(aviso_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_efectiva', aviso_response.data)

    def test_registered_notice_exposes_late_registration_alert(self):
        mandato = self._create_active_mandato(codigo='MAND-107-LATE-REG', owner_rut='16161618-8')
        arrendatario = self._create_arrendatario(rut='17171719-5')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-107-LATE-REG')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        aviso_response = self.client.post(
            reverse('contratos-aviso-list'),
            {
                'contrato': current_response.data['id'],
                'fecha_efectiva': '2026-12-31',
                'causal': 'No renovacion tardia',
                'estado': EstadoAvisoTermino.REGISTERED,
            },
            format='json',
        )
        self.assertEqual(aviso_response.status_code, status.HTTP_201_CREATED)

        AvisoTermino.objects.filter(pk=aviso_response.data['id']).update(
            created_at=timezone.make_aware(datetime(2026, 11, 2, 10, 0, 0))
        )

        detail_response = self.client.get(reverse('contratos-aviso-detail', args=[aviso_response.data['id']]))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_response.data['registrado_fuera_plazo'])
        self.assertTrue(detail_response.data['fecha_limite_registro_oportuno'].startswith('2026-11-01T23:59:59'))
        self.assertIn('fuera del plazo contractual', detail_response.data['alerta_registro_fuera_plazo'])

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

    def test_tenant_replacement_endpoint_creates_notice_future_contract_and_audit(self):
        mandato = self._create_active_mandato(codigo='MAND-TEN-REP', owner_rut='20202021-0')
        arrendatario = self._create_arrendatario(rut='21212122-9')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-TEN-REP-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)
        current_period = PeriodoContractual.objects.get(contrato_id=current_response.data['id'], numero_periodo=1)
        PagoMensual.objects.create(
            contrato_id=current_response.data['id'],
            periodo_contractual=current_period,
            mes=12,
            anio=2026,
            monto_facturable_clp=Decimal('1000000.00'),
            monto_calculado_clp=Decimal('1000000.00'),
            monto_efecto_codigo_efectivo_clp=Decimal('0.00'),
            fecha_vencimiento=date(2026, 12, 5),
            codigo_conciliacion_efectivo='123',
        )

        nuevo_arrendatario = self._create_arrendatario(rut='23232323-3')
        response = self.client.post(
            reverse('contratos-contrato-cambio-arrendatario', args=[current_response.data['id']]),
            {
                'arrendatario': nuevo_arrendatario.id,
                'codigo_contrato': 'CTR-TEN-REP-F',
                'fecha_inicio': '2027-01-01',
                'fecha_fin_vigente': '2027-12-31',
                'causal_aviso': 'Cambio de arrendatario acordado',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['aviso_termino']['fecha_efectiva'], '2026-12-31')
        self.assertEqual(response.data['contrato_nuevo']['codigo_contrato'], 'CTR-TEN-REP-F')
        self.assertEqual(response.data['contrato_nuevo']['estado'], EstadoContrato.FUTURE)
        self.assertEqual(response.data['contrato_nuevo']['arrendatario'], nuevo_arrendatario.id)

        current_contract = Contrato.objects.get(pk=current_response.data['id'])
        future_contract = Contrato.objects.get(codigo_contrato='CTR-TEN-REP-F')
        aviso = AvisoTermino.objects.get(contrato=current_contract)
        self.assertEqual(current_contract.arrendatario_id, arrendatario.id)
        self.assertEqual(future_contract.contrato_propiedades.count(), 1)
        self.assertEqual(future_contract.periodos_contractuales.get().origen_periodo, 'cambio_arrendatario')
        self.assertTrue(PagoMensual.objects.filter(contrato=current_contract, mes=12, anio=2026).exists())
        self.assertFalse(PagoMensual.objects.filter(contrato=future_contract).exists())
        self.assertTrue(
            AuditEvent.objects.filter(
                event_type=TENANT_REPLACEMENT_EVENT_TYPE,
                entity_type='contrato',
                entity_id=str(future_contract.pk),
                metadata__contrato_anterior_id=current_contract.pk,
                metadata__aviso_termino_id=aviso.pk,
                metadata__arrendatario_anterior_id=arrendatario.id,
                metadata__arrendatario_nuevo_id=nuevo_arrendatario.id,
            ).exists()
        )

    def test_tenant_replacement_endpoint_rejects_same_tenant(self):
        mandato = self._create_active_mandato(codigo='MAND-TEN-SAME', owner_rut='20202022-9')
        arrendatario = self._create_arrendatario(rut='21212123-7')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-TEN-SAME-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('contratos-contrato-cambio-arrendatario', args=[current_response.data['id']]),
            {
                'arrendatario': arrendatario.id,
                'codigo_contrato': 'CTR-TEN-SAME-F',
                'fecha_inicio': '2027-01-01',
                'fecha_fin_vigente': '2027-12-31',
                'causal_aviso': 'Cambio invalido con mismo arrendatario',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('arrendatario', response.data)

    def test_tenant_replacement_endpoint_requires_next_day_after_current_term(self):
        mandato = self._create_active_mandato(codigo='MAND-TEN-DATE', owner_rut='20202023-7')
        arrendatario = self._create_arrendatario(rut='21212124-5')
        current_payload = self._base_contract_payload(mandato, arrendatario, codigo='CTR-TEN-DATE-C')
        current_response = self.client.post(reverse('contratos-contrato-list'), current_payload, format='json')
        self.assertEqual(current_response.status_code, status.HTTP_201_CREATED)

        nuevo_arrendatario = self._create_arrendatario(rut='24242424-1')
        response = self.client.post(
            reverse('contratos-contrato-cambio-arrendatario', args=[current_response.data['id']]),
            {
                'arrendatario': nuevo_arrendatario.id,
                'codigo_contrato': 'CTR-TEN-DATE-F',
                'fecha_inicio': '2026-07-01',
                'fecha_fin_vigente': '2027-06-30',
                'causal_aviso': 'Cambio con fecha incompatible',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fecha_inicio', response.data)

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
