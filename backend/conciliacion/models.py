import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils.dateparse import parse_date

from cobranza.models import CodigoCobroResidual, EstadoCobroResidual, EstadoPago, PagoMensual
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
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


class CategoriaMovimiento(models.TextChoices):
    BANK_COMMISSION = 'comision_bancaria', 'Comision bancaria'
    GUARANTEE = 'garantia', 'Garantia'
    PPM = 'ppm', 'PPM'
    INTERNAL_TRANSFER = 'transferencia_interna', 'Transferencia interna'
    PARTNER_SETTLEMENT = 'liquidacion_socio', 'Liquidacion a socio'
    REIMBURSEMENT = 'reintegro', 'Reintegro'
    WRONG_ENTITY_EXPENSE = 'gasto_entidad_equivocada', 'Gasto pagado por entidad equivocada'
    RESIDUAL_COLLECTION = 'cobranza_residual', 'Cobranza residual'
    REGULARIZATION = 'regularizacion', 'Regularizacion'


class EstadoConciliacionMovimiento(models.TextChoices):
    PENDING = 'pendiente', 'Pendiente'
    EXACT_MATCH = 'conciliado_exacto', 'Conciliado exacto'
    UNKNOWN_INCOME = 'ingreso_desconocido', 'Ingreso desconocido'
    MANUAL_REQUIRED = 'manual_requerida', 'Manual requerida'


class EstadoIngresoDesconocido(models.TextChoices):
    OPEN = 'pendiente_revision', 'Pendiente revision'
    RESOLVED = 'resuelto', 'Resuelto'
    DISMISSED = 'descartado', 'Descartado'


class EstadoCuadraturaBancaria(models.TextChoices):
    SQUARED = 'cuadrada', 'Cuadrada'
    OPEN_DIFFERENCE = 'diferencia_abierta', 'Diferencia abierta'
    EXPLAINED_DIFFERENCE = 'diferencia_explicada', 'Diferencia explicada'


class OrigenImportacionMovimiento(models.TextChoices):
    MANUAL_CONTROLLED = 'manual_controlada', 'Manual controlada'
    PROVIDER_SYNC = 'provider_sync', 'Provider sync'


ECONOMIC_PERIOD_RE = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')


def has_text(value):
    return bool(str(value or '').strip())


def _add_non_sensitive_reference_error(errors, instance, field_name, message):
    value = getattr(instance, field_name, '')
    if has_text(value) and not is_non_sensitive_reference(value):
        errors[field_name] = message


def _add_sensitive_text_error(errors, instance, field_name, message):
    value = getattr(instance, field_name, '')
    if has_text(value) and contains_sensitive_reference(value):
        errors[field_name] = message


def _append_error(errors, field_name, message):
    current = errors.get(field_name)
    if current is None:
        errors[field_name] = message
    elif isinstance(current, list):
        current.append(message)
    else:
        errors[field_name] = [current, message]


def _coerce_date(value):
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value
    if isinstance(value, str):
        return parse_date(value)
    return None


