from rest_framework import serializers

from cobranza.models import PagoMensual
from conciliacion.models import CategoriaMovimiento, MovimientoBancarioImportado
from core.reference_validation import (
    contains_sensitive_reference,
    is_non_sensitive_reference,
    redact_sensitive_payload,
    redact_sensitive_reference,
)
from core.scope_access import scope_queryset_for_user
from patrimonio.models import Empresa, ModoRepresentacionComunidad, Socio
from patrimonio.validators import validate_rut

from .models import AuditEvent, ManualResolution


SPECIALIZED_MANUAL_RESOLUTION_CATEGORIES = {
    'conciliacion.ingreso_desconocido',
    'conciliacion.movimiento_cargo',
    'migration.propiedad.owner_manual_required',
    'migration.cobranza.distribucion_facturable_conflict',
}


class AuditEventSerializer(serializers.ModelSerializer):
    actor_user_display = serializers.SerializerMethodField()

    class Meta:
        model = AuditEvent
        fields = '__all__'

    def get_actor_user_display(self, obj):
        if obj.actor_user_id:
            return obj.actor_user.display_name or obj.actor_user.username
        return redact_sensitive_reference(obj.actor_identifier) or 'Sistema'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in ('actor_identifier', 'entity_id', 'summary', 'request_id'):
            data[field_name] = redact_sensitive_reference(data.get(field_name))
        data['metadata'] = redact_sensitive_payload(data.get('metadata') or {})
        return data


class ManualResolutionSerializer(serializers.ModelSerializer):
    requested_by_display = serializers.SerializerMethodField()
    resolved_by_display = serializers.SerializerMethodField()

    class Meta:
        model = ManualResolution
        fields = '__all__'
        read_only_fields = ('id', 'requested_by', 'resolved_by', 'created_at', 'resolved_at')

    def get_requested_by_display(self, obj):
        if obj.requested_by_id:
            return obj.requested_by.display_name or obj.requested_by.username
        return ''

    def get_resolved_by_display(self, obj):
        if obj.resolved_by_id:
            return obj.resolved_by.display_name or obj.resolved_by.username
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field_name in ('scope_reference', 'summary', 'rationale'):
            data[field_name] = redact_sensitive_reference(data.get(field_name))
        data['metadata'] = redact_sensitive_payload(data.get('metadata') or {})
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        category = attrs.get('category', self.instance.category if self.instance else None)
        errors = {}
        for field_name in ('scope_reference', 'summary', 'rationale'):
            if field_name in attrs and contains_sensitive_reference(attrs[field_name]):
                errors[field_name] = 'Use una referencia o descripcion trazable no sensible.'
        if 'metadata' in attrs and contains_sensitive_reference(attrs['metadata'], include_sensitive_keys=True):
            errors['metadata'] = 'metadata no debe contener URLs, tokens, correos, credenciales ni claves sensibles.'
        terminal_statuses = {ManualResolution.Status.RESOLVED, ManualResolution.Status.SUPERSEDED}
        status_value = attrs.get('status')
        if self.instance is None and status_value in terminal_statuses:
            errors['status'] = 'La resolucion manual debe crearse abierta y cerrarse por un flujo auditado.'
        if self.instance is None and category in SPECIALIZED_MANUAL_RESOLUTION_CATEGORIES:
            errors['category'] = 'Use el servicio especializado correspondiente para crear este caso.'
        if (
            self.instance
            and (
                self.instance.category in SPECIALIZED_MANUAL_RESOLUTION_CATEGORIES
                or category in SPECIALIZED_MANUAL_RESOLUTION_CATEGORIES
            )
        ):
            if category and category != self.instance.category:
                errors['category'] = 'Use el servicio especializado correspondiente para cambiar este caso.'
            for field_name in ('scope_type', 'scope_reference', 'metadata'):
                if field_name in attrs:
                    errors[field_name] = 'Use el servicio especializado correspondiente para retargetear este caso.'
            status_value = attrs.get('status')
            if (
                status_value in {ManualResolution.Status.RESOLVED, ManualResolution.Status.SUPERSEDED}
                and self.instance.status != status_value
            ):
                errors['status'] = 'Use la resolución especializada correspondiente para cerrar este caso.'
            if errors:
                raise serializers.ValidationError(errors)
        if self.instance:
            next_status = status_value or self.instance.status
            if self.instance.status in terminal_statuses and status_value and status_value != self.instance.status:
                errors['status'] = 'Una resolucion manual cerrada no puede reabrirse ni cambiar de estado.'
            if next_status in terminal_statuses and self.instance.status != next_status:
                rationale = attrs.get('rationale', self.instance.rationale)
                if not str(rationale or '').strip():
                    errors['rationale'] = 'Cerrar una resolucion manual requiere rationale trazable.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class ResolveMigrationPropertyOwnerParticipationSerializer(serializers.Serializer):
    participante_tipo = serializers.ChoiceField(choices=('socio', 'empresa'))
    participante_id = serializers.IntegerField(required=False)
    participante_rut = serializers.CharField(required=False)
    porcentaje = serializers.DecimalField(max_digits=5, decimal_places=2)
    vigente_desde = serializers.DateField()
    vigente_hasta = serializers.DateField(required=False, allow_null=True)
    activo = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        participante_id = attrs.get('participante_id')
        participante_rut = attrs.get('participante_rut')
        if not participante_id and not participante_rut:
            raise serializers.ValidationError('Debe enviar participante_id o participante_rut.')
        if participante_rut:
            attrs['participante_rut'] = validate_rut(participante_rut)

        participante_tipo = attrs['participante_tipo']
        model = Socio if participante_tipo == 'socio' else Empresa
        if participante_id:
            try:
                participant = model.objects.get(pk=participante_id)
            except model.DoesNotExist as error:
                raise serializers.ValidationError({'participante_id': 'El participante indicado no existe.'}) from error
        else:
            lookup_field = 'rut'
            try:
                participant = model.objects.get(**{lookup_field: attrs['participante_rut']})
            except model.DoesNotExist as error:
                raise serializers.ValidationError({'participante_rut': 'No existe un participante canónico para ese RUT.'}) from error

        attrs['participante_socio_obj'] = participant if participante_tipo == 'socio' else None
        attrs['participante_empresa_obj'] = participant if participante_tipo == 'empresa' else None
        return attrs


