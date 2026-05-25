from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from canales.services import materialize_payment_notification_schedule
from core.permissions import AdminOnlyPermission, OperationalModulePermission
from core.reference_validation import redact_sensitive_reference
from core.scope_access import (
    ScopedQuerysetMixin,
    ensure_queryset_scope,
    get_scope_access,
    scope_queryset_for_access,
    scope_queryset_for_user,
)
from contratos.models import Arrendatario, Contrato

from .models import (
    AjusteContrato,
    CodigoCobroResidual,
    DistribucionCobroMensual,
    EstadoCuentaArrendatario,
    EstadoPago,
    GateCobroExterno,
    GarantiaContractual,
    HistorialGarantia,
    IntentoPagoWebPay,
    PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
)
from .serializers import (
    AjusteContratoSerializer,
    CodigoCobroResidualSerializer,
    EstadoCuentaArrendatarioSerializer,
    EstadoCuentaRecalculoSerializer,
    GateCobroExternoSerializer,
    GarantiaContractualSerializer,
    GarantiaMovimientoSerializer,
    HistorialGarantiaReadSerializer,
    IntentoPagoWebPaySerializer,
    PagoMensualGenerateSerializer,
    PagoMensualRefreshMoraSerializer,
    PagoMensualSerializer,
    DistribucionCobroMensualSerializer,
    RepactacionDeudaSerializer,
    ValorUFDiarioSerializer,
    WebPayIntentConfirmSerializer,
    WebPayIntentPrepareSerializer,
)
from .services import (
    build_account_state_summary,
    calculate_monthly_amount,
    confirm_webpay_intent_manually,
    prepare_webpay_intent,
    rebuild_account_state,
    refresh_overdue_payments,
    sync_payment_distribution,
    sync_payment_state,
)


def _partial_repayment_exception_trace(instance):
    if not isinstance(instance, RepactacionDeuda) or not instance.es_repactacion_parcial:
        return ''
    return '|'.join(
        [
            str(instance.pk or ''),
            instance.excepcion_parcial_ref.strip(),
            instance.excepcion_parcial_motivo.strip(),
            str(instance.monto_total_plan_clp),
            str(instance.deuda_total_original),
        ]
    )


