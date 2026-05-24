from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from cobranza.models import CodigoCobroResidual, PagoMensual
from core.reference_validation import is_non_sensitive_reference
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


class OrigenImportacionMovimiento(models.TextChoices):
    MANUAL_CONTROLLED = 'manual_controlada', 'Manual controlada'
    PROVIDER_SYNC = 'provider_sync', 'Provider sync'


def has_text(value):
    return bool(str(value or '').strip())


def _add_non_sensitive_reference_error(errors, instance, field_name, message):
    value = getattr(instance, field_name, '')
    if has_text(value) and not is_non_sensitive_reference(value):
        errors[field_name] = message


class ConexionBancaria(TimestampedModel):
    cuenta_recaudadora = models.ForeignKey(
        CuentaRecaudadora,
        on_delete=models.CASCADE,
        related_name='conexiones_bancarias',
    )
    provider_key = models.CharField(max_length=64)
    credencial_ref = models.CharField(max_length=255)
    scope = models.CharField(max_length=255, blank=True)
    evidencia_gate_ref = models.CharField(max_length=255, blank=True)
    prueba_conectividad_ref = models.CharField(max_length=255, blank=True)
    prueba_movimientos_ref = models.CharField(max_length=255, blank=True)
    prueba_saldos_ref = models.CharField(max_length=255, blank=True)
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

    def clean(self):
        super().clean()
        errors = {}
        for field_name in [
            'credencial_ref',
            'evidencia_gate_ref',
            'prueba_conectividad_ref',
            'prueba_movimientos_ref',
            'prueba_saldos_ref',
        ]:
            _add_non_sensitive_reference_error(
                errors,
                self,
                field_name,
                f'{field_name} debe ser una referencia no sensible, no una URL, token o credencial.',
            )

        operational = (
            self.estado_conexion == EstadoConexionBancaria.ACTIVE
            or self.primaria_movimientos
            or self.primaria_saldos
            or self.primaria_conectividad
        )
        if operational:
            if self.estado_conexion != EstadoConexionBancaria.ACTIVE:
                errors['estado_conexion'] = 'Una conexion bancaria primaria debe estar activa.'
            if not has_text(self.credencial_ref):
                errors['credencial_ref'] = 'Una conexion bancaria operativa requiere credencial_ref trazable.'
            if not has_text(self.evidencia_gate_ref):
                errors['evidencia_gate_ref'] = 'Una conexion bancaria operativa requiere evidencia_gate_ref.'
            if not has_text(self.prueba_conectividad_ref):
                errors['prueba_conectividad_ref'] = 'Una conexion bancaria operativa requiere prueba_conectividad_ref.'
            if self.primaria_movimientos and not has_text(self.prueba_movimientos_ref):
                errors['prueba_movimientos_ref'] = 'Banca.Movimientos primaria requiere prueba_movimientos_ref.'
            if self.primaria_saldos:
                if not has_text(self.prueba_movimientos_ref):
                    errors['prueba_movimientos_ref'] = 'Banca.Saldos primaria requiere base Banca.Movimientos validada.'
                if not has_text(self.prueba_saldos_ref):
                    errors['prueba_saldos_ref'] = 'Banca.Saldos primaria requiere prueba_saldos_ref.'

        if errors:
            raise ValidationError(errors)


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
    origen_importacion = models.CharField(
        max_length=24,
        choices=OrigenImportacionMovimiento.choices,
        default=OrigenImportacionMovimiento.MANUAL_CONTROLLED,
    )
    evidencia_importacion_ref = models.CharField(max_length=255, blank=True)
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

    def clean(self):
        super().clean()
        errors = {}
        _add_non_sensitive_reference_error(
            errors,
            self,
            'evidencia_importacion_ref',
            'evidencia_importacion_ref debe ser una referencia no sensible, no una URL, token o credencial.',
        )
        _add_non_sensitive_reference_error(
            errors,
            self,
            'transaction_id_banco',
            'transaction_id_banco debe ser una referencia no sensible, no una URL, token o credencial.',
        )

        if self.origen_importacion == OrigenImportacionMovimiento.MANUAL_CONTROLLED:
            if not has_text(self.evidencia_importacion_ref):
                errors['evidencia_importacion_ref'] = 'La carga manual bancaria requiere evidencia_importacion_ref.'
            if errors:
                raise ValidationError(errors)
            return

        if self.origen_importacion == OrigenImportacionMovimiento.PROVIDER_SYNC:
            if not has_text(self.transaction_id_banco):
                errors['transaction_id_banco'] = 'Provider sync requiere transaction_id_banco trazable.'
            try:
                conexion = self.conexion_bancaria
            except ConexionBancaria.DoesNotExist:
                conexion = None
            reason = bank_provider_sync_blocking_reason(conexion)
            if reason:
                errors['conexion_bancaria'] = reason

        if errors:
            raise ValidationError(errors)


