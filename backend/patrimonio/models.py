from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from .validators import normalize_rut, validate_rut


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoPatrimonial(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class TipoInmueble(models.TextChoices):
    APARTMENT = 'departamento', 'Departamento'
    HOUSE = 'casa', 'Casa'
    LOCAL = 'local', 'Local'
    OFFICE = 'oficina', 'Oficina'
    STORAGE = 'bodega', 'Bodega'
    PARKING = 'estacionamiento', 'Estacionamiento'
    OTHER = 'otro', 'Otro'


class Socio(TimestampedModel):
    nombre = models.CharField(max_length=255)
    rut = models.CharField(max_length=16, unique=True, validators=[validate_rut])
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    domicilio = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre} ({self.rut})'


class Empresa(TimestampedModel):
    razon_social = models.CharField(max_length=255)
    rut = models.CharField(max_length=16, unique=True, validators=[validate_rut])
    domicilio = models.CharField(max_length=255, blank=True)
    giro = models.CharField(max_length=255, blank=True)
    codigo_actividad_sii = models.CharField(max_length=32, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoPatrimonial.choices, default=EstadoPatrimonial.DRAFT)

    class Meta:
        ordering = ['razon_social']

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.razon_social

    def participaciones_activas(self):
        today = timezone.localdate()
        return self.participaciones_vigentes_en(today)

    def participaciones_vigentes_en(self, effective_date):
        return self.participaciones.filter(
            activo=True,
            vigente_desde__lte=effective_date,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=effective_date),
        )

    def total_participaciones_activas(self):
        total = self.participaciones_activas().aggregate(total=Sum('porcentaje'))['total']
        return total or Decimal('0.00')

    def participaciones_completas(self):
        return self.total_participaciones_activas() == Decimal('100.00')

    def clean(self):
        super().clean()
        if self.estado == EstadoPatrimonial.ACTIVE and not self.participaciones_completas():
            raise ValidationError(
                {'estado': 'La empresa activa requiere participaciones activas que sumen exactamente 100.00.'}
            )


class ComunidadPatrimonial(TimestampedModel):
    nombre = models.CharField(max_length=255)
    estado = models.CharField(max_length=16, choices=EstadoPatrimonial.choices, default=EstadoPatrimonial.DRAFT)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'comunidades patrimoniales'

    def __str__(self):
        return self.nombre

    def participaciones_activas(self):
        today = timezone.localdate()
        return self.participaciones_vigentes_en(today)

    def participaciones_vigentes_en(self, effective_date):
        return self.participaciones.filter(
            activo=True,
            vigente_desde__lte=effective_date,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=effective_date),
        )

    def total_participaciones_activas(self):
        total = self.participaciones_activas().aggregate(total=Sum('porcentaje'))['total']
        return total or Decimal('0.00')

    def participaciones_completas(self):
        return self.total_participaciones_activas() == Decimal('100.00')

    def representaciones_activas(self):
        today = timezone.localdate()
        return self.representaciones.filter(
            activo=True,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=today),
        )

    def representacion_vigente(self):
        return self.representaciones_activas().select_related('socio_representante').order_by('-vigente_desde', '-id').first()

    @property
    def representante_socio(self):
        representacion = self.representacion_vigente()
        return representacion.socio_representante if representacion else None

    @property
    def representante_socio_id(self):
        representacion = self.representacion_vigente()
        return representacion.socio_representante_id if representacion else None

    def representante_es_participante_activo(self):
        representacion = self.representacion_vigente()
        if not representacion or representacion.modo_representacion != ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT:
            return False
        return self.participaciones_activas().filter(participante_socio=representacion.socio_representante).exists()

    def clean(self):
        super().clean()
        if self.estado == EstadoPatrimonial.ACTIVE:
            if not self.participaciones_completas():
                raise ValidationError(
                    {'estado': 'La comunidad activa requiere participaciones activas que sumen exactamente 100.00.'}
                )
            if not self.representacion_vigente():
                raise ValidationError({'estado': 'La comunidad activa debe tener una representacion vigente.'})
            if not self.representacion_vigente().socio_representante.activo:
                raise ValidationError({'estado': 'La representacion activa debe usar un socio activo.'})
            if (
                self.representacion_vigente().modo_representacion == ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT
                and not self.representante_es_participante_activo()
            ):
                raise ValidationError(
                    {'estado': 'La representacion patrimonial activa debe pertenecer a las participaciones activas.'}
                )