def create_partial_repayment_exception_event(instance, request):
    if not instance.es_repactacion_parcial:
        return
    create_audit_event(
        event_type=PARTIAL_REPAYMENT_EXCEPTION_EVENT_TYPE,
        entity_type='repactacion_deuda',
        entity_id=str(instance.pk),
        summary=f'Repactacion parcial autorizada para arrendatario {instance.arrendatario_id}',
        actor_user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        metadata={
            'arrendatario_id': instance.arrendatario_id,
            'contrato_id': instance.contrato_origen_id,
            'deuda_total_original': str(instance.deuda_total_original),
            'monto_total_plan_clp': str(instance.monto_total_plan_clp),
            'excepcion_parcial_ref': instance.excepcion_parcial_ref.strip(),
        },
    )


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            if isinstance(instance, RepactacionDeuda):
                create_partial_repayment_exception_event(instance, self.request)
        self._create_audit_event(instance=instance, action='created')

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        previous_repayment_trace = _partial_repayment_exception_trace(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            current_repayment_trace = _partial_repayment_exception_trace(instance)
            if isinstance(instance, RepactacionDeuda) and current_repayment_trace and current_repayment_trace != previous_repayment_trace:
                create_partial_repayment_exception_event(instance, self.request)
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )

    def _extract_state(self, instance):
        for field in ('estado_pago', 'estado_garantia'):
            if hasattr(instance, field):
                return getattr(instance, field)
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'cobranza.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class CobranzaSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)

        contratos = scope_queryset_for_access(
            Contrato.objects.only('id', 'codigo_contrato').order_by('codigo_contrato', 'id'),
            access,
            property_paths=('mandato_operacion__propiedad_id',),
        )
        arrendatarios = scope_queryset_for_access(
            Arrendatario.objects.only('id', 'nombre_razon_social').order_by('nombre_razon_social', 'id'),
            access,
            property_paths=('contratos__mandato_operacion__propiedad_id',),
        )
        valores_uf = ValorUFDiario.objects.order_by('-fecha', '-id')
        ajustes = scope_queryset_for_access(
            AjusteContrato.objects.select_related('contrato').order_by('-mes_inicio', '-id'),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        pagos = scope_queryset_for_access(
            PagoMensual.objects.select_related('contrato', 'repactacion_deuda').order_by('-anio', '-mes', '-id'),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        garantias = scope_queryset_for_access(
            GarantiaContractual.objects.select_related('contrato').order_by('-id'),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        historial = scope_queryset_for_access(
            HistorialGarantia.objects.select_related('garantia_contractual__contrato').order_by('-fecha', '-id'),
            access,
            property_paths=('garantia_contractual__contrato__mandato_operacion__propiedad_id',),
        )
        estados_cuenta = scope_queryset_for_access(
            EstadoCuentaArrendatario.objects.select_related('arrendatario').order_by('id'),
            access,
            property_paths=('arrendatario__contratos__mandato_operacion__propiedad_id',),
        )
        intentos_webpay = scope_queryset_for_access(
            IntentoPagoWebPay.objects.select_related('pago_mensual__contrato', 'gate_cobro').order_by('-id'),
            access,
            property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
        )

        return Response(
            {
                'gates_cobro': [
                    {
                        'id': item.id,
                        'capacidad_key': item.capacidad_key,
                        'provider_key': item.provider_key,
                        'estado_gate': item.estado_gate,
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                    }
                    for item in GateCobroExterno.objects.order_by('capacidad_key', 'provider_key', 'id')
                ],
                'contratos': [
                    {
                        'id': item.id,
                        'codigo_contrato': item.codigo_contrato,
                    }
                    for item in contratos
                ],
                'arrendatarios': [
                    {
                        'id': item.id,
                        'nombre_razon_social': item.nombre_razon_social,
                    }
                    for item in arrendatarios
                ],
                'valores_uf': [
                    {
                        'id': item.id,
                        'fecha': item.fecha,
                        'valor': item.valor,
                        'source_key': item.source_key,
                    }
                    for item in valores_uf
                ],
                'ajustes': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'tipo_ajuste': item.tipo_ajuste,
                        'monto': item.monto,
                        'moneda': item.moneda,
                        'mes_inicio': item.mes_inicio,
                        'mes_fin': item.mes_fin,
                        'activo': item.activo,
                    }
                    for item in ajustes
                ],
                'pagos': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'mes': item.mes,
                        'anio': item.anio,
                        'monto_facturable_clp': item.monto_facturable_clp,
                        'monto_calculado_clp': item.monto_calculado_clp,
                        'monto_pagado_clp': item.monto_pagado_clp,
                        'fecha_vencimiento': item.fecha_vencimiento,
                        'estado_pago': item.estado_pago,
                        'repactacion_deuda': item.repactacion_deuda_id,
                        'dias_mora': item.dias_mora,
                        'fecha_pago_webpay': item.fecha_pago_webpay,
                    }
                    for item in pagos
                ],
                'intentos_webpay': [
                    {
                        'id': item.id,
                        'pago_mensual': item.pago_mensual_id,
                        'gate_cobro': item.gate_cobro_id,
                        'provider_key': item.provider_key,
                        'monto_clp_snapshot': item.monto_clp_snapshot,
                        'buy_order': item.buy_order,
                        'estado': item.estado,
                        'motivo_bloqueo': item.motivo_bloqueo,
                        'external_ref': redact_sensitive_reference(item.external_ref),
                        'fecha_pago_webpay': item.fecha_pago_webpay,
                    }
                    for item in intentos_webpay
                ],
                'garantias': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'monto_pactado': item.monto_pactado,
                        'monto_recibido': item.monto_recibido,
                        'saldo_vigente': item.saldo_vigente,
                        'brecha_garantia_clp': item.brecha_garantia_clp,
                        'garantia_incompleta': item.garantia_incompleta,
                        'garantia_parcial_aceptada': item.garantia_parcial_aceptada,
                        'aceptacion_parcial_ref': redact_sensitive_reference(item.aceptacion_parcial_ref),
                        'estado_garantia': item.estado_garantia,
                    }
                    for item in garantias
                ],
                'historial_garantias': [
                    {
                        'id': item.id,
                        'contrato_id': item.garantia_contractual.contrato_id,
                        'tipo_movimiento': item.tipo_movimiento,
                        'monto_clp': item.monto_clp,
                        'fecha': item.fecha,
                        'justificacion': item.justificacion,
                    }
                    for item in historial
                ],
                'estados_cuenta': [
                    {
                        'id': item.id,
                        'arrendatario': item.arrendatario_id,
                        'score_pago': item.score_pago,
                        'resumen_operativo': build_account_state_summary(item.arrendatario, access),
                    }
                    for item in estados_cuenta
                ],
            }
        )


class ValorUFDiarioListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ValorUFDiarioSerializer
    queryset = ValorUFDiario.objects.all()
    audit_entity_type = 'valor_uf'
    audit_entity_label = 'valor UF'


class ValorUFDiarioDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ValorUFDiarioSerializer
    queryset = ValorUFDiario.objects.all()
    audit_entity_type = 'valor_uf'
    audit_entity_label = 'valor UF'


class AjusteContratoListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AjusteContratoSerializer
    queryset = AjusteContrato.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'ajuste_contrato'
    audit_entity_label = 'ajuste de contrato'


class AjusteContratoDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AjusteContratoSerializer
    queryset = AjusteContrato.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'ajuste_contrato'
    audit_entity_label = 'ajuste de contrato'


class PagoMensualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PagoMensualSerializer
    queryset = PagoMensual.objects.select_related('contrato', 'periodo_contractual', 'repactacion_deuda').prefetch_related(
        Prefetch(
            'distribuciones_cobro',
            queryset=DistribucionCobroMensual.objects.select_related(
                'beneficiario_socio_owner',
                'beneficiario_empresa_owner',
            ),
        )
    ).all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class PagoMensualDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PagoMensualSerializer
    queryset = PagoMensual.objects.select_related('contrato', 'periodo_contractual', 'repactacion_deuda').prefetch_related(
        Prefetch(
            'distribuciones_cobro',
            queryset=DistribucionCobroMensual.objects.select_related(
                'beneficiario_socio_owner',
                'beneficiario_empresa_owner',
            ),
        )
    ).all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'pago_mensual'
    audit_entity_label = 'pago mensual'

    def perform_update(self, serializer):
        next_state = serializer.validated_data.get('estado_pago', serializer.instance.estado_pago)
        if next_state in {
            EstadoPago.PAID,
            EstadoPago.PAID_VIA_REPAYMENT,
            EstadoPago.PAID_BY_TERMINATION,
        }:
            raise ValidationError(
                {
                    'estado_pago': (
                        'Los pagos cerrados solo se registran desde conciliacion bancaria '
                        'o desde el flujo especifico con artefacto de cierre.'
                    )
                }
            )

        previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            sync_payment_state(instance)
            sync_payment_distribution(instance)
            instance.save(
                update_fields=[
                    'monto_pagado_clp',
                    'fecha_deposito_banco',
                    'fecha_pago_webpay',
                    'fecha_deteccion_sistema',
                    'estado_pago',
                    'repactacion_deuda',
                    'dias_mora',
                    'updated_at',
                ]
            )
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )


