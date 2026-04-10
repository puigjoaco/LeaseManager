from rest_framework import serializers

from patrimonio.models import Empresa, ModoRepresentacionComunidad, Socio
from patrimonio.validators import validate_rut

from .models import AuditEvent, ManualResolution


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = '__all__'


class ManualResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManualResolution
        fields = '__all__'
        read_only_fields = ('id', 'created_at', 'resolved_at')


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
