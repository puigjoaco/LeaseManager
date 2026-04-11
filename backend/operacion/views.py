from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.scope_access import ScopedQuerysetMixin
from rest_framework import generics

from .models import AsignacionCanalOperacion, CuentaRecaudadora, IdentidadDeEnvio, MandatoOperacion
from .serializers import (
    AsignacionCanalOperacionSerializer,
    CuentaRecaudadoraSerializer,
    IdentidadDeEnvioSerializer,
    MandatoOperacionSerializer,
)


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''

    def perform_create(self, serializer):
        instance = serializer.save()
        self._create_audit_event(instance=instance, action='created')

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        instance = serializer.save()
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )

    def _extract_state(self, instance):
        for field in ('estado_operativo', 'estado'):
            if hasattr(instance, field):
                return getattr(instance, field)
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'operacion.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class CuentaRecaudadoraListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CuentaRecaudadoraSerializer
    queryset = CuentaRecaudadora.objects.select_related('empresa_owner', 'socio_owner').all()
    bank_account_scope_paths = ('id',)
    audit_entity_type = 'cuenta_recaudadora'
    audit_entity_label = 'cuenta recaudadora'


class CuentaRecaudadoraDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CuentaRecaudadoraSerializer
    queryset = CuentaRecaudadora.objects.select_related('empresa_owner', 'socio_owner').all()
    bank_account_scope_paths = ('id',)
    audit_entity_type = 'cuenta_recaudadora'
    audit_entity_label = 'cuenta recaudadora'


class IdentidadDeEnvioListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = IdentidadDeEnvioSerializer
    queryset = IdentidadDeEnvio.objects.select_related('empresa_owner', 'socio_owner').all()
    company_scope_paths = ('empresa_owner_id',)
    property_scope_paths = ('asignaciones_operacion__mandato_operacion__propiedad_id',)
    audit_entity_type = 'identidad_envio'
    audit_entity_label = 'identidad de envio'


class IdentidadDeEnvioDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = IdentidadDeEnvioSerializer
    queryset = IdentidadDeEnvio.objects.select_related('empresa_owner', 'socio_owner').all()
    company_scope_paths = ('empresa_owner_id',)
    property_scope_paths = ('asignaciones_operacion__mandato_operacion__propiedad_id',)
    audit_entity_type = 'identidad_envio'
    audit_entity_label = 'identidad de envio'


class MandatoOperacionListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = MandatoOperacionSerializer
    queryset = MandatoOperacion.objects.select_related(
        'propiedad',
        'propietario_empresa_owner',
        'propietario_comunidad_owner',
        'propietario_socio_owner',
        'administrador_empresa_owner',
        'administrador_socio_owner',
        'recaudador_empresa_owner',
        'recaudador_socio_owner',
        'entidad_facturadora',
        'cuenta_recaudadora',
    ).all()
    property_scope_paths = ('propiedad_id',)
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
    audit_entity_type = 'mandato_operacion'
    audit_entity_label = 'mandato operativo'


class MandatoOperacionDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = MandatoOperacionSerializer
    queryset = MandatoOperacion.objects.select_related(
        'propiedad',
        'propietario_empresa_owner',
        'propietario_comunidad_owner',
        'propietario_socio_owner',
        'administrador_empresa_owner',
        'administrador_socio_owner',
        'recaudador_empresa_owner',
        'recaudador_socio_owner',
        'entidad_facturadora',
        'cuenta_recaudadora',
    ).all()
    property_scope_paths = ('propiedad_id',)
    bank_account_scope_paths = ('cuenta_recaudadora_id',)
    audit_entity_type = 'mandato_operacion'
    audit_entity_label = 'mandato operativo'


class AsignacionCanalOperacionListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AsignacionCanalOperacionSerializer
    queryset = AsignacionCanalOperacion.objects.select_related(
        'mandato_operacion',
        'identidad_envio',
    ).all()
    property_scope_paths = ('mandato_operacion__propiedad_id',)
    bank_account_scope_paths = ('mandato_operacion__cuenta_recaudadora_id',)
    audit_entity_type = 'asignacion_canal_operacion'
    audit_entity_label = 'asignacion de canal'


class AsignacionCanalOperacionDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AsignacionCanalOperacionSerializer
    queryset = AsignacionCanalOperacion.objects.select_related(
        'mandato_operacion',
        'identidad_envio',
    ).all()
    property_scope_paths = ('mandato_operacion__propiedad_id',)
    bank_account_scope_paths = ('mandato_operacion__cuenta_recaudadora_id',)
    audit_entity_type = 'asignacion_canal_operacion'
    audit_entity_label = 'asignacion de canal'
