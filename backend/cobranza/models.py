from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from contratos.models import Contrato, MonedaBaseContrato, PeriodoContractual
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from patrimonio.models import Empresa, Socio


codigo_efectivo_validator = RegexValidator(
    regex=r'^\d{3}$',
    message='El codigo de conciliacion efectivo debe tener exactamente 3 digitos.',
)


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class EstadoPago(models.TextChoices):
    PENDING = 'pendiente', 'Pendiente'
    PAID = 'pagado', 'Pagado'
    OVERDUE = 'atrasado', 'Atrasado'
    IN_REPAYMENT = 'en_repactacion', 'En repactacion'
    PAID_VIA_REPAYMENT = 'pagado_via_repactacion', 'Pagado via repactacion'
    PAID_BY_TERMINATION = 'pagado_por_acuerdo_termino', 'Pagado por acuerdo de termino'
    FORGIVEN = 'condonado', 'Condonado'


class EstadoGarantia(models.TextChoices):
    PENDING = 'pendiente_recepcion', 'Pendiente recepcion'
    HELD = 'retenida', 'Retenida'
    PARTIALLY_RETURNED = 'parcialmente_devuelta', 'Parcialmente devuelta'
    RETURNED = 'devuelta', 'Devuelta'
    APPLIED = 'aplicada', 'Aplicada'


class EstadoRepactacion(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    ACTIVE = 'activa', 'Activa'
    COMPLETED = 'cumplida', 'Cumplida'
    DEFAULTED = 'incumplida', 'Incumplida'
    CANCELED = 'cancelada', 'Cancelada'


class EstadoCobroResidual(models.TextChoices):
    ACTIVE = 'activa', 'Activa'
    PAID = 'pagada', 'Pagada'
    CANCELED = 'cancelada', 'Cancelada'


class EstadoGateCobroExterno(models.TextChoices):
    OPEN = 'abierto', 'Abierto'
    CONDITIONED = 'condicionado', 'Condicionado'
    CLOSED = 'cerrado', 'Cerrado'
    SUSPENDED = 'suspendido', 'Suspendido'


class CapacidadCobroExterno(models.TextChoices):
    WEBPAY_INTENT = 'WebPay.IntentoPago', 'WebPay intento de pago'


class EstadoIntentoPagoWebPay(models.TextChoices):
    BLOCKED = 'bloqueado_gate', 'Bloqueado por gate'
    PREPARED = 'preparado', 'Preparado'
    CONFIRMED_MANUAL = 'confirmado_manual_controlado', 'Confirmado manual controlado'
    CANCELED = 'cancelado', 'Cancelado'
    FAILED = 'fallido', 'Fallido'


class TipoMovimientoGarantia(models.TextChoices):
    DEPOSIT = 'deposito', 'Deposito'
    PARTIAL_RETURN = 'devolucion_parcial', 'Devolucion parcial'
    TOTAL_RETURN = 'devolucion_total', 'Devolucion total'
    PARTIAL_RETENTION = 'retencion_parcial', 'Retencion parcial'
    TOTAL_RETENTION = 'retencion_total', 'Retencion total'


class ValorUFDiario(TimestampedModel):
    fecha = models.DateField(unique=True)
    valor = models.DecimalField(max_digits=12, decimal_places=4, validators=[MinValueValidator(Decimal('0.0001'))])
    source_key = models.CharField(max_length=64, default='manual')

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.fecha} - {self.valor}'


