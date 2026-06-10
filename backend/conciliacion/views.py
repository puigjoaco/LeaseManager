from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference
from core.scope_access import (
    ScopedQuerysetMixin,
    get_scope_access,
    scope_queryset_for_access,
    scope_queryset_for_user,
)
from operacion.models import CuentaRecaudadora

from .models import (
    CuadraturaBancaria,
    ConexionBancaria,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    TransferenciaIntercuenta,
)
from .serializers import (
    CuadraturaBancariaSerializer,
    ConexionBancariaSerializer,
    IngresoDesconocidoSerializer,
    MovimientoBancarioImportadoSerializer,
    TransferenciaIntercuentaSerializer,
)
from .services import MOVEMENT_MATCH_RETRIED_EVENT_TYPE, reconcile_exact_movement


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''
    audit_state_fields = ('estado_conexion', 'estado', 'estado_conciliacion')

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            self._create_audit_event(instance=instance, action='created')
        return instance

    def perform_update(self, serializer):
        previous_state_field, previous_state = self._extract_state(serializer.instance)
        with transaction.atomic():
            instance = serializer.save()
            self._create_audit_event(instance=instance, action='updated')
            current_state_field, current_state = self._extract_state(instance)
            if previous_state != current_state:
                self._create_audit_event(
                    instance=instance,
                    action='state_changed',
                    summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
                    metadata=self._state_change_metadata(
                        previous_field=previous_state_field,
                        previous_state=previous_state,
                        current_field=current_state_field,
                        current_state=current_state,
                    ),
                )
        return instance

    def _extract_state(self, instance):
        for field in self.audit_state_fields:
            if hasattr(instance, field):
                return field, getattr(instance, field)
        return None, None

    def _state_change_metadata(self, *, previous_field, previous_state, current_field, current_state):
        return {
            'campo_estado': current_field or previous_field,
            'estado_anterior': previous_state,
            'estado_nuevo': current_state,
        }

    def _create_audit_event(self, *, instance, action, summary='', metadata=None):
        create_audit_event(
            event_type=f'conciliacion.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata=metadata,
        )


class ConciliacionSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)
        cuentas = scope_queryset_for_access(
            CuentaRecaudadora.objects.select_related('empresa_owner', 'socio_owner').order_by('numero_cuenta', 'id'),
            access,
            bank_account_paths=('id',),
        )
        conexiones = scope_queryset_for_access(
            ConexionBancaria.objects.select_related('cuenta_recaudadora').order_by('-id'),
            access,
            bank_account_paths=('cuenta_recaudadora_id',),
        )
        movimientos = scope_queryset_for_access(
            MovimientoBancarioImportado.objects.select_related(
                'conexion_bancaria',
                'pago_mensual',
                'codigo_cobro_residual',
            ).order_by('-fecha_movimiento', '-id'),
            access,
            bank_account_paths=('conexion_bancaria__cuenta_recaudadora_id',),
        )
        ingresos = scope_queryset_for_access(
            IngresoDesconocido.objects.select_related('movimiento_bancario', 'cuenta_recaudadora').order_by('-fecha_movimiento', '-id'),
            access,
            bank_account_paths=('cuenta_recaudadora_id',),
        )
        cuadraturas = scope_queryset_for_access(
            CuadraturaBancaria.objects.select_related('cuenta_recaudadora').order_by('-periodo_economico', '-id'),
            access,
            bank_account_paths=('cuenta_recaudadora_id',),
        )
        transferencias = scope_queryset_for_access(
            TransferenciaIntercuenta.objects.select_related(
                'movimiento_origen__conexion_bancaria__cuenta_recaudadora',
                'movimiento_destino__conexion_bancaria__cuenta_recaudadora',
            ).order_by('-periodo_economico', '-id'),
            access,
            bank_account_paths=(
                'movimiento_origen__conexion_bancaria__cuenta_recaudadora_id',
                'movimiento_destino__conexion_bancaria__cuenta_recaudadora_id',
            ),
        )

        return Response(
            {
                'cuentas': [
                    {
                        'id': item.id,
                        'numero_cuenta': item.numero_cuenta_redacted,
                        'numero_cuenta_redacted': item.numero_cuenta_redacted,
                        'owner_display': item.owner_display,
                    }
                    for item in cuentas
                ],
                'conexiones': [
                    {
                        'id': item.id,
                        'cuenta_recaudadora': item.cuenta_recaudadora_id,
                        'provider_key': item.provider_key,
                        'credencial_ref': redact_sensitive_reference(item.credencial_ref),
                        'scope': item.scope,
                        'estado_conexion': item.estado_conexion,
                    }
                    for item in conexiones
                ],
                'movimientos': [
                    {
                        'id': item.id,
                        'fecha_movimiento': item.fecha_movimiento,
                        'tipo_movimiento': item.tipo_movimiento,
                        'monto': item.monto,
                        'descripcion_origen': item.descripcion_origen,
                        'referencia': redact_sensitive_reference(item.referencia),
                        'estado_conciliacion': item.estado_conciliacion,
                    }
                    for item in movimientos
                ],
                'ingresos_desconocidos': [
                    {
                        'id': item.id,
                        'cuenta_recaudadora': item.cuenta_recaudadora_id,
                        'fecha_movimiento': item.fecha_movimiento,
                        'monto': item.monto,
                        'descripcion_origen': item.descripcion_origen,
                        'estado': item.estado,
                        'sugerencia_asistida': redact_sensitive_payload(item.sugerencia_asistida or {}),
                    }
                    for item in ingresos
                ],
                'cuadraturas_bancarias': [
                    {
                        'id': item.id,
                        'cuenta_recaudadora': item.cuenta_recaudadora_id,
                        'periodo_economico': item.periodo_economico,
                        'fecha_cuadratura': item.fecha_cuadratura,
                        'saldo_sistema_clp': item.saldo_sistema_clp,
                        'saldo_banco_clp': item.saldo_banco_clp,
                        'diferencia_clp': item.diferencia_clp,
                        'estado': item.estado,
                        'evidencia_cuadratura_ref': redact_sensitive_reference(item.evidencia_cuadratura_ref),
                        'responsable_ref': redact_sensitive_reference(item.responsable_ref),
                        'rationale': redact_sensitive_reference(item.rationale),
                    }
                    for item in cuadraturas
                ],
                'transferencias_intercuenta': [
                    {
                        'id': item.id,
                        'movimiento_origen': item.movimiento_origen_id,
                        'movimiento_destino': item.movimiento_destino_id,
                        'periodo_economico': item.periodo_economico,
                        'entidad_origen_tipo': item.entidad_origen_tipo,
                        'entidad_origen_id': item.entidad_origen_id,
                        'entidad_destino_tipo': item.entidad_destino_tipo,
                        'entidad_destino_id': item.entidad_destino_id,
                        'criterio_conciliacion': redact_sensitive_reference(item.criterio_conciliacion),
                        'evidencia_transferencia_ref': redact_sensitive_reference(item.evidencia_transferencia_ref),
                        'responsable_ref': redact_sensitive_reference(item.responsable_ref),
                        'rationale': redact_sensitive_reference(item.rationale),
                    }
                    for item in transferencias
                ],
            }
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
        with transaction.atomic():
            instance = serializer.save()
            self._create_audit_event(instance=instance, action='created')
            reconcile_exact_movement(
                instance,
                audit_actor_user=self.request.user,
                audit_ip_address=self.request.META.get('REMOTE_ADDR'),
            )
        return instance


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
        try:
            with transaction.atomic():
                reconcile_exact_movement(
                    movimiento,
                    audit_event_type=MOVEMENT_MATCH_RETRIED_EVENT_TYPE,
                    audit_actor_user=request.user,
                    audit_ip_address=request.META.get('REMOTE_ADDR'),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        movimiento.refresh_from_db()
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


class CuadraturaBancariaListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CuadraturaBancariaSerializer
    queryset = CuadraturaBancaria.objects.select_related('cuenta_recaudadora').all()
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
    audit_entity_type = 'cuadratura_bancaria'
    audit_entity_label = 'cuadratura bancaria'


class CuadraturaBancariaDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CuadraturaBancariaSerializer
    queryset = CuadraturaBancaria.objects.select_related('cuenta_recaudadora').all()
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
    audit_entity_type = 'cuadratura_bancaria'
    audit_entity_label = 'cuadratura bancaria'


class TransferenciaIntercuentaListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = TransferenciaIntercuentaSerializer
    queryset = TransferenciaIntercuenta.objects.select_related(
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora',
    ).all()
    bank_account_scope_paths = (
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora_id',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora_id',
    )


class TransferenciaIntercuentaDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = TransferenciaIntercuentaSerializer
    queryset = TransferenciaIntercuenta.objects.select_related(
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora',
    ).all()
    bank_account_scope_paths = (
        'movimiento_origen__conexion_bancaria__cuenta_recaudadora_id',
        'movimiento_destino__conexion_bancaria__cuenta_recaudadora_id',
    )
