from django.db import transaction
from django.core.cache import cache
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import ControlModulePermission
from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference
from core.scope_access import (
    ScopedQuerysetMixin,
    get_scope_access,
    scope_queryset_for_access,
    scope_queryset_for_user,
)
from patrimonio.models import Empresa

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    LineaLiquidacionMensual,
    LiquidacionMensual,
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
    CierreMensualReopenSerializer,
    ConfiguracionFiscalEmpresaSerializer,
    CuentaContableSerializer,
    EventoContableSerializer,
    LibroDiarioSerializer,
    LibroMayorSerializer,
    LineaLiquidacionMensualSerializer,
    LiquidacionMensualSerializer,
    MatrizReglasContablesSerializer,
    ObligacionTributariaMensualSerializer,
    PoliticaReversoContableSerializer,
    RegimenTributarioEmpresaSerializer,
    ReglaContableSerializer,
)
from .services import approve_monthly_close, post_accounting_event, prepare_monthly_close, reopen_monthly_close

CONTROL_SNAPSHOT_CACHE_TTL_SECONDS = 15


def build_control_snapshot_payload(access, *, mode='full', use_cache=True):
    include_core = mode in {'full', 'core', 'bootstrap'}
    include_catalogs = mode in {'full', 'catalogs', 'bootstrap'}
    include_activity = mode in {'full', 'activity'}

    cache_key = None
    if use_cache:
        cache_key = (
            'contabilidad:snapshot:'
            f'{mode}:restricted={int(access.restricted)}:'
            f'companies={",".join(map(str, sorted(access.company_ids)))}:'
            f'properties={",".join(map(str, sorted(access.property_ids)))}:'
            f'bank_accounts={",".join(map(str, sorted(access.bank_account_ids)))}'
        )
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    def scoped(queryset, *, company_paths: tuple[str, ...]):
        return scope_queryset_for_access(queryset, access, company_paths=company_paths)

    payload = {
        'regimenes_tributarios': (
            list(
                RegimenTributarioEmpresa.objects.values(
                    'id',
                    'codigo_regimen',
                    'descripcion',
                    'estado',
                )
            )
            if include_core
            else []
        ),
        'empresas': (
            [
                {
                    'id': empresa.id,
                    'razon_social': empresa.razon_social,
                    'rut': empresa.rut,
                    'estado': empresa.estado,
                    'participaciones_detail': [],
                }
                for empresa in scoped(
                    Empresa.objects.order_by('razon_social', 'id'),
                    company_paths=('id',),
                )
            ]
            if include_core
            else []
        ),
        'configuraciones_fiscales': (
            list(
                scoped(
                    ConfiguracionFiscalEmpresa.objects.all(),
                    company_paths=('empresa_id',),
                ).values(
                    'id',
                    'empresa',
                    'regimen_tributario',
                    'afecta_iva_arriendo',
                    'tasa_iva',
                    'tasa_ppm_vigente',
                    'aplica_ppm',
                    'ddjj_habilitadas',
                    'inicio_ejercicio',
                    'moneda_funcional',
                    'estado',
                )
            )
            if include_core
            else []
        ),
        'cuentas_contables': (
            list(
                scoped(
                    CuentaContable.objects.all(),
                    company_paths=('empresa_id',),
                ).values(
                    'id',
                    'empresa',
                    'plan_cuentas_version',
                    'codigo',
                    'nombre',
                    'naturaleza',
                    'padre',
                    'estado',
                )
            )
            if include_catalogs
            else []
        ),
        'reglas_contables': (
            list(
                scoped(
                    ReglaContable.objects.all(),
                    company_paths=('empresa_id',),
                ).values(
                    'id',
                    'empresa',
                    'evento_tipo',
                    'plan_cuentas_version',
                    'criterio_cargo',
                    'criterio_abono',
                    'estado',
                )
            )
            if include_catalogs
            else []
        ),
        'matrices_reglas': (
            list(
                scoped(
                    MatrizReglasContables.objects.all(),
                    company_paths=('regla_contable__empresa_id',),
                ).values(
                    'id',
                    'regla_contable',
                    'cuenta_debe',
                    'cuenta_haber',
                    'condicion_impuesto',
                    'estado',
                )
            )
            if include_catalogs
            else []
        ),
        'eventos_contables': (
            list(
                scoped(
                    EventoContable.objects.all(),
                    company_paths=('empresa_id',),
                ).values(
                    'id',
                    'empresa',
                    'evento_tipo',
                    'entidad_origen_tipo',
                    'entidad_origen_id',
                    'monto_base',
                    'estado_contable',
                )
            )
            if include_activity
            else []
        ),
        'asientos_contables': (
            [
                {
                    'id': asiento.id,
                    'evento_contable': asiento.evento_contable_id,
                    'periodo_contable': asiento.periodo_contable,
                    'estado': asiento.estado,
                    'debe_total': asiento.debe_total,
                    'haber_total': asiento.haber_total,
                    'movimientos': [],
                }
                for asiento in scoped(
                    AsientoContable.objects.all(),
                    company_paths=('evento_contable__empresa_id',),
                )
            ]
            if include_activity
            else []
        ),
        'obligaciones_mensuales': (
            list(
                scoped(
                    ObligacionTributariaMensual.objects.all(),
                    company_paths=('empresa_id',),
                ).values(
                    'id',
                    'empresa',
                    'anio',
                    'mes',
                    'obligacion_tipo',
                    'monto_calculado',
                    'estado_preparacion',
                )
            )
            if include_activity
            else []
        ),
        'cierres_mensuales': (
            list(
                scoped(
                    CierreMensualContable.objects.all(),
                    company_paths=('empresa_id',),
                ).values(
                    'id',
                    'empresa',
                    'anio',
                    'mes',
                    'estado',
                )
            )
            if include_activity
            else []
        ),
        'liquidaciones_mensuales': (
            [
                {
                    'id': liquidacion.id,
                    'owner_tipo': liquidacion.owner_tipo,
                    'empresa': liquidacion.empresa_id,
                    'comunidad': liquidacion.comunidad_id,
                    'socio': liquidacion.socio_id,
                    'cierre_contable': liquidacion.cierre_contable_id,
                    'anio': liquidacion.anio,
                    'mes': liquidacion.mes,
                    'estado': liquidacion.estado,
                    'comision_administracion_aplica': liquidacion.comision_administracion_aplica,
                    'saldo_final_clp': liquidacion.saldo_final_clp,
                    'saldo_final_explicacion': redact_sensitive_reference(liquidacion.saldo_final_explicacion),
                    'saldo_final_evidencia_ref': redact_sensitive_reference(liquidacion.saldo_final_evidencia_ref),
                    'evidencia_base_ref': redact_sensitive_reference(liquidacion.evidencia_base_ref),
                    'responsable_ref': redact_sensitive_reference(liquidacion.responsable_ref),
                }
                for liquidacion in scoped(
                    LiquidacionMensual.objects.select_related('empresa', 'cierre_contable'),
                    company_paths=('empresa_id', 'cierre_contable__empresa_id'),
                )
            ]
            if include_activity
            else []
        ),
        'lineas_liquidacion': (
            [
                {
                    'id': linea.id,
                    'liquidacion': linea.liquidacion_id,
                    'tipo_linea': linea.tipo_linea,
                    'descripcion': redact_sensitive_reference(linea.descripcion),
                    'monto_clp': linea.monto_clp,
                    'evidencia_ref': redact_sensitive_reference(linea.evidencia_ref),
                    'beneficiario_socio': linea.beneficiario_socio_id,
                    'evento_contable': linea.evento_contable_id,
                }
                for linea in scoped(
                    LineaLiquidacionMensual.objects.select_related('liquidacion', 'evento_contable'),
                    company_paths=('liquidacion__empresa_id', 'liquidacion__cierre_contable__empresa_id'),
                )
            ]
            if include_activity
            else []
        ),
    }

    if use_cache and cache_key:
        cache.set(cache_key, payload, CONTROL_SNAPSHOT_CACHE_TTL_SECONDS)
    return payload


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''
    audit_state_fields = ('estado', 'estado_contable')

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
            event_type=f'contabilidad.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            metadata=metadata,
        )


class RegimenTributarioEmpresaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = RegimenTributarioEmpresaSerializer
    queryset = RegimenTributarioEmpresa.objects.all()
    audit_entity_type = 'regimen_tributario'
    audit_entity_label = 'regimen tributario'


class ControlSnapshotView(APIView):
    permission_classes = [ControlModulePermission]

    def get(self, request):
        access = get_scope_access(request.user)
        mode = request.query_params.get('mode', 'full')
        use_cache = request.query_params.get('refresh') != '1'
        return Response(build_control_snapshot_payload(access, mode=mode, use_cache=use_cache))


class RegimenTributarioEmpresaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = RegimenTributarioEmpresaSerializer
    queryset = RegimenTributarioEmpresa.objects.all()
    audit_entity_type = 'regimen_tributario'
    audit_entity_label = 'regimen tributario'


class ConfiguracionFiscalEmpresaListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ConfiguracionFiscalEmpresaSerializer
    queryset = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'configuracion_fiscal'
    audit_entity_label = 'configuracion fiscal'


class ConfiguracionFiscalEmpresaDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ConfiguracionFiscalEmpresaSerializer
    queryset = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'configuracion_fiscal'
    audit_entity_label = 'configuracion fiscal'


class CuentaContableListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CuentaContableSerializer
    queryset = CuentaContable.objects.select_related('empresa', 'padre').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'cuenta_contable'
    audit_entity_label = 'cuenta contable'


class CuentaContableDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CuentaContableSerializer
    queryset = CuentaContable.objects.select_related('empresa', 'padre').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'cuenta_contable'
    audit_entity_label = 'cuenta contable'


class ReglaContableListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ReglaContableSerializer
    queryset = ReglaContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'regla_contable'
    audit_entity_label = 'regla contable'


class ReglaContableDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ReglaContableSerializer
    queryset = ReglaContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'regla_contable'
    audit_entity_label = 'regla contable'


class MatrizReglasContablesListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = MatrizReglasContablesSerializer
    queryset = MatrizReglasContables.objects.select_related('regla_contable', 'cuenta_debe', 'cuenta_haber').all()
    company_scope_paths = ('regla_contable__empresa_id',)
    audit_entity_type = 'matriz_reglas'
    audit_entity_label = 'matriz de reglas contables'


class MatrizReglasContablesDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = MatrizReglasContablesSerializer
    queryset = MatrizReglasContables.objects.select_related('regla_contable', 'cuenta_debe', 'cuenta_haber').all()
    company_scope_paths = ('regla_contable__empresa_id',)
    audit_entity_type = 'matriz_reglas'
    audit_entity_label = 'matriz de reglas contables'


class EventoContableListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = EventoContableSerializer
    queryset = EventoContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'evento_contable'
    audit_entity_label = 'evento contable'

    def perform_create(self, serializer):
        with transaction.atomic():
            event = serializer.save()
            self._create_audit_event(instance=event, action='created')
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
        return event


class EventoContableDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = EventoContableSerializer
    queryset = EventoContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class EventoContablePostView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        event = generics.get_object_or_404(
            scope_queryset_for_user(
                EventoContable.objects.select_related('empresa'),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        with transaction.atomic():
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
        event.refresh_from_db()
        return Response(EventoContableSerializer(event).data, status=status.HTTP_200_OK)


class AsientoContableListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AsientoContableSerializer
    queryset = AsientoContable.objects.select_related('evento_contable').prefetch_related('movimientos').all()
    company_scope_paths = ('evento_contable__empresa_id',)


class AsientoContableDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = AsientoContableSerializer
    queryset = AsientoContable.objects.select_related('evento_contable').prefetch_related('movimientos').all()
    company_scope_paths = ('evento_contable__empresa_id',)


class PoliticaReversoContableListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = PoliticaReversoContableSerializer
    queryset = PoliticaReversoContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'politica_reverso'
    audit_entity_label = 'politica reverso contable'


class PoliticaReversoContableDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = PoliticaReversoContableSerializer
    queryset = PoliticaReversoContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)
    audit_entity_type = 'politica_reverso'
    audit_entity_label = 'politica reverso contable'


class ObligacionTributariaMensualListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ObligacionTributariaMensualSerializer
    queryset = ObligacionTributariaMensual.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class LibroDiarioListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = LibroDiarioSerializer
    queryset = LibroDiario.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class LibroMayorListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = LibroMayorSerializer
    queryset = LibroMayor.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class BalanceComprobacionListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = BalanceComprobacionSerializer
    queryset = BalanceComprobacion.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class CierreMensualContableListView(ScopedQuerysetMixin, generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CierreMensualContableSerializer
    queryset = CierreMensualContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class CierreMensualContableDetailView(ScopedQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CierreMensualContableSerializer
    queryset = CierreMensualContable.objects.select_related('empresa').all()
    company_scope_paths = ('empresa_id',)


class LiquidacionMensualListCreateView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = LiquidacionMensualSerializer
    queryset = LiquidacionMensual.objects.select_related(
        'empresa',
        'comunidad',
        'socio',
        'cierre_contable',
    ).prefetch_related('lineas')
    company_scope_paths = ('empresa_id', 'cierre_contable__empresa_id')
    audit_entity_type = 'liquidacion_mensual'
    audit_entity_label = 'liquidacion mensual'


class LiquidacionMensualDetailView(ScopedQuerysetMixin, AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = LiquidacionMensualSerializer
    queryset = LiquidacionMensual.objects.select_related(
        'empresa',
        'comunidad',
        'socio',
        'cierre_contable',
    ).prefetch_related('lineas')
    company_scope_paths = ('empresa_id', 'cierre_contable__empresa_id')
    audit_entity_type = 'liquidacion_mensual'
    audit_entity_label = 'liquidacion mensual'


class LineaLiquidacionMensualListCreateView(
    ScopedQuerysetMixin,
    AuditCreateUpdateMixin,
    generics.ListCreateAPIView,
):
    permission_classes = [ControlModulePermission]
    serializer_class = LineaLiquidacionMensualSerializer
    queryset = LineaLiquidacionMensual.objects.select_related(
        'liquidacion',
        'beneficiario_socio',
        'evento_contable',
    )
    company_scope_paths = ('liquidacion__empresa_id', 'liquidacion__cierre_contable__empresa_id')
    audit_entity_type = 'linea_liquidacion_mensual'
    audit_entity_label = 'linea de liquidacion mensual'


class LineaLiquidacionMensualDetailView(
    ScopedQuerysetMixin,
    AuditCreateUpdateMixin,
    generics.RetrieveUpdateAPIView,
):
    permission_classes = [ControlModulePermission]
    serializer_class = LineaLiquidacionMensualSerializer
    queryset = LineaLiquidacionMensual.objects.select_related(
        'liquidacion',
        'beneficiario_socio',
        'evento_contable',
    )
    company_scope_paths = ('liquidacion__empresa_id', 'liquidacion__cierre_contable__empresa_id')
    audit_entity_type = 'linea_liquidacion_mensual'
    audit_entity_label = 'linea de liquidacion mensual'


class CierreMensualPrepareView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = CierreMensualPrepareSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                close = prepare_monthly_close(
                    serializer.validated_data['empresa'],
                    serializer.validated_data['anio'],
                    serializer.validated_data['mes'],
                )
                create_audit_event(
                    event_type='contabilidad.cierre_mensual.prepared',
                    entity_type='cierre_mensual_contable',
                    entity_id=str(close.pk),
                    summary='Cierre mensual preparado',
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        close.refresh_from_db()
        return Response(CierreMensualContableSerializer(close).data, status=status.HTTP_200_OK)


class CierreMensualApproveView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        close = generics.get_object_or_404(
            scope_queryset_for_user(
                CierreMensualContable.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        previous_state = close.estado
        try:
            with transaction.atomic():
                close = approve_monthly_close(close)
                approval_context = (close.resumen_obligaciones or {}).get('liquidacion_mensual', {})
                transition_metadata = {
                    'campo_estado': 'estado',
                    'estado_anterior': previous_state,
                    'estado_nuevo': close.estado,
                    'liquidacion_mensual': redact_sensitive_payload(approval_context),
                }
                create_audit_event(
                    event_type='contabilidad.cierre_mensual.approved',
                    entity_type='cierre_mensual_contable',
                    entity_id=str(close.pk),
                    summary='Cierre mensual aprobado',
                    metadata=transition_metadata,
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
                create_audit_event(
                    event_type='contabilidad.cierre_mensual.state_changed',
                    entity_type='cierre_mensual_contable',
                    entity_id=str(close.pk),
                    summary='Cambio de estado de cierre mensual',
                    metadata=transition_metadata,
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        close.refresh_from_db()
        return Response(CierreMensualContableSerializer(close).data, status=status.HTTP_200_OK)


class CierreMensualReopenView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        serializer = CierreMensualReopenSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        close = generics.get_object_or_404(
            scope_queryset_for_user(
                CierreMensualContable.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
        try:
            with transaction.atomic():
                close, effect = reopen_monthly_close(close, **serializer.validated_data)
                create_audit_event(
                    event_type='contabilidad.cierre_mensual.reopened',
                    entity_type='cierre_mensual_contable',
                    entity_id=str(close.pk),
                    summary='Cierre mensual reabierto',
                    metadata={'efecto_reapertura_id': effect.pk, 'evento_contable_id': effect.evento_contable_id},
                    actor_user=request.user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        close.refresh_from_db()
        return Response(CierreMensualContableSerializer(close).data, status=status.HTTP_200_OK)
