from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import ControlModulePermission

from .models import CapacidadTributariaSII, DTEEmitido, F29PreparacionMensual
from .serializers import (
    AnnualGenerateSerializer,
    AnnualStatusSerializer,
    CapacidadTributariaSIISerializer,
    DDJJPreparacionAnualSerializer,
    DTEEmitidoSerializer,
    DTEGenerateSerializer,
    DTEStatusSerializer,
    F22PreparacionAnualSerializer,
    F29GenerateSerializer,
    F29PreparacionMensualSerializer,
    F29StatusSerializer,
    ProcesoRentaAnualSerializer,
)
from .services import (
    generate_annual_preparation,
    generate_dte_draft,
    generate_f29_draft,
    register_annual_status,
    register_dte_status,
    register_f29_status,
)
from .models import DDJJPreparacionAnual, F22PreparacionAnual, ProcesoRentaAnual


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
        if hasattr(instance, 'estado_gate'):
            return instance.estado_gate
        if hasattr(instance, 'estado_dte'):
            return instance.estado_dte
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'sii.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class CapacidadTributariaSIIListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CapacidadTributariaSIISerializer
    queryset = CapacidadTributariaSII.objects.select_related('empresa').all()
    audit_entity_type = 'capacidad_sii'
    audit_entity_label = 'capacidad SII'


class CapacidadTributariaSIIDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = CapacidadTributariaSIISerializer
    queryset = CapacidadTributariaSII.objects.select_related('empresa').all()
    audit_entity_type = 'capacidad_sii'
    audit_entity_label = 'capacidad SII'


class DTEEmitidoListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = DTEEmitidoSerializer
    queryset = DTEEmitido.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'contrato',
        'pago_mensual',
        'distribucion_cobro_mensual',
        'arrendatario',
    ).all()


class DTEEmitidoDetailView(generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = DTEEmitidoSerializer
    queryset = DTEEmitido.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'contrato',
        'pago_mensual',
        'distribucion_cobro_mensual',
        'arrendatario',
    ).all()


class DTEGenerateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = DTEGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            dte, created = generate_dte_draft(
                serializer.validated_data['pago_mensual'],
                tipo_dte=serializer.validated_data['tipo_dte'],
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        create_audit_event(
            event_type='sii.dte_emitido.draft_generated',
            entity_type='dte_emitido',
            entity_id=str(dte.pk),
            summary='Borrador DTE generado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'created': created},
        )
        return Response(DTEEmitidoSerializer(dte).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class DTEStatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        dte = generics.get_object_or_404(DTEEmitido, pk=pk)
        serializer = DTEStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dte = register_dte_status(dte, **serializer.validated_data)
        create_audit_event(
            event_type='sii.dte_emitido.status_updated',
            entity_type='dte_emitido',
            entity_id=str(dte.pk),
            summary='Estado DTE actualizado manualmente',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'estado_dte': dte.estado_dte, 'sii_track_id': dte.sii_track_id},
        )
        return Response(DTEEmitidoSerializer(dte).data, status=status.HTTP_200_OK)


class F29PreparacionListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = F29PreparacionMensualSerializer
    queryset = F29PreparacionMensual.objects.select_related('empresa', 'capacidad_tributaria', 'cierre_mensual').all()


class F29PreparacionDetailView(generics.RetrieveAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = F29PreparacionMensualSerializer
    queryset = F29PreparacionMensual.objects.select_related('empresa', 'capacidad_tributaria', 'cierre_mensual').all()


class F29GenerateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = F29GenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            draft, created = generate_f29_draft(
                serializer.validated_data['empresa'],
                serializer.validated_data['anio'],
                serializer.validated_data['mes'],
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        create_audit_event(
            event_type='sii.f29_preparacion.generated',
            entity_type='f29_preparacion',
            entity_id=str(draft.pk),
            summary='Borrador F29 generado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'created': created},
        )
        return Response(
            F29PreparacionMensualSerializer(draft).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class F29StatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        draft = generics.get_object_or_404(F29PreparacionMensual, pk=pk)
        serializer = F29StatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        draft = register_f29_status(draft, **serializer.validated_data)
        create_audit_event(
            event_type='sii.f29_preparacion.status_updated',
            entity_type='f29_preparacion',
            entity_id=str(draft.pk),
            summary='Estado de F29 actualizado manualmente',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'estado_preparacion': draft.estado_preparacion},
        )
        return Response(F29PreparacionMensualSerializer(draft).data, status=status.HTTP_200_OK)


class ProcesoRentaAnualListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = ProcesoRentaAnualSerializer
    queryset = ProcesoRentaAnual.objects.select_related('empresa').all()


class DDJJPreparacionAnualListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = DDJJPreparacionAnualSerializer
    queryset = DDJJPreparacionAnual.objects.select_related('empresa', 'capacidad_tributaria', 'proceso_renta_anual').all()


class F22PreparacionAnualListView(generics.ListAPIView):
    permission_classes = [ControlModulePermission]
    serializer_class = F22PreparacionAnualSerializer
    queryset = F22PreparacionAnual.objects.select_related('empresa', 'capacidad_tributaria', 'proceso_renta_anual').all()


class AnnualGenerateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request):
        serializer = AnnualGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            process, ddjj, f22 = generate_annual_preparation(
                serializer.validated_data['empresa'],
                serializer.validated_data['anio_tributario'],
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        create_audit_event(
            event_type='sii.preparacion_anual.generated',
            entity_type='proceso_renta_anual',
            entity_id=str(process.pk),
            summary='Proceso anual preparado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'ddjj_id': ddjj.pk, 'f22_id': f22.pk},
        )
        return Response(
            {
                'proceso_renta_anual': ProcesoRentaAnualSerializer(process).data,
                'ddjj_preparacion': DDJJPreparacionAnualSerializer(ddjj).data,
                'f22_preparacion': F22PreparacionAnualSerializer(f22).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DDJJStatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        document = generics.get_object_or_404(DDJJPreparacionAnual, pk=pk)
        serializer = AnnualStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = register_annual_status(document, **serializer.validated_data)
        create_audit_event(
            event_type='sii.ddjj_preparacion.status_updated',
            entity_type='ddjj_preparacion',
            entity_id=str(document.pk),
            summary='Estado de DDJJ actualizado manualmente',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'estado_preparacion': document.estado_preparacion},
        )
        return Response(DDJJPreparacionAnualSerializer(document).data, status=status.HTTP_200_OK)


class F22StatusUpdateView(APIView):
    permission_classes = [ControlModulePermission]

    def post(self, request, pk):
        document = generics.get_object_or_404(F22PreparacionAnual, pk=pk)
        serializer = AnnualStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = register_annual_status(document, **serializer.validated_data)
        create_audit_event(
            event_type='sii.f22_preparacion.status_updated',
            entity_type='f22_preparacion',
            entity_id=str(document.pk),
            summary='Estado de F22 actualizado manualmente',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'estado_preparacion': document.estado_preparacion},
        )
        return Response(F22PreparacionAnualSerializer(document).data, status=status.HTTP_200_OK)
