from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cobranza.models import EstadoPago, GarantiaContractual, PagoMensual
from conciliacion.models import ConexionBancaria, MovimientoBancarioImportado
from core.models import Role, Scope, UserScopeAssignment
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    ObligacionTributariaMensual,
)
from .services import DEFAULT_REGIME_CODE, ensure_default_regime


class ContabilidadAPITests(APITestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='ledger',
            password='secret123',
            default_role_code='AdministradorGlobal',
        )
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='LedgerCo', rut='88888888-8'):
        rut_seed = ''.join(char for char in rut if char.isdigit())
        socio_seed = rut_seed[-7:]
        socio_1 = self._create_socio(f'{nombre} Socio 1', f'{socio_seed}1-1')
        socio_2 = self._create_socio(f'{nombre} Socio 2', f'{socio_seed}2-2')
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

    def _assign_company_scope_reviewer(self, user, empresa):
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        scope = Scope.objects.create(
            code=f'company-{empresa.id}',
            name=f'Empresa {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=user, role=reviewer_role, scope=scope, is_primary=True)

    def _setup_contabilidad(self, empresa):
        regime = ensure_default_regime()
        ConfiguracionFiscalEmpresa.objects.create(
            empresa=empresa,
            regimen_tributario=regime,
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )
        bancos = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='1101',
            nombre='Bancos',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        cxc = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='1201',
            nombre='Cuentas por Cobrar Arriendos',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        garantias = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='2101',
            nombre='Garantias Recibidas',
            naturaleza='acreedora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        return {'bancos': bancos, 'cxc': cxc, 'garantias': garantias}

    def _create_rule_matrix(
        self,
        empresa,
        event_type,
        debit_account,
        credit_account,
        *,
        vigencia_desde='2026-01-01',
        vigencia_hasta=None,
    ):
        payload = {
            'empresa': empresa.id,
            'evento_tipo': event_type,
            'plan_cuentas_version': 'v1',
            'criterio_cargo': debit_account.codigo,
            'criterio_abono': credit_account.codigo,
            'vigencia_desde': vigencia_desde,
            'estado': 'activa',
        }
        if vigencia_hasta is not None:
            payload['vigencia_hasta'] = vigencia_hasta
        regla = self.client.post(
            reverse('contabilidad-regla-list'),
            payload,
            format='json',
        )
        self.assertEqual(regla.status_code, status.HTTP_201_CREATED)
        matrix = self.client.post(
            reverse('contabilidad-matriz-list'),
            {
                'regla_contable': regla.data['id'],
                'cuenta_debe': debit_account.id,
                'cuenta_haber': credit_account.id,
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(matrix.status_code, status.HTTP_201_CREATED)
        return regla.data['id']

    def _create_contract_with_company_admin(self, empresa, codigo='LED-001'):
        propiedad = Propiedad.objects.create(
            direccion=f'Av {codigo}',
            comuna='Santiago',
            region='RM',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=f'PROP-{codigo}'[:16],
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
        arr = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {codigo}',
            rut='44444444-4',
            email='tenant@example.com',
            telefono='999',
            domicilio_notificaciones='Dir 123',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=codigo,
            mandato_operacion=mandato,
            arrendatario=arr,
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
        return contrato, cuenta

    def test_manual_event_without_fiscal_setup_stays_in_review(self):
        empresa = self._create_active_empresa()
        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': '1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'manual-review-1',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = EventoContable.objects.get(pk=response.data['id'])
        self.assertEqual(event.estado_contable, 'pendiente_revision_contable')
        self.assertFalse(AsientoContable.objects.filter(evento_contable=event).exists())

    def test_manual_event_rejects_non_positive_monto_base(self):
        empresa = self._create_active_empresa()

        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'invalid-zero',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '0.00',
                'payload_resumen': {},
                'idempotency_key': 'invalid-zero',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_and_patch_configuracion_fiscal_with_tasa_ppm_vigente(self):
        empresa = self._create_active_empresa(nombre='FiscalCo', rut='78787878-7')
        regime = ensure_default_regime()

        created = self.client.post(
            reverse('contabilidad-config-list'),
            {
                'empresa': empresa.id,
                'regimen_tributario': regime.id,
                'afecta_iva_arriendo': False,
                'tasa_iva': '0.00',
                'tasa_ppm_vigente': '10.00',
                'aplica_ppm': True,
                'ddjj_habilitadas': [],
                'inicio_ejercicio': '2026-01-01',
                'moneda_funcional': 'CLP',
                'estado': 'activa',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data['tasa_ppm_vigente'], '10.00')

        updated = self.client.patch(
            reverse('contabilidad-config-detail', args=[created.data['id']]),
            {'tasa_ppm_vigente': '12.50'},
            format='json',
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(updated.data['tasa_ppm_vigente'], '12.50')

        config = ConfiguracionFiscalEmpresa.objects.get(pk=created.data['id'])
        self.assertEqual(str(config.tasa_ppm_vigente), '12.50')

    def test_control_snapshot_returns_initial_control_payload(self):
        empresa = self._create_active_empresa(nombre='SnapshotCo', rut='73737373-7')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='snapshot-1',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100000.00',
            payload_resumen={},
            idempotency_key='snapshot-1',
            estado_contable='contabilizado',
        )
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100000.00',
            monto_calculado='10000.00',
            estado_preparacion='preparado',
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='preparado',
        )

        response = self.client.get(reverse('contabilidad-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['regimenes_tributarios']), 1)
        self.assertEqual(len(response.data['configuraciones_fiscales']), 1)
        self.assertEqual(len(response.data['cuentas_contables']), 3)
        self.assertEqual(len(response.data['reglas_contables']), 1)
        self.assertEqual(len(response.data['matrices_reglas']), 1)
        self.assertEqual(len(response.data['eventos_contables']), 1)
        self.assertEqual(len(response.data['obligaciones_mensuales']), 1)
        self.assertEqual(len(response.data['cierres_mensuales']), 1)

    def test_control_snapshot_refresh_bypasses_cached_mode_payload(self):
        empresa = self._create_active_empresa(nombre='SnapshotRefreshCo', rut='73737374-7')
        self._setup_contabilidad(empresa)

        initial = self.client.get(f"{reverse('contabilidad-snapshot')}?mode=core")
        self.assertEqual(initial.status_code, status.HTTP_200_OK)
        self.assertEqual(len(initial.data['configuraciones_fiscales']), 1)

        ConfiguracionFiscalEmpresa.objects.create(
            empresa=self._create_active_empresa(nombre='SnapshotRefreshCo2', rut='73737375-7'),
            regimen_tributario=ensure_default_regime(),
            afecta_iva_arriendo=False,
            tasa_iva='0.00',
            aplica_ppm=True,
            ddjj_habilitadas=[],
            inicio_ejercicio='2026-01-01',
            moneda_funcional='CLP',
            estado='activa',
        )

        cached = self.client.get(f"{reverse('contabilidad-snapshot')}?mode=core")
        self.assertEqual(cached.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cached.data['configuraciones_fiscales']), 1)

        refreshed = self.client.get(f"{reverse('contabilidad-snapshot')}?mode=core&refresh=1")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertEqual(len(refreshed.data['configuraciones_fiscales']), 2)

    def test_retry_post_after_setup_creates_balanced_asiento(self):
        empresa = self._create_active_empresa(nombre='RetryCo', rut='99999999-9')
        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': '2',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'manual-retry-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event_id = response.data['id']

        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        retry = self.client.post(reverse('contabilidad-evento-post', args=[event_id]), format='json')
        self.assertEqual(retry.status_code, status.HTTP_200_OK)

        event = EventoContable.objects.get(pk=event_id)
        asiento = AsientoContable.objects.get(evento_contable=event)
        self.assertEqual(event.estado_contable, 'contabilizado')
        self.assertEqual(asiento.debe_total, asiento.haber_total)
        self.assertEqual(asiento.movimientos.count(), 2)

    def test_historical_event_stays_in_review_when_only_future_rule_exists(self):
        empresa = self._create_active_empresa(nombre='FutureRuleCo', rut='97979797-9')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(
            empresa,
            'PagoConciliadoArriendo',
            accounts['bancos'],
            accounts['cxc'],
            vigencia_desde='2026-02-01',
        )

        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'historical-before-rule',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'historical-before-rule',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = EventoContable.objects.get(pk=response.data['id'])
        self.assertEqual(event.estado_contable, 'pendiente_revision_contable')
        self.assertFalse(AsientoContable.objects.filter(evento_contable=event).exists())

    def test_historical_event_uses_rule_effective_on_operational_date(self):
        empresa = self._create_active_empresa(nombre='HistoricalRuleCo', rut='96969696-9')
        accounts = self._setup_contabilidad(empresa)
        caja_transitoria = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='1102',
            nombre='Caja Transitoria',
            naturaleza='deudora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )
        pasivo_diferido = CuentaContable.objects.create(
            empresa=empresa,
            plan_cuentas_version='v1',
            codigo='2102',
            nombre='Pasivo Diferido',
            naturaleza='acreedora',
            nivel=1,
            estado='activa',
            es_control_obligatoria=True,
        )

        self._create_rule_matrix(
            empresa,
            'PagoConciliadoArriendo',
            accounts['bancos'],
            accounts['cxc'],
            vigencia_desde='2026-01-01',
            vigencia_hasta='2026-01-31',
        )
        self._create_rule_matrix(
            empresa,
            'PagoConciliadoArriendo',
            caja_transitoria,
            pasivo_diferido,
            vigencia_desde='2026-02-01',
        )

        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'historical-correct-rule',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'historical-correct-rule',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = EventoContable.objects.get(pk=response.data['id'])
        asiento = AsientoContable.objects.get(evento_contable=event)
        account_codes = sorted(asiento.movimientos.values_list('cuenta_contable__codigo', flat=True))

        self.assertEqual(event.estado_contable, 'contabilizado')
        self.assertEqual(account_codes, ['1101', '1201'])

    def test_payment_reconciliation_auto_generates_posted_event(self):
        empresa = self._create_active_empresa(nombre='PayCo', rut='77777777-7')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        contrato, cuenta = self._create_contract_with_company_admin(empresa, codigo='LED-PAY')
        self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-pay',
            estado_conexion='activa',
            primaria_movimientos=True,
        )

        movimiento = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '100111.00',
                'descripcion_origen': 'Pago exacto',
            },
            format='json',
        )
        self.assertEqual(movimiento.status_code, status.HTTP_201_CREATED)

        event = EventoContable.objects.get(evento_tipo='PagoConciliadoArriendo')
        asiento = AsientoContable.objects.get(evento_contable=event)
        self.assertEqual(event.estado_contable, 'contabilizado')
        self.assertEqual(asiento.movimientos.count(), 2)

    def test_guarantee_movement_auto_generates_posted_event(self):
        empresa = self._create_active_empresa(nombre='GarCo', rut='66666666-6')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'GarantiaRecibida', accounts['bancos'], accounts['garantias'])

        contrato, _ = self._create_contract_with_company_admin(empresa, codigo='LED-GAR')
        garantia = self.client.post(
            reverse('cobranza-garantia-list'),
            {'contrato': contrato.id, 'monto_pactado': '100000.00'},
            format='json',
        )
        self.assertEqual(garantia.status_code, status.HTTP_201_CREATED)

        movimiento = self.client.post(
            reverse('cobranza-garantia-movimiento', args=[garantia.data['id']]),
            {'tipo_movimiento': 'deposito', 'monto_clp': '100000.00', 'fecha': '2026-01-01'},
            format='json',
        )
        self.assertEqual(movimiento.status_code, status.HTTP_201_CREATED)

        event = EventoContable.objects.get(evento_tipo='GarantiaRecibida')
        asiento = AsientoContable.objects.get(evento_contable=event)
        self.assertEqual(event.estado_contable, 'contabilizado')
        self.assertEqual(str(asiento.debe_total), '100000.00')
        self.assertEqual(asiento.movimientos.count(), 2)

    def test_prepare_monthly_close_fails_when_events_are_pending(self):
        empresa = self._create_active_empresa(nombre='CloseCo', rut='55555555-5')
        self._setup_contabilidad(empresa)
        self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'pending-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'close-pending-1',
            },
            format='json',
        )
        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prepare_monthly_close_creates_ppm_obligation_and_snapshots(self):
        empresa = self._create_active_empresa(nombre='MonthlyCo', rut='45454545-4')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        contrato, cuenta = self._create_contract_with_company_admin(empresa, codigo='LED-MONTH')
        self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-close',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '100111.00',
                'descripcion_origen': 'Pago exacto cierre',
            },
            format='json',
        )

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        close = CierreMensualContable.objects.get(empresa=empresa, anio=2026, mes=1)
        obligation = ObligacionTributariaMensual.objects.get(empresa=empresa, anio=2026, mes=1, obligacion_tipo='PPM')
        self.assertEqual(close.estado, 'preparado')
        self.assertEqual(str(obligation.base_imponible), '100111.00')
        self.assertEqual(str(obligation.monto_calculado), '10011.10')
        self.assertEqual(obligation.estado_preparacion, 'preparado')

    def test_end_to_end_payment_reconciliation_close_lifecycle(self):
        empresa = self._create_active_empresa(nombre='WorkflowCo', rut='43434343-4')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        contrato, cuenta = self._create_contract_with_company_admin(empresa, codigo='LED-WORKFLOW')
        generate = self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(generate.status_code, status.HTTP_201_CREATED)

        pago = PagoMensual.objects.get(pk=generate.data['id'])
        self.assertEqual(pago.estado_pago, EstadoPago.PENDING)
        self.assertEqual(pago.distribuciones_cobro.count(), 1)

        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-workflow',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        movimiento_response = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '100111.00',
                'descripcion_origen': 'Pago exacto workflow',
            },
            format='json',
        )
        self.assertEqual(movimiento_response.status_code, status.HTTP_201_CREATED)

        pago.refresh_from_db()
        movimiento = MovimientoBancarioImportado.objects.get(pk=movimiento_response.data['id'])
        distribucion_empresa = pago.distribuciones_cobro.get(beneficiario_empresa_owner=empresa)
        event = EventoContable.objects.get(evento_tipo='PagoConciliadoArriendo', empresa=empresa)
        asiento = AsientoContable.objects.get(evento_contable=event)

        self.assertEqual(pago.estado_pago, EstadoPago.PAID)
        self.assertEqual(str(pago.monto_pagado_clp), '100111.00')
        self.assertEqual(movimiento.estado_conciliacion, 'conciliado_exacto')
        self.assertEqual(movimiento.pago_mensual_id, pago.id)
        self.assertEqual(str(distribucion_empresa.monto_conciliado_clp), '100111.00')
        self.assertEqual(event.estado_contable, 'contabilizado')
        self.assertEqual(str(asiento.debe_total), '100111.00')
        self.assertEqual(str(asiento.haber_total), '100111.00')
        self.assertEqual(asiento.movimientos.count(), 2)

        prepare = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(prepare.status_code, status.HTTP_200_OK)

        close = CierreMensualContable.objects.get(empresa=empresa, anio=2026, mes=1)
        obligation = ObligacionTributariaMensual.objects.get(empresa=empresa, anio=2026, mes=1, obligacion_tipo='PPM')
        libro_diario = LibroDiario.objects.get(empresa=empresa, periodo='2026-01')
        libro_mayor = LibroMayor.objects.get(empresa=empresa, periodo='2026-01')
        balance = BalanceComprobacion.objects.get(empresa=empresa, periodo='2026-01')

        self.assertEqual(close.estado, 'preparado')
        self.assertEqual(close.resumen_obligaciones['snapshots']['libro_diario'], '2026-01')
        self.assertEqual(close.resumen_obligaciones['snapshots']['libro_mayor'], '2026-01')
        self.assertEqual(close.resumen_obligaciones['snapshots']['balance_comprobacion'], '2026-01')
        self.assertEqual(str(obligation.base_imponible), '100111.00')
        self.assertEqual(str(obligation.monto_calculado), '10011.10')
        self.assertEqual(obligation.estado_preparacion, 'preparado')
        self.assertEqual(len(libro_diario.resumen['asientos']), 1)
        self.assertEqual(len(libro_mayor.resumen['cuentas']), 2)
        self.assertTrue(balance.resumen['cuadrado'])

        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[close.id]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        close.refresh_from_db()
        self.assertEqual(close.estado, 'aprobado')
        self.assertIsNotNone(close.fecha_aprobacion)

        reopen = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[close.id]),
            format='json',
        )
        self.assertEqual(reopen.status_code, status.HTTP_200_OK)
        close.refresh_from_db()
        self.assertEqual(close.estado, 'reabierto')

    def test_prepare_and_approve_and_reopen_monthly_close(self):
        empresa = self._create_active_empresa(nombre='ApproveCo', rut='56565656-5')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'close-approve-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'close-approve-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        prepare = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(prepare.status_code, status.HTTP_200_OK)

        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        self.assertEqual(approve.data['estado'], 'aprobado')

        reopen = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(reopen.status_code, status.HTTP_200_OK)
        self.assertEqual(reopen.data['estado'], 'reabierto')

    def test_prepare_monthly_close_rejects_already_approved_period(self):
        empresa = self._create_active_empresa(nombre='ApproveLockedCo', rut='57575757-5')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        event_response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'lock-close-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'lock-close-1',
            },
            format='json',
        )
        self.assertEqual(event_response.status_code, status.HTTP_201_CREATED)

        prepare = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(prepare.status_code, status.HTTP_200_OK)
        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)

        second_prepare = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(second_prepare.status_code, status.HTTP_400_BAD_REQUEST)

    def test_event_created_after_approved_close_stays_in_review_without_asiento(self):
        empresa = self._create_active_empresa(nombre='ApprovedPeriodCo', rut='58585858-5')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        seed_event = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'approved-period-seed',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'approved-period-seed',
            },
            format='json',
        )
        self.assertEqual(seed_event.status_code, status.HTTP_201_CREATED)

        prepare = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(prepare.status_code, status.HTTP_200_OK)
        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)

        late_event = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'approved-period-late',
                'fecha_operativa': '2026-01-20',
                'moneda': 'CLP',
                'monto_base': '50000.00',
                'payload_resumen': {},
                'idempotency_key': 'approved-period-late',
            },
            format='json',
        )
        self.assertEqual(late_event.status_code, status.HTTP_201_CREATED)
        event = EventoContable.objects.get(pk=late_event.data['id'])
        self.assertEqual(event.estado_contable, 'pendiente_revision_contable')
        self.assertFalse(AsientoContable.objects.filter(evento_contable=event).exists())

    def test_scoped_reviewer_lists_only_obligaciones_for_assigned_company(self):
        empresa_a = self._create_active_empresa(nombre='Scope Ledger A', rut='61111111-1')
        empresa_b = self._create_active_empresa(nombre='Scope Ledger B', rut='62222222-2')
        ObligacionTributariaMensual.objects.create(
            empresa=empresa_a,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100000.00',
            monto_calculado='10000.00',
            estado_preparacion='preparado',
        )
        ObligacionTributariaMensual.objects.create(
            empresa=empresa_b,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='200000.00',
            monto_calculado='20000.00',
            estado_preparacion='preparado',
        )

        user_model = get_user_model()
        reviewer = user_model.objects.create_user(
            username='ledger-reviewer',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        self._assign_company_scope_reviewer(reviewer, empresa_a)
        self.client.force_authenticate(reviewer)

        response = self.client.get(reverse('contabilidad-obligacion-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['empresa'], empresa_a.id)

    def test_scoped_reviewer_lists_books_only_for_assigned_company(self):
        empresa_a = self._create_active_empresa(nombre='Scope Books A', rut='63333333-3')
        empresa_b = self._create_active_empresa(nombre='Scope Books B', rut='64444444-4')
        LibroDiario.objects.create(empresa=empresa_a, periodo='2026-01', estado_snapshot='preparado', resumen={'empresa': 'A'})
        LibroDiario.objects.create(empresa=empresa_b, periodo='2026-01', estado_snapshot='preparado', resumen={'empresa': 'B'})
        LibroMayor.objects.create(empresa=empresa_a, periodo='2026-01', estado_snapshot='preparado', resumen={'empresa': 'A'})
        LibroMayor.objects.create(empresa=empresa_b, periodo='2026-01', estado_snapshot='preparado', resumen={'empresa': 'B'})
        BalanceComprobacion.objects.create(empresa=empresa_a, periodo='2026-01', estado_snapshot='preparado', resumen={'empresa': 'A'})
        BalanceComprobacion.objects.create(empresa=empresa_b, periodo='2026-01', estado_snapshot='preparado', resumen={'empresa': 'B'})

        user_model = get_user_model()
        reviewer = user_model.objects.create_user(
            username='books-reviewer',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        self._assign_company_scope_reviewer(reviewer, empresa_a)
        self.client.force_authenticate(reviewer)

        libro_diario = self.client.get(reverse('contabilidad-libro-diario-list'))
        libro_mayor = self.client.get(reverse('contabilidad-libro-mayor-list'))
        balance = self.client.get(reverse('contabilidad-balance-list'))

        self.assertEqual(libro_diario.status_code, status.HTTP_200_OK)
        self.assertEqual(libro_mayor.status_code, status.HTTP_200_OK)
        self.assertEqual(balance.status_code, status.HTTP_200_OK)
        self.assertEqual([item['empresa'] for item in libro_diario.data], [empresa_a.id])
        self.assertEqual([item['empresa'] for item in libro_mayor.data], [empresa_a.id])
        self.assertEqual([item['empresa'] for item in balance.data], [empresa_a.id])
