from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.scope_access import scope_queryset_for_user
from contratos.models import Arrendatario, Contrato
from documentos.scope import scope_documento_queryset
from documentos.models import DocumentoEmitido
from operacion.models import IdentidadDeEnvio

from .models import CanalMensajeria, MensajeSaliente
from .services import resolve_document_contract


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


def _request_user(serializer):
    request = serializer.context.get('request')
    return getattr(request, 'user', None)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['identidad_envio'].queryset = scope_queryset_for_user(
            IdentidadDeEnvio.objects.all(),
            user,
            company_paths=('empresa_owner_id',),
            property_paths=('asignaciones_operacion__mandato_operacion__propiedad_id',),
        )
        self.fields['contrato'].queryset = scope_queryset_for_user(
            Contrato.objects.all(),
            user,
            property_paths=('mandato_operacion__propiedad_id',),
            bank_account_paths=('mandato_operacion__cuenta_recaudadora_id',),
        )
        self.fields['arrendatario'].queryset = scope_queryset_for_user(
            Arrendatario.objects.all(),
            user,
            property_paths=('contratos__mandato_operacion__propiedad_id',),
            bank_account_paths=('contratos__mandato_operacion__cuenta_recaudadora_id',),
        )
        self.fields['documento_emitido'].queryset = scope_documento_queryset(DocumentoEmitido.objects.all(), user)

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

        document_contract = resolve_document_contract(candidate.documento_emitido)
        if candidate.documento_emitido and candidate.documento_emitido.expediente.entidad_tipo == 'contrato' and document_contract is None:
            raise serializers.ValidationError(
                {'documento_emitido': 'El documento emitido no referencia un contrato valido.'}
            )
        if document_contract and candidate.contrato and document_contract.pk != candidate.contrato.pk:
            raise serializers.ValidationError(
                {'documento_emitido': 'El documento emitido debe pertenecer al mismo contrato informado.'}
            )
        if document_contract and candidate.arrendatario and document_contract.arrendatario_id != candidate.arrendatario.id:
            raise serializers.ValidationError(
                {'arrendatario': 'El arrendatario debe coincidir con el contrato del documento emitido.'}
            )
        if candidate.contrato and candidate.arrendatario and candidate.contrato.arrendatario_id != candidate.arrendatario.id:
            raise serializers.ValidationError(
                {'arrendatario': 'El arrendatario debe coincidir con el contrato informado.'}
            )
        return attrs


class MensajeRegistrarEnvioSerializer(serializers.Serializer):
    external_ref = serializers.CharField(required=False, allow_blank=True)
