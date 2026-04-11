from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.scope_access import scope_queryset_for_user

from .models import ConexionBancaria, IngresoDesconocido, MovimientoBancarioImportado


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


class ConexionBancariaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConexionBancaria
        fields = (
            'id',
            'cuenta_recaudadora',
            'provider_key',
            'credencial_ref',
            'scope',
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


class MovimientoBancarioImportadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoBancarioImportado
        fields = (
            'id',
            'conexion_bancaria',
            'fecha_movimiento',
            'tipo_movimiento',
            'monto',
            'descripcion_origen',
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
