from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from operacion.models import MandatoOperacion
from patrimonio.validators import normalize_rut, validate_rut


codigo_efectivo_validator = RegexValidator(
    regex=r'^\d{3}$',
    message='El codigo de conciliacion efectivo debe tener exactamente 3 digitos.',
)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TipoArrendatario(models.TextChoices):
    NATURAL = 'persona_natural', 'Persona natural'
    COMPANY = 'empresa', 'Empresa'


class EstadoContactoArrendatario(models.TextChoices):
    PENDING = 'pendiente', 'Pendiente'
    ACTIVE = 'activo', 'Activo'
    INACTIVE = 'inactivo', 'Inactivo'


class EstadoContrato(models.TextChoices):
    PENDING = 'pendiente_activacion', 'Pendiente activacion'
    FUTURE = 'futuro', 'Futuro'
    ACTIVE = 'vigente', 'Vigente'
    EARLY_TERMINATED = 'terminado_anticipadamente', 'Terminado anticipadamente'
    FINISHED = 'finalizado', 'Finalizado'
    CANCELED = 'cancelado', 'Cancelado'


class RolContratoPropiedad(models.TextChoices):
    PRIMARY = 'principal', 'Principal'
    LINKED = 'vinculada', 'Vinculada'


class EstadoCodeudorSolidario(models.TextChoices):
    ACTIVE = 'activo', 'Activo'
    INACTIVE = 'inactivo', 'Inactivo'


class EstadoAvisoTermino(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    REGISTERED = 'registrado', 'Registrado'
    CANCELED = 'cancelado', 'Cancelado'


class MonedaBaseContrato(models.TextChoices):
    CLP = 'CLP', 'CLP'
    UF = 'UF', 'UF'


class Arrendatario(TimestampedModel):
    tipo_arrendatario = models.CharField(max_length=20, choices=TipoArrendatario.choices)
    nombre_razon_social = models.CharField(max_length=255)
    rut = models.CharField(max_length=16, unique=True, validators=[validate_rut])
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)
    domicilio_notificaciones = models.CharField(max_length=255, blank=True)
    estado_contacto = models.CharField(
        max_length=16,
        choices=EstadoContactoArrendatario.choices,
        default=EstadoContactoArrendatario.PENDING,
    )
    whatsapp_bloqueado = models.BooleanField(default=False)

    class Meta:
        ordering = ['nombre_razon_social']

    def __str__(self):
        return self.nombre_razon_social

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        super().save(*args, **kwargs)


class Contrato(TimestampedModel):
    codigo_contrato = models.CharField(max_length=64, unique=True)
    mandato_operacion = models.ForeignKey(
        MandatoOperacion,
        on_delete=models.PROTECT,
        related_name='contratos',
    )
    arrendatario = models.ForeignKey(
        Arrendatario,
        on_delete=models.PROTECT,
        related_name='contratos',
    )
    fecha_inicio = models.DateField()
    fecha_fin_vigente = models.DateField()
    fecha_entrega = models.DateField(null=True, blank=True)
    dia_pago_mensual = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    plazo_notificacion_termino_dias = models.PositiveSmallIntegerField(default=60)
    dias_prealerta_admin = models.PositiveSmallIntegerField(default=90)
    estado = models.CharField(max_length=32, choices=EstadoContrato.choices, default=EstadoContrato.PENDING)
    tiene_tramos = models.BooleanField(default=False)
    tiene_gastos_comunes = models.BooleanField(default=False)
    snapshot_representante_legal = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['codigo_contrato']

    def __str__(self):
        return self.codigo_contrato

    def principal_property_id(self):
        principal = self.contrato_propiedades.filter(rol_en_contrato=RolContratoPropiedad.PRIMARY).first()
        return principal.propiedad_id if principal else None

    def clean(self):
        super().clean()
        if self.fecha_fin_vigente < self.fecha_inicio:
            raise ValidationError({'fecha_fin_vigente': 'La fecha fin vigente no puede ser anterior al inicio.'})

        if self.fecha_entrega and self.fecha_entrega < self.fecha_inicio:
            raise ValidationError({'fecha_entrega': 'La fecha de entrega no puede ser anterior al inicio.'})

        if self.plazo_notificacion_termino_dias <= 0:
            raise ValidationError(
                {'plazo_notificacion_termino_dias': 'El plazo de notificacion debe ser mayor que cero.'}
            )

        if self.dias_prealerta_admin <= 0:
            raise ValidationError({'dias_prealerta_admin': 'Los dias de prealerta deben ser mayores que cero.'})

        if self.estado in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            if self.mandato_operacion.estado != 'activa':
                raise ValidationError(
                    {'mandato_operacion': 'Un contrato vigente o futuro requiere un mandato operativo activo.'}
                )


