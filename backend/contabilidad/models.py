import hashlib
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from patrimonio.models import ComunidadPatrimonial, Empresa, Socio


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


class EstadoLiquidacionMensual(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparada', 'Preparada'
    APPROVED = 'aprobada', 'Aprobada'
    OBSERVED = 'observada', 'Observada'


class TipoOwnerLiquidacion(models.TextChoices):
    COMPANY = 'empresa', 'Empresa'
    COMMUNITY = 'comunidad', 'Comunidad'
    PARTNER = 'socio', 'Socio'


class TipoLineaLiquidacion(models.TextChoices):
    RENT_INCOME = 'ingreso_arriendo', 'Ingreso arriendo'
    OPERATING_EXPENSE = 'egreso_operativo', 'Egreso operativo'
    ADMINISTRATION_FEE = 'comision_administracion', 'Comision administracion'
    PARTNER_DISTRIBUTION = 'distribucion_socio', 'Distribucion socio'
    TAX_PROVISION = 'provision_impuesto', 'Provision impuesto'
    ADJUSTMENT = 'ajuste', 'Ajuste'
    FINAL_BALANCE = 'saldo_final_explicado', 'Saldo final explicado'


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


class TipoEfectoReaperturaCierre(models.TextChoices):
    REVERSAL = 'reverso', 'Reverso'
    COMPLEMENTARY_ENTRY = 'asiento_complementario', 'Asiento complementario'


def has_text(value):
    return bool(str(value or '').strip())


def _add_non_sensitive_reference_error(errors, instance, field_name):
    value = getattr(instance, field_name, '')
    if has_text(value) and not is_non_sensitive_reference(value):
        errors[field_name] = f'{field_name} debe ser una referencia no sensible, no una URL, token o credencial.'


def _add_non_sensitive_payload_error(errors, field_name, value):
    if value and contains_sensitive_reference(value, include_sensitive_keys=True):
        errors[field_name] = f'{field_name} no debe contener URLs, tokens, credenciales ni correos.'


def _normalize_text_fields(instance, field_names):
    for field_name in field_names:
        setattr(instance, field_name, str(getattr(instance, field_name, '') or '').strip())


class OperationalTextNormalizationMixin:
    operational_text_fields = ()

    def _normalize_operational_fields(self):
        _normalize_text_fields(self, self.operational_text_fields)

    def full_clean(self, *args, **kwargs):
        self._normalize_operational_fields()
        super().full_clean(*args, **kwargs)

    def clean(self):
        self._normalize_operational_fields()
        super().clean()

    def save(self, *args, **kwargs):
        self._normalize_operational_fields()
        super().save(*args, **kwargs)


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
        if self.estado == EstadoRegistro.ACTIVE and self.regimen_tributario.estado != EstadoRegistro.ACTIVE:
            raise ValidationError(
                {'regimen_tributario': 'La configuracion fiscal activa requiere un regimen tributario activo.'}
            )


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
        errors = {}
        if self.vigencia_hasta and self.vigencia_hasta < self.vigencia_desde:
            errors['vigencia_hasta'] = 'La vigencia final no puede ser anterior a la inicial.'
        if (
            self.estado == EstadoRegistro.ACTIVE
            and self.empresa_id
            and has_text(self.evento_tipo)
            and has_text(self.plan_cuentas_version)
            and self.vigencia_desde
        ):
            overlapping_rules = ReglaContable.objects.filter(
                empresa_id=self.empresa_id,
                evento_tipo=self.evento_tipo,
                plan_cuentas_version=self.plan_cuentas_version,
                estado=EstadoRegistro.ACTIVE,
            ).filter(
                Q(vigencia_hasta__isnull=True) | Q(vigencia_hasta__gte=self.vigencia_desde)
            )
            if self.vigencia_hasta:
                overlapping_rules = overlapping_rules.filter(vigencia_desde__lte=self.vigencia_hasta)
            if self.pk:
                overlapping_rules = overlapping_rules.exclude(pk=self.pk)
            if overlapping_rules.exists():
                errors['vigencia_desde'] = (
                    'No puede existir otra regla contable activa solapada para la misma empresa, '
                    'tipo de evento y version del plan de cuentas.'
                )
        if errors:
            raise ValidationError(errors)


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

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_payload_error(errors, 'payload_resumen', self.payload_resumen)
        if self.estado_contable == EstadoEventoContable.POSTED and self.empresa_id:
            duplicate_query = EventoContable.objects.filter(
                empresa_id=self.empresa_id,
                evento_tipo=self.evento_tipo,
                entidad_origen_tipo=self.entidad_origen_tipo,
                entidad_origen_id=self.entidad_origen_id,
                estado_contable=EstadoEventoContable.POSTED,
            )
            if self.pk:
                duplicate_query = duplicate_query.exclude(pk=self.pk)
            if duplicate_query.exists():
                errors['entidad_origen_id'] = (
                    'Ya existe un evento contable contabilizado para la misma empresa, tipo y entidad origen.'
                )
        if errors:
            raise ValidationError(errors)


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
        errors = {}
        if self.debe_total != self.haber_total:
            errors['__all__'] = 'El asiento contable debe cuadrar debe = haber.'
        if self.fecha_contable and self.periodo_contable:
            expected_period = str(self.fecha_contable)[:7]
            if self.periodo_contable != expected_period:
                errors['periodo_contable'] = 'periodo_contable debe coincidir con fecha_contable.'
        if self.estado == EstadoAsientoContable.POSTED:
            if not has_text(self.hash_integridad):
                errors['hash_integridad'] = 'El asiento contabilizado requiere hash de integridad.'
            elif not self.hash_integridad_matches():
                errors['hash_integridad'] = 'hash_integridad no corresponde al contenido actual del asiento.'
        if errors:
            raise ValidationError(errors)

    def expected_hash_integridad(self):
        base = f'{self.evento_contable_id}|{self.fecha_contable}|{self.debe_total}|{self.haber_total}|{self.moneda_funcional}'
        return hashlib.sha256(base.encode('utf-8')).hexdigest()

    def hash_integridad_matches(self):
        return has_text(self.hash_integridad) and self.hash_integridad == self.expected_hash_integridad()

    def set_hash_integridad(self):
        self.hash_integridad = self.expected_hash_integridad()


class MovimientoAsiento(OperationalTextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('glosa', 'centro_resultado_ref')

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

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'centro_resultado_ref')
        if self.asiento_contable_id and self.cuenta_contable_id:
            asiento_empresa_id = self.asiento_contable.evento_contable.empresa_id
            cuenta_empresa_id = self.cuenta_contable.empresa_id
            if asiento_empresa_id != cuenta_empresa_id:
                errors['cuenta_contable'] = (
                    'La cuenta contable debe pertenecer a la misma empresa del evento contable.'
                )
        if errors:
            raise ValidationError(errors)


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

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_payload_error(errors, 'detalle_calculo', self.detalle_calculo)
        if errors:
            raise ValidationError(errors)


class LedgerSnapshotValidationMixin(OperationalTextNormalizationMixin):
    operational_text_fields = ('storage_ref',)

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'storage_ref')
        _add_non_sensitive_payload_error(errors, 'resumen', self.resumen)
        if errors:
            raise ValidationError(errors)


