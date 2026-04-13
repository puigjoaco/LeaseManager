from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import ControlModulePermission
from core.scope_access import (
    ScopedQuerysetMixin,
    get_scope_access,
    scope_queryset_for_access,
    scope_queryset_for_user,
)

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


class ControlSnapshotView(APIView):
    permission_classes = [ControlModulePermission]

    def get(self, request):
        context = {'request': request}
        access = get_scope_access(request.user)
        mode = request.query_params.get('mode', 'full')
        include_core = mode in {'full', 'core'}
        include_catalogs = mode in {'full', 'catalogs'}
        include_activity = mode in {'full', 'activity'}

        def scoped(queryset, *, company_paths: tuple[str, ...]):
            return scope_queryset_for_access(queryset, access, company_paths=company_paths)

        return Response(
            {
                'regimenes_tributarios': (
                    RegimenTributarioEmpresaSerializer(
                        RegimenTributarioEmpresa.objects.all(),
                        many=True,
                        context=context,
                    ).data
                    if include_core
                    else []
                ),
                'configuraciones_fiscales': (
                    ConfiguracionFiscalEmpresaSerializer(
                        scoped(
                            ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario'),
                            company_paths=('empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_core
                    else []
                ),
                'cuentas_contables': (
                    CuentaContableSerializer(
                        scoped(
                            CuentaContable.objects.select_related('empresa', 'padre'),
                            company_paths=('empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_catalogs
                    else []
                ),
                'reglas_contables': (
                    ReglaContableSerializer(
                        scoped(
                            ReglaContable.objects.select_related('empresa'),
                            company_paths=('empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_catalogs
                    else []
                ),
                'matrices_reglas': (
                    MatrizReglasContablesSerializer(
                        scoped(
                            MatrizReglasContables.objects.select_related('regla_contable', 'cuenta_debe', 'cuenta_haber'),
                            company_paths=('regla_contable__empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_catalogs
                    else []
                ),
                'eventos_contables': (
                    EventoContableSerializer(
                        scoped(
                            EventoContable.objects.select_related('empresa'),
                            company_paths=('empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_activity
                    else []
                ),
                'asientos_contables': (
                    AsientoContableSerializer(
                        scoped(
                            AsientoContable.objects.select_related('evento_contable').prefetch_related('movimientos'),
                            company_paths=('evento_contable__empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_activity
                    else []
                ),
                'obligaciones_mensuales': (
                    ObligacionTributariaMensualSerializer(
                        scoped(
                            ObligacionTributariaMensual.objects.select_related('empresa'),
                            company_paths=('empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_activity
                    else []
                ),
                'cierres_mensuales': (
                    CierreMensualContableSerializer(
                        scoped(
                            CierreMensualContable.objects.select_related('empresa'),
                            company_paths=('empresa_id',),
                        ),
                        many=True,
                        context=context,
                    ).data
                    if include_activity
                    else []
                ),
            }
        )


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


class CierreMensualPrepareView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = CierreMensualPrepareSerializer(data=request.data, context={'request': request})
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
        close = generics.get_object_or_404(
            scope_queryset_for_user(
                CierreMensualContable.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
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
        close = generics.get_object_or_404(
            scope_queryset_for_user(
                CierreMensualContable.objects.all(),
                request.user,
                company_paths=('empresa_id',),
            ),
            pk=pk,
        )
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
