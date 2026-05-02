from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import AdminOnlyPermission, OperationalModulePermission

from .scope import scope_documento_queryset, scope_expediente_queryset
from .models import DocumentoEmitido, ExpedienteDocumental, PoliticaFirmaYNotaria
from .serializers import (
    DocumentoEmitidoSerializer,
    DocumentoFormalizarSerializer,
    ExpedienteDocumentalSerializer,
    PoliticaFirmaYNotariaSerializer,
)


def serialize_validation_error(error):
    if hasattr(error, 'message_dict'):
        return error.message_dict
    return {'detail': error.messages}


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
        if hasattr(instance, 'estado'):
            return instance.estado
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'documentos.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class DocumentsSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        expedientes = scope_expediente_queryset(ExpedienteDocumental.objects.all().order_by('id'), request.user)
        politicas = PoliticaFirmaYNotaria.objects.all().order_by('tipo_documental', 'id')
        documentos = scope_documento_queryset(
            DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial').all().order_by('id'),
            request.user,
        )

        return Response(
            {
                'expedientes': [
                    {
                        'id': item.id,
                        'entidad_tipo': item.entidad_tipo,
                        'entidad_id': item.entidad_id,
                        'estado': item.estado,
                        'owner_operativo': item.owner_operativo,
                    }
                    for item in expedientes
                ],
                'politicas_firma': [
                    {
                        'id': item.id,
                        'tipo_documental': item.tipo_documental,
                        'requiere_firma_arrendador': item.requiere_firma_arrendador,
                        'requiere_firma_arrendatario': item.requiere_firma_arrendatario,
                        'requiere_codeudor': item.requiere_codeudor,
                        'requiere_notaria': item.requiere_notaria,
                        'modo_firma_permitido': item.modo_firma_permitido,
                        'estado': item.estado,
                    }
                    for item in politicas
                ],
                'documentos_emitidos': [
                    {
                        'id': item.id,
                        'expediente': item.expediente_id,
                        'tipo_documental': item.tipo_documental,
                        'version_plantilla': item.version_plantilla,
                        'origen': item.origen,
                        'estado': item.estado,
                        'storage_ref': item.storage_ref,
                    }
                    for item in documentos
                ],
            }
        )


class ExpedienteDocumentalListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ExpedienteDocumentalSerializer
    queryset = ExpedienteDocumental.objects.all()
    audit_entity_type = 'expediente'
    audit_entity_label = 'expediente documental'

    def get_queryset(self):
        return scope_expediente_queryset(super().get_queryset(), self.request.user)


class ExpedienteDocumentalDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = ExpedienteDocumentalSerializer
    queryset = ExpedienteDocumental.objects.all()
    audit_entity_type = 'expediente'
    audit_entity_label = 'expediente documental'

    def get_queryset(self):
        return scope_expediente_queryset(super().get_queryset(), self.request.user)


class PoliticaFirmaYNotariaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PoliticaFirmaYNotariaSerializer
    queryset = PoliticaFirmaYNotaria.objects.all()
    audit_entity_type = 'politica_firma'
    audit_entity_label = 'politica de firma'


class PoliticaFirmaYNotariaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PoliticaFirmaYNotariaSerializer
    queryset = PoliticaFirmaYNotaria.objects.all()
    audit_entity_type = 'politica_firma'
    audit_entity_label = 'politica de firma'


class DocumentoEmitidoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DocumentoEmitidoSerializer
    queryset = DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial').all()
    audit_entity_type = 'documento_emitido'
    audit_entity_label = 'documento emitido'

    def get_queryset(self):
        return scope_documento_queryset(super().get_queryset(), self.request.user)


class DocumentoEmitidoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DocumentoEmitidoSerializer
    queryset = DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial').all()
    audit_entity_type = 'documento_emitido'
    audit_entity_label = 'documento emitido'

    def get_queryset(self):
        return scope_documento_queryset(super().get_queryset(), self.request.user)


class DocumentoFormalizarView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        document = generics.get_object_or_404(
            scope_documento_queryset(
                DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial'),
                request.user,
            ),
            pk=pk,
        )
        previous_state = document.estado
        serializer = DocumentoFormalizarSerializer(instance=document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                document = serializer.save()
        except DjangoValidationError as error:
            return Response(serialize_validation_error(error), status=status.HTTP_400_BAD_REQUEST)
        create_audit_event(
            event_type='documentos.documento_emitido.formalized',
            entity_type='documento_emitido',
            entity_id=str(document.pk),
            summary='Documento formalizado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        if previous_state != document.estado:
            create_audit_event(
                event_type='documentos.documento_emitido.state_changed',
                entity_type='documento_emitido',
                entity_id=str(document.pk),
                summary='Cambio de estado documental',
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        return Response(DocumentoEmitidoSerializer(document, context={'request': request}).data, status=status.HTTP_200_OK)
