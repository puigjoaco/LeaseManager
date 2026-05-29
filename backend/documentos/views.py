from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import AdminOnlyPermission, OperationalModulePermission
from core.reference_validation import redact_sensitive_reference

from .correction_audit import build_correction_audit_metadata
from .formalization_audit import FORMALIZATION_AUDIT_EVENT_TYPE, build_formalization_audit_metadata
from .scope import scope_documento_queryset, scope_expediente_queryset
from .models import DocumentoEmitido, ExpedienteDocumental, PlantillaDocumental, PoliticaFirmaYNotaria
from .pdf_generation import emit_generated_pdf_document, preview_generated_pdf_document
from .serializers import (
    DocumentoEmitidoSerializer,
    DocumentoFormalizarSerializer,
    DocumentoGenerarPDFSerializer,
    ExpedienteDocumentalSerializer,
    PlantillaDocumentalSerializer,
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
        if getattr(instance, 'documento_origen_id', None):
            self._create_audit_event(
                instance=instance,
                action='corrective_version_created',
                summary=f'Version correctiva de documento {instance.documento_origen_id}',
                metadata=build_correction_audit_metadata(instance),
            )
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

    def _create_audit_event(self, *, instance, action, summary='', metadata=None):
        create_audit_event(
            event_type=f'documentos.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            metadata=metadata,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class DocumentsSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        expedientes = scope_expediente_queryset(ExpedienteDocumental.objects.all().order_by('id'), request.user)
        politicas = PoliticaFirmaYNotaria.objects.all().order_by('tipo_documental', 'id')
        plantillas = PlantillaDocumental.objects.all().order_by('tipo_documental', 'version_plantilla', 'id')
        documentos = scope_documento_queryset(
            DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial', 'documento_origen').all().order_by('id'),
            request.user,
        )

        return Response(
            {
                'expedientes': [
                    {
                        'id': item.id,
                        'entidad_tipo': redact_sensitive_reference(item.entidad_tipo),
                        'entidad_id': redact_sensitive_reference(item.entidad_id),
                        'estado': item.estado,
                        'owner_operativo': redact_sensitive_reference(item.owner_operativo),
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
                        'requiere_nacionalidad_arrendatario': item.requiere_nacionalidad_arrendatario,
                        'requiere_estado_civil_arrendatario': item.requiere_estado_civil_arrendatario,
                        'requiere_profesion_arrendatario': item.requiere_profesion_arrendatario,
                        'requiere_notaria': item.requiere_notaria,
                        'modo_firma_permitido': item.modo_firma_permitido,
                        'estado': item.estado,
                    }
                    for item in politicas
                ],
                'plantillas_documentales': [
                    {
                        'id': item.id,
                        'tipo_documental': item.tipo_documental,
                        'version_plantilla': item.version_plantilla,
                        'plantilla_ref': redact_sensitive_reference(item.plantilla_ref),
                        'checksum_plantilla': item.checksum_plantilla,
                        'descripcion': item.descripcion,
                        'estado': item.estado,
                    }
                    for item in plantillas
                ],
                'documentos_emitidos': [
                    {
                        'id': item.id,
                        'expediente': item.expediente_id,
                        'tipo_documental': item.tipo_documental,
                        'version_plantilla': item.version_plantilla,
                        'checksum': item.checksum,
                        'fecha_carga': item.fecha_carga,
                        'usuario': item.usuario_id,
                        'origen': item.origen,
                        'estado': item.estado,
                        'storage_ref': redact_sensitive_reference(item.storage_ref),
                        'firma_arrendador_registrada': item.firma_arrendador_registrada,
                        'firma_arrendatario_registrada': item.firma_arrendatario_registrada,
                        'firma_codeudor_registrada': item.firma_codeudor_registrada,
                        'recepcion_notarial_registrada': item.recepcion_notarial_registrada,
                        'evidencia_formalizacion_ref': redact_sensitive_reference(item.evidencia_formalizacion_ref),
                        'comprobante_notarial': item.comprobante_notarial_id,
                        'documento_origen': item.documento_origen_id,
                        'correccion_ref': redact_sensitive_reference(item.correccion_ref),
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


class PlantillaDocumentalListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PlantillaDocumentalSerializer
    queryset = PlantillaDocumental.objects.all()
    audit_entity_type = 'plantilla_documental'
    audit_entity_label = 'plantilla documental'


class PlantillaDocumentalDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PlantillaDocumentalSerializer
    queryset = PlantillaDocumental.objects.all()
    audit_entity_type = 'plantilla_documental'
    audit_entity_label = 'plantilla documental'


class DocumentoEmitidoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DocumentoEmitidoSerializer
    queryset = DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial', 'documento_origen').all()
    audit_entity_type = 'documento_emitido'
    audit_entity_label = 'documento emitido'

    def get_queryset(self):
        return scope_documento_queryset(super().get_queryset(), self.request.user)


class DocumentoEmitidoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = DocumentoEmitidoSerializer
    queryset = DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial', 'documento_origen').all()
    audit_entity_type = 'documento_emitido'
    audit_entity_label = 'documento emitido'

    def get_queryset(self):
        return scope_documento_queryset(super().get_queryset(), self.request.user)


class DocumentoGenerarPDFView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = DocumentoGenerarPDFSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            document, pdf_bytes = emit_generated_pdf_document(
                expediente=serializer.validated_data['expediente'],
                tipo_documental=serializer.validated_data['tipo_documental'],
                version_plantilla=serializer.validated_data['version_plantilla'],
                titulo=serializer.validated_data['titulo'],
                lineas=serializer.validated_data['lineas'],
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except DjangoValidationError as error:
            return Response(serialize_validation_error(error), status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                'documento': DocumentoEmitidoSerializer(document, context={'request': request}).data,
                'pdf_sha256': document.checksum,
                'pdf_size_bytes': len(pdf_bytes),
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentoPrevisualizarPDFView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = DocumentoGenerarPDFSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        payload = preview_generated_pdf_document(
            expediente=serializer.validated_data['expediente'],
            tipo_documental=serializer.validated_data['tipo_documental'],
            version_plantilla=serializer.validated_data['version_plantilla'],
            titulo=serializer.validated_data['titulo'],
            lineas=serializer.validated_data['lineas'],
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(
            {
                'pdf_sha256': payload['checksum'],
                'pdf_size_bytes': len(payload['pdf_bytes']),
                'storage_ref_preview': payload['storage_ref'],
                'preview_ref': payload['checksum'],
            },
            status=status.HTTP_200_OK,
        )


class DocumentoFormalizarView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        document = generics.get_object_or_404(
            scope_documento_queryset(
                DocumentoEmitido.objects.select_related('expediente', 'usuario', 'comprobante_notarial', 'documento_origen'),
                request.user,
            ),
            pk=pk,
        )
        previous_state = document.estado
        serializer = DocumentoFormalizarSerializer(
            instance=document,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                document = serializer.save()
                create_audit_event(
                    event_type=FORMALIZATION_AUDIT_EVENT_TYPE,
                    entity_type='documento_emitido',
                    entity_id=str(document.pk),
                    summary='Documento formalizado',
                    actor_user=request.user,
                    metadata=build_formalization_audit_metadata(document),
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
        except DjangoValidationError as error:
            return Response(serialize_validation_error(error), status=status.HTTP_400_BAD_REQUEST)
        return Response(DocumentoEmitidoSerializer(document, context={'request': request}).data, status=status.HTTP_200_OK)