class LibroDiario(LedgerSnapshotValidationMixin, TimestampedModel):
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


class LibroMayor(LedgerSnapshotValidationMixin, TimestampedModel):
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


class BalanceComprobacion(LedgerSnapshotValidationMixin, TimestampedModel):
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

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_payload_error(errors, 'resumen_obligaciones', self.resumen_obligaciones)
        if errors:
            raise ValidationError(errors)


class LiquidacionMensual(OperationalTextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'saldo_final_explicacion',
        'saldo_final_evidencia_ref',
        'evidencia_base_ref',
        'responsable_ref',
    )

    owner_tipo = models.CharField(max_length=16, choices=TipoOwnerLiquidacion.choices)
    empresa = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='liquidaciones_mensuales',
    )
    comunidad = models.ForeignKey(
        ComunidadPatrimonial,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='liquidaciones_mensuales',
    )
    socio = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='liquidaciones_mensuales',
    )
    cierre_contable = models.ForeignKey(
        CierreMensualContable,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='liquidaciones_mensuales',
    )
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    estado = models.CharField(
        max_length=16,
        choices=EstadoLiquidacionMensual.choices,
        default=EstadoLiquidacionMensual.DRAFT,
    )
    comision_administracion_aplica = models.BooleanField(default=False)
    saldo_final_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    saldo_final_explicacion = models.CharField(max_length=255, blank=True)
    saldo_final_evidencia_ref = models.CharField(max_length=255, blank=True)
    evidencia_base_ref = models.CharField(max_length=255, blank=True)
    responsable_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['owner_tipo', '-anio', '-mes', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'anio', 'mes'],
                condition=Q(owner_tipo=TipoOwnerLiquidacion.COMPANY, empresa__isnull=False),
                name='uniq_liquidacion_empresa_periodo',
            ),
            models.UniqueConstraint(
                fields=['comunidad', 'anio', 'mes'],
                condition=Q(owner_tipo=TipoOwnerLiquidacion.COMMUNITY, comunidad__isnull=False),
                name='uniq_liquidacion_comunidad_periodo',
            ),
            models.UniqueConstraint(
                fields=['socio', 'anio', 'mes'],
                condition=Q(owner_tipo=TipoOwnerLiquidacion.PARTNER, socio__isnull=False),
                name='uniq_liquidacion_socio_periodo',
            ),
        ]

    def __str__(self):
        return f'{self.owner_tipo} {self.anio}-{self.mes:02d}'

    def saldo_final_line_total(self):
        if not self.pk:
            return Decimal('0.00')
        return self.lineas.filter(tipo_linea=TipoLineaLiquidacion.FINAL_BALANCE).aggregate(
            total=Sum('monto_clp')
        )['total'] or Decimal('0.00')

    def has_saldo_final_line(self):
        return bool(
            self.pk
            and self.lineas.filter(tipo_linea=TipoLineaLiquidacion.FINAL_BALANCE).exists()
        )

    def clean(self):
        super().clean()
        errors = {}
        owner_values = {
            TipoOwnerLiquidacion.COMPANY: self.empresa_id,
            TipoOwnerLiquidacion.COMMUNITY: self.comunidad_id,
            TipoOwnerLiquidacion.PARTNER: self.socio_id,
        }
        selected_owners = [value for value in owner_values.values() if value]
        if len(selected_owners) != 1:
            errors['owner_tipo'] = 'La liquidacion mensual debe tener exactamente un owner operativo.'
        elif not owner_values.get(self.owner_tipo):
            errors['owner_tipo'] = 'owner_tipo debe coincidir con el owner informado.'

        for field_name in ('evidencia_base_ref', 'responsable_ref', 'saldo_final_evidencia_ref'):
            _add_non_sensitive_reference_error(errors, self, field_name)
        _add_non_sensitive_payload_error(errors, 'saldo_final_explicacion', self.saldo_final_explicacion)

        prepared_or_approved = self.estado in {
            EstadoLiquidacionMensual.PREPARED,
            EstadoLiquidacionMensual.APPROVED,
        }
        if prepared_or_approved:
            if not has_text(self.evidencia_base_ref):
                errors['evidencia_base_ref'] = 'La liquidacion preparada requiere evidencia base no sensible.'
            if not has_text(self.responsable_ref):
                errors['responsable_ref'] = 'La liquidacion preparada requiere responsable no sensible.'
            if self.owner_tipo == TipoOwnerLiquidacion.COMPANY and not self.cierre_contable_id:
                errors['cierre_contable'] = 'La liquidacion de empresa preparada requiere cierre contable trazable.'

        if self.saldo_final_clp != Decimal('0.00'):
            if not has_text(self.saldo_final_explicacion):
                errors['saldo_final_explicacion'] = 'Un saldo final distinto de cero requiere explicacion.'
            if not has_text(self.saldo_final_evidencia_ref):
                errors['saldo_final_evidencia_ref'] = 'Un saldo final distinto de cero requiere evidencia no sensible.'
            if prepared_or_approved:
                if not self.has_saldo_final_line():
                    errors['saldo_final_clp'] = (
                        'Un saldo final distinto de cero debe quedar como linea explicita de saldo final explicado.'
                    )
                elif self.saldo_final_line_total() != self.saldo_final_clp:
                    errors['saldo_final_clp'] = (
                        'Las lineas de saldo final explicado deben cuadrar con saldo_final_clp.'
                    )

        if self.cierre_contable_id:
            if self.cierre_contable.anio != self.anio or self.cierre_contable.mes != self.mes:
                errors['cierre_contable'] = 'El cierre contable debe corresponder al periodo de la liquidacion.'
            if self.empresa_id and self.cierre_contable.empresa_id != self.empresa_id:
                errors['cierre_contable'] = 'El cierre contable debe pertenecer a la misma empresa.'
            if self.estado == EstadoLiquidacionMensual.APPROVED and self.cierre_contable.estado != EstadoCierreMensual.APPROVED:
                errors['cierre_contable'] = 'La liquidacion aprobada requiere cierre contable aprobado.'

        if (
            prepared_or_approved
            and self.comision_administracion_aplica
            and (
                not self.pk
                or not self.lineas.filter(tipo_linea=TipoLineaLiquidacion.ADMINISTRATION_FEE).exists()
            )
        ):
            errors['comision_administracion_aplica'] = (
                'La comision de administracion aplicable debe quedar como linea explicita.'
            )

        if errors:
            raise ValidationError(errors)