def bank_provider_sync_blocking_reason(conexion):
    if conexion is None:
        return ''
    if conexion.estado_conexion != EstadoConexionBancaria.ACTIVE:
        return 'Banca.Movimientos requiere conexion bancaria activa.'
    if not conexion.primaria_movimientos:
        return 'Banca.Movimientos requiere conexion primaria_movimientos.'
    if not is_non_sensitive_reference(conexion.credencial_ref):
        return 'Banca.Movimientos requiere credencial_ref trazable no sensible.'
    if not is_non_sensitive_reference(conexion.evidencia_gate_ref):
        return 'Banca.Movimientos requiere evidencia_gate_ref no sensible.'
    if not is_non_sensitive_reference(conexion.prueba_conectividad_ref):
        return 'Banca.Movimientos requiere prueba_conectividad_ref no sensible.'
    if not is_non_sensitive_reference(conexion.prueba_movimientos_ref):
        return 'Banca.Movimientos requiere prueba_movimientos_ref no sensible.'
    return ''


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

    def clean(self):
        super().clean()
        errors = {}
        try:
            movimiento = self.movimiento_bancario
        except MovimientoBancarioImportado.DoesNotExist:
            movimiento = None

        if movimiento is None:
            return

        if movimiento.tipo_movimiento != TipoMovimientoBancario.CREDIT:
            errors['movimiento_bancario'] = 'Un ingreso desconocido solo puede originarse en un abono bancario.'

        if self.cuenta_recaudadora_id != movimiento.conexion_bancaria.cuenta_recaudadora_id:
            errors['cuenta_recaudadora'] = 'La cuenta recaudadora debe coincidir con la conexion del movimiento.'

        if Decimal(str(self.monto)) != Decimal(str(movimiento.monto)):
            errors['monto'] = 'El monto del ingreso desconocido debe coincidir con el movimiento bancario.'
        if self.fecha_movimiento != movimiento.fecha_movimiento:
            errors['fecha_movimiento'] = 'La fecha del ingreso desconocido debe coincidir con el movimiento bancario.'
        if self.descripcion_origen != movimiento.descripcion_origen:
            errors['descripcion_origen'] = 'La descripcion debe coincidir con el movimiento bancario.'

        if self.estado == EstadoIngresoDesconocido.OPEN:
            if movimiento.estado_conciliacion != EstadoConciliacionMovimiento.UNKNOWN_INCOME:
                errors['estado'] = 'Un ingreso desconocido abierto requiere movimiento en estado ingreso_desconocido.'
            if movimiento.pago_mensual_id or movimiento.codigo_cobro_residual_id:
                errors['movimiento_bancario'] = 'Un ingreso desconocido abierto no puede tener target conciliado.'

        if (
            self.estado == EstadoIngresoDesconocido.RESOLVED
            and movimiento.estado_conciliacion == EstadoConciliacionMovimiento.UNKNOWN_INCOME
        ):
            errors['estado'] = 'Un ingreso desconocido resuelto no puede conservar movimiento en ingreso_desconocido.'

        if errors:
            raise ValidationError(errors)

