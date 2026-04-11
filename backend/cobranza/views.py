from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import OperationalModulePermission

from .models import AjusteContrato, DistribucionCobroMensual, GarantiaContractual, HistorialGarantia, PagoMensual, ValorUFDiario
from .serializers import (
    AjusteContratoSerializer,
    CodigoCobroResidualSerializer,
    EstadoCuentaArrendatarioSerializer,
    EstadoCuentaRecalculoSerializer,
    GarantiaContractualSerializer,
    GarantiaMovimientoSerializer,
    HistorialGarantiaReadSerializer,
    PagoMensualGenerateSerializer,
    PagoMensualSerializer,
    DistribucionCobroMensualSerializer,
    RepactacionDeudaSerializer,
    ValorUFDiarioSerializer,
)
from .services import calculate_monthly_amount, rebuild_account_state, sync_payment_distribution, sync_payment_state
from .models import CodigoCobroResidual, EstadoCuentaArrendatario, RepactacionDeuda


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
        self._create_audit_event(instance=instance, action='created')

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
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


class AjusteContratoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AjusteContratoSerializer
    queryset = AjusteContrato.objects.select_related('contrato').all()
    audit_entity_type = 'ajuste_contrato'
    audit_entity_label = 'ajuste de contrato'


class AjusteContratoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AjusteContratoSerializer
    queryset = AjusteContrato.objects.select_related('contrato').all()
    audit_entity_type = 'ajuste_contrato'
    audit_entity_label = 'ajuste de contrato'


class PagoMensualListView(generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PagoMensualSerializer
    queryset = PagoMensual.objects.select_related('contrato', 'periodo_contractual').all()


class PagoMensualDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PagoMensualSerializer
    queryset = PagoMensual.objects.select_related('contrato', 'periodo_contractual').all()
    audit_entity_type = 'pago_mensual'
    audit_entity_label = 'pago mensual'

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            sync_payment_state(instance)
            sync_payment_distribution(instance)
            instance.save(update_fields=['monto_pagado_clp', 'fecha_deposito_banco', 'fecha_deteccion_sistema', 'estado_pago', 'dias_mora', 'updated_at'])
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
        serializer = PagoMensualGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contrato = serializer.validated_data['contrato']
        anio = serializer.validated_data['anio']
        mes = serializer.validated_data['mes']

        existing = PagoMensual.objects.filter(contrato=contrato, anio=anio, mes=mes).first()
        if existing:
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

        return Response(PagoMensualSerializer(payment).data, status=status.HTTP_201_CREATED)


class DistribucionCobroMensualListView(generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DistribucionCobroMensualSerializer
    queryset = DistribucionCobroMensual.objects.select_related(
        'pago_mensual',
        'beneficiario_socio_owner',
        'beneficiario_empresa_owner',
    ).all()


class DistribucionCobroMensualDetailView(generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DistribucionCobroMensualSerializer
    queryset = DistribucionCobroMensual.objects.select_related(
        'pago_mensual',
        'beneficiario_socio_owner',
        'beneficiario_empresa_owner',
    ).all()


class GarantiaContractualListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = GarantiaContractualSerializer
    queryset = GarantiaContractual.objects.select_related('contrato').all()
    audit_entity_type = 'garantia_contractual'
    audit_entity_label = 'garantia contractual'


class GarantiaContractualDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = GarantiaContractualSerializer
    queryset = GarantiaContractual.objects.select_related('contrato').all()
    audit_entity_type = 'garantia_contractual'
    audit_entity_label = 'garantia contractual'


class HistorialGarantiaListView(generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = HistorialGarantiaReadSerializer
    queryset = HistorialGarantia.objects.select_related('garantia_contractual', 'garantia_contractual__contrato').all()


class HistorialGarantiaDetailView(generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = HistorialGarantiaReadSerializer
    queryset = HistorialGarantia.objects.select_related('garantia_contractual', 'garantia_contractual__contrato').all()


class GarantiaMovimientoCreateView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        garantia = generics.get_object_or_404(GarantiaContractual.objects.select_related('contrato'), pk=pk)
        previous_state = garantia.estado_garantia
        serializer = GarantiaMovimientoSerializer(data=request.data, context={'garantia': garantia})
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


class RepactacionDeudaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = RepactacionDeudaSerializer
    queryset = RepactacionDeuda.objects.select_related('arrendatario', 'contrato_origen').all()
    audit_entity_type = 'repactacion_deuda'
    audit_entity_label = 'repactacion de deuda'


class RepactacionDeudaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = RepactacionDeudaSerializer
    queryset = RepactacionDeuda.objects.select_related('arrendatario', 'contrato_origen').all()
    audit_entity_type = 'repactacion_deuda'
    audit_entity_label = 'repactacion de deuda'


class CodigoCobroResidualListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodigoCobroResidualSerializer
    queryset = CodigoCobroResidual.objects.select_related('arrendatario', 'contrato_origen').all()
    audit_entity_type = 'codigo_cobro_residual'
    audit_entity_label = 'codigo de cobro residual'


class CodigoCobroResidualDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodigoCobroResidualSerializer
    queryset = CodigoCobroResidual.objects.select_related('arrendatario', 'contrato_origen').all()
    audit_entity_type = 'codigo_cobro_residual'
    audit_entity_label = 'codigo de cobro residual'


class EstadoCuentaArrendatarioListView(generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = EstadoCuentaArrendatarioSerializer
    queryset = EstadoCuentaArrendatario.objects.select_related('arrendatario').all()


class EstadoCuentaArrendatarioDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = EstadoCuentaArrendatarioSerializer
    queryset = EstadoCuentaArrendatario.objects.select_related('arrendatario').all()
    audit_entity_type = 'estado_cuenta_arrendatario'
    audit_entity_label = 'estado de cuenta arrendatario'


class EstadoCuentaArrendatarioRebuildView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = EstadoCuentaRecalculoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        arrendatario = serializer.validated_data['arrendatario']
        estado = rebuild_account_state(arrendatario)
        create_audit_event(
            event_type='cobranza.estado_cuenta_arrendatario.rebuilt',
            entity_type='estado_cuenta_arrendatario',
            entity_id=str(estado.pk),
            summary='Estado de cuenta arrendatario recalculado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'arrendatario_id': arrendatario.pk},
        )
        return Response(EstadoCuentaArrendatarioSerializer(estado).data, status=status.HTTP_200_OK)
