from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models

from cobranza.models import DistribucionCobroMensual, PagoMensual
from contabilidad.models import CierreMensualContable, EstadoPreparacionTributaria, EstadoRegistro
from contratos.models import Contrato
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
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


def has_text(value):
    return bool(str(value or '').strip())


SII_AUTOMATED_REGIME_CODE = 'EmpresaContabilidadCompletaV1'
TAX_REFERENCE_REQUIRED_STATES = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}


def _add_error(errors, field_name, message):
    existing = errors.get(field_name)
    if existing:
        errors[field_name] = (
            [*existing, message]
            if isinstance(existing, list)
            else [existing, message]
        )
    else:
        errors[field_name] = message


def _active_fiscal_config_for(empresa):
    try:
        fiscal_config = empresa.configuracion_fiscal
    except ObjectDoesNotExist:
        return None
    if fiscal_config.estado != EstadoRegistro.ACTIVE:
        return None
    return fiscal_config


def _add_active_fiscal_config_error(errors, instance, artifact_label):
    if _active_fiscal_config_for(instance.empresa) is None:
        _add_error(
            errors,
            'empresa',
            f'{artifact_label} requiere ConfiguracionFiscalEmpresa activa para la misma empresa.',
        )


def _add_non_sensitive_reference_error(errors, instance, field_name):
    value = getattr(instance, field_name, '')
    if has_text(value) and not is_non_sensitive_reference(value):
        errors[field_name] = f'{field_name} debe ser una referencia no sensible, no una URL, token o credencial.'


def _add_required_tax_reference_error(errors, instance, field_name, state_field_name):
    state = getattr(instance, state_field_name, '')
    if state in TAX_REFERENCE_REQUIRED_STATES and not has_text(getattr(instance, field_name, '')):
        errors[field_name] = (
            f'{field_name} es obligatorio para estados tributarios aprobados, '
            'presentados, observados o rectificados.'
        )


def _add_non_sensitive_payload_error(errors, field_name, value):
    if value and contains_sensitive_reference(value, include_sensitive_keys=True):
        _add_error(
            errors,
            field_name,
            f'{field_name} no debe contener URLs, tokens, credenciales, correos ni claves sensibles.',
        )


def _summary_fiscal_year(summary):
    if not isinstance(summary, dict) or not has_text(summary.get('fiscal_year')):
        return None
    try:
        return int(summary.get('fiscal_year'))
    except (TypeError, ValueError):
        return None


def _add_annual_summary_year_error(errors, field_name, summary, anio_tributario):
    if not isinstance(summary, dict) or not has_text(summary.get('fiscal_year')):
        return
    fiscal_year = _summary_fiscal_year(summary)
    expected_fiscal_year = anio_tributario - 1
    if fiscal_year != expected_fiscal_year:
        _add_error(
            errors,
            field_name,
            f'{field_name} debe corresponder al año comercial {expected_fiscal_year} '
            f'para el año tributario {anio_tributario}.',
        )


