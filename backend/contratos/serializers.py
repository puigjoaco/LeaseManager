import calendar
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from core.reference_validation import redact_sensitive_reference
from core.scope_access import scope_queryset_for_user
from operacion.models import IdentidadDeEnvio, MandatoOperacion
from patrimonio.models import Propiedad
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
            'whatsapp_opt_in',
            'whatsapp_opt_in_evidencia_ref',
            'whatsapp_bloqueado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

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

    def validate(self, attrs):
        if attrs['fecha_fin'] < attrs['fecha_inicio']:
            raise serializers.ValidationError({'fecha_fin': 'La fecha fin del periodo no puede ser anterior al inicio.'})
        if attrs['fecha_inicio'].day != 1:
            raise serializers.ValidationError({'fecha_inicio': 'El periodo contractual debe iniciar el primer dia del mes.'})
        last_day = calendar.monthrange(attrs['fecha_fin'].year, attrs['fecha_fin'].month)[1]
        if attrs['fecha_fin'].day != last_day:
            raise serializers.ValidationError({'fecha_fin': 'El periodo contractual debe terminar el ultimo dia del mes.'})
        if attrs['moneda_base'] == MonedaBaseContrato.CLP and attrs['monto_base'] < Decimal('1000.00'):
            raise serializers.ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
        if attrs['moneda_base'] == MonedaBaseContrato.UF and attrs['monto_base'] <= Decimal('0.00'):
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
            'fecha_registro_operativo',
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

        self._validate_contract_properties(contrato_propiedades, mandato, estado)
        self._validate_periods(periodos, fecha_inicio, fecha_fin_vigente)
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

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        if 'snapshot_representante_legal' in attrs:
            attrs['snapshot_representante_legal'] = candidate.snapshot_representante_legal

        return attrs

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
            inactive_properties = [
                item['propiedad'].codigo_propiedad
                for item in contrato_propiedades
                if item['propiedad'].estado != 'activa'
            ]
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

        principal_property = next(
            item['propiedad'] if 'propiedad' in item else None
            for item in contrato_propiedades
            if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )
        principal_property_id = principal_property.id if principal_property else next(
            item['propiedad_id'] for item in contrato_propiedades if item['rol_en_contrato'] == RolContratoPropiedad.PRIMARY
        )
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

    def _validate_periods(self, periodos, fecha_inicio, fecha_fin_vigente):
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
            aviso_exists = AvisoTermino.objects.filter(
                estado=EstadoAvisoTermino.REGISTERED,
                fecha_efectiva__lte=fecha_inicio,
                contrato=current_contract,
            ).exists()
            if not aviso_exists:
                raise serializers.ValidationError(
                    {'estado': 'Un contrato futuro requiere un AvisoTermino registrado para la propiedad principal.'}
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
    class Meta:
        model = AvisoTermino
        fields = (
            'id',
            'contrato',
            'fecha_efectiva',
            'causal',
            'estado',
            'registrado_por',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'registrado_por', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = _request_user(self)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['contrato'].queryset = _scoped_contrato_queryset(user)

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
