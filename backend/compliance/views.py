from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import AdminOnlyPermission

from .models import ExportacionSensible, PoliticaRetencionDatos
from .serializers import (
    ExportacionPrepareSerializer,
    ExportacionSensibleSerializer,
    PoliticaRetencionDatosSerializer,
)
from .services import get_export_payload, prepare_sensitive_export, render_export_payload, revoke_export


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
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'compliance.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class PoliticaRetencionDatosListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PoliticaRetencionDatosSerializer
    queryset = PoliticaRetencionDatos.objects.all()
    audit_entity_type = 'politica_retencion'
    audit_entity_label = 'politica de retencion'


class PoliticaRetencionDatosDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PoliticaRetencionDatosSerializer
    queryset = PoliticaRetencionDatos.objects.all()
    audit_entity_type = 'politica_retencion'
    audit_entity_label = 'politica de retencion'


class ExportacionSensibleListView(generics.ListAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = ExportacionSensibleSerializer
    queryset = ExportacionSensible.objects.select_related('created_by').all()


class ExportacionSensibleDetailView(generics.RetrieveAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = ExportacionSensibleSerializer
    queryset = ExportacionSensible.objects.select_related('created_by').all()


class ExportacionPrepareView(APIView):
    permission_classes = [AdminOnlyPermission]

    def post(self, request):
        serializer = ExportacionPrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scope_resumen = {key: value for key, value in data.items() if key not in {'categoria_dato', 'export_kind', 'motivo', 'hold_activo'}}
        payload = render_export_payload(data['export_kind'], scope_resumen)
        export = prepare_sensitive_export(
            categoria_dato=data['categoria_dato'],
            export_kind=data['export_kind'],
            scope_resumen=scope_resumen,
            motivo=data['motivo'],
            payload=payload,
            created_by=request.user,
            hold_activo=data.get('hold_activo', False),
        )
        create_audit_event(
            event_type='compliance.exportacion_sensible.prepared',
            entity_type='exportacion_sensible',
            entity_id=str(export.pk),
            summary='Exportacion sensible preparada y cifrada',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'export_kind': export.export_kind, 'scope_resumen': export.scope_resumen},
        )
        return Response(ExportacionSensibleSerializer(export).data, status=status.HTTP_201_CREATED)


class ExportacionContentView(APIView):
    permission_classes = [AdminOnlyPermission]

    def get(self, request, pk):
        export = generics.get_object_or_404(ExportacionSensible, pk=pk)
        try:
            payload = get_export_payload(export)
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        create_audit_event(
            event_type='compliance.exportacion_sensible.accessed',
            entity_type='exportacion_sensible',
            entity_id=str(export.pk),
            summary='Contenido de exportacion sensible accedido',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(
            {
                'id': export.id,
                'export_kind': export.export_kind,
                'payload_hash': export.payload_hash,
                'payload': payload,
            },
            status=status.HTTP_200_OK,
        )


class ExportacionRevokeView(APIView):
    permission_classes = [AdminOnlyPermission]

    def post(self, request, pk):
        export = generics.get_object_or_404(ExportacionSensible, pk=pk)
        export = revoke_export(export)
        create_audit_event(
            event_type='compliance.exportacion_sensible.revoked',
            entity_type='exportacion_sensible',
            entity_id=str(export.pk),
            summary='Exportacion sensible revocada',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(ExportacionSensibleSerializer(export).data, status=status.HTTP_200_OK)
