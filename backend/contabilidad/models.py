import hashlib
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from patrimonio.models import Empresa


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoRegistro(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ACTIVE = 'activa', 'Activa'
    INACTIVE = 'inactiva', 'Inactiva'


class EstadoEventoContable(models.TextChoices):
    PENDING = 'pendiente_contabilizacion', 'Pendiente contabilizacion'
    REVIEW = 'pendiente_revision_contable', 'Pendiente revision contable'
    POSTED = 'contabilizado', 'Contabilizado'


class EstadoAsientoContable(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    POSTED = 'contabilizado', 'Contabilizado'
    REVERSED = 'revertido', 'Revertido'


class EstadoCierreMensual(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    APPROVED = 'aprobado', 'Aprobado'
    REOPENED = 'reabierto', 'Reabierto'


class EstadoPreparacionTributaria(models.TextChoices):
    NOT_APPLICABLE = 'no_aplica', 'No aplica'
    PENDING_DATA = 'pendiente_datos', 'Pendiente datos'
    IN_PREPARATION = 'en_preparacion', 'En preparacion'
    PREPARED = 'preparado', 'Preparado'
    APPROVED = 'aprobado_para_presentacion', 'Aprobado para presentacion'
    PRESENTED = 'presentado', 'Presentado'
    OBSERVED = 'observado', 'Observado'
    RECTIFIED = 'rectificado', 'Rectificado'


class NaturalezaCuenta(models.TextChoices):
    DEBIT = 'deudora', 'Deudora'
    CREDIT = 'acreedora', 'Acreedora'


class TipoMovimientoAsiento(models.TextChoices):
    DEBIT = 'debe', 'Debe'
    CREDIT = 'haber', 'Haber'


class RegimenTributarioEmpresa(TimestampedModel):
    codigo_regimen = models.CharField(max_length=64, unique=True)
    descripcion = models.CharField(max_length=255)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['codigo_regimen']

    def __str__(self):
        return self.codigo_regimen


class ConfiguracionFiscalEmpresa(TimestampedModel):
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name='configuracion_fiscal',
    )
    regimen_tributario = models.ForeignKey(
        RegimenTributarioEmpresa,
        on_delete=models.PROTECT,
        related_name='configuraciones_fiscales',
    )
    afecta_iva_arriendo = models.BooleanField(default=False)
    tasa_iva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    tasa_ppm_vigente = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
    )
    aplica_ppm = models.BooleanField(default=False)
    ddjj_habilitadas = models.JSONField(default=list, blank=True)
    inicio_ejercicio = models.DateField()
    moneda_funcional = models.CharField(max_length=8, choices=[('CLP', 'CLP'), ('UF', 'UF')], default='CLP')
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.DRAFT)

    class Meta:
        ordering = ['empresa_id']

    def __str__(self):
        return f'Fiscal {self.empresa.razon_social}'

    def clean(self):
        super().clean()
        if self.estado == EstadoRegistro.ACTIVE and self.empresa.estado != 'activa':
            raise ValidationError({'estado': 'La configuracion fiscal activa requiere una empresa activa.'})


class CuentaContable(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cuentas_contables',
    )
    plan_cuentas_version = models.CharField(max_length=32)
    codigo = models.CharField(max_length=32)
    nombre = models.CharField(max_length=255)
    naturaleza = models.CharField(max_length=16, choices=NaturalezaCuenta.choices)
    nivel = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    padre = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='subcuentas',
    )
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)
    es_control_obligatoria = models.BooleanField(default=False)

    class Meta:
        ordering = ['empresa_id', 'plan_cuentas_version', 'codigo']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'plan_cuentas_version', 'codigo'],
                name='uniq_cuenta_contable_por_empresa_version_codigo',
            ),
        ]

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class ReglaContable(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='reglas_contables',
    )
    evento_tipo = models.CharField(max_length=64)
    plan_cuentas_version = models.CharField(max_length=32)
    criterio_cargo = models.TextField(blank=True)
    criterio_abono = models.TextField(blank=True)
    vigencia_desde = models.DateField()
    vigencia_hasta = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['empresa_id', 'evento_tipo', '-vigencia_desde']

    def __str__(self):
        return f'{self.empresa_id} - {self.evento_tipo}'

    def clean(self):
        super().clean()
        if self.vigencia_hasta and self.vigencia_hasta < self.vigencia_desde:
            raise ValidationError({'vigencia_hasta': 'La vigencia final no puede ser anterior a la inicial.'})


