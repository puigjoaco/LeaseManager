from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import ManualResolution
from cobranza.models import EstadoPago, GarantiaContractual, PagoMensual
from conciliacion.models import (
    ConexionBancaria,
    CuadraturaBancaria,
    EstadoCuadraturaBancaria,
    MovimientoBancarioImportado,
)
from core.models import Role, Scope, UserScopeAssignment
from core.reference_validation import REDACTED_SENSITIVE_REFERENCE
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import Empresa, ParticipacionPatrimonial, Propiedad, Socio, TipoInmueble

from .admin import (
    AsientoContableAdmin,
    BalanceComprobacionAdmin,
    CierreMensualContableAdmin,
    ConfiguracionFiscalEmpresaAdmin,
    CuentaContableAdmin,
    EfectoReaperturaCierreMensualAdmin,
    EventoContableAdmin,
    LibroDiarioAdmin,
    LibroMayorAdmin,
    LineaLiquidacionMensualAdmin,
    LiquidacionMensualAdmin,
    MatrizReglasContablesAdmin,
    MovimientoAsientoAdmin,
    ObligacionTributariaMensualAdmin,
    PoliticaReversoContableAdmin,
    RegimenTributarioEmpresaAdmin,
    ReglaContableAdmin,
)
from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EfectoReaperturaCierreMensual,
    EstadoLiquidacionMensual,
    EstadoEventoContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    LineaLiquidacionMensual,
    LiquidacionMensual,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
    TipoLineaLiquidacion,
    TipoMovimientoAsiento,
    TipoOwnerLiquidacion,
)
from .services import (
    DEFAULT_REGIME_CODE,
    MONTHLY_CLOSE_REOPEN_POLICY_TYPE,
    MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
    ensure_default_regime,
)


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

    def _allow_monthly_close_reopen(self, empresa):
        return PoliticaReversoContable.objects.create(
            empresa=empresa,
            tipo_ajuste=MONTHLY_CLOSE_REOPEN_POLICY_TYPE,
            usa_reverso=True,
            usa_asiento_complementario=True,
            permite_reapertura=True,
            aprobacion_requerida=True,
            ventana_operativa='periodo-siguiente-controlado',
            estado='activa',
        )

    def _reopen_effect_payload(self, suffix='1'):
        return {
            'tipo_efecto': 'reverso',
            'monto_efecto': '100000.00',
            'motivo': f'reapertura-controlada-{suffix}',
            'efecto_esperado': f'reverso-posterior-controlado-{suffix}',
            'evidencia_ref': f'stage5-reopen-evidence-{suffix}',
        }

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
            autoridad_operativa_nombre='Representante Operativo',
            autoridad_operativa_rut='12345678-5',
            autoridad_operativa_evidencia_ref='mandate-authority-act-001',
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

    def _create_squared_bank_reconciliation(self, cuenta, amount='0.00', suffix='close'):
        return CuadraturaBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            periodo_economico='2026-01',
            fecha_cuadratura=date(2026, 1, 31),
            saldo_sistema_clp=amount,
            saldo_banco_clp=amount,
            estado=EstadoCuadraturaBancaria.SQUARED,
            evidencia_cuadratura_ref=f'bank-square-evidence-{suffix}',
            responsable_ref=f'bank-square-owner-{suffix}',
        )

    def _create_company_liquidation_for_close(self, empresa, close):
        if not isinstance(close, CierreMensualContable):
            close = CierreMensualContable.objects.get(pk=close)
        liquidation = LiquidacionMensual(
            owner_tipo=TipoOwnerLiquidacion.COMPANY,
            empresa=empresa,
            cierre_contable=close,
            anio=close.anio,
            mes=close.mes,
            estado=EstadoLiquidacionMensual.PREPARED,
            comision_administracion_aplica=False,
            saldo_final_clp=Decimal('0.00'),
            evidencia_base_ref=f'stage5-liquidation-base-{close.pk}',
            responsable_ref=f'stage5-liquidation-owner-{close.pk}',
        )
        liquidation.full_clean()
        liquidation.save()
        return liquidation

    def _post_manual_accounting_event(self, empresa, suffix, amount='100000.00'):
        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': f'atomicity-{suffix}',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': amount,
                'payload_resumen': {},
                'idempotency_key': f'atomicity-{suffix}',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    def _prepare_monthly_close_for_audit_tests(self, suffix, *, with_reopen_rule=False):
        empresa = self._create_active_empresa(
            nombre=f'AtomicClose{suffix}',
            rut=f'78{suffix[-6:].zfill(6)}-5',
        )
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        if with_reopen_rule:
            self._create_rule_matrix(
                empresa,
                MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
                accounts['cxc'],
                accounts['bancos'],
                vigencia_desde='2026-02-01',
            )
        self._post_manual_accounting_event(empresa, suffix)
        prepare = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(prepare.status_code, status.HTTP_200_OK)
        return empresa, accounts, CierreMensualContable.objects.get(pk=prepare.data['id'])

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

    def test_account_create_rolls_back_when_view_audit_fails(self):
        empresa = self._create_active_empresa(nombre='AccountAuditFailCo', rut='78111111-1')
        payload = {
            'empresa': empresa.id,
            'plan_cuentas_version': 'v1',
            'codigo': '1999',
            'nombre': 'Cuenta sin auditoria',
            'naturaleza': 'deudora',
            'nivel': 1,
            'estado': 'activa',
        }

        with patch('contabilidad.views.create_audit_event', side_effect=RuntimeError('account audit unavailable')):
            with self.assertRaisesRegex(RuntimeError, 'account audit unavailable'):
                self.client.post(reverse('contabilidad-cuenta-list'), payload, format='json')

        self.assertFalse(CuentaContable.objects.filter(empresa=empresa, codigo='1999').exists())

    def test_event_create_rolls_back_when_post_attempt_audit_fails(self):
        empresa = self._create_active_empresa(nombre='EventAuditFailCo', rut='78222222-2')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])

        def fail_post_attempt_audit(**kwargs):
            if kwargs['event_type'] == 'contabilidad.evento_contable.post_attempted':
                raise RuntimeError('post attempt audit unavailable')
            return None

        with patch('contabilidad.views.create_audit_event', side_effect=fail_post_attempt_audit):
            with self.assertRaisesRegex(RuntimeError, 'post attempt audit unavailable'):
                self.client.post(
                    reverse('contabilidad-evento-list'),
                    {
                        'empresa': empresa.id,
                        'evento_tipo': 'PagoConciliadoArriendo',
                        'entidad_origen_tipo': 'manual',
                        'entidad_origen_id': 'post-attempt-audit-fail',
                        'fecha_operativa': '2026-01-10',
                        'moneda': 'CLP',
                        'monto_base': '100000.00',
                        'payload_resumen': {},
                        'idempotency_key': 'post-attempt-audit-fail',
                    },
                    format='json',
                )

        self.assertFalse(EventoContable.objects.filter(idempotency_key='post-attempt-audit-fail').exists())
        self.assertFalse(
            AsientoContable.objects.filter(evento_contable__idempotency_key='post-attempt-audit-fail').exists()
        )

    def test_event_post_retry_rolls_back_when_view_audit_fails(self):
        empresa = self._create_active_empresa(nombre='EventRetryAuditFailCo', rut='78233333-3')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='post-retry-audit-fail',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100000.00',
            payload_resumen={},
            idempotency_key='post-retry-audit-fail',
            estado_contable=EstadoEventoContable.REVIEW,
        )

        def fail_post_retry_audit(**kwargs):
            if kwargs['event_type'] == 'contabilidad.evento_contable.post_retried':
                raise RuntimeError('post retry audit unavailable')
            return None

        with patch('contabilidad.views.create_audit_event', side_effect=fail_post_retry_audit):
            with self.assertRaisesRegex(RuntimeError, 'post retry audit unavailable'):
                self.client.post(reverse('contabilidad-evento-post', args=[event.id]), format='json')

        event.refresh_from_db()
        self.assertEqual(event.estado_contable, EstadoEventoContable.REVIEW)
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

    def test_manual_event_rejects_sensitive_payload_on_write(self):
        empresa = self._create_active_empresa(nombre='PayloadRejectCo', rut='75757575-5')

        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'sensitive-write',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {'access_token': 'opaque-value'},
                'idempotency_key': 'sensitive-write',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('payload_resumen', response.data)

    def test_posting_duplicate_origin_event_keeps_second_event_in_review(self):
        empresa = self._create_active_empresa(nombre='DedupLedgerCo', rut='53535353-5')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(
            empresa,
            'PagoConciliadoArriendo',
            accounts['bancos'],
            accounts['cxc'],
        )
        base_payload = {
            'empresa': empresa.id,
            'evento_tipo': 'PagoConciliadoArriendo',
            'entidad_origen_tipo': 'pago_mensual',
            'entidad_origen_id': 'payment-dedup-001',
            'fecha_operativa': '2026-01-10',
            'moneda': 'CLP',
            'monto_base': '100000.00',
            'payload_resumen': {},
        }

        first = self.client.post(
            reverse('contabilidad-evento-list'),
            {**base_payload, 'idempotency_key': 'payment-dedup-001-a'},
            format='json',
        )
        second = self.client.post(
            reverse('contabilidad-evento-list'),
            {**base_payload, 'idempotency_key': 'payment-dedup-001-b'},
            format='json',
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        first_event = EventoContable.objects.get(pk=first.data['id'])
        second_event = EventoContable.objects.get(pk=second.data['id'])
        self.assertEqual(first_event.estado_contable, EstadoEventoContable.POSTED)
        self.assertEqual(second_event.estado_contable, EstadoEventoContable.REVIEW)
        self.assertTrue(AsientoContable.objects.filter(evento_contable=first_event).exists())
        self.assertFalse(AsientoContable.objects.filter(evento_contable=second_event).exists())

    def test_posted_duplicate_origin_event_fails_model_validation(self):
        empresa = self._create_active_empresa(nombre='PostedDedupCo', rut='54545454-6')
        EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='pago_mensual',
            entidad_origen_id='payment-dedup-validation',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100000.00',
            payload_resumen={},
            idempotency_key='payment-dedup-validation-a',
            estado_contable=EstadoEventoContable.POSTED,
        )
        duplicate = EventoContable(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='pago_mensual',
            entidad_origen_id='payment-dedup-validation',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100000.00',
            payload_resumen={},
            idempotency_key='payment-dedup-validation-b',
            estado_contable=EstadoEventoContable.POSTED,
        )

        with self.assertRaises(ValidationError) as context:
            duplicate.full_clean()

        self.assertIn('entidad_origen_id', context.exception.message_dict)

    def test_accounting_apis_redact_inherited_sensitive_payloads_and_refs(self):
        empresa = self._create_active_empresa(nombre='RedactionLedgerCo', rut='76767676-6')
        accounts = self._setup_contabilidad(empresa)
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='redaction-1',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base='100000.00',
            payload_resumen={
                'callback': 'https://ledger.example.test/event?token=secret',
                'safe_ref': 'ledger-controlled-ref',
            },
            idempotency_key='redaction-event-1',
            estado_contable='contabilizado',
        )
        asiento = AsientoContable.objects.create(
            evento_contable=event,
            fecha_contable='2026-01-10',
            periodo_contable='2026-01',
            estado='contabilizado',
            debe_total='100000.00',
            haber_total='100000.00',
            moneda_funcional='CLP',
        )
        MovimientoAsiento.objects.create(
            asiento_contable=asiento,
            cuenta_contable=accounts['bancos'],
            tipo_movimiento=TipoMovimientoAsiento.DEBIT,
            monto='100000.00',
            glosa='Centro heredado sensible',
            centro_resultado_ref='https://ledger.example.test/center?token=secret',
        )
        ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible='100000.00',
            monto_calculado='10000.00',
            estado_preparacion='preparado',
            detalle_calculo={
                'callback': 'https://tax.example.test/calc?token=secret',
                'safe_ref': 'tax-controlled-ref',
            },
        )
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
            resumen={'cuadrado': True, 'api_key': 'secret-api-key-value'},
        )
        CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
            resumen_obligaciones={'callback': 'https://close.example.test/summary?token=secret'},
        )

        responses = {
            'eventos': self.client.get(reverse('contabilidad-evento-list')),
            'asientos': self.client.get(reverse('contabilidad-asiento-list')),
            'obligaciones': self.client.get(reverse('contabilidad-obligacion-list')),
            'diario': self.client.get(reverse('contabilidad-libro-diario-list')),
            'mayor': self.client.get(reverse('contabilidad-libro-mayor-list')),
            'balance': self.client.get(reverse('contabilidad-balance-list')),
            'cierres': self.client.get(reverse('contabilidad-cierre-list')),
        }

        for response in responses.values():
            self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(responses['eventos'].data[0]['payload_resumen']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(responses['eventos'].data[0]['payload_resumen']['safe_ref'], 'ledger-controlled-ref')
        self.assertEqual(
            responses['asientos'].data[0]['movimientos'][0]['centro_resultado_ref'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(
            responses['obligaciones'].data[0]['detalle_calculo']['callback'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertEqual(responses['diario'].data[0]['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(responses['diario'].data[0]['resumen']['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(responses['diario'].data[0]['resumen']['safe_ref'], 'diario-controlled-ref')
        self.assertEqual(responses['mayor'].data[0]['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(responses['mayor'].data[0]['resumen']['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(responses['balance'].data[0]['storage_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(responses['balance'].data[0]['resumen']['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(
            responses['cierres'].data[0]['resumen_obligaciones']['callback'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        rendered = ''.join(str(response.data) for response in responses.values())
        self.assertNotIn('ledger.example.test', rendered)
        self.assertNotIn('storage.example.test', rendered)
        self.assertNotIn('secret-api-key-value', rendered)

    def test_accounting_configuration_admins_block_manual_delete(self):
        site = AdminSite()

        for admin_instance in (
            RegimenTributarioEmpresaAdmin(RegimenTributarioEmpresa, site),
            ConfiguracionFiscalEmpresaAdmin(ConfiguracionFiscalEmpresa, site),
            CuentaContableAdmin(CuentaContable, site),
            ReglaContableAdmin(ReglaContable, site),
            MatrizReglasContablesAdmin(MatrizReglasContables, site),
            PoliticaReversoContableAdmin(PoliticaReversoContable, site),
        ):
            self.assertFalse(admin_instance.has_delete_permission(None))
            self.assertFalse(admin_instance.has_delete_permission(None, obj=object()))

    def test_accounting_admin_redacts_sensitive_payloads_and_refs(self):
        empresa = self._create_active_empresa(nombre='AdminRedactLedgerCo', rut='74747474-4')
        accounts = self._setup_contabilidad(empresa)
        event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo='PagoConciliadoArriendo',
            entidad_origen_tipo='manual',
            entidad_origen_id='admin-redaction-1',
            fecha_operativa='2026-01-10',
            moneda='CLP',
            monto_base=Decimal('100000.00'),
            payload_resumen={'callback': 'https://ledger.example.test/event?token=secret'},
            idempotency_key='admin-redaction-event-1',
            estado_contable=EstadoEventoContable.POSTED,
        )
        asiento = AsientoContable.objects.create(
            evento_contable=event,
            fecha_contable='2026-01-10',
            periodo_contable='2026-01',
            estado='contabilizado',
            debe_total=Decimal('100000.00'),
            haber_total=Decimal('100000.00'),
            moneda_funcional='CLP',
        )
        movimiento = MovimientoAsiento.objects.create(
            asiento_contable=asiento,
            cuenta_contable=accounts['bancos'],
            tipo_movimiento=TipoMovimientoAsiento.DEBIT,
            monto=Decimal('100000.00'),
            glosa='Centro heredado sensible',
            centro_resultado_ref='https://ledger.example.test/center?token=secret',
        )
        obligacion = ObligacionTributariaMensual.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            obligacion_tipo='PPM',
            base_imponible=Decimal('100000.00'),
            monto_calculado=Decimal('10000.00'),
            estado_preparacion='preparado',
            detalle_calculo={'api_key': 'secret-api-key-value'},
        )
        libro_diario = LibroDiario.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            storage_ref='https://storage.example.test/diario.pdf?token=secret',
            resumen={'authorization': 'Bearer inherited-ledger-value'},
        )
        libro_mayor = LibroMayor.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            storage_ref='https://storage.example.test/mayor.pdf?token=secret',
            resumen={'callback': 'https://storage.example.test/mayor?token=secret'},
        )
        balance = BalanceComprobacion.objects.create(
            empresa=empresa,
            periodo='2026-01',
            estado_snapshot='aprobado',
            storage_ref='https://storage.example.test/balance.pdf?token=secret',
            resumen={'api_key': 'secret-api-key-value'},
        )
        cierre = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='aprobado',
            resumen_obligaciones={'callback': 'https://close.example.test/summary?token=secret'},
        )
        policy = self._allow_monthly_close_reopen(empresa)
        effect_event = EventoContable.objects.create(
            empresa=empresa,
            evento_tipo=MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
            entidad_origen_tipo='cierre_mensual_contable',
            entidad_origen_id=str(cierre.pk),
            fecha_operativa='2026-02-01',
            moneda='CLP',
            monto_base=Decimal('100000.00'),
            payload_resumen={'callback': 'https://close.example.test/reopen?token=secret'},
            idempotency_key='admin-redaction-reopen-event-1',
            estado_contable=EstadoEventoContable.POSTED,
        )
        effect = EfectoReaperturaCierreMensual.objects.create(
            cierre=cierre,
            politica_reverso=policy,
            evento_contable=effect_event,
            tipo_efecto='reverso',
            monto_efecto=Decimal('100000.00'),
            motivo='Motivo en https://close.example.test/reopen?token=secret',
            efecto_esperado='Esperado con token=secret',
            evidencia_ref='https://close.example.test/evidence?token=secret',
        )
        socio = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).first().participante_socio
        liquidacion = LiquidacionMensual.objects.create(
            owner_tipo=TipoOwnerLiquidacion.COMPANY,
            empresa=empresa,
            cierre_contable=cierre,
            anio=2026,
            mes=1,
            estado=EstadoLiquidacionMensual.APPROVED,
            comision_administracion_aplica=True,
            saldo_final_clp=Decimal('25000.00'),
            saldo_final_explicacion='Saldo con https://settlement.example.test/balance?token=secret',
            saldo_final_evidencia_ref='https://settlement.example.test/evidence?token=secret',
            evidencia_base_ref='https://settlement.example.test/base?token=secret',
            responsable_ref='mailto:controller@example.test',
        )
        linea_liquidacion = LineaLiquidacionMensual.objects.create(
            liquidacion=liquidacion,
            tipo_linea=TipoLineaLiquidacion.ADMINISTRATION_FEE,
            descripcion='Comision sensible https://settlement.example.test/fee?token=secret',
            monto_clp=Decimal('10000.00'),
            evidencia_ref='https://settlement.example.test/fee-evidence?token=secret',
            beneficiario_socio=socio,
            evento_contable=event,
        )
        site = AdminSite()

        event_admin = EventoContableAdmin(EventoContable, site)
        asiento_admin = AsientoContableAdmin(AsientoContable, site)
        movement_admin = MovimientoAsientoAdmin(MovimientoAsiento, site)
        obligation_admin = ObligacionTributariaMensualAdmin(ObligacionTributariaMensual, site)
        diario_admin = LibroDiarioAdmin(LibroDiario, site)
        mayor_admin = LibroMayorAdmin(LibroMayor, site)
        balance_admin = BalanceComprobacionAdmin(BalanceComprobacion, site)
        close_admin = CierreMensualContableAdmin(CierreMensualContable, site)
        effect_admin = EfectoReaperturaCierreMensualAdmin(EfectoReaperturaCierreMensual, site)
        liquidation_admin = LiquidacionMensualAdmin(LiquidacionMensual, site)
        liquidation_line_admin = LineaLiquidacionMensualAdmin(LineaLiquidacionMensual, site)

        self.assertNotIn('payload_resumen', event_admin.fields)
        self.assertEqual(event_admin.payload_resumen_redacted(event)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(event_admin.fields).issubset(set(event_admin.readonly_fields)))
        self.assertFalse(event_admin.has_add_permission(None))
        self.assertFalse(event_admin.has_change_permission(None, obj=event))
        self.assertFalse(event_admin.has_delete_permission(None))

        self.assertTrue(set(asiento_admin.fields).issubset(set(asiento_admin.readonly_fields)))
        self.assertFalse(asiento_admin.has_add_permission(None))
        self.assertFalse(asiento_admin.has_change_permission(None, obj=asiento))
        self.assertFalse(asiento_admin.has_delete_permission(None))

        self.assertNotIn('centro_resultado_ref', movement_admin.fields)
        self.assertEqual(movement_admin.centro_resultado_ref_redacted(movimiento), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(movement_admin.fields).issubset(set(movement_admin.readonly_fields)))
        self.assertFalse(movement_admin.has_add_permission(None))
        self.assertFalse(movement_admin.has_change_permission(None, obj=movimiento))
        self.assertFalse(movement_admin.has_delete_permission(None))

        self.assertNotIn('detalle_calculo', obligation_admin.fields)
        self.assertEqual(obligation_admin.detalle_calculo_redacted(obligacion)['api_key'], REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(obligation_admin.fields).issubset(set(obligation_admin.readonly_fields)))
        self.assertFalse(obligation_admin.has_add_permission(None))
        self.assertFalse(obligation_admin.has_change_permission(None, obj=obligacion))
        self.assertFalse(obligation_admin.has_delete_permission(None))

        for admin_instance, obj in (
            (diario_admin, libro_diario),
            (mayor_admin, libro_mayor),
            (balance_admin, balance),
        ):
            self.assertNotIn('storage_ref', admin_instance.fields)
            self.assertNotIn('resumen', admin_instance.fields)
            self.assertEqual(admin_instance.storage_ref_redacted(obj), REDACTED_SENSITIVE_REFERENCE)
            self.assertTrue(set(admin_instance.fields).issubset(set(admin_instance.readonly_fields)))
            self.assertFalse(admin_instance.has_add_permission(None))
            self.assertFalse(admin_instance.has_change_permission(None, obj=obj))
            self.assertFalse(admin_instance.has_delete_permission(None))

        self.assertEqual(diario_admin.resumen_redacted(libro_diario)['authorization'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(mayor_admin.resumen_redacted(libro_mayor)['callback'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(balance_admin.resumen_redacted(balance)['api_key'], REDACTED_SENSITIVE_REFERENCE)

        self.assertNotIn('resumen_obligaciones', close_admin.fields)
        self.assertEqual(
            close_admin.resumen_obligaciones_redacted(cierre)['callback'],
            REDACTED_SENSITIVE_REFERENCE,
        )
        self.assertTrue(set(close_admin.fields).issubset(set(close_admin.readonly_fields)))
        self.assertFalse(close_admin.has_add_permission(None))
        self.assertFalse(close_admin.has_change_permission(None, obj=cierre))
        self.assertFalse(close_admin.has_delete_permission(None))

        for raw_field in ('motivo', 'efecto_esperado', 'evidencia_ref'):
            self.assertNotIn(raw_field, effect_admin.fields)
            self.assertNotIn(raw_field, effect_admin.search_fields)
        self.assertEqual(effect_admin.motivo_redacted(effect), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(effect_admin.efecto_esperado_redacted(effect), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(effect_admin.evidencia_ref_redacted(effect), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(effect_admin.fields).issubset(set(effect_admin.readonly_fields)))
        self.assertFalse(effect_admin.has_add_permission(None))
        self.assertFalse(effect_admin.has_change_permission(None, obj=effect))
        self.assertFalse(effect_admin.has_delete_permission(None))

        for raw_field in (
            'saldo_final_explicacion',
            'saldo_final_evidencia_ref',
            'evidencia_base_ref',
            'responsable_ref',
        ):
            self.assertNotIn(raw_field, liquidation_admin.fields)
        self.assertEqual(liquidation_admin.saldo_final_explicacion_redacted(liquidacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_admin.saldo_final_evidencia_ref_redacted(liquidacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_admin.evidencia_base_ref_redacted(liquidacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_admin.responsable_ref_redacted(liquidacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(liquidation_admin.fields).issubset(set(liquidation_admin.readonly_fields)))
        self.assertFalse(liquidation_admin.has_add_permission(None))
        self.assertFalse(liquidation_admin.has_change_permission(None, obj=liquidacion))
        self.assertFalse(liquidation_admin.has_delete_permission(None))

        self.assertNotIn('descripcion', liquidation_line_admin.fields)
        self.assertNotIn('evidencia_ref', liquidation_line_admin.fields)
        self.assertEqual(liquidation_line_admin.descripcion_redacted(linea_liquidacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_line_admin.evidencia_ref_redacted(linea_liquidacion), REDACTED_SENSITIVE_REFERENCE)
        self.assertTrue(set(liquidation_line_admin.fields).issubset(set(liquidation_line_admin.readonly_fields)))
        self.assertFalse(liquidation_line_admin.has_add_permission(None))
        self.assertFalse(liquidation_line_admin.has_change_permission(None, obj=linea_liquidacion))
        self.assertFalse(liquidation_line_admin.has_delete_permission(None))

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

    def test_active_configuracion_fiscal_rejects_inactive_regime(self):
        empresa = self._create_active_empresa(nombre='FiscalInactiveRegimeCo', rut='79797979-4')
        regime = ensure_default_regime()
        regime.estado = 'inactiva'
        regime.save(update_fields=['estado', 'updated_at'])
        config = ConfiguracionFiscalEmpresa(
            empresa=empresa,
            regimen_tributario=regime,
            tasa_ppm_vigente='1.00',
            aplica_ppm=True,
            inicio_ejercicio='2026-01-01',
            estado='activa',
        )

        with self.assertRaises(ValidationError):
            config.full_clean()

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

    def test_liquidacion_prepared_requires_explicit_admin_fee_line(self):
        empresa = self._create_active_empresa(nombre='LiquidationPrepCo', rut='72727272-7')
        self._setup_contabilidad(empresa)
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='preparado',
            fecha_preparacion=timezone.now(),
        )

        direct_prepared = self.client.post(
            reverse('contabilidad-liquidacion-list'),
            {
                'owner_tipo': TipoOwnerLiquidacion.COMPANY,
                'empresa': empresa.id,
                'cierre_contable': close.id,
                'anio': 2026,
                'mes': 1,
                'estado': EstadoLiquidacionMensual.PREPARED,
                'comision_administracion_aplica': True,
                'evidencia_base_ref': 'liquidation-base-controlled-direct',
                'responsable_ref': 'liquidation-owner-controlled-direct',
            },
            format='json',
        )
        self.assertEqual(direct_prepared.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comision_administracion_aplica', direct_prepared.data)

        created = self.client.post(
            reverse('contabilidad-liquidacion-list'),
            {
                'owner_tipo': TipoOwnerLiquidacion.COMPANY,
                'empresa': empresa.id,
                'cierre_contable': close.id,
                'anio': 2026,
                'mes': 1,
                'estado': EstadoLiquidacionMensual.DRAFT,
                'comision_administracion_aplica': True,
                'evidencia_base_ref': 'liquidation-base-controlled-001',
                'responsable_ref': 'liquidation-owner-controlled-001',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        prepared = self.client.patch(
            reverse('contabilidad-liquidacion-detail', args=[created.data['id']]),
            {'estado': EstadoLiquidacionMensual.PREPARED},
            format='json',
        )

        self.assertEqual(prepared.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('comision_administracion_aplica', prepared.data)

    def test_liquidacion_prepared_requires_matching_final_balance_line(self):
        empresa = self._create_active_empresa(nombre='LiquidationBalanceCo', rut='72727274-7')
        self._setup_contabilidad(empresa)
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='preparado',
            fecha_preparacion=timezone.now(),
        )

        created = self.client.post(
            reverse('contabilidad-liquidacion-list'),
            {
                'owner_tipo': TipoOwnerLiquidacion.COMPANY,
                'empresa': empresa.id,
                'cierre_contable': close.id,
                'anio': 2026,
                'mes': 1,
                'estado': EstadoLiquidacionMensual.DRAFT,
                'comision_administracion_aplica': False,
                'saldo_final_clp': '25000.00',
                'saldo_final_explicacion': 'Saldo final por ajuste operacional controlado',
                'saldo_final_evidencia_ref': 'liquidation-final-balance-evidence-001',
                'evidencia_base_ref': 'liquidation-base-controlled-003',
                'responsable_ref': 'liquidation-owner-controlled-003',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        missing_line = self.client.patch(
            reverse('contabilidad-liquidacion-detail', args=[created.data['id']]),
            {'estado': EstadoLiquidacionMensual.PREPARED},
            format='json',
        )
        self.assertEqual(missing_line.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('saldo_final_clp', missing_line.data)

        line = self.client.post(
            reverse('contabilidad-linea-liquidacion-list'),
            {
                'liquidacion': created.data['id'],
                'tipo_linea': TipoLineaLiquidacion.FINAL_BALANCE,
                'descripcion': 'Saldo final explicado enero controlado',
                'monto_clp': '20000.00',
                'evidencia_ref': 'liquidation-final-balance-line-001',
            },
            format='json',
        )
        self.assertEqual(line.status_code, status.HTTP_201_CREATED)

        mismatched_line = self.client.patch(
            reverse('contabilidad-liquidacion-detail', args=[created.data['id']]),
            {'estado': EstadoLiquidacionMensual.PREPARED},
            format='json',
        )
        self.assertEqual(mismatched_line.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('saldo_final_clp', mismatched_line.data)

        updated_line = self.client.patch(
            reverse('contabilidad-linea-liquidacion-detail', args=[line.data['id']]),
            {'monto_clp': '25000.00'},
            format='json',
        )
        self.assertEqual(updated_line.status_code, status.HTTP_200_OK)

        prepared = self.client.patch(
            reverse('contabilidad-liquidacion-detail', args=[created.data['id']]),
            {'estado': EstadoLiquidacionMensual.PREPARED},
            format='json',
        )
        self.assertEqual(prepared.status_code, status.HTTP_200_OK)

    def test_liquidacion_api_creates_line_and_snapshot_redacts_sensitive_fields(self):
        empresa = self._create_active_empresa(nombre='LiquidationSnapshotCo', rut='72727273-7')
        self._setup_contabilidad(empresa)
        close = CierreMensualContable.objects.create(
            empresa=empresa,
            anio=2026,
            mes=1,
            estado='preparado',
            fecha_preparacion=timezone.now(),
        )
        socio = ParticipacionPatrimonial.objects.filter(empresa_owner=empresa).first().participante_socio

        created = self.client.post(
            reverse('contabilidad-liquidacion-list'),
            {
                'owner_tipo': TipoOwnerLiquidacion.COMPANY,
                'empresa': empresa.id,
                'cierre_contable': close.id,
                'anio': 2026,
                'mes': 1,
                'estado': EstadoLiquidacionMensual.DRAFT,
                'comision_administracion_aplica': True,
                'evidencia_base_ref': 'liquidation-base-controlled-002',
                'responsable_ref': 'liquidation-owner-controlled-002',
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)

        line = self.client.post(
            reverse('contabilidad-linea-liquidacion-list'),
            {
                'liquidacion': created.data['id'],
                'tipo_linea': TipoLineaLiquidacion.ADMINISTRATION_FEE,
                'descripcion': 'Comision administracion enero controlada',
                'monto_clp': '10000.00',
                'evidencia_ref': 'liquidation-fee-controlled-002',
                'beneficiario_socio': socio.id,
            },
            format='json',
        )
        self.assertEqual(line.status_code, status.HTTP_201_CREATED)

        LiquidacionMensual.objects.filter(pk=created.data['id']).update(
            saldo_final_explicacion='Saldo con https://settlement.example.test/balance?token=secret',
            saldo_final_evidencia_ref='https://settlement.example.test/evidence?token=secret',
            evidencia_base_ref='https://settlement.example.test/base?token=secret',
            responsable_ref='mailto:controller@example.test',
        )
        LineaLiquidacionMensual.objects.filter(pk=line.data['id']).update(
            descripcion='Comision sensible https://settlement.example.test/fee?token=secret',
            evidencia_ref='https://settlement.example.test/fee-evidence?token=secret',
        )

        snapshot = self.client.get(f"{reverse('contabilidad-snapshot')}?refresh=1")

        self.assertEqual(snapshot.status_code, status.HTTP_200_OK)
        liquidation_payload = next(
            item for item in snapshot.data['liquidaciones_mensuales'] if item['id'] == created.data['id']
        )
        line_payload = next(item for item in snapshot.data['lineas_liquidacion'] if item['id'] == line.data['id'])
        self.assertEqual(liquidation_payload['saldo_final_explicacion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_payload['saldo_final_evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_payload['evidencia_base_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(liquidation_payload['responsable_ref'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(line_payload['descripcion'], REDACTED_SENSITIVE_REFERENCE)
        self.assertEqual(line_payload['evidencia_ref'], REDACTED_SENSITIVE_REFERENCE)

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

    def test_asiento_full_clean_rejects_period_mismatch(self):
        empresa = self._create_active_empresa(nombre='PeriodCleanCo', rut='90909090-9')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'period-clean-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'period-clean-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        asiento = AsientoContable.objects.get(evento_contable_id=response.data['id'])
        asiento.periodo_contable = '2026-02'

        with self.assertRaises(ValidationError) as error:
            asiento.full_clean()

        self.assertIn('periodo_contable', error.exception.message_dict)

    def test_asiento_full_clean_rejects_stale_integrity_hash(self):
        empresa = self._create_active_empresa(nombre='HashCleanCo', rut='91919191-9')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'hash-clean-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'hash-clean-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        asiento = AsientoContable.objects.get(evento_contable_id=response.data['id'])
        asiento.fecha_contable = date(2026, 1, 11)

        with self.assertRaises(ValidationError) as error:
            asiento.full_clean()

        self.assertIn('hash_integridad', error.exception.message_dict)

    def test_movimiento_full_clean_rejects_account_from_other_company(self):
        empresa = self._create_active_empresa(nombre='MovementCompanyCo', rut='92929292-9')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'movement-company-clean-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'movement-company-clean-1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        other_empresa = self._create_active_empresa(nombre='MovementOtherCo', rut='93939393-9')
        other_accounts = self._setup_contabilidad(other_empresa)
        asiento = AsientoContable.objects.get(evento_contable_id=response.data['id'])
        movimiento = asiento.movimientos.get(tipo_movimiento=TipoMovimientoAsiento.DEBIT)
        movimiento.cuenta_contable = other_accounts['bancos']

        with self.assertRaises(ValidationError) as error:
            movimiento.full_clean()

        self.assertIn('cuenta_contable', error.exception.message_dict)

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
            evidencia_gate_ref='bank-gate-pay',
            prueba_conectividad_ref='bank-connectivity-pay',
            prueba_movimientos_ref='bank-movements-pay',
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
                'origen_importacion': 'manual_controlada',
                'evidencia_importacion_ref': 'manual-import-pay',
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

    def test_internal_transfer_resolution_auto_generates_accounting_events(self):
        origin_empresa = self._create_active_empresa(nombre='TransferOriginCo', rut='62626262-6')
        origin_accounts = self._setup_contabilidad(origin_empresa)
        self._create_rule_matrix(
            origin_empresa,
            'TransferenciaIntercuentaSalida',
            origin_accounts['cxc'],
            origin_accounts['bancos'],
        )
        origin_account = CuentaRecaudadora.objects.create(
            empresa_owner=origin_empresa,
            institucion='Banco Transfer',
            numero_cuenta='TRF-ORIGIN-001',
            tipo_cuenta='corriente',
            titular_nombre=origin_empresa.razon_social,
            titular_rut=origin_empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )

        destination_empresa = self._create_active_empresa(nombre='TransferDestCo', rut='63636363-6')
        destination_accounts = self._setup_contabilidad(destination_empresa)
        self._create_rule_matrix(
            destination_empresa,
            'TransferenciaIntercuentaEntrada',
            destination_accounts['bancos'],
            destination_accounts['cxc'],
        )
        destination_account = CuentaRecaudadora.objects.create(
            empresa_owner=destination_empresa,
            institucion='Banco Transfer',
            numero_cuenta='TRF-DEST-001',
            tipo_cuenta='corriente',
            titular_nombre=destination_empresa.razon_social,
            titular_rut=destination_empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )

        origin_connection = ConexionBancaria.objects.create(
            cuenta_recaudadora=origin_account,
            provider_key='origin-transfer-bank',
            credencial_ref='cred-transfer-origin',
            evidencia_gate_ref='gate-transfer-origin',
            prueba_conectividad_ref='connectivity-transfer-origin',
            prueba_movimientos_ref='movements-transfer-origin',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        destination_connection = ConexionBancaria.objects.create(
            cuenta_recaudadora=destination_account,
            provider_key='destination-transfer-bank',
            credencial_ref='cred-transfer-destination',
            evidencia_gate_ref='gate-transfer-destination',
            prueba_conectividad_ref='connectivity-transfer-destination',
            prueba_movimientos_ref='movements-transfer-destination',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        origin_movement = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=origin_connection,
            fecha_movimiento=date(2026, 1, 20),
            tipo_movimiento='cargo',
            monto='150000.00',
            descripcion_origen='Transferencia intercuenta enviada',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-transfer-origin',
            estado_conciliacion='manual_requerida',
        )
        destination_movement = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=destination_connection,
            fecha_movimiento=date(2026, 1, 20),
            tipo_movimiento='abono',
            monto='150000.00',
            descripcion_origen='Transferencia intercuenta recibida',
            origen_importacion='manual_controlada',
            evidencia_importacion_ref='manual-transfer-destination',
            estado_conciliacion='pendiente',
        )
        resolution = ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            scope_type='movimiento_bancario',
            scope_reference=str(origin_movement.pk),
            summary='Transferencia intercuenta requiere resolucion manual.',
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-internal-transfer', args=[resolution.pk]),
            {
                'movimiento_destino_id': destination_movement.pk,
                'periodo_economico': '2026-01',
                'criterio_conciliacion': 'Par cargo/abono entre cuentas recaudadoras de empresas.',
                'evidencia_transferencia_ref': 'transfer-evidence-controlled-001',
                'responsable_ref': 'accounting-owner-controlled',
                'rationale': 'Transferencia intercuenta con trazabilidad contable.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['evento_contable_ids']), 2)
        events = EventoContable.objects.filter(
            entidad_origen_tipo='transferencia_intercuenta',
            entidad_origen_id=str(response.data['transferencia_intercuenta_id']),
        ).order_by('evento_tipo')
        self.assertEqual(events.count(), 2)
        self.assertEqual({event.estado_contable for event in events}, {'contabilizado'})
        self.assertEqual(
            set(events.values_list('evento_tipo', flat=True)),
            {'TransferenciaIntercuentaEntrada', 'TransferenciaIntercuentaSalida'},
        )
        self.assertEqual(AsientoContable.objects.filter(evento_contable__in=events).count(), 2)
        resolution.refresh_from_db()
        self.assertEqual(sorted(resolution.metadata['evento_contable_ids']), sorted(response.data['evento_contable_ids']))

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

    def test_prepare_monthly_close_rejects_asiento_movement_total_mismatch(self):
        empresa = self._create_active_empresa(nombre='MovementMismatchCo', rut='46464646-4')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        event_response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'movement-mismatch-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'movement-mismatch-1',
            },
            format='json',
        )
        self.assertEqual(event_response.status_code, status.HTTP_201_CREATED)

        asiento = AsientoContable.objects.get(evento_contable_id=event_response.data['id'])
        movement = asiento.movimientos.get(tipo_movimiento='debe')
        movement.monto = Decimal('99999.00')
        movement.save(update_fields=['monto', 'updated_at'])

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('movimientos del asiento no cuadran', response.data['detail'])
        self.assertFalse(CierreMensualContable.objects.filter(empresa=empresa, anio=2026, mes=1).exists())

    def test_prepare_monthly_close_rejects_asiento_period_mismatch(self):
        empresa = self._create_active_empresa(nombre='MovementPeriodCo', rut='46464646-5')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        event_response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'period-mismatch-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'period-mismatch-1',
            },
            format='json',
        )
        self.assertEqual(event_response.status_code, status.HTTP_201_CREATED)

        asiento = AsientoContable.objects.get(evento_contable_id=event_response.data['id'])
        asiento.periodo_contable = '2026-02'
        asiento.save(update_fields=['periodo_contable', 'updated_at'])

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('periodo_contable', response.data['detail'])
        self.assertFalse(CierreMensualContable.objects.filter(empresa=empresa, anio=2026, mes=1).exists())

    def test_prepare_monthly_close_rejects_stale_asiento_hash(self):
        empresa = self._create_active_empresa(nombre='MovementHashCo', rut='46464646-6')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        event_response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'hash-mismatch-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'hash-mismatch-1',
            },
            format='json',
        )
        self.assertEqual(event_response.status_code, status.HTTP_201_CREATED)

        asiento = AsientoContable.objects.get(evento_contable_id=event_response.data['id'])
        asiento.fecha_contable = date(2026, 1, 11)
        asiento.save(update_fields=['fecha_contable', 'updated_at'])

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hash de integridad', response.data['detail'])
        self.assertFalse(CierreMensualContable.objects.filter(empresa=empresa, anio=2026, mes=1).exists())

    def test_prepare_monthly_close_rejects_cross_company_movement_account(self):
        empresa = self._create_active_empresa(nombre='MovementCompanyCo', rut='47474747-4')
        other_empresa = self._create_active_empresa(nombre='MovementOtherCo', rut='48484848-4')
        accounts = self._setup_contabilidad(empresa)
        other_accounts = self._setup_contabilidad(other_empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        event_response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'cross-company-movement-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'cross-company-movement-1',
            },
            format='json',
        )
        self.assertEqual(event_response.status_code, status.HTTP_201_CREATED)

        asiento = AsientoContable.objects.get(evento_contable_id=event_response.data['id'])
        movement = asiento.movimientos.get(tipo_movimiento='debe')
        movement.cuenta_contable = other_accounts['bancos']
        movement.save(update_fields=['cuenta_contable', 'updated_at'])

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cuentas de otra empresa', response.data['detail'])

    def test_prepare_monthly_close_fails_when_bank_movements_are_unresolved(self):
        empresa = self._create_active_empresa(nombre='BankOpenCo', rut='45454545-5')
        accounts = self._setup_contabilidad(empresa)
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        _, cuenta = self._create_contract_with_company_admin(empresa, codigo='LED-BANK-OPEN')
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-bank-open',
            evidencia_gate_ref='bank-gate-open',
            prueba_conectividad_ref='bank-connectivity-open',
            prueba_movimientos_ref='bank-movements-open',
            estado_conexion='activa',
            primaria_movimientos=True,
        )

        movimiento = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-08',
                'tipo_movimiento': 'abono',
                'monto': '999999.00',
                'descripcion_origen': 'Abono sin clasificacion para cierre',
                'origen_importacion': 'manual_controlada',
                'evidencia_importacion_ref': 'manual-import-open-close',
            },
            format='json',
        )
        self.assertEqual(movimiento.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Conciliacion no cerrada', response.data['detail'])

    def test_prepare_monthly_close_requires_bank_square_when_bank_movements_exist(self):
        empresa = self._create_active_empresa(nombre='BankSquareCo', rut='45454545-6')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        contrato, cuenta = self._create_contract_with_company_admin(empresa, codigo='LED-BANK-SQUARE')
        self.client.post(
            reverse('cobranza-pago-generate'),
            {'contrato_id': contrato.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-bank-square',
            evidencia_gate_ref='bank-gate-square',
            prueba_conectividad_ref='bank-connectivity-square',
            prueba_movimientos_ref='bank-movements-square',
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
                'descripcion_origen': 'Pago exacto sin cuadratura bancaria',
                'origen_importacion': 'manual_controlada',
                'evidencia_importacion_ref': 'manual-import-no-bank-square',
            },
            format='json',
        )
        self.assertEqual(movimiento.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Banco no cuadrado', response.data['detail'])

    def test_prepare_monthly_close_creates_ppm_obligation_and_snapshots(self):
        empresa = self._create_active_empresa(nombre='MonthlyCo', rut='45454545-4')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        self._create_rule_matrix(
            empresa,
            MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
            accounts['cxc'],
            accounts['bancos'],
            vigencia_desde='2026-02-01',
        )

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
            evidencia_gate_ref='bank-gate-close',
            prueba_conectividad_ref='bank-connectivity-close',
            prueba_movimientos_ref='bank-movements-close',
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
                'origen_importacion': 'manual_controlada',
                'evidencia_importacion_ref': 'manual-import-close',
            },
            format='json',
        )
        self._create_squared_bank_reconciliation(cuenta, amount='100111.00', suffix='close')

        response = self.client.post(
            reverse('contabilidad-cierre-prepare'),
            {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        close = CierreMensualContable.objects.get(empresa=empresa, anio=2026, mes=1)
        obligation = ObligacionTributariaMensual.objects.get(empresa=empresa, anio=2026, mes=1, obligacion_tipo='PPM')
        self.assertEqual(close.estado, 'preparado')
        self.assertEqual(close.resumen_obligaciones['conciliacion']['movimientos_bancarios_periodo'], 1)
        self.assertEqual(close.resumen_obligaciones['conciliacion']['movimientos_bancarios_no_resueltos'], 0)
        self.assertEqual(close.resumen_obligaciones['conciliacion']['cuadraturas_bancarias_cuadradas'], 1)
        self.assertEqual(str(obligation.base_imponible), '100111.00')
        self.assertEqual(str(obligation.monto_calculado), '10011.10')
        self.assertEqual(obligation.estado_preparacion, 'preparado')

    def test_prepare_monthly_close_rolls_back_when_view_audit_fails(self):
        empresa = self._create_active_empresa(nombre='PrepareAuditFailCo', rut='78333333-3')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        self._post_manual_accounting_event(empresa, '000333')

        def fail_prepare_audit(**kwargs):
            if kwargs['event_type'] == 'contabilidad.cierre_mensual.prepared':
                raise RuntimeError('prepare audit unavailable')
            return None

        with patch('contabilidad.views.create_audit_event', side_effect=fail_prepare_audit):
            with self.assertRaisesRegex(RuntimeError, 'prepare audit unavailable'):
                self.client.post(
                    reverse('contabilidad-cierre-prepare'),
                    {'empresa_id': empresa.id, 'anio': 2026, 'mes': 1},
                    format='json',
                )

        self.assertFalse(CierreMensualContable.objects.filter(empresa=empresa, anio=2026, mes=1).exists())
        self.assertFalse(ObligacionTributariaMensual.objects.filter(empresa=empresa, anio=2026, mes=1).exists())
        self.assertFalse(LibroDiario.objects.filter(empresa=empresa, periodo='2026-01').exists())
        self.assertFalse(LibroMayor.objects.filter(empresa=empresa, periodo='2026-01').exists())
        self.assertFalse(BalanceComprobacion.objects.filter(empresa=empresa, periodo='2026-01').exists())

    def test_approve_monthly_close_requires_company_liquidation(self):
        empresa = self._create_active_empresa(nombre='CloseLiquidationCo', rut='42424242-4')
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
                'entidad_origen_id': 'close-liquidation-guard-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'close-liquidation-guard-1',
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

        denied = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('liquidacion mensual de empresa preparada', denied.data['detail'])

        self._create_company_liquidation_for_close(empresa, prepare.data['id'])
        approved = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approved.status_code, status.HTTP_200_OK)
        self.assertEqual(approved.data['estado'], 'aprobado')
        self.assertEqual(approved.data['resumen_obligaciones']['liquidacion_mensual']['owner_tipo'], 'empresa')

    def test_approve_monthly_close_rolls_back_when_view_audit_fails(self):
        empresa, _, close = self._prepare_monthly_close_for_audit_tests('000444')
        self._create_company_liquidation_for_close(empresa, close)

        def fail_approve_audit(**kwargs):
            if kwargs['event_type'] == 'contabilidad.cierre_mensual.approved':
                raise RuntimeError('approve audit unavailable')
            return None

        with patch('contabilidad.views.create_audit_event', side_effect=fail_approve_audit):
            with self.assertRaisesRegex(RuntimeError, 'approve audit unavailable'):
                self.client.post(reverse('contabilidad-cierre-approve', args=[close.id]), format='json')

        close.refresh_from_db()
        self.assertEqual(close.estado, 'preparado')
        self.assertIsNone(close.fecha_aprobacion)
        self.assertEqual(LibroDiario.objects.get(empresa=empresa, periodo='2026-01').estado_snapshot, 'preparado')
        self.assertEqual(LibroMayor.objects.get(empresa=empresa, periodo='2026-01').estado_snapshot, 'preparado')
        self.assertEqual(
            BalanceComprobacion.objects.get(empresa=empresa, periodo='2026-01').estado_snapshot,
            'preparado',
        )

    def test_end_to_end_payment_reconciliation_close_lifecycle(self):
        empresa = self._create_active_empresa(nombre='WorkflowCo', rut='43434343-4')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        self._create_rule_matrix(
            empresa,
            MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
            accounts['cxc'],
            accounts['bancos'],
            vigencia_desde='2026-02-01',
        )

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
            evidencia_gate_ref='bank-gate-workflow',
            prueba_conectividad_ref='bank-connectivity-workflow',
            prueba_movimientos_ref='bank-movements-workflow',
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
                'origen_importacion': 'manual_controlada',
                'evidencia_importacion_ref': 'manual-import-workflow',
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
        self._create_squared_bank_reconciliation(cuenta, amount='100111.00', suffix='workflow')

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
        self._create_company_liquidation_for_close(empresa, close)

        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[close.id]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        close.refresh_from_db()
        libro_diario.refresh_from_db()
        libro_mayor.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual(close.estado, 'aprobado')
        self.assertIsNotNone(close.fecha_aprobacion)
        self.assertEqual(libro_diario.estado_snapshot, 'aprobado')
        self.assertEqual(libro_mayor.estado_snapshot, 'aprobado')
        self.assertEqual(balance.estado_snapshot, 'aprobado')

        self._allow_monthly_close_reopen(empresa)
        reopen = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[close.id]),
            self._reopen_effect_payload('workflow'),
            format='json',
        )
        self.assertEqual(reopen.status_code, status.HTTP_200_OK)
        close.refresh_from_db()
        libro_diario.refresh_from_db()
        libro_mayor.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual(close.estado, 'reabierto')
        self.assertEqual(close.resumen_obligaciones['reapertura']['tipo_efecto'], 'reverso')
        self.assertEqual(libro_diario.estado_snapshot, 'reabierto')
        self.assertEqual(libro_mayor.estado_snapshot, 'reabierto')
        self.assertEqual(balance.estado_snapshot, 'reabierto')
        self.assertEqual(EfectoReaperturaCierreMensual.objects.filter(cierre=close).count(), 1)
        reopen_event = EventoContable.objects.get(evento_tipo=MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE)
        self.assertEqual(reopen_event.estado_contable, 'contabilizado')
        self.assertEqual(str(reopen_event.fecha_operativa), '2026-02-01')

    def test_reopen_monthly_close_rolls_back_when_view_audit_fails(self):
        empresa, _, close = self._prepare_monthly_close_for_audit_tests('000555', with_reopen_rule=True)
        self._create_company_liquidation_for_close(empresa, close)
        approve = self.client.post(reverse('contabilidad-cierre-approve', args=[close.id]), format='json')
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        self._allow_monthly_close_reopen(empresa)

        def fail_reopen_audit(**kwargs):
            if kwargs['event_type'] == 'contabilidad.cierre_mensual.reopened':
                raise RuntimeError('reopen audit unavailable')
            return None

        with patch('contabilidad.views.create_audit_event', side_effect=fail_reopen_audit):
            with self.assertRaisesRegex(RuntimeError, 'reopen audit unavailable'):
                self.client.post(
                    reverse('contabilidad-cierre-reopen', args=[close.id]),
                    self._reopen_effect_payload('audit-fail'),
                    format='json',
                )

        close.refresh_from_db()
        self.assertEqual(close.estado, 'aprobado')
        self.assertFalse(EfectoReaperturaCierreMensual.objects.filter(cierre=close).exists())
        self.assertFalse(
            EventoContable.objects.filter(
                evento_tipo=MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
                entidad_origen_tipo='cierre_mensual_contable',
                entidad_origen_id=str(close.pk),
            ).exists()
        )
        self.assertEqual(LibroDiario.objects.get(empresa=empresa, periodo='2026-01').estado_snapshot, 'aprobado')
        self.assertEqual(LibroMayor.objects.get(empresa=empresa, periodo='2026-01').estado_snapshot, 'aprobado')
        self.assertEqual(
            BalanceComprobacion.objects.get(empresa=empresa, periodo='2026-01').estado_snapshot,
            'aprobado',
        )

    def test_prepare_and_approve_and_reopen_monthly_close(self):
        empresa = self._create_active_empresa(nombre='ApproveCo', rut='56565656-5')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        self._create_rule_matrix(
            empresa,
            MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
            accounts['cxc'],
            accounts['bancos'],
            vigencia_desde='2026-02-01',
        )

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
        self._create_company_liquidation_for_close(empresa, prepare.data['id'])

        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        self.assertEqual(approve.data['estado'], 'aprobado')

        self._allow_monthly_close_reopen(empresa)
        reopen = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[prepare.data['id']]),
            self._reopen_effect_payload('approve'),
            format='json',
        )
        self.assertEqual(reopen.status_code, status.HTTP_200_OK)
        self.assertEqual(reopen.data['estado'], 'reabierto')
        self.assertEqual(reopen.data['resumen_obligaciones']['reapertura']['tipo_efecto'], 'reverso')
        self.assertEqual(EfectoReaperturaCierreMensual.objects.count(), 1)

    def test_reopen_monthly_close_requires_posted_reopen_effect(self):
        empresa = self._create_active_empresa(nombre='ReopenEffectCo', rut='58585858-3')
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
                'entidad_origen_id': 'close-reopen-effect-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'close-reopen-effect-1',
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
        self._create_company_liquidation_for_close(empresa, prepare.data['id'])
        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)
        self._allow_monthly_close_reopen(empresa)

        denied = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[prepare.data['id']]),
            self._reopen_effect_payload('missing-rule'),
            format='json',
        )

        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('regla y matriz activas', str(denied.data['detail']))
        self.assertFalse(EfectoReaperturaCierreMensual.objects.exists())
        self.assertEqual(CierreMensualContable.objects.get(pk=prepare.data['id']).estado, 'aprobado')

    def test_reopen_monthly_close_requires_active_reopen_policy(self):
        empresa = self._create_active_empresa(nombre='ReopenPolicyCo', rut='56565656-7')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        self._create_rule_matrix(
            empresa,
            MONTHLY_CLOSE_REOPEN_REVERSAL_EVENT_TYPE,
            accounts['cxc'],
            accounts['bancos'],
            vigencia_desde='2026-02-01',
        )

        response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'close-reopen-policy-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'close-reopen-policy-1',
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
        self._create_company_liquidation_for_close(empresa, prepare.data['id'])
        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_200_OK)

        PoliticaReversoContable.objects.create(
            empresa=empresa,
            tipo_ajuste=MONTHLY_CLOSE_REOPEN_POLICY_TYPE,
            usa_reverso=True,
            usa_asiento_complementario=True,
            permite_reapertura=True,
            aprobacion_requerida=False,
            ventana_operativa='periodo-siguiente-controlado',
            estado='activa',
        )

        denied = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[prepare.data['id']]),
            self._reopen_effect_payload('denied'),
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('politica activa', str(denied.data['detail']))
        close = CierreMensualContable.objects.get(pk=prepare.data['id'])
        self.assertEqual(close.estado, 'aprobado')

        PoliticaReversoContable.objects.filter(empresa=empresa).delete()
        self._allow_monthly_close_reopen(empresa)
        reopened = self.client.post(
            reverse('contabilidad-cierre-reopen', args=[prepare.data['id']]),
            self._reopen_effect_payload('allowed'),
            format='json',
        )
        self.assertEqual(reopened.status_code, status.HTTP_200_OK)
        self.assertEqual(reopened.data['estado'], 'reabierto')

    def test_approve_monthly_close_revalidates_bank_movements(self):
        empresa = self._create_active_empresa(nombre='ApproveBankGateCo', rut='56565656-6')
        accounts = self._setup_contabilidad(empresa)
        config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        config.tasa_ppm_vigente = '10.00'
        config.save(update_fields=['tasa_ppm_vigente'])
        self._create_rule_matrix(empresa, 'PagoConciliadoArriendo', accounts['bancos'], accounts['cxc'])
        _, cuenta = self._create_contract_with_company_admin(empresa, codigo='LED-APP-BANK')

        event_response = self.client.post(
            reverse('contabilidad-evento-list'),
            {
                'empresa': empresa.id,
                'evento_tipo': 'PagoConciliadoArriendo',
                'entidad_origen_tipo': 'manual',
                'entidad_origen_id': 'approve-bank-gate-1',
                'fecha_operativa': '2026-01-10',
                'moneda': 'CLP',
                'monto_base': '100000.00',
                'payload_resumen': {},
                'idempotency_key': 'approve-bank-gate-1',
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
        self._create_company_liquidation_for_close(empresa, prepare.data['id'])

        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key='banco_de_chile',
            credencial_ref='cred-approve-bank',
            evidencia_gate_ref='bank-gate-approve',
            prueba_conectividad_ref='bank-connectivity-approve',
            prueba_movimientos_ref='bank-movements-approve',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        movimiento = self.client.post(
            reverse('conciliacion-movimiento-list'),
            {
                'conexion_bancaria': conexion.id,
                'fecha_movimiento': '2026-01-20',
                'tipo_movimiento': 'abono',
                'monto': '888888.00',
                'descripcion_origen': 'Abono posterior a preparacion',
                'origen_importacion': 'manual_controlada',
                'evidencia_importacion_ref': 'manual-import-approve-bank',
            },
            format='json',
        )
        self.assertEqual(movimiento.status_code, status.HTTP_201_CREATED)

        approve = self.client.post(
            reverse('contabilidad-cierre-approve', args=[prepare.data['id']]),
            format='json',
        )
        self.assertEqual(approve.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Conciliacion no cerrada', approve.data['detail'])

        close = CierreMensualContable.objects.get(pk=prepare.data['id'])
        self.assertEqual(close.estado, 'preparado')

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
        self._create_company_liquidation_for_close(empresa, prepare.data['id'])
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
        self._create_company_liquidation_for_close(empresa, prepare.data['id'])
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
