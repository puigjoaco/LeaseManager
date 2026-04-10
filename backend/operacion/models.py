from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from patrimonio.models import ComunidadPatrimonial, Empresa, Propiedad, Socio
from patrimonio.validators import normalize_rut, validate_rut


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoCuentaRecaudadora(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ACTIVE = 'activa', 'Activa'
    PAUSED = 'pausada', 'Pausada'
    INACTIVE = 'inactiva', 'Inactiva'


class EstadoIdentidadEnvio(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ACTIVE = 'activa', 'Activa'
    SUSPENDED = 'suspendida', 'Suspendida'
    INACTIVE = 'inactiva', 'Inactiva'


class EstadoMandatoOperacion(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class EstadoAsignacionCanal(models.TextChoices):
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class CanalOperacion(models.TextChoices):
    EMAIL = 'email', 'Email'
    WHATSAPP = 'whatsapp', 'WhatsApp'


class MonedaOperativa(models.TextChoices):
    CLP = 'CLP', 'CLP'
    UF = 'UF', 'UF'


def owner_tuple(*, empresa_id=None, socio_id=None):
    if empresa_id:
        return ('empresa', empresa_id)
    if socio_id:
        return ('socio', socio_id)
    return (None, None)


def patrimonio_owner_tuple(*, empresa_id=None, comunidad_id=None, socio_id=None):
    if empresa_id:
        return ('empresa', empresa_id)
    if comunidad_id:
        return ('comunidad', comunidad_id)
    if socio_id:
        return ('socio', socio_id)
    return (None, None)


class CuentaRecaudadora(TimestampedModel):
    empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='cuentas_recaudadoras',
    )
    socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='cuentas_recaudadoras',
    )
    institucion = models.CharField(max_length=120)
    numero_cuenta = models.CharField(max_length=64)
    tipo_cuenta = models.CharField(max_length=64)
    titular_nombre = models.CharField(max_length=255)
    titular_rut = models.CharField(max_length=16, validators=[validate_rut])
    moneda_operativa = models.CharField(max_length=8, choices=MonedaOperativa.choices, default=MonedaOperativa.CLP)
    estado_operativo = models.CharField(
        max_length=16,
        choices=EstadoCuentaRecaudadora.choices,
        default=EstadoCuentaRecaudadora.DRAFT,
    )

    class Meta:
        ordering = ['institucion', 'numero_cuenta']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(empresa_owner__isnull=False, socio_owner__isnull=True)
                    | Q(empresa_owner__isnull=True, socio_owner__isnull=False)
                ),
                name='cuenta_recaudadora_exactly_one_owner',
            ),
            models.UniqueConstraint(
                fields=['institucion', 'numero_cuenta'],
                name='uniq_cuenta_recaudadora_por_institucion_numero',
            ),
        ]

    def __str__(self):
        return f'{self.institucion} {self.numero_cuenta}'

    @property
    def owner_tipo(self):
        return owner_tuple(empresa_id=self.empresa_owner_id, socio_id=self.socio_owner_id)[0]

    @property
    def owner_id(self):
        return owner_tuple(empresa_id=self.empresa_owner_id, socio_id=self.socio_owner_id)[1]

    @property
    def owner_display(self):
        if self.empresa_owner_id:
            return self.empresa_owner.razon_social
        return self.socio_owner.nombre

    def owner_is_active(self):
        if self.empresa_owner_id:
            return self.empresa_owner.estado == 'activa'
        return self.socio_owner.activo

    def save(self, *args, **kwargs):
        self.titular_rut = normalize_rut(self.titular_rut)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if sum(bool(value) for value in (self.empresa_owner_id, self.socio_owner_id)) != 1:
            raise ValidationError('La cuenta recaudadora debe pertenecer exactamente a una empresa o socio.')

        if self.estado_operativo == EstadoCuentaRecaudadora.ACTIVE and not self.owner_is_active():
            raise ValidationError({'estado_operativo': 'La cuenta activa requiere un owner activo.'})


