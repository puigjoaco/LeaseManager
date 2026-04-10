from django.core.exceptions import ValidationError
from django.db import models

from cobranza.models import DistribucionCobroMensual, PagoMensual
from contabilidad.models import CierreMensualContable, EstadoPreparacionTributaria
from contratos.models import Contrato
from patrimonio.models import Empresa


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoGateSII(models.TextChoices):
    OPEN = 'abierto', 'Abierto'
    CONDITIONED = 'condicionado', 'Condicionado'
    CLOSED = 'cerrado', 'Cerrado'
    SUSPENDED = 'suspendido', 'Suspendido'
    PRUNED = 'podado', 'Podado'


class CapacidadSII(models.TextChoices):
    DTE_EMISION = 'DTEEmision', 'DTE Emision'
    DTE_CONSULTA = 'DTEConsultaEstado', 'DTE Consulta Estado'
    F29_PREPARACION = 'F29Preparacion', 'F29 Preparacion'
    F29_PRESENTACION = 'F29Presentacion', 'F29 Presentacion'
    DDJJ_PREPARACION = 'DDJJPreparacion', 'DDJJ Preparacion'
    F22_PREPARACION = 'F22Preparacion', 'F22 Preparacion'


class AmbienteSII(models.TextChoices):
    CERTIFICATION = 'certificacion', 'Certificacion'
    PRODUCTION = 'produccion', 'Produccion'


class EstadoDTE(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    SENT_MANUAL = 'enviado_manual_controlado', 'Enviado manual controlado'
    ACCEPTED = 'aceptado', 'Aceptado'
    REJECTED = 'rechazado', 'Rechazado'
    CANCELED = 'anulado', 'Anulado'


class TipoDTE(models.TextChoices):
    FACTURA_EXENTA = '34', 'Factura Exenta'
    NOTA_DEBITO = '56', 'Nota de Debito'
    NOTA_CREDITO = '61', 'Nota de Credito'


class CapacidadTributariaSII(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='capacidades_sii',
    )
    capacidad_key = models.CharField(max_length=32, choices=CapacidadSII.choices)
    certificado_ref = models.CharField(max_length=255, blank=True)
    ambiente = models.CharField(max_length=16, choices=AmbienteSII.choices, default=AmbienteSII.CERTIFICATION)
    estado_gate = models.CharField(max_length=16, choices=EstadoGateSII.choices, default=EstadoGateSII.CONDITIONED)
    ultimo_resultado = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['empresa_id', 'capacidad_key']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'capacidad_key'],
                name='uniq_capacidad_sii_por_empresa',
            ),
        ]

    def __str__(self):
        return f'{self.empresa.razon_social} - {self.capacidad_key}'


class DTEEmitido(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='dtes_emitidos',
    )
    capacidad_tributaria = models.ForeignKey(
        CapacidadTributariaSII,
        on_delete=models.PROTECT,
        related_name='dtes_emitidos',
    )
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        related_name='dtes_emitidos',
    )
    pago_mensual = models.OneToOneField(
        PagoMensual,
        on_delete=models.PROTECT,
        related_name='dte_emitido',
    )
    distribucion_cobro_mensual = models.OneToOneField(
        DistribucionCobroMensual,
        on_delete=models.PROTECT,
        related_name='dte_emitido',
    )
    arrendatario = models.ForeignKey(
        'contratos.Arrendatario',
        on_delete=models.PROTECT,
        related_name='dtes_emitidos',
    )
    tipo_dte = models.CharField(max_length=3, choices=TipoDTE.choices, default=TipoDTE.FACTURA_EXENTA)
    monto_neto_clp = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_emision = models.DateField()
    estado_dte = models.CharField(max_length=32, choices=EstadoDTE.choices, default=EstadoDTE.DRAFT)
    sii_track_id = models.CharField(max_length=64, blank=True)
    ultimo_estado_sii = models.CharField(max_length=128, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_emision', '-id']

    def __str__(self):
        return f'{self.tipo_dte} - {self.pago_mensual_id}'

    def clean(self):
        super().clean()
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            raise ValidationError({'capacidad_tributaria': 'La capacidad SII debe pertenecer a la misma empresa del DTE.'})
        if self.pago_mensual.contrato_id != self.contrato_id:
            raise ValidationError({'pago_mensual': 'El pago mensual debe pertenecer al mismo contrato del DTE.'})
        if self.distribucion_cobro_mensual.pago_mensual_id != self.pago_mensual_id:
            raise ValidationError({'distribucion_cobro_mensual': 'La distribucion debe pertenecer al mismo pago mensual del DTE.'})
        if not self.distribucion_cobro_mensual.requiere_dte:
            raise ValidationError({'distribucion_cobro_mensual': 'El DTE solo puede emitirse desde una distribucion facturable.'})
        if self.distribucion_cobro_mensual.beneficiario_empresa_owner_id != self.empresa_id:
            raise ValidationError({'empresa': 'La empresa del DTE debe coincidir con la empresa beneficiaria de la distribucion.'})
        if self.contrato.arrendatario_id != self.arrendatario_id:
            raise ValidationError({'arrendatario': 'El DTE debe pertenecer al mismo arrendatario del contrato.'})


class F29PreparacionMensual(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='f29_preparados',
    )
    capacidad_tributaria = models.ForeignKey(
        CapacidadTributariaSII,
        on_delete=models.PROTECT,
        related_name='f29_preparados',
    )
    cierre_mensual = models.ForeignKey(
        CierreMensualContable,
        on_delete=models.PROTECT,
        related_name='f29_preparados',
    )
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    estado_preparacion = models.CharField(
        max_length=32,
        choices=EstadoPreparacionTributaria.choices,
        default=EstadoPreparacionTributaria.PENDING_DATA,
    )
    resumen_formulario = models.JSONField(default=dict, blank=True)
    borrador_ref = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['empresa_id', '-anio', '-mes']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'anio', 'mes'], name='uniq_f29_preparacion_por_empresa_periodo'),
        ]

    def __str__(self):
        return f'F29 {self.empresa_id} {self.anio}-{self.mes}'

    def clean(self):
        super().clean()
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            raise ValidationError({'capacidad_tributaria': 'La capacidad SII debe pertenecer a la misma empresa del borrador F29.'})
        if self.cierre_mensual.empresa_id != self.empresa_id or self.cierre_mensual.anio != self.anio or self.cierre_mensual.mes != self.mes:
            raise ValidationError({'cierre_mensual': 'El cierre mensual debe coincidir con la empresa y periodo del F29.'})


