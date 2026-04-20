from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cobranza.models import PagoMensual
from cobranza.services import sync_payment_distribution
from contabilidad.models import ConfiguracionFiscalEmpresa, RegimenTributarioEmpresa
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import Role, Scope, UserScopeAssignment
from .scope_access import ScopeAccess, _coerce_scope_identifier, get_scope_access, scope_queryset_for_access


class ScopeFilteringAPITests(APITestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')

        self.company_a = self._create_active_company(
            nombre='Empresa A',
            rut='76.311.245-4',
            socio_ruts=('11.111.111-1', '22.222.222-2'),
        )
        self.company_b = self._create_active_company(
            nombre='Empresa B',
            rut='76.390.560-8',
            socio_ruts=('33.333.333-3', '44.444.444-4'),
        )

        self.context_a = self._create_operational_context(self.company_a, codigo='CMP-A', arr_rut='55.555.555-5')
        self.context_b = self._create_operational_context(self.company_b, codigo='CMP-B', arr_rut='66.666.666-6')

        self._create_fiscal_config(self.company_a)
        self._create_fiscal_config(self.company_b)

    def _create_active_company(self, *, nombre, rut, socio_ruts):
        socio_1 = Socio.objects.create(nombre=f'{nombre} Socio 1', rut=socio_ruts[0], activo=True)
        socio_2 = Socio.objects.create(nombre=f'{nombre} Socio 2', rut=socio_ruts[1], activo=True)
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

    def _create_operational_context(self, empresa, *, codigo, arr_rut):
        propiedad = Propiedad.objects.create(
            direccion=f'Av. {codigo} 100',
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
            nombre_razon_social=f'Arrendatario {codigo}',
            rut=arr_rut,
            email=f'{codigo.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Direccion {codigo}',
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
        periodo = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        payment = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pendiente',
            codigo_conciliacion_efectivo='111',
        )
        sync_payment_distribution(payment)
        return {
            'propiedad': propiedad,
            'cuenta': cuenta,
            'mandato': mandato,
            'arrendatario': arrendatario,
            'contrato': contrato,
        }

    def _create_fiscal_config(self, empresa):
        regimen, _ = RegimenTributarioEmpresa.objects.get_or_create(
            codigo_regimen='EmpresaContabilidadCompletaV1',
            defaults={'descripcion': 'Regimen canonico', 'estado': 'activa'},
        )
        return ConfiguracionFiscalEmpresa.objects.create(
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

    def _assign_company_scope(self, user, role, empresa):
        scope = Scope.objects.create(
            code=f'company-{empresa.id}',
            name=f'Empresa {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=user, role=role, scope=scope, is_primary=True)

    def test_operator_company_scope_limits_operational_and_contract_views(self):
        user = self.user_model.objects.create_user(
            username='operator-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self._assign_company_scope(user, self.operator_role, self.company_a)
        self.client.force_authenticate(user)

        cuentas = self.client.get(reverse('operacion-cuenta-list'))
        mandatos = self.client.get(reverse('operacion-mandato-list'))
        contratos = self.client.get(reverse('contratos-contrato-list'))
        dashboard = self.client.get(reverse('reporting-dashboard-operativo'))
        control_read = self.client.get(reverse('contabilidad-config-list'))

        self.assertEqual(cuentas.status_code, status.HTTP_200_OK)
        self.assertEqual(mandatos.status_code, status.HTTP_200_OK)
        self.assertEqual(contratos.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertEqual(control_read.status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(len(cuentas.data), 1)
        self.assertEqual(cuentas.data[0]['id'], self.context_a['cuenta'].id)
        self.assertEqual(len(mandatos.data), 1)
        self.assertEqual(mandatos.data[0]['id'], self.context_a['mandato'].id)
        self.assertEqual(len(contratos.data), 1)
        self.assertEqual(contratos.data[0]['id'], self.context_a['contrato'].id)
        self.assertEqual(dashboard.data['propiedades_activas'], 1)
        self.assertEqual(dashboard.data['contratos_vigentes'], 1)
        self.assertEqual(dashboard.data['pagos_pendientes'], 1)

    def test_reviewer_company_scope_limits_control_views_and_financial_summary(self):
        user = self.user_model.objects.create_user(
            username='reviewer-scope',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        self._assign_company_scope(user, self.reviewer_role, self.company_b)
        self.client.force_authenticate(user)

        configs = self.client.get(reverse('contabilidad-config-list'))
        financial = self.client.get(
            f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={self.company_b.id}"
        )
        dashboard = self.client.get(reverse('reporting-dashboard-operativo'))

        self.assertEqual(configs.status_code, status.HTTP_200_OK)
        self.assertEqual(len(configs.data), 1)
        self.assertEqual(configs.data[0]['empresa'], self.company_b.id)

        self.assertEqual(financial.status_code, status.HTTP_200_OK)
        self.assertEqual(financial.data['empresa_id'], self.company_b.id)
        self.assertEqual(financial.data['pagos_generados'], 1)
        self.assertEqual(financial.data['monto_facturable_total_clp'], '100000.00')
        self.assertEqual(dashboard.status_code, status.HTTP_403_FORBIDDEN)

    def test_company_scope_includes_operational_mandate_roles_without_ownership(self):
        admin_company = self._create_active_company(
            nombre='Administradora Operativa',
            rut='76.500.000-1',
            socio_ruts=('77.111.111-1', '77.222.222-2'),
        )
        owner_company = self._create_active_company(
            nombre='Propietaria Operativa',
            rut='76.500.000-2',
            socio_ruts=('88.111.111-1', '88.222.222-2'),
        )
        propiedad = Propiedad.objects.create(
            direccion='Av. Operativa 100',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad='OPS-001',
            estado='activa',
            empresa_owner=owner_company,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=admin_company,
            institucion='Banco Uno',
            numero_cuenta='ACC-OPS-001',
            tipo_cuenta='corriente',
            titular_nombre=admin_company.razon_social,
            titular_rut=admin_company.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=owner_company,
            administrador_empresa_owner=admin_company,
            recaudador_empresa_owner=admin_company,
            entidad_facturadora=owner_company,
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
            nombre_razon_social='Arrendatario Operativo',
            rut='99.111.111-1',
            email='operativo@example.com',
            telefono='999',
            domicilio_notificaciones='Direccion Operativa',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato='CTR-OPS-001',
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
        periodo = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        payment = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pendiente',
            codigo_conciliacion_efectivo='111',
        )
        sync_payment_distribution(payment)

        user = self.user_model.objects.create_user(
            username='operator-operational-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self._assign_company_scope(user, self.operator_role, admin_company)
        self.client.force_authenticate(user)

        cuentas = self.client.get(reverse('operacion-cuenta-list'))
        mandatos = self.client.get(reverse('operacion-mandato-list'))
        contratos = self.client.get(reverse('contratos-contrato-list'))
        dashboard = self.client.get(reverse('reporting-dashboard-operativo'))

        self.assertEqual(cuentas.status_code, status.HTTP_200_OK)
        self.assertEqual(mandatos.status_code, status.HTTP_200_OK)
        self.assertEqual(contratos.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in cuentas.data], [cuenta.id])
        self.assertEqual([item['id'] for item in mandatos.data], [mandato.id])
        self.assertEqual([item['id'] for item in contratos.data], [contrato.id])
        self.assertEqual(dashboard.data['propiedades_activas'], 1)
        self.assertEqual(dashboard.data['contratos_vigentes'], 1)
        self.assertEqual(dashboard.data['pagos_pendientes'], 1)

    def test_company_only_scope_filter_skips_property_and_bank_visibility_expansion(self):
        access = ScopeAccess(
            restricted=True,
            company_ids={self.company_a.id},
            property_ids=set(),
            bank_account_ids=set(),
        )

        with patch.object(Propiedad.objects, 'filter', side_effect=AssertionError('property expansion should not run')):
            with patch.object(CuentaRecaudadora.objects, 'filter', side_effect=AssertionError('bank expansion should not run')):
                queryset = scope_queryset_for_access(
                    ConfiguracionFiscalEmpresa.objects.all(),
                    access,
                    company_paths=('empresa_id',),
                )

        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().empresa_id, self.company_a.id)

    def test_global_scope_assignment_remains_unrestricted(self):
        user = self.user_model.objects.create_user(
            username='global-operator',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        global_scope = Scope.objects.create(
            code='global-backoffice',
            name='Backoffice completo',
            scope_type=Scope.ScopeType.GLOBAL,
            external_reference='backoffice',
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=user, role=self.operator_role, scope=global_scope, is_primary=True)

        access = get_scope_access(user)

        self.assertFalse(access.restricted)
        self.assertEqual(access.company_ids, set())
        self.assertEqual(access.property_ids, set())
        self.assertEqual(access.bank_account_ids, set())

    def test_scope_identifier_does_not_guess_from_malformed_code(self):
        scope = Scope(
            code='company-backup-2026-q1',
            name='Scope con codigo ambiguo',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference='',
            metadata={},
        )

        self.assertIsNone(_coerce_scope_identifier(scope))

    def test_operator_cannot_generate_payment_for_contract_outside_scope(self):
        user = self.user_model.objects.create_user(
            username='operator-bypass',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self._assign_company_scope(user, self.operator_role, self.company_a)
        self.client.force_authenticate(user)

        response = self.client.post(
            reverse('cobranza-pago-generate'),
            {
                'contrato_id': self.context_b['contrato'].id,
                'anio': 2026,
                'mes': 2,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_create_mandato_with_property_outside_scope(self):
        user = self.user_model.objects.create_user(
            username='operator-mandato-bypass',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self._assign_company_scope(user, self.operator_role, self.company_a)
        self.client.force_authenticate(user)

        response = self.client.post(
            reverse('operacion-mandato-list'),
            {
                'propiedad_id': self.context_b['propiedad'].id,
                'propietario_tipo': 'empresa',
                'propietario_id': self.company_b.id,
                'administrador_operativo_tipo': 'empresa',
                'administrador_operativo_id': self.company_b.id,
                'recaudador_tipo': 'empresa',
                'recaudador_id': self.company_b.id,
                'entidad_facturadora_id': self.company_b.id,
                'cuenta_recaudadora_id': self.context_b['cuenta'].id,
                'tipo_relacion_operativa': 'mandato_externo',
                'autoriza_recaudacion': True,
                'autoriza_facturacion': True,
                'autoriza_comunicacion': True,
                'vigencia_desde': '2026-01-01',
                'estado': 'activa',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_cannot_create_contract_with_mandato_outside_scope(self):
        user = self.user_model.objects.create_user(
            username='operator-contract-bypass',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self._assign_company_scope(user, self.operator_role, self.company_a)
        self.client.force_authenticate(user)

        response = self.client.post(
            reverse('contratos-contrato-list'),
            {
                'codigo_contrato': 'CTR-BYPASS',
                'mandato_operacion': self.context_b['mandato'].id,
                'arrendatario': self.context_a['arrendatario'].id,
                'fecha_inicio': '2026-02-01',
                'fecha_fin_vigente': '2026-12-31',
                'fecha_entrega': '2026-02-01',
                'dia_pago_mensual': 5,
                'plazo_notificacion_termino_dias': 60,
                'dias_prealerta_admin': 90,
                'estado': 'vigente',
                'tiene_tramos': False,
                'tiene_gastos_comunes': False,
                'contrato_propiedades': [
                    {
                        'propiedad_id': self.context_b['propiedad'].id,
                        'rol_en_contrato': 'principal',
                        'porcentaje_distribucion_interna': '100.00',
                        'codigo_conciliacion_efectivo_snapshot': '111',
                    }
                ],
                'periodos_contractuales': [
                    {
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-02-01',
                        'fecha_fin': '2026-12-31',
                        'monto_base': '100000.00',
                        'moneda_base': 'CLP',
                        'tipo_periodo': 'inicial',
                        'origen_periodo': 'manual',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