class IdentidadDeEnvio(TimestampedModel):
    empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='identidades_envio',
    )
    socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='identidades_envio',
    )
    canal = models.CharField(max_length=16, choices=CanalOperacion.choices)
    remitente_visible = models.CharField(max_length=255)
    direccion_o_numero = models.CharField(max_length=255)
    credencial_ref = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoIdentidadEnvio.choices, default=EstadoIdentidadEnvio.DRAFT)

    class Meta:
        ordering = ['canal', 'remitente_visible']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(empresa_owner__isnull=False, socio_owner__isnull=True)
                    | Q(empresa_owner__isnull=True, socio_owner__isnull=False)
                ),
                name='identidad_envio_exactly_one_owner',
            ),
            models.UniqueConstraint(
                fields=['canal', 'direccion_o_numero'],
                name='uniq_identidad_envio_por_canal_direccion',
            ),
        ]

    def __str__(self):
        return f'{self.get_canal_display()} - {self.remitente_visible}'

    @property
    def owner_tipo(self):
        return owner_tuple(empresa_id=self.empresa_owner_id, socio_id=self.socio_owner_id)[0]

    @property
    def owner_id(self):
        return owner_tuple(empresa_id=self.empresa_owner_id, socio_id=self.socio_owner_id)[1]

    @property
    def owner_display(self):
        if self.empresa_owner_id:
            return self.empresa_owner.razon_social
        return self.socio_owner.nombre

    def owner_is_active(self):
        if self.empresa_owner_id:
            return self.empresa_owner.estado == 'activa'
        return self.socio_owner.activo

    def clean(self):
        super().clean()
        if sum(bool(value) for value in (self.empresa_owner_id, self.socio_owner_id)) != 1:
            raise ValidationError('La identidad de envio debe pertenecer exactamente a una empresa o socio.')

        if self.estado == EstadoIdentidadEnvio.ACTIVE:
            if not self.credencial_ref:
                raise ValidationError({'credencial_ref': 'La identidad activa requiere una referencia de credencial.'})
            if not self.owner_is_active():
                raise ValidationError({'estado': 'La identidad activa requiere un owner activo.'})