class PagoMensualGenerateView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = PagoMensualGenerateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        contrato = serializer.validated_data['contrato']
        ensure_queryset_scope(
            contrato.__class__.objects.filter(pk=contrato.pk),
            request.user,
            property_paths=('mandato_operacion__propiedad_id',),
        )
        anio = serializer.validated_data['anio']
        mes = serializer.validated_data['mes']

        existing = PagoMensual.objects.filter(contrato=contrato, anio=anio, mes=mes).first()
        if existing:
            materialized = materialize_payment_notification_schedule(existing)
            if materialized['created_count']:
                create_audit_event(
                    event_type='canales.notificacion_cobranza.materialized',
                    entity_type='pago_mensual',
                    entity_id=str(existing.pk),
                    summary='Notificaciones de cobranza programadas para pago existente',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={
                        'contrato_id': contrato.id,
                        'anio': anio,
                        'mes': mes,
                        'created_count': materialized['created_count'],
                    },
                )
            return Response(PagoMensualSerializer(existing).data, status=status.HTTP_200_OK)

        try:
            calculation = calculate_monthly_amount(contrato, anio, mes)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            payment = PagoMensual.objects.create(
                contrato=contrato,
                periodo_contractual=calculation['periodo_contractual'],
                mes=mes,
                anio=anio,
                monto_facturable_clp=calculation['monto_facturable_clp'],
                monto_calculado_clp=calculation['monto_calculado_clp'],
                fecha_vencimiento=calculation['fecha_vencimiento'],
                codigo_conciliacion_efectivo=calculation['codigo_conciliacion_efectivo'],
            )
            sync_payment_distribution(payment)
            create_audit_event(
                event_type='cobranza.pago_mensual.generated',
                entity_type='pago_mensual',
                entity_id=str(payment.pk),
                summary='Pago mensual generado',
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                metadata={'contrato_id': contrato.id, 'anio': anio, 'mes': mes},
            )
            materialized = materialize_payment_notification_schedule(payment)
            if materialized['created_count']:
                create_audit_event(
                    event_type='canales.notificacion_cobranza.materialized',
                    entity_type='pago_mensual',
                    entity_id=str(payment.pk),
                    summary='Notificaciones de cobranza programadas al generar pago',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    metadata={
                        'contrato_id': contrato.id,
                        'anio': anio,
                        'mes': mes,
                        'created_count': materialized['created_count'],
                    },
                )

        return Response(PagoMensualSerializer(payment).data, status=status.HTTP_201_CREATED)


class PagoMensualRefreshMoraView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = PagoMensualRefreshMoraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reference_date = serializer.validated_data.get('fecha_corte') or timezone.localdate()
        queryset = scope_queryset_for_user(
            PagoMensual.objects.select_related('contrato', 'contrato__arrendatario'),
            request.user,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
            bank_account_paths=('contrato__mandato_operacion__cuenta_recaudadora_id',),
        )
        result = refresh_overdue_payments(
            queryset=queryset,
            reference_date=reference_date,
            access=get_scope_access(request.user),
        )
        create_audit_event(
            event_type='cobranza.pago_mensual.overdue_refreshed',
            entity_type='pago_mensual',
            entity_id='bulk',
            summary='Mora de pagos vencidos refrescada',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata=result,
        )
        return Response(result, status=status.HTTP_200_OK)


class GateCobroExternoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = GateCobroExternoSerializer
    queryset = GateCobroExterno.objects.all()
    audit_entity_type = 'gate_cobro_externo'
    audit_entity_label = 'gate de cobro externo'


class GateCobroExternoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = GateCobroExternoSerializer
    queryset = GateCobroExterno.objects.all()
    audit_entity_type = 'gate_cobro_externo'
    audit_entity_label = 'gate de cobro externo'


class IntentoPagoWebPayListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = IntentoPagoWebPaySerializer
    queryset = IntentoPagoWebPay.objects.select_related('pago_mensual__contrato', 'gate_cobro', 'usuario').all()
    property_scope_paths = ('pago_mensual__contrato__mandato_operacion__propiedad_id',)


class IntentoPagoWebPayDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = IntentoPagoWebPaySerializer
    queryset = IntentoPagoWebPay.objects.select_related('pago_mensual__contrato', 'gate_cobro', 'usuario').all()
    property_scope_paths = ('pago_mensual__contrato__mandato_operacion__propiedad_id',)


class WebPayIntentPrepareView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        payment = generics.get_object_or_404(
            scope_queryset_for_user(
                PagoMensual.objects.select_related('contrato', 'periodo_contractual'),
                request.user,
                property_paths=('contrato__mandato_operacion__propiedad_id',),
                bank_account_paths=('contrato__mandato_operacion__cuenta_recaudadora_id',),
            ),
            pk=pk,
        )
        serializer = WebPayIntentPrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            intent = prepare_webpay_intent(
                payment=payment,
                gate=data.get('gate_cobro'),
                provider_key=data.get('provider_key', 'transbank_webpay'),
                return_url_ref=data['return_url_ref'],
                usuario=request.user,
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        create_audit_event(
            event_type='cobranza.webpay_intento.prepared',
            entity_type='webpay_intento',
            entity_id=str(intent.pk),
            summary='Intento WebPay preparado o bloqueado segun gate',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'estado': intent.estado, 'pago_mensual_id': payment.pk, 'gate_cobro_id': intent.gate_cobro_id},
        )
        return Response(IntentoPagoWebPaySerializer(intent).data, status=status.HTTP_201_CREATED)


