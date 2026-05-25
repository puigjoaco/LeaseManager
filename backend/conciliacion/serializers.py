from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.reference_validation import redact_sensitive_reference
from core.scope_access import scope_queryset_for_user

from .models import (
    CuadraturaBancaria,
    ConexionBancaria,
    IngresoDesconocido,
    MovimientoBancarioImportado,
    TransferenciaIntercuenta,
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


def _scoped_cuenta_queryset(user):
    from operacion.models import CuentaRecaudadora

    return scope_queryset_for_user(CuentaRecaudadora.objects.all(), user, bank_account_paths=('id',))


def _scoped_conexion_queryset(user):
    return scope_queryset_for_user(
        ConexionBancaria.objects.all(),
        user,
        bank_account_paths=('cuenta_recaudadora_id',),
    )


class RedactReferenceFieldsMixin:
    redacted_reference_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in self.redacted_reference_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_reference(data[field_name])
        return data


class ConexionBancariaSerializer(RedactReferenceFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = (
        'credencial_ref',
        'evidencia_gate_ref',
        'prueba_conectividad_ref',
        'prueba_movimientos_ref',
        'prueba_saldos_ref',
    )

    class Meta:
        model = ConexionBancaria
        fields = (
            'id',
            'cuenta_recaudadora',
            'provider_key',
            'credencial_ref',
            'scope',
            'evidencia_gate_ref',
            'prueba_conectividad_ref',
            'prueba_movimientos_ref',
            'prueba_saldos_ref',
            'expira_en',
            'estado_conexion',
            'primaria_movimientos',
            'primaria_saldos',
            'primaria_conectividad',
            'ultimo_exito_at',
            'ultimo_error_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['cuenta_recaudadora'].queryset = _scoped_cuenta_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, ConexionBancaria)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class MovimientoBancarioImportadoSerializer(RedactReferenceFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('evidencia_importacion_ref', 'referencia', 'transaction_id_banco')

    class Meta:
        model = MovimientoBancarioImportado
        fields = (
            'id',
            'conexion_bancaria',
            'fecha_movimiento',
            'tipo_movimiento',
            'monto',
            'descripcion_origen',
            'origen_importacion',
            'evidencia_importacion_ref',
            'numero_documento',
            'saldo_reportado',
            'referencia',
            'transaction_id_banco',
            'estado_conciliacion',
            'pago_mensual',
            'codigo_cobro_residual',
            'notas_admin',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'estado_conciliacion',
            'pago_mensual',
            'codigo_cobro_residual',
            'created_at',
            'updated_at',
        )
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['conexion_bancaria'].queryset = _scoped_conexion_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, MovimientoBancarioImportado)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class IngresoDesconocidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngresoDesconocido
        fields = (
            'id',
            'movimiento_bancario',
            'cuenta_recaudadora',
            'monto',
            'fecha_movimiento',
            'descripcion_origen',
            'estado',
            'sugerencia_asistida',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class CuadraturaBancariaSerializer(RedactReferenceFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('evidencia_cuadratura_ref', 'responsable_ref')

    class Meta:
        model = CuadraturaBancaria
        fields = (
            'id',
            'cuenta_recaudadora',
            'periodo_economico',
            'fecha_cuadratura',
            'saldo_sistema_clp',
            'saldo_banco_clp',
            'diferencia_clp',
            'estado',
            'evidencia_cuadratura_ref',
            'responsable_ref',
            'rationale',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'diferencia_clp', 'created_at', 'updated_at')
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['cuenta_recaudadora'].queryset = _scoped_cuenta_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, CuadraturaBancaria)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class TransferenciaIntercuentaSerializer(RedactReferenceFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('evidencia_transferencia_ref', 'responsable_ref')

    class Meta:
        model = TransferenciaIntercuenta
        fields = (
            'id',
            'movimiento_origen',
            'movimiento_destino',
            'periodo_economico',
            'entidad_origen_tipo',
            'entidad_origen_id',
            'entidad_destino_tipo',
            'entidad_destino_id',
            'criterio_conciliacion',
            'evidencia_transferencia_ref',
            'responsable_ref',
            'rationale',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'entidad_origen_tipo',
            'entidad_origen_id',
            'entidad_destino_tipo',
            'entidad_destino_id',
            'created_at',
            'updated_at',
        )
        validators = []

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, TransferenciaIntercuenta)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs
