from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.scope_access import ScopedQuerysetMixin, scope_queryset_for_user

from .models import ConexionBancaria, IngresoDesconocido, MovimientoBancarioImportado
from .serializers import ConexionBancariaSerializer, IngresoDesconocidoSerializer, MovimientoBancarioImportadoSerializer
from .services import reconcile_exact_movement


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
        if hasattr(instance, 'estado_conexion'):
            return instance.estado_conexion
        if hasattr(instance, 'estado'):
            return instance.estado
        if hasattr(instance, 'estado_conciliacion'):
            return instance.estado_conciliacion
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'conciliacion.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class ConexionBancariaListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ConexionBancariaSerializer
    queryset = ConexionBancaria.objects.select_related('cuenta_recaudadora').all()
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
    audit_entity_type = 'conexion_bancaria'
    audit_entity_label = 'conexion bancaria'


class ConexionBancariaDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ConexionBancariaSerializer
    queryset = ConexionBancaria.objects.select_related('cuenta_recaudadora').all()
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
    audit_entity_type = 'conexion_bancaria'
    audit_entity_label = 'conexion bancaria'


class MovimientoBancarioListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = MovimientoBancarioImportadoSerializer
    queryset = MovimientoBancarioImportado.objects.select_related(
        'conexion_bancaria',
        'pago_mensual',
        'codigo_cobro_residual',
    ).all()
    bank_account_scope_paths = ('conexion_bancaria__cuenta_recaudadora_id',)
    audit_entity_type = 'movimiento_bancario'
    audit_entity_label = 'movimiento bancario'

    def perform_create(self, serializer):
        instance = super().perform_create(serializer)
        result = reconcile_exact_movement(instance)
        create_audit_event(
            event_type='conciliacion.movimiento_bancario.match_attempted',
            entity_type='movimiento_bancario',
            entity_id=str(instance.pk),
            summary='Intento de match exacto sobre movimiento bancario',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata=result,
        )


class MovimientoBancarioDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = MovimientoBancarioImportadoSerializer
    queryset = MovimientoBancarioImportado.objects.select_related(
        'conexion_bancaria',
        'pago_mensual',
        'codigo_cobro_residual',
    ).all()
    bank_account_scope_paths = ('conexion_bancaria__cuenta_recaudadora_id',)


class MovimientoBancarioRetryMatchView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        movimiento = generics.get_object_or_404(
            scope_queryset_for_user(
                MovimientoBancarioImportado.objects.select_related('conexion_bancaria'),
                request.user,
                bank_account_paths=('conexion_bancaria__cuenta_recaudadora_id',),
            ),
            pk=pk,
        )
        result = reconcile_exact_movement(movimiento)
        create_audit_event(
            event_type='conciliacion.movimiento_bancario.match_retried',
            entity_type='movimiento_bancario',
            entity_id=str(movimiento.pk),
            summary='Reintento manual de match exacto',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata=result,
        )
        return Response(MovimientoBancarioImportadoSerializer(movimiento).data, status=status.HTTP_200_OK)


class IngresoDesconocidoListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = IngresoDesconocidoSerializer
    queryset = IngresoDesconocido.objects.select_related('movimiento_bancario', 'cuenta_recaudadora').all()
    bank_account_scope_paths = ('cuenta_recaudadora_id',)


class IngresoDesconocidoDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = IngresoDesconocidoSerializer
    queryset = IngresoDesconocido.objects.select_related('movimiento_bancario', 'cuenta_recaudadora').all()
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
