from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from core.scope_access import scope_queryset_for_user
from contratos.models import Contrato

from .models import (
    AjusteContrato,
    CodigoCobroResidual,
    DistribucionCobroMensual,
    EstadoCuentaArrendatario,
    EstadoPago,
    GarantiaContractual,
    HistorialGarantia,
    PagoMensual,
    RepactacionDeuda,
    ValorUFDiario,
)
from .services import (
    PAYMENT_STATE_TRANSITIONS,
    apply_guarantee_movement,
    generate_residual_reference,
    calculate_monthly_amount,
    sync_payment_state,
)


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


def _scoped_contrato_queryset(user):
    return scope_queryset_for_user(Contrato.objects.all(), user, property_paths=('mandato_operacion__propiedad_id',))


def _scoped_arrendatario_queryset(user):
    return scope_queryset_for_user(
        EstadoCuentaArrendatario._meta.get_field('arrendatario').remote_field.model.objects.all(),
        user,
        property_paths=('contratos__mandato_operacion__propiedad_id',),
    )


def _scoped_historial_queryset(user):
    return scope_queryset_for_user(
        HistorialGarantia.objects.all(),
        user,
        property_paths=('garantia_contractual__contrato__mandato_operacion__propiedad_id',),
    )


class ValorUFDiarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValorUFDiario
        fields = ('id', 'fecha', 'valor', 'source_key', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class AjusteContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AjusteContrato
        fields = (
            'id',
            'contrato',
            'tipo_ajuste',
            'monto',
            'moneda',
            'mes_inicio',
            'mes_fin',
            'justificacion',
            'activo',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['contrato'].queryset = _scoped_contrato_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, AjusteContrato)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class PagoMensualSerializer(serializers.ModelSerializer):
    distribuciones_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PagoMensual
        fields = (
            'id',
            'contrato',
            'periodo_contractual',
            'mes',
            'anio',
            'monto_facturable_clp',
            'monto_calculado_clp',
            'monto_pagado_clp',
            'fecha_vencimiento',
            'fecha_deposito_banco',
            'fecha_deteccion_sistema',
            'estado_pago',
            'dias_mora',
            'codigo_conciliacion_efectivo',
            'distribuciones_detail',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'contrato',
            'periodo_contractual',
            'mes',
            'anio',
            'monto_facturable_clp',
            'monto_calculado_clp',
            'fecha_vencimiento',
            'dias_mora',
            'codigo_conciliacion_efectivo',
            'created_at',
            'updated_at',
        )

    def validate(self, attrs):
        if not self.instance:
            return attrs

        next_state = attrs.get('estado_pago', self.instance.estado_pago)
        previous_state = self.instance.estado_pago
        if next_state != previous_state and next_state not in PAYMENT_STATE_TRANSITIONS.get(previous_state, set()):
            raise serializers.ValidationError(
                {'estado_pago': f'Transicion invalida desde {previous_state} hacia {next_state}.'}
            )

        if next_state in {
            EstadoPago.PAID,
            EstadoPago.PAID_VIA_REPAYMENT,
            EstadoPago.PAID_BY_TERMINATION,
        }:
            monto_pagado = attrs.get('monto_pagado_clp', self.instance.monto_pagado_clp)
            if monto_pagado <= 0:
                raise serializers.ValidationError(
                    {'monto_pagado_clp': 'Los estados de pago efectivo requieren un monto_pagado_clp mayor que cero.'}
                )
            if not attrs.get('fecha_deposito_banco', self.instance.fecha_deposito_banco) and not attrs.get(
                'fecha_deteccion_sistema',
                self.instance.fecha_deteccion_sistema,
            ):
                raise serializers.ValidationError(
                    {'fecha_deposito_banco': 'Debe registrar fecha de deposito o deteccion para cerrar un pago.'}
                )

        candidate = build_validation_candidate(self.instance, PagoMensual)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        sync_payment_state(candidate)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        attrs['dias_mora'] = candidate.dias_mora
        return attrs

    def get_distribuciones_detail(self, obj):
        return DistribucionCobroMensualSerializer(
            obj.distribuciones_cobro.all(),
            many=True,
        ).data


class PagoMensualGenerateSerializer(serializers.Serializer):
    contrato_id = serializers.PrimaryKeyRelatedField(source='contrato', queryset=Contrato.objects.all())
    anio = serializers.IntegerField(min_value=2000, max_value=9999)
    mes = serializers.IntegerField(min_value=1, max_value=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['contrato_id'].queryset = _scoped_contrato_queryset(user)


class DistribucionCobroMensualSerializer(serializers.ModelSerializer):
    beneficiario_tipo = serializers.CharField(read_only=True)
    beneficiario_id = serializers.IntegerField(read_only=True)
    beneficiario_display = serializers.CharField(read_only=True)

    class Meta:
        model = DistribucionCobroMensual
        fields = (
            'id',
            'pago_mensual',
            'beneficiario_tipo',
            'beneficiario_id',
            'beneficiario_display',
            'porcentaje_snapshot',
            'monto_devengado_clp',
            'monto_conciliado_clp',
            'monto_facturable_clp',
            'requiere_dte',
            'origen_atribucion',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class GarantiaContractualSerializer(serializers.ModelSerializer):
    saldo_vigente = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = GarantiaContractual
        fields = (
            'id',
            'contrato',
            'monto_pactado',
            'monto_recibido',
            'monto_devuelto',
            'monto_aplicado',
            'saldo_vigente',
            'estado_garantia',
            'fecha_recepcion',
            'fecha_cierre',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'monto_recibido',
            'monto_devuelto',
            'monto_aplicado',
            'saldo_vigente',
            'estado_garantia',
            'fecha_recepcion',
            'fecha_cierre',
            'created_at',
            'updated_at',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['contrato'].queryset = _scoped_contrato_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, GarantiaContractual)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class HistorialGarantiaReadSerializer(serializers.ModelSerializer):
    contrato_id = serializers.IntegerField(source='garantia_contractual.contrato_id', read_only=True)

    class Meta:
        model = HistorialGarantia
        fields = (
            'id',
            'garantia_contractual',
            'contrato_id',
            'tipo_movimiento',
            'monto_clp',
            'fecha',
            'justificacion',
            'movimiento_origen',
            'created_at',
            'updated_at',
        )


class GarantiaMovimientoSerializer(serializers.Serializer):
    tipo_movimiento = serializers.ChoiceField(choices=HistorialGarantia._meta.get_field('tipo_movimiento').choices)
    monto_clp = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    fecha = serializers.DateField()
    justificacion = serializers.CharField(required=False, allow_blank=True)
    movimiento_origen = serializers.PrimaryKeyRelatedField(
        queryset=HistorialGarantia.objects.all(),
        required=False,
        allow_null=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['movimiento_origen'].queryset = _scoped_historial_queryset(user)

    def create(self, validated_data):
        garantia = self.context['garantia']
        return apply_guarantee_movement(garantia=garantia, **validated_data)


class RepactacionDeudaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepactacionDeuda
        fields = (
            'id',
            'arrendatario',
            'contrato_origen',
            'deuda_total_original',
            'cantidad_cuotas',
            'monto_cuota',
            'saldo_pendiente',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['arrendatario'].queryset = _scoped_arrendatario_queryset(user)
        self.fields['contrato_origen'].queryset = _scoped_contrato_queryset(user)

    def validate(self, attrs):
        if not self.instance and 'saldo_pendiente' not in attrs:
            attrs['saldo_pendiente'] = attrs['deuda_total_original']
        candidate = build_validation_candidate(self.instance, RepactacionDeuda)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class CodigoCobroResidualSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodigoCobroResidual
        fields = (
            'id',
            'referencia_visible',
            'arrendatario',
            'contrato_origen',
            'saldo_actual',
            'estado',
            'fecha_activacion',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'referencia_visible', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['arrendatario'].queryset = _scoped_arrendatario_queryset(user)
        self.fields['contrato_origen'].queryset = _scoped_contrato_queryset(user)

    def validate(self, attrs):
        if not self.instance:
            attrs['referencia_visible'] = generate_residual_reference()
        candidate = build_validation_candidate(self.instance, CodigoCobroResidual)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class EstadoCuentaArrendatarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoCuentaArrendatario
        fields = (
            'id',
            'arrendatario',
            'resumen_operativo',
            'score_pago',
            'observaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'arrendatario', 'resumen_operativo', 'created_at', 'updated_at')


class EstadoCuentaRecalculoSerializer(serializers.Serializer):
    arrendatario_id = serializers.PrimaryKeyRelatedField(source='arrendatario', queryset=EstadoCuentaArrendatario._meta.get_field('arrendatario').remote_field.model.objects.all())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['arrendatario_id'].queryset = _scoped_arrendatario_queryset(user)
