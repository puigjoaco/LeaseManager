import json
from datetime import timedelta

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditEvent, ManualResolution
from canales.models import CanalMensajeria, EstadoMensajeSaliente, MensajeSaliente
from cobranza.models import EstadoCuentaArrendatario, GarantiaContractual, PagoMensual
from cobranza.services import sync_payment_distribution
from conciliacion.models import (
    ConexionBancaria,
    CuadraturaBancaria,
    EstadoCuadraturaBancaria,
    IngresoDesconocido,
    MovimientoBancarioImportado,
)
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MovimientoAsiento,
    NaturalezaCuenta,
    ObligacionTributariaMensual,
    TipoMovimientoAsiento,
)
from contabilidad.services import ensure_default_regime
from contratos.models import (
    Arrendatario,
    AvisoTermino,
    Contrato,
    ContratoPropiedad,
    EstadoAvisoTermino,
    PeriodoContractual,
)
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble
from sii.models import (
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DTEEmitido,
    F22PreparacionAnual,
    F29PreparacionMensual,
    ProcesoRentaAnual,
)
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
            codigo_propiedad=f'P{codigo_num}-001',
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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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

    def _activate_fiscal_config(self, empresa):
        return ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            tasa_ppm_vigente='10.00',
            aplica_ppm=True,
            ddjj_habilitadas=['1887'],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )

    def _create_annual_reporting_process(self, empresa, *, anio_tributario=2027):
        return ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=anio_tributario,
            estado=EstadoPreparacionTributaria.PREPARED,
            resumen_anual={
                'fiscal_year': anio_tributario - 1,
                'obligaciones': [{'mes': 1}],
                'total_obligaciones': 12,
            },
        )

    def _create_annual_ddjj(self, empresa, process, *, suffix='default', resumen_paquete=None):
        if resumen_paquete is None:
            resumen_paquete = {
                'ddjj_habilitadas': ['1887'],
                'resumen_anual': {'fiscal_year': process.anio_tributario - 1},
            }
        return DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.DDJJ_PREPARACION,
                certificado_ref=f'cert-ddjj-{suffix}',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=process.anio_tributario,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete=resumen_paquete,
        )

    def _create_annual_f22(self, empresa, process, *, suffix='default', resumen_f22=None):
        if resumen_f22 is None:
            resumen_f22 = {
                'base': '100.00',
                'resumen_anual': {'fiscal_year': process.anio_tributario - 1},
            }
        return F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.F22_PREPARACION,
                certificado_ref=f'cert-f22-{suffix}',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=process.anio_tributario,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22=resumen_f22,
        )

    def _complete_bank_support_manifest(self, empresa, *, fiscal_year=2026, tax_year=2027):
        return {
            'schema_version': 'company-bank-support-coverage-manifest.v1',
            'company_ref': f'company-{empresa.id}',
            'fiscal_year': fiscal_year,
            'tax_year': tax_year,
            'required_operations': [
                {
                    'operation_ref': 'leasing-op-001',
                    'label_ref': 'leasing-main-contract',
                    'required_categories': [
                        'contract_or_schedule',
                        'payment_history',
                        'invoice_or_tax_document_bundle',
                    ],
                }
            ],
            'attachments': [
                {'operation_ref': 'leasing-op-001', 'category': 'contract_or_schedule', 'evidence_ref': 'contract-schedule-hash'},
                {'operation_ref': 'leasing-op-001', 'category': 'payment_history', 'evidence_ref': 'payment-history-hash'},
                {
                    'operation_ref': 'leasing-op-001',
                    'category': 'invoice_or_tax_document_bundle',
                    'evidence_ref': 'invoice-bundle-hash',
                },
            ],
            'confirmations': [{'statement_ref': 'bank-confirmation-redacted', 'statement_strength': 'verified_complete'}],
        }

    def _create_posted_asiento(self, event, *, amount='100111.00', with_movements=True, hash_mode='valid'):
        asiento = AsientoContable.objects.create(
            evento_contable=event,
            fecha_contable='2026-01-10',
            periodo_contable='2026-01',
            estado=EstadoAsientoContable.POSTED,
            debe_total=amount,
            haber_total=amount,
        )
        if with_movements:
            cuenta_debe = CuentaContable.objects.create(
                empresa=event.empresa,
                plan_cuentas_version='test',
                codigo=f'1-{event.id}',
                nombre='Caja test',
                naturaleza=NaturalezaCuenta.DEBIT,
                nivel=1,
            )
            cuenta_haber = CuentaContable.objects.create(
                empresa=event.empresa,
                plan_cuentas_version='test',
                codigo=f'4-{event.id}',
                nombre='Ingreso test',
                naturaleza=NaturalezaCuenta.CREDIT,
                nivel=1,
            )
            MovimientoAsiento.objects.create(
                asiento_contable=asiento,
                cuenta_contable=cuenta_debe,
                tipo_movimiento=TipoMovimientoAsiento.DEBIT,
                monto=amount,
                glosa='Debe test local',
            )
            MovimientoAsiento.objects.create(
                asiento_contable=asiento,
                cuenta_contable=cuenta_haber,
                tipo_movimiento=TipoMovimientoAsiento.CREDIT,
                monto=amount,
                glosa='Haber test local',
            )
        if hash_mode == 'valid':
            asiento.set_hash_integridad()
            asiento.save(update_fields=['hash_integridad'])
        elif hash_mode == 'stale':
            asiento.hash_integridad = '0' * 64
            asiento.save(update_fields=['hash_integridad'])
        elif hash_mode != 'missing':
            raise ValueError(f'Unsupported hash mode: {hash_mode}')
        return asiento

    def _create_financial_summary_event_with_close(self, codigo, *, origin_id, idempotency_key):
        _, empresa, _, _, contrato, periodo = self._create_context(
            codigo,
            owner_kind='empresa',
            with_facturadora=True,
        )
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
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id=origin_id,
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100111.00',
            payload_resumen={},
            idempotency_key=idempotency_key,
            estado_contable='contabilizado',
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )
        return empresa, event

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
        review_response = client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': 1, 'fiscal_year': 2026, 'bank_support_manifest': {}},
            format='json',
        )
        self.assertEqual(review_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_operational_dashboard_summarizes_cross_module_counts(self):
        _, empresa, _, cuenta, contrato, periodo = self._create_context('DASH')
        contrato.fecha_fin_vigente = timezone.localdate() + timedelta(days=30)
        contrato.save(update_fields=['fecha_fin_vigente', 'updated_at'])
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
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura='2026-01-31',
            saldo_sistema_clp='100000.00',
            saldo_banco_clp='90000.00',
            diferencia_clp='-10000.00',
            estado=EstadoCuadraturaBancaria.OPEN_DIFFERENCE,
            evidencia_cuadratura_ref='bank-square-evidence-dash',
            responsable_ref='ops-bank-square-dash',
            rationale='Diferencia en revision operativa.',
        )
        AvisoTermino.objects.create(
            contrato=contrato,
            fecha_efectiva=contrato.fecha_fin_vigente,
            causal='termino programado',
            estado=EstadoAvisoTermino.REGISTERED,
            registrado_por=self.user,
        )
        GarantiaContractual.objects.create(
            contrato=contrato,
            monto_pactado='100000.00',
            monto_recibido='50000.00',
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.PREPARED,
        )
        canal = CanalMensajeria.objects.create(canal='email', provider_key='gmail_api', estado_gate='condicionado')
        MensajeSaliente.objects.create(
            canal='email',
            canal_mensajeria=canal,
            contrato=contrato,
            arrendatario=contrato.arrendatario,
            destinatario='x@y.com',
            estado='bloqueado',
            usuario=self.user,
        )
        MensajeSaliente.objects.create(
            canal='email',
            canal_mensajeria=canal,
            contrato=contrato,
            arrendatario=contrato.arrendatario,
            destinatario='failed@example.com',
            estado=EstadoMensajeSaliente.FAILED,
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
        self.assertEqual(response.data['movimientos_sin_clasificar'], 1)
        self.assertEqual(response.data['diferencias_banco_sistema'], 1)
        self.assertEqual(response.data['contratos_por_vencer'], 1)
        self.assertEqual(response.data['avisos_termino_registrados'], 1)
        self.assertEqual(response.data['garantias_incompletas'], 1)
        self.assertEqual(response.data['fallas_integracion'], 1)
        self.assertEqual(response.data['cierres_bloqueados'], 1)
        self.assertEqual(response.data['ingresos_desconocidos_abiertos'], 1)
        self.assertEqual(response.data['mensajes_bloqueados'], 1)

        summary_response = self.client.get(f"{reverse('reporting-dashboard-operativo')}?mode=summary&refresh=1")
        self.assertEqual(summary_response.status_code, status.HTTP_200_OK)
        self.assertEqual(summary_response.data['movimientos_sin_clasificar'], 1)
        self.assertEqual(summary_response.data['diferencias_banco_sistema'], 1)
        self.assertEqual(summary_response.data['contratos_por_vencer'], 1)
        self.assertEqual(summary_response.data['garantias_incompletas'], 1)
        self.assertEqual(summary_response.data['fallas_integracion'], 1)
        self.assertEqual(summary_response.data['cierres_bloqueados'], 1)
        self.assertNotIn('socios_total', summary_response.data)

    def test_operational_dashboard_refresh_bypasses_cached_summary(self):
        self._create_context('CACHE1')

        initial = self.client.get(f"{reverse('reporting-dashboard-operativo')}?mode=summary")
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(initial.data['propiedades_activas'], 1)

        self._create_context('CACHE2')

        cached = self.client.get(f"{reverse('reporting-dashboard-operativo')}?mode=summary")
        self.assertEqual(cached.status_code, status.HTTP_200_OK)
        self.assertEqual(cached.data['propiedades_activas'], 1)

        refreshed = self.client.get(
            reverse('reporting-dashboard-operativo'),
            {'mode': ' summary ', 'refresh': ' 1 '},
        )
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
        self._activate_fiscal_config(empresa)
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
        event = EventoContable.objects.create(
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
        self._create_posted_asiento(event)
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100111.00',
            monto_calculado='10011.10',
            estado_preparacion='preparado',
        )
        close = CierreMensualContable.objects.create(
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
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            certificado_ref='cert-f29-1',
            ambiente='certificacion',
            estado_gate='condicionado',
        )
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'periodo': '2026-01', 'obligaciones': ['PPM']},
        )
        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertIn('CierreMensualContable', response.data['trazabilidad']['fuentes'])
        self.assertIn('F29PreparacionMensual', response.data['trazabilidad']['fuentes'])
        self.assertEqual(response.data['eventos_contables_posteados'], 1)
        self.assertEqual(len(response.data['obligaciones']), 1)
        self.assertEqual(len(response.data['cierres']), 1)
        self.assertEqual(response.data['control_cierre_mensual'][0]['estado_control'], 'listo')
        self.assertEqual(response.data['control_cierre_mensual'][0]['f29_estado'], 'preparado')
        self.assertEqual(response.data['control_cierre_mensual'][0]['bloqueadores_periodo'], [])

    def test_financial_monthly_summary_flags_unresolved_bank_movements_in_close_control(self):
        _, empresa, _, cuenta, contrato, periodo = self._create_context('FINBANK', owner_kind='empresa', with_facturadora=True)
        self._activate_fiscal_config(empresa)
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
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='bank-control-1',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100111.00',
            payload_resumen={},
            idempotency_key='rep-fin-bank-control-1',
            estado_contable='contabilizado',
        )
        self._create_posted_asiento(event)
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100111.00',
            monto_calculado='10011.10',
            estado_preparacion='preparado',
        )
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )
        f29_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key='F29Preparacion',
            certificado_ref='cert-f29-bank-control',
            ambiente='certificacion',
            estado_gate='condicionado',
        )
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f29_capability,
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion='preparado',
            resumen_formulario={'periodo': '2026-01', 'obligaciones': ['PPM']},
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-bank-control',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=conexion,
            fecha_movimiento='2026-01-08',
            tipo_movimiento='abono',
            monto='50000.00',
            descripcion_origen='Ingreso sin resolver para control mensual',
            estado_conciliacion='ingreso_desconocido',
        )
        IngresoDesconocido.objects.create(
            movimiento_bancario=movimiento,
            cuenta_recaudadora=cuenta,
            monto='50000.00',
            fecha_movimiento='2026-01-08',
            descripcion_origen='Ingreso sin resolver para control mensual',
            estado='pendiente_revision',
        )
        CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura='2026-01-31',
            saldo_sistema_clp='50000.00',
            saldo_banco_clp='50000.00',
            diferencia_clp='0.00',
            estado=EstadoCuadraturaBancaria.SQUARED,
            evidencia_cuadratura_ref='bank-square-evidence-control',
            responsable_ref='ops-bank-square-control',
            rationale='Cuadratura controlada para test local.',
        )

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        control = response.data['control_cierre_mensual'][0]
        self.assertEqual(control['estado_control'], 'bloqueado')
        self.assertTrue(control['cierre_contable_aprobado'])
        self.assertTrue(control['banco_cuadrado'])
        self.assertEqual(control['movimientos_bancarios_sin_resolver'], 1)
        self.assertEqual(control['bloqueadores_periodo'], ['movimientos_bancarios_sin_resolver'])

    def test_financial_monthly_summary_exposes_monthly_close_control_blockers(self):
        _, empresa, _, _, contrato, periodo = self._create_context('FINCTRL', owner_kind='empresa', with_facturadora=True)
        self._activate_fiscal_config(empresa)
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
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='ctrl-1',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100111.00',
            payload_resumen={},
            idempotency_key='rep-fin-control-1',
            estado_contable='contabilizado',
        )
        self._create_posted_asiento(event)
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

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        control = response.data['control_cierre_mensual'][0]
        self.assertEqual(control['estado_control'], 'bloqueado')
        self.assertTrue(control['cierre_contable_aprobado'])
        self.assertTrue(control['banco_cuadrado'])
        self.assertTrue(control['f29_requerido'])
        self.assertEqual(control['f29_estado'], 'faltante')
        self.assertEqual(control['bloqueadores_periodo'], ['f29_faltante'])

    def test_financial_monthly_summary_blocks_without_approved_close(self):
        _, empresa, _, _, contrato, periodo = self._create_context('FINBLOCK', owner_kind='empresa', with_facturadora=True)
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

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.monthly_close_missing')

    def test_financial_monthly_summary_blocks_posted_event_without_origin(self):
        _, empresa, _, _, _, _ = self._create_context('FINORIGIN', owner_kind='empresa', with_facturadora=True)
        EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='',
            entidad_origen_id='',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100111.00',
            payload_resumen={},
            idempotency_key='rep-fin-missing-origin',
            estado_contable='contabilizado',
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.event_origin_missing')
        self.assertEqual(str(response.data['traceability']['details']['eventos_sin_origen']), '1')

    def test_financial_monthly_summary_blocks_posted_event_without_accounting_entry(self):
        _, empresa, _, _, contrato, periodo = self._create_context('FINASIENTO', owner_kind='empresa', with_facturadora=True)
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
            idempotency_key='rep-fin-missing-asiento',
            estado_contable='contabilizado',
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
        )

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.accounting_entry_missing')

    def test_financial_monthly_summary_blocks_accounting_entry_without_hash(self):
        empresa, event = self._create_financial_summary_event_with_close(
            'FINHASHMISS',
            origin_id='hash-missing-1',
            idempotency_key='rep-fin-hash-missing',
        )
        asiento = self._create_posted_asiento(event, hash_mode='missing')

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.accounting_entry_hash_missing')
        self.assertEqual(
            [str(value) for value in response.data['traceability']['details']['asientos_sin_hash']],
            [str(asiento.id)],
        )

    def test_financial_monthly_summary_blocks_accounting_entry_not_posted(self):
        empresa, event = self._create_financial_summary_event_with_close(
            'FINENTRYDRAFT',
            origin_id='entry-draft-1',
            idempotency_key='rep-fin-entry-draft',
        )
        asiento = self._create_posted_asiento(event)
        asiento.estado = EstadoAsientoContable.DRAFT
        asiento.save(update_fields=['estado'])

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.accounting_entry_not_posted')
        self.assertEqual(
            [str(value) for value in response.data['traceability']['details']['asientos_no_posteados']],
            [str(asiento.id)],
        )

    def test_financial_monthly_summary_blocks_accounting_entry_unbalanced(self):
        empresa, event = self._create_financial_summary_event_with_close(
            'FINENTRYUNBAL',
            origin_id='entry-unbalanced-1',
            idempotency_key='rep-fin-entry-unbalanced',
        )
        asiento = self._create_posted_asiento(event)
        AsientoContable.objects.filter(pk=asiento.pk).update(haber_total='100000.00')

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.accounting_entry_unbalanced')
        self.assertEqual(
            [str(value) for value in response.data['traceability']['details']['asientos_descuadrados']],
            [str(asiento.id)],
        )

    def test_financial_monthly_summary_blocks_accounting_entry_with_stale_hash(self):
        empresa, event = self._create_financial_summary_event_with_close(
            'FINHASHBAD',
            origin_id='hash-stale-1',
            idempotency_key='rep-fin-hash-stale',
        )
        asiento = self._create_posted_asiento(event, hash_mode='stale')

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.accounting_entry_hash_mismatch')
        self.assertEqual(
            [str(value) for value in response.data['traceability']['details']['asientos_hash_desactualizado']],
            [str(asiento.id)],
        )

    def test_financial_monthly_summary_blocks_accounting_entry_without_movements(self):
        empresa, event = self._create_financial_summary_event_with_close(
            'FINMOVMISS',
            origin_id='movements-missing-1',
            idempotency_key='rep-fin-movements-missing',
        )
        asiento = self._create_posted_asiento(event, with_movements=False)

        response = self.client.get(f"{reverse('reporting-financiero-mensual')}?anio=2026&mes=1&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.accounting_entry_movements_missing')
        self.assertEqual(
            [str(value) for value in response.data['traceability']['details']['asientos_sin_movimientos']],
            [str(asiento.id)],
        )

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
        progress_missing = self.client.get(reverse('reporting-company-accounting-progress'))
        progress_invalid = self.client.get(
            f"{reverse('reporting-company-accounting-progress')}?empresa_id=x&fiscal_year=y"
        )
        review_invalid = self.client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': 'x', 'fiscal_year': 'y', 'bank_support_manifest': []},
            format='json',
        )

        self.assertEqual(books_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(books_missing.data['empresa_id'], 'Este parametro es obligatorio.')
        self.assertEqual(annual_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(annual_invalid.data['anio_tributario'], 'Debe ser un entero valido.')
        self.assertEqual(progress_missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(progress_missing.data['empresa_id'], 'Este parametro es obligatorio.')
        self.assertEqual(progress_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(progress_invalid.data['empresa_id'], 'Debe ser un entero valido.')
        self.assertEqual(review_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(review_invalid.data['empresa_id'], 'Debe ser un entero valido.')

    def test_partner_summary_returns_404_when_partner_does_not_exist(self):
        socio, _, _, _, _, _ = self._create_context('PARTNER404')
        response = self.client.get(reverse('reporting-socio-resumen', args=[socio.id + 9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_period_books_summary_returns_snapshot_payloads(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKS')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'asientos': [{'id': 1}]})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'cuentas': [{'id': 1}]})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertEqual(response.data['libro_diario']['estado_snapshot'], 'aprobado')
        self.assertTrue(response.data['balance_comprobacion']['resumen']['cuadrado'])

    def test_company_accounting_progress_endpoint_returns_objective_progress_without_rut(self):
        _, empresa, _, _, _, _ = self._create_context('PROGRESS')
        self._activate_fiscal_config(empresa)
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
            fecha_preparacion=timezone.now(),
            fecha_aprobacion=timezone.now(),
        )
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            storage_ref='balance-progress-controlled',
            resumen={'cuadrado': True},
        )
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.F29_PREPARACION,
                certificado_ref='progress-f29-cert-controlled',
                estado_gate='abierto',
            ),
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'progress-test'},
            borrador_ref='progress-f29-draft',
            responsable_revision_ref='progress-reviewer',
        )

        response = self.client.get(
            reverse('reporting-company-accounting-progress'),
            {'empresa_id': empresa.id, 'fiscal_year': 2026},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['empresa']['id'], empresa.id)
        self.assertEqual(response.data['fiscal_year'], 2026)
        self.assertEqual(response.data['tax_year'], 2027)
        self.assertEqual(response.data['classification'], 'parcial')
        self.assertFalse(response.data['ready_for_company_accounting_review'])
        self.assertFalse(response.data['review_boundary']['autonomous_accounting'])
        self.assertFalse(response.data['review_boundary']['final_tax_calculation'])
        self.assertFalse(response.data['review_boundary']['sii_submission'])
        self.assertTrue(response.data['review_boundary']['requires_responsible_review'])
        self.assertEqual(response.data['responsible_review_gate']['state'], 'local_layers_incomplete')
        self.assertFalse(response.data['responsible_review_gate']['local_layers_ready_for_review'])
        self.assertFalse(response.data['responsible_review_gate']['ready_for_responsible_decision_handoff'])
        self.assertFalse(response.data['responsible_review_gate']['ready_for_final_tax_calculation'])
        self.assertFalse(response.data['responsible_review_gate']['ready_for_sii_submission'])
        self.assertEqual(
            response.data['responsible_review_gate']['next_action_ref'],
            'complete_local_phase:monthly_closes',
        )
        self.assertEqual(response.data['next_blocking_phase'], 'monthly_closes')
        self.assertEqual(response.data['phases']['monthly_closes']['completed'], 1)
        self.assertEqual(response.data['phases']['monthly_balances_squared']['completed'], 1)
        self.assertEqual(response.data['phases']['f29_monthly']['completed'], 1)
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertFalse(response.data['trazabilidad']['controles']['autonomous_accounting'])
        self.assertFalse(response.data['trazabilidad']['controles']['final_tax_calculation'])
        self.assertFalse(response.data['trazabilidad']['controles']['sii_submission'])
        self.assertTrue(response.data['trazabilidad']['controles']['requires_responsible_review'])
        self.assertEqual(
            response.data['trazabilidad']['controles']['responsible_review_gate_state'],
            'local_layers_incomplete',
        )
        self.assertFalse(response.data['trazabilidad']['controles']['ready_for_responsible_decision_handoff'])
        self.assertFalse(response.data['trazabilidad']['controles']['ready_for_final_tax_calculation'])
        self.assertFalse(response.data['trazabilidad']['controles']['ready_for_sii_submission'])
        self.assertNotIn(empresa.rut, json.dumps(response.data))

    def test_company_accounting_candidates_endpoint_lists_scoped_signal_years_without_rut(self):
        _, empresa, _, _, _, _ = self._create_context('PROGCAND')
        _, empresa_empty, _, _, _, _ = self._create_context('PROGEMPTY')
        self._activate_fiscal_config(empresa)
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
            fecha_preparacion=timezone.now(),
            fecha_aprobacion=timezone.now(),
        )
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot=EstadoCierreMensual.APPROVED,
            storage_ref='candidate-balance-controlled',
            resumen={'cuadrado': True},
        )
        F29PreparacionMensual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.F29_PREPARACION,
                certificado_ref='candidate-f29-cert-controlled',
                estado_gate='abierto',
            ),
            cierre_mensual=close,
            anio=2026,
            mes=1,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_formulario={'source': 'candidate-test'},
            borrador_ref='candidate-f29-draft',
            responsable_revision_ref='candidate-reviewer',
        )

        response = self.client.get(reverse('reporting-company-accounting-candidates'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['companies_total'], 2)
        self.assertEqual(response.data['summary']['candidate_companies'], 1)
        self.assertFalse(response.data['selection_boundary']['uses_external_sources'])
        self.assertFalse(response.data['selection_boundary']['autonomous_accounting'])
        self.assertFalse(response.data['selection_boundary']['final_tax_calculation'])
        self.assertFalse(response.data['selection_boundary']['sii_submission'])
        self.assertEqual(response.data['candidates'][0]['empresa']['id'], empresa.id)
        self.assertEqual(response.data['candidates'][0]['recommended_fiscal_year'], 2026)
        self.assertEqual(response.data['candidates'][0]['years'][0]['signals']['monthly_closes'], 1)
        self.assertEqual(response.data['candidates'][0]['years'][0]['signals']['monthly_balances_squared'], 1)
        self.assertEqual(response.data['candidates'][0]['years'][0]['signals']['f29_monthly'], 1)
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertFalse(response.data['trazabilidad']['controles']['autonomous_accounting'])
        self.assertFalse(response.data['trazabilidad']['controles']['final_tax_calculation'])
        self.assertFalse(response.data['trazabilidad']['controles']['sii_submission'])
        self.assertNotIn(empresa.rut, json.dumps(response.data))
        self.assertNotIn(empresa_empty.rut, json.dumps(response.data))

    def test_company_accounting_review_package_endpoint_returns_safe_review_boundary(self):
        _, empresa, _, _, _, _ = self._create_context('REVIEWPKG')
        self._activate_fiscal_config(empresa)
        manifest = self._complete_bank_support_manifest(empresa)

        response = self.client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': empresa.id, 'fiscal_year': 2026, 'bank_support_manifest': manifest},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['schema_version'], 'company-accounting-review-package.v1')
        self.assertEqual(response.data['empresa']['id'], empresa.id)
        self.assertEqual(response.data['fiscal_year'], 2026)
        self.assertEqual(response.data['tax_year'], 2027)
        self.assertEqual(response.data['classification'], 'parcial')
        self.assertFalse(response.data['ready_for_productive_accounting_review'])
        self.assertEqual(response.data['summary']['expected_company_ref'], f'company-{empresa.id}')
        self.assertEqual(response.data['summary']['bank_support_company_ref'], f'company-{empresa.id}')
        self.assertTrue(response.data['bank_support_coverage']['ready_for_accounting_document_review'])
        self.assertFalse(response.data['boundary']['autonomous_accounting'])
        self.assertFalse(response.data['boundary']['final_tax_calculation'])
        self.assertFalse(response.data['boundary']['sii_submission'])
        self.assertFalse(response.data['boundary']['uses_external_integrations'])
        self.assertTrue(response.data['boundary']['requires_responsible_review'])
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertFalse(response.data['trazabilidad']['controles']['autonomous_accounting'])
        self.assertFalse(response.data['trazabilidad']['controles']['final_tax_calculation'])
        self.assertFalse(response.data['trazabilidad']['controles']['sii_submission'])
        self.assertFalse(response.data['trazabilidad']['controles']['uses_external_integrations'])
        self.assertTrue(response.data['trazabilidad']['controles']['requires_responsible_review'])
        self.assertIn('accounting_progress_hash', response.data['evidence'])
        self.assertIn('bank_support_hash', response.data['evidence'])
        self.assertNotIn(empresa.rut, json.dumps(response.data))

    def test_company_accounting_review_package_endpoint_rejects_document_intake_local_sources(self):
        _, empresa, _, _, _, _ = self._create_context('REVIEWINTAKEAPI')
        self._activate_fiscal_config(empresa)
        manifest = self._complete_bank_support_manifest(empresa)
        sensitive_path = r'D:\Clientes\InmobiliariaPuig\BancoChile\cartola-2025.pdf'

        response = self.client.post(
            reverse('reporting-company-accounting-review-package'),
            {
                'empresa_id': empresa.id,
                'fiscal_year': 2026,
                'bank_support_manifest': manifest,
                'document_intake_package_dir': sensitive_path,
                'document_intake_package': {'package_hash': 'fake-client-side-package'},
            },
            format='json',
        )

        rendered = json.dumps(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('document_intake_package_dir', response.data)
        self.assertIn('document_intake_package', response.data)
        self.assertNotIn('InmobiliariaPuig', rendered)
        self.assertNotIn('BancoChile', rendered)
        self.assertNotIn('cartola-2025.pdf', rendered)
        self.assertNotIn('fake-client-side-package', rendered)

    def test_company_accounting_review_package_endpoint_blocks_manifest_for_other_company(self):
        _, empresa_a, _, _, _, _ = self._create_context('REVIEWPKGA')
        _, empresa_b, _, _, _, _ = self._create_context('REVIEWPKGB')
        self._activate_fiscal_config(empresa_a)
        manifest = self._complete_bank_support_manifest(empresa_b)

        response = self.client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': empresa_a.id, 'fiscal_year': 2026, 'bank_support_manifest': manifest},
            format='json',
        )

        rendered = json.dumps(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['classification'], 'parcial')
        self.assertFalse(response.data['ready_for_productive_accounting_review'])
        self.assertTrue(response.data['bank_support_coverage']['ready_for_accounting_document_review'])
        self.assertEqual(response.data['summary']['expected_company_ref'], f'company-{empresa_a.id}')
        self.assertEqual(response.data['summary']['bank_support_company_ref'], f'company-{empresa_b.id}')
        self.assertIn(
            'company_accounting_review.bank_support_company_ref_mismatch',
            {issue['code'] for issue in response.data['issues']},
        )
        self.assertNotIn(empresa_a.rut, rendered)
        self.assertNotIn(empresa_b.rut, rendered)

    def test_company_accounting_review_package_endpoint_redacts_sensitive_manifest_values(self):
        _, empresa, _, _, _, _ = self._create_context('REVIEWSECRETS')
        manifest = self._complete_bank_support_manifest(empresa)
        manifest['company_ref'] = empresa.rut
        manifest['attachments'][0]['evidence_ref'] = 'https://storage.example.com/leasing.pdf?token=secret'
        manifest['attachments'][1]['evidence_ref'] = r'D:\Documentos\leasing\payment-history.pdf'
        manifest['confirmations'][0]['password'] = 'secret-value'

        response = self.client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': empresa.id, 'fiscal_year': 2026, 'bank_support_manifest': manifest},
            format='json',
        )

        rendered = json.dumps(response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['ready_for_productive_accounting_review'])
        self.assertIn('company_accounting_review.bank_support_incomplete', {issue['code'] for issue in response.data['issues']})
        self.assertIn(
            'company_bank_support.sensitive_reference',
            {issue['code'] for issue in response.data['bank_support_coverage']['issues']},
        )
        self.assertIn(REDACTED_SENSITIVE_REFERENCE, rendered)
        self.assertNotIn(empresa.rut, rendered)
        self.assertNotIn('storage.example.com', rendered)
        self.assertNotIn('secret-value', rendered)
        self.assertNotIn('payment-history.pdf', rendered)

    def test_company_accounting_progress_endpoint_respects_company_scope(self):
        _, empresa_a, _, _, _, _ = self._create_context('PROGSCOPEA')
        _, empresa_b, _, _, _, _ = self._create_context('PROGSCOPEB')
        reviewer_client = self._create_scoped_reviewer_client(empresa_a)

        in_scope = reviewer_client.get(
            reverse('reporting-company-accounting-progress'),
            {'empresa_id': empresa_a.id, 'fiscal_year': 2026},
        )
        out_of_scope = reviewer_client.get(
            reverse('reporting-company-accounting-progress'),
            {'empresa_id': empresa_b.id, 'fiscal_year': 2026},
        )

        self.assertEqual(in_scope.status_code, status.HTTP_200_OK)
        self.assertEqual(out_of_scope.status_code, status.HTTP_404_NOT_FOUND)

    def test_company_accounting_review_package_endpoint_respects_company_scope(self):
        _, empresa_a, _, _, _, _ = self._create_context('REVPKGSCOPEA')
        _, empresa_b, _, _, _, _ = self._create_context('REVPKGSCOPEB')
        reviewer_client = self._create_scoped_reviewer_client(empresa_a)
        payload = {'fiscal_year': 2026, 'bank_support_manifest': self._complete_bank_support_manifest(empresa_a)}

        in_scope = reviewer_client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': empresa_a.id, **payload},
            format='json',
        )
        out_of_scope = reviewer_client.post(
            reverse('reporting-company-accounting-review-package'),
            {'empresa_id': empresa_b.id, **payload},
            format='json',
        )

        self.assertEqual(in_scope.status_code, status.HTTP_200_OK)
        self.assertEqual(out_of_scope.status_code, status.HTTP_404_NOT_FOUND)

    def test_company_accounting_candidates_endpoint_respects_company_scope(self):
        _, empresa_a, _, _, _, _ = self._create_context('PROGCANDSA')
        _, empresa_b, _, _, _, _ = self._create_context('PROGCANDSB')
        CierreMensualContable.objects.create(
            empresa=empresa_a,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
        )
        CierreMensualContable.objects.create(
            empresa=empresa_b,
            anio=2026,
            mes=1,
            estado=EstadoCierreMensual.APPROVED,
        )
        reviewer_client = self._create_scoped_reviewer_client(empresa_a)

        response = reviewer_client.get(reverse('reporting-company-accounting-candidates'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['summary']['companies_total'], 1)
        self.assertEqual(response.data['summary']['candidate_companies'], 1)
        self.assertEqual(response.data['candidates'][0]['empresa']['id'], empresa_a.id)
        self.assertNotIn(empresa_b.razon_social, json.dumps(response.data))

    def test_reporting_query_params_normalize_before_filtering(self):
        _, empresa, _, _, _, _ = self._create_context('QUERYNORM')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'asientos': [{'id': 1}]})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'cuentas': [{'id': 1}]})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )
        ManualResolution.objects.create(
            category='ops.open_required',
            status=ManualResolution.Status.OPEN,
            scope_type='operacion',
            scope_reference='op-open',
            summary='Resolucion abierta',
        )
        ManualResolution.objects.create(
            category='ops.resolved',
            status=ManualResolution.Status.RESOLVED,
            scope_type='operacion',
            scope_reference='op-resolved',
            summary='Resolucion cerrada',
        )

        books_response = self.client.get(
            reverse('reporting-libros-periodo'),
            {'empresa_id': f' {empresa.id} ', 'periodo': ' 2026-01 '},
        )
        manual_response = self.client.get(reverse('reporting-manual-resolutions-summary'), {'status': ' open '})

        self.assertEqual(books_response.status_code, status.HTTP_200_OK)
        self.assertEqual(books_response.data['periodo'], '2026-01')
        self.assertEqual(books_response.data['trazabilidad']['controles']['periodo'], '2026-01')
        self.assertEqual(manual_response.status_code, status.HTTP_200_OK)
        self.assertEqual(manual_response.data['status'], 'open')
        self.assertEqual(manual_response.data['total'], 1)
        self.assertEqual(manual_response.data['categorias'], [{'category': 'ops.open_required', 'total': 1}])

    def test_period_books_summary_redacts_inherited_sensitive_snapshot_refs(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKSREDACT')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            storage_ref='https://storage.example.test/diario.pdf?token=secret',
            resumen={'authorization': 'Bearer inherited-ledger-value', 'safe_ref': 'diario-controlled-ref'},
        )
        LibroMayor.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            storage_ref='https://storage.example.test/mayor.pdf?token=secret',
            resumen={'callback': 'https://storage.example.test/mayor?token=secret'},
        )
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            storage_ref='https://storage.example.test/balance.pdf?token=secret',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True, 'api_key': 'secret-key'},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertEqual(response.data['libro_diario']['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data['libro_diario']['resumen']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data['libro_diario']['resumen']['safe_ref'], 'diario-controlled-ref')
        self.assertEqual(response.data['libro_mayor']['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data['libro_mayor']['resumen']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data['balance_comprobacion']['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(response.data['balance_comprobacion']['resumen']['api_key'], REDACTED_SENSITIVE_REFERENCE)
        rendered = str(response.data)
        self.assertNotIn('storage.example.test', rendered)
        self.assertNotIn('secret-key', rendered)

    def test_period_books_summary_blocks_unapproved_snapshots(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKSBLOCK')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='preparado', resumen={'asientos': [{'id': 1}]})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'cuentas': [{'id': 1}]})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.books_snapshot_not_approved')

    def test_period_books_summary_blocks_missing_snapshot_for_close(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKSNOSNAPSHOT')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'asientos': [{'id': 1}]},
        )
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.books_snapshot_missing_for_close')
        self.assertEqual(response.data['traceability']['details']['faltantes'], ['libro_mayor'])

    def test_period_books_summary_blocks_snapshot_without_summary(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKSNOSUM')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'cuentas': [{'id': 1}]})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.books_snapshot_summary_missing')
        self.assertEqual(response.data['traceability']['details']['snapshots_sin_resumen'], ['libro_diario'])

    def test_period_books_summary_blocks_unbalanced_balance(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKSBALBAD')
        CierreMensualContable.objects.create(empresa=empresa, anio=2026, mes=1, estado='aprobado')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'asientos': [{'id': 1}]})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'cuentas': [{'id': 1}]})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '90.00', 'cuadrado': False},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.books_balance_not_square')

    def test_period_books_summary_blocks_without_approved_close(self):
        _, empresa, _, _, _, _ = self._create_context('BOOKSCLOSE')
        LibroDiario.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'asientos': [{'id': 1}]})
        LibroMayor.objects.create(empresa=empresa, periodo='2026-01', estado_snapshot='aprobado', resumen={'cuentas': [{'id': 1}]})
        BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            resumen={'total_debe': '100.00', 'total_haber': '100.00', 'cuadrado': True},
        )

        response = self.client.get(f"{reverse('reporting-libros-periodo')}?empresa_id={empresa.id}&periodo=2026-01")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.books_close_missing')

    def test_annual_tax_summary_returns_process_ddjj_and_f22(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUAL')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={
                'fiscal_year': 2026,
                'obligaciones': [{'mes': 1}],
                'total_obligaciones': 12,
                'empty_review_ref': '',
                'headers': {'authorization': ''},
            },
            responsable_revision_ref='process-review-controlled-ref',
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
            paquete_ref='ddjj-controlled-ref',
            responsable_revision_ref='ddjj-review-controlled-ref',
            resumen_paquete={
                'ddjj_habilitadas': ['1887'],
                'resumen_anual': {'fiscal_year': 2026},
                'empty_review_ref': '',
                'headers': {'authorization': ''},
            },
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
            borrador_ref='f22-controlled-ref',
            responsable_revision_ref='f22-review-controlled-ref',
            resumen_f22={
                'base': '100.00',
                'resumen_anual': {'fiscal_year': 2026},
                'empty_review_ref': '',
                'headers': {'authorization': ''},
            },
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['trazabilidad']['estado'], 'verificado')
        self.assertEqual(len(response.data['procesos_renta']), 1)
        self.assertEqual(len(response.data['ddjj_preparadas']), 1)
        self.assertEqual(len(response.data['f22_preparados']), 1)
        self.assertEqual(response.data['procesos_renta'][0]['responsable_revision_ref'], 'process-review-controlled-ref')
        self.assertEqual(response.data['ddjj_preparadas'][0]['responsable_revision_ref'], 'ddjj-review-controlled-ref')
        self.assertEqual(response.data['f22_preparados'][0]['responsable_revision_ref'], 'f22-review-controlled-ref')
        self.assertEqual(response.data['procesos_renta'][0]['resumen_anual']['empty_review_ref'], '')
        self.assertEqual(response.data['procesos_renta'][0]['resumen_anual']['headers']['authorization'], '')
        self.assertEqual(response.data['ddjj_preparadas'][0]['resumen_paquete']['headers']['authorization'], '')
        self.assertEqual(response.data['f22_preparados'][0]['resumen_f22']['headers']['authorization'], '')
        self.assertNotIn(REDACTED_SENSITIVE_REFERENCE, json.dumps(response.data))

    def test_annual_tax_summary_blocks_process_without_traceable_state(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCSTATE')
        self._activate_fiscal_config(empresa)
        ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.IN_PREPARATION,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_not_traceable')
        self.assertEqual(
            response.data['traceability']['details']['estado'],
            EstadoPreparacionTributaria.IN_PREPARATION,
        )

    def test_annual_tax_summary_blocks_in_scope_status_audit_without_transition_metadata(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALAUDIT')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-audit',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-audit',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id=str(ddjj.id),
            summary='Actualizacion anual heredada sin metadata de transicion para reporting.',
            metadata={'estado_nuevo': EstadoPreparacionTributaria.APPROVED},
        )
        AuditEvent.objects.create(
            event_type='sii.f22_preparacion.status_updated',
            entity_type='f22_preparacion',
            entity_id='999999',
            summary='Evento fuera del reporte anual solicitado.',
            metadata={'estado_nuevo': EstadoPreparacionTributaria.APPROVED},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_status_transition_metadata_missing')
        missing_events = response.data['traceability']['details']['eventos_status_updated_incompletos']
        self.assertEqual(len(missing_events), 1)
        self.assertEqual(str(missing_events[0]['documento']), 'DDJJPreparacionAnual')
        self.assertEqual(str(missing_events[0]['event_type']), 'sii.ddjj_preparacion.status_updated')
        self.assertEqual(str(missing_events[0]['eventos_incompletos']), '1')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('999999', serialized_response)
        self.assertNotIn('estado_nuevo', serialized_response)

    def test_annual_tax_summary_blocks_status_audit_without_review_responsible(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALAUDITRESP')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
            responsable_revision_ref='process-review-controlled-ref',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.DDJJ_PREPARACION,
                certificado_ref='cert-ddjj-audit-responsible',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            responsable_revision_ref='ddjj-review-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.F22_PREPARACION,
                certificado_ref='cert-f22-audit-responsible',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            responsable_revision_ref='f22-review-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id=str(ddjj.id),
            summary='Actualizacion anual heredada sin responsable auditado.',
            metadata={
                'campo_estado': 'estado_preparacion',
                'estado_anterior': EstadoPreparacionTributaria.PREPARED,
                'estado_nuevo': EstadoPreparacionTributaria.APPROVED,
            },
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_status_responsible_ref_missing')
        missing_events = response.data['traceability']['details']['eventos_status_updated_sin_responsable']
        self.assertEqual(len(missing_events), 1)
        self.assertEqual(str(missing_events[0]['documento']), 'DDJJPreparacionAnual')
        self.assertEqual(str(missing_events[0]['eventos_sin_responsable']), '1')
        self.assertNotIn('estado_nuevo', json.dumps(response.data))

    def test_annual_tax_summary_blocks_status_audit_sensitive_review_responsible_without_leak(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALAUDITRESPSENS')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
            responsable_revision_ref='process-review-controlled-ref',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.DDJJ_PREPARACION,
                certificado_ref='cert-ddjj-audit-responsible-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            responsable_revision_ref='ddjj-review-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.F22_PREPARACION,
                certificado_ref='cert-f22-audit-responsible-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            responsable_revision_ref='f22-review-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        AuditEvent.objects.create(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id=str(ddjj.id),
            summary='Actualizacion anual heredada con responsable sensible.',
            metadata={
                'campo_estado': 'estado_preparacion',
                'estado_anterior': EstadoPreparacionTributaria.PREPARED,
                'estado_nuevo': EstadoPreparacionTributaria.APPROVED,
                'responsable_revision_ref': 'https://sii.example.test/reviewer?token=secret',
            },
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_status_responsible_ref_sensitive')
        sensitive_events = response.data['traceability']['details']['eventos_status_updated_responsable_sensible']
        self.assertEqual(len(sensitive_events), 1)
        self.assertEqual(str(sensitive_events[0]['documento']), 'DDJJPreparacionAnual')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_final_process_without_ddjj_ref(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCREF')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-process-ref',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-process-ref',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_ddjj_ref_missing')

    def test_annual_tax_summary_blocks_final_process_without_f22_ref(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCF22REF')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='',
        )
        self._create_annual_ddjj(empresa, process, suffix='process-f22-missing-ddjj')
        self._create_annual_f22(empresa, process, suffix='process-f22-missing-f22')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_f22_ref_missing')

    def test_annual_tax_summary_blocks_final_process_without_review_responsible(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCREVIEW')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        self._create_annual_ddjj(empresa, process, suffix='process-review-missing-ddjj')
        self._create_annual_f22(empresa, process, suffix='process-review-missing-f22')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['traceability']['code'],
            'reporting.annual_process_responsible_ref_missing',
        )

    def test_annual_tax_summary_blocks_sensitive_process_review_responsible_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCREVIEWSENS')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
            responsable_revision_ref='https://sii.example.test/reviewer?token=secret',
        )
        self._create_annual_ddjj(empresa, process, suffix='process-review-sensitive-ddjj')
        self._create_annual_f22(empresa, process, suffix='process-review-sensitive-f22')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['traceability']['code'],
            'reporting.annual_process_responsible_ref_sensitive',
        )
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_final_ddjj_without_review_responsible(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJREVIEW')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
            responsable_revision_ref='process-review-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.DDJJ_PREPARACION,
                certificado_ref='cert-ddjj-review-missing',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        self._create_annual_f22(empresa, process, suffix='ddjj-review-missing-f22')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['traceability']['code'],
            'reporting.annual_ddjj_responsible_ref_missing',
        )

    def test_annual_tax_summary_blocks_final_f22_without_review_responsible(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22REVIEW')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
            responsable_revision_ref='process-review-controlled-ref',
        )
        self._create_annual_ddjj(empresa, process, suffix='f22-review-missing-ddjj')
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key=CapacidadSII.F22_PREPARACION,
                certificado_ref='cert-f22-review-missing',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['traceability']['code'],
            'reporting.annual_f22_responsible_ref_missing',
        )

    def test_annual_tax_summary_blocks_final_ddjj_without_text_ref(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJTEXT')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-text-ref',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-ddjj-text-ref',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        DDJJPreparacionAnual.objects.filter(pk=ddjj.pk).update(paquete_ref='   ')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_ref_missing')

    def test_annual_tax_summary_blocks_final_f22_without_text_ref(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22TEXT')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-f22-text-ref',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-text-ref',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.filter(pk=f22.pk).update(borrador_ref='   ')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_ref_missing')

    def test_annual_tax_summary_blocks_final_ddjj_sensitive_ref_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJSENSITIVE')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-final-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-ddjj-final-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        DDJJPreparacionAnual.objects.filter(pk=ddjj.pk).update(
            paquete_ref='https://sii.example.test/ddjj?token=secret'
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_ref_sensitive')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_final_f22_sensitive_ref_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22SENSITIVE')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-f22-final-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-final-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.filter(pk=f22.pk).update(
            borrador_ref='https://sii.example.test/f22?token=secret'
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_ref_sensitive')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_final_process_sensitive_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCPAYLOAD')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-process-payload',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-process-payload',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        ProcesoRentaAnual.objects.filter(pk=process.pk).update(
            resumen_anual={
                'fiscal_year': 2026,
                'obligaciones': [{'mes': 1}],
                'total_obligaciones': 12,
                'api_key': None,
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_sensitive_payload')
        self.assertNotIn('api_key', json.dumps(response.data))

    def test_annual_tax_summary_blocks_final_ddjj_sensitive_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJPAYLOAD')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-final-payload',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-ddjj-final-payload',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        DDJJPreparacionAnual.objects.filter(pk=ddjj.pk).update(
            resumen_paquete={
                'ddjj_habilitadas': ['1887'],
                'resumen_anual': {'fiscal_year': 2026},
                'access_token': None,
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_sensitive_payload')
        self.assertNotIn('access_token', json.dumps(response.data))

    def test_annual_tax_summary_blocks_final_f22_sensitive_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22PAYLOAD')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-f22-final-payload',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-final-payload',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.filter(pk=f22.pk).update(
            resumen_f22={
                'base': '100.00',
                'resumen_anual': {'fiscal_year': 2026},
                'credential': None,
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_sensitive_payload')
        self.assertNotIn('credential', json.dumps(response.data))

    def test_annual_tax_summary_blocks_prepared_process_sensitive_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPREPPROCPAYLOAD')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='prepared-process-payload')
        self._create_annual_f22(empresa, process, suffix='prepared-process-payload')
        ProcesoRentaAnual.objects.filter(pk=process.pk).update(
            resumen_anual={
                'fiscal_year': 2026,
                'obligaciones': [{'mes': 1}],
                'total_obligaciones': 12,
                'api_key': None,
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_sensitive_payload')
        self.assertNotIn('api_key', json.dumps(response.data))

    def test_annual_tax_summary_blocks_control_sensitive_process_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPREPPROCCONTROL')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='prepared-process-control')
        self._create_annual_f22(empresa, process, suffix='prepared-process-control')
        ProcesoRentaAnual.objects.filter(pk=process.pk).update(
            resumen_anual={
                'fiscal_year': 2026,
                'obligaciones': [{'mes': 1}],
                'total_obligaciones': 12,
                'source_ref': 'source_11.111.111-1',
                'support_ref': 'source_C:/Privado/renta.xlsx',
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_sensitive_payload')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('11.111.111-1', serialized_response)
        self.assertNotIn('C:/Privado', serialized_response)

    def test_annual_tax_summary_blocks_prepared_ddjj_sensitive_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPREPDDJJPAYLOAD')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        ddjj = self._create_annual_ddjj(empresa, process, suffix='prepared-ddjj-payload')
        self._create_annual_f22(empresa, process, suffix='prepared-ddjj-payload')
        DDJJPreparacionAnual.objects.filter(pk=ddjj.pk).update(
            resumen_paquete={
                'ddjj_habilitadas': ['1887'],
                'resumen_anual': {'fiscal_year': 2026},
                'access_token': None,
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_sensitive_payload')
        self.assertNotIn('access_token', json.dumps(response.data))

    def test_annual_tax_summary_blocks_prepared_f22_sensitive_payload_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPREPF22PAYLOAD')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='prepared-f22-payload')
        f22 = self._create_annual_f22(empresa, process, suffix='prepared-f22-payload')
        F22PreparacionAnual.objects.filter(pk=f22.pk).update(
            resumen_f22={
                'base': '100.00',
                'resumen_anual': {'fiscal_year': 2026},
                'credential': None,
            }
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_sensitive_payload')
        self.assertNotIn('credential', json.dumps(response.data))

    def test_annual_tax_summary_blocks_prepared_ddjj_sensitive_ref_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPREPDDJJREF')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        ddjj = self._create_annual_ddjj(empresa, process, suffix='prepared-ddjj-ref')
        self._create_annual_f22(empresa, process, suffix='prepared-ddjj-ref')
        DDJJPreparacionAnual.objects.filter(pk=ddjj.pk).update(
            paquete_ref='https://sii.example.test/ddjj?token=secret'
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_ref_sensitive')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_prepared_f22_sensitive_ref_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPREPF22REF')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='prepared-f22-ref')
        f22 = self._create_annual_f22(empresa, process, suffix='prepared-f22-ref')
        F22PreparacionAnual.objects.filter(pk=f22.pk).update(
            borrador_ref='https://sii.example.test/f22?token=secret'
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_ref_sensitive')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_sensitive_process_refs_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCSENSITIVE')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='https://sii.example.test/process-ddjj?token=secret',
            borrador_f22_ref='process-f22-controlled-ref',
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-process-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            paquete_ref='ddjj-controlled-ref',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-process-sensitive',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.APPROVED,
            borrador_ref='f22-controlled-ref',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_ddjj_ref_sensitive')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_control_sensitive_process_refs_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCCONTROLREF')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='process-control-ref')
        self._create_annual_f22(empresa, process, suffix='process-control-ref')
        ProcesoRentaAnual.objects.filter(pk=process.pk).update(paquete_ddjj_ref='package_11.111.111-1')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_ddjj_ref_sensitive')
        self.assertNotIn('11.111.111-1', json.dumps(response.data))

    def test_annual_tax_summary_blocks_sensitive_process_f22_ref_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALPROCF22SENSITIVE')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.APPROVED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
            paquete_ddjj_ref='process-ddjj-controlled-ref',
            borrador_f22_ref='https://sii.example.test/process-f22?token=secret',
        )
        self._create_annual_ddjj(empresa, process, suffix='process-f22-sensitive-ddjj')
        self._create_annual_f22(empresa, process, suffix='process-f22-sensitive-f22')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_f22_ref_sensitive')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('token=secret', serialized_response)

    def test_annual_tax_summary_blocks_inherited_sensitive_payloads_without_leaking_value(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALREDACT')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={
                'fiscal_year': 2026,
                'obligaciones': [{'mes': 1}],
                'callback': 'https://sii.example.test/process?token=secret',
            },
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-redact',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            paquete_ref='https://sii.example.test/ddjj?token=secret',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'api_key': 'secret-api-key-value'},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-redact',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            borrador_ref='https://sii.example.test/f22?token=secret',
            resumen_f22={'base': '100.00', 'access_token': 'secret-token-value'},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_sensitive_payload')
        serialized_response = json.dumps(response.data)
        self.assertNotIn('sii.example.test', serialized_response)
        self.assertNotIn('secret', serialized_response)

    def test_annual_tax_summary_blocks_process_without_active_fiscal_config(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALFISCALPROC')
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-no-fiscal',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-no-fiscal',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_fiscal_config_missing')
        self.assertEqual(
            [
                str(item)
                for item in response.data['traceability']['details']['empresas_proceso_sin_configuracion_fiscal']
            ],
            [str(empresa.id)],
        )

    def test_annual_tax_summary_blocks_ddjj_without_active_fiscal_config(self):
        _, empresa_proceso, _, _, _, _ = self._create_context('ANNUALFISCALDDJJP')
        _, empresa_ddjj, _, _, _, _ = self._create_context('ANNUALFISCALDDJJD')
        self._activate_fiscal_config(empresa_proceso)
        process = self._create_annual_reporting_process(empresa_proceso)
        self._create_annual_ddjj(empresa_ddjj, process, suffix='no-fiscal-ddjj')
        self._create_annual_f22(empresa_proceso, process, suffix='no-fiscal-ddjj')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_fiscal_config_missing')
        self.assertEqual(
            [str(item) for item in response.data['traceability']['details']['empresas_ddjj_sin_configuracion_fiscal']],
            [str(empresa_ddjj.id)],
        )

    def test_annual_tax_summary_blocks_f22_without_active_fiscal_config(self):
        _, empresa_proceso, _, _, _, _ = self._create_context('ANNUALFISCALF22P')
        _, empresa_f22, _, _, _, _ = self._create_context('ANNUALFISCALF22D')
        self._activate_fiscal_config(empresa_proceso)
        process = self._create_annual_reporting_process(empresa_proceso)
        self._create_annual_ddjj(empresa_proceso, process, suffix='no-fiscal-f22')
        self._create_annual_f22(empresa_f22, process, suffix='no-fiscal-f22')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_fiscal_config_missing')
        self.assertEqual(
            [str(item) for item in response.data['traceability']['details']['empresas_f22_sin_configuracion_fiscal']],
            [str(empresa_f22.id)],
        )

    def test_annual_tax_summary_blocks_incomplete_annual_summary(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALBLOCK')
        self._activate_fiscal_config(empresa)
        ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'total_obligaciones': 12},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_summary_incomplete')

    def test_annual_tax_summary_blocks_empty_annual_obligations(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALEMPTYOBL')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [], 'total_obligaciones': 0},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-empty-obligations',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-empty-obligations',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'base': '0.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_summary_incomplete')

    def test_annual_tax_summary_blocks_global_without_process(self):
        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_process_missing')

    def test_annual_tax_summary_blocks_process_without_ddjj_document(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALNODDJJ')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_f22(empresa, process, suffix='missing-ddjj')

        url = f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_missing_for_process')
        self.assertEqual(str(response.data['traceability']['details']['proceso_renta_anual_id']), str(process.id))

    def test_annual_tax_summary_blocks_process_without_f22_document(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALNOF22')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='missing-f22')

        url = f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_missing_for_process')
        self.assertEqual(str(response.data['traceability']['details']['proceso_renta_anual_id']), str(process.id))

    def test_annual_tax_summary_blocks_documents_from_other_process_company(self):
        _, empresa_documento, _, _, _, _ = self._create_context('ANNUALDOCA')
        _, empresa_proceso, _, _, _, _ = self._create_context('ANNUALDOCB')
        self._activate_fiscal_config(empresa_documento)
        self._activate_fiscal_config(empresa_proceso)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa_proceso,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa_documento,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa_documento,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-mismatch',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa_proceso,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa_proceso,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-mismatch',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_process_mismatch')

    def test_annual_tax_summary_blocks_f22_from_other_process_company(self):
        _, empresa_documento, _, _, _, _ = self._create_context('ANNUALF22DOCA')
        _, empresa_proceso, _, _, _, _ = self._create_context('ANNUALF22DOCB')
        self._activate_fiscal_config(empresa_documento)
        self._activate_fiscal_config(empresa_proceso)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa_proceso,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa_proceso,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa_proceso,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-f22-mismatch',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa_documento,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa_documento,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-mismatch',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_process_mismatch')

    def test_annual_tax_summary_blocks_ddjj_with_wrong_capability_kind(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJKIND')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        f22_capability = CapacidadTributariaSII.objects.create(
            empresa=empresa,
            capacidad_key=CapacidadSII.F22_PREPARACION,
            certificado_ref='cert-f22-ddjj-wrong-kind',
            ambiente='certificacion',
            estado_gate='condicionado',
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=f22_capability,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_invalid')
        self.assertEqual(str(response.data['traceability']['details']['ddjj_id']), str(ddjj.id))
        self.assertEqual(
            response.data['traceability']['details']['capacidad_key'],
            CapacidadSII.F22_PREPARACION,
        )

    def test_annual_tax_summary_blocks_f22_with_wrong_capability_kind(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22KIND')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        ddjj = self._create_annual_ddjj(empresa, process, suffix='f22-wrong-kind')
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=ddjj.capacidad_tributaria,
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_invalid')
        self.assertEqual(str(response.data['traceability']['details']['f22_id']), str(f22.id))
        self.assertEqual(
            response.data['traceability']['details']['capacidad_key'],
            CapacidadSII.DDJJ_PREPARACION,
        )

    def test_annual_tax_summary_blocks_ddjj_without_traceable_state(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJSTATE')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.PREPARED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )
        ddjj = DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-state',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.IN_PREPARATION,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-state',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_not_traceable')
        self.assertEqual(str(response.data['traceability']['details']['ddjj_id']), str(ddjj.id))
        self.assertEqual(
            response.data['traceability']['details']['estado'],
            EstadoPreparacionTributaria.IN_PREPARATION,
        )

    def test_annual_tax_summary_blocks_f22_without_traceable_state(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22STATE')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado=EstadoPreparacionTributaria.PREPARED,
            resumen_anual={'fiscal_year': 2026, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-f22-state',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.PREPARED,
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        f22 = F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-state-block',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion=EstadoPreparacionTributaria.IN_PREPARATION,
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_not_traceable')
        self.assertEqual(str(response.data['traceability']['details']['f22_id']), str(f22.id))
        self.assertEqual(
            response.data['traceability']['details']['estado'],
            EstadoPreparacionTributaria.IN_PREPARATION,
        )

    def test_annual_tax_summary_blocks_ddjj_without_summary(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJNOSUM')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        ddjj = self._create_annual_ddjj(empresa, process, suffix='ddjj-no-summary', resumen_paquete={})
        self._create_annual_f22(empresa, process, suffix='ddjj-no-summary')

        url = f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_summary_missing')
        self.assertEqual(str(response.data['traceability']['details']['ddjj_id']), str(ddjj.id))

    def test_annual_tax_summary_blocks_f22_without_summary(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22NOSUM')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa)
        self._create_annual_ddjj(empresa, process, suffix='f22-no-summary')
        f22 = self._create_annual_f22(empresa, process, suffix='f22-no-summary', resumen_f22={})

        url = f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_summary_missing')
        self.assertEqual(str(response.data['traceability']['details']['f22_id']), str(f22.id))

    def test_annual_tax_summary_blocks_wrong_fiscal_year(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALYEAR')
        self._activate_fiscal_config(empresa)
        process = ProcesoRentaAnual.objects.create(
            empresa=empresa,
            anio_tributario=2027,
            estado='preparado',
            resumen_anual={'fiscal_year': 2025, 'obligaciones': [{'mes': 1}], 'total_obligaciones': 12},
        )
        DDJJPreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='DDJJPreparacion',
                certificado_ref='cert-ddjj-year',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2026}},
        )
        F22PreparacionAnual.objects.create(
            empresa=empresa,
            capacidad_tributaria=CapacidadTributariaSII.objects.create(
                empresa=empresa,
                capacidad_key='F22Preparacion',
                certificado_ref='cert-f22-year',
                ambiente='certificacion',
                estado_gate='condicionado',
            ),
            proceso_renta_anual=process,
            anio_tributario=2027,
            estado_preparacion='preparado',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2026}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_fiscal_year_mismatch')
        self.assertEqual(str(response.data['traceability']['details']['expected_fiscal_year']), '2026')

    def test_annual_tax_summary_blocks_ddjj_wrong_fiscal_year(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALDDJJYEAR')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa, anio_tributario=2027)
        ddjj = self._create_annual_ddjj(
            empresa,
            process,
            suffix='wrong-ddjj-year',
            resumen_paquete={'ddjj_habilitadas': ['1887'], 'resumen_anual': {'fiscal_year': 2025}},
        )
        self._create_annual_f22(empresa, process, suffix='valid-f22-year')

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_ddjj_fiscal_year_mismatch')
        self.assertEqual(str(response.data['traceability']['details']['ddjj_id']), str(ddjj.id))
        self.assertEqual(str(response.data['traceability']['details']['fiscal_year']), '2025')
        self.assertEqual(str(response.data['traceability']['details']['expected_fiscal_year']), '2026')

    def test_annual_tax_summary_blocks_f22_wrong_fiscal_year(self):
        _, empresa, _, _, _, _ = self._create_context('ANNUALF22YEAR')
        self._activate_fiscal_config(empresa)
        process = self._create_annual_reporting_process(empresa, anio_tributario=2027)
        self._create_annual_ddjj(empresa, process, suffix='valid-ddjj-year')
        f22 = self._create_annual_f22(
            empresa,
            process,
            suffix='wrong-f22-year',
            resumen_f22={'base': '100.00', 'resumen_anual': {'fiscal_year': 2025}},
        )

        response = self.client.get(f"{reverse('reporting-tributario-anual')}?anio_tributario=2027&empresa_id={empresa.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['traceability']['code'], 'reporting.annual_f22_fiscal_year_mismatch')
        self.assertEqual(str(response.data['traceability']['details']['f22_id']), str(f22.id))
        self.assertEqual(str(response.data['traceability']['details']['fiscal_year']), '2025')
        self.assertEqual(str(response.data['traceability']['details']['expected_fiscal_year']), '2026')

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
