from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference, redact_sensitive_payload, redact_sensitive_reference
from core.scope_access import scope_queryset_for_user
from patrimonio.models import ComunidadPatrimonial, Empresa, Socio

from .models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EventoContable,
    LibroDiario,
    LibroMayor,
    LineaLiquidacionMensual,
    LiquidacionMensual,
    MatrizReglasContables,
    MovimientoAsiento,
    ObligacionTributariaMensual,
    PoliticaReversoContable,
    RegimenTributarioEmpresa,
    ReglaContable,
    TipoEfectoReaperturaCierre,
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


class RedactSensitiveAccountingFieldsMixin:
    redacted_payload_fields = ()
    redacted_reference_fields = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in self.redacted_reference_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_reference(data[field_name])
        for field_name in self.redacted_payload_fields:
            if field_name in data:
                data[field_name] = redact_sensitive_payload(data[field_name])
        return data


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
            'tasa_ppm_vigente',
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
        if 'data' not in kwargs:
            return
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
        if 'data' not in kwargs:
            return
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
        if 'data' not in kwargs:
            return
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
        if 'data' not in kwargs:
            return
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


class EventoContableSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_payload_fields = ('payload_resumen',)

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
        if 'data' not in kwargs:
            return
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = _scoped_empresa_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, EventoContable)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        if candidate.monto_base <= 0:
            raise serializers.ValidationError({'monto_base': 'El monto_base debe ser mayor que cero.'})
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class MovimientoAsientoSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('centro_resultado_ref',)

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
        if 'data' not in kwargs:
            return
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa'].queryset = _scoped_empresa_queryset(user)


class ObligacionTributariaMensualSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_payload_fields = ('detalle_calculo',)

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


class LibroDiarioSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_payload_fields = ('resumen',)
    redacted_reference_fields = ('storage_ref',)

    class Meta:
        model = LibroDiario
        fields = ('id', 'empresa', 'periodo', 'estado_snapshot', 'storage_ref', 'resumen', 'created_at', 'updated_at')
        read_only_fields = fields


class LibroMayorSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_payload_fields = ('resumen',)
    redacted_reference_fields = ('storage_ref',)

    class Meta:
        model = LibroMayor
        fields = ('id', 'empresa', 'periodo', 'estado_snapshot', 'storage_ref', 'resumen', 'created_at', 'updated_at')
        read_only_fields = fields


class BalanceComprobacionSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_payload_fields = ('resumen',)
    redacted_reference_fields = ('storage_ref',)

    class Meta:
        model = BalanceComprobacion
        fields = ('id', 'empresa', 'periodo', 'estado_snapshot', 'storage_ref', 'resumen', 'created_at', 'updated_at')
        read_only_fields = fields


class CierreMensualContableSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_payload_fields = ('resumen_obligaciones',)

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


class LineaLiquidacionMensualSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('descripcion', 'evidencia_ref')

    class Meta:
        model = LineaLiquidacionMensual
        fields = (
            'id',
            'liquidacion',
            'tipo_linea',
            'descripcion',
            'monto_clp',
            'evidencia_ref',
            'beneficiario_socio',
            'evento_contable',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'data' not in kwargs:
            return
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['liquidacion'].queryset = scope_queryset_for_user(
            LiquidacionMensual.objects.all(),
            user,
            company_paths=('empresa_id', 'cierre_contable__empresa_id'),
        )
        self.fields['evento_contable'].queryset = scope_queryset_for_user(
            EventoContable.objects.all(),
            user,
            company_paths=('empresa_id',),
        )
        self.fields['beneficiario_socio'].queryset = Socio.objects.filter(activo=True)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, LineaLiquidacionMensual)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class LiquidacionMensualSerializer(RedactSensitiveAccountingFieldsMixin, serializers.ModelSerializer):
    redacted_reference_fields = ('evidencia_base_ref', 'responsable_ref', 'saldo_final_evidencia_ref')
    lineas = LineaLiquidacionMensualSerializer(many=True, read_only=True)

    class Meta:
        model = LiquidacionMensual
        fields = (
            'id',
            'owner_tipo',
            'empresa',
            'comunidad',
            'socio',
            'cierre_contable',
            'anio',
            'mes',
            'estado',
            'comision_administracion_aplica',
            'saldo_final_clp',
            'saldo_final_explicacion',
            'saldo_final_evidencia_ref',
            'evidencia_base_ref',
            'responsable_ref',
            'lineas',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'lineas', 'created_at', 'updated_at')
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'data' not in kwargs:
            return
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['empresa'].queryset = _scoped_empresa_queryset(user)
        self.fields['cierre_contable'].queryset = scope_queryset_for_user(
            CierreMensualContable.objects.all(),
            user,
            company_paths=('empresa_id',),
        )
        self.fields['comunidad'].queryset = ComunidadPatrimonial.objects.filter(estado='activa')
        self.fields['socio'].queryset = Socio.objects.filter(activo=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['saldo_final_explicacion'] = redact_sensitive_reference(data.get('saldo_final_explicacion', ''))
        return data

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, LiquidacionMensual)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class CierreMensualPrepareSerializer(serializers.Serializer):
    empresa_id = serializers.PrimaryKeyRelatedField(source='empresa', queryset=Empresa.objects.all())
    anio = serializers.IntegerField(min_value=2000, max_value=9999)
    mes = serializers.IntegerField(min_value=1, max_value=12)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['empresa_id'].queryset = _scoped_empresa_queryset(user)


class CierreMensualReopenSerializer(serializers.Serializer):
    tipo_efecto = serializers.ChoiceField(choices=TipoEfectoReaperturaCierre.choices)
    monto_efecto = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal('0.01'))
    motivo = serializers.CharField(max_length=255, trim_whitespace=True)
    efecto_esperado = serializers.CharField(max_length=255, trim_whitespace=True)
    evidencia_ref = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate(self, attrs):
        if not is_non_sensitive_reference(attrs['evidencia_ref']):
            raise serializers.ValidationError(
                {'evidencia_ref': 'evidencia_ref debe ser una referencia no sensible.'}
            )
        for field in ('motivo', 'efecto_esperado'):
            if contains_sensitive_reference(attrs[field], include_sensitive_keys=True):
                raise serializers.ValidationError(
                    {field: f'{field} no debe contener URLs, tokens, credenciales ni correos.'}
                )
        return attrs