def _period_from_date(value):
    date_value = _coerce_date(value)
    if date_value is None:
        return ''
    return f'{date_value.year:04d}-{date_value.month:02d}'


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

    def _normalize_operational_fields(self):
        self.provider_key = (self.provider_key or '').strip()
        self.scope = (self.scope or '').strip()
        self.credencial_ref = (self.credencial_ref or '').strip()
        self.evidencia_gate_ref = (self.evidencia_gate_ref or '').strip()
        self.prueba_conectividad_ref = (self.prueba_conectividad_ref or '').strip()
        self.prueba_movimientos_ref = (self.prueba_movimientos_ref or '').strip()
        self.prueba_saldos_ref = (self.prueba_saldos_ref or '').strip()

    def clean(self):
        super().clean()
        errors = {}
        self._normalize_operational_fields()
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

    def save(self, *args, **kwargs):
        self._normalize_operational_fields()
        super().save(*args, **kwargs)


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
            models.UniqueConstraint(
                fields=['conexion_bancaria', 'transaction_id_banco'],
                condition=~Q(transaction_id_banco=''),
                name='uniq_transaction_id_banco_por_conexion',
            ),
        ]

    def __str__(self):
        return f'{self.fecha_movimiento} - {self.monto}'

    def _normalize_operational_fields(self):
        self.evidencia_importacion_ref = (self.evidencia_importacion_ref or '').strip()
        self.referencia = (self.referencia or '').strip()
        self.transaction_id_banco = (self.transaction_id_banco or '').strip()
        self.notas_admin = (self.notas_admin or '').strip()

    def _validate_bank_transaction_identity(self, errors):
        transaction_id = str(self.transaction_id_banco or '').strip()
        if not transaction_id:
            return

        try:
            conexion = self.conexion_bancaria
        except ConexionBancaria.DoesNotExist:
            conexion = None
        connection_id = self.conexion_bancaria_id or getattr(conexion, 'pk', None)

        if not connection_id:
            return

        duplicates = MovimientoBancarioImportado.objects.filter(
            conexion_bancaria_id=connection_id,
            transaction_id_banco=transaction_id,
        )
        if self.pk:
            duplicates = duplicates.exclude(pk=self.pk)
        if duplicates.exists():
            _append_error(
                errors,
                'transaction_id_banco',
                'transaction_id_banco debe ser unico por conexion bancaria.',
            )

    def _validate_reconciliation_snapshot(self, errors):
        has_payment_target = bool(self.pago_mensual_id)
        has_residual_target = bool(self.codigo_cobro_residual_id)
        target_count = int(has_payment_target) + int(has_residual_target)

        if target_count > 1:
            _append_error(
                errors,
                'pago_mensual',
                'Un movimiento bancario solo puede apuntar a un pago mensual o a un codigo residual.',
            )
            return

        if self.estado_conciliacion != EstadoConciliacionMovimiento.EXACT_MATCH:
            if target_count:
                _append_error(
                    errors,
                    'estado_conciliacion',
                    'Solo un movimiento conciliado exacto puede conservar target conciliado.',
                )
            return

        if self.tipo_movimiento == TipoMovimientoBancario.DEBIT:
            if target_count:
                _append_error(
                    errors,
                    'estado_conciliacion',
                    'Un cargo conciliado exacto no puede apuntar a pagos mensuales ni codigos residuales.',
                )
            return

        if self.tipo_movimiento != TipoMovimientoBancario.CREDIT:
            return

        if target_count == 0:
            if self._has_internal_transfer_pair():
                return
            _append_error(
                errors,
                'pago_mensual',
                'Un abono conciliado exacto requiere pago mensual o codigo residual trazable.',
            )
            return

        try:
            conexion = self.conexion_bancaria
        except ConexionBancaria.DoesNotExist:
            conexion = None
        connection_account_id = conexion.cuenta_recaudadora_id if conexion is not None else None
        movement_amount = Decimal(str(self.monto))
        movement_date = _coerce_date(self.fecha_movimiento)

        if has_payment_target:
            try:
                payment = self.pago_mensual
            except PagoMensual.DoesNotExist:
                payment = None
            if payment is None:
                return

            payment_account_id = payment.contrato.mandato_operacion.cuenta_recaudadora_id
            if connection_account_id is not None and payment_account_id != connection_account_id:
                _append_error(
                    errors,
                    'pago_mensual',
                    'El pago conciliado debe pertenecer a la misma cuenta recaudadora del movimiento.',
                )
            if payment.estado_pago != EstadoPago.PAID:
                _append_error(errors, 'pago_mensual', 'El pago mensual target debe estar pagado.')
            if Decimal(str(payment.monto_pagado_clp)) < movement_amount:
                _append_error(
                    errors,
                    'pago_mensual',
                    'El monto del movimiento no puede exceder el monto pagado del pago mensual.',
                )
            if Decimal(str(payment.monto_calculado_clp)) < movement_amount:
                _append_error(
                    errors,
                    'pago_mensual',
                    'El monto del movimiento no puede exceder el monto calculado del pago mensual.',
                )
            if movement_date and (payment.anio != movement_date.year or payment.mes != movement_date.month):
                _append_error(
                    errors,
                    'pago_mensual',
                    'El periodo del pago mensual debe coincidir con el periodo del movimiento bancario.',
                )
            if _coerce_date(payment.fecha_deposito_banco) != movement_date:
                _append_error(
                    errors,
                    'pago_mensual',
                    'La fecha de deposito del pago debe coincidir con la fecha del movimiento bancario.',
                )
            return

        try:
            residual = self.codigo_cobro_residual
        except CodigoCobroResidual.DoesNotExist:
            residual = None
        if residual is None:
            return

        residual_account_id = residual.contrato_origen.mandato_operacion.cuenta_recaudadora_id
        if connection_account_id is not None and residual_account_id != connection_account_id:
            _append_error(
                errors,
                'codigo_cobro_residual',
                'El codigo residual debe pertenecer a la misma cuenta recaudadora del movimiento.',
            )
        if residual.estado != EstadoCobroResidual.PAID:
            _append_error(errors, 'codigo_cobro_residual', 'El codigo residual target debe estar pagado.')
        if Decimal(str(residual.saldo_actual)) != Decimal('0.00'):
            _append_error(
                errors,
                'codigo_cobro_residual',
                'El codigo residual pagado debe quedar con saldo_actual cero.',
            )

    def _has_internal_transfer_pair(self):
        if not self.pk:
            return False
        return (
            self.transferencias_intercuenta_origen.exists()
            or self.transferencias_intercuenta_destino.exists()
        )

    def clean(self):
        super().clean()
        errors = {}
        self._normalize_operational_fields()
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
        _add_non_sensitive_reference_error(
            errors,
            self,
            'referencia',
            'referencia debe ser una referencia bancaria no sensible, no una URL, token o credencial.',
        )
        _add_sensitive_text_error(
            errors,
            self,
            'notas_admin',
            'notas_admin no puede contener URLs, tokens, correos ni credenciales bancarias.',
        )

        self._validate_bank_transaction_identity(errors)
        self._validate_reconciliation_snapshot(errors)

        if self.origen_importacion == OrigenImportacionMovimiento.MANUAL_CONTROLLED:
            if not has_text(self.evidencia_importacion_ref):
                errors['evidencia_importacion_ref'] = 'La carga manual bancaria requiere evidencia_importacion_ref.'

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

    def save(self, *args, **kwargs):
        self._normalize_operational_fields()
        super().save(*args, **kwargs)


