from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

from patrimonio.models import ComunidadPatrimonial, Empresa, Propiedad, Socio

from .models import (
    AsignacionCanalOperacion,
    CanalOperacion,
    CuentaRecaudadora,
    IdentidadDeEnvio,
    MandatoOperacion,
)


def raise_drf_validation_error(error):
    if hasattr(error, 'message_dict'):
        raise serializers.ValidationError(error.message_dict)
    raise serializers.ValidationError(error.messages)


def build_validation_candidate(instance, model_class):
    if instance is None:
        return model_class()
    return model_class.objects.get(pk=instance.pk)


def resolve_simple_owner(owner_tipo, owner_id):
    model_map = {
        'empresa': Empresa,
        'socio': Socio,
    }
    model = model_map[owner_tipo]
    try:
        return model.objects.get(pk=owner_id)
    except model.DoesNotExist as exc:
        raise serializers.ValidationError({'owner_id': 'El owner indicado no existe.'}) from exc


def resolve_patrimonio_owner(owner_tipo, owner_id):
    model_map = {
        'empresa': Empresa,
        'comunidad': ComunidadPatrimonial,
        'socio': Socio,
    }
    model = model_map[owner_tipo]
    try:
        return model.objects.get(pk=owner_id)
    except model.DoesNotExist as exc:
        raise serializers.ValidationError({'propietario_id': 'El propietario indicado no existe.'}) from exc