class MatrizReglasContables(TimestampedModel):
    regla_contable = models.ForeignKey(
        ReglaContable,
        on_delete=models.CASCADE,
        related_name='lineas_matriz',
    )
    cuenta_debe = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        related_name='reglas_debe',
    )
    cuenta_haber = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        related_name='reglas_haber',
    )
    condicion_impuesto = models.CharField(max_length=128, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['regla_contable_id', 'id']

    def __str__(self):
        return f'{self.regla_contable.evento_tipo} -> {self.cuenta_debe.codigo}/{self.cuenta_haber.codigo}'

    def clean(self):
        super().clean()
        if self.cuenta_debe.empresa_id != self.regla_contable.empresa_id or self.cuenta_haber.empresa_id != self.regla_contable.empresa_id:
            raise ValidationError('Las cuentas de la matriz deben pertenecer a la misma empresa de la regla.')
        if self.cuenta_debe.plan_cuentas_version != self.regla_contable.plan_cuentas_version or self.cuenta_haber.plan_cuentas_version != self.regla_contable.plan_cuentas_version:
            raise ValidationError('La matriz debe usar cuentas de la misma version del plan de cuentas.')


class EventoContable(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='eventos_contables',
    )
    evento_tipo = models.CharField(max_length=64)
    entidad_origen_tipo = models.CharField(max_length=64)
    entidad_origen_id = models.CharField(max_length=64)
    fecha_operativa = models.DateField()
    moneda = models.CharField(max_length=8, choices=[('CLP', 'CLP'), ('UF', 'UF')], default='CLP')
    monto_base = models.DecimalField(max_digits=14, decimal_places=2)
    payload_resumen = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    estado_contable = models.CharField(
        max_length=32,
        choices=EstadoEventoContable.choices,
        default=EstadoEventoContable.PENDING,
    )

    class Meta:
        ordering = ['-fecha_operativa', '-id']

    def __str__(self):
        return self.idempotency_key


class AsientoContable(TimestampedModel):
    evento_contable = models.OneToOneField(
        EventoContable,
        on_delete=models.CASCADE,
        related_name='asiento_contable',
    )
    fecha_contable = models.DateField()
    periodo_contable = models.CharField(max_length=7)
    estado = models.CharField(max_length=16, choices=EstadoAsientoContable.choices, default=EstadoAsientoContable.POSTED)
    debe_total = models.DecimalField(max_digits=14, decimal_places=2)
    haber_total = models.DecimalField(max_digits=14, decimal_places=2)
    moneda_funcional = models.CharField(max_length=8, choices=[('CLP', 'CLP'), ('UF', 'UF')], default='CLP')
    hash_integridad = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['-fecha_contable', '-id']

    def __str__(self):
        return f'Asiento {self.id}'

    def clean(self):
        super().clean()
        if self.debe_total != self.haber_total:
            raise ValidationError('El asiento contable debe cuadrar debe = haber.')

    def set_hash_integridad(self):
        base = f'{self.evento_contable_id}|{self.fecha_contable}|{self.debe_total}|{self.haber_total}|{self.moneda_funcional}'
        self.hash_integridad = hashlib.sha256(base.encode('utf-8')).hexdigest()


class MovimientoAsiento(TimestampedModel):
    asiento_contable = models.ForeignKey(
        AsientoContable,
        on_delete=models.CASCADE,
        related_name='movimientos',
    )
    cuenta_contable = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        related_name='movimientos',
    )
    tipo_movimiento = models.CharField(max_length=8, choices=TipoMovimientoAsiento.choices)
    monto = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    glosa = models.CharField(max_length=255, blank=True)
    centro_resultado_ref = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ['asiento_contable_id', 'id']

    def __str__(self):
        return f'{self.asiento_contable_id} - {self.tipo_movimiento} {self.monto}'


class PoliticaReversoContable(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='politicas_reverso_contable',
    )
    tipo_ajuste = models.CharField(max_length=64)
    usa_reverso = models.BooleanField(default=False)
    usa_asiento_complementario = models.BooleanField(default=True)
    permite_reapertura = models.BooleanField(default=False)
    aprobacion_requerida = models.BooleanField(default=True)
    ventana_operativa = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['empresa_id', 'tipo_ajuste']

    def __str__(self):
        return f'{self.empresa_id} - {self.tipo_ajuste}'


class ObligacionTributariaMensual(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='obligaciones_tributarias_mensuales',
    )
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    obligacion_tipo = models.CharField(max_length=32)
    base_imponible = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_calculado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    estado_preparacion = models.CharField(
        max_length=32,
        choices=EstadoPreparacionTributaria.choices,
        default=EstadoPreparacionTributaria.PENDING_DATA,
    )
    detalle_calculo = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['empresa_id', '-anio', '-mes', 'obligacion_tipo']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'anio', 'mes', 'obligacion_tipo'],
                name='uniq_obligacion_tributaria_por_empresa_periodo_tipo',
            ),
        ]

    def __str__(self):
        return f'{self.empresa_id} {self.anio}-{self.mes} {self.obligacion_tipo}'


class LibroDiario(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='libros_diario',
    )
    periodo = models.CharField(max_length=7)
    estado_snapshot = models.CharField(max_length=16, choices=EstadoCierreMensual.choices, default=EstadoCierreMensual.PREPARED)
    storage_ref = models.CharField(max_length=255, blank=True)
    resumen = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['empresa_id', '-periodo']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'periodo'], name='uniq_libro_diario_por_empresa_periodo'),
        ]


class LibroMayor(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='libros_mayor',
    )
    periodo = models.CharField(max_length=7)
    estado_snapshot = models.CharField(max_length=16, choices=EstadoCierreMensual.choices, default=EstadoCierreMensual.PREPARED)
    storage_ref = models.CharField(max_length=255, blank=True)
    resumen = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['empresa_id', '-periodo']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'periodo'], name='uniq_libro_mayor_por_empresa_periodo'),
        ]


class BalanceComprobacion(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='balances_comprobacion',
    )
    periodo = models.CharField(max_length=7)
    estado_snapshot = models.CharField(max_length=16, choices=EstadoCierreMensual.choices, default=EstadoCierreMensual.PREPARED)
    storage_ref = models.CharField(max_length=255, blank=True)
    resumen = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['empresa_id', '-periodo']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'periodo'], name='uniq_balance_comprobacion_por_empresa_periodo'),
        ]


class CierreMensualContable(TimestampedModel):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='cierres_mensuales_contables',
    )
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    estado = models.CharField(max_length=16, choices=EstadoCierreMensual.choices, default=EstadoCierreMensual.DRAFT)
    fecha_preparacion = models.DateTimeField(null=True, blank=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    resumen_obligaciones = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['empresa_id', '-anio', '-mes']
        constraints = [
            models.UniqueConstraint(fields=['empresa', 'anio', 'mes'], name='uniq_cierre_mensual_por_empresa_periodo'),
        ]

    def __str__(self):
        return f'{self.empresa_id} {self.anio}-{self.mes}'