def _add_capability_kind_error(errors, instance, expected_capability, artifact_label):
    capability = getattr(instance, 'capacidad_tributaria', None)
    if capability and capability.capacidad_key != expected_capability:
        message = (
            f'{artifact_label} requiere capacidad SII {expected_capability}; '
            f'recibio {capability.capacidad_key}.'
        )
        _add_error(errors, 'capacidad_tributaria', message)


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
    evidencia_ref = models.CharField(max_length=255, blank=True, default='')
    prueba_flujo_ref = models.CharField(max_length=255, blank=True, default='')
    autorizacion_ambiente_ref = models.CharField(max_length=255, blank=True, default='')
    regla_fiscal_ref = models.CharField(max_length=255, blank=True, default='')
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

    def readiness_errors(self):
        if self.estado_gate != EstadoGateSII.OPEN:
            return {}

        errors = {}
        if not has_text(self.certificado_ref):
            errors['certificado_ref'] = 'SII abierto requiere certificado_ref trazable.'
        if not has_text(self.evidencia_ref):
            errors['evidencia_ref'] = 'SII abierto requiere evidencia_ref del gate.'
        if not has_text(self.prueba_flujo_ref):
            errors['prueba_flujo_ref'] = 'SII abierto requiere prueba_flujo_ref trazable.'
        if not has_text(self.autorizacion_ambiente_ref):
            errors['autorizacion_ambiente_ref'] = 'SII abierto requiere autorizacion_ambiente_ref.'

        fiscal_rule_capabilities = {
            CapacidadSII.DTE_EMISION,
            CapacidadSII.F29_PREPARACION,
            CapacidadSII.F29_PRESENTACION,
            CapacidadSII.DDJJ_PREPARACION,
            CapacidadSII.F22_PREPARACION,
        }
        if self.capacidad_key in fiscal_rule_capabilities and not has_text(self.regla_fiscal_ref):
            errors['regla_fiscal_ref'] = 'SII abierto requiere regla_fiscal_ref validada.'

        fiscal_config = _active_fiscal_config_for(self.empresa)
        if fiscal_config is None:
            errors['empresa'] = 'SII abierto requiere ConfiguracionFiscalEmpresa activa para la misma empresa.'
        elif fiscal_config.regimen_tributario.codigo_regimen != SII_AUTOMATED_REGIME_CODE:
            errors['empresa'] = 'La empresa no pertenece al regimen fiscal automatizable del v1.'

        if self.ambiente == AmbienteSII.PRODUCTION:
            metadata = self.ultimo_resultado if isinstance(self.ultimo_resultado, dict) else {}
            if not has_text(metadata.get('autorizacion_produccion_ref')):
                errors['ultimo_resultado'] = 'SII en produccion requiere autorizacion_produccion_ref en ultimo_resultado.'

        return errors

    def clean(self):
        super().clean()
        errors = self.readiness_errors()
        for field_name in (
            'certificado_ref',
            'evidencia_ref',
            'prueba_flujo_ref',
            'autorizacion_ambiente_ref',
            'regla_fiscal_ref',
        ):
            _add_non_sensitive_reference_error(errors, self, field_name)
        _add_non_sensitive_payload_error(errors, 'ultimo_resultado', self.ultimo_resultado)
        if errors:
            raise ValidationError(errors)


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
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'sii_track_id')
        _add_active_fiscal_config_error(errors, self, 'DTE')
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            errors['capacidad_tributaria'] = 'La capacidad SII debe pertenecer a la misma empresa del DTE.'
        _add_capability_kind_error(errors, self, CapacidadSII.DTE_EMISION, 'DTE')
        if self.pago_mensual.contrato_id != self.contrato_id:
            errors['pago_mensual'] = 'El pago mensual debe pertenecer al mismo contrato del DTE.'
        if self.distribucion_cobro_mensual.pago_mensual_id != self.pago_mensual_id:
            errors['distribucion_cobro_mensual'] = 'La distribucion debe pertenecer al mismo pago mensual del DTE.'
        if not self.distribucion_cobro_mensual.requiere_dte:
            errors['distribucion_cobro_mensual'] = 'El DTE solo puede emitirse desde una distribucion facturable.'
        if self.distribucion_cobro_mensual.beneficiario_empresa_owner_id != self.empresa_id:
            errors['empresa'] = 'La empresa del DTE debe coincidir con la empresa beneficiaria de la distribucion.'
        if self.contrato.arrendatario_id != self.arrendatario_id:
            errors['arrendatario'] = 'El DTE debe pertenecer al mismo arrendatario del contrato.'
        if errors:
            raise ValidationError(errors)


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
        errors = {}
        _add_required_tax_reference_error(errors, self, 'borrador_ref', 'estado_preparacion')
        _add_non_sensitive_reference_error(errors, self, 'borrador_ref')
        _add_active_fiscal_config_error(errors, self, 'F29')
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            errors['capacidad_tributaria'] = 'La capacidad SII debe pertenecer a la misma empresa del borrador F29.'
        _add_capability_kind_error(errors, self, CapacidadSII.F29_PREPARACION, 'F29')
        _add_non_sensitive_payload_error(errors, 'resumen_formulario', self.resumen_formulario)
        if self.cierre_mensual.empresa_id != self.empresa_id or self.cierre_mensual.anio != self.anio or self.cierre_mensual.mes != self.mes:
            errors['cierre_mensual'] = 'El cierre mensual debe coincidir con la empresa y periodo del F29.'
        if errors:
            raise ValidationError(errors)


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

    def clean(self):
        super().clean()
        errors = {}
        _add_required_tax_reference_error(errors, self, 'paquete_ddjj_ref', 'estado')
        _add_required_tax_reference_error(errors, self, 'borrador_f22_ref', 'estado')
        _add_non_sensitive_reference_error(errors, self, 'paquete_ddjj_ref')
        _add_non_sensitive_reference_error(errors, self, 'borrador_f22_ref')
        _add_active_fiscal_config_error(errors, self, 'ProcesoRentaAnual')
        _add_non_sensitive_payload_error(errors, 'resumen_anual', self.resumen_anual)
        _add_annual_summary_year_error(errors, 'resumen_anual', self.resumen_anual, self.anio_tributario)
        if errors:
            raise ValidationError(errors)


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
        errors = {}
        _add_required_tax_reference_error(errors, self, 'paquete_ref', 'estado_preparacion')
        _add_non_sensitive_reference_error(errors, self, 'paquete_ref')
        _add_active_fiscal_config_error(errors, self, 'DDJJ')
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            errors['capacidad_tributaria'] = 'La capacidad DDJJ debe pertenecer a la misma empresa.'
        _add_capability_kind_error(errors, self, CapacidadSII.DDJJ_PREPARACION, 'DDJJ')
        if self.proceso_renta_anual.empresa_id != self.empresa_id or self.proceso_renta_anual.anio_tributario != self.anio_tributario:
            errors['proceso_renta_anual'] = 'El proceso anual debe coincidir con la empresa y año tributario de DDJJ.'
        _add_non_sensitive_payload_error(errors, 'resumen_paquete', self.resumen_paquete)
        summary = self.resumen_paquete.get('resumen_anual') if isinstance(self.resumen_paquete, dict) else None
        _add_annual_summary_year_error(errors, 'resumen_paquete', summary, self.anio_tributario)
        if errors:
            raise ValidationError(errors)


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
        errors = {}
        _add_required_tax_reference_error(errors, self, 'borrador_ref', 'estado_preparacion')
        _add_non_sensitive_reference_error(errors, self, 'borrador_ref')
        _add_active_fiscal_config_error(errors, self, 'F22')
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            errors['capacidad_tributaria'] = 'La capacidad F22 debe pertenecer a la misma empresa.'
        _add_capability_kind_error(errors, self, CapacidadSII.F22_PREPARACION, 'F22')
        if self.proceso_renta_anual.empresa_id != self.empresa_id or self.proceso_renta_anual.anio_tributario != self.anio_tributario:
            errors['proceso_renta_anual'] = 'El proceso anual debe coincidir con la empresa y año tributario del F22.'
        _add_non_sensitive_payload_error(errors, 'resumen_f22', self.resumen_f22)
        summary = self.resumen_f22.get('resumen_anual') if isinstance(self.resumen_f22, dict) else None
        _add_annual_summary_year_error(errors, 'resumen_f22', summary, self.anio_tributario)
        if errors:
            raise ValidationError(errors)
