from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event

from .models import CanalMensajeria, MensajeSaliente
from .serializers import (
    CanalMensajeriaSerializer,
    MensajePrepararSerializer,
    MensajeRegistrarEnvioSerializer,
    MensajeSalienteSerializer,
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


class CanalMensajeriaListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CanalMensajeriaSerializer
    queryset = CanalMensajeria.objects.all()
    audit_entity_type = 'canal_mensajeria'
    audit_entity_label = 'canal de mensajeria'


class CanalMensajeriaDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CanalMensajeriaSerializer
    queryset = CanalMensajeria.objects.all()
    audit_entity_type = 'canal_mensajeria'
    audit_entity_label = 'canal de mensajeria'


class MensajeSalienteListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MensajeSalienteSerializer
    queryset = MensajeSaliente.objects.select_related(
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'arrendatario',
        'documento_emitido',
        'usuario',
    ).all()


class MensajeSalienteDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MensajeSalienteSerializer
    queryset = MensajeSaliente.objects.select_related(
        'canal_mensajeria',
        'identidad_envio',
        'contrato',
        'arrendatario',
        'documento_emitido',
        'usuario',
    ).all()


class MensajePrepararView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MensajePrepararSerializer(data=request.data)
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
        )

        create_audit_event(
            event_type='canales.mensaje_saliente.prepared',
            entity_type='mensaje_saliente',
            entity_id=str(message.pk),
            summary='Mensaje preparado o bloqueado segun gate/identidad',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'estado': message.estado, 'canal': message.canal},
        )
        return Response(
            MensajeSalienteSerializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class MensajeRegistrarEnvioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        message = generics.get_object_or_404(MensajeSaliente, pk=pk)
        serializer = MensajeRegistrarEnvioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            message = mark_message_as_sent(message, external_ref=serializer.validated_data.get('external_ref', ''))
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        create_audit_event(
            event_type='canales.mensaje_saliente.sent_manually',
            entity_type='mensaje_saliente',
            entity_id=str(message.pk),
            summary='Envio manual registrado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
            metadata={'external_ref': message.external_ref},
        )
        return Response(MensajeSalienteSerializer(message).data, status=status.HTTP_200_OK)

