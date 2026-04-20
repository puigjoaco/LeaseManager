from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import ManualResolution
from canales.models import CanalMensajeria, MensajeSaliente
from cobranza.models import EstadoCuentaArrendatario, PagoMensual
from cobranza.services import sync_payment_distribution
from conciliacion.models import ConexionBancaria, IngresoDesconocido, MovimientoBancarioImportado
from contabilidad.models import BalanceComprobacion, CierreMensualContable, EventoContable, LibroDiario, LibroMayor, ObligacionTributariaMensual
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from sii.models import CapacidadTributariaSII, DDJJPreparacionAnual, DTEEmitido, F22PreparacionAnual, ProcesoRentaAnual
from core.models import Role, Scope, UserScopeAssignment


class ReportingAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='reporting',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _create_context(self, codigo='RPT', owner_kind='socio', with_facturadora=False):
        codigo_num = sum(ord(char) for char in codigo)
        socio = Socio.objects.create(
            nombre=f'Socio {codigo}',
            rut=f'{11000000 + codigo_num}-1',
            email=f'socio-{codigo.lower()}@example.com',
        )
        empresa = Empresa.objects.create(razon_social=f'Empresa {codigo}', rut=f'{22000000 + codigo_num}-2', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=empresa,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            codigo_propiedad=f'{codigo}-001',
            direccion=f'Av {codigo} 123',
            comuna='Santiago',
            region='RM',
            tipo_inmueble='local',
            estado='activa',
            empresa_owner=empresa if owner_kind == 'empresa' else None,
            socio_owner=socio if owner_kind == 'socio' else None,
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
            propietario_empresa_owner=empresa if owner_kind == 'empresa' else None,
            propietario_socio_owner=socio if owner_kind == 'socio' else None,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa if with_facturadora else None,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=with_facturadora,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut=f'{33000000 + codigo_num}-3',
            email=f'tenant-{codigo.lower()}@example.com',
            telefono='+56912345678',
            domicilio_notificaciones='Dir',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'{codigo}-CTR',
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
        return socio, empresa, propiedad, cuenta, contrato, periodo

    def _create_scoped_reviewer_client(self, empresa):
        reviewer = get_user_model().objects.create_user(
            username=f'reviewer-{empresa.id}',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        reviewer_role, _ = Role.objects.get_or_create(
            code='RevisorFiscalExterno',
            defaults={'name': 'Revisor fiscal externo'},
        )
        scope = Scope.objects.create(
            code=f'company-{empresa.id}',
            name=f'Empresa {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=reviewer, role=reviewer_role, scope=scope, is_primary=True)

        reviewer_client = self.client_class()
        reviewer_client.force_authenticate(reviewer)
        return reviewer_client

    def _create_scoped_operator_client(self, empresa):
        operator = get_user_model().objects.create_user(
            username=f'operator-{empresa.id}',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        operator_role, _ = Role.objects.get_or_create(
            code='OperadorDeCartera',
            defaults={'name': 'Operador de cartera'},
        )
        scope = Scope.objects.create(
            code=f'company-{empresa.id}',
            name=f'Empresa {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=operator, role=operator_role, scope=scope, is_primary=True)

        operator_client = self.client_class()
        operator_client.force_authenticate(operator)
        return operator_client

    def _create_manual_resolution_for_cuenta(self, cuenta, *, suffix='manual'):
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref=f'cred-{suffix}-{cuenta.id}',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='cargo',
            monto='45000.00',
            descripcion_origen=f'Movimiento {suffix}',
            estado_conciliacion='pendiente_revision',
        )
        return ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.id),
            summary=f'Movimiento {suffix} requiere clasificacion manual',
        )

    def test_auth_is_required_for_reporting_endpoints(self):
        client = self.client_class()
        urls = [
            reverse('reporting-dashboard-operativo'),
            f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1",
            f"{reverse('reporting-libros-periodo')}?empresa_id=1&periodo=2026-01",
            f"{reverse('reporting-tributario-anual')}?anio_tributario=2027",
            reverse('reporting-socio-resumen', args=[1]),
        ]
        for url in urls:
            response = client.get(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_operational_dashboard_summarizes_cross_module_counts(self):
        _, empresa, _, cuenta, contrato, periodo = self._create_context('DASH')
        PagoMensual.objects.create(
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
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-dash',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='50000.00',
            descripcion_origen='Ingreso',
            estado_conciliacion='ingreso_desconocido',
        )
        IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto='50000.00',
            fecha_movimiento='2026-01-08',
            descripcion_origen='Ingreso',
            estado='pendiente_revision',
        )
        CanalMensajeria.objects.create(canal='email', provider_key='gmail_api', estado_gate='condicionado')
        MensajeSaliente.objects.create(
            canal='email',
            canal_mensajeria=CanalMensajeria.objects.first(),
            contrato=contrato,
            arrendatario=contrato.arrendatario,
            destinatario='x@y.com',
            estado='bloqueado',
            usuario=self.user,
        )

        response = self.client.get(reverse('reporting-dashboard-operativo'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['socios_total'], 1)
        self.assertEqual(response.data['empresas_total'], 1)
        self.assertEqual(response.data['comunidades_total'], 0)
        self.assertEqual(response.data['propiedades_total'], 1)
        self.assertEqual(response.data['propiedades_activas'], 1)
        self.assertEqual(response.data['cuentas_total'], 1)
        self.assertEqual(response.data['identidades_total'], 0)
        self.assertEqual(response.data['mandatos_total'], 1)
        self.assertEqual(response.data['contratos_vigentes'], 1)
        self.assertEqual(response.data['pagos_pendientes'], 1)
        self.assertEqual(response.data['ingresos_desconocidos_abiertos'], 1)
        self.assertEqual(response.data['mensajes_bloqueados'], 1)

    def test_operational_dashboard_refresh_bypasses_cached_summary(self):
        self._create_context('CACHE1')

        initial = self.client.get(f"{reverse('reporting-dashboard-operativo')}?mode=summary")
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(initial.data['propiedades_activas'], 1)

        self._create_context('CACHE2')

        cached = self.client.get(f"{reverse('reporting-dashboard-operativo')}?mode=summary")
        self.assertEqual(cached.status_code, status.HTTP_200_OK)
        self.assertEqual(cached.data['propiedades_activas'], 1)

        refreshed = self.client.get(f"{reverse('reporting-dashboard-operativo')}?mode=summary&refresh=1")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertEqual(refreshed.data['propiedades_activas'], 2)

    def test_scoped_operator_dashboard_and_manual_summary_include_in_scope_resolutions(self):
        _, empresa, _, cuenta, _, _ = self._create_context('MANSCOPE', owner_kind='empresa')
        self._create_manual_resolution_for_cuenta(cuenta, suffix='in-scope')
        operator_client = self._create_scoped_operator_client(empresa)

        dashboard = operator_client.get(reverse('reporting-dashboard-operativo'))
        summary = operator_client.get(reverse('reporting-manual-resolutions-summary'))

        self.assertEqual(dashboard.status_code, status.HTTP_200_OK)
        self.assertEqual(dashboard.data['resoluciones_manuales_abiertas'], 1)
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertEqual(summary.data['total'], 1)
        self.assertEqual(summary.data['categorias'], [{'category': 'conciliacion.movimiento_cargo', 'total': 1}])

    def test_financial_monthly_summary_aggregates_payments_events_and_obligations(self):
        _, empresa, _, _, contrato, periodo = self._create_context('FIN', owner_kind='empresa', with_facturadora=True)
        pago = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100111.00',
            monto_pagado_clp='100111.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pagado',
            codigo_conciliacion_efectivo='111',
        )
        sync_payment_distribution(pago)
        EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='1',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100111.00',
            payload_resumen={},
            idempotency_key='rep-fin-1',
            estado_contable='contabilizado',
        )
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100111.00',
            monto_calculado='10011.10',
            estado_preparacion='preparado',
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )
        capacidad = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='DTEEmision',
            certificado_ref='cert-1',
            ambiente='certificacion',
            estado_gate='condicionado',
        )
        DTEEmitido.objects.create(
            empresa=empresa,
            capacidad_tributaria=capacidad,
            contrato=contrato,
            pago_mensual=pago,
            distribucion_cobro_mensual=pago.distribuciones_cobro.get(requiere_dte=True),
            arrendatario=contrato.arrendatario,
            tipo_dte='34',
            monto_neto_clp='100000.00',
            fecha_emision='2026-01-10',
            estado_dte='borrador',
        )
        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['eventos_contables_posteados'], 1)
        self.assertEqual(len(response.data['obligaciones']), 1)
        self.assertEqual(len(response.data['cierres']), 1)

    def test_partner_summary_returns_shares_and_direct_properties(self):
        socio, _, _, _, contrato, _ = self._create_context('PARTNER')
        EstadoCuentaArrendatario.objects.create(arrendatario=contrato.arrendatario, resumen_operativo={})
        response = self.client.get(reverse('reporting-socio-resumen', args=[socio.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['socio']['id'], socio.id)
        self.assertEqual(len(response.data['participaciones_empresas']), 1)
        self.assertEqual(len(response.data['propiedades_directas']), 1)
        self.assertEqual(response.data['estados_cuenta_relacionados'], 1)

    def test_partner_role_can_only_access_own_summary(self):
        socio_1, _, _, _, contrato_1, _ = self._create_context('PARTNEROWN1')
        socio_2, _, _, _, contrato_2, _ = self._create_context('PARTNEROWN2')
        EstadoCuentaArrendatario.objects.create(arrendatario=contrato_1.arrendatario, resumen_operativo={})
        EstadoCuentaArrendatario.objects.create(arrendatario=contrato_2.arrendatario, resumen_operativo={})

        user_model = get_user_model()
        partner_user = user_model.objects.create_user(
            username='reporting-partner',
            password='secret123',
            default_role_code='Socio',
            metadata={'socio_id': socio_1.id},
        )
        partner_client = self.client_class()
        partner_client.force_authenticate(partner_user)

        own_response = partner_client.get(reverse('reporting-socio-resumen', args=[socio_1.id]))
        other_response = partner_client.get(reverse('reporting-socio-resumen', args=[socio_2.id]))

        self.assertEqual(own_response.status_code, status.HTTP_200_OK)
        self.assertEqual(own_response.data['socio']['id'], socio_1.id)
        self.assertEqual(other_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_scoped_reviewer_cannot_access_partner_summary_outside_scope(self):
        socio_a, empresa_a, _, _, contrato_a, _ = self._create_context('PARTNERSCOPEA', owner_kind='empresa', with_facturadora=True)
        socio_b, _, _, _, contrato_b, _ = self._create_context('PARTNERSCOPEB', owner_kind='empresa', with_facturadora=True)
        EstadoCuentaArrendatario.objects.create(arrendatario=contrato_a.arrendatario, resumen_operativo={})
        EstadoCuentaArrendatario.objects.create(arrendatario=contrato_b.arrendatario, resumen_operativo={})

        user_model = get_user_model()
        reviewer_user = user_model.objects.create_user(
            username='reporting-reviewer-scoped',
            password='secret123',
            default_role_code='Socio',
        )
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        company_scope = Scope.objects.create(
            code=f'company-{empresa_a.id}',
            name=f'Empresa {empresa_a.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa_a.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=reviewer_user, role=reviewer_role, scope=company_scope, is_primary=True)
        reviewer_client = self.client_class()
        reviewer_client.force_authenticate(reviewer_user)

        in_scope_response = reviewer_client.get(reverse('reporting-socio-resumen', args=[socio_a.id]))
        out_of_scope_response = reviewer_client.get(reverse('reporting-socio-resumen', args=[socio_b.id]))

        self.assertEqual(in_scope_response.status_code, status.HTTP_200_OK)
        self.assertEqual(out_of_scope_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_financial_monthly_summary_returns_400_when_required_params_are_missing_or_invalid(self):
        missing = self.client.get(reverse('reporting-financiero-mensual'))
        invalid = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=abc&empresa_id=nope")

        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.data['anio'], 'Este parametro es obligatorio.')
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid.data['mes'], 'Debe ser un entero valido.')

    def test_period_books_and_annual_summary_return_400_for_invalid_query_params(self):
        books_missing = self.client.get(reverse('reporting-libros-periodo'))
        annual_invalid = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=x&empresa_id=y")

        self.assertEqual(books_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(books_missing.data['empresa_id'], 'Este parametro es obligatorio.')
        self.assertEqual(annual_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(annual_invalid.data['anio_tributario'], 'Debe ser un entero valido.')

    def test_partner_summary_returns_404_when_partner_does_not_exist(self):
        socio, _, _, _, _, _ = self._create_context('PARTNER404')
        response = self.client.get(reverse('reporting-socio-resumen', args=[socio.id + 9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_period_books_summary_returns_snapshot_payloads(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKS')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='preparado', resumen={'asientos': []})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='preparado', resumen={'cuentas': []})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='preparado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['libro_diario']['estado_snapshot'], 'preparado')
        self.assertTrue(response.data['balance_comprobacion']['resumen']['cuadrado'])

    def test_annual_tax_summary_returns_process_ddjj_and_f22(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUAL')
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'total_obligaciones': 12},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'ddjj_habilitadas': ['1887']},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'base': '100.00'},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['procesos_renta']), 1)
        self.assertEqual(len(response.data['ddjj_preparadas']), 1)
        self.assertEqual(len(response.data['f22_preparados']), 1)

    def test_migration_manual_resolution_summary_returns_category_breakdown(self):
        ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-1',
            summary='Propiedad requiere owner',
            metadata={
                'codigo': 46,
                'direccion': 'Av. Santa Maria 9500 Dpto 1014',
                'candidate_owner_model': 'comunidad',
                'participaciones_count': 6,
                'total_pct': 100.0,
                'blocked_contract_legacy_ids': ['ctr-1'],
                'socios': [{'socio_legacy_id': 'soc-1', 'socio_nombre': 'Socio Uno', 'porcentaje': '16.66'}],
            },
        )
        ManualResolution.objects.create(
            category='migration.arrendatario.invalid_rut',
            scope_type='legacy_arrendatario',
            scope_reference='arr-1',
            summary='Arrendatario sin rut',
        )

        response = self.client.get(reverse('reporting-migration-manual-resolutions'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(len(response.data['categorias']), 2)
        self.assertEqual(len(response.data['propiedades_owner_manual_required']), 1)
        self.assertEqual(
            response.data['propiedades_owner_manual_required'][0]['candidate_owner_model'],
            'comunidad',
        )

    def test_manual_resolution_summary_returns_all_open_categories(self):
        ManualResolution.objects.create(
            category='ops.retry_needed',
            scope_type='operacion',
            scope_reference='op-1',
            summary='Requiere reintento manual',
        )
        ManualResolution.objects.create(
            category='cobranza.assignment_required',
            scope_type='pago',
            scope_reference='pay-1',
            summary='Requiere asignación manual',
        )

        response = self.client.get(reverse('reporting-manual-resolutions-summary'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(len(response.data['categorias']), 2)

    def test_scoped_reporting_reference_options_redact_socio_pii_and_skip_out_of_scope_socios(self):
        socio_a, empresa_a, _, _, _, _ = self._create_context('SCOPEA', owner_kind='empresa')
        socio_b, _, _, _, _, _ = self._create_context('SCOPEB', owner_kind='empresa')
        reviewer_client = self._create_scoped_reviewer_client(empresa_a)

        response = reviewer_client.get(reverse('reporting-reference-options'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data['socios']], [socio_a.id])
        self.assertEqual(response.data['socios'][0]['nombre'], socio_a.nombre)
        self.assertEqual(response.data['socios'][0]['rut'], '')
        self.assertEqual(response.data['socios'][0]['email'], '')
        self.assertEqual(response.data['socios'][0]['telefono'], '')
        self.assertEqual(response.data['socios'][0]['domicilio'], '')
        self.assertNotIn(socio_b.id, [item['id'] for item in response.data['socios']])
