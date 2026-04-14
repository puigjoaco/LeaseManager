from django.db import transaction
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.scope_access import ScopedQuerysetMixin, get_scope_access, scope_queryset_for_access
from operacion.models import MandatoOperacion

from .models import Arrendatario, AvisoTermino, CodeudorSolidario, Contrato, ContratoPropiedad, PeriodoContractual
from .serializers import (
    ArrendatarioSerializer,
    AvisoTerminoSerializer,
    CodeudorSolidarioReadSerializer,
    ContratoPropiedadReadSerializer,
    ContratoSerializer,
    PeriodoContractualReadSerializer,
)


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
        for field in ('estado_contacto', 'estado'):
            if hasattr(instance, field):
                return getattr(instance, field)
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'contratos.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class ContractsSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)
        arrendatarios = scope_queryset_for_access(
            Arrendatario.objects.all().order_by('nombre_razon_social', 'id'),
            access,
            property_paths=('contratos__mandato_operacion__propiedad_id',),
        )
        mandatos = scope_queryset_for_access(
            MandatoOperacion.objects.select_related(
                'propiedad',
                'propietario_empresa_owner',
                'propietario_comunidad_owner',
                'propietario_socio_owner',
            ).order_by('id'),
            access,
            property_paths=('propiedad_id',),
            bank_account_paths=('cuenta_recaudadora_id',),
        )
        contratos = scope_queryset_for_access(
            Contrato.objects.select_related('mandato_operacion__propiedad', 'arrendatario').prefetch_related(
                'contrato_propiedades__propiedad',
                'periodos_contractuales',
            ).order_by('codigo_contrato', 'id'),
            access,
            property_paths=('mandato_operacion__propiedad_id',),
        )
        avisos = scope_queryset_for_access(
            AvisoTermino.objects.select_related('contrato').order_by('-fecha_efectiva', '-id'),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )

        return Response(
            {
                'arrendatarios': [
                    {
                        'id': item.id,
                        'nombre_razon_social': item.nombre_razon_social,
                        'rut': item.rut,
                        'tipo_arrendatario': item.tipo_arrendatario,
                        'email': item.email or '',
                        'telefono': item.telefono or '',
                        'domicilio_notificaciones': item.domicilio_notificaciones or '',
                        'estado_contacto': item.estado_contacto,
                        'whatsapp_bloqueado': item.whatsapp_bloqueado,
                    }
                    for item in arrendatarios
                ],
                'mandatos': [
                    {
                        'id': item.id,
                        'propiedad_codigo': item.propiedad.codigo_propiedad,
                        'propietario_display': (
                            item.propietario_empresa_owner.razon_social if item.propietario_empresa_owner_id
                            else item.propietario_comunidad_owner.nombre if item.propietario_comunidad_owner_id
                            else item.propietario_socio_owner.nombre
                        ),
                    }
                    for item in mandatos
                ],
                'contratos': [
                    {
                        'id': item.id,
                        'codigo_contrato': item.codigo_contrato,
                        'mandato_operacion': item.mandato_operacion_id,
                        'arrendatario': item.arrendatario_id,
                        'fecha_inicio': item.fecha_inicio,
                        'fecha_fin_vigente': item.fecha_fin_vigente,
                        'fecha_entrega': item.fecha_entrega,
                        'dia_pago_mensual': item.dia_pago_mensual,
                        'plazo_notificacion_termino_dias': item.plazo_notificacion_termino_dias,
                        'dias_prealerta_admin': item.dias_prealerta_admin,
                        'estado': item.estado,
                        'tiene_tramos': item.tiene_tramos,
                        'tiene_gastos_comunes': item.tiene_gastos_comunes,
                        'contrato_propiedades_detail': [
                            {
                                'propiedad': prop.propiedad_id,
                                'propiedad_codigo': prop.propiedad.codigo_propiedad,
                                'propiedad_direccion': prop.propiedad.direccion,
                                'rol_en_contrato': prop.rol_en_contrato,
                            }
                            for prop in item.contrato_propiedades.all()
                        ],
                        'periodos_contractuales_detail': [
                            {
                                'numero_periodo': periodo.numero_periodo,
                                'fecha_inicio': periodo.fecha_inicio,
                                'fecha_fin': periodo.fecha_fin,
                                'monto_base': periodo.monto_base,
                                'moneda_base': periodo.moneda_base,
                                'tipo_periodo': periodo.tipo_periodo,
                                'origen_periodo': periodo.origen_periodo,
                            }
                            for periodo in item.periodos_contractuales.all()
                        ],
                    }
                    for item in contratos
                ],
                'avisos': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'fecha_efectiva': item.fecha_efectiva,
                        'causal': item.causal,
                        'estado': item.estado,
                    }
                    for item in avisos
                ],
            }
        )


class ArrendatarioListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ArrendatarioSerializer
    queryset = Arrendatario.objects.all()
    property_scope_paths = ('contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'arrendatario'
    audit_entity_label = 'arrendatario'


class ArrendatarioDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ArrendatarioSerializer
    queryset = Arrendatario.objects.all()
    property_scope_paths = ('contratos__mandato_operacion__propiedad_id',)
    audit_entity_type = 'arrendatario'
    audit_entity_label = 'arrendatario'


class ContratoListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.select_related('mandato_operacion', 'arrendatario').prefetch_related(
        'contrato_propiedades__propiedad',
        'periodos_contractuales',
        'codeudores_solidarios',
    )
    property_scope_paths = ('mandato_operacion__propiedad_id',)
    audit_entity_type = 'contrato'
    audit_entity_label = 'contrato'


class ContratoDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoSerializer
    queryset = Contrato.objects.select_related('mandato_operacion', 'arrendatario').prefetch_related(
        'contrato_propiedades__propiedad',
        'periodos_contractuales',
        'codeudores_solidarios',
    )
    property_scope_paths = ('mandato_operacion__propiedad_id',)
    audit_entity_type = 'contrato'
    audit_entity_label = 'contrato'


class AvisoTerminoListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AvisoTerminoSerializer
    queryset = AvisoTermino.objects.select_related('contrato', 'registrado_por').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'aviso_termino'
    audit_entity_label = 'aviso de termino'


class AvisoTerminoDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = AvisoTerminoSerializer
    queryset = AvisoTermino.objects.select_related('contrato', 'registrado_por').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
    audit_entity_type = 'aviso_termino'
    audit_entity_label = 'aviso de termino'


class ContratoPropiedadListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoPropiedadReadSerializer
    queryset = ContratoPropiedad.objects.select_related('contrato', 'propiedad').all()
    property_scope_paths = ('propiedad_id',)


class ContratoPropiedadDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ContratoPropiedadReadSerializer
    queryset = ContratoPropiedad.objects.select_related('contrato', 'propiedad').all()
    property_scope_paths = ('propiedad_id',)


class PeriodoContractualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PeriodoContractualReadSerializer
    queryset = PeriodoContractual.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class PeriodoContractualDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PeriodoContractualReadSerializer
    queryset = PeriodoContractual.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class CodeudorSolidarioListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodeudorSolidarioReadSerializer
    queryset = CodeudorSolidario.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)


class CodeudorSolidarioDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = CodeudorSolidarioReadSerializer
    queryset = CodeudorSolidario.objects.select_related('contrato').all()
    property_scope_paths = ('contrato__mandato_operacion__propiedad_id',)