class CuadraturaBancaria(TimestampedModel):
    cuenta_recaudadora = models.ForeignKey(
        CuentaRecaudadora,
        on_delete=models.PROTECT,
        related_name='cuadraturas_bancarias',
    )
    periodo_economico = models.CharField(max_length=7)
    fecha_cuadratura = models.DateField()
    saldo_sistema_clp = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_banco_clp = models.DecimalField(max_digits=14, decimal_places=2)
    diferencia_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    estado = models.CharField(
        max_length=24,
        choices=EstadoCuadraturaBancaria.choices,
        default=EstadoCuadraturaBancaria.SQUARED,
    )
    evidencia_cuadratura_ref = models.CharField(max_length=255)
    responsable_ref = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)

    class Meta:
        ordering = ['-periodo_economico', '-fecha_cuadratura', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['cuenta_recaudadora', 'periodo_economico'],
                name='uniq_cuadratura_bancaria_por_cuenta_periodo',
            ),
        ]

    def __str__(self):
        return f'Cuadratura {self.cuenta_recaudadora_id} {self.periodo_economico}'

    def _calculated_difference(self):
        return Decimal(str(self.saldo_banco_clp or '0.00')) - Decimal(str(self.saldo_sistema_clp or '0.00'))

    def clean(self):
        super().clean()
        errors = {}
        self.diferencia_clp = self._calculated_difference()

        if not ECONOMIC_PERIOD_RE.fullmatch(str(self.periodo_economico or '').strip()):
            errors['periodo_economico'] = 'periodo_economico debe usar formato YYYY-MM.'
        elif _period_from_date(self.fecha_cuadratura) != str(self.periodo_economico).strip():
            errors['periodo_economico'] = 'periodo_economico debe coincidir con el mes de fecha_cuadratura.'

        if not is_non_sensitive_reference(self.evidencia_cuadratura_ref):
            errors['evidencia_cuadratura_ref'] = (
                'evidencia_cuadratura_ref debe ser una referencia no sensible, no una URL, token o credencial.'
            )
        if not is_non_sensitive_reference(self.responsable_ref):
            errors['responsable_ref'] = 'responsable_ref debe ser una referencia no sensible.'

        if self.diferencia_clp == Decimal('0.00'):
            if self.estado != EstadoCuadraturaBancaria.SQUARED:
                errors['estado'] = 'Una cuadratura sin diferencia debe quedar en estado cuadrada.'
        else:
            if self.estado == EstadoCuadraturaBancaria.SQUARED:
                errors['estado'] = 'Una cuadratura con diferencia no puede quedar marcada como cuadrada.'
            if not has_text(self.rationale):
                errors['rationale'] = 'Una diferencia banco/sistema requiere motivo o explicacion auditable.'
        _add_sensitive_text_error(
            errors,
            self,
            'rationale',
            'rationale no puede contener URLs, tokens, correos ni credenciales bancarias.',
        )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.diferencia_clp = self._calculated_difference()
        super().save(*args, **kwargs)


