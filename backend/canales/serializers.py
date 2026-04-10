from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from contratos.models import Arrendatario, Contrato
from documentos.models import DocumentoEmitido
from operacion.models import IdentidadDeEnvio

from .models import CanalMensajeria, MensajeSaliente


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


class CanalMensajeriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CanalMensajeria
        fields = (
            'id',
            'canal',
            'provider_key',
            'estado_gate',
            'restricciones_operativas',
            'evidencia_ref',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class MensajeSalienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensajeSaliente
        fields = (
            'id',
            'canal',
            'canal_mensajeria',
            'identidad_envio',
            'contrato',
            'arrendatario',
            'documento_emitido',
            'destinatario',
            'asunto',
            'cuerpo',
            'estado',
            'motivo_bloqueo',
            'external_ref',
            'usuario',
            'provider_payload',
            'enviado_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'estado',
            'motivo_bloqueo',
            'external_ref',
            'usuario',
            'provider_payload',
            'enviado_at',
            'created_at',
            'updated_at',
        )


class MensajePrepararSerializer(serializers.Serializer):
    canal = serializers.ChoiceField(choices=CanalMensajeria._meta.get_field('canal').choices)
    canal_mensajeria = serializers.PrimaryKeyRelatedField(queryset=CanalMensajeria.objects.all())
    identidad_envio = serializers.PrimaryKeyRelatedField(queryset=IdentidadDeEnvio.objects.all(), required=False, allow_null=True)
    contrato = serializers.PrimaryKeyRelatedField(queryset=Contrato.objects.all(), required=False, allow_null=True)
    arrendatario = serializers.PrimaryKeyRelatedField(queryset=Arrendatario.objects.all(), required=False, allow_null=True)
    documento_emitido = serializers.PrimaryKeyRelatedField(queryset=DocumentoEmitido.objects.all(), required=False, allow_null=True)
    asunto = serializers.CharField(required=False, allow_blank=True)
    cuerpo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        candidate = build_validation_candidate(None, MensajeSaliente)
        candidate.canal = attrs['canal']
        candidate.canal_mensajeria = attrs['canal_mensajeria']
        candidate.identidad_envio = attrs.get('identidad_envio')
        candidate.contrato = attrs.get('contrato')
        candidate.arrendatario = attrs.get('arrendatario')
        candidate.documento_emitido = attrs.get('documento_emitido')
        candidate.destinatario = ''
        candidate.asunto = attrs.get('asunto', '')
        candidate.cuerpo = attrs.get('cuerpo', '')
        try:
            candidate.full_clean(exclude=['destinatario', 'estado', 'motivo_bloqueo', 'external_ref', 'usuario', 'provider_payload', 'enviado_at'])
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class MensajeRegistrarEnvioSerializer(serializers.Serializer):
    external_ref = serializers.CharField(required=False, allow_blank=True)

