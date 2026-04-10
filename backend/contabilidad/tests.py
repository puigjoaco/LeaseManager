from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cobranza.models import GarantiaContractual
from conciliacion.models import ConexionBancaria
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .models import AsientoContable, CierreMensualContable, ConfiguracionFiscalEmpresa, CuentaContable, EventoContable, ObligacionTributariaMensual
from .services import DEFAULT_REGIME_CODE, ensure_default_regime


class ContabilidadAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='ledger', password='secret123')
        self.client.force_authenticate(self.user)

    def _create_socio(self, nombre, rut, activo=True):
        return Socio.objects.create(nombre=nombre, rut=rut, activo=activo)

    def _create_active_empresa(self, nombre='LedgerCo', rut='88888888-8'):
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

    def _create_rule_matrix(self, empresa, event_type, debit_account, credit_account):
        regla = self.client.post(
            reverse('contabilidad-regla-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': event_type,
                'plan_cuentas_version': 'v1',
                'criterio_cargo': debit_account.codigo,
                'criterio_abono': credit_account.codigo,
                'vigencia_desde': '2026-01-01',
                'estado': 'activa',
            },
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
