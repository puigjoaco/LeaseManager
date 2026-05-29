from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import AdminOnlyPermission, OperationalModulePermission
from core.reference_validation import redact_sensitive_reference
from core.scope_access import scope_queryset_for_user
from contratos.models import Arrendatario, Contrato
from documentos.scope import scope_documento_queryset
from documentos.models import DocumentoEmitido
from operacion.models import IdentidadDeEnvio

from .models import CanalMensajeria, ConfiguracionNotificacionContrato, MensajeSaliente, NotificacionCobranzaProgramada
from .redaction import redact_channel_gate_restrictions
from .scope import scope_mensaje_queryset, scope_notificacion_cobranza_queryset
from .serializers import (
    CanalMensajeriaSerializer,
    ConfiguracionNotificacionContratoSerializer,
    MensajePrepararSerializer,
    MensajeRegistrarEnvioSerializer,
    MensajeSalienteSerializer,
    NotificacionCobranzaProgramadaSerializer,
)
from .services import mark_message_as_sent, prepare_message


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
        if hasattr(instance, 'estado'):
            return instance.estado
        if hasattr(instance, 'activa'):
            return instance.activa
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'canales.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class ChannelsSnapshotView(APIView):
    permission_classes = [OperationalModulePermission]

    def get(self, request):
        identidades = scope_queryset_for_user(
            IdentidadDeEnvio.objects.all().order_by('remitente_visible', 'id'),
            request.user,
            company_paths=('empresa_owner_id',),
            property_paths=('asignaciones_operacion__mandato_operacion__propiedad_id',),
        )
        contratos = scope_queryset_for_user(
            Contrato.objects.only('id', 'codigo_contrato').order_by('codigo_contrato', 'id'),
            request.user,
            property_paths=('mandato_operacion__propiedad_id',),
            bank_account_paths=('mandato_operacion__cuenta_recaudadora_id',),
        )
        arrendatarios = scope_queryset_for_user(
            Arrendatario.objects.only('id', 'nombre_razon_social').order_by('nombre_razon_social', 'id'),
            request.user,
            property_paths=('contratos__mandato_operacion__propiedad_id',),
            bank_account_paths=('contratos__mandato_operacion__cuenta_recaudadora_id',),
        )
        documentos = scope_documento_queryset(DocumentoEmitido.objects.all().order_by('id'), request.user)

        return Response(
            {
                'gates': [
                    {
                        'id': item.id,
                        'canal': item.canal,
                        'provider_key': item.provider_key,
                        'estado_gate': item.estado_gate,
                        'restricciones_operativas': redact_channel_gate_restrictions(item.restricciones_operativas),
                        'evidencia_ref': redact_sensitive_reference(item.evidencia_ref),
                    }
                    for item in CanalMensajeria.objects.order_by('canal', 'provider_key', 'id')
                ],
                'mensajes': [
                    {
                        'id': item.id,
                        'canal': item.canal,
                        'contrato': item.contrato_id,
                        'documento_emitido': item.documento_emitido_id,
                        'destinatario': item.destinatario,
                        'asunto': item.asunto,
                        'cuerpo': item.cuerpo,
                        'estado': item.estado,
                        'motivo_bloqueo': redact_sensitive_reference(item.motivo_bloqueo),
                        'external_ref': redact_sensitive_reference(item.external_ref),
                    }
                    for item in scope_mensaje_queryset(MensajeSaliente.objects.all().order_by('-id'), request.user)
                ],
                'configuraciones_notificacion': [
                    {
                        'id': item.id,
                        'contrato': item.contrato_id,
                        'canal': item.canal,
                        'dias_notificacion': item.dias_notificacion,
                        'activa': item.activa,
                        'evidencia_configuracion_ref': redact_sensitive_reference(
                            item.evidencia_configuracion_ref
                        ),
                    }
                    for item in scope_queryset_for_user(
                        ConfiguracionNotificacionContrato.objects.select_related('contrato').order_by(
                            'contrato__codigo_contrato',
                            'canal',
                            'id',
                        ),
                        request.user,
                        property_paths=('contrato__mandato_operacion__propiedad_id',),
                        bank_account_paths=('contrato__mandato_operacion__cuenta_recaudadora_id',),
                    )
                ],
                'notificaciones_cobranza': [
                    {
                        'id': item.id,
                        'pago_mensual': item.pago_mensual_id,
                        'contrato': item.pago_mensual.contrato_id,
                        'configuracion': item.configuracion_id,
                        'canal': item.canal,
                        'dia_notificacion': item.dia_notificacion,
                        'fecha_programada': item.fecha_programada,
                        'estado': item.estado,
                        'mensaje_saliente': item.mensaje_saliente_id,
                        'motivo_estado': redact_sensitive_reference(item.motivo_estado),
                    }
                    for item in scope_notificacion_cobranza_queryset(
                        NotificacionCobranzaProgramada.objects.select_related(
                            'pago_mensual',
                            'pago_mensual__contrato',
                            'configuracion',
                        ).order_by('fecha_programada', 'id'),
                        request.user,
                    )
                ],
                'identidades': [
                    {
                        'id': item.id,
                        'canal': item.canal,
                        'remitente_visible': item.remitente_visible,
                        'direccion_o_numero': item.direccion_o_numero,
                    }
                    for item in identidades
                ],
                'contratos': [
                    {
                        'id': item.id,
                        'codigo_contrato': item.codigo_contrato,
                    }
                    for item in contratos
                ],
                'arrendatarios': [
                    {
                        'id': item.id,
                        'nombre_razon_social': item.nombre_razon_social,
                    }
                    for item in arrendatarios
                ],
                'documentos_emitidos': [
                    {
                        'id': item.id,
                        'tipo_documental': item.tipo_documental,
                        'storage_ref': redact_sensitive_reference(item.storage_ref),
                    }
                    for item in documentos
                ],
            }
        )


class CanalMensajeriaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = CanalMensajeriaSerializer
    queryset = CanalMensajeria.objects.all()
    audit_entity_type = 'canal_mensajeria'
    audit_entity_label = 'canal de mensajeria'


class CanalMensajeriaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = CanalMensajeriaSerializer
    queryset = CanalMensajeria.objects.all()
    audit_entity_type = 'canal_mensajeria'
    audit_entity_label = 'canal de mensajeria'


class ConfiguracionNotificacionContratoListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = ConfiguracionNotificacionContratoSerializer
    queryset = ConfiguracionNotificacionContrato.objects.select_related('contrato').all()
    audit_entity_type = 'configuracion_notificacion_contrato'
    audit_entity_label = 'configuracion de notificacion de contrato'

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'request': self.request}

    def get_queryset(self):
        return scope_queryset_for_user(
            super().get_queryset(),
            self.request.user,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
            bank_account_paths=('contrato__mandato_operacion__cuenta_recaudadora_id',),
        )


class ConfiguracionNotificacionContratoDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = ConfiguracionNotificacionContratoSerializer
    queryset = ConfiguracionNotificacionContrato.objects.select_related('contrato').all()
    audit_entity_type = 'configuracion_notificacion_contrato'
    audit_entity_label = 'configuracion de notificacion de contrato'

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'request': self.request}

    def get_queryset(self):
        return scope_queryset_for_user(
            super().get_queryset(),
            self.request.user,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
            bank_account_paths=('contrato__mandato_operacion__cuenta_recaudadora_id',),
        )


class MensajeSalienteListView(generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = MensajeSalienteSerializer
    queryset = MensajeSaliente.objects.select_related(
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'arrendatario',
        'documento_emitido',
        'usuario',
    ).all()

    def get_queryset(self):
        return scope_mensaje_queryset(super().get_queryset(), self.request.user)


class MensajeSalienteDetailView(generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = MensajeSalienteSerializer
    queryset = MensajeSaliente.objects.select_related(
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'arrendatario',
        'documento_emitido',
        'usuario',
    ).all()

    def get_queryset(self):
        return scope_mensaje_queryset(super().get_queryset(), self.request.user)


class NotificacionCobranzaProgramadaListView(generics.ListAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = NotificacionCobranzaProgramadaSerializer
    queryset = NotificacionCobranzaProgramada.objects.select_related(
        'pago_mensual',
        'pago_mensual__contrato',
        'configuracion',
        'mensaje_saliente',
    ).all()

    def get_queryset(self):
        return scope_notificacion_cobranza_queryset(super().get_queryset(), self.request.user)


class NotificacionCobranzaProgramadaDetailView(generics.RetrieveAPIView):
    permission_classes = [OperationalModulePermission]
    serializer_class = NotificacionCobranzaProgramadaSerializer
    queryset = NotificacionCobranzaProgramada.objects.select_related(
        'pago_mensual',
        'pago_mensual__contrato',
        'configuracion',
        'mensaje_saliente',
    ).all()

    def get_queryset(self):
        return scope_notificacion_cobranza_queryset(super().get_queryset(), self.request.user)


class MensajePrepararView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request):
        serializer = MensajePrepararSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        message = prepare_message(
            canal=data['canal'],
            canal_mensajeria=data['canal_mensajeria'],
            contrato=data.get('contrato'),
            arrendatario=data.get('arrendatario'),
            documento_emitido=data.get('documento_emitido'),
            explicit_identity=data.get('identidad_envio'),
            asunto=data.get('asunto', ''),
            cuerpo=data.get('cuerpo', ''),
            usuario=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return Response(
            MensajeSalienteSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class MensajeRegistrarEnvioView(APIView):
    permission_classes = [OperationalModulePermission]

    def post(self, request, pk):
        message = generics.get_object_or_404(
            scope_mensaje_queryset(MensajeSaliente.objects.all(), request.user),
            pk=pk,
        )
        serializer = MensajeRegistrarEnvioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = mark_message_as_sent(
                message,
                external_ref=serializer.validated_data.get('external_ref', ''),
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(MensajeSalienteSerializer(message).data, status=status.HTTP_200_OK)