class WebPayIntentManualConfirmView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        intent = generics.get_object_or_404(
            scope_queryset_for_user(
                IntentoPagoWebPay.objects.select_related('pago_mensual__contrato', 'gate_cobro'),
                request.user,
                property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
                bank_account_paths=('pago_mensual__contrato__mandato_operacion__cuenta_recaudadora_id',),
            ),
            pk=pk,
        )
        serializer = WebPayIntentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            intent, payment = confirm_webpay_intent_manually(
                intent=intent,
                external_ref=serializer.validated_data['external_ref'],
                fecha_pago_webpay=serializer.validated_data['fecha_pago_webpay'],
                actor_user=request.user,
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        create_audit_event(
            event_type='cobranza.webpay_intento.confirmed_manually',
            entity_type='webpay_intento',
            entity_id=str(intent.pk),
            summary='Confirmacion WebPay manual controlada registrada',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={
                'external_ref': redact_sensitive_reference(intent.external_ref),
                'pago_mensual_id': payment.pk,
                'fecha_pago_webpay': str(intent.fecha_pago_webpay),
            },
        )
        return Response(IntentoPagoWebPaySerializer(intent).data, status=status.HTTP_200_OK)


class DistribucionCobroMensualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DistribucionCobroMensualSerializer
    queryset = DistribucionCobroMensual.objects.select_related(
        'pago_mensual',
        'beneficiario_socio_owner',
        'beneficiario_empresa_owner',
    ).all()
    company_scope_paths = ('beneficiario_empresa_owner_id',)
    property_scope_paths = ('pago_mensual__contrato__mandato_operacion__propiedad_id',)


class DistribucionCobroMensualDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DistribucionCobroMensualSerializer
    queryset = DistribucionCobroMensual.objects.select_related(
        'pago_mensual',
        'beneficiario_socio_owner',
        'beneficiario_empresa_owner',
    ).all()
    company_scope_paths = ('beneficiario_empresa_owner_id',)
    property_scope_paths = ('pago_mensual__contrato__mandato_operacion__propiedad_id',)


class GarantiaContractualListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = GarantiaContractualSerializer
    queryset = GarantiaContractual.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'garantia_contractual'
    audit_entity_label = 'garantia contractual'


class GarantiaContractualDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = GarantiaContractualSerializer
    queryset = GarantiaContractual.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'garantia_contractual'
    audit_entity_label = 'garantia contractual'


class HistorialGarantiaListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = HistorialGarantiaReadSerializer
    queryset = HistorialGarantia.objects.select_related('garantia_contractual', 'garantia_contractual__contrato').all()
    property_scope_paths = ('garantia_contractual__contrato__mandato_operacion__propiedad_id',)


class HistorialGarantiaDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = HistorialGarantiaReadSerializer
    queryset = HistorialGarantia.objects.select_related('garantia_contractual', 'garantia_contractual__contrato').all()
    property_scope_paths = ('garantia_contractual__contrato__mandato_operacion__propiedad_id',)


class GarantiaMovimientoCreateView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        garantia = generics.get_object_or_404(
            scope_queryset_for_user(
                GarantiaContractual.objects.select_related('contrato'),
                request.user,
                property_paths=('contrato__mandato_operacion__propiedad_id',),
            ),
            pk=pk,
        )
        previous_state = garantia.estado_garantia
        serializer = GarantiaMovimientoSerializer(data=request.data, context={'garantia': garantia, 'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                movimiento, garantia = serializer.save()
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        from contabilidad.services import create_guarantee_event

        create_guarantee_event(movimiento)

        create_audit_event(
            event_type='cobranza.historial_garantia.created',
            entity_type='historial_garantia',
            entity_id=str(movimiento.pk),
            summary='Movimiento de garantia registrado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'garantia_id': garantia.id, 'tipo_movimiento': movimiento.tipo_movimiento},
        )
        create_audit_event(
            event_type='cobranza.garantia_contractual.updated',
            entity_type='garantia_contractual',
            entity_id=str(garantia.pk),
            summary='Garantia contractual actualizada por movimiento',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        if previous_state != garantia.estado_garantia:
            create_audit_event(
                event_type='cobranza.garantia_contractual.state_changed',
                entity_type='garantia_contractual',
                entity_id=str(garantia.pk),
                summary='Cambio de estado de garantia contractual',
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )

        return Response(HistorialGarantiaReadSerializer(movimiento).data, status=status.HTTP_201_CREATED)


class RepactacionDeudaListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = RepactacionDeudaSerializer
    queryset = RepactacionDeuda.objects.select_related('arrendatario', 'contrato_origen').all()
    property_scope_paths = (
        'contrato_origen__mandato_operacion__propiedad_id',
        'arrendatario__contratos__mandato_operacion__propiedad_id',
    )
    audit_entity_type = 'repactacion_deuda'
    audit_entity_label = 'repactacion de deuda'


class RepactacionDeudaDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = RepactacionDeudaSerializer
    queryset = RepactacionDeuda.objects.select_related('arrendatario', 'contrato_origen').all()
    property_scope_paths = (
        'contrato_origen__mandato_operacion__propiedad_id',
        'arrendatario__contratos__mandato_operacion__propiedad_id',
    )
    audit_entity_type = 'repactacion_deuda'
    audit_entity_label = 'repactacion de deuda'


class CodigoCobroResidualListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodigoCobroResidualSerializer
    queryset = CodigoCobroResidual.objects.select_related('arrendatario', 'contrato_origen').all()
    property_scope_paths = (
        'contrato_origen__mandato_operacion__propiedad_id',
        'arrendatario__contratos__mandato_operacion__propiedad_id',
    )
    audit_entity_type = 'codigo_cobro_residual'
    audit_entity_label = 'codigo de cobro residual'


class CodigoCobroResidualDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodigoCobroResidualSerializer
    queryset = CodigoCobroResidual.objects.select_related('arrendatario', 'contrato_origen').all()
    property_scope_paths = (
        'contrato_origen__mandato_operacion__propiedad_id',
        'arrendatario__contratos__mandato_operacion__propiedad_id',
    )
    audit_entity_type = 'codigo_cobro_residual'
    audit_entity_label = 'codigo de cobro residual'


class EstadoCuentaArrendatarioListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = EstadoCuentaArrendatarioSerializer
    queryset = EstadoCuentaArrendatario.objects.select_related('arrendatario').all()
    property_scope_paths = ('arrendatario__contratos__mandato_operacion__propiedad_id',)


class EstadoCuentaArrendatarioDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = EstadoCuentaArrendatarioSerializer
    queryset = EstadoCuentaArrendatario.objects.select_related('arrendatario').all()
    property_scope_paths = ('arrendatario__contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'estado_cuenta_arrendatario'
    audit_entity_label = 'estado de cuenta arrendatario'


class EstadoCuentaArrendatarioRebuildView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = EstadoCuentaRecalculoSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        arrendatario = serializer.validated_data['arrendatario']
        ensure_queryset_scope(
            arrendatario.__class__.objects.filter(pk=arrendatario.pk),
            request.user,
            property_paths=('contratos__mandato_operacion__propiedad_id',),
        )
        estado = rebuild_account_state(arrendatario, access=get_scope_access(request.user))
        create_audit_event(
            event_type='cobranza.estado_cuenta_arrendatario.rebuilt',
            entity_type='estado_cuenta_arrendatario',
            entity_id=str(estado.pk),
            summary='Estado de cuenta arrendatario recalculado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'arrendatario_id': arrendatario.pk},
        )
        return Response(EstadoCuentaArrendatarioSerializer(estado, context={'request': request}).data, status=status.HTTP_200_OK)
