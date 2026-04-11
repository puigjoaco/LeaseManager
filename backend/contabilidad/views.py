from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import ControlModulePermission

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MatrizReglasContables,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
)
from .serializers import (
    AsientoContableSerializer,
    BalanceComprobacionSerializer,
    CierreMensualContableSerializer,
    CierreMensualPrepareSerializer,
    ConfiguracionFiscalEmpresaSerializer,
    CuentaContableSerializer,
    EventoContableSerializer,
    LibroDiarioSerializer,
    LibroMayorSerializer,
    MatrizReglasContablesSerializer,
    ObligacionTributariaMensualSerializer,
    PoliticaReversoContableSerializer,
    RegimenTributarioEmpresaSerializer,
    ReglaContableSerializer,
)
from .services import approve_monthly_close, post_accounting_event, prepare_monthly_close, reopen_monthly_close


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
        self._create_audit_event(instance=instance, action='created')
        return instance

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
        for field in ('estado', 'estado_contable'):
            if hasattr(instance, field):
                return getattr(instance, field)
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'contabilidad.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class RegimenTributarioEmpresaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = RegimenTributarioEmpresaSerializer
    queryset = RegimenTributarioEmpresa.objects.all()
    audit_entity_type = 'regimen_tributario'
    audit_entity_label = 'regimen tributario'


class RegimenTributarioEmpresaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = RegimenTributarioEmpresaSerializer
    queryset = RegimenTributarioEmpresa.objects.all()
    audit_entity_type = 'regimen_tributario'
    audit_entity_label = 'regimen tributario'


class ConfiguracionFiscalEmpresaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ConfiguracionFiscalEmpresaSerializer
    queryset = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario').all()
    audit_entity_type = 'configuracion_fiscal'
    audit_entity_label = 'configuracion fiscal'


class ConfiguracionFiscalEmpresaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ConfiguracionFiscalEmpresaSerializer
    queryset = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario').all()
    audit_entity_type = 'configuracion_fiscal'
    audit_entity_label = 'configuracion fiscal'


class CuentaContableListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CuentaContableSerializer
    queryset = CuentaContable.objects.select_related('empresa', 'padre').all()
    audit_entity_type = 'cuenta_contable'
    audit_entity_label = 'cuenta contable'


class CuentaContableDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CuentaContableSerializer
    queryset = CuentaContable.objects.select_related('empresa', 'padre').all()
    audit_entity_type = 'cuenta_contable'
    audit_entity_label = 'cuenta contable'


class ReglaContableListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ReglaContableSerializer
    queryset = ReglaContable.objects.select_related('empresa').all()
    audit_entity_type = 'regla_contable'
    audit_entity_label = 'regla contable'


class ReglaContableDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ReglaContableSerializer
    queryset = ReglaContable.objects.select_related('empresa').all()
    audit_entity_type = 'regla_contable'
    audit_entity_label = 'regla contable'


class MatrizReglasContablesListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = MatrizReglasContablesSerializer
    queryset = MatrizReglasContables.objects.select_related('regla_contable', 'cuenta_debe', 'cuenta_haber').all()
    audit_entity_type = 'matriz_reglas'
    audit_entity_label = 'matriz de reglas contables'


class MatrizReglasContablesDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = MatrizReglasContablesSerializer
    queryset = MatrizReglasContables.objects.select_related('regla_contable', 'cuenta_debe', 'cuenta_haber').all()
    audit_entity_type = 'matriz_reglas'
    audit_entity_label = 'matriz de reglas contables'


class EventoContableListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = EventoContableSerializer
    queryset = EventoContable.objects.select_related('empresa').all()
    audit_entity_type = 'evento_contable'
    audit_entity_label = 'evento contable'

    def perform_create(self, serializer):
        event = super().perform_create(serializer)
        asiento = post_accounting_event(event)
        create_audit_event(
            event_type='contabilidad.evento_contable.post_attempted',
            entity_type='evento_contable',
            entity_id=str(event.pk),
            summary='Intento de contabilizacion de evento',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata={'asiento_id': asiento.pk if asiento else None, 'estado_contable': event.estado_contable},
        )


