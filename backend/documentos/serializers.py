from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import DocumentoEmitido, ExpedienteDocumental, EstadoDocumento, PoliticaFirmaYNotaria


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


class ExpedienteDocumentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpedienteDocumental
        fields = ('id', 'entidad_tipo', 'entidad_id', 'estado', 'owner_operativo', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class PoliticaFirmaYNotariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticaFirmaYNotaria
        fields = (
            'id',
            'tipo_documental',
            'requiere_firma_arrendador',
            'requiere_firma_arrendatario',
            'requiere_codeudor',
            'requiere_notaria',
            'modo_firma_permitido',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, PoliticaFirmaYNotaria)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class DocumentoEmitidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoEmitido
        fields = (
            'id',
            'expediente',
            'tipo_documental',
            'version_plantilla',
            'checksum',
            'fecha_carga',
            'usuario',
            'origen',
            'estado',
            'storage_ref',
            'firma_arrendador_registrada',
            'firma_arrendatario_registrada',
            'firma_codeudor_registrada',
            'recepcion_notarial_registrada',
            'comprobante_notarial',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'usuario', 'created_at', 'updated_at')

    def validate(self, attrs):
        if not self.instance and 'fecha_carga' not in attrs:
            attrs['fecha_carga'] = timezone.now()

        candidate = build_validation_candidate(self.instance, DocumentoEmitido)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        if self.instance:
            candidate.usuario = self.instance.usuario
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs

    def create(self, validated_data):
        validated_data['usuario'] = self.context['request'].user
        return super().create(validated_data)


class DocumentoFormalizarSerializer(serializers.Serializer):
    firma_arrendador_registrada = serializers.BooleanField(required=False)
    firma_arrendatario_registrada = serializers.BooleanField(required=False)
    firma_codeudor_registrada = serializers.BooleanField(required=False)
    recepcion_notarial_registrada = serializers.BooleanField(required=False)
    comprobante_notarial = serializers.PrimaryKeyRelatedField(
        queryset=DocumentoEmitido.objects.all(),
        required=False,
        allow_null=True,
    )

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.estado = EstadoDocumento.FORMALIZED
        instance.full_clean()
        instance.save()
        return instance