class ModoRepresentacionComunidad(models.TextChoices):
    PATRIMONIAL_PARTICIPANT = 'participante_patrimonial', 'Participante patrimonial'
    DESIGNATED = 'designado', 'Designado'


class RepresentacionComunidad(TimestampedModel):
    comunidad = models.ForeignKey(
        ComunidadPatrimonial,
        on_delete=models.CASCADE,
        related_name='representaciones',
    )
    modo_representacion = models.CharField(
        max_length=32,
        choices=ModoRepresentacionComunidad.choices,
        default=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
    )
    socio_representante = models.ForeignKey(
        Socio,
        on_delete=models.PROTECT,
        related_name='representaciones_comunidad',
    )
    vigente_desde = models.DateField(default=timezone.localdate)
    vigente_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['comunidad_id', '-vigente_desde', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['comunidad'],
                condition=Q(activo=True),
                name='uniq_representacion_activa_por_comunidad',
            ),
        ]

    def __str__(self):
        return f'{self.comunidad.nombre} - {self.socio_representante.nombre}'

    def clean(self):
        super().clean()
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError({'vigente_hasta': 'La vigencia final no puede ser anterior a la inicial.'})
        if self.activo and not self.socio_representante.activo:
            raise ValidationError({'socio_representante': 'La representacion activa requiere un socio activo.'})
        if self.modo_representacion == ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT:
            if not self.comunidad.participaciones_activas().filter(participante_socio=self.socio_representante).exists():
                raise ValidationError(
                    {'socio_representante': 'La representacion patrimonial debe pertenecer a las participaciones activas.'}
                )


class ParticipacionPatrimonial(TimestampedModel):
    participante_socio = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='participaciones_patrimoniales_como_participante',
    )
    participante_empresa = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='participaciones_patrimoniales_como_participante',
    )
    empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='participaciones',
    )
    comunidad_owner = models.ForeignKey(
        ComunidadPatrimonial,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='participaciones',
    )
    porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
    )
    vigente_desde = models.DateField(default=timezone.localdate)
    vigente_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-vigente_desde', '-id']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(empresa_owner__isnull=False, comunidad_owner__isnull=True)
                    | Q(empresa_owner__isnull=True, comunidad_owner__isnull=False)
                ),
                name='participacion_exactly_one_owner',
            ),
            models.CheckConstraint(
                check=(
                    Q(participante_socio__isnull=False, participante_empresa__isnull=True)
                    | Q(participante_socio__isnull=True, participante_empresa__isnull=False)
                ),
                name='participacion_exactly_one_participant',
            ),
        ]

    def __str__(self):
        return f'{self.participante_display} - {self.porcentaje}%'

    @property
    def owner_tipo(self):
        if self.empresa_owner_id:
            return 'empresa'
        return 'comunidad'

    @property
    def owner_id(self):
        if self.empresa_owner_id:
            return self.empresa_owner_id
        return self.comunidad_owner_id

    @property
    def participante_tipo(self):
        if self.participante_socio_id:
            return 'socio'
        return 'empresa'

    @property
    def participante_id(self):
        if self.participante_socio_id:
            return self.participante_socio_id
        return self.participante_empresa_id

    @property
    def participante_display(self):
        if self.participante_socio_id:
            return self.participante_socio.nombre
        return self.participante_empresa.razon_social

    @property
    def participante_rut(self):
        if self.participante_socio_id:
            return self.participante_socio.rut
        return self.participante_empresa.rut

    def clean(self):
        super().clean()
        owner_count = sum(bool(owner_id) for owner_id in (self.empresa_owner_id, self.comunidad_owner_id))
        if owner_count != 1:
            raise ValidationError('La participacion debe pertenecer exactamente a una empresa o comunidad.')
        participant_count = sum(bool(participant_id) for participant_id in (self.participante_socio_id, self.participante_empresa_id))
        if participant_count != 1:
            raise ValidationError('La participacion debe declarar exactamente un participante.')
        if self.vigente_hasta and self.vigente_hasta < self.vigente_desde:
            raise ValidationError({'vigente_hasta': 'La vigencia final no puede ser anterior a la inicial.'})
        if self.empresa_owner_id and self.participante_empresa_id:
            raise ValidationError({'participante_empresa': 'Una empresa no puede tener empresas como participantes patrimoniales en el boundary actual.'})


