from rest_framework import serializers

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


class CapacidadTributariaSIISerializer(serializers.ModelSerializer):
    class Meta:
        model = CapacidadTributariaSII
        fields = (
            'id',
            'empresa',
            'capacidad_key',
            'certificado_ref',
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


class DTEEmitidoSerializer(serializers.ModelSerializer):
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


class F29PreparacionMensualSerializer(serializers.ModelSerializer):
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


class ProcesoRentaAnualSerializer(serializers.ModelSerializer):
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


class DDJJPreparacionAnualSerializer(serializers.ModelSerializer):
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


class F22PreparacionAnualSerializer(serializers.ModelSerializer):
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
