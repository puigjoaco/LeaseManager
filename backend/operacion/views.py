from audit.services import create_audit_event
from core.permissions import OperationalModulePermission
from core.scope_access import ScopedQuerysetMixin, get_scope_access, scope_queryset_for_access
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView

from patrimonio.models import ComunidadPatrimonial, Empresa, Propiedad, Socio
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


class OperationSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)

        socios = scope_queryset_for_access(
            Socio.objects.order_by('nombre', 'id'),
            access,
            property_paths=(
                'propiedades_directas__id',
                'representaciones_comunidad__comunidad__propiedades__id',
                'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
                'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
            ),
        )
        empresas = scope_queryset_for_access(
            Empresa.objects.order_by('razon_social', 'id'),
            access,
            company_paths=('id',),
        )
        comunidades = scope_queryset_for_access(
            ComunidadPatrimonial.objects.order_by('nombre', 'id'),
            access,
            property_paths=('propiedades__id',),
        )
        propiedades = scope_queryset_for_access(
            Propiedad.objects.select_related('empresa_owner', 'comunidad_owner', 'socio_owner').order_by('codigo_propiedad', 'id'),
            access,
            property_paths=('id',),
        )
        cuentas = scope_queryset_for_access(
            CuentaRecaudadora.objects.select_related('empresa_owner', 'socio_owner').order_by('numero_cuenta', 'id'),
            access,
            bank_account_paths=('id',),
        )
        identidades = scope_queryset_for_access(
            IdentidadDeEnvio.objects.select_related('empresa_owner', 'socio_owner').order_by('remitente_visible', 'id'),
            access,
            company_paths=('empresa_owner_id',),
            property_paths=('asignaciones_operacion__mandato_operacion__propiedad_id',),
        )
        mandatos = scope_queryset_for_access(
            MandatoOperacion.objects.select_related(
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
            ).order_by('id'),
            access,
            property_paths=('propiedad_id',),
            bank_account_paths=('cuenta_recaudadora_id',),
        )

        return Response(
            {
                'socios': [
                    {
                        'id': socio.id,
                        'nombre': socio.nombre,
                        'rut': socio.rut,
                        'email': socio.email or '',
                        'telefono': socio.telefono or '',
                        'domicilio': socio.domicilio or '',
                        'activo': socio.activo,
                    }
                    for socio in socios
                ],
                'empresas': [
                    {
                        'id': empresa.id,
                        'razon_social': empresa.razon_social,
                        'rut': empresa.rut,
                        'estado': empresa.estado,
                        'participaciones_detail': [],
                    }
                    for empresa in empresas
                ],
                'comunidades': [
                    {
                        'id': comunidad.id,
                        'nombre': comunidad.nombre,
                        'estado': comunidad.estado,
                        'participaciones_detail': [],
                        'representacion_vigente': None,
                    }
                    for comunidad in comunidades
                ],
                'propiedades': [
                    {
                        'id': propiedad.id,
                        'rol_avaluo': propiedad.rol_avaluo,
                        'codigo_propiedad': propiedad.codigo_propiedad,
                        'direccion': propiedad.direccion,
                        'comuna': propiedad.comuna,
                        'region': propiedad.region,
                        'tipo_inmueble': propiedad.tipo_inmueble,
                        'owner_tipo': propiedad.owner_tipo,
                        'owner_id': propiedad.owner_id,
                        'owner_display': (
                            propiedad.empresa_owner.razon_social if propiedad.empresa_owner_id
                            else propiedad.comunidad_owner.nombre if propiedad.comunidad_owner_id
                            else propiedad.socio_owner.nombre
                        ),
                        'estado': propiedad.estado,
                    }
                    for propiedad in propiedades
                ],
                'cuentas': [
                    {
                        'id': cuenta.id,
                        'institucion': cuenta.institucion,
                        'numero_cuenta': cuenta.numero_cuenta,
                        'tipo_cuenta': cuenta.tipo_cuenta,
                        'titular_nombre': cuenta.titular_nombre,
                        'titular_rut': cuenta.titular_rut,
                        'moneda_operativa': cuenta.moneda_operativa,
                        'estado_operativo': cuenta.estado_operativo,
                        'owner_tipo': cuenta.owner_tipo,
                        'owner_id': cuenta.owner_id,
                        'owner_display': cuenta.owner_display,
                    }
                    for cuenta in cuentas
                ],
                'identidades': [
                    {
                        'id': identidad.id,
                        'canal': identidad.canal,
                        'remitente_visible': identidad.remitente_visible,
                        'direccion_o_numero': identidad.direccion_o_numero,
                        'owner_tipo': identidad.owner_tipo,
                        'owner_display': identidad.owner_display,
                        'estado': identidad.estado,
                    }
                    for identidad in identidades
                ],
                'mandatos': [
                    {
                        'id': mandato.id,
                        'propiedad_id': mandato.propiedad_id,
                        'propiedad_codigo': mandato.propiedad.codigo_propiedad,
                        'propietario_tipo': mandato.propietario_tipo,
                        'propietario_id': mandato.propietario_id,
                        'propietario_display': (
                            mandato.propietario_empresa_owner.razon_social if mandato.propietario_empresa_owner_id
                            else mandato.propietario_comunidad_owner.nombre if mandato.propietario_comunidad_owner_id
                            else mandato.propietario_socio_owner.nombre
                        ),
                        'administrador_operativo_tipo': mandato.administrador_operativo_tipo,
                        'administrador_operativo_id': mandato.administrador_operativo_id,
                        'administrador_operativo_display': (
                            mandato.administrador_empresa_owner.razon_social if mandato.administrador_empresa_owner_id
                            else mandato.administrador_socio_owner.nombre
                        ),
                        'recaudador_tipo': mandato.recaudador_tipo,
                        'recaudador_id': mandato.recaudador_id,
                        'recaudador_display': (
                            mandato.recaudador_empresa_owner.razon_social if mandato.recaudador_empresa_owner_id
                            else mandato.recaudador_socio_owner.nombre
                        ),
                        'entidad_facturadora_id': mandato.entidad_facturadora_id,
                        'entidad_facturadora_display': mandato.entidad_facturadora.razon_social if mandato.entidad_facturadora_id else None,
                        'cuenta_recaudadora_id': mandato.cuenta_recaudadora_id,
                        'cuenta_recaudadora_display': mandato.cuenta_recaudadora.numero_cuenta,
                        'tipo_relacion_operativa': mandato.tipo_relacion_operativa,
                        'autoriza_recaudacion': mandato.autoriza_recaudacion,
                        'autoriza_facturacion': mandato.autoriza_facturacion,
                        'autoriza_comunicacion': mandato.autoriza_comunicacion,
                        'vigencia_desde': mandato.vigencia_desde,
                        'vigencia_hasta': mandato.vigencia_hasta,
                        'estado': mandato.estado,
                    }
                    for mandato in mandatos
                ],
            }
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