class Propiedad(TimestampedModel):
    rol_avaluo = models.CharField(max_length=64, blank=True)
    direccion = models.CharField(max_length=255)
    comuna = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    tipo_inmueble = models.CharField(max_length=32, choices=TipoInmueble.choices)
    codigo_propiedad = models.CharField(max_length=16)
    estado = models.CharField(max_length=16, choices=EstadoPatrimonial.choices, default=EstadoPatrimonial.DRAFT)
    empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='propiedades',
    )
    comunidad_owner = models.ForeignKey(
        ComunidadPatrimonial,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='propiedades',
    )
    socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='propiedades_directas',
    )

    class Meta:
        ordering = ['codigo_propiedad', 'direccion']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(empresa_owner__isnull=False, comunidad_owner__isnull=True, socio_owner__isnull=True)
                    | Q(empresa_owner__isnull=True, comunidad_owner__isnull=False, socio_owner__isnull=True)
                    | Q(empresa_owner__isnull=True, comunidad_owner__isnull=True, socio_owner__isnull=False)
                ),
                name='propiedad_exactly_one_owner',
            ),
            models.UniqueConstraint(
                fields=['codigo_propiedad', 'empresa_owner'],
                condition=Q(empresa_owner__isnull=False),
                name='uniq_codigo_propiedad_por_empresa',
            ),
            models.UniqueConstraint(
                fields=['codigo_propiedad', 'comunidad_owner'],
                condition=Q(comunidad_owner__isnull=False),
                name='uniq_codigo_propiedad_por_comunidad',
            ),
            models.UniqueConstraint(
                fields=['codigo_propiedad', 'socio_owner'],
                condition=Q(socio_owner__isnull=False),
                name='uniq_codigo_propiedad_por_socio',
            ),
        ]

    def __str__(self):
        return f'{self.codigo_propiedad} - {self.direccion}'

    @property
    def owner_tipo(self):
        if self.empresa_owner_id:
            return 'empresa'
        if self.comunidad_owner_id:
            return 'comunidad'
        return 'socio'

    @property
    def owner_id(self):
        if self.empresa_owner_id:
            return self.empresa_owner_id
        if self.comunidad_owner_id:
            return self.comunidad_owner_id
        return self.socio_owner_id

    def clean(self):
        super().clean()
        owner_count = sum(
            bool(owner_id) for owner_id in (self.empresa_owner_id, self.comunidad_owner_id, self.socio_owner_id)
        )
        if owner_count != 1:
            raise ValidationError('La propiedad debe pertenecer exactamente a un owner.')

        if self.estado != EstadoPatrimonial.ACTIVE:
            return

        if self.empresa_owner_id:
            if self.empresa_owner.estado != EstadoPatrimonial.ACTIVE or not self.empresa_owner.participaciones_completas():
                raise ValidationError(
                    {'estado': 'La propiedad activa requiere una empresa activa con participaciones completas.'}
                )
        elif self.comunidad_owner_id:
            if self.comunidad_owner.estado != EstadoPatrimonial.ACTIVE or not self.comunidad_owner.participaciones_completas():
                raise ValidationError(
                    {'estado': 'La propiedad activa requiere una comunidad activa con participaciones completas.'}
                )
        elif self.socio_owner_id and not self.socio_owner.activo:
            raise ValidationError({'estado': 'La propiedad activa requiere un socio activo.'})