class LineaLiquidacionMensual(OperationalTextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('descripcion', 'evidencia_ref')

    liquidacion = models.ForeignKey(
        LiquidacionMensual,
        on_delete=models.CASCADE,
        related_name='lineas',
    )
    tipo_linea = models.CharField(max_length=32, choices=TipoLineaLiquidacion.choices)
    descripcion = models.CharField(max_length=255)
    monto_clp = models.DecimalField(max_digits=14, decimal_places=2)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    beneficiario_socio = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='lineas_liquidacion_beneficiario',
    )
    evento_contable = models.ForeignKey(
        EventoContable,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='lineas_liquidacion',
    )

    class Meta:
        ordering = ['liquidacion_id', 'id']

    def __str__(self):
        return f'{self.liquidacion_id} - {self.tipo_linea} {self.monto_clp}'

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_payload_error(errors, 'descripcion', self.descripcion)
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')

        if self.monto_clp == Decimal('0.00'):
            errors['monto_clp'] = 'La linea de liquidacion debe tener monto distinto de cero.'

        if self.tipo_linea in {
            TipoLineaLiquidacion.ADMINISTRATION_FEE,
            TipoLineaLiquidacion.PARTNER_DISTRIBUTION,
        }:
            if self.monto_clp <= Decimal('0.00'):
                errors['monto_clp'] = 'Comisiones y distribuciones deben registrarse con monto positivo.'
            if not self.beneficiario_socio_id:
                errors['beneficiario_socio'] = 'La linea requiere socio beneficiario trazable.'
            if not has_text(self.evidencia_ref):
                errors['evidencia_ref'] = 'La linea requiere evidencia no sensible.'

        if self.tipo_linea == TipoLineaLiquidacion.FINAL_BALANCE and not has_text(self.evidencia_ref):
            errors['evidencia_ref'] = 'La explicacion de saldo final requiere evidencia no sensible.'

        if self.liquidacion_id and self.evento_contable_id:
            if self.liquidacion.empresa_id and self.evento_contable.empresa_id != self.liquidacion.empresa_id:
                errors['evento_contable'] = 'El evento contable debe pertenecer a la empresa de la liquidacion.'

        if (
            self.liquidacion_id
            and self.liquidacion.estado in {EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED}
            and self.tipo_linea
            in {
                TipoLineaLiquidacion.RENT_INCOME,
                TipoLineaLiquidacion.OPERATING_EXPENSE,
                TipoLineaLiquidacion.ADMINISTRATION_FEE,
                TipoLineaLiquidacion.PARTNER_DISTRIBUTION,
                TipoLineaLiquidacion.TAX_PROVISION,
                TipoLineaLiquidacion.ADJUSTMENT,
            }
            and not self.evento_contable_id
        ):
            errors['evento_contable'] = 'La linea economica preparada requiere traza a evento contable.'

        if errors:
            raise ValidationError(errors)


