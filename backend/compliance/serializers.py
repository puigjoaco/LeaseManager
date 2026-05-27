from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.reference_validation import (
    contains_sensitive_reference,
    redact_sensitive_payload,
    redact_sensitive_reference,
)

from .models import ExportacionSensible, PoliticaRetencionDatos
from .services import EXPORT_KIND_CATEGORY_MAP, validate_sensitive_export_controls


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


class PoliticaRetencionDatosSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticaRetencionDatos
        fields = (
            'id',
            'categoria_dato',
            'evento_inicio',
            'plazo_minimo_anos',
            'permite_borrado_logico',
            'permite_purga_fisica',
            'requiere_hold',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, PoliticaRetencionDatos)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class ExportacionSensibleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportacionSensible
        fields = (
            'id',
            'categoria_dato',
            'export_kind',
            'scope_resumen',
            'motivo',
            'payload_hash',
            'encrypted_ref',
            'expires_at',
            'hold_activo',
            'estado',
            'created_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['scope_resumen'] = redact_sensitive_payload(data.get('scope_resumen') or {})
        data['motivo'] = redact_sensitive_reference(data.get('motivo'))
        data['encrypted_ref'] = redact_sensitive_reference(data.get('encrypted_ref'))
        return data


class ExportacionPrepareSerializer(serializers.Serializer):
    categoria_dato = serializers.ChoiceField(choices=PoliticaRetencionDatos._meta.get_field('categoria_dato').choices)
    export_kind = serializers.ChoiceField(choices=tuple(EXPORT_KIND_CATEGORY_MAP.keys()))
    motivo = serializers.CharField()
    hold_activo = serializers.BooleanField(required=False, default=False)
    anio = serializers.IntegerField(required=False)
    mes = serializers.IntegerField(required=False)
    anio_tributario = serializers.IntegerField(required=False)
    empresa_id = serializers.IntegerField(required=False)
    socio_id = serializers.IntegerField(required=False)
    periodo = serializers.CharField(required=False)

    def validate(self, attrs):
        export_kind = attrs['export_kind']
        if export_kind == 'financiero_mensual' and not all(key in attrs for key in ('anio', 'mes')):
            raise serializers.ValidationError('financiero_mensual requiere anio y mes.')
        if export_kind == 'tributario_anual' and 'anio_tributario' not in attrs:
            raise serializers.ValidationError('tributario_anual requiere anio_tributario.')
        if export_kind == 'socio_resumen' and 'socio_id' not in attrs:
            raise serializers.ValidationError('socio_resumen requiere socio_id.')
        if export_kind == 'libros_periodo' and not all(key in attrs for key in ('empresa_id', 'periodo')):
            raise serializers.ValidationError('libros_periodo requiere empresa_id y periodo.')
        try:
            validate_sensitive_export_controls(categoria_dato=attrs['categoria_dato'], export_kind=export_kind)
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        scope_resumen = {
            key: value
            for key, value in attrs.items()
            if key not in {'categoria_dato', 'export_kind', 'motivo', 'hold_activo'}
        }
        errors = {}
        if contains_sensitive_reference(attrs.get('motivo'), include_sensitive_keys=True):
            errors['motivo'] = 'El motivo no puede contener URLs, correos, tokens, bearer, claves ni credenciales.'
        if contains_sensitive_reference(scope_resumen, include_sensitive_keys=True):
            errors['scope_resumen'] = 'El scope de exportacion no puede contener referencias sensibles.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
