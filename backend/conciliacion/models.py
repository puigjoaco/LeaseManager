from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from cobranza.models import CodigoCobroResidual, PagoMensual
from operacion.models import CuentaRecaudadora


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoConexionBancaria(models.TextChoices):
    VERIFYING = 'verificando', 'Verificando'
    ACTIVE = 'activa', 'Activa'
    PAUSED = 'pausada', 'Pausada'
    INACTIVE = 'inactiva', 'Inactiva'


class TipoMovimientoBancario(models.TextChoices):
    CREDIT = 'abono', 'Abono'
    DEBIT = 'cargo', 'Cargo'


class EstadoConciliacionMovimiento(models.TextChoices):
    PENDING = 'pendiente', 'Pendiente'
    EXACT_MATCH = 'conciliado_exacto', 'Conciliado exacto'
    UNKNOWN_INCOME = 'ingreso_desconocido', 'Ingreso desconocido'
    MANUAL_REQUIRED = 'manual_requerida', 'Manual requerida'


class EstadoIngresoDesconocido(models.TextChoices):
    OPEN = 'pendiente_revision', 'Pendiente revision'
    RESOLVED = 'resuelto', 'Resuelto'
    DISMISSED = 'descartado', 'Descartado'


class ConexionBancaria(TimestampedModel):
    cuenta_recaudadora = models.ForeignKey(
        CuentaRecaudadora,
        on_delete=models.CASCADE,
        related_name='conexiones_bancarias',
    )
    provider_key = models.CharField(max_length=64)
    credencial_ref = models.CharField(max_length=255)
    scope = models.CharField(max_length=255, blank=True)
    expira_en = models.DateTimeField(null=True, blank=True)
    estado_conexion = models.CharField(
        max_length=16,
        choices=EstadoConexionBancaria.choices,
        default=EstadoConexionBancaria.VERIFYING,
    )
    primaria_movimientos = models.BooleanField(default=False)
    primaria_saldos = models.BooleanField(default=False)
    primaria_conectividad = models.BooleanField(default=False)
    ultimo_exito_at = models.DateTimeField(null=True, blank=True)
    ultimo_error_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['cuenta_recaudadora_id', 'provider_key']
        constraints = [
            models.UniqueConstraint(
                fields=['cuenta_recaudadora', 'provider_key'],
                name='uniq_provider_por_cuenta_recaudadora',
            ),
            models.UniqueConstraint(
                fields=['cuenta_recaudadora'],
                condition=Q(primaria_movimientos=True),
                name='uniq_primaria_movimientos_por_cuenta',
            ),
            models.UniqueConstraint(
                fields=['cuenta_recaudadora'],
                condition=Q(primaria_saldos=True),
                name='uniq_primaria_saldos_por_cuenta',
            ),
            models.UniqueConstraint(
                fields=['cuenta_recaudadora'],
                condition=Q(primaria_conectividad=True),
                name='uniq_primaria_conectividad_por_cuenta',
            ),
        ]

    def __str__(self):
        return f'{self.cuenta_recaudadora_id} - {self.provider_key}'


class MovimientoBancarioImportado(TimestampedModel):
    conexion_bancaria = models.ForeignKey(
        ConexionBancaria,
        on_delete=models.CASCADE,
        related_name='movimientos_importados',
    )
    fecha_movimiento = models.DateField()
    tipo_movimiento = models.CharField(max_length=8, choices=TipoMovimientoBancario.choices)
    monto = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    descripcion_origen = models.TextField()
    numero_documento = models.CharField(max_length=64, blank=True)
    saldo_reportado = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    referencia = models.CharField(max_length=255, blank=True)
    transaction_id_banco = models.CharField(max_length=255, blank=True)
    estado_conciliacion = models.CharField(
        max_length=24,
        choices=EstadoConciliacionMovimiento.choices,
        default=EstadoConciliacionMovimiento.PENDING,
    )
    pago_mensual = models.ForeignKey(
        PagoMensual,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='movimientos_bancarios',
    )
    codigo_cobro_residual = models.ForeignKey(
        CodigoCobroResidual,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='movimientos_bancarios',
    )
    notas_admin = models.TextField(blank=True)

    class Meta:
        ordering = ['-fecha_movimiento', '-id']
        constraints = [
            models.CheckConstraint(
                check=(
                    Q(pago_mensual__isnull=False, codigo_cobro_residual__isnull=True)
                    | Q(pago_mensual__isnull=True, codigo_cobro_residual__isnull=False)
                    | Q(pago_mensual__isnull=True, codigo_cobro_residual__isnull=True)
                ),
                name='movimiento_exactly_one_match_target',
            ),
        ]

    def __str__(self):
        return f'{self.fecha_movimiento} - {self.monto}'


class IngresoDesconocido(TimestampedModel):
    movimiento_bancario = models.OneToOneField(
        MovimientoBancarioImportado,
        on_delete=models.CASCADE,
        related_name='ingreso_desconocido',
    )
    cuenta_recaudadora = models.ForeignKey(
        CuentaRecaudadora,
        on_delete=models.PROTECT,
        related_name='ingresos_desconocidos',
    )
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_movimiento = models.DateField()
    descripcion_origen = models.TextField()
    estado = models.CharField(
        max_length=24,
        choices=EstadoIngresoDesconocido.choices,
        default=EstadoIngresoDesconocido.OPEN,
    )
    sugerencia_asistida = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-fecha_movimiento', '-id']

    def __str__(self):
        return f'IngresoDesconocido {self.movimiento_bancario_id}'

