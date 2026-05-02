from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from core.scope_access import scope_queryset_for_user

from .models import (
    ComunidadPatrimonial,
    Empresa,
    EstadoPatrimonial,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
)
from .validators import validate_rut


ACTIVE_TOTAL = Decimal('100.00')
SOCIO_SCOPE_PATHS = (
    'propiedades_directas__id',
    'representaciones_comunidad__comunidad__propiedades__id',
    'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
    'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
)


def _request_user(serializer):
    request = serializer.context.get('request')
    return getattr(request, 'user', None)


class SocioSerializer(serializers.ModelSerializer):
    def validate_rut(self, value):
        normalized = validate_rut(value)
        queryset = Socio.objects.filter(rut=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe un socio con ese RUT.')
        return normalized

    class Meta:
        model = Socio
        fields = (
            'id',
            'nombre',
            'rut',
            'email',
            'telefono',
            'domicilio',
            'activo',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class ParticipacionPatrimonialReadSerializer(serializers.ModelSerializer):
    participante_tipo = serializers.CharField(read_only=True)
    participante_id = serializers.IntegerField(read_only=True)
    participante_nombre = serializers.CharField(source='participante_display', read_only=True)
    participante_rut = serializers.CharField(read_only=True)
    owner_tipo = serializers.CharField(read_only=True)
    owner_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = ParticipacionPatrimonial
        fields = (
            'id',
            'participante_tipo',
            'participante_id',
            'participante_nombre',
            'participante_rut',
            'owner_tipo',
            'owner_id',
            'porcentaje',
            'vigente_desde',
            'vigente_hasta',
            'activo',
            'created_at',
            'updated_at',
        )


class ParticipacionPatrimonialWriteSerializer(serializers.Serializer):
    participante_tipo = serializers.ChoiceField(choices=('socio', 'empresa'))
    participante_id = serializers.IntegerField()
    porcentaje = serializers.DecimalField(max_digits=5, decimal_places=2)
    vigente_desde = serializers.DateField(required=False, default=timezone.localdate)
    vigente_hasta = serializers.DateField(required=False, allow_null=True)
    activo = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        if attrs.get('vigente_hasta') and attrs['vigente_hasta'] < attrs['vigente_desde']:
            raise serializers.ValidationError(
                {'vigente_hasta': 'La vigencia final no puede ser anterior a la inicial.'}
            )
        participante_tipo = attrs['participante_tipo']
        participante_id = attrs['participante_id']
        model = Socio if participante_tipo == 'socio' else Empresa
        try:
            participante = model.objects.get(pk=participante_id)
        except model.DoesNotExist as error:
            raise serializers.ValidationError({'participante_id': 'El participante indicado no existe.'}) from error

        attrs['participante_socio'] = participante if participante_tipo == 'socio' else None
        attrs['participante_empresa'] = participante if participante_tipo == 'empresa' else None
        return attrs


class RepresentacionComunidadReadSerializer(serializers.ModelSerializer):
    socio_representante_id = serializers.IntegerField(read_only=True)
    socio_representante_nombre = serializers.CharField(source='socio_representante.nombre', read_only=True)
    socio_representante_rut = serializers.CharField(source='socio_representante.rut', read_only=True)

    class Meta:
        model = RepresentacionComunidad
        fields = (
            'id',
            'modo_representacion',
            'socio_representante_id',
            'socio_representante_nombre',
            'socio_representante_rut',
            'vigente_desde',
            'vigente_hasta',
            'activo',
            'observaciones',
            'created_at',
            'updated_at',
        )


class OwnerBaseSerializer(serializers.ModelSerializer):
    participaciones = ParticipacionPatrimonialWriteSerializer(many=True, required=False, write_only=True)
    participaciones_detail = serializers.SerializerMethodField(read_only=True)

    owner_label = ''

    def get_participaciones_detail(self, obj):
        return ParticipacionPatrimonialReadSerializer(
            obj.participaciones.all(),
            many=True,
        ).data

    def _get_participaciones_payload(self, attrs):
        if 'participaciones' in attrs:
            return attrs['participaciones']
        if not self.instance:
            return []
        payload = []
        for participacion in self.instance.participaciones.all():
            payload.append(
                {
                    'participante_tipo': participacion.participante_tipo,
                    'participante_id': participacion.participante_id,
                    'participante_socio': participacion.participante_socio,
                    'participante_empresa': participacion.participante_empresa,
                    'porcentaje': participacion.porcentaje,
                    'vigente_desde': participacion.vigente_desde,
                    'vigente_hasta': participacion.vigente_hasta,
                    'activo': participacion.activo,
                }
            )
        return payload

    def _get_active_total(self, participaciones):
        today = timezone.localdate()
        total = Decimal('0.00')
        for participacion in participaciones:
            vigente_hasta = participacion.get('vigente_hasta')
            if participacion.get('activo', True) and (vigente_hasta is None or vigente_hasta >= today):
                total += Decimal(participacion['porcentaje'])
        return total

    def _validate_no_duplicate_participantes(self, participaciones):
        participant_keys = []
        for participacion in participaciones:
            if participacion.get('participante_socio'):
                participant_keys.append(('socio', participacion['participante_socio'].id))
            elif participacion.get('participante_empresa'):
                participant_keys.append(('empresa', participacion['participante_empresa'].id))
            else:
                participant_keys.append((participacion['participante_tipo'], participacion['participante_id']))
        if len(participant_keys) != len(set(participant_keys)):
            raise serializers.ValidationError(
                {'participaciones': 'No se puede repetir un participante activo en el mismo set.'}
            )

    def _validate_activation_requirements(self, attrs, participaciones):
        estado = attrs.get('estado', getattr(self.instance, 'estado', EstadoPatrimonial.DRAFT))
        if estado != EstadoPatrimonial.ACTIVE:
            return

        total = self._get_active_total(participaciones)
        if total != ACTIVE_TOTAL:
            raise serializers.ValidationError(
                {'participaciones': 'Las participaciones activas deben sumar exactamente 100.00 para activar el owner.'}
            )

    def _validate_allowed_participants(self, owner_model, participaciones):
        if owner_model is Empresa:
            invalid = [item for item in participaciones if item['participante_tipo'] != 'socio']
            if invalid:
                raise serializers.ValidationError(
                    {'participaciones': 'Las empresas solo pueden tener socios como participantes patrimoniales.'}
                )

    def _sync_participaciones(self, owner, participaciones):
        if participaciones is None:
            return

        owner.participaciones.all().delete()
        items = []
        for participacion in participaciones:
            item_data = {
                'participante_socio': participacion.get('participante_socio'),
                'participante_empresa': participacion.get('participante_empresa'),
                'porcentaje': participacion['porcentaje'],
                'vigente_desde': participacion['vigente_desde'],
                'vigente_hasta': participacion.get('vigente_hasta'),
                'activo': participacion.get('activo', True),
            }
            if isinstance(owner, Empresa):
                item_data['empresa_owner'] = owner
            else:
                item_data['comunidad_owner'] = owner
            items.append(ParticipacionPatrimonial(**item_data))

        ParticipacionPatrimonial.objects.bulk_create(items)

    def create(self, validated_data):
        participaciones = validated_data.pop('participaciones', None)
        with transaction.atomic():
            instance = super().create(validated_data)
            self._sync_participaciones(instance, participaciones)
        return instance

    def update(self, instance, validated_data):
        participaciones = validated_data.pop('participaciones', None)
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            self._sync_participaciones(instance, participaciones)
        return instance


class EmpresaSerializer(OwnerBaseSerializer):
    participaciones_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Empresa
        fields = (
            'id',
            'razon_social',
            'rut',
            'domicilio',
            'giro',
            'codigo_actividad_sii',
            'estado',
            'participaciones',
            'participaciones_detail',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'participaciones_detail')

    def validate_rut(self, value):
        normalized = validate_rut(value)
        queryset = Empresa.objects.filter(rut=normalized)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('Ya existe una empresa con ese RUT.')
        return normalized

    def validate(self, attrs):
        participaciones = self._get_participaciones_payload(attrs)
        self._validate_no_duplicate_participantes(participaciones)
        self._validate_allowed_participants(Empresa, participaciones)
        self._validate_activation_requirements(attrs, participaciones)
        return attrs


class ComunidadPatrimonialSerializer(OwnerBaseSerializer):
    participaciones_detail = serializers.SerializerMethodField(read_only=True)
    representante_modo = serializers.ChoiceField(
        choices=ModoRepresentacionComunidad.choices,
        required=False,
        write_only=True,
    )
    representante_socio_id = serializers.PrimaryKeyRelatedField(
        source='representante_socio_obj',
        queryset=Socio.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    representacion_vigente = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ComunidadPatrimonial
        fields = (
            'id',
            'nombre',
            'representante_modo',
            'representante_socio_id',
            'representacion_vigente',
            'estado',
            'participaciones',
            'participaciones_detail',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'participaciones_detail')

    def get_representacion_vigente(self, obj):
        cached = getattr(obj, '_prefetched_objects_cache', {})
        representaciones = cached.get('representaciones')
        if representaciones is not None:
            today = timezone.localdate()
            activas = [
                item for item in representaciones
                if item.activo and (item.vigente_hasta is None or item.vigente_hasta >= today)
            ]
            activas.sort(key=lambda item: (item.vigente_desde, item.id), reverse=True)
            representacion = activas[0] if activas else None
        else:
            representacion = obj.representacion_vigente()
        if not representacion:
            return None
        return RepresentacionComunidadReadSerializer(representacion).data

    def validate(self, attrs):
        participaciones = self._get_participaciones_payload(attrs)
        self._validate_no_duplicate_participantes(participaciones)
        self._validate_allowed_participants(ComunidadPatrimonial, participaciones)
        self._validate_activation_requirements(attrs, participaciones)

        estado = attrs.get('estado', getattr(self.instance, 'estado', EstadoPatrimonial.DRAFT))
        representante_modo = attrs.pop('representante_modo', None)
        representante = attrs.pop('representante_socio_obj', None)
        explicit_representation_change = (
            'representante_modo' in getattr(self, 'initial_data', {})
            or 'representante_socio_id' in getattr(self, 'initial_data', {})
        )

        current_representation = self.instance.representacion_vigente() if self.instance else None
        if self.instance and representante_modo is None and current_representation:
            representante_modo = current_representation.modo_representacion
        if self.instance and representante is None and current_representation:
            representante = current_representation.socio_representante

        attrs['_representante_modo'] = representante_modo
        attrs['_representante_socio'] = representante
        attrs['_sync_representacion'] = explicit_representation_change or (self.instance is None and representante is not None)

        if estado == EstadoPatrimonial.ACTIVE:
            if representante is None or representante_modo is None:
                raise serializers.ValidationError(
                    {'representacion_vigente': 'La comunidad activa debe tener una representacion vigente.'}
                )

            active_socio_ids = {
                participacion['participante_socio'].id
                for participacion in participaciones
                if participacion.get('participante_socio')
                if participacion.get('activo', True)
                and (participacion.get('vigente_hasta') is None or participacion.get('vigente_hasta') >= timezone.localdate())
            }
            if representante_modo == ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT and representante.id not in active_socio_ids:
                raise serializers.ValidationError(
                    {'representacion_vigente': 'La representacion patrimonial debe pertenecer a las participaciones activas de la comunidad.'}
                )
            if not representante.activo:
                raise serializers.ValidationError({'representacion_vigente': 'La representacion activa requiere un socio activo.'})
        return attrs

    def _sync_representacion(self, comunidad, *, representante_modo=None, representante=None):
        if representante_modo is None and representante is None:
            return

        comunidad.representaciones.filter(activo=True).update(activo=False)
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=representante_modo,
            socio_representante=representante,
            vigente_desde=timezone.localdate(),
            activo=True,
        )

    def create(self, validated_data):
        participaciones = validated_data.pop('participaciones', None)
        representante_modo = validated_data.pop('_representante_modo', None)
        representante = validated_data.pop('_representante_socio', None)
        sync_representacion = validated_data.pop('_sync_representacion', False)
        with transaction.atomic():
            requested_state = validated_data.get('estado', EstadoPatrimonial.DRAFT)
            if requested_state == EstadoPatrimonial.ACTIVE:
                validated_data['estado'] = EstadoPatrimonial.DRAFT
            instance = ComunidadPatrimonial.objects.create(**validated_data)
            self._sync_participaciones(instance, participaciones)
            if sync_representacion:
                self._sync_representacion(instance, representante_modo=representante_modo, representante=representante)
            if requested_state == EstadoPatrimonial.ACTIVE:
                instance.estado = EstadoPatrimonial.ACTIVE
                instance.save(update_fields=['estado', 'updated_at'])
        return instance

    def update(self, instance, validated_data):
        participaciones = validated_data.pop('participaciones', None)
        representante_modo = validated_data.pop('_representante_modo', None)
        representante = validated_data.pop('_representante_socio', None)
        sync_representacion = validated_data.pop('_sync_representacion', False)
        with transaction.atomic():
            requested_state = validated_data.get('estado', instance.estado)
            if requested_state == EstadoPatrimonial.ACTIVE:
                validated_data['estado'] = EstadoPatrimonial.DRAFT
            instance = serializers.ModelSerializer.update(self, instance, validated_data)
            self._sync_participaciones(instance, participaciones)
            if sync_representacion:
                self._sync_representacion(instance, representante_modo=representante_modo, representante=representante)
            if requested_state == EstadoPatrimonial.ACTIVE:
                instance.estado = EstadoPatrimonial.ACTIVE
                instance.save(update_fields=['estado', 'updated_at'])
        return instance


class PropiedadSerializer(serializers.ModelSerializer):
    owner_tipo = serializers.ChoiceField(choices=('empresa', 'comunidad', 'socio'), write_only=True, required=False)
    owner_id = serializers.IntegerField(write_only=True, required=False)
    owner_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Propiedad
        fields = (
            'id',
            'rol_avaluo',
            'direccion',
            'comuna',
            'region',
            'tipo_inmueble',
            'codigo_propiedad',
            'estado',
            'owner_tipo',
            'owner_id',
            'owner_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'owner_display')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['owner_tipo'] = instance.owner_tipo
        data['owner_id'] = instance.owner_id
        return data

    def get_owner_display(self, obj):
        if obj.empresa_owner_id:
            return obj.empresa_owner.razon_social
        if obj.comunidad_owner_id:
            return obj.comunidad_owner.nombre
        return obj.socio_owner.nombre

    def validate(self, attrs):
        user = _request_user(self)
        owner_tipo = attrs.pop('owner_tipo', None)
        owner_id = attrs.pop('owner_id', None)

        if self.instance and owner_tipo is None and owner_id is None:
            owner_tipo = self.instance.owner_tipo
            owner_id = self.instance.owner_id
            owner = self._current_owner()
        elif self.instance and owner_tipo == self.instance.owner_tipo and owner_id == self.instance.owner_id:
            owner = self._current_owner()
        elif owner_tipo is None or owner_id is None:
            raise serializers.ValidationError('Debe enviar owner_tipo y owner_id.')
        else:
            owner = self._resolve_owner(owner_tipo, owner_id, user=user)
        attrs['empresa_owner'] = owner if owner_tipo == 'empresa' else None
        attrs['comunidad_owner'] = owner if owner_tipo == 'comunidad' else None
        attrs['socio_owner'] = owner if owner_tipo == 'socio' else None

        estado = attrs.get('estado', getattr(self.instance, 'estado', EstadoPatrimonial.DRAFT))
        if estado == EstadoPatrimonial.ACTIVE:
            self._validate_active_owner(owner_tipo, owner)

        codigo_propiedad = attrs.get('codigo_propiedad', getattr(self.instance, 'codigo_propiedad', None))
        self._validate_codigo_unique(owner_tipo, owner.id, codigo_propiedad)
        return attrs

    def _current_owner(self):
        if self.instance.empresa_owner_id:
            return self.instance.empresa_owner
        if self.instance.comunidad_owner_id:
            return self.instance.comunidad_owner
        return self.instance.socio_owner

    def _resolve_owner(self, owner_tipo, owner_id, *, user=None):
        queryset_map = {
            'empresa': scope_queryset_for_user(Empresa.objects.all(), user, company_paths=('id',)) if user else Empresa.objects.all(),
            'comunidad': scope_queryset_for_user(
                ComunidadPatrimonial.objects.all(),
                user,
                property_paths=('propiedades__id',),
            ) if user else ComunidadPatrimonial.objects.all(),
            'socio': scope_queryset_for_user(Socio.objects.all(), user, property_paths=SOCIO_SCOPE_PATHS) if user else Socio.objects.all(),
        }
        queryset = queryset_map[owner_tipo]
        try:
            return queryset.get(pk=owner_id)
        except queryset.model.DoesNotExist as error:
            raise serializers.ValidationError(
                {'owner_id': 'El owner indicado no existe o queda fuera del scope asignado.'}
            ) from error

    def _validate_active_owner(self, owner_tipo, owner):
        if owner_tipo == 'empresa':
            if owner.estado != EstadoPatrimonial.ACTIVE or not owner.participaciones_completas():
                raise serializers.ValidationError(
                    {'owner_id': 'La propiedad activa requiere una empresa activa con participaciones completas.'}
                )
        elif owner_tipo == 'comunidad':
            if owner.estado != EstadoPatrimonial.ACTIVE or not owner.participaciones_completas():
                raise serializers.ValidationError(
                    {'owner_id': 'La propiedad activa requiere una comunidad activa con participaciones completas.'}
                )
        elif owner_tipo == 'socio' and not owner.activo:
            raise serializers.ValidationError({'owner_id': 'La propiedad activa requiere un socio activo.'})

    def _validate_codigo_unique(self, owner_tipo, owner_id, codigo_propiedad):
        queryset = Propiedad.objects.filter(codigo_propiedad=codigo_propiedad)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        filters = {
            'empresa': {'empresa_owner_id': owner_id},
            'comunidad': {'comunidad_owner_id': owner_id},
            'socio': {'socio_owner_id': owner_id},
        }[owner_tipo]
        if queryset.filter(**filters).exists():
            raise serializers.ValidationError(
                {'codigo_propiedad': 'El codigo_propiedad debe ser unico dentro del owner indicado.'}
            )