class ResolveMigrationPropertyOwnerSerializer(serializers.Serializer):
    nombre_comunidad = serializers.CharField(max_length=255)
    representante_socio_id = serializers.IntegerField(required=False)
    representante_modo = serializers.ChoiceField(
        choices=ModoRepresentacionComunidad.choices,
        required=False,
        default=ModoRepresentacionComunidad.DESIGNATED,
    )
    region = serializers.CharField(max_length=100, required=False)
    participaciones = ResolveMigrationPropertyOwnerParticipationSerializer(many=True, required=False)


class ResolveUnknownIncomeSerializer(serializers.Serializer):
    pago_mensual_id = serializers.IntegerField()
    periodo_economico = serializers.RegexField(
        regex=r'^\d{4}-(0[1-9]|1[0-2])$',
        required=True,
        error_messages={
            'required': 'La regularizacion manual requiere periodo economico.',
            'invalid': 'periodo_economico debe usar formato YYYY-MM.',
        },
    )
    criterio_aplicado = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La regularizacion manual requiere criterio aplicado.',
            'blank': 'La regularizacion manual requiere criterio aplicado.',
        },
    )
    evidencia_regularizacion_ref = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La regularizacion manual requiere evidencia no sensible.',
            'blank': 'La regularizacion manual requiere evidencia no sensible.',
        },
    )
    rationale = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            'required': 'La resolucion manual requiere un motivo auditable.',
            'blank': 'La resolucion manual requiere un motivo auditable.',
        },
    )

    def validate_pago_mensual_id(self, value):
        user = self.context['request'].user
        try:
            payment = PagoMensual.objects.select_related('contrato__mandato_operacion').get(pk=value)
        except PagoMensual.DoesNotExist as error:
            raise serializers.ValidationError('El pago mensual indicado no existe.') from error

        if not scope_queryset_for_user(
            PagoMensual.objects.filter(pk=value),
            user,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        ).exists():
            raise serializers.ValidationError('El pago mensual indicado queda fuera del scope asignado.')

        self.context['pago_mensual'] = payment
        return value

    def validate_evidencia_regularizacion_ref(self, value):
        if not is_non_sensitive_reference(value):
            raise serializers.ValidationError(
                'evidencia_regularizacion_ref debe ser una referencia no sensible, no una URL, token o credencial.'
            )
        return value

    def validate_criterio_aplicado(self, value):
        if contains_sensitive_reference(value):
            raise serializers.ValidationError(
                'criterio_aplicado no puede contener URLs, tokens, correos ni credenciales bancarias.'
            )
        return value

    def validate_rationale(self, value):
        if contains_sensitive_reference(value):
            raise serializers.ValidationError(
                'rationale no puede contener URLs, tokens, correos ni credenciales bancarias.'
            )
        return value