class AjusteContrato(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='ajustes_contrato',
    )
    tipo_ajuste = models.CharField(max_length=64)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    moneda = models.CharField(max_length=8, choices=MonedaBaseContrato.choices)
    mes_inicio = models.DateField()
    mes_fin = models.DateField()
    justificacion = models.TextField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['contrato_id', 'mes_inicio']

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - {self.tipo_ajuste}'

    def clean(self):
        super().clean()
        if self.mes_inicio.day != 1:
            raise ValidationError({'mes_inicio': 'El mes inicial del ajuste debe ser el primer dia del mes.'})
        if self.mes_fin.day != 1:
            raise ValidationError({'mes_fin': 'El mes final del ajuste debe ser el primer dia del mes.'})
        if self.mes_fin < self.mes_inicio:
            raise ValidationError({'mes_fin': 'El mes final del ajuste no puede ser anterior al inicial.'})

        if not self.contrato_id:
            return

        errors = {}
        if self.mes_inicio < self.contrato.fecha_inicio:
            errors['mes_inicio'] = 'El ajuste no puede iniciar antes de la vigencia del contrato.'
        if self.mes_fin > self.contrato.fecha_fin_vigente:
            errors['mes_fin'] = 'El ajuste no puede terminar despues de la vigencia del contrato.'
        if errors:
            raise ValidationError(errors)


class PagoMensual(TimestampedModel):
    contrato = models.ForeignKey(
        Contrato,
        on_delete=models.CASCADE,
        related_name='pagos_mensuales',
    )
    periodo_contractual = models.ForeignKey(
        PeriodoContractual,
        on_delete=models.PROTECT,
        related_name='pagos_mensuales',
    )
    mes = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    anio = models.PositiveSmallIntegerField()
    monto_facturable_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_calculado_clp = models.DecimalField(max_digits=14, decimal_places=2)
    monto_pagado_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    fecha_vencimiento = models.DateField()
    fecha_deposito_banco = models.DateField(null=True, blank=True)
    fecha_pago_webpay = models.DateField(null=True, blank=True)
    fecha_deteccion_sistema = models.DateField(null=True, blank=True)
    estado_pago = models.CharField(max_length=32, choices=EstadoPago.choices, default=EstadoPago.PENDING)
    dias_mora = models.PositiveIntegerField(default=0)
    codigo_conciliacion_efectivo = models.CharField(max_length=3, validators=[codigo_efectivo_validator])

    class Meta:
        ordering = ['-anio', '-mes', 'contrato_id']
        constraints = [
            models.UniqueConstraint(
                fields=['contrato', 'anio', 'mes'],
                name='uniq_pago_mensual_por_contrato_periodo',
            ),
        ]

    def __str__(self):
        return f'{self.contrato.codigo_contrato} - {self.mes}/{self.anio}'

    def clean(self):
        super().clean()
        if self.codigo_conciliacion_efectivo == '000':
            raise ValidationError(
                {
                    'codigo_conciliacion_efectivo': (
                        'El codigo efectivo debe estar en el rango 001-999.'
                    )
                }
            )
        if self.periodo_contractual.contrato_id != self.contrato_id:
            raise ValidationError({'periodo_contractual': 'El periodo contractual debe pertenecer al mismo contrato.'})