def _movement_account(movement):
    try:
        return movement.conexion_bancaria.cuenta_recaudadora
    except (ConexionBancaria.DoesNotExist, AttributeError):
        return None


def _movement_period(movement):
    movement_date = _coerce_date(getattr(movement, 'fecha_movimiento', None))
    if movement_date is None:
        return ''
    return f'{movement_date.year:04d}-{movement_date.month:02d}'


class TransferenciaIntercuenta(TimestampedModel):
    movimiento_origen = models.ForeignKey(
        MovimientoBancarioImportado,
        on_delete=models.PROTECT,
        related_name='transferencias_intercuenta_origen',
    )
    movimiento_destino = models.ForeignKey(
        MovimientoBancarioImportado,
        on_delete=models.PROTECT,
        related_name='transferencias_intercuenta_destino',
    )
    periodo_economico = models.CharField(max_length=7)
    entidad_origen_tipo = models.CharField(max_length=16, blank=True)
    entidad_origen_id = models.PositiveIntegerField(null=True, blank=True)
    entidad_destino_tipo = models.CharField(max_length=16, blank=True)
    entidad_destino_id = models.PositiveIntegerField(null=True, blank=True)
    criterio_conciliacion = models.CharField(max_length=255)
    evidencia_transferencia_ref = models.CharField(max_length=255)
    responsable_ref = models.CharField(max_length=255)
    rationale = models.TextField()

    class Meta:
        ordering = ['-periodo_economico', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['movimiento_origen'],
                name='uniq_transferencia_intercuenta_origen',
            ),
            models.UniqueConstraint(
                fields=['movimiento_destino'],
                name='uniq_transferencia_intercuenta_destino',
            ),
            models.UniqueConstraint(
                fields=['movimiento_origen', 'movimiento_destino'],
                name='uniq_transferencia_intercuenta_par_movimientos',
            ),
        ]

    def __str__(self):
        return f'Transferencia intercuenta {self.movimiento_origen_id}->{self.movimiento_destino_id}'

    def _populate_entity_snapshots(self):
        origin_account = _movement_account(getattr(self, 'movimiento_origen', None))
        destination_account = _movement_account(getattr(self, 'movimiento_destino', None))
        if origin_account is not None:
            self.entidad_origen_tipo = origin_account.owner_tipo or ''
            self.entidad_origen_id = origin_account.owner_id
        if destination_account is not None:
            self.entidad_destino_tipo = destination_account.owner_tipo or ''
            self.entidad_destino_id = destination_account.owner_id

    def clean(self):
        super().clean()
        self._populate_entity_snapshots()
        errors = {}

        if not ECONOMIC_PERIOD_RE.fullmatch(str(self.periodo_economico or '').strip()):
            errors['periodo_economico'] = 'periodo_economico debe usar formato YYYY-MM.'
        if not has_text(self.criterio_conciliacion):
            errors['criterio_conciliacion'] = 'La transferencia interna requiere criterio de conciliacion.'
        _add_sensitive_text_error(
            errors,
            self,
            'criterio_conciliacion',
            'criterio_conciliacion no puede contener URLs, tokens, correos ni credenciales bancarias.',
        )
        if not is_non_sensitive_reference(self.evidencia_transferencia_ref):
            errors['evidencia_transferencia_ref'] = (
                'evidencia_transferencia_ref debe ser una referencia no sensible.'
            )
        if not is_non_sensitive_reference(self.responsable_ref):
            errors['responsable_ref'] = 'responsable_ref debe ser una referencia no sensible.'
        if not has_text(self.rationale):
            errors['rationale'] = 'La transferencia interna requiere motivo auditable.'
        _add_sensitive_text_error(
            errors,
            self,
            'rationale',
            'rationale no puede contener URLs, tokens, correos ni credenciales bancarias.',
        )

        try:
            origin = self.movimiento_origen
        except MovimientoBancarioImportado.DoesNotExist:
            origin = None
        try:
            destination = self.movimiento_destino
        except MovimientoBancarioImportado.DoesNotExist:
            destination = None

        if origin is None or destination is None:
            if origin is None:
                errors['movimiento_origen'] = 'La transferencia requiere movimiento origen.'
            if destination is None:
                errors['movimiento_destino'] = 'La transferencia requiere movimiento destino.'
            if errors:
                raise ValidationError(errors)

        if origin.pk and destination.pk and origin.pk == destination.pk:
            errors['movimiento_destino'] = 'La transferencia requiere movimientos distintos.'

        if origin.tipo_movimiento != TipoMovimientoBancario.DEBIT:
            errors['movimiento_origen'] = 'El movimiento origen de transferencia debe ser cargo.'
        if destination.tipo_movimiento != TipoMovimientoBancario.CREDIT:
            errors['movimiento_destino'] = 'El movimiento destino de transferencia debe ser abono.'

        origin_account = _movement_account(origin)
        destination_account = _movement_account(destination)
        if origin_account is not None and destination_account is not None:
            if origin_account.pk == destination_account.pk:
                errors['movimiento_destino'] = 'La transferencia interna requiere cuentas recaudadoras distintas.'

        if Decimal(str(origin.monto)) != Decimal(str(destination.monto)):
            errors['movimiento_destino'] = 'El cargo y el abono de transferencia deben tener el mismo monto.'

        if _movement_period(origin) != self.periodo_economico:
            errors['periodo_economico'] = 'El periodo economico debe coincidir con el mes del movimiento origen.'
        if _movement_period(destination) != self.periodo_economico:
            errors['movimiento_destino'] = 'El movimiento destino debe pertenecer al mismo periodo economico.'

        if origin.pago_mensual_id or origin.codigo_cobro_residual_id:
            errors['movimiento_origen'] = 'El movimiento origen de transferencia no puede tener target de cobro.'
        if destination.pago_mensual_id or destination.codigo_cobro_residual_id:
            errors['movimiento_destino'] = 'El movimiento destino de transferencia no puede tener target de cobro.'

        allowed_origin_states = {
            EstadoConciliacionMovimiento.MANUAL_REQUIRED,
            EstadoConciliacionMovimiento.EXACT_MATCH,
        }
        allowed_destination_states = {
            EstadoConciliacionMovimiento.PENDING,
            EstadoConciliacionMovimiento.UNKNOWN_INCOME,
            EstadoConciliacionMovimiento.EXACT_MATCH,
        }
        if origin.estado_conciliacion not in allowed_origin_states:
            errors['movimiento_origen'] = 'El cargo origen debe estar pendiente de clasificacion o ya conciliado.'
        if destination.estado_conciliacion not in allowed_destination_states:
            errors['movimiento_destino'] = 'El abono destino debe estar pendiente, desconocido o conciliado por transferencia.'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self._populate_entity_snapshots()
        super().save(*args, **kwargs)


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
    if conexion.ultimo_error_at and (
        conexion.ultimo_exito_at is None or conexion.ultimo_error_at > conexion.ultimo_exito_at
    ):
        return 'Banca.Movimientos requiere un ultimo exito posterior al ultimo error del proveedor.'
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

