from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from contratos.models import Contrato
from core.scope_access import scope_queryset_for_user
from operacion.models import MandatoOperacion

from .scope import scope_documento_queryset, scope_expediente_queryset
from .models import DocumentoEmitido, ExpedienteDocumental, EstadoDocumento, PoliticaFirmaYNotaria


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


class ExpedienteDocumentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpedienteDocumental
        fields = ('id', 'entidad_tipo', 'entidad_id', 'estado', 'owner_operativo', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        user = _request_user(self)
        entidad_tipo = attrs.get('entidad_tipo', getattr(self.instance, 'entidad_tipo', ''))
        entidad_id = attrs.get('entidad_id', getattr(self.instance, 'entidad_id', ''))
        owner_operativo = attrs.get('owner_operativo', getattr(self.instance, 'owner_operativo', ''))

        if user and getattr(user, 'is_authenticated', False):
            if entidad_tipo == 'contrato':
                try:
                    contract_id = int(str(entidad_id))
                except ValueError as error:
                    raise serializers.ValidationError({'entidad_id': 'El expediente contractual requiere un ID numérico de contrato.'}) from error
                if not Contrato.objects.filter(pk=contract_id).exists():
                    raise serializers.ValidationError({'entidad_id': 'El contrato indicado no existe.'})

                scoped_contracts = scope_queryset_for_user(
                    Contrato.objects.filter(pk=contract_id),
                    user,
                    property_paths=('mandato_operacion__propiedad_id',),
                )
                if not scoped_contracts.exists():
                    raise serializers.ValidationError({'entidad_id': 'El contrato indicado queda fuera del scope asignado.'})

            if owner_operativo.startswith('mandato:'):
                mandato_value = owner_operativo.split(':', 1)[1]
                try:
                    mandato_id = int(mandato_value)
                except ValueError as error:
                    raise serializers.ValidationError({'owner_operativo': 'El owner_operativo debe usar el formato mandato:<id>.'}) from error

                scoped_mandato = scope_queryset_for_user(
                    MandatoOperacion.objects.filter(pk=mandato_id),
                    user,
                    property_paths=('propiedad_id',),
                    bank_account_paths=('cuenta_recaudadora_id',),
                )
                if not scoped_mandato.exists():
                    raise serializers.ValidationError({'owner_operativo': 'El mandato indicado queda fuera del scope asignado.'})

        candidate = build_validation_candidate(self.instance, ExpedienteDocumental)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['expediente'].queryset = scope_expediente_queryset(ExpedienteDocumental.objects.all(), user)
            self.fields['comprobante_notarial'].queryset = scope_documento_queryset(DocumentoEmitido.objects.all(), user)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['comprobante_notarial'].queryset = scope_documento_queryset(DocumentoEmitido.objects.all(), user)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.estado = EstadoDocumento.FORMALIZED
        instance.full_clean()
        instance.save()
        return instance