class GateCobroExterno(TimestampedModel):
    capacidad_key = models.CharField(
        max_length=32,
        choices=CapacidadCobroExterno.choices,
        default=CapacidadCobroExterno.WEBPAY_INTENT,
    )
    provider_key = models.CharField(max_length=64, default='transbank_webpay')
    estado_gate = models.CharField(
        max_length=16,
        choices=EstadoGateCobroExterno.choices,
        default=EstadoGateCobroExterno.CONDITIONED,
    )
    restricciones_operativas = models.JSONField(default=dict, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['capacidad_key', 'provider_key']
        constraints = [
            models.UniqueConstraint(
                fields=['capacidad_key', 'provider_key'],
                name='uniq_gate_cobro_externo_capacidad_provider',
            ),
        ]

    def __str__(self):
        return f'{self.capacidad_key} - {self.provider_key}'

    def clean(self):
        super().clean()
        if self.evidencia_ref.strip() and not is_non_sensitive_reference(self.evidencia_ref):
            raise ValidationError({'evidencia_ref': 'evidencia_ref debe ser una referencia no sensible.'})
        if contains_sensitive_reference(self.restricciones_operativas):
            raise ValidationError(
                {
                    'restricciones_operativas': (
                        'restricciones_operativas no debe contener URLs, tokens, credenciales ni correos.'
                    )
                }
            )
        if self.estado_gate == EstadoGateCobroExterno.OPEN and not is_non_sensitive_reference(self.evidencia_ref):
            raise ValidationError({'evidencia_ref': 'Un gate de cobro externo abierto requiere evidencia_ref no sensible.'})


class IntentoPagoWebPay(TimestampedModel):
    pago_mensual = models.ForeignKey(
        PagoMensual,
        on_delete=models.PROTECT,
        related_name='intentos_webpay',
    )
    gate_cobro = models.ForeignKey(
        GateCobroExterno,
        on_delete=models.PROTECT,
        related_name='intentos_webpay',
    )
    provider_key = models.CharField(max_length=64, default='transbank_webpay')
    monto_clp_snapshot = models.DecimalField(max_digits=14, decimal_places=2)
    buy_order = models.CharField(max_length=64, blank=True)
    session_id = models.CharField(max_length=64, blank=True)
    return_url_ref = models.CharField(max_length=255, blank=True)
    estado = models.CharField(
        max_length=32,
        choices=EstadoIntentoPagoWebPay.choices,
        default=EstadoIntentoPagoWebPay.BLOCKED,
    )
    motivo_bloqueo = models.TextField(blank=True)
    external_ref = models.CharField(max_length=255, blank=True)
    fecha_pago_webpay = models.DateField(null=True, blank=True)
    confirmado_at = models.DateTimeField(null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='intentos_webpay',
    )
    provider_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['pago_mensual'],
                condition=models.Q(estado=EstadoIntentoPagoWebPay.PREPARED),
                name='uniq_intento_webpay_preparado_por_pago',
            ),
            models.UniqueConstraint(
                fields=['buy_order'],
                condition=~models.Q(buy_order=''),
                name='uniq_intento_webpay_buy_order_no_vacio',
            ),
        ]

    def __str__(self):
        return f'WebPay {self.pago_mensual_id} - {self.estado}'

    def clean(self):
        super().clean()
        if self.gate_cobro.provider_key != self.provider_key:
            raise ValidationError({'gate_cobro': 'El gate de cobro debe pertenecer al mismo provider_key.'})
        if self.gate_cobro.capacidad_key != CapacidadCobroExterno.WEBPAY_INTENT:
            raise ValidationError({'gate_cobro': 'El gate debe corresponder a WebPay.IntentoPago.'})
        if self.estado in {EstadoIntentoPagoWebPay.PREPARED, EstadoIntentoPagoWebPay.CONFIRMED_MANUAL}:
            if self.gate_cobro.estado_gate != EstadoGateCobroExterno.OPEN:
                raise ValidationError({'estado': 'WebPay solo puede prepararse o confirmarse con gate abierto.'})
            if not self.gate_cobro.evidencia_ref.strip():
                raise ValidationError({'gate_cobro': 'WebPay requiere evidencia_ref del gate antes de operar.'})
            if not self.return_url_ref.strip():
                raise ValidationError({'return_url_ref': 'WebPay requiere una referencia de retorno no sensible.'})
            if not is_non_sensitive_reference(self.return_url_ref):
                raise ValidationError(
                    {
                        'return_url_ref': (
                            'return_url_ref debe ser una referencia no sensible, no una URL, token o credencial.'
                        )
                    }
                )
            if self.estado == EstadoIntentoPagoWebPay.PREPARED and self.pago_mensual.estado_pago not in {
                EstadoPago.PENDING,
                EstadoPago.OVERDUE,
            }:
                raise ValidationError({'pago_mensual': 'Solo se puede preparar WebPay para pagos pendientes o atrasados.'})
        if self.estado == EstadoIntentoPagoWebPay.CONFIRMED_MANUAL:
            if not self.external_ref.strip():
                raise ValidationError({'external_ref': 'La confirmacion WebPay requiere transaction id o token externo.'})
            if not is_non_sensitive_reference(self.external_ref):
                raise ValidationError(
                    {'external_ref': 'external_ref debe ser una referencia no sensible, no una URL, token o credencial.'}
                )
            if not self.fecha_pago_webpay:
                raise ValidationError({'fecha_pago_webpay': 'La confirmacion WebPay requiere fecha de pago WebPay.'})