class ProcesoRentaAnual(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='procesos_renta_anual',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    estado = models.CharField(
        max_length=32,
        choices=EstadoPreparacionTributaria.choices,
        default=EstadoPreparacionTributaria.PENDING_DATA,
    )
    fecha_preparacion = models.DateTimeField(null=True, blank=True)
    resumen_anual = models.JSONField(default=dict, blank=True)
    paquete_ddjj_ref = models.CharField(max_length=255, blank=True)
    borrador_f22_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['empresa_id', '-anio_tributario']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'anio_tributario'], name='uniq_proceso_renta_anual_por_empresa'),
        ]

    def __str__(self):
        return f'Renta {self.empresa_id} {self.anio_tributario}'


class DDJJPreparacionAnual(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='ddjj_preparadas',
    )
    capacidad_tributaria = models.ForeignKey(
        CapacidadTributariaSII,
        on_delete=models.PROTECT,
        related_name='ddjj_preparadas',
    )
    proceso_renta_anual = models.ForeignKey(
        ProcesoRentaAnual,
        on_delete=models.PROTECT,
        related_name='ddjj_preparadas',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    estado_preparacion = models.CharField(
        max_length=32,
        choices=EstadoPreparacionTributaria.choices,
        default=EstadoPreparacionTributaria.PENDING_DATA,
    )
    resumen_paquete = models.JSONField(default=dict, blank=True)
    paquete_ref = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['empresa_id', '-anio_tributario']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'anio_tributario'], name='uniq_ddjj_preparacion_por_empresa'),
        ]

    def clean(self):
        super().clean()
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            raise ValidationError({'capacidad_tributaria': 'La capacidad DDJJ debe pertenecer a la misma empresa.'})
        if self.proceso_renta_anual.empresa_id != self.empresa_id or self.proceso_renta_anual.anio_tributario != self.anio_tributario:
            raise ValidationError({'proceso_renta_anual': 'El proceso anual debe coincidir con la empresa y año tributario de DDJJ.'})


class F22PreparacionAnual(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='f22_preparados',
    )
    capacidad_tributaria = models.ForeignKey(
        CapacidadTributariaSII,
        on_delete=models.PROTECT,
        related_name='f22_preparados',
    )
    proceso_renta_anual = models.ForeignKey(
        ProcesoRentaAnual,
        on_delete=models.PROTECT,
        related_name='f22_preparados',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    estado_preparacion = models.CharField(
        max_length=32,
        choices=EstadoPreparacionTributaria.choices,
        default=EstadoPreparacionTributaria.PENDING_DATA,
    )
    resumen_f22 = models.JSONField(default=dict, blank=True)
    borrador_ref = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['empresa_id', '-anio_tributario']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'anio_tributario'], name='uniq_f22_preparacion_por_empresa'),
        ]

    def clean(self):
        super().clean()
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            raise ValidationError({'capacidad_tributaria': 'La capacidad F22 debe pertenecer a la misma empresa.'})
        if self.proceso_renta_anual.empresa_id != self.empresa_id or self.proceso_renta_anual.anio_tributario != self.anio_tributario:
            raise ValidationError({'proceso_renta_anual': 'El proceso anual debe coincidir con la empresa y año tributario del F22.'})