class EventoContableDetailView(generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = EventoContableSerializer
    queryset = EventoContable.objects.select_related('empresa').all()


class EventoContablePostView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        event = generics.get_object_or_404(EventoContable.objects.select_related('empresa'), pk=pk)
        asiento = post_accounting_event(event)
        create_audit_event(
            event_type='contabilidad.evento_contable.post_retried',
            entity_type='evento_contable',
            entity_id=str(event.pk),
            summary='Reintento de contabilizacion',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'asiento_id': asiento.pk if asiento else None, 'estado_contable': event.estado_contable},
        )
        return Response(EventoContableSerializer(event).data, status=status.HTTP_200_OK)


class AsientoContableListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AsientoContableSerializer
    queryset = AsientoContable.objects.select_related('evento_contable').prefetch_related('movimientos').all()


class AsientoContableDetailView(generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AsientoContableSerializer
    queryset = AsientoContable.objects.select_related('evento_contable').prefetch_related('movimientos').all()


class PoliticaReversoContableListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = PoliticaReversoContableSerializer
    queryset = PoliticaReversoContable.objects.select_related('empresa').all()
    audit_entity_type = 'politica_reverso'
    audit_entity_label = 'politica reverso contable'


class PoliticaReversoContableDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = PoliticaReversoContableSerializer
    queryset = PoliticaReversoContable.objects.select_related('empresa').all()
    audit_entity_type = 'politica_reverso'
    audit_entity_label = 'politica reverso contable'


class ObligacionTributariaMensualListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ObligacionTributariaMensualSerializer
    queryset = ObligacionTributariaMensual.objects.select_related('empresa').all()


class LibroDiarioListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = LibroDiarioSerializer
    queryset = LibroDiario.objects.select_related('empresa').all()


class LibroMayorListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = LibroMayorSerializer
    queryset = LibroMayor.objects.select_related('empresa').all()


class BalanceComprobacionListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = BalanceComprobacionSerializer
    queryset = BalanceComprobacion.objects.select_related('empresa').all()


class CierreMensualContableListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CierreMensualContableSerializer
    queryset = CierreMensualContable.objects.select_related('empresa').all()


class CierreMensualContableDetailView(generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CierreMensualContableSerializer
    queryset = CierreMensualContable.objects.select_related('empresa').all()


class CierreMensualPrepareView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = CierreMensualPrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            close = prepare_monthly_close(
                serializer.validated_data['empresa'],
                serializer.validated_data['anio'],
                serializer.validated_data['mes'],
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        create_audit_event(
            event_type='contabilidad.cierre_mensual.prepared',
            entity_type='cierre_mensual_contable',
            entity_id=str(close.pk),
            summary='Cierre mensual preparado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(CierreMensualContableSerializer(close).data, status=status.HTTP_200_OK)


class CierreMensualApproveView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        close = generics.get_object_or_404(CierreMensualContable, pk=pk)
        try:
            close = approve_monthly_close(close)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        create_audit_event(
            event_type='contabilidad.cierre_mensual.approved',
            entity_type='cierre_mensual_contable',
            entity_id=str(close.pk),
            summary='Cierre mensual aprobado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(CierreMensualContableSerializer(close).data, status=status.HTTP_200_OK)


class CierreMensualReopenView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        close = generics.get_object_or_404(CierreMensualContable, pk=pk)
        try:
            close = reopen_monthly_close(close)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        create_audit_event(
            event_type='contabilidad.cierre_mensual.reopened',
            entity_type='cierre_mensual_contable',
            entity_id=str(close.pk),
            summary='Cierre mensual reabierto',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(CierreMensualContableSerializer(close).data, status=status.HTTP_200_OK)