class DistribucionCobroMensual(TimestampedModel):
    pago_mensual = models.ForeignKey(
        PagoMensual,
        on_delete=models.CASCADE,
        related_name='distribuciones_cobro',
    )
    beneficiario_socio_owner = models.ForeignKey(
        Socio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='distribuciones_cobro_mensual',
    )
    beneficiario_empresa_owner = models.ForeignKey(
        Empresa,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='distribuciones_cobro_mensual',
    )
    porcentaje_snapshot = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('100.00'))],
    )
    monto_devengado_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_conciliado_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_facturable_clp = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    requiere_dte = models.BooleanField(default=False)
    origen_atribucion = models.CharField(max_length=64, default='snapshot_pago')

    class Meta:
        ordering = ['pago_mensual_id', 'id']
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(beneficiario_socio_owner__isnull=False, beneficiario_empresa_owner__isnull=True)
                    | models.Q(beneficiario_socio_owner__isnull=True, beneficiario_empresa_owner__isnull=False)
                ),
                name='distribucion_cobro_exactly_one_beneficiary',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(monto_devengado_clp__gte=Decimal('0.00'))
                    & models.Q(monto_conciliado_clp__gte=Decimal('0.00'))
                    & models.Q(monto_facturable_clp__gte=Decimal('0.00'))
                ),
                name='distribucion_cobro_non_negative_amounts',
            ),
            models.CheckConstraint(
                check=models.Q(monto_facturable_clp__lte=models.F('monto_devengado_clp')),
                name='distribucion_cobro_facturable_lte_devengado',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(requiere_dte=False, monto_facturable_clp=Decimal('0.00'))
                    | models.Q(requiere_dte=True, monto_facturable_clp__gt=Decimal('0.00'))
                ),
                name='distribucion_cobro_facturable_matches_dte_flag',
            ),
            models.CheckConstraint(
                check=(
                    models.Q(requiere_dte=False)
                    | models.Q(beneficiario_empresa_owner__isnull=False, beneficiario_socio_owner__isnull=True)
                ),
                name='distribucion_cobro_dte_requires_company_beneficiary',
            ),
            models.UniqueConstraint(
                fields=['pago_mensual', 'beneficiario_empresa_owner'],
                condition=models.Q(beneficiario_empresa_owner__isnull=False),
                name='uniq_distribucion_pago_empresa_beneficiaria',
            ),
            models.UniqueConstraint(
                fields=['pago_mensual', 'beneficiario_socio_owner'],
                condition=models.Q(beneficiario_socio_owner__isnull=False),
                name='uniq_distribucion_pago_socio_beneficiario',
            ),
        ]

    def __str__(self):
        return f'{self.pago_mensual_id} - {self.beneficiario_display}'

    @property
    def beneficiario_tipo(self):
        if self.beneficiario_socio_owner_id:
            return 'socio'
        return 'empresa'

    @property
    def beneficiario_id(self):
        if self.beneficiario_socio_owner_id:
            return self.beneficiario_socio_owner_id
        return self.beneficiario_empresa_owner_id

    @property
    def beneficiario_display(self):
        if self.beneficiario_socio_owner_id:
            return self.beneficiario_socio_owner.nombre
        return self.beneficiario_empresa_owner.razon_social

    def clean(self):
        super().clean()
        beneficiary_count = sum(
            bool(value) for value in (self.beneficiario_socio_owner_id, self.beneficiario_empresa_owner_id)
        )
        if beneficiary_count != 1:
            raise ValidationError('La distribucion debe pertenecer exactamente a un beneficiario.')
        if self.monto_devengado_clp < 0 or self.monto_conciliado_clp < 0 or self.monto_facturable_clp < 0:
            raise ValidationError('Los montos de distribucion no pueden ser negativos.')
        if self.monto_facturable_clp > self.monto_devengado_clp:
            raise ValidationError({'monto_facturable_clp': 'El monto facturable no puede exceder el monto devengado.'})
        pago_conciliado = Decimal(str(self.pago_mensual.monto_pagado_clp))
        if self.monto_conciliado_clp > pago_conciliado:
            raise ValidationError({'monto_conciliado_clp': 'El monto conciliado no puede exceder el pago conciliado.'})
        if self.requiere_dte and not self.beneficiario_empresa_owner_id:
            raise ValidationError({'requiere_dte': 'Solo un beneficiario empresa puede requerir DTE.'})


