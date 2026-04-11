from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.scope_access import scope_queryset_for_user
from patrimonio.models import Empresa

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
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


def _scoped_empresa_queryset(user):
    return scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',))


class RegimenTributarioEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegimenTributarioEmpresa
        fields = ('id', 'codigo_regimen', 'descripcion', 'estado', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')


class ConfiguracionFiscalEmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionFiscalEmpresa
        fields = (
            'id',
            'empresa',
            'regimen_tributario',
            'afecta_iva_arriendo',
            'tasa_iva',
            'aplica_ppm',
            'ddjj_habilitadas',
            'inicio_ejercicio',
            'moneda_funcional',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = _scoped_empresa_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, ConfiguracionFiscalEmpresa)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class CuentaContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuentaContable
        fields = (
            'id',
            'empresa',
            'plan_cuentas_version',
            'codigo',
            'nombre',
            'naturaleza',
            'nivel',
            'padre',
            'estado',
            'es_control_obligatoria',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['empresa'].queryset = _scoped_empresa_queryset(user)
        self.fields['padre'].queryset = scope_queryset_for_user(
            CuentaContable.objects.all(),
            user,
            company_paths=('empresa_id',),
        )

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, CuentaContable)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class ReglaContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReglaContable
        fields = (
            'id',
            'empresa',
            'evento_tipo',
            'plan_cuentas_version',
            'criterio_cargo',
            'criterio_abono',
            'vigencia_desde',
            'vigencia_hasta',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = _scoped_empresa_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, ReglaContable)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class MatrizReglasContablesSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatrizReglasContables
        fields = (
            'id',
            'regla_contable',
            'cuenta_debe',
            'cuenta_haber',
            'condicion_impuesto',
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
        self.fields['regla_contable'].queryset = scope_queryset_for_user(
            ReglaContable.objects.all(),
            user,
            company_paths=('empresa_id',),
        )
        scoped_cuentas = scope_queryset_for_user(CuentaContable.objects.all(), user, company_paths=('empresa_id',))
        self.fields['cuenta_debe'].queryset = scoped_cuentas
        self.fields['cuenta_haber'].queryset = scoped_cuentas

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, MatrizReglasContables)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class EventoContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoContable
        fields = (
            'id',
            'empresa',
            'evento_tipo',
            'entidad_origen_tipo',
            'entidad_origen_id',
            'fecha_operativa',
            'moneda',
            'monto_base',
            'payload_resumen',
            'idempotency_key',
            'estado_contable',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'estado_contable', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = _scoped_empresa_queryset(user)


class MovimientoAsientoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoAsiento
        fields = (
            'id',
            'cuenta_contable',
            'tipo_movimiento',
            'monto',
            'glosa',
            'centro_resultado_ref',
            'created_at',
            'updated_at',
        )


class AsientoContableSerializer(serializers.ModelSerializer):
    movimientos = MovimientoAsientoSerializer(many=True, read_only=True)

    class Meta:
        model = AsientoContable
        fields = (
            'id',
            'evento_contable',
            'fecha_contable',
            'periodo_contable',
            'estado',
            'debe_total',
            'haber_total',
            'moneda_funcional',
            'hash_integridad',
            'movimientos',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class PoliticaReversoContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = PoliticaReversoContable
        fields = (
            'id',
            'empresa',
            'tipo_ajuste',
            'usa_reverso',
            'usa_asiento_complementario',
            'permite_reapertura',
            'aprobacion_requerida',
            'ventana_operativa',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = _scoped_empresa_queryset(user)


class ObligacionTributariaMensualSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObligacionTributariaMensual
        fields = (
            'id',
            'empresa',
            'anio',
            'mes',
            'obligacion_tipo',
            'base_imponible',
            'monto_calculado',
            'estado_preparacion',
            'detalle_calculo',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class LibroDiarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibroDiario
        fields = ('id', 'empresa', 'periodo', 'estado_snapshot', 'storage_ref', 'resumen', 'created_at', 'updated_at')
        read_only_fields = fields


class LibroMayorSerializer(serializers.ModelSerializer):
    class Meta:
        model = LibroMayor
        fields = ('id', 'empresa', 'periodo', 'estado_snapshot', 'storage_ref', 'resumen', 'created_at', 'updated_at')
        read_only_fields = fields


class BalanceComprobacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BalanceComprobacion
        fields = ('id', 'empresa', 'periodo', 'estado_snapshot', 'storage_ref', 'resumen', 'created_at', 'updated_at')
        read_only_fields = fields


class CierreMensualContableSerializer(serializers.ModelSerializer):
    class Meta:
        model = CierreMensualContable
        fields = (
            'id',
            'empresa',
            'anio',
            'mes',
            'estado',
            'fecha_preparacion',
            'fecha_aprobacion',
            'resumen_obligaciones',
            'created_at',
            'updated_at',
        )
        read_only_fields = fields


class CierreMensualPrepareSerializer(serializers.Serializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', queryset=Empresa.objects.all())
    anio = serializers.IntegerField(min_value=2000, max_value=9999)
    mes = serializers.IntegerField(min_value=1, max_value=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa_id'].queryset = _scoped_empresa_queryset(user)