class ResolveChargeMovementSerializer(serializers.Serializer):
    categoria_movimiento = serializers.ChoiceField(
        choices=((CategoriaMovimiento.BANK_COMMISSION, 'Comision bancaria'),),
        error_messages={
            'required': 'La clasificacion manual requiere CategoriaMovimiento.',
            'invalid_choice': 'La categoria de movimiento indicada aun no tiene flujo de cierre seguro.',
        },
    )
    entidad_afectada_tipo = serializers.ChoiceField(
        choices=(('empresa', 'Empresa'),),
        error_messages={
            'required': 'La clasificacion manual requiere entidad afectada.',
            'invalid_choice': 'La entidad afectada indicada no es soportada para este cierre.',
        },
    )
    entidad_afectada_id = serializers.IntegerField(
        min_value=1,
        error_messages={'required': 'La clasificacion manual requiere entidad afectada.'},
    )
    periodo_economico = serializers.RegexField(
        regex=r'^\d{4}-(0[1-9]|1[0-2])$',
        required=True,
        error_messages={
            'required': 'La clasificacion manual requiere periodo economico.',
            'invalid': 'periodo_economico debe usar formato YYYY-MM.',
        },
    )
    criterio_reparto = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La clasificacion manual requiere criterio de reparto.',
            'blank': 'La clasificacion manual requiere criterio de reparto.',
        },
    )
    evidencia_clasificacion_ref = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La clasificacion manual requiere evidencia no sensible.',
            'blank': 'La clasificacion manual requiere evidencia no sensible.',
        },
    )
    rationale = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            'required': 'La resolucion manual requiere un motivo auditable.',
            'blank': 'La resolucion manual requiere un motivo auditable.',
        },
    )

    def validate_evidencia_clasificacion_ref(self, value):
        if not is_non_sensitive_reference(value):
            raise serializers.ValidationError(
                'evidencia_clasificacion_ref debe ser una referencia no sensible, no una URL, token o credencial.'
            )
        return value

    def validate_criterio_reparto(self, value):
        if contains_sensitive_reference(value):
            raise serializers.ValidationError(
                'criterio_reparto no puede contener URLs, tokens, correos ni credenciales bancarias.'
            )
        return value

    def validate_rationale(self, value):
        if contains_sensitive_reference(value):
            raise serializers.ValidationError(
                'rationale no puede contener URLs, tokens, correos ni credenciales bancarias.'
            )
        return value


class ResolveInternalTransferSerializer(serializers.Serializer):
    movimiento_destino_id = serializers.IntegerField(
        min_value=1,
        error_messages={'required': 'La transferencia interna requiere movimiento destino.'},
    )
    periodo_economico = serializers.RegexField(
        regex=r'^\d{4}-(0[1-9]|1[0-2])$',
        required=True,
        error_messages={
            'required': 'La transferencia interna requiere periodo economico.',
            'invalid': 'periodo_economico debe usar formato YYYY-MM.',
        },
    )
    criterio_conciliacion = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La transferencia interna requiere criterio de conciliacion.',
            'blank': 'La transferencia interna requiere criterio de conciliacion.',
        },
    )
    evidencia_transferencia_ref = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La transferencia interna requiere evidencia no sensible.',
            'blank': 'La transferencia interna requiere evidencia no sensible.',
        },
    )
    responsable_ref = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        max_length=255,
        error_messages={
            'required': 'La transferencia interna requiere responsable_ref no sensible.',
            'blank': 'La transferencia interna requiere responsable_ref no sensible.',
        },
    )
    rationale = serializers.CharField(
        required=True,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            'required': 'La resolucion manual requiere un motivo auditable.',
            'blank': 'La resolucion manual requiere un motivo auditable.',
        },
    )

    def validate_movimiento_destino_id(self, value):
        user = self.context['request'].user
        try:
            movement = MovimientoBancarioImportado.objects.select_related('conexion_bancaria').get(pk=value)
        except MovimientoBancarioImportado.DoesNotExist as error:
            raise serializers.ValidationError('El movimiento destino indicado no existe.') from error

        if not scope_queryset_for_user(
            MovimientoBancarioImportado.objects.filter(pk=value),
            user,
            bank_account_paths=('conexion_bancaria__cuenta_recaudadora_id',),
        ).exists():
            raise serializers.ValidationError('El movimiento destino queda fuera del scope asignado.')

        self.context['movimiento_destino'] = movement
        return value

    def validate_evidencia_transferencia_ref(self, value):
        if not is_non_sensitive_reference(value):
            raise serializers.ValidationError(
                'evidencia_transferencia_ref debe ser una referencia no sensible, no una URL, token o credencial.'
            )
        return value

    def validate_criterio_conciliacion(self, value):
        if contains_sensitive_reference(value):
            raise serializers.ValidationError(
                'criterio_conciliacion no puede contener URLs, tokens, correos ni credenciales bancarias.'
            )
        return value

    def validate_responsable_ref(self, value):
        if not is_non_sensitive_reference(value):
            raise serializers.ValidationError('responsable_ref debe ser una referencia no sensible.')
        return value

    def validate_rationale(self, value):
        if contains_sensitive_reference(value):
            raise serializers.ValidationError(
                'rationale no puede contener URLs, tokens, correos ni credenciales bancarias.'
            )
        return value
