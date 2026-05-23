import calendar
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
    whatsapp_opt_in = models.BooleanField(default=False)
    whatsapp_opt_in_evidencia_ref = models.CharField(max_length=255, blank=True)
    whatsapp_bloqueado = models.BooleanField(default=False)

    class Meta:
        ordering = ['nombre_razon_social']

    def __str__(self):
        return self.nombre_razon_social

    def save(self, *args, **kwargs):
        self.rut = normalize_rut(self.rut)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if not self.whatsapp_opt_in:
            return
        if self.whatsapp_bloqueado:
            raise ValidationError({'whatsapp_opt_in': 'No puede existir opt-in activo si WhatsApp esta bloqueado.'})
        if not self.telefono:
            raise ValidationError({'telefono': 'El opt-in de WhatsApp requiere telefono operativo.'})
        if not self.whatsapp_opt_in_evidencia_ref.strip():
            raise ValidationError(
                {
                    'whatsapp_opt_in_evidencia_ref': (
                        'El opt-in de WhatsApp requiere referencia de evidencia.'
                    )
                }
            )


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
            if self.fecha_inicio.day != 1:
                raise ValidationError({'fecha_inicio': 'Un contrato vigente o futuro debe iniciar el dia 1.'})
            last_day = calendar.monthrange(self.fecha_fin_vigente.year, self.fecha_fin_vigente.month)[1]
            if self.fecha_fin_vigente.day != last_day:
                raise ValidationError(
                    {'fecha_fin_vigente': 'Un contrato vigente o futuro debe terminar el ultimo dia del mes.'}
                )
            if self.mandato_operacion.estado != 'activa':
                raise ValidationError(
                    {'mandato_operacion': 'Un contrato vigente o futuro requiere un mandato operativo activo.'}
                )
            mandato_errors = []
            if self.mandato_operacion.vigencia_desde > self.fecha_inicio:
                mandato_errors.append('El mandato operativo debe estar vigente al inicio del contrato.')
            if (
                self.mandato_operacion.vigencia_hasta
                and self.mandato_operacion.vigencia_hasta < self.fecha_fin_vigente
            ):
                mandato_errors.append('El mandato operativo debe cubrir la fecha fin vigente del contrato.')
            if mandato_errors:
                raise ValidationError({'mandato_operacion': mandato_errors})


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

    def clean(self):
        super().clean()
        if self.codigo_conciliacion_efectivo_snapshot == '000':
            raise ValidationError(
                {
                    'codigo_conciliacion_efectivo_snapshot': (
                        'El codigo efectivo debe estar en el rango 001-999.'
                    )
                }
            )
        if not self.contrato_id or not self.propiedad_id:
            return
        if self.contrato.estado not in {EstadoContrato.ACTIVE, EstadoContrato.FUTURE}:
            return

        if self.propiedad.estado != 'activa':
            raise ValidationError(
                {'propiedad': 'Un contrato vigente o futuro solo puede usar propiedades activas.'}
            )

        same_contract_links = ContratoPropiedad.objects.filter(contrato_id=self.contrato_id).exclude(pk=self.pk)
        if same_contract_links.count() >= 2:
            raise ValidationError(
                {'contrato': 'Un contrato vigente o futuro solo puede cubrir una propiedad o una pareja principal + vinculada.'}
            )

        if self.rol_en_contrato == RolContratoPropiedad.PRIMARY:
            mismatched_contract_codes = same_contract_links.exclude(
                codigo_conciliacion_efectivo_snapshot=self.codigo_conciliacion_efectivo_snapshot,
            )
            if mismatched_contract_codes.exists():
                raise ValidationError(
                    {
                        'codigo_conciliacion_efectivo_snapshot': (
                            'La propiedad principal y la vinculada deben compartir el mismo codigo efectivo.'
                        )
                    }
                )
        else:
            primary_link = same_contract_links.filter(rol_en_contrato=RolContratoPropiedad.PRIMARY).first()
            if (
                primary_link
                and primary_link.codigo_conciliacion_efectivo_snapshot
                != self.codigo_conciliacion_efectivo_snapshot
            ):
                raise ValidationError(
                    {
                        'codigo_conciliacion_efectivo_snapshot': (
                            'La propiedad principal y la vinculada deben compartir el mismo codigo efectivo.'
                        )
                    }
                )

        same_state_links = ContratoPropiedad.objects.filter(
            propiedad_id=self.propiedad_id,
            contrato__estado=self.contrato.estado,
        ).exclude(pk=self.pk)
        if self.contrato_id:
            same_state_links = same_state_links.exclude(contrato_id=self.contrato_id)

        if same_state_links.exists():
            label = 'vigente' if self.contrato.estado == EstadoContrato.ACTIVE else 'futuro'
            raise ValidationError(
                {'propiedad': f'La propiedad ya participa en otro contrato {label}.'}
            )

        same_code_links = ContratoPropiedad.objects.filter(
            contrato__mandato_operacion__cuenta_recaudadora_id=(
                self.contrato.mandato_operacion.cuenta_recaudadora_id
            ),
            contrato__estado=self.contrato.estado,
            codigo_conciliacion_efectivo_snapshot=self.codigo_conciliacion_efectivo_snapshot,
        ).exclude(pk=self.pk)
        if self.contrato_id:
            same_code_links = same_code_links.exclude(contrato_id=self.contrato_id)

        if same_code_links.exists():
            label = 'vigente' if self.contrato.estado == EstadoContrato.ACTIVE else 'futuro'
            raise ValidationError(
                {
                    'codigo_conciliacion_efectivo_snapshot': (
                        f'El codigo efectivo ya esta usado en otro contrato {label} de la misma cuenta recaudadora.'
                    )
                }
            )


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
        if self.moneda_base == MonedaBaseContrato.CLP and self.monto_base < Decimal('1000.00'):
            raise ValidationError({'monto_base': 'Un periodo CLP debe respetar el minimo operativo de 1.000.'})
        if self.moneda_base == MonedaBaseContrato.UF and self.monto_base <= Decimal('0.00'):
            raise ValidationError({'monto_base': 'Un periodo UF debe tener monto positivo.'})


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

    def clean(self):
        super().clean()
        snapshot = self.snapshot_identidad or {}
        if not isinstance(snapshot, dict):
            raise ValidationError(
                {'snapshot_identidad': 'El snapshot del codeudor debe ser un objeto con nombre y RUT.'}
            )

        nombre = str(snapshot.get('nombre') or '').strip()
        rut_value = str(snapshot.get('rut') or '').strip()
        if not nombre or not rut_value:
            raise ValidationError(
                {'snapshot_identidad': 'El snapshot del codeudor debe incluir nombre y RUT.'}
            )

        try:
            normalized_rut = validate_rut(rut_value)
        except ValidationError as error:
            raise ValidationError({'snapshot_identidad': error.messages}) from error

        if self.estado != EstadoCodeudorSolidario.ACTIVE or not self.contrato_id:
            return

        active_codebtors = CodeudorSolidario.objects.filter(
            contrato_id=self.contrato_id,
            estado=EstadoCodeudorSolidario.ACTIVE,
        ).exclude(pk=self.pk)
        if active_codebtors.count() >= 3:
            raise ValidationError({'estado': 'Un contrato admite como maximo 3 codeudores solidarios activos.'})

        for codebtor in active_codebtors:
            other_snapshot = codebtor.snapshot_identidad or {}
            if not isinstance(other_snapshot, dict):
                continue
            try:
                other_rut = validate_rut(other_snapshot.get('rut'))
            except ValidationError:
                continue
            if other_rut == normalized_rut:
                raise ValidationError(
                    {'snapshot_identidad': 'No puede repetir el mismo codeudor activo dentro del contrato.'}
                )


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
        if self.fecha_efectiva > self.contrato.fecha_fin_vigente:
            raise ValidationError(
                {'fecha_efectiva': 'La fecha efectiva no puede ser posterior a la fecha fin vigente del contrato.'}
            )

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

