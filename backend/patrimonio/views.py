from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.scope_access import ScopedQuerysetMixin, get_scope_access, scope_queryset_for_access
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ComunidadPatrimonial, Empresa, ParticipacionPatrimonial, Propiedad, Socio
from .serializers import (
    ComunidadPatrimonialSerializer,
    EmpresaSerializer,
    ParticipacionPatrimonialReadSerializer,
    PropiedadSerializer,
    SocioSerializer,
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
        if hasattr(instance, 'estado'):
            return instance.estado
        if hasattr(instance, 'activo'):
            return instance.activo
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'patrimonio.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class PatrimonioSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)
        socios = scope_queryset_for_access(
            Socio.objects.all().order_by('nombre', 'id'),
            access,
            property_paths=(
                'propiedades_directas__id',
                'representaciones_comunidad__comunidad__propiedades__id',
                'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
                'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
            ),
        )
        empresas = scope_queryset_for_access(
            Empresa.objects.prefetch_related('participaciones').order_by('razon_social', 'id'),
            access,
            company_paths=('id',),
        )
        comunidades = scope_queryset_for_access(
            ComunidadPatrimonial.objects.prefetch_related(
                'representaciones__socio_representante',
                'participaciones',
            ).order_by('nombre', 'id'),
            access,
            property_paths=('propiedades__id',),
        )
        propiedades = scope_queryset_for_access(
            Propiedad.objects.select_related('empresa_owner', 'comunidad_owner', 'socio_owner').order_by('codigo_propiedad', 'id'),
            access,
            property_paths=('id',),
        )

        today = timezone.localdate()

        return Response(
            {
                'socios': [
                    {
                        'id': item.id,
                        'nombre': item.nombre,
                        'rut': item.rut,
                        'email': item.email or '',
                        'telefono': item.telefono or '',
                        'domicilio': item.domicilio or '',
                        'activo': item.activo,
                    }
                    for item in socios
                ],
                'empresas': [
                    {
                        'id': item.id,
                        'razon_social': item.razon_social,
                        'rut': item.rut,
                        'estado': item.estado,
                        'participaciones_count': item.participaciones.count(),
                    }
                    for item in empresas
                ],
                'comunidades': [
                    {
                        'id': item.id,
                        'nombre': item.nombre,
                        'estado': item.estado,
                        'participaciones_count': item.participaciones.count(),
                        'representacion_vigente': (
                            {
                                'modo_representacion': representacion.modo_representacion,
                                'socio_representante_nombre': representacion.socio_representante.nombre,
                            }
                            if (
                                representacion := next(
                                    (
                                        rep for rep in item.representaciones.all()
                                        if rep.activo and (rep.vigente_hasta is None or rep.vigente_hasta >= today)
                                    ),
                                    None,
                                )
                            )
                            else None
                        ),
                    }
                    for item in comunidades
                ],
                'propiedades': [
                    {
                        'id': item.id,
                        'codigo_propiedad': item.codigo_propiedad,
                        'direccion': item.direccion,
                        'comuna': item.comuna,
                        'region': item.region,
                        'rol_avaluo': item.rol_avaluo,
                        'tipo_inmueble': item.tipo_inmueble,
                        'owner_tipo': item.owner_tipo,
                        'owner_id': item.owner_id,
                        'owner_display': (
                            item.empresa_owner.razon_social if item.empresa_owner_id
                            else item.comunidad_owner.nombre if item.comunidad_owner_id
                            else item.socio_owner.nombre
                        ),
                        'estado': item.estado,
                    }
                    for item in propiedades
                ],
            }
        )


class SocioListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = SocioSerializer
    queryset = Socio.objects.all()
    property_scope_paths = (
        'propiedades_directas__id',
        'representaciones_comunidad__comunidad__propiedades__id',
        'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
        'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
    )
    audit_entity_type = 'socio'
    audit_entity_label = 'socio'


class SocioDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = SocioSerializer
    queryset = Socio.objects.all()
    property_scope_paths = (
        'propiedades_directas__id',
        'representaciones_comunidad__comunidad__propiedades__id',
        'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
        'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
    )
    audit_entity_type = 'socio'
    audit_entity_label = 'socio'


class EmpresaListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = EmpresaSerializer
    queryset = Empresa.objects.prefetch_related('participaciones__participante_socio').all()
    company_scope_paths = ('id',)
    audit_entity_type = 'empresa'
    audit_entity_label = 'empresa'


class EmpresaDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = EmpresaSerializer
    queryset = Empresa.objects.prefetch_related('participaciones__participante_socio').all()
    company_scope_paths = ('id',)
    audit_entity_type = 'empresa'
    audit_entity_label = 'empresa'


class ComunidadListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ComunidadPatrimonialSerializer
    queryset = ComunidadPatrimonial.objects.prefetch_related(
        'representaciones__socio_representante',
        'participaciones__participante_socio',
        'participaciones__participante_empresa',
    )
    property_scope_paths = ('propiedades__id',)
    audit_entity_type = 'comunidad'
    audit_entity_label = 'comunidad'


class ComunidadDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ComunidadPatrimonialSerializer
    queryset = ComunidadPatrimonial.objects.prefetch_related(
        'representaciones__socio_representante',
        'participaciones__participante_socio',
        'participaciones__participante_empresa',
    )
    property_scope_paths = ('propiedades__id',)
    audit_entity_type = 'comunidad'
    audit_entity_label = 'comunidad'


class PropiedadListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PropiedadSerializer
    queryset = Propiedad.objects.select_related('empresa_owner', 'comunidad_owner', 'socio_owner').all()
    property_scope_paths = ('id',)
    audit_entity_type = 'propiedad'
    audit_entity_label = 'propiedad'


class PropiedadDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = PropiedadSerializer
    queryset = Propiedad.objects.select_related('empresa_owner', 'comunidad_owner', 'socio_owner').all()
    property_scope_paths = ('id',)
    audit_entity_type = 'propiedad'
    audit_entity_label = 'propiedad'


class ParticipacionListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ParticipacionPatrimonialReadSerializer
    queryset = ParticipacionPatrimonial.objects.select_related(
        'participante_socio',
        'participante_empresa',
        'empresa_owner',
        'comunidad_owner',
    ).all()
    property_scope_paths = ('empresa_owner__propiedades__id', 'comunidad_owner__propiedades__id')


class ParticipacionDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ParticipacionPatrimonialReadSerializer
    queryset = ParticipacionPatrimonial.objects.select_related(
        'participante_socio',
        'participante_empresa',
        'empresa_owner',
        'comunidad_owner',
    ).all()
    property_scope_paths = ('empresa_owner__propiedades__id', 'comunidad_owner__propiedades__id')
