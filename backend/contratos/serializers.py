import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from core.reference_validation import is_non_sensitive_reference, redact_sensitive_reference
from core.scope_access import scope_queryset_for_user
from documentos.models import PoliticaFirmaYNotaria
from operacion.models import IdentidadDeEnvio, MandatoOperacion
from patrimonio.models import Propiedad, ServicioPropiedad, TipoServicioPropiedad
from patrimonio.validators import validate_rut

from .models import (
    Arrendatario,
    AvisoTermino,
    CodeudorSolidario,
    ContactoPagoArrendatario,
    Contrato,
    ContratoPropiedad,
    EstadoAvisoTermino,
    EstadoCodeudorSolidario,
    EstadoContrato,
    MonedaBaseContrato,
    PeriodoContractual,
    RENEWAL_PERIOD_KIND,
    RolContratoPropiedad,
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


def _scoped_propiedad_queryset(user):
    return scope_queryset_for_user(Propiedad.objects.all(), user, property_paths=('id',))


def _scoped_mandato_queryset(user):
    return scope_queryset_for_user(MandatoOperacion.objects.all(), user, property_paths=('propiedad_id',))


def _scoped_arrendatario_queryset(user):
    return scope_queryset_for_user(
        Arrendatario.objects.all(),
        user,
        property_paths=('contratos__mandato_operacion__propiedad_id',),
    )


def _scoped_identidad_queryset(user):
    return scope_queryset_for_user(
        IdentidadDeEnvio.objects.all(),
        user,
        company_paths=('empresa_owner_id',),
        property_paths=(
            'asignaciones_operacion__mandato_operacion__propiedad_id',
            'contratos_override__mandato_operacion__propiedad_id',
        ),
    )


def _scoped_contrato_queryset(user):
    return scope_queryset_for_user(
        Contrato.objects.all(),
        user,
        property_paths=('mandato_operacion__propiedad_id',),
    )


class ArrendatarioSerializer(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['whatsapp_opt_in_evidencia_ref'] = redact_sensitive_reference(
            data.get('whatsapp_opt_in_evidencia_ref')
        )
        data['whatsapp_bloqueo_evidencia_ref'] = redact_sensitive_reference(
            data.get('whatsapp_bloqueo_evidencia_ref')
        )
        data['whatsapp_rehabilitacion_ref'] = redact_sensitive_reference(
            data.get('whatsapp_rehabilitacion_ref')
        )
        return data

    class Meta:
        model = Arrendatario
        fields = (
            'id',
            'tipo_arrendatario',
            'nombre_razon_social',
            'rut',
            'email',
            'telefono',
            'domicilio_notificaciones',
            'estado_contacto',
            'nacionalidad',
            'estado_civil',
            'profesion',
            'whatsapp_opt_in',
            'whatsapp_opt_in_evidencia_ref',
            'whatsapp_bloqueado',
            'whatsapp_bloqueo_motivo',
            'whatsapp_bloqueo_evidencia_ref',
            'whatsapp_bloqueado_at',
            'whatsapp_rehabilitacion_ref',
            'whatsapp_rehabilitado_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'whatsapp_bloqueado_at', 'whatsapp_rehabilitado_at', 'created_at', 'updated_at')

    def validate_rut(self, value):
        normalized = validate_rut(value)
        queryset = Arrendatario.objects.filter(rut=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe un arrendatario con ese RUT.')
        return normalized

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, Arrendatario)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class ArrendatarioWhatsappBlockSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=500, trim_whitespace=True)
    evidencia_ref = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate_evidencia_ref(self, value):
        if not is_non_sensitive_reference(value):
            raise serializers.ValidationError('La evidencia de bloqueo WhatsApp debe ser no sensible.')
        return value


class ArrendatarioWhatsappRehabilitateSerializer(serializers.Serializer):
    rehabilitacion_ref = serializers.CharField(max_length=255, trim_whitespace=True)

    def validate_rehabilitacion_ref(self, value):
        if not is_non_sensitive_reference(value):
            raise serializers.ValidationError('La rehabilitacion manual de WhatsApp debe usar referencia no sensible.')
        return value


class ContactoPagoArrendatarioSerializer(serializers.ModelSerializer):
    arrendatario_display = serializers.CharField(source='arrendatario.nombre_razon_social', read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['evidencia_autorizacion_ref'] = redact_sensitive_reference(
            data.get('evidencia_autorizacion_ref')
        )
        return data

    class Meta:
        model = ContactoPagoArrendatario
        fields = (
            'id',
            'arrendatario',
            'arrendatario_display',
            'nombre',
            'rol_operativo',
            'email',
            'telefono',
            'evidencia_autorizacion_ref',
            'es_principal',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'arrendatario_display', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['arrendatario'].queryset = _scoped_arrendatario_queryset(user)

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, ContactoPagoArrendatario)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class CodeudorSolidarioReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeudorSolidario
        fields = ('id', 'snapshot_identidad', 'fecha_inclusion', 'estado', 'created_at', 'updated_at')


class CodeudorSolidarioWriteSerializer(serializers.Serializer):
    snapshot_identidad = serializers.JSONField()
    fecha_inclusion = serializers.DateField(required=False, default=timezone.localdate)
    estado = serializers.ChoiceField(
        choices=EstadoCodeudorSolidario.choices,
        required=False,
        default=EstadoCodeudorSolidario.ACTIVE,
    )

    def validate_snapshot_identidad(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('El snapshot del codeudor debe ser un objeto con nombre y rut.')

        nombre = str(value.get('nombre') or '').strip()
        rut_value = str(value.get('rut') or '').strip()
        if not nombre or not rut_value:
            raise serializers.ValidationError('El snapshot del codeudor debe incluir nombre y rut.')

        normalized = dict(value)
        normalized['nombre'] = nombre
        normalized['rut'] = validate_rut(rut_value)
        return normalized


class ContratoPropiedadReadSerializer(serializers.ModelSerializer):
    propiedad_codigo = serializers.CharField(source='propiedad.codigo_propiedad', read_only=True)
    propiedad_direccion = serializers.CharField(source='propiedad.direccion', read_only=True)

    class Meta:
        model = ContratoPropiedad
        fields = (
            'id',
            'propiedad',
            'propiedad_codigo',
            'propiedad_direccion',
            'rol_en_contrato',
            'porcentaje_distribucion_interna',
            'codigo_conciliacion_efectivo_snapshot',
            'created_at',
            'updated_at',
        )


class ContratoPropiedadWriteSerializer(serializers.Serializer):
    propiedad_id = serializers.PrimaryKeyRelatedField(source='propiedad', queryset=ContratoPropiedad._meta.get_field('propiedad').remote_field.model.objects.all())
    rol_en_contrato = serializers.ChoiceField(choices=RolContratoPropiedad.choices)
    porcentaje_distribucion_interna = serializers.DecimalField(max_digits=5, decimal_places=2)
    codigo_conciliacion_efectivo_snapshot = serializers.RegexField(regex=r'^\d{3}$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['propiedad_id'].queryset = _scoped_propiedad_queryset(user)

    def validate_codigo_conciliacion_efectivo_snapshot(self, value):
        if value == '000':
            raise serializers.ValidationError('El codigo efectivo debe estar en el rango 001-999.')
        return value


class PeriodoContractualReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodoContractual
        fields = (
            'id',
            'numero_periodo',
            'fecha_inicio',
            'fecha_fin',
            'monto_base',
            'moneda_base',
            'tipo_periodo',
            'origen_periodo',
            'politica_base_renovacion_ref',
            'politica_base_renovacion_motivo',
            'created_at',
            'updated_at',
        )


class PeriodoContractualWriteSerializer(serializers.Serializer):
    numero_periodo = serializers.IntegerField(min_value=1)
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    monto_base = serializers.DecimalField(max_digits=14, decimal_places=2)
    moneda_base = serializers.ChoiceField(choices=PeriodoContractual._meta.get_field('moneda_base').choices)
    tipo_periodo = serializers.CharField(max_length=64)
    origen_periodo = serializers.CharField(max_length=64)
    politica_base_renovacion_ref = serializers.CharField(max_length=255, required=False, allow_blank=True)
    politica_base_renovacion_motivo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs['fecha_fin'] < attrs['fecha_inicio']:
            raise serializers.ValidationError({'fecha_fin': 'La fecha fin del periodo no puede ser anterior al inicio.'})
        if attrs['fecha_inicio'].day != 1:
            raise serializers.ValidationError({'fecha_inicio': 'El periodo contractual debe iniciar el primer dia del mes.'})
        if attrs['moneda_base'] == MonedaBaseContrato.CLP and attrs['monto_base'] < Decimal('1000.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
        if attrs['moneda_base'] == MonedaBaseContrato.UF and attrs['monto_base'] <= Decimal('0.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})
        attrs['politica_base_renovacion_ref'] = str(attrs.get('politica_base_renovacion_ref') or '').strip()
        attrs['politica_base_renovacion_motivo'] = str(attrs.get('politica_base_renovacion_motivo') or '').strip()
        if bool(attrs['politica_base_renovacion_ref']) != bool(attrs['politica_base_renovacion_motivo']):
            raise serializers.ValidationError(
                {
                    'politica_base_renovacion_ref': (
                        'La politica de base de renovacion requiere referencia y motivo trazable.'
                    )
                }
            )
        if attrs['politica_base_renovacion_ref'] and not is_non_sensitive_reference(
            attrs['politica_base_renovacion_ref']
        ):
            raise serializers.ValidationError(
                {
                    'politica_base_renovacion_ref': (
                        'La politica de base de renovacion debe usar una referencia no sensible.'
                    )
                }
            )
        return attrs


class ContratoAutomaticRenewalSerializer(serializers.Serializer):
    fecha_fin = serializers.DateField()
    monto_base = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    moneda_base = serializers.ChoiceField(
        choices=PeriodoContractual._meta.get_field('moneda_base').choices,
        required=False,
    )
    politica_base_renovacion_ref = serializers.CharField(max_length=255, required=False, allow_blank=True)
    politica_base_renovacion_motivo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        policy_ref = str(attrs.get('politica_base_renovacion_ref') or '').strip()
        policy_reason = str(attrs.get('politica_base_renovacion_motivo') or '').strip()
        attrs['politica_base_renovacion_ref'] = policy_ref
        attrs['politica_base_renovacion_motivo'] = policy_reason
        if bool(policy_ref) != bool(policy_reason):
            raise serializers.ValidationError(
                {
                    'politica_base_renovacion_ref': (
                        'La politica de base de renovacion requiere referencia y motivo trazable.'
                    )
                }
            )
        if policy_ref and not is_non_sensitive_reference(policy_ref):
            raise serializers.ValidationError(
                {
                    'politica_base_renovacion_ref': (
                        'La politica de base de renovacion debe usar una referencia no sensible.'
                    )
                }
            )
        monto_base = attrs.get('monto_base')
        moneda_base = attrs.get('moneda_base')
        if monto_base is not None and moneda_base == MonedaBaseContrato.CLP and monto_base < Decimal('1000.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
        if monto_base is not None and moneda_base == MonedaBaseContrato.UF and monto_base <= Decimal('0.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})
        return attrs


class ContratoTenantReplacementSerializer(serializers.Serializer):
    arrendatario = serializers.PrimaryKeyRelatedField(queryset=Arrendatario.objects.all())
    codigo_contrato = serializers.CharField(max_length=64, trim_whitespace=True)
    fecha_inicio = serializers.DateField()
    fecha_fin_vigente = serializers.DateField()
    causal_aviso = serializers.CharField(max_length=255, trim_whitespace=True)
    monto_base = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    moneda_base = serializers.ChoiceField(
        choices=PeriodoContractual._meta.get_field('moneda_base').choices,
        required=False,
    )
    dia_pago_mensual = serializers.IntegerField(min_value=1, max_value=5, required=False)
    plazo_notificacion_termino_dias = serializers.IntegerField(min_value=1, required=False)
    dias_prealerta_admin = serializers.IntegerField(min_value=1, required=False)
    politica_documental = serializers.PrimaryKeyRelatedField(
        queryset=PoliticaFirmaYNotaria.objects.all(),
        required=False,
        allow_null=True,
    )
    identidad_envio_override = serializers.PrimaryKeyRelatedField(
        queryset=IdentidadDeEnvio.objects.all(),
        required=False,
        allow_null=True,
    )
    tiene_gastos_comunes = serializers.BooleanField(required=False)
    snapshot_representante_legal = serializers.JSONField(required=False)
    resolucion_conflicto_renovacion_ref = serializers.CharField(max_length=255, required=False, allow_blank=True)
    resolucion_conflicto_renovacion_motivo = serializers.CharField(required=False, allow_blank=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['arrendatario'].queryset = _scoped_arrendatario_queryset(user)
        self.fields['identidad_envio_override'].queryset = _scoped_identidad_queryset(user)

    def validate_codigo_contrato(self, value):
        if Contrato.objects.filter(codigo_contrato=value).exists():
            raise serializers.ValidationError('Ya existe un contrato con ese codigo.')
        return value

    def validate(self, attrs):
        if attrs['fecha_fin_vigente'] < attrs['fecha_inicio']:
            raise serializers.ValidationError(
                {'fecha_fin_vigente': 'La fecha fin del contrato nuevo no puede ser anterior al inicio.'}
            )
        conflict_ref = str(attrs.get('resolucion_conflicto_renovacion_ref') or '').strip()
        conflict_reason = str(attrs.get('resolucion_conflicto_renovacion_motivo') or '').strip()
        attrs['resolucion_conflicto_renovacion_ref'] = conflict_ref
        attrs['resolucion_conflicto_renovacion_motivo'] = conflict_reason
        if bool(conflict_ref) != bool(conflict_reason):
            raise serializers.ValidationError(
                {
                    'resolucion_conflicto_renovacion_ref': (
                        'La resolucion guiada requiere referencia y motivo trazable.'
                    )
                }
            )
        if conflict_ref and not is_non_sensitive_reference(conflict_ref):
            raise serializers.ValidationError(
                {'resolucion_conflicto_renovacion_ref': 'La resolucion guiada debe usar referencia no sensible.'}
            )
        monto_base = attrs.get('monto_base')
        moneda_base = attrs.get('moneda_base')
        if monto_base is not None and moneda_base == MonedaBaseContrato.CLP and monto_base < Decimal('1000.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
        if monto_base is not None and moneda_base == MonedaBaseContrato.UF and monto_base <= Decimal('0.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})
        return attrs


class ContratoSerializer(serializers.ModelSerializer):
    contrato_propiedades = ContratoPropiedadWriteSerializer(many=True, write_only=True, required=False)
    periodos_contractuales = PeriodoContractualWriteSerializer(many=True, write_only=True, required=False)
    codeudores_solidarios = CodeudorSolidarioWriteSerializer(many=True, write_only=True, required=False)
    requiere_notificacion_manual_retroactiva = serializers.SerializerMethodField(read_only=True)
    alerta_notificacion_manual_retroactiva = serializers.SerializerMethodField(read_only=True)
    identidad_envio_override_display = serializers.CharField(
        source='identidad_envio_override.remitente_visible',
        read_only=True,
    )
    contrato_propiedades_detail = serializers.SerializerMethodField(read_only=True)
    periodos_contractuales_detail = serializers.SerializerMethodField(read_only=True)
    codeudores_solidarios_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Contrato
        fields = (
            'id',
            'codigo_contrato',
            'mandato_operacion',
            'arrendatario',
            'fecha_inicio',
            'fecha_fin_vigente',
            'fecha_entrega',
            'entrega_llaves_autorizacion_ref',
            'entrega_llaves_autorizacion_motivo',
            'fecha_registro_operativo',
            'terminacion_anticipada_prorrata_ref',
            'terminacion_anticipada_prorrata_motivo',
            'requiere_notificacion_manual_retroactiva',
            'alerta_notificacion_manual_retroactiva',
            'dia_pago_mensual',
            'plazo_notificacion_termino_dias',
            'dias_prealerta_admin',
            'estado',
            'identidad_envio_override',
            'identidad_envio_override_display',
            'politica_documental',
            'tiene_tramos',
            'tiene_gastos_comunes',
            'snapshot_representante_legal',
            'contrato_propiedades',
            'periodos_contractuales',
            'codeudores_solidarios',
            'contrato_propiedades_detail',
            'periodos_contractuales_detail',
            'codeudores_solidarios_detail',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'fecha_registro_operativo',
            'requiere_notificacion_manual_retroactiva',
            'alerta_notificacion_manual_retroactiva',
            'identidad_envio_override_display',
            'contrato_propiedades_detail',
            'periodos_contractuales_detail',
            'codeudores_solidarios_detail',
            'created_at',
            'updated_at',
        )

    def get_contrato_propiedades_detail(self, obj):
        return ContratoPropiedadReadSerializer(obj.contrato_propiedades.all(), many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['terminacion_anticipada_prorrata_ref'] = redact_sensitive_reference(
            data.get('terminacion_anticipada_prorrata_ref')
        )
        data['entrega_llaves_autorizacion_ref'] = redact_sensitive_reference(
            data.get('entrega_llaves_autorizacion_ref')
        )
        return data

    def get_periodos_contractuales_detail(self, obj):
        return PeriodoContractualReadSerializer(obj.periodos_contractuales.all(), many=True).data

    def get_codeudores_solidarios_detail(self, obj):
        return CodeudorSolidarioReadSerializer(obj.codeudores_solidarios.all(), many=True).data

    def get_requiere_notificacion_manual_retroactiva(self, obj):
        return obj.requires_retroactive_manual_notification()

    def get_alerta_notificacion_manual_retroactiva(self, obj):
        return obj.retroactive_manual_notification_alert()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if not user or not getattr(user, 'is_authenticated', False):
            return
        self.fields['mandato_operacion'].queryset = _scoped_mandato_queryset(user)
        self.fields['arrendatario'].queryset = _scoped_arrendatario_queryset(user)
        self.fields['identidad_envio_override'].queryset = _scoped_identidad_queryset(user)

    def _get_nested_payload(self, attrs, attr_name, queryset):
        if attr_name in attrs:
            return attrs[attr_name]
        if not self.instance:
            return []
        return list(queryset)

    def validate(self, attrs):
        contrato_propiedades = self._get_nested_payload(
            attrs,
            'contrato_propiedades',
            self.instance.contrato_propiedades.values(
                'propiedad_id',
                'rol_en_contrato',
                'porcentaje_distribucion_interna',
                'codigo_conciliacion_efectivo_snapshot',
            ) if self.instance else [],
        )
        periodos = self._get_nested_payload(
            attrs,
            'periodos_contractuales',
            self.instance.periodos_contractuales.values(
                'numero_periodo',
                'fecha_inicio',
                'fecha_fin',
                'monto_base',
                'moneda_base',
                'tipo_periodo',
                'origen_periodo',
                'politica_base_renovacion_ref',
                'politica_base_renovacion_motivo',
            ) if self.instance else [],
        )
        codeudores = self._get_nested_payload(
            attrs,
            'codeudores_solidarios',
            self.instance.codeudores_solidarios.values(
                'snapshot_identidad',
                'fecha_inclusion',
                'estado',
            ) if self.instance else [],
        )

        if self.instance and attrs.get('arrendatario') and attrs['arrendatario'] != self.instance.arrendatario:
            raise serializers.ValidationError(
                {'arrendatario': 'Cambiar el arrendatario requiere terminar el contrato anterior y crear uno nuevo.'}
            )

        if self.instance and attrs.get('codigo_contrato') and attrs['codigo_contrato'] != self.instance.codigo_contrato:
            raise serializers.ValidationError({'codigo_contrato': 'La identidad del contrato es inmutable una vez creada.'})

        mandato = attrs.get('mandato_operacion', getattr(self.instance, 'mandato_operacion', None))
        estado = attrs.get('estado', getattr(self.instance, 'estado', EstadoContrato.PENDING))
        fecha_inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fecha_fin_vigente = attrs.get('fecha_fin_vigente', getattr(self.instance, 'fecha_fin_vigente', None))
        tiene_tramos = attrs.get('tiene_tramos', getattr(self.instance, 'tiene_tramos', False))
        tiene_gastos_comunes = attrs.get(
            'tiene_gastos_comunes',
            getattr(self.instance, 'tiene_gastos_comunes', False),
        )
        self._validate_contract_properties(contrato_propiedades, mandato, estado)
        self._validate_common_expense_service(contrato_propiedades, estado, tiene_gastos_comunes)
        self._validate_periods(
            periodos,
            fecha_inicio,
            fecha_fin_vigente,
            estado=estado,
            tiene_tramos=tiene_tramos,
        )
        self._validate_codeudores(codeudores)
        self._validate_overlap(contrato_propiedades, estado)
        self._validate_effective_code_namespace(contrato_propiedades, estado, mandato)
        self._validate_future_contract_requirements(contrato_propiedades, estado, fecha_inicio)

        candidate = build_validation_candidate(self.instance, Contrato)
        model_attrs = attrs.copy()
        model_attrs.pop('contrato_propiedades', None)
        model_attrs.pop('periodos_contractuales', None)
        model_attrs.pop('codeudores_solidarios', None)
        for field, value in model_attrs.items():
            setattr(candidate, field, value)
        primary_property_id = self._primary_property_id(contrato_propiedades)
        candidate._common_expense_primary_property_id = primary_property_id
        candidate._future_contract_primary_property_id = primary_property_id

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        self._validate_key_delivery_update(attrs, candidate)
        if 'snapshot_representante_legal' in attrs:
            attrs['snapshot_representante_legal'] = candidate.snapshot_representante_legal

        return attrs

    def _validate_key_delivery_update(self, attrs, candidate):
        guarded_fields = {
            'fecha_entrega',
            'entrega_llaves_autorizacion_ref',
            'entrega_llaves_autorizacion_motivo',
        }
        if not self.instance or not guarded_fields.intersection(attrs):
            return
        if not candidate.fecha_entrega:
            return
        if self._has_key_delivery_guarantee_coverage(candidate) or candidate.has_key_delivery_authorization():
            return
        raise serializers.ValidationError(
            {
                'entrega_llaves_autorizacion_ref': (
                    'Registrar entrega de llaves requiere garantia cubierta o autorizacion auditada no sensible.'
                )
            }
        )

    def _has_key_delivery_guarantee_coverage(self, contrato):
        try:
            garantia = contrato.garantia_contractual
        except ObjectDoesNotExist:
            return False
        if garantia.monto_pactado <= Decimal('0.00'):
            return True
        return garantia.monto_recibido >= garantia.monto_pactado or garantia.garantia_parcial_aceptada

    def _validate_contract_properties(self, contrato_propiedades, mandato, estado):
        if not contrato_propiedades:
            raise serializers.ValidationError({'contrato_propiedades': 'Debe enviar al menos una propiedad.'})
        if len(contrato_propiedades) > 2:
            raise serializers.ValidationError(
                {'contrato_propiedades': 'Un contrato solo puede cubrir una propiedad o una pareja principal + vinculada.'}
            )

        property_ids = [
            item['propiedad'].id if 'propiedad' in item else item['propiedad_id']
            for item in contrato_propiedades
        ]
        if len(property_ids) != len(set(property_ids)):
            raise serializers.ValidationError({'contrato_propiedades': 'No puede repetir la misma propiedad dentro del contrato.'})

        if estado in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            inactive_properties = list(
                Propiedad.objects.filter(id__in=property_ids)
                .exclude(estado='activa')
                .values_list('codigo_propiedad', flat=True)
            )
            if inactive_properties:
                raise serializers.ValidationError(
                    {'contrato_propiedades': 'Contratos vigentes o futuros solo pueden usar propiedades activas.'}
                )

        roles = [item['rol_en_contrato'] for item in contrato_propiedades]
        if roles.count(RolContratoPropiedad.PRIMARY) != 1:
            raise serializers.ValidationError({'contrato_propiedades': 'Debe existir exactamente una propiedad principal.'})
        if len(contrato_propiedades) == 2 and roles.count(RolContratoPropiedad.LINKED) != 1:
            raise serializers.ValidationError({'contrato_propiedades': 'Una pareja valida requiere una propiedad vinculada.'})
        if len(contrato_propiedades) == 1 and roles[0] != RolContratoPropiedad.PRIMARY:
            raise serializers.ValidationError({'contrato_propiedades': 'Si hay una sola propiedad, debe ser principal.'})

        principal_property_id = self._primary_property_id(contrato_propiedades)
        if mandato and principal_property_id != mandato.propiedad_id:
            raise serializers.ValidationError(
                {'contrato_propiedades': 'La propiedad principal del contrato debe coincidir con la propiedad del mandato operativo.'}
            )

        total = sum(Decimal(item['porcentaje_distribucion_interna']) for item in contrato_propiedades)
        if total != Decimal('100.00'):
            raise serializers.ValidationError(
                {'contrato_propiedades': 'La distribucion interna del contrato debe sumar exactamente 100.00.'}
            )

        primary_code = next(
            item['codigo_conciliacion_efectivo_snapshot']
            for item in contrato_propiedades
            if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )
        for item in contrato_propiedades:
            if item['codigo_conciliacion_efectivo_snapshot'] != primary_code:
                raise serializers.ValidationError(
                    {'contrato_propiedades': 'La propiedad principal y la vinculada deben compartir el mismo codigo efectivo.'}
                )

    def _validate_common_expense_service(self, contrato_propiedades, estado, tiene_gastos_comunes):
        if not tiene_gastos_comunes or estado not in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            return

        principal_property_id = self._primary_property_id(contrato_propiedades)
        if not ServicioPropiedad.objects.filter(
            propiedad_id=principal_property_id,
            tipo_servicio=TipoServicioPropiedad.COMMON_EXPENSES,
            activo=True,
        ).exists():
            raise serializers.ValidationError(
                {
                    'tiene_gastos_comunes': (
                        'Un contrato vigente o futuro con gastos comunes requiere gasto comun activo '
                        'estructurado en la propiedad principal.'
                    )
                }
            )

    def _primary_property_id(self, contrato_propiedades):
        principal_property = next(
            item['propiedad'] if 'propiedad' in item else None
            for item in contrato_propiedades
            if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )
        if principal_property:
            return principal_property.id
        return next(
            item['propiedad_id'] for item in contrato_propiedades if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )

    def _validate_periods(
        self,
        periodos,
        fecha_inicio,
        fecha_fin_vigente,
        *,
        estado=None,
        tiene_tramos=False,
    ):
        if not periodos:
            raise serializers.ValidationError({'periodos_contractuales': 'Debe enviar al menos un periodo contractual.'})

        numbers = [periodo['numero_periodo'] for periodo in periodos]
        if len(numbers) != len(set(numbers)):
            raise serializers.ValidationError({'periodos_contractuales': 'No puede repetir numero_periodo dentro del contrato.'})

        sorted_numbers = sorted(numbers)
        if sorted_numbers != list(range(1, len(sorted_numbers) + 1)):
            raise serializers.ValidationError({'periodos_contractuales': 'Los periodos deben numerarse secuencialmente desde 1.'})

        sorted_periods = sorted(periodos, key=lambda item: (item['fecha_inicio'], item['numero_periodo']))
        for expected_number, period in enumerate(sorted_periods, start=1):
            if period['numero_periodo'] != expected_number:
                raise serializers.ValidationError(
                    {'periodos_contractuales': 'Los periodos deben numerarse en orden cronologico desde 1.'}
                )
            period_end = period['fecha_fin']
            last_day = calendar.monthrange(period_end.year, period_end.month)[1]
            is_final_period = expected_number == len(sorted_periods)
            allow_partial_final_period = (
                is_final_period
                and estado == EstadoContrato.EARLY_TERMINATED
                and fecha_fin_vigente == period_end
                and period_end.day != last_day
            )
            if period_end.day != last_day and not allow_partial_final_period:
                raise serializers.ValidationError(
                    {'periodos_contractuales': 'Los periodos contractuales deben cerrar al ultimo dia del mes, salvo ultimo mes parcial por terminacion anticipada auditada.'}
                )
        for index in range(1, len(sorted_periods)):
            if sorted_periods[index]['fecha_inicio'] <= sorted_periods[index - 1]['fecha_fin']:
                raise serializers.ValidationError(
                    {'periodos_contractuales': 'Los periodos contractuales no pueden solaparse.'}
                )
            expected_start = sorted_periods[index - 1]['fecha_fin'] + timedelta(days=1)
            if sorted_periods[index]['fecha_inicio'] != expected_start:
                raise serializers.ValidationError(
                    {'periodos_contractuales': 'Los periodos contractuales deben cubrir la vigencia sin huecos.'}
                )
            if (
                tiene_tramos
                and str(sorted_periods[index]['tipo_periodo']).strip().lower() == RENEWAL_PERIOD_KIND
                and (
                    sorted_periods[index]['moneda_base'] != sorted_periods[index - 1]['moneda_base']
                    or Decimal(sorted_periods[index]['monto_base']) != Decimal(sorted_periods[index - 1]['monto_base'])
                )
                and not (
                    str(sorted_periods[index].get('politica_base_renovacion_ref') or '').strip()
                    and str(sorted_periods[index].get('politica_base_renovacion_motivo') or '').strip()
                )
            ):
                raise serializers.ValidationError(
                    {
                        'periodos_contractuales': (
                            'Una renovacion con base distinta al ultimo tramo vigente requiere '
                            'politica documentada con referencia no sensible y motivo trazable.'
                        )
                    }
                )

        if fecha_inicio and sorted_periods[0]['fecha_inicio'] != fecha_inicio:
            raise serializers.ValidationError(
                {'periodos_contractuales': 'El primer periodo debe iniciar exactamente en la fecha de inicio del contrato.'}
            )

        if fecha_fin_vigente and sorted_periods[-1]['fecha_fin'] != fecha_fin_vigente:
            raise serializers.ValidationError(
                {'periodos_contractuales': 'El ultimo periodo debe cerrar exactamente en la fecha_fin_vigente del contrato.'}
            )

    def _validate_codeudores(self, codeudores):
        if len(codeudores) > 3:
            raise serializers.ValidationError({'codeudores_solidarios': 'Un contrato admite como maximo 3 codeudores solidarios.'})

        rut_values = []
        for codeudor in codeudores:
            snapshot = codeudor['snapshot_identidad']
            rut_values.append(snapshot['rut'])
        if len(rut_values) != len(set(rut_values)):
            raise serializers.ValidationError({'codeudores_solidarios': 'No puede repetir el mismo codeudor dentro del contrato.'})

    def _validate_overlap(self, contrato_propiedades, estado):
        if estado not in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            return

        property_ids = [
            item['propiedad'].id if 'propiedad' in item else item['propiedad_id']
            for item in contrato_propiedades
        ]
        queryset = ContratoPropiedad.objects.filter(propiedad_id__in=property_ids)
        if self.instance:
            queryset = queryset.exclude(contrato=self.instance)

        state_to_check = EstadoContrato.ACTIVE if estado == EstadoContrato.ACTIVE else EstadoContrato.FUTURE
        if queryset.filter(contrato__estado=state_to_check).exists():
            label = 'vigente' if estado == EstadoContrato.ACTIVE else 'futuro'
            raise serializers.ValidationError(
                {'contrato_propiedades': f'Las propiedades ya tienen un contrato {label} incompatible.'}
            )

    def _validate_effective_code_namespace(self, contrato_propiedades, estado, mandato):
        if estado not in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE} or not mandato:
            return

        primary_code = next(
            item['codigo_conciliacion_efectivo_snapshot']
            for item in contrato_propiedades
            if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )
        queryset = ContratoPropiedad.objects.filter(
            contrato__mandato_operacion__cuenta_recaudadora_id=mandato.cuenta_recaudadora_id,
            contrato__estado=estado,
            codigo_conciliacion_efectivo_snapshot=primary_code,
        )
        if self.instance:
            queryset = queryset.exclude(contrato=self.instance)

        if queryset.exists():
            label = 'vigente' if estado == EstadoContrato.ACTIVE else 'futuro'
            raise serializers.ValidationError(
                {
                    'contrato_propiedades': (
                        f'El codigo efectivo ya esta usado en otro contrato {label} de la misma cuenta recaudadora.'
                    )
                }
            )

    def _validate_future_contract_requirements(self, contrato_propiedades, estado, fecha_inicio):
        if estado != EstadoContrato.FUTURE:
            return

        principal_property_id = next(
            item['propiedad'].id if 'propiedad' in item else item['propiedad_id']
            for item in contrato_propiedades
            if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )
        current_contract_qs = Contrato.objects.filter(
            estado=EstadoContrato.ACTIVE,
            contrato_propiedades__propiedad_id=principal_property_id,
            contrato_propiedades__rol_en_contrato=RolContratoPropiedad.PRIMARY,
        ).distinct()
        if self.instance:
            current_contract_qs = current_contract_qs.exclude(pk=self.instance.pk)
        current_contract = current_contract_qs.order_by('-fecha_inicio', '-id').first()
        if current_contract is not None:
            aviso = AvisoTermino.objects.filter(
                estado=EstadoAvisoTermino.REGISTERED,
                fecha_efectiva__lte=fecha_inicio,
                contrato=current_contract,
            ).order_by('-fecha_efectiva', '-id').first()
            if aviso is None:
                raise serializers.ValidationError(
                    {'estado': 'Un contrato futuro requiere un AvisoTermino registrado para la propiedad principal.'}
                )
            if aviso.has_executed_renewal_conflict(fecha_inicio):
                if (
                    not aviso.has_renewal_conflict_resolution()
                    or not is_non_sensitive_reference(aviso.resolucion_conflicto_renovacion_ref)
                ):
                    raise serializers.ValidationError(
                        {
                            'estado': (
                                'Existe conflicto entre AvisoTermino, renovacion ya ejecutada y contrato futuro; '
                                'se requiere resolucion guiada con referencia no sensible y motivo trazable.'
                            )
                        }
                    )
            return

        early_terminated_exists = Contrato.objects.filter(
            estado=EstadoContrato.EARLY_TERMINATED,
            fecha_fin_vigente__lte=fecha_inicio,
            contrato_propiedades__propiedad_id=principal_property_id,
            contrato_propiedades__rol_en_contrato=RolContratoPropiedad.PRIMARY,
        ).exclude(pk=self.instance.pk if self.instance else None).exists()
        if not early_terminated_exists:
            raise serializers.ValidationError(
                {'estado': 'Un contrato futuro requiere un AvisoTermino registrado o una terminación anticipada ejecutada sobre la propiedad principal.'}
            )

    def create(self, validated_data):
        contrato_propiedades = validated_data.pop('contrato_propiedades', [])
        periodos = validated_data.pop('periodos_contractuales', [])
        codeudores = validated_data.pop('codeudores_solidarios', [])
        validated_data.setdefault('fecha_registro_operativo', timezone.localdate())
        with transaction.atomic():
            contrato = Contrato.objects.create(**validated_data)
            self._sync_children(contrato, contrato_propiedades, periodos, codeudores)
        return contrato

    def update(self, instance, validated_data):
        contrato_propiedades = validated_data.pop('contrato_propiedades', None)
        periodos = validated_data.pop('periodos_contractuales', None)
        codeudores = validated_data.pop('codeudores_solidarios', None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            self._sync_children(instance, contrato_propiedades, periodos, codeudores)
        return instance

    def _sync_children(self, contrato, contrato_propiedades, periodos, codeudores):
        if contrato_propiedades is not None:
            contrato.contrato_propiedades.all().delete()
            ContratoPropiedad.objects.bulk_create(
                [
                    ContratoPropiedad(
                        contrato=contrato,
                        propiedad=item['propiedad'],
                        rol_en_contrato=item['rol_en_contrato'],
                        porcentaje_distribucion_interna=item['porcentaje_distribucion_interna'],
                        codigo_conciliacion_efectivo_snapshot=item['codigo_conciliacion_efectivo_snapshot'],
                    )
                    for item in contrato_propiedades
                ]
            )

        if periodos is not None:
            contrato.periodos_contractuales.all().delete()
            PeriodoContractual.objects.bulk_create(
                [
                    PeriodoContractual(
                        contrato=contrato,
                        numero_periodo=item['numero_periodo'],
                        fecha_inicio=item['fecha_inicio'],
                        fecha_fin=item['fecha_fin'],
                        monto_base=item['monto_base'],
                        moneda_base=item['moneda_base'],
                        tipo_periodo=item['tipo_periodo'],
                        origen_periodo=item['origen_periodo'],
                        politica_base_renovacion_ref=item.get('politica_base_renovacion_ref', ''),
                        politica_base_renovacion_motivo=item.get('politica_base_renovacion_motivo', ''),
                    )
                    for item in periodos
                ]
            )

        if codeudores is not None:
            contrato.codeudores_solidarios.all().delete()
            CodeudorSolidario.objects.bulk_create(
                [
                    CodeudorSolidario(
                        contrato=contrato,
                        snapshot_identidad=item['snapshot_identidad'],
                        fecha_inclusion=item['fecha_inclusion'],
                        estado=item['estado'],
                    )
                    for item in codeudores
                ]
            )


class AvisoTerminoSerializer(serializers.ModelSerializer):
    fecha_limite_registro_oportuno = serializers.SerializerMethodField(read_only=True)
    registrado_fuera_plazo = serializers.SerializerMethodField(read_only=True)
    alerta_registro_fuera_plazo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AvisoTermino
        fields = (
            'id',
            'contrato',
            'fecha_efectiva',
            'causal',
            'estado',
            'resolucion_conflicto_renovacion_ref',
            'resolucion_conflicto_renovacion_motivo',
            'registrado_por',
            'fecha_limite_registro_oportuno',
            'registrado_fuera_plazo',
            'alerta_registro_fuera_plazo',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'registrado_por', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['contrato'].queryset = _scoped_contrato_queryset(user)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['resolucion_conflicto_renovacion_ref'] = redact_sensitive_reference(
            data.get('resolucion_conflicto_renovacion_ref')
        )
        return data

    def get_fecha_limite_registro_oportuno(self, obj):
        latest = obj.latest_timely_registration_at()
        return latest.isoformat() if latest else None

    def get_registrado_fuera_plazo(self, obj):
        return obj.is_late_registered_notice()

    def get_alerta_registro_fuera_plazo(self, obj):
        return obj.late_registration_alert()

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, AvisoTermino)
        for field, value in attrs.items():
            setattr(candidate, field, value)
        if candidate.estado == EstadoAvisoTermino.REGISTERED and not getattr(candidate, 'registrado_por_id', None):
            candidate.registrado_por = self.context['request'].user

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs

    def create(self, validated_data):
        if validated_data.get('estado') == EstadoAvisoTermino.REGISTERED:
            validated_data['registrado_por'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('estado') == EstadoAvisoTermino.REGISTERED and not instance.registrado_por_id:
            validated_data['registrado_por'] = self.context['request'].user
        return super().update(instance, validated_data)
