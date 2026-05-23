from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.reference_validation import redact_sensitive_payload, redact_sensitive_reference
from core.scope_access import scope_queryset_for_user
from cobranza.models import PagoMensual

from patrimonio.models import Empresa

from .models import (
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DTEEmitido,
    F22PreparacionAnual,
    F29PreparacionMensual,
    ProcesoRentaAnual,
    TipoDTE,
)


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


class RedactSensitiveSiiFieldsMixin:
    redacted_reference_fields = ()
    redacted_payload_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in self.redacted_reference_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_reference(data[field_name])
        for field_name in self.redacted_payload_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_payload(data[field_name])
        return data


class CapacidadTributariaSIISerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = (
        'certificado_ref',
        'evidencia_ref',
        'prueba_flujo_ref',
        'autorizacion_ambiente_ref',
        'regla_fiscal_ref',
    )
    redacted_payload_fields = ('ultimo_resultado',)

    class Meta:
        model = CapacidadTributariaSII
        fields = (
            'id',
            'empresa',
            'capacidad_key',
            'certificado_ref',
            'evidencia_ref',
            'prueba_flujo_ref',
            'autorizacion_ambiente_ref',
            'regla_fiscal_ref',
            'ambiente',
            'estado_gate',
            'ultimo_resultado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, CapacidadTributariaSII)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class DTEEmitidoSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('sii_track_id',)

    class Meta:
        model = DTEEmitido
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'contrato',
            'pago_mensual',
            'distribucion_cobro_mensual',
            'arrendatario',
            'tipo_dte',
            'monto_neto_clp',
            'fecha_emision',
            'estado_dte',
            'sii_track_id',
            'ultimo_estado_sii',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'contrato',
            'pago_mensual',
            'distribucion_cobro_mensual',
            'arrendatario',
            'monto_neto_clp',
            'fecha_emision',
            'created_at',
            'updated_at',
        )


class DTEGenerateSerializer(serializers.Serializer):
    pago_mensual_id = serializers.PrimaryKeyRelatedField(source='pago_mensual', queryset=PagoMensual.objects.all())
    tipo_dte = serializers.ChoiceField(
        choices=((TipoDTE.FACTURA_EXENTA, TipoDTE(TipoDTE.FACTURA_EXENTA).label),),
        required=False,
        default=TipoDTE.FACTURA_EXENTA,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['pago_mensual_id'].queryset = scope_queryset_for_user(
                PagoMensual.objects.all(),
                user,
                property_paths=('contrato__mandato_operacion__propiedad_id',),
            )


class DTEStatusSerializer(serializers.Serializer):
    estado_dte = serializers.ChoiceField(choices=DTEEmitido._meta.get_field('estado_dte').choices)
    sii_track_id = serializers.CharField(required=False, allow_blank=True)
    ultimo_estado_sii = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class F29PreparacionMensualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('borrador_ref',)
    redacted_payload_fields = ('resumen_formulario',)

    class Meta:
        model = F29PreparacionMensual
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'cierre_mensual',
            'anio',
            'mes',
            'estado_preparacion',
            'resumen_formulario',
            'borrador_ref',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class F29GenerateSerializer(serializers.Serializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', queryset=Empresa.objects.all())
    anio = serializers.IntegerField(min_value=2000, max_value=9999)
    mes = serializers.IntegerField(min_value=1, max_value=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa_id'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))


class F29StatusSerializer(serializers.Serializer):
    estado_preparacion = serializers.ChoiceField(choices=F29PreparacionMensual._meta.get_field('estado_preparacion').choices)
    borrador_ref = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class ProcesoRentaAnualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('paquete_ddjj_ref', 'borrador_f22_ref')
    redacted_payload_fields = ('resumen_anual',)

    class Meta:
        model = ProcesoRentaAnual
        fields = (
            'id',
            'empresa',
            'anio_tributario',
            'estado',
            'fecha_preparacion',
            'resumen_anual',
            'paquete_ddjj_ref',
            'borrador_f22_ref',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class DDJJPreparacionAnualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('paquete_ref',)
    redacted_payload_fields = ('resumen_paquete',)

    class Meta:
        model = DDJJPreparacionAnual
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'proceso_renta_anual',
            'anio_tributario',
            'estado_preparacion',
            'resumen_paquete',
            'paquete_ref',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class F22PreparacionAnualSerializer(RedactSensitiveSiiFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('borrador_ref',)
    redacted_payload_fields = ('resumen_f22',)

    class Meta:
        model = F22PreparacionAnual
        fields = (
            'id',
            'empresa',
            'capacidad_tributaria',
            'proceso_renta_anual',
            'anio_tributario',
            'estado_preparacion',
            'resumen_f22',
            'borrador_ref',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class AnnualGenerateSerializer(serializers.Serializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', queryset=Empresa.objects.all())
    anio_tributario = serializers.IntegerField(min_value=2000, max_value=9999)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa_id'].queryset = scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))


class AnnualStatusSerializer(serializers.Serializer):
    estado_preparacion = serializers.ChoiceField(choices=F22PreparacionAnual._meta.get_field('estado_preparacion').choices)
    ref_value = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