class CuentaRecaudadoraSerializer(serializers.ModelSerializer):
    owner_tipo = serializers.ChoiceField(choices=('empresa', 'socio'), write_only=True, required=False)
    owner_id = serializers.IntegerField(write_only=True, required=False)
    owner_display = serializers.CharField(read_only=True)

    class Meta:
        model = CuentaRecaudadora
        fields = (
            'id',
            'institucion',
            'numero_cuenta',
            'tipo_cuenta',
            'titular_nombre',
            'titular_rut',
            'moneda_operativa',
            'estado_operativo',
            'owner_tipo',
            'owner_id',
            'owner_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'owner_display', 'created_at', 'updated_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['owner_tipo'] = instance.owner_tipo
        data['owner_id'] = instance.owner_id
        return data

    def validate(self, attrs):
        owner_tipo = attrs.pop('owner_tipo', None)
        owner_id = attrs.pop('owner_id', None)

        if self.instance and owner_tipo is None and owner_id is None:
            owner_tipo = self.instance.owner_tipo
            owner_id = self.instance.owner_id
        elif owner_tipo is None or owner_id is None:
            raise serializers.ValidationError('Debe enviar owner_tipo y owner_id.')

        owner = resolve_simple_owner(owner_tipo, owner_id)
        attrs['empresa_owner'] = owner if owner_tipo == 'empresa' else None
        attrs['socio_owner'] = owner if owner_tipo == 'socio' else None

        candidate = build_validation_candidate(self.instance, CuentaRecaudadora)
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class IdentidadDeEnvioSerializer(serializers.ModelSerializer):
    owner_tipo = serializers.ChoiceField(choices=('empresa', 'socio'), write_only=True, required=False)
    owner_id = serializers.IntegerField(write_only=True, required=False)
    owner_display = serializers.CharField(read_only=True)

    class Meta:
        model = IdentidadDeEnvio
        fields = (
            'id',
            'canal',
            'remitente_visible',
            'direccion_o_numero',
            'credencial_ref',
            'estado',
            'owner_tipo',
            'owner_id',
            'owner_display',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'owner_display', 'created_at', 'updated_at')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['owner_tipo'] = instance.owner_tipo
        data['owner_id'] = instance.owner_id
        return data

    def validate(self, attrs):
        owner_tipo = attrs.pop('owner_tipo', None)
        owner_id = attrs.pop('owner_id', None)

        if self.instance and owner_tipo is None and owner_id is None:
            owner_tipo = self.instance.owner_tipo
            owner_id = self.instance.owner_id
        elif owner_tipo is None or owner_id is None:
            raise serializers.ValidationError('Debe enviar owner_tipo y owner_id.')

        owner = resolve_simple_owner(owner_tipo, owner_id)
        attrs['empresa_owner'] = owner if owner_tipo == 'empresa' else None
        attrs['socio_owner'] = owner if owner_tipo == 'socio' else None

        canal = attrs.get('canal', getattr(self.instance, 'canal', None))
        direccion = attrs.get('direccion_o_numero', getattr(self.instance, 'direccion_o_numero', ''))
        if canal == CanalOperacion.EMAIL:
            try:
                EmailValidator()(direccion)
            except DjangoValidationError as error:
                raise_drf_validation_error(error)

        candidate = build_validation_candidate(self.instance, IdentidadDeEnvio)
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class MandatoOperacionSerializer(serializers.ModelSerializer):
    propiedad_id = serializers.PrimaryKeyRelatedField(source='propiedad', queryset=Propiedad.objects.all())
    propietario_tipo = serializers.ChoiceField(choices=('empresa', 'comunidad', 'socio'), write_only=True, required=False)
    propietario_id = serializers.IntegerField(write_only=True, required=False)
    administrador_operativo_tipo = serializers.ChoiceField(
        choices=('empresa', 'socio'),
        write_only=True,
        required=False,
    )
    administrador_operativo_id = serializers.IntegerField(write_only=True, required=False)
    recaudador_tipo = serializers.ChoiceField(
        choices=('empresa', 'socio'),
        write_only=True,
        required=False,
    )
    recaudador_id = serializers.IntegerField(write_only=True, required=False)
    entidad_facturadora_id = serializers.PrimaryKeyRelatedField(
        source='entidad_facturadora',
        queryset=Empresa.objects.all(),
        required=False,
        allow_null=True,
    )
    cuenta_recaudadora_id = serializers.PrimaryKeyRelatedField(
        source='cuenta_recaudadora',
        queryset=CuentaRecaudadora.objects.all(),
    )
    propiedad_codigo = serializers.CharField(source='propiedad.codigo_propiedad', read_only=True)
    propietario_display = serializers.SerializerMethodField(read_only=True)
    administrador_operativo_display = serializers.SerializerMethodField(read_only=True)
    recaudador_display = serializers.SerializerMethodField(read_only=True)
    entidad_facturadora_display = serializers.CharField(source='entidad_facturadora.razon_social', read_only=True)
    cuenta_recaudadora_display = serializers.CharField(source='cuenta_recaudadora.numero_cuenta', read_only=True)

    class Meta:
        model = MandatoOperacion
        fields = (
            'id',
            'propiedad_id',
            'propiedad_codigo',
            'propietario_tipo',
            'propietario_id',
            'propietario_display',
            'administrador_operativo_tipo',
            'administrador_operativo_id',
            'administrador_operativo_display',
            'recaudador_tipo',
            'recaudador_id',
            'recaudador_display',
            'entidad_facturadora_id',
            'entidad_facturadora_display',
            'cuenta_recaudadora_id',
            'cuenta_recaudadora_display',
            'tipo_relacion_operativa',
            'autoriza_recaudacion',
            'autoriza_facturacion',
            'autoriza_comunicacion',
            'vigencia_desde',
            'vigencia_hasta',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'propiedad_codigo',
            'propietario_display',
            'administrador_operativo_display',
            'recaudador_display',
            'entidad_facturadora_display',
            'cuenta_recaudadora_display',
            'created_at',
            'updated_at',
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['propietario_tipo'] = instance.propietario_tipo
        data['propietario_id'] = instance.propietario_id
        data['administrador_operativo_tipo'] = instance.administrador_operativo_tipo
        data['administrador_operativo_id'] = instance.administrador_operativo_id
        data['recaudador_tipo'] = instance.recaudador_tipo
        data['recaudador_id'] = instance.recaudador_id
        return data

    def get_propietario_display(self, obj):
        if obj.propietario_empresa_owner_id:
            return obj.propietario_empresa_owner.razon_social
        if obj.propietario_comunidad_owner_id:
            return obj.propietario_comunidad_owner.nombre
        return obj.propietario_socio_owner.nombre

    def get_administrador_operativo_display(self, obj):
        if obj.administrador_empresa_owner_id:
            return obj.administrador_empresa_owner.razon_social
        return obj.administrador_socio_owner.nombre

    def get_recaudador_display(self, obj):
        if obj.recaudador_empresa_owner_id:
            return obj.recaudador_empresa_owner.razon_social
        return obj.recaudador_socio_owner.nombre

    def validate(self, attrs):
        propietario_tipo = attrs.pop('propietario_tipo', None)
        propietario_id = attrs.pop('propietario_id', None)
        admin_tipo = attrs.pop('administrador_operativo_tipo', None)
        admin_id = attrs.pop('administrador_operativo_id', None)
        recaudador_tipo = attrs.pop('recaudador_tipo', None)
        recaudador_id = attrs.pop('recaudador_id', None)

        if self.instance and propietario_tipo is None and propietario_id is None:
            propietario_tipo = self.instance.propietario_tipo
            propietario_id = self.instance.propietario_id
        elif propietario_tipo is None or propietario_id is None:
            raise serializers.ValidationError('Debe enviar propietario_tipo y propietario_id.')

        if self.instance and admin_tipo is None and admin_id is None:
            admin_tipo = self.instance.administrador_operativo_tipo
            admin_id = self.instance.administrador_operativo_id
        elif admin_tipo is None or admin_id is None:
            raise serializers.ValidationError(
                'Debe enviar administrador_operativo_tipo y administrador_operativo_id.'
            )

        if self.instance and recaudador_tipo is None and recaudador_id is None:
            recaudador_tipo = self.instance.recaudador_tipo
            recaudador_id = self.instance.recaudador_id
        elif recaudador_tipo is None or recaudador_id is None:
            raise serializers.ValidationError('Debe enviar recaudador_tipo y recaudador_id.')

        propietario = resolve_patrimonio_owner(propietario_tipo, propietario_id)
        admin = resolve_simple_owner(admin_tipo, admin_id)
        recaudador = resolve_simple_owner(recaudador_tipo, recaudador_id)

        attrs['propietario_empresa_owner'] = propietario if propietario_tipo == 'empresa' else None
        attrs['propietario_comunidad_owner'] = propietario if propietario_tipo == 'comunidad' else None
        attrs['propietario_socio_owner'] = propietario if propietario_tipo == 'socio' else None
        attrs['administrador_empresa_owner'] = admin if admin_tipo == 'empresa' else None
        attrs['administrador_socio_owner'] = admin if admin_tipo == 'socio' else None
        attrs['recaudador_empresa_owner'] = recaudador if recaudador_tipo == 'empresa' else None
        attrs['recaudador_socio_owner'] = recaudador if recaudador_tipo == 'socio' else None

        candidate = build_validation_candidate(self.instance, MandatoOperacion)
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs


class AsignacionCanalOperacionSerializer(serializers.ModelSerializer):
    mandato_operacion_id = serializers.PrimaryKeyRelatedField(
        source='mandato_operacion',
        queryset=MandatoOperacion.objects.all(),
    )
    identidad_envio_id = serializers.PrimaryKeyRelatedField(
        source='identidad_envio',
        queryset=IdentidadDeEnvio.objects.all(),
    )
    identidad_envio_display = serializers.CharField(source='identidad_envio.remitente_visible', read_only=True)

    class Meta:
        model = AsignacionCanalOperacion
        fields = (
            'id',
            'mandato_operacion_id',
            'canal',
            'identidad_envio_id',
            'identidad_envio_display',
            'prioridad',
            'estado',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'identidad_envio_display', 'created_at', 'updated_at')

    def validate(self, attrs):
        candidate = build_validation_candidate(self.instance, AsignacionCanalOperacion)
        for field, value in attrs.items():
            setattr(candidate, field, value)

        try:
            candidate.full_clean()
        except DjangoValidationError as error:
            raise_drf_validation_error(error)
        return attrs