class MandatoOperacion(TimestampedModel):
    propiedad = models.ForeignKey(Propiedad, on_delete=models.PROTECT, related_name='mandatos_operacion')
    propietario_empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_propietaria',
    )
    propietario_comunidad_owner = models.ForeignKey(
        ComunidadPatrimonial,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_propietaria',
    )
    propietario_socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_propietario',
    )
    administrador_empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_administradora',
    )
    administrador_socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_administrador',
    )
    recaudador_empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_recaudadora',
    )
    recaudador_socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_recaudador',
    )
    entidad_facturadora = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='mandatos_como_facturadora',
    )
    cuenta_recaudadora = models.ForeignKey(
        CuentaRecaudadora,
        on_delete=models.PROTECT,
        related_name='mandatos_operacion',
    )
    tipo_relacion_operativa = models.CharField(max_length=64)
    autoriza_recaudacion = models.BooleanField(default=False)
    autoriza_facturacion = models.BooleanField(default=False)
    autoriza_comunicacion = models.BooleanField(default=False)
    vigencia_desde = models.DateField(default=timezone.localdate)
    vigencia_hasta = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoMandatoOperacion.choices, default=EstadoMandatoOperacion.DRAFT)

    class Meta:
        ordering = ['propiedad__codigo_propiedad', '-vigencia_desde']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(propietario_empresa_owner__isnull=False, propietario_comunidad_owner__isnull=True, propietario_socio_owner__isnull=True)
                    | Q(propietario_empresa_owner__isnull=True, propietario_comunidad_owner__isnull=False, propietario_socio_owner__isnull=True)
                    | Q(propietario_empresa_owner__isnull=True, propietario_comunidad_owner__isnull=True, propietario_socio_owner__isnull=False)
                ),
                name='mandato_exactly_one_propietario',
            ),
            models.CheckConstraint(
                check=(
                    Q(administrador_empresa_owner__isnull=False, administrador_socio_owner__isnull=True)
                    | Q(administrador_empresa_owner__isnull=True, administrador_socio_owner__isnull=False)
                ),
                name='mandato_exactly_one_administrador',
            ),
            models.CheckConstraint(
                check=(
                    Q(recaudador_empresa_owner__isnull=False, recaudador_socio_owner__isnull=True)
                    | Q(recaudador_empresa_owner__isnull=True, recaudador_socio_owner__isnull=False)
                ),
                name='mandato_exactly_one_recaudador',
            ),
            models.UniqueConstraint(
                fields=['propiedad'],
                condition=Q(estado='activa'),
                name='uniq_mandato_operacion_activo_por_propiedad',
            ),
        ]

    def __str__(self):
        return f'Mandato {self.propiedad.codigo_propiedad}'

    @property
    def propietario_tipo(self):
        return patrimonio_owner_tuple(
            empresa_id=self.propietario_empresa_owner_id,
            comunidad_id=self.propietario_comunidad_owner_id,
            socio_id=self.propietario_socio_owner_id,
        )[0]

    @property
    def propietario_id(self):
        return patrimonio_owner_tuple(
            empresa_id=self.propietario_empresa_owner_id,
            comunidad_id=self.propietario_comunidad_owner_id,
            socio_id=self.propietario_socio_owner_id,
        )[1]

    @property
    def administrador_operativo_tipo(self):
        return owner_tuple(
            empresa_id=self.administrador_empresa_owner_id,
            socio_id=self.administrador_socio_owner_id,
        )[0]

    @property
    def administrador_operativo_id(self):
        return owner_tuple(
            empresa_id=self.administrador_empresa_owner_id,
            socio_id=self.administrador_socio_owner_id,
        )[1]

    @property
    def recaudador_tipo(self):
        return owner_tuple(
            empresa_id=self.recaudador_empresa_owner_id,
            socio_id=self.recaudador_socio_owner_id,
        )[0]

    @property
    def recaudador_id(self):
        return owner_tuple(
            empresa_id=self.recaudador_empresa_owner_id,
            socio_id=self.recaudador_socio_owner_id,
        )[1]

    def propietario_tuple(self):
        return (self.propietario_tipo, self.propietario_id)

    def administrador_tuple(self):
        return (self.administrador_operativo_tipo, self.administrador_operativo_id)

    def recaudador_tuple(self):
        return (self.recaudador_tipo, self.recaudador_id)

    def facturadora_tuple(self):
        if self.entidad_facturadora_id:
            return ('empresa', self.entidad_facturadora_id)
        return (None, None)

    def property_owner_tuple(self):
        return patrimonio_owner_tuple(
            empresa_id=self.propiedad.empresa_owner_id,
            comunidad_id=self.propiedad.comunidad_owner_id,
            socio_id=self.propiedad.socio_owner_id,
        )

    def clean(self):
        super().clean()
        if self.vigencia_hasta and self.vigencia_hasta < self.vigencia_desde:
            raise ValidationError({'vigencia_hasta': 'La vigencia final no puede ser anterior a la inicial.'})

        if sum(
            bool(value)
            for value in (
                self.propietario_empresa_owner_id,
                self.propietario_comunidad_owner_id,
                self.propietario_socio_owner_id,
            )
        ) != 1:
            raise ValidationError('El mandato debe declarar exactamente un propietario.')

        if sum(bool(value) for value in (self.administrador_empresa_owner_id, self.administrador_socio_owner_id)) != 1:
            raise ValidationError('El mandato debe declarar exactamente un administrador operativo.')

        if sum(bool(value) for value in (self.recaudador_empresa_owner_id, self.recaudador_socio_owner_id)) != 1:
            raise ValidationError('El mandato debe declarar exactamente un recaudador.')

        if self.property_owner_tuple() != self.propietario_tuple():
            raise ValidationError({'propiedad': 'El propietario declarado debe coincidir con el owner de la propiedad.'})

        if self.autoriza_facturacion and not self.entidad_facturadora_id:
            raise ValidationError({'entidad_facturadora': 'No se puede autorizar facturacion sin entidad facturadora.'})

        if self.estado != EstadoMandatoOperacion.ACTIVE:
            return

        if self.propiedad.estado != 'activa':
            raise ValidationError({'estado': 'El mandato activo requiere una propiedad activa.'})

        if self.cuenta_recaudadora.estado_operativo != EstadoCuentaRecaudadora.ACTIVE:
            raise ValidationError({'cuenta_recaudadora': 'El mandato activo requiere una cuenta recaudadora activa.'})

        admin_tuple = self.administrador_tuple()
        recaudador_tuple_value = self.recaudador_tuple()
        propietario_tuple_value = self.propietario_tuple()
        facturadora_tuple_value = self.facturadora_tuple()
        cuenta_owner_tuple = (self.cuenta_recaudadora.owner_tipo, self.cuenta_recaudadora.owner_id)

        if self.administrador_empresa_owner_id and self.administrador_empresa_owner.estado != 'activa':
            raise ValidationError({'estado': 'El mandato activo requiere un administrador operativo activo.'})

        if self.administrador_socio_owner_id and not self.administrador_socio_owner.activo:
            raise ValidationError({'estado': 'El mandato activo requiere un administrador operativo activo.'})

        if self.recaudador_empresa_owner_id and self.recaudador_empresa_owner.estado != 'activa':
            raise ValidationError({'estado': 'El mandato activo requiere un recaudador activo.'})

        if self.recaudador_socio_owner_id and not self.recaudador_socio_owner.activo:
            raise ValidationError({'estado': 'El mandato activo requiere un recaudador activo.'})

        if self.entidad_facturadora_id and self.entidad_facturadora.estado != 'activa':
            raise ValidationError({'entidad_facturadora': 'La entidad facturadora debe estar activa.'})

        if cuenta_owner_tuple != recaudador_tuple_value:
            raise ValidationError(
                {'cuenta_recaudadora': 'La cuenta recaudadora debe pertenecer exactamente al recaudador del mandato.'}
            )

        if recaudador_tuple_value != propietario_tuple_value:
            if not self.autoriza_recaudacion:
                raise ValidationError({'autoriza_recaudacion': 'Debe autorizar la recaudacion cuando el recaudador difiere del propietario.'})

        if admin_tuple != propietario_tuple_value:
            if not self.autoriza_comunicacion:
                raise ValidationError({'autoriza_comunicacion': 'Debe autorizar la comunicacion cuando el administrador difiere del propietario.'})

        if facturadora_tuple_value != (None, None) and facturadora_tuple_value != propietario_tuple_value:
            if not self.autoriza_facturacion:
                raise ValidationError({'autoriza_facturacion': 'Debe autorizar la facturacion cuando la facturadora difiere del propietario.'})

        if self.propietario_comunidad_owner_id:
            active_company_participants = self.propietario_comunidad_owner.participaciones_activas().filter(
                participante_empresa__isnull=False
            )
            company_count = active_company_participants.count()
            if company_count == 0 and self.entidad_facturadora_id:
                raise ValidationError(
                    {'entidad_facturadora': 'Una comunidad sin empresa participante activa no puede declarar entidad facturadora.'}
                )
            if company_count == 1 and self.entidad_facturadora_id:
                expected_company_id = active_company_participants.first().participante_empresa_id
                if self.entidad_facturadora_id != expected_company_id:
                    raise ValidationError(
                        {'entidad_facturadora': 'La entidad facturadora debe coincidir con la empresa participante activa de la comunidad.'}
                    )
            if company_count > 1 and self.entidad_facturadora_id:
                raise ValidationError(
                    {'entidad_facturadora': 'El boundary actual no soporta automatizacion con multiples empresas participantes activas en una comunidad.'}
                )