class GarantiaContractual(TimestampedModel):
    contrato = models.OneToOneField(
        Contrato,
        on_delete=models.CASCADE,
        related_name='garantia_contractual',
    )
    monto_pactado = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    monto_recibido = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_devuelto = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_aplicado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    estado_garantia = models.CharField(max_length=32, choices=EstadoGarantia.choices, default=EstadoGarantia.PENDING)
    fecha_recepcion = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['contrato_id']

    def __str__(self):
        return f'Garantia {self.contrato.codigo_contrato}'

    @property
    def saldo_vigente(self):
        return self.monto_recibido - self.monto_devuelto - self.monto_aplicado

    def clean(self):
        super().clean()
        if self.monto_recibido < 0 or self.monto_devuelto < 0 or self.monto_aplicado < 0:
            raise ValidationError('Los montos de garantia no pueden ser negativos.')

        if self.monto_recibido > self.monto_pactado:
            raise ValidationError({'monto_recibido': 'La garantia recibida no puede exceder el monto pactado.'})

        if self.monto_devuelto + self.monto_aplicado > self.monto_recibido:
            raise ValidationError('La garantia no puede devolver o aplicar mas de lo recibido.')

        saldo = self.saldo_vigente
        if self.monto_recibido == 0:
            if self.estado_garantia != EstadoGarantia.PENDING:
                raise ValidationError({'estado_garantia': 'Una garantia sin recepcion debe quedar pendiente.'})
            if self.fecha_recepcion or self.fecha_cierre:
                raise ValidationError({'fecha_recepcion': 'Una garantia sin recepcion no debe tener fechas operativas.'})
            return

        if not self.fecha_recepcion:
            raise ValidationError({'fecha_recepcion': 'Una garantia recibida requiere fecha de recepcion.'})
        if self.fecha_cierre and self.fecha_cierre < self.fecha_recepcion:
            raise ValidationError({'fecha_cierre': 'La fecha de cierre no puede ser anterior a la recepcion.'})

        if saldo > 0:
            expected_state = EstadoGarantia.PARTIALLY_RETURNED if self.monto_devuelto > 0 else EstadoGarantia.HELD
            if self.estado_garantia != expected_state:
                raise ValidationError(
                    {'estado_garantia': 'El estado de garantia no coincide con sus montos abiertos.'}
                )
            if self.fecha_cierre:
                raise ValidationError({'fecha_cierre': 'Una garantia con saldo vigente no debe tener fecha de cierre.'})
            return

        expected_closed_state = EstadoGarantia.APPLIED if self.monto_aplicado > 0 else EstadoGarantia.RETURNED
        if self.estado_garantia != expected_closed_state:
            raise ValidationError({'estado_garantia': 'El estado de garantia no coincide con sus montos cerrados.'})
        if not self.fecha_cierre:
            raise ValidationError({'fecha_cierre': 'Una garantia cerrada requiere fecha de cierre.'})


