from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ConexionBancaria, IngresoDesconocido, MovimientoBancarioImportado


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


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