class EfectoReaperturaCierreMensual(OperationalTextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('motivo', 'efecto_esperado', 'evidencia_ref')

    cierre = models.ForeignKey(
        CierreMensualContable,
        on_delete=models.CASCADE,
        related_name='efectos_reapertura',
    )
    politica_reverso = models.ForeignKey(
        PoliticaReversoContable,
        on_delete=models.PROTECT,
        related_name='efectos_reapertura',
    )
    evento_contable = models.OneToOneField(
        EventoContable,
        on_delete=models.PROTECT,
        related_name='efecto_reapertura_cierre',
    )
    tipo_efecto = models.CharField(max_length=32, choices=TipoEfectoReaperturaCierre.choices)
    monto_efecto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    motivo = models.CharField(max_length=255)
    efecto_esperado = models.CharField(max_length=255)
    evidencia_ref = models.CharField(max_length=255)
    fecha_aplicacion = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['cierre_id', 'created_at', 'id']

    def __str__(self):
        return f'{self.cierre_id} - {self.tipo_efecto}'

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')
        _add_non_sensitive_payload_error(errors, 'motivo', self.motivo)
        _add_non_sensitive_payload_error(errors, 'efecto_esperado', self.efecto_esperado)
        if self.cierre_id and self.politica_reverso_id:
            if self.cierre.empresa_id != self.politica_reverso.empresa_id:
                errors['politica_reverso'] = 'La politica debe pertenecer a la misma empresa del cierre.'
            if self.tipo_efecto == TipoEfectoReaperturaCierre.REVERSAL and not self.politica_reverso.usa_reverso:
                errors['tipo_efecto'] = 'La politica no permite reverso para esta reapertura.'
            if (
                self.tipo_efecto == TipoEfectoReaperturaCierre.COMPLEMENTARY_ENTRY
                and not self.politica_reverso.usa_asiento_complementario
            ):
                errors['tipo_efecto'] = 'La politica no permite asiento complementario para esta reapertura.'
        if self.cierre_id and self.evento_contable_id:
            if self.cierre.empresa_id != self.evento_contable.empresa_id:
                errors['evento_contable'] = 'El evento contable debe pertenecer a la misma empresa del cierre.'
        if errors:
            raise ValidationError(errors)
