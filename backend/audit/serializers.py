from rest_framework import serializers

from cobranza.models import PagoMensual
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
        return obj.actor_identifier or 'Sistema'


class ManualResolutionSerializer(serializers.ModelSerializer):
    requested_by_display = serializers.SerializerMethodField()
    resolved_by_display = serializers.SerializerMethodField()

    class Meta:
        model = ManualResolution
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'resolved_at')

    def get_requested_by_display(self, obj):
        if obj.requested_by_id:
            return obj.requested_by.display_name or obj.requested_by.username
        return ''

    def get_resolved_by_display(self, obj):
        if obj.resolved_by_id:
            return obj.resolved_by.display_name or obj.resolved_by.username
        return ''

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if (
            self.instance
            and self.instance.category in SPECIALIZED_MANUAL_RESOLUTION_CATEGORIES
            and attrs.get('status') == ManualResolution.Status.RESOLVED
            and self.instance.status != ManualResolution.Status.RESOLVED
        ):
            raise serializers.ValidationError(
                {'status': 'Use la resolución especializada correspondiente para cerrar este caso.'}
            )
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
    rationale = serializers.CharField(required=False, allow_blank=True)

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


class ResolveChargeMovementSerializer(serializers.Serializer):
    rationale = serializers.CharField(required=False, allow_blank=True)