class HistorialGarantia(TimestampedModel):
    garantia_contractual = models.ForeignKey(
        GarantiaContractual,
        on_delete=models.CASCADE,
        related_name='historial_movimientos',
    )
    tipo_movimiento = models.CharField(max_length=32, choices=TipoMovimientoGarantia.choices)
    monto_clp = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    fecha = models.DateField()
    justificacion = models.TextField(blank=True)
    movimiento_origen = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='movimientos_derivados',
    )

    class Meta:
        ordering = ['garantia_contractual_id', 'fecha', 'id']

    def __str__(self):
        return f'{self.garantia_contractual.contrato.codigo_contrato} - {self.tipo_movimiento}'

    def clean(self):
        super().clean()
        if (
            self.movimiento_origen_id
            and self.garantia_contractual_id
            and self.movimiento_origen.garantia_contractual_id != self.garantia_contractual_id
        ):
            raise ValidationError(
                {'movimiento_origen': 'El movimiento origen debe pertenecer a la misma garantia contractual.'}
            )


class RepactacionDeuda(TimestampedModel):
    arrendatario = models.ForeignKey(
        'contratos.Arrendatario',
        on_delete=models.PROTECT,
        related_name='repactaciones_deuda',
    )
    contrato_origen = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        related_name='repactaciones_deuda',
    )
    deuda_total_original = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    cantidad_cuotas = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    monto_cuota = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    saldo_pendiente = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    estado = models.CharField(max_length=16, choices=EstadoRepactacion.choices, default=EstadoRepactacion.DRAFT)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Repactacion {self.arrendatario_id} - {self.contrato_origen.codigo_contrato}'

    def clean(self):
        super().clean()
        if self.contrato_origen.arrendatario_id != self.arrendatario_id:
            raise ValidationError({'arrendatario': 'La repactacion debe pertenecer al mismo arrendatario del contrato origen.'})
        if self.saldo_pendiente > self.deuda_total_original:
            raise ValidationError({'saldo_pendiente': 'El saldo pendiente no puede exceder la deuda total original.'})


class CodigoCobroResidual(TimestampedModel):
    referencia_visible = models.CharField(max_length=10, unique=True)
    arrendatario = models.ForeignKey(
        'contratos.Arrendatario',
        on_delete=models.PROTECT,
        related_name='codigos_cobro_residual',
    )
    contrato_origen = models.ForeignKey(
        Contrato,
        on_delete=models.PROTECT,
        related_name='codigos_cobro_residual',
    )
    saldo_actual = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    estado = models.CharField(max_length=16, choices=EstadoCobroResidual.choices, default=EstadoCobroResidual.ACTIVE)
    fecha_activacion = models.DateField()

    class Meta:
        ordering = ['-fecha_activacion']

    def __str__(self):
        return self.referencia_visible

    def clean(self):
        super().clean()
        if self.contrato_origen.arrendatario_id != self.arrendatario_id:
            raise ValidationError({'arrendatario': 'El cobro residual debe pertenecer al mismo arrendatario del contrato origen.'})
        if self.estado == EstadoCobroResidual.ACTIVE and self.saldo_actual <= 0:
            raise ValidationError({'saldo_actual': 'El cobro residual activo requiere un saldo mayor que cero.'})


class EstadoCuentaArrendatario(TimestampedModel):
    arrendatario = models.OneToOneField(
        'contratos.Arrendatario',
        on_delete=models.CASCADE,
        related_name='estado_cuenta',
    )
    resumen_operativo = models.JSONField(default=dict, blank=True)
    score_pago = models.PositiveSmallIntegerField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ['arrendatario_id']

    def __str__(self):
        return f'EstadoCuenta {self.arrendatario_id}'