class ContratoPropiedad(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='contrato_propiedades',
    )
    propiedad = models.ForeignKey(
        'patrimonio.Propiedad',
        on_delete=models.PROTECT,
        related_name='contrato_propiedades',
    )
    rol_en_contrato = models.CharField(max_length=16, choices=RolContratoPropiedad.choices)
    porcentaje_distribucion_interna = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
    )
    codigo_conciliacion_efectivo_snapshot = models.CharField(max_length=3, validators=[codigo_efectivo_validator])

    class Meta:
        ordering = ['contrato_id', 'rol_en_contrato']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'propiedad'],
                name='uniq_propiedad_por_contrato',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - {self.propiedad.codigo_propiedad}'


class PeriodoContractual(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='periodos_contractuales',
    )
    numero_periodo = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    monto_base = models.DecimalField(max_digits=14, decimal_places=2)
    moneda_base = models.CharField(max_length=8, choices=MonedaBaseContrato.choices)
    tipo_periodo = models.CharField(max_length=64)
    origen_periodo = models.CharField(max_length=64)

    class Meta:
        ordering = ['contrato_id', 'numero_periodo']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'numero_periodo'],
                name='uniq_numero_periodo_por_contrato',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - Periodo {self.numero_periodo}'

    def clean(self):
        super().clean()
        if self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha fin del periodo no puede ser anterior al inicio.'})


class CodeudorSolidario(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='codeudores_solidarios',
    )
    snapshot_identidad = models.JSONField(default=dict)
    fecha_inclusion = models.DateField(default=timezone.localdate)
    estado = models.CharField(
        max_length=16,
        choices=EstadoCodeudorSolidario.choices,
        default=EstadoCodeudorSolidario.ACTIVE,
    )

    class Meta:
        ordering = ['contrato_id', 'fecha_inclusion']

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - Codeudor {self.pk}'


class AvisoTermino(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='avisos_termino',
    )
    fecha_efectiva = models.DateField()
    causal = models.CharField(max_length=255)
    estado = models.CharField(max_length=16, choices=EstadoAvisoTermino.choices, default=EstadoAvisoTermino.DRAFT)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='avisos_termino_registrados',
    )

    class Meta:
        ordering = ['-fecha_efectiva']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato'],
                condition=Q(estado='registrado'),
                name='uniq_aviso_registrado_por_contrato',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - {self.estado}'

    def clean(self):
        super().clean()
        if self.fecha_efectiva < self.contrato.fecha_inicio:
            raise ValidationError({'fecha_efectiva': 'La fecha efectiva no puede ser anterior al inicio del contrato.'})

        if self.estado == EstadoAvisoTermino.CANCELED:
            principal_ids = list(
                self.contrato.contrato_propiedades.filter(
                    rol_en_contrato=RolContratoPropiedad.PRIMARY
                ).values_list('propiedad_id', flat=True)
            )
            if principal_ids:
                future_exists = Contrato.objects.filter(
                    estado=EstadoContrato.FUTURE,
                    contrato_propiedades__propiedad_id__in=principal_ids,
                    contrato_propiedades__rol_en_contrato=RolContratoPropiedad.PRIMARY,
                ).exclude(pk=self.contrato_id).exists()
                if future_exists:
                    raise ValidationError(
                        {'estado': 'No se puede cancelar el aviso si existe un contrato futuro activo para la propiedad principal.'}
                    )