class AsignacionCanalOperacion(TimestampedModel):
    mandato_operacion = models.ForeignKey(
        MandatoOperacion,
        on_delete=models.CASCADE,
        related_name='asignaciones_canal',
    )
    canal = models.CharField(max_length=16, choices=CanalOperacion.choices)
    identidad_envio = models.ForeignKey(
        IdentidadDeEnvio,
        on_delete=models.PROTECT,
        related_name='asignaciones_operacion',
    )
    prioridad = models.PositiveSmallIntegerField(default=1)
    estado = models.CharField(max_length=16, choices=EstadoAsignacionCanal.choices, default=EstadoAsignacionCanal.ACTIVE)

    class Meta:
        ordering = ['mandato_operacion_id', 'canal', 'prioridad']
        constraints = [
            models.UniqueConstraint(
                fields=['mandato_operacion', 'canal', 'prioridad'],
                name='uniq_asignacion_canal_prioridad_por_mandato',
            ),
        ]

    def __str__(self):
        return f'{self.mandato_operacion_id} - {self.canal} - {self.prioridad}'

    def clean(self):
        super().clean()
        if self.identidad_envio.canal != self.canal:
            raise ValidationError({'identidad_envio': 'La identidad debe pertenecer al mismo canal de la asignacion.'})

        if self.estado != EstadoAsignacionCanal.ACTIVE:
            return

        if self.mandato_operacion.estado != EstadoMandatoOperacion.ACTIVE:
            raise ValidationError({'mandato_operacion': 'La asignacion activa requiere un mandato operativo activo.'})

        if self.identidad_envio.estado != EstadoIdentidadEnvio.ACTIVE:
            raise ValidationError({'identidad_envio': 'La asignacion activa requiere una identidad de envio activa.'})

        identity_owner = (self.identidad_envio.owner_tipo, self.identidad_envio.owner_id)
        admin_tuple = self.mandato_operacion.administrador_tuple()
        facturadora_tuple_value = self.mandato_operacion.facturadora_tuple()
        propietario_tuple_value = self.mandato_operacion.propietario_tuple()

        if identity_owner not in {admin_tuple, facturadora_tuple_value}:
            raise ValidationError(
                {'identidad_envio': 'La identidad debe pertenecer a la entidad facturadora o al administrador operativo del mandato.'}
            )

        if identity_owner != propietario_tuple_value and not self.mandato_operacion.autoriza_comunicacion:
            raise ValidationError(
                {'mandato_operacion': 'El mandato debe autorizar comunicacion para usar una identidad de un actor distinto al propietario.'}
            )
