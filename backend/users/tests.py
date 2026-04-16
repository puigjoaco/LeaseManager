from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from contabilidad.models import ConfiguracionFiscalEmpresa, RegimenTributarioEmpresa
from patrimonio.models import Empresa, ParticipacionPatrimonial, Socio


class UserAuthAPITests(APITestCase):
    def _create_active_company(self, *, nombre='AuthCo', rut='76000111-1'):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=f'{rut[:-2]}1-1', activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=f'{rut[:-2]}2-2', activo=True)
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

    def test_login_returns_overview_bootstrap_for_admin(self):
        user = get_user_model().objects.create_user(
            username='admin-bootstrap',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('overview', response.data['bootstrap'])
        self.assertIn('dashboard', response.data['bootstrap']['overview'])
        self.assertNotIn('manual_summary', response.data['bootstrap']['overview'])

    def test_login_returns_control_bootstrap_for_reviewer(self):
        user = get_user_model().objects.create_user(
            username='reviewer-bootstrap',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        empresa = self._create_active_company(nombre='ReviewerAuthCo', rut='76000112-2')
        regimen, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regimen,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )

        response = self.client.post(
            reverse('login'),
            {'username': user.username, 'password': 'secret123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bootstrap', response.data)
        self.assertIn('control', response.data['bootstrap'])
        self.assertEqual(len(response.data['bootstrap']['control']['configuraciones_fiscales']), 1)
