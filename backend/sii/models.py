import hashlib
import json
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q

from cobranza.models import DistribucionCobroMensual, PagoMensual
from contabilidad.models import (
    CierreMensualContable,
    EstadoCierreMensual,
    EstadoLiquidacionMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    LiquidacionMensual,
    RegimenTributarioEmpresa,
)
from contratos.models import Contrato
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from patrimonio.models import Empresa


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OperationalSIITextNormalizationMixin:
    operational_text_fields = ()

    def _normalize_operational_fields(self):
        for field_name in self.operational_text_fields:
            setattr(self, field_name, str(getattr(self, field_name, '') or '').strip())

    def full_clean(self, *args, **kwargs):
        self._normalize_operational_fields()
        super().full_clean(*args, **kwargs)

    def clean(self):
        self._normalize_operational_fields()
        super().clean()

    def save(self, *args, **kwargs):
        self._normalize_operational_fields()
        super().save(*args, **kwargs)


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


def _add_required_review_responsible_error(errors, instance, state_field_name):
    state = getattr(instance, state_field_name, '')
    field_name = 'responsable_revision_ref'
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


def _add_non_sensitive_text_error(errors, field_name, value):
    if has_text(value) and contains_sensitive_reference(value):
        _add_error(
            errors,
            field_name,
            f'{field_name} no debe contener URLs, tokens, credenciales ni correos.',
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


class CapacidadTributariaSII(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'certificado_ref',
        'evidencia_ref',
        'prueba_flujo_ref',
        'autorizacion_ambiente_ref',
        'regla_fiscal_ref',
    )

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


class DTEEmitido(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('sii_track_id', 'ultimo_estado_sii', 'observaciones')

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
        _add_non_sensitive_text_error(errors, 'observaciones', self.observaciones)
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


class F29PreparacionMensual(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('borrador_ref', 'responsable_revision_ref', 'observaciones')

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
    responsable_revision_ref = models.CharField(max_length=255, blank=True, default='')
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
        _add_required_review_responsible_error(errors, self, 'estado_preparacion')
        _add_non_sensitive_reference_error(errors, self, 'borrador_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsable_revision_ref')
        _add_non_sensitive_text_error(errors, 'observaciones', self.observaciones)
        _add_active_fiscal_config_error(errors, self, 'F29')
        if self.capacidad_tributaria.empresa_id != self.empresa_id:
            errors['capacidad_tributaria'] = 'La capacidad SII debe pertenecer a la misma empresa del borrador F29.'
        _add_capability_kind_error(errors, self, CapacidadSII.F29_PREPARACION, 'F29')
        _add_non_sensitive_payload_error(errors, 'resumen_formulario', self.resumen_formulario)
        if self.cierre_mensual.empresa_id != self.empresa_id or self.cierre_mensual.anio != self.anio or self.cierre_mensual.mes != self.mes:
            errors['cierre_mensual'] = 'El cierre mensual debe coincidir con la empresa y periodo del F29.'
        if errors:
            raise ValidationError(errors)


class EstadoReglaTributariaAnual(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    APPROVED = 'aprobada', 'Aprobada'
    CONDITIONED = 'condicionada', 'Condicionada'
    RETIRED = 'retirada', 'Retirada'


class DestinoMapeoTributarioAnual(models.TextChoices):
    RLI = 'RLI', 'RLI'
    CPT = 'CPT', 'CPT'
    RAI = 'RAI', 'RAI'
    SAC = 'SAC', 'SAC'
    DDJJ = 'DDJJ', 'DDJJ'
    F22 = 'F22', 'F22'
    DOSSIER = 'DOSSIER', 'Dossier'


class TipoAnnualTaxOfficialSource(models.TextChoices):
    SII_F22_CERTIFICATION = 'sii_f22_certification', 'SII certificacion F22'
    SII_F22_INSTRUCTIONS = 'sii_f22_instructions', 'SII instrucciones F22'
    SII_DDJJ_MEDIA = 'sii_ddjj_media', 'SII medios DDJJ'
    SII_DDJJ_FORMS = 'sii_ddjj_forms', 'SII formularios DDJJ'
    SII_DDJJ_SOFTWARE_HOUSES = 'sii_ddjj_software_houses', 'SII casas software DDJJ'
    SII_DJ1847_INSTRUCTIONS = 'sii_dj1847_instructions', 'SII instrucciones DJ1847'
    SII_F29_CERTIFICATION = 'sii_f29_certification', 'SII certificacion F29'
    SII_DTE_TECHNICAL = 'sii_dte_technical', 'SII tecnico DTE'
    EXPERT_REVIEW = 'expert_review', 'Revision experta'


class EstadoAnnualTaxOfficialSource(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    REVIEWED = 'revisada', 'Revisada'
    APPROVED = 'aprobada', 'Aprobada'
    RETIRED = 'retirada', 'Retirada'


class EstadoAnnualTaxSourceBundle(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    FROZEN = 'congelado', 'Congelado'
    RETIRED = 'retirado', 'Retirado'


class SourceKindRentaAnual(models.TextChoices):
    LOCAL = 'local', 'Local'
    FIXTURE = 'fixture', 'Fixture'
    DEMO = 'demo', 'Demo'
    CONTROLLED_SNAPSHOT = 'snapshot_controlado', 'Snapshot controlado'
    AUTHORIZED_REAL = 'real_autorizado', 'Real autorizado'


class EstadoMonthlyTaxFact(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    NORMALIZED = 'normalizado', 'Normalizado'
    RETIRED = 'retirado', 'Retirado'


class TipoAnnualTaxWorkbook(models.TextChoices):
    RLI = 'RLI', 'RLI'
    CPT = 'CPT', 'CPT'


class EstadoAnnualTaxWorkbook(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class TipoAnnualEnterpriseRegister(models.TextChoices):
    RAI = 'RAI', 'RAI'
    SAC = 'SAC', 'SAC'
    RETIROS = 'RETIROS', 'Retiros'
    DIVIDENDOS = 'DIVIDENDOS', 'Dividendos'


class EstadoAnnualEnterpriseRegister(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualRealEstateSection(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualTaxArtifactMatrix(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualTaxDossier(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualTaxExport(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class TipoAnnualTaxExport(models.TextChoices):
    PREVIEW_PACKAGE = 'preview_package', 'Preview package'


class TipoAnnualTaxArtifactTarget(models.TextChoices):
    DDJJ = 'DDJJ', 'DDJJ'
    F22 = 'F22', 'F22'


class SourceKindAnnualTaxArtifact(models.TextChoices):
    SOURCE_BUNDLE = 'source_bundle', 'Source bundle'
    TAX_MAPPING = 'tax_mapping', 'Tax code mapping'
    ANNUAL_SUMMARY = 'annual_summary', 'Annual summary'
    ANNUAL_WORKBOOK = 'annual_workbook', 'Annual workbook'
    ENTERPRISE_REGISTER = 'enterprise_register', 'Enterprise register'
    REAL_ESTATE = 'real_estate', 'Real estate'
    FISCAL_CONFIG = 'fiscal_config', 'Fiscal config'


class EstadoAnnualTaxArtifactReview(models.TextChoices):
    READY_FOR_REVIEW = 'listo_revision', 'Listo para revision'
    REQUIRES_REVIEW = 'requiere_revision', 'Requiere revision'
    BLOCKED = 'bloqueado', 'Bloqueado'


class SignoAnnualTaxLine(models.TextChoices):
    ADD = 'suma', 'Suma'
    SUBTRACT = 'resta', 'Resta'
    INFO = 'informativo', 'Informativo'


def _normalize_hash(value):
    return str(value or '').strip().lower()


def _is_sha256(value):
    normalized = _normalize_hash(value)
    return len(normalized) == 64 and all(character in '0123456789abcdef' for character in normalized)


SII_PUBLIC_SOURCE_DOMAINS = {
    'api.sii.cl',
    'www.sii.cl',
    'www4.sii.cl',
    'zeus.sii.cl',
}


def is_safe_public_sii_source_url(value):
    normalized = str(value or '').strip()
    if not normalized:
        return False
    parsed = urlparse(normalized)
    hostname = str(parsed.hostname or '').lower()
    return (
        parsed.scheme == 'https'
        and hostname in SII_PUBLIC_SOURCE_DOMAINS
        and not parsed.username
        and not parsed.password
        and not parsed.query
        and not parsed.fragment
        and not contains_sensitive_reference(parsed.path)
    )


def _canonical_json_payload(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)


def _payload_hash(value):
    return hashlib.sha256(_canonical_json_payload(value).encode('utf-8')).hexdigest()


def _line_integrity_payload(line):
    return {
        'workbook_id': line.workbook_id,
        'mapping_id': line.mapping_id,
        'codigo_interno': line.codigo_interno,
        'codigo_destino': line.codigo_destino,
        'origen': line.origen,
        'signo': line.signo,
        'monto_clp': str(line.monto_clp),
        'formula_ref': line.formula_ref,
        'evidencia_ref': line.evidencia_ref,
        'warnings': line.warnings,
        'source_payload': line.source_payload,
    }


def _enterprise_movement_integrity_payload(movement):
    return {
        'register_set_id': movement.register_set_id,
        'source_workbook_line_id': movement.source_workbook_line_id,
        'codigo_interno': movement.codigo_interno,
        'origen': movement.origen,
        'signo': movement.signo,
        'monto_clp': str(movement.monto_clp),
        'formula_ref': movement.formula_ref,
        'evidencia_ref': movement.evidencia_ref,
        'warnings': movement.warnings,
        'source_payload': movement.source_payload,
    }


def _real_estate_item_integrity_payload(item):
    return {
        'section_id': item.section_id,
        'propiedad_id': item.propiedad_id,
        'codigo_propiedad_snapshot': item.codigo_propiedad_snapshot,
        'rol_avaluo_snapshot': item.rol_avaluo_snapshot,
        'direccion_snapshot': item.direccion_snapshot,
        'comuna_snapshot': item.comuna_snapshot,
        'region_snapshot': item.region_snapshot,
        'tipo_inmueble_snapshot': item.tipo_inmueble_snapshot,
        'owner_tipo_snapshot': item.owner_tipo_snapshot,
        'owner_id_snapshot': item.owner_id_snapshot,
        'arriendo_devengado_clp': str(item.arriendo_devengado_clp),
        'arriendo_conciliado_clp': str(item.arriendo_conciliado_clp),
        'arriendo_facturable_clp': str(item.arriendo_facturable_clp),
        'contribuciones_clp': str(item.contribuciones_clp),
        'formula_ref': item.formula_ref,
        'evidencia_ref': item.evidencia_ref,
        'warnings': item.warnings,
        'source_payload': item.source_payload,
    }


def _annual_tax_artifact_matrix_item_integrity_payload(item):
    return {
        'matrix_id': item.matrix_id,
        'target_kind': item.target_kind,
        'target_code': item.target_code,
        'medio_sii': item.medio_sii,
        'source_kind': item.source_kind,
        'source_model': item.source_model,
        'source_object_id': item.source_object_id,
        'source_hash': item.source_hash,
        'review_state': item.review_state,
        'formula_ref': item.formula_ref,
        'evidencia_ref': item.evidencia_ref,
        'responsible_ref': item.responsible_ref,
        'warnings': item.warnings,
        'source_payload': item.source_payload,
    }


class TaxYearRuleSet(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'version',
        'fuente_ref',
        'hash_normativo',
        'responsable_aprobacion_ref',
        'descripcion',
    )

    anio_tributario = models.PositiveSmallIntegerField()
    regimen_tributario = models.ForeignKey(
        RegimenTributarioEmpresa,
        on_delete=models.PROTECT,
        related_name='tax_year_rule_sets',
    )
    version = models.CharField(max_length=32)
    estado = models.CharField(
        max_length=16,
        choices=EstadoReglaTributariaAnual.choices,
        default=EstadoReglaTributariaAnual.DRAFT,
    )
    fuente_ref = models.CharField(max_length=255, blank=True)
    hash_normativo = models.CharField(max_length=64, blank=True)
    responsable_aprobacion_ref = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-anio_tributario', 'regimen_tributario_id', 'version']
        constraints = [
            models.UniqueConstraint(
                fields=['anio_tributario', 'regimen_tributario', 'version'],
                name='uniq_tax_year_ruleset_version',
            ),
            models.UniqueConstraint(
                fields=['anio_tributario', 'regimen_tributario'],
                condition=Q(estado=EstadoReglaTributariaAnual.APPROVED),
                name='uniq_tax_year_ruleset_approved',
            ),
        ]

    def __str__(self):
        return f'AT{self.anio_tributario} {self.regimen_tributario.codigo_regimen} {self.version}'

    def clean(self):
        super().clean()
        self.hash_normativo = _normalize_hash(self.hash_normativo)
        errors = {}
        try:
            regimen_tributario = self.regimen_tributario
        except ObjectDoesNotExist:
            regimen_tributario = None
        if self.estado == EstadoReglaTributariaAnual.APPROVED:
            if not has_text(self.fuente_ref):
                errors['fuente_ref'] = 'TaxYearRuleSet aprobado requiere fuente_ref no sensible.'
            if not has_text(self.hash_normativo):
                errors['hash_normativo'] = 'TaxYearRuleSet aprobado requiere hash_normativo.'
            if not has_text(self.responsable_aprobacion_ref):
                errors['responsable_aprobacion_ref'] = 'TaxYearRuleSet aprobado requiere responsable_aprobacion_ref.'
            if regimen_tributario is None:
                errors['regimen_tributario'] = 'TaxYearRuleSet aprobado requiere regimen tributario.'
            elif regimen_tributario.estado != EstadoRegistro.ACTIVE:
                errors['regimen_tributario'] = 'TaxYearRuleSet aprobado requiere regimen tributario activo.'
        if has_text(self.hash_normativo) and not _is_sha256(self.hash_normativo):
            errors['hash_normativo'] = 'hash_normativo debe ser SHA-256 hexadecimal de 64 caracteres.'
        _add_non_sensitive_reference_error(errors, self, 'fuente_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsable_aprobacion_ref')
        _add_non_sensitive_payload_error(errors, 'metadata', self.metadata)
        if errors:
            raise ValidationError(errors)


class TaxCodeMapping(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'codigo_interno',
        'codigo_destino',
        'formula_ref',
        'evidencia_ref',
    )

    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.CASCADE,
        related_name='code_mappings',
    )
    destino = models.CharField(max_length=16, choices=DestinoMapeoTributarioAnual.choices)
    codigo_interno = models.CharField(max_length=64)
    codigo_destino = models.CharField(max_length=64)
    formula_ref = models.CharField(max_length=255, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['rule_set_id', 'destino', 'codigo_interno', 'codigo_destino']
        constraints = [
            models.UniqueConstraint(
                fields=['rule_set', 'destino', 'codigo_interno', 'codigo_destino'],
                name='uniq_tax_code_mapping_target',
            ),
        ]

    def __str__(self):
        return f'{self.rule_set_id} {self.destino}:{self.codigo_interno}->{self.codigo_destino}'

    def clean(self):
        super().clean()
        errors = {}
        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is None:
            errors['rule_set'] = 'Mapeo tributario requiere TaxYearRuleSet.'
        elif self.estado == EstadoRegistro.ACTIVE and rule_set.estado == EstadoReglaTributariaAnual.APPROVED:
            if not has_text(self.formula_ref):
                errors['formula_ref'] = 'Mapeo activo de rule set aprobado requiere formula_ref no sensible.'
            if not has_text(self.evidencia_ref):
                errors['evidencia_ref'] = 'Mapeo activo de rule set aprobado requiere evidencia_ref no sensible.'
        _add_non_sensitive_reference_error(errors, self, 'formula_ref')
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')
        _add_non_sensitive_payload_error(errors, 'metadata', self.metadata)
        if errors:
            raise ValidationError(errors)


class AnnualTaxOfficialSource(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_key',
        'title',
        'source_url',
        'source_ref',
        'source_hash',
        'responsible_ref',
        'scope_note',
        'form_code',
        'regime_code',
    )

    anio_tributario = models.PositiveSmallIntegerField()
    source_key = models.CharField(max_length=96)
    source_type = models.CharField(max_length=64, choices=TipoAnnualTaxOfficialSource.choices)
    title = models.CharField(max_length=160)
    source_url = models.CharField(max_length=255, blank=True)
    source_ref = models.CharField(max_length=255, blank=True)
    source_hash = models.CharField(max_length=64, blank=True)
    retrieved_on = models.DateField(null=True, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxOfficialSource.choices,
        default=EstadoAnnualTaxOfficialSource.DRAFT,
    )
    applies_to = models.CharField(max_length=16, choices=DestinoMapeoTributarioAnual.choices, blank=True)
    form_code = models.CharField(max_length=32, blank=True)
    regime_code = models.CharField(max_length=64, blank=True)
    scope_note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-anio_tributario', 'source_type', 'source_key']
        constraints = [
            models.UniqueConstraint(
                fields=['anio_tributario', 'source_key'],
                name='uniq_annual_tax_official_source_key',
            ),
        ]

    def __str__(self):
        return f'AT{self.anio_tributario} {self.source_key}'

    def clean(self):
        super().clean()
        self.source_hash = _normalize_hash(self.source_hash)
        errors = {}
        if self.anio_tributario < 2000:
            errors['anio_tributario'] = 'anio_tributario debe ser un ano tributario valido.'
        if self.source_type.startswith('sii_'):
            if not has_text(self.source_url):
                errors['source_url'] = 'Fuente oficial SII requiere source_url publica trazable.'
            elif not is_safe_public_sii_source_url(self.source_url):
                errors['source_url'] = 'source_url debe ser HTTPS, publica, sin query/fragment y bajo dominio SII permitido.'
        elif has_text(self.source_url) and not is_safe_public_sii_source_url(self.source_url):
            errors['source_url'] = 'source_url solo admite URL publica SII segura.'
        if self.estado in {
            EstadoAnnualTaxOfficialSource.REVIEWED,
            EstadoAnnualTaxOfficialSource.APPROVED,
        }:
            if not has_text(self.title):
                errors['title'] = 'Fuente revisada requiere title.'
            if not has_text(self.source_ref):
                errors['source_ref'] = 'Fuente revisada requiere source_ref no sensible.'
            if not has_text(self.source_hash):
                errors['source_hash'] = 'Fuente revisada requiere source_hash SHA-256.'
            if self.retrieved_on is None:
                errors['retrieved_on'] = 'Fuente revisada requiere retrieved_on.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'Fuente revisada requiere responsible_ref no sensible.'
        if has_text(self.source_hash) and not _is_sha256(self.source_hash):
            errors['source_hash'] = 'source_hash debe ser SHA-256 hexadecimal de 64 caracteres.'
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_text_error(errors, 'scope_note', self.scope_note)
        _add_non_sensitive_payload_error(errors, 'metadata', self.metadata)
        if errors:
            raise ValidationError(errors)


class AnnualTaxSourceBundle(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_label',
        'authorization_ref',
        'responsible_ref',
        'hash_fuentes',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_source_bundles',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    source_kind = models.CharField(
        max_length=32,
        choices=SourceKindRentaAnual.choices,
        default=SourceKindRentaAnual.LOCAL,
    )
    source_label = models.CharField(max_length=255, blank=True)
    authorization_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    hash_fuentes = models.CharField(max_length=64, blank=True)
    resumen_fuentes = models.JSONField(default=dict, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxSourceBundle.choices,
        default=EstadoAnnualTaxSourceBundle.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'source_kind', 'source_label']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'anio_tributario', 'source_kind', 'source_label'],
                name='uniq_annual_tax_source_bundle_label',
            ),
            models.UniqueConstraint(
                fields=['empresa', 'anio_tributario'],
                condition=Q(estado=EstadoAnnualTaxSourceBundle.FROZEN),
                name='uniq_annual_tax_source_bundle_frozen',
            ),
        ]

    def __str__(self):
        return f'{self.empresa_id} AT{self.anio_tributario} {self.source_kind}:{self.source_label}'

    def clean(self):
        super().clean()
        self.hash_fuentes = _normalize_hash(self.hash_fuentes)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_label')
        _add_non_sensitive_reference_error(errors, self, 'authorization_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_fuentes', self.resumen_fuentes)
        if has_text(self.hash_fuentes) and not _is_sha256(self.hash_fuentes):
            errors['hash_fuentes'] = 'hash_fuentes debe ser SHA-256 hexadecimal de 64 caracteres.'

        if self.estado == EstadoAnnualTaxSourceBundle.FROZEN:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxSourceBundle')
            if not has_text(self.source_label):
                errors['source_label'] = 'AnnualTaxSourceBundle congelado requiere source_label no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxSourceBundle congelado requiere responsible_ref no sensible.'
            if not has_text(self.hash_fuentes):
                errors['hash_fuentes'] = 'AnnualTaxSourceBundle congelado requiere hash_fuentes.'
            elif isinstance(self.resumen_fuentes, dict) and self.hash_fuentes != _payload_hash(self.resumen_fuentes):
                errors['hash_fuentes'] = 'hash_fuentes debe corresponder al resumen_fuentes congelado.'
            if self.source_kind in {
                SourceKindRentaAnual.CONTROLLED_SNAPSHOT,
                SourceKindRentaAnual.AUTHORIZED_REAL,
            } and not has_text(self.authorization_ref):
                errors['authorization_ref'] = (
                    'AnnualTaxSourceBundle evidencial requiere authorization_ref no sensible.'
                )

            summary = self.resumen_fuentes if isinstance(self.resumen_fuentes, dict) else {}
            close_months = summary.get('approved_close_months') or []
            try:
                normalized_close_months = sorted({int(month) for month in close_months})
            except (TypeError, ValueError):
                normalized_close_months = []
            if normalized_close_months != list(range(1, 13)):
                errors['resumen_fuentes'] = (
                    'AnnualTaxSourceBundle congelado requiere doce cierres mensuales aprobados.'
                )
            obligation_months = summary.get('obligation_months') or []
            try:
                normalized_obligation_months = sorted({int(month) for month in obligation_months})
            except (TypeError, ValueError):
                normalized_obligation_months = []
            if normalized_obligation_months != list(range(1, 13)):
                _add_error(
                    errors,
                    'resumen_fuentes',
                    'AnnualTaxSourceBundle congelado requiere obligaciones mensuales trazables para los doce meses.',
                )
        if errors:
            raise ValidationError(errors)


class MonthlyTaxFact(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'hash_hecho',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='monthly_tax_facts',
    )
    anio = models.PositiveSmallIntegerField()
    mes = models.PositiveSmallIntegerField()
    cierre_mensual = models.ForeignKey(
        CierreMensualContable,
        on_delete=models.PROTECT,
        related_name='monthly_tax_facts',
    )
    f29_preparacion = models.ForeignKey(
        F29PreparacionMensual,
        on_delete=models.PROTECT,
        related_name='monthly_tax_facts',
        null=True,
        blank=True,
    )
    liquidacion_mensual = models.ForeignKey(
        LiquidacionMensual,
        on_delete=models.PROTECT,
        related_name='monthly_tax_facts',
        null=True,
        blank=True,
    )
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    resumen_hecho = models.JSONField(default=dict, blank=True)
    hash_hecho = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoMonthlyTaxFact.choices,
        default=EstadoMonthlyTaxFact.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio', 'mes']
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'anio', 'mes'],
                name='uniq_monthly_tax_fact_por_empresa_periodo',
            ),
        ]

    def __str__(self):
        return f'{self.empresa_id} {self.anio}-{self.mes:02d}'

    def clean(self):
        super().clean()
        self.hash_hecho = _normalize_hash(self.hash_hecho)
        errors = {}
        if self.mes < 1 or self.mes > 12:
            errors['mes'] = 'mes debe estar entre 1 y 12.'
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_hecho', self.resumen_hecho)

        if self.cierre_mensual_id:
            if self.cierre_mensual.empresa_id != self.empresa_id:
                errors['cierre_mensual'] = 'El cierre mensual debe pertenecer a la misma empresa del hecho mensual.'
            elif self.cierre_mensual.anio != self.anio or self.cierre_mensual.mes != self.mes:
                errors['cierre_mensual'] = 'El cierre mensual debe coincidir con el periodo del hecho mensual.'
            elif self.estado == EstadoMonthlyTaxFact.NORMALIZED and self.cierre_mensual.estado != EstadoCierreMensual.APPROVED:
                errors['cierre_mensual'] = 'El hecho mensual normalizado requiere cierre mensual aprobado.'

        if self.f29_preparacion_id:
            if self.f29_preparacion.empresa_id != self.empresa_id:
                errors['f29_preparacion'] = 'El F29 debe pertenecer a la misma empresa del hecho mensual.'
            elif self.f29_preparacion.anio != self.anio or self.f29_preparacion.mes != self.mes:
                errors['f29_preparacion'] = 'El F29 debe coincidir con el periodo del hecho mensual.'
            elif self.estado == EstadoMonthlyTaxFact.NORMALIZED and self.f29_preparacion.estado_preparacion not in {
                EstadoPreparacionTributaria.PREPARED,
                EstadoPreparacionTributaria.APPROVED,
                EstadoPreparacionTributaria.OBSERVED,
                EstadoPreparacionTributaria.RECTIFIED,
            }:
                errors['f29_preparacion'] = 'El hecho mensual normalizado requiere F29 trazable si existe F29 asociado.'

        if self.liquidacion_mensual_id:
            if self.liquidacion_mensual.empresa_id != self.empresa_id:
                errors['liquidacion_mensual'] = 'La liquidacion mensual debe pertenecer a la misma empresa.'
            elif self.liquidacion_mensual.anio != self.anio or self.liquidacion_mensual.mes != self.mes:
                errors['liquidacion_mensual'] = 'La liquidacion mensual debe coincidir con el periodo del hecho.'
            elif self.estado == EstadoMonthlyTaxFact.NORMALIZED and self.liquidacion_mensual.estado not in {
                EstadoLiquidacionMensual.PREPARED,
                EstadoLiquidacionMensual.APPROVED,
            }:
                errors['liquidacion_mensual'] = 'El hecho mensual normalizado requiere liquidacion preparada o aprobada.'

        if self.resumen_hecho and not isinstance(self.resumen_hecho, dict):
            errors['resumen_hecho'] = 'resumen_hecho debe ser un objeto JSON.'
        elif isinstance(self.resumen_hecho, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('anio', self.anio),
                ('mes', self.mes),
            ):
                value = self.resumen_hecho.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_hecho'] = 'resumen_hecho debe coincidir con empresa, anio y mes.'
            expected_hash = _payload_hash(self.resumen_hecho)
            if self.hash_hecho and self.hash_hecho != expected_hash:
                errors['hash_hecho'] = 'hash_hecho debe corresponder al resumen_hecho mensual.'

        if self.estado == EstadoMonthlyTaxFact.NORMALIZED:
            _add_active_fiscal_config_error(errors, self, 'MonthlyTaxFact')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'MonthlyTaxFact normalizado requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'MonthlyTaxFact normalizado requiere responsible_ref no sensible.'
            if not self.resumen_hecho:
                errors['resumen_hecho'] = 'MonthlyTaxFact normalizado requiere resumen_hecho.'
            if not has_text(self.hash_hecho):
                errors['hash_hecho'] = 'MonthlyTaxFact normalizado requiere hash_hecho.'
        if has_text(self.hash_hecho) and not _is_sha256(self.hash_hecho):
            errors['hash_hecho'] = 'hash_hecho debe ser SHA-256 hexadecimal de 64 caracteres.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxWorkbook(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'hash_workbook',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_workbooks',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='tax_workbooks',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='tax_workbooks',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='tax_workbooks',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    tipo = models.CharField(max_length=8, choices=TipoAnnualTaxWorkbook.choices)
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    resumen_workbook = models.JSONField(default=dict, blank=True)
    hash_workbook = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxWorkbook.choices,
        default=EstadoAnnualTaxWorkbook.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'tipo']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual', 'tipo'],
                name='uniq_annual_tax_workbook_process_tipo',
            ),
        ]

    def __str__(self):
        return f'{self.tipo} {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_workbook = _normalize_hash(self.hash_workbook)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_workbook', self.resumen_workbook)
        if has_text(self.hash_workbook) and not _is_sha256(self.hash_workbook):
            errors['hash_workbook'] = 'hash_workbook debe ser SHA-256 hexadecimal de 64 caracteres.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa del workbook.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'El workbook debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa del workbook.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualTaxWorkbook requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario del workbook.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualTaxWorkbook requiere TaxYearRuleSet aprobado.'

        if isinstance(self.resumen_workbook, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('tipo', self.tipo),
            ):
                value = self.resumen_workbook.get(key)
                if value is None:
                    continue
                if key == 'tipo':
                    matches = str(value) == str(expected)
                else:
                    try:
                        matches = int(value) == int(expected)
                    except (TypeError, ValueError):
                        matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_workbook'] = 'resumen_workbook debe coincidir con empresa, proceso, fuente, regla, anio y tipo.'
            expected_hash = _payload_hash(self.resumen_workbook)
            if self.hash_workbook and self.hash_workbook != expected_hash:
                errors['hash_workbook'] = 'hash_workbook debe corresponder al resumen_workbook.'
        elif self.resumen_workbook:
            errors['resumen_workbook'] = 'resumen_workbook debe ser un objeto JSON.'

        if self.estado == EstadoAnnualTaxWorkbook.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxWorkbook')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualTaxWorkbook preparado requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxWorkbook preparado requiere responsible_ref no sensible.'
            if not self.resumen_workbook:
                errors['resumen_workbook'] = 'AnnualTaxWorkbook preparado requiere resumen_workbook.'
            if not has_text(self.hash_workbook):
                errors['hash_workbook'] = 'AnnualTaxWorkbook preparado requiere hash_workbook.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxWorkbookLine(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'codigo_interno',
        'codigo_destino',
        'origen',
        'formula_ref',
        'evidencia_ref',
        'hash_linea',
    )

    workbook = models.ForeignKey(
        AnnualTaxWorkbook,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    mapping = models.ForeignKey(
        TaxCodeMapping,
        on_delete=models.PROTECT,
        related_name='annual_tax_lines',
    )
    codigo_interno = models.CharField(max_length=64)
    codigo_destino = models.CharField(max_length=64)
    origen = models.CharField(max_length=64)
    signo = models.CharField(max_length=16, choices=SignoAnnualTaxLine.choices, default=SignoAnnualTaxLine.INFO)
    monto_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    formula_ref = models.CharField(max_length=255, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_linea = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['workbook_id', 'codigo_interno', 'codigo_destino']
        constraints = [
            models.UniqueConstraint(
                fields=['workbook', 'codigo_interno', 'codigo_destino'],
                name='uniq_annual_tax_workbook_line_target',
            ),
        ]

    def __str__(self):
        return f'{self.workbook_id} {self.codigo_interno}->{self.codigo_destino}'

    def clean(self):
        super().clean()
        self.hash_linea = _normalize_hash(self.hash_linea)
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'formula_ref')
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')
        _add_non_sensitive_payload_error(errors, 'warnings', self.warnings)
        _add_non_sensitive_payload_error(errors, 'source_payload', self.source_payload)
        if self.warnings and not isinstance(self.warnings, list):
            errors['warnings'] = 'warnings debe ser una lista JSON.'
        if self.source_payload and not isinstance(self.source_payload, dict):
            errors['source_payload'] = 'source_payload debe ser un objeto JSON.'
        if has_text(self.hash_linea) and not _is_sha256(self.hash_linea):
            errors['hash_linea'] = 'hash_linea debe ser SHA-256 hexadecimal de 64 caracteres.'

        try:
            workbook = self.workbook
        except ObjectDoesNotExist:
            workbook = None
        try:
            mapping = self.mapping
        except ObjectDoesNotExist:
            mapping = None

        if workbook is not None and mapping is not None:
            if mapping.rule_set_id != workbook.rule_set_id:
                errors['mapping'] = 'La linea debe usar un TaxCodeMapping del mismo TaxYearRuleSet del workbook.'
            if mapping.destino != workbook.tipo:
                errors['mapping'] = 'La linea RLI/CPT debe coincidir con el destino del TaxCodeMapping.'
            if self.codigo_interno != mapping.codigo_interno:
                errors['codigo_interno'] = 'codigo_interno debe coincidir con el TaxCodeMapping.'
            if self.codigo_destino != mapping.codigo_destino:
                errors['codigo_destino'] = 'codigo_destino debe coincidir con el TaxCodeMapping.'

        expected_hash = _payload_hash(_line_integrity_payload(self))
        if self.hash_linea and self.hash_linea != expected_hash:
            errors['hash_linea'] = 'hash_linea debe corresponder a la linea normalizada.'

        if self.estado == EstadoRegistro.ACTIVE:
            if not has_text(self.origen):
                errors['origen'] = 'Linea activa requiere origen trazable.'
            if not has_text(self.formula_ref):
                errors['formula_ref'] = 'Linea activa requiere formula_ref no sensible.'
            if not has_text(self.evidencia_ref):
                errors['evidencia_ref'] = 'Linea activa requiere evidencia_ref no sensible.'
            if not self.source_payload:
                errors['source_payload'] = 'Linea activa requiere source_payload trazable.'
            if not has_text(self.hash_linea):
                errors['hash_linea'] = 'Linea activa requiere hash_linea.'
        if errors:
            raise ValidationError(errors)


class AnnualEnterpriseRegisterSet(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'hash_registro',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_enterprise_registers',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='enterprise_registers',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='enterprise_registers',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='enterprise_registers',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    tipo_registro = models.CharField(max_length=16, choices=TipoAnnualEnterpriseRegister.choices)
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    saldo_inicial_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    movimientos_total_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    saldo_final_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    resumen_registro = models.JSONField(default=dict, blank=True)
    hash_registro = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualEnterpriseRegister.choices,
        default=EstadoAnnualEnterpriseRegister.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'tipo_registro']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual', 'tipo_registro'],
                name='uniq_annual_enterprise_register_process_tipo',
            ),
        ]

    def __str__(self):
        return f'{self.tipo_registro} {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_registro = _normalize_hash(self.hash_registro)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_registro', self.resumen_registro)
        if has_text(self.hash_registro) and not _is_sha256(self.hash_registro):
            errors['hash_registro'] = 'hash_registro debe ser SHA-256 hexadecimal de 64 caracteres.'
        if self.saldo_final_clp != self.saldo_inicial_clp + self.movimientos_total_clp:
            errors['saldo_final_clp'] = 'saldo_final_clp debe ser saldo_inicial_clp + movimientos_total_clp.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa del registro.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'El registro debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa del registro.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualEnterpriseRegisterSet requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario del registro.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualEnterpriseRegisterSet requiere TaxYearRuleSet aprobado.'

        if isinstance(self.resumen_registro, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('tipo_registro', self.tipo_registro),
                ('saldo_inicial_clp', str(self.saldo_inicial_clp)),
                ('movimientos_total_clp', str(self.movimientos_total_clp)),
                ('saldo_final_clp', str(self.saldo_final_clp)),
            ):
                value = self.resumen_registro.get(key)
                if value is None:
                    continue
                if key in {'tipo_registro', 'saldo_inicial_clp', 'movimientos_total_clp', 'saldo_final_clp'}:
                    matches = str(value) == str(expected)
                else:
                    try:
                        matches = int(value) == int(expected)
                    except (TypeError, ValueError):
                        matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_registro'] = (
                    'resumen_registro debe coincidir con empresa, proceso, fuente, regla, anio, tipo y saldos.'
                )
            expected_hash = _payload_hash(self.resumen_registro)
            if self.hash_registro and self.hash_registro != expected_hash:
                errors['hash_registro'] = 'hash_registro debe corresponder al resumen_registro.'
        elif self.resumen_registro:
            errors['resumen_registro'] = 'resumen_registro debe ser un objeto JSON.'

        if self.estado == EstadoAnnualEnterpriseRegister.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualEnterpriseRegisterSet')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualEnterpriseRegisterSet preparado requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualEnterpriseRegisterSet preparado requiere responsible_ref no sensible.'
            if not self.resumen_registro:
                errors['resumen_registro'] = 'AnnualEnterpriseRegisterSet preparado requiere resumen_registro.'
            if not has_text(self.hash_registro):
                errors['hash_registro'] = 'AnnualEnterpriseRegisterSet preparado requiere hash_registro.'
        if errors:
            raise ValidationError(errors)


class AnnualEnterpriseRegisterMovement(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'codigo_interno',
        'origen',
        'formula_ref',
        'evidencia_ref',
        'hash_movimiento',
    )

    register_set = models.ForeignKey(
        AnnualEnterpriseRegisterSet,
        on_delete=models.CASCADE,
        related_name='movements',
    )
    source_workbook_line = models.ForeignKey(
        AnnualTaxWorkbookLine,
        on_delete=models.PROTECT,
        related_name='enterprise_register_movements',
        null=True,
        blank=True,
    )
    codigo_interno = models.CharField(max_length=64)
    origen = models.CharField(max_length=64)
    signo = models.CharField(max_length=16, choices=SignoAnnualTaxLine.choices, default=SignoAnnualTaxLine.INFO)
    monto_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    formula_ref = models.CharField(max_length=255, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_movimiento = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['register_set_id', 'codigo_interno', 'origen']
        constraints = [
            models.UniqueConstraint(
                fields=['register_set', 'codigo_interno', 'origen'],
                name='uniq_enterprise_register_movement_origin',
            ),
        ]

    def __str__(self):
        return f'{self.register_set_id} {self.codigo_interno}'

    def clean(self):
        super().clean()
        self.hash_movimiento = _normalize_hash(self.hash_movimiento)
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'formula_ref')
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')
        _add_non_sensitive_payload_error(errors, 'warnings', self.warnings)
        _add_non_sensitive_payload_error(errors, 'source_payload', self.source_payload)
        if self.warnings and not isinstance(self.warnings, list):
            errors['warnings'] = 'warnings debe ser una lista JSON.'
        if self.source_payload and not isinstance(self.source_payload, dict):
            errors['source_payload'] = 'source_payload debe ser un objeto JSON.'
        if has_text(self.hash_movimiento) and not _is_sha256(self.hash_movimiento):
            errors['hash_movimiento'] = 'hash_movimiento debe ser SHA-256 hexadecimal de 64 caracteres.'

        try:
            register_set = self.register_set
        except ObjectDoesNotExist:
            register_set = None
        try:
            source_workbook_line = self.source_workbook_line
        except ObjectDoesNotExist:
            source_workbook_line = None

        if register_set is not None and source_workbook_line is not None:
            workbook = source_workbook_line.workbook
            if workbook.proceso_renta_anual_id != register_set.proceso_renta_anual_id:
                errors['source_workbook_line'] = 'El movimiento debe usar una linea RLI/CPT del mismo proceso anual.'
            elif workbook.rule_set_id != register_set.rule_set_id:
                errors['source_workbook_line'] = 'El movimiento debe usar una linea RLI/CPT del mismo TaxYearRuleSet.'
            elif workbook.empresa_id != register_set.empresa_id:
                errors['source_workbook_line'] = 'El movimiento debe usar una linea RLI/CPT de la misma empresa.'

        expected_hash = _payload_hash(_enterprise_movement_integrity_payload(self))
        if self.hash_movimiento and self.hash_movimiento != expected_hash:
            errors['hash_movimiento'] = 'hash_movimiento debe corresponder al movimiento normalizado.'

        if self.estado == EstadoRegistro.ACTIVE:
            if not has_text(self.origen):
                errors['origen'] = 'Movimiento activo requiere origen trazable.'
            if not has_text(self.formula_ref):
                errors['formula_ref'] = 'Movimiento activo requiere formula_ref no sensible.'
            if not has_text(self.evidencia_ref):
                errors['evidencia_ref'] = 'Movimiento activo requiere evidencia_ref no sensible.'
            if not self.source_payload:
                errors['source_payload'] = 'Movimiento activo requiere source_payload trazable.'
            if not has_text(self.hash_movimiento):
                errors['hash_movimiento'] = 'Movimiento activo requiere hash_movimiento.'
        if errors:
            raise ValidationError(errors)


class AnnualRealEstateSection(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'hash_seccion',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_real_estate_sections',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='real_estate_sections',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='real_estate_sections',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='real_estate_sections',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    propiedades_total = models.PositiveIntegerField(default=0)
    arriendo_devengado_total_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    arriendo_conciliado_total_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    arriendo_facturable_total_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    contribuciones_total_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    resumen_seccion = models.JSONField(default=dict, blank=True)
    hash_seccion = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualRealEstateSection.choices,
        default=EstadoAnnualRealEstateSection.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual'],
                name='uniq_annual_real_estate_section_process',
            ),
        ]

    def __str__(self):
        return f'Bienes raices {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_seccion = _normalize_hash(self.hash_seccion)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_seccion', self.resumen_seccion)
        if has_text(self.hash_seccion) and not _is_sha256(self.hash_seccion):
            errors['hash_seccion'] = 'hash_seccion debe ser SHA-256 hexadecimal de 64 caracteres.'
        if min(
            self.arriendo_devengado_total_clp,
            self.arriendo_conciliado_total_clp,
            self.arriendo_facturable_total_clp,
            self.contribuciones_total_clp,
        ) < 0:
            errors['resumen_seccion'] = 'Los totales de la seccion anual inmobiliaria no pueden ser negativos.'
        if self.arriendo_facturable_total_clp > self.arriendo_devengado_total_clp:
            errors['arriendo_facturable_total_clp'] = 'El total facturable no puede exceder el devengado.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa de la seccion.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'La seccion debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa de la seccion.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualRealEstateSection requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario de la seccion.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualRealEstateSection requiere TaxYearRuleSet aprobado.'

        if isinstance(self.resumen_seccion, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('propiedades_total', self.propiedades_total),
                ('arriendo_devengado_total_clp', str(self.arriendo_devengado_total_clp)),
                ('arriendo_conciliado_total_clp', str(self.arriendo_conciliado_total_clp)),
                ('arriendo_facturable_total_clp', str(self.arriendo_facturable_total_clp)),
                ('contribuciones_total_clp', str(self.contribuciones_total_clp)),
            ):
                value = self.resumen_seccion.get(key)
                if value is None:
                    continue
                if key.endswith('_clp'):
                    matches = str(value) == str(expected)
                else:
                    try:
                        matches = int(value) == int(expected)
                    except (TypeError, ValueError):
                        matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_seccion'] = (
                    'resumen_seccion debe coincidir con empresa, proceso, fuente, regla, anio y totales.'
                )
            expected_hash = _payload_hash(self.resumen_seccion)
            if self.hash_seccion and self.hash_seccion != expected_hash:
                errors['hash_seccion'] = 'hash_seccion debe corresponder al resumen_seccion.'
        elif self.resumen_seccion:
            errors['resumen_seccion'] = 'resumen_seccion debe ser un objeto JSON.'

        if self.estado == EstadoAnnualRealEstateSection.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualRealEstateSection')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualRealEstateSection preparada requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualRealEstateSection preparada requiere responsible_ref no sensible.'
            if not self.resumen_seccion:
                errors['resumen_seccion'] = 'AnnualRealEstateSection preparada requiere resumen_seccion.'
            if not has_text(self.hash_seccion):
                errors['hash_seccion'] = 'AnnualRealEstateSection preparada requiere hash_seccion.'
        if errors:
            raise ValidationError(errors)


class AnnualRealEstateItem(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'codigo_propiedad_snapshot',
        'rol_avaluo_snapshot',
        'direccion_snapshot',
        'comuna_snapshot',
        'region_snapshot',
        'tipo_inmueble_snapshot',
        'owner_tipo_snapshot',
        'formula_ref',
        'evidencia_ref',
        'hash_item',
    )

    section = models.ForeignKey(
        AnnualRealEstateSection,
        on_delete=models.CASCADE,
        related_name='items',
    )
    propiedad = models.ForeignKey(
        'patrimonio.Propiedad',
        on_delete=models.PROTECT,
        related_name='annual_real_estate_items',
    )
    codigo_propiedad_snapshot = models.CharField(max_length=16)
    rol_avaluo_snapshot = models.CharField(max_length=64, blank=True)
    direccion_snapshot = models.CharField(max_length=255)
    comuna_snapshot = models.CharField(max_length=100)
    region_snapshot = models.CharField(max_length=100)
    tipo_inmueble_snapshot = models.CharField(max_length=32)
    owner_tipo_snapshot = models.CharField(max_length=32)
    owner_id_snapshot = models.PositiveIntegerField()
    arriendo_devengado_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    arriendo_conciliado_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    arriendo_facturable_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    contribuciones_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    formula_ref = models.CharField(max_length=255, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_item = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['section_id', 'codigo_propiedad_snapshot', 'propiedad_id']
        constraints = [
            models.UniqueConstraint(
                fields=['section', 'propiedad'],
                name='uniq_annual_real_estate_item_property',
            ),
        ]

    def __str__(self):
        return f'{self.section_id} {self.codigo_propiedad_snapshot}'

    def clean(self):
        super().clean()
        self.hash_item = _normalize_hash(self.hash_item)
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'formula_ref')
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')
        _add_non_sensitive_payload_error(errors, 'warnings', self.warnings)
        _add_non_sensitive_payload_error(errors, 'source_payload', self.source_payload)
        if self.warnings and not isinstance(self.warnings, list):
            errors['warnings'] = 'warnings debe ser una lista JSON.'
        if self.source_payload and not isinstance(self.source_payload, dict):
            errors['source_payload'] = 'source_payload debe ser un objeto JSON.'
        if has_text(self.hash_item) and not _is_sha256(self.hash_item):
            errors['hash_item'] = 'hash_item debe ser SHA-256 hexadecimal de 64 caracteres.'
        if min(
            self.arriendo_devengado_clp,
            self.arriendo_conciliado_clp,
            self.arriendo_facturable_clp,
            self.contribuciones_clp,
        ) < 0:
            errors['source_payload'] = 'Los montos del item inmobiliario no pueden ser negativos.'
        if self.arriendo_facturable_clp > self.arriendo_devengado_clp:
            errors['arriendo_facturable_clp'] = 'El monto facturable no puede exceder el devengado.'

        try:
            section = self.section
        except ObjectDoesNotExist:
            section = None
        if section is not None and isinstance(self.source_payload, dict):
            for key, expected in (
                ('empresa_id', section.empresa_id),
                ('proceso_renta_anual_id', section.proceso_renta_anual_id),
                ('anio_tributario', section.anio_tributario),
                ('anio_comercial', section.anio_comercial),
            ):
                value = self.source_payload.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    errors['source_payload'] = 'source_payload debe coincidir con la seccion anual inmobiliaria.'
                    break

        if isinstance(self.source_payload, dict):
            payload_property_id = self.source_payload.get('propiedad_id')
            if payload_property_id is not None:
                try:
                    property_matches = int(payload_property_id) == int(self.propiedad_id)
                except (TypeError, ValueError):
                    property_matches = False
                if not property_matches:
                    errors['source_payload'] = 'source_payload debe coincidir con la propiedad del item inmobiliario.'

        expected_hash = _payload_hash(_real_estate_item_integrity_payload(self))
        if self.hash_item and self.hash_item != expected_hash:
            errors['hash_item'] = 'hash_item debe corresponder al item inmobiliario normalizado.'

        if self.estado == EstadoRegistro.ACTIVE:
            for field_name in (
                'codigo_propiedad_snapshot',
                'direccion_snapshot',
                'comuna_snapshot',
                'region_snapshot',
                'tipo_inmueble_snapshot',
                'owner_tipo_snapshot',
            ):
                if not has_text(getattr(self, field_name)):
                    errors[field_name] = 'Item inmobiliario activo requiere snapshot de propiedad completo.'
            if not self.owner_id_snapshot:
                errors['owner_id_snapshot'] = 'Item inmobiliario activo requiere owner_id_snapshot.'
            if not has_text(self.formula_ref):
                errors['formula_ref'] = 'Item inmobiliario activo requiere formula_ref no sensible.'
            if not has_text(self.evidencia_ref):
                errors['evidencia_ref'] = 'Item inmobiliario activo requiere evidencia_ref no sensible.'
            if not self.source_payload:
                errors['source_payload'] = 'Item inmobiliario activo requiere source_payload trazable.'
            if not has_text(self.hash_item):
                errors['hash_item'] = 'Item inmobiliario activo requiere hash_item.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxArtifactMatrix(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'hash_matriz',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_artifact_matrices',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='artifact_matrices',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='artifact_matrices',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='artifact_matrices',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    items_total = models.PositiveIntegerField(default=0)
    ddjj_items_total = models.PositiveIntegerField(default=0)
    f22_items_total = models.PositiveIntegerField(default=0)
    resumen_matriz = models.JSONField(default=dict, blank=True)
    hash_matriz = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxArtifactMatrix.choices,
        default=EstadoAnnualTaxArtifactMatrix.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual'],
                name='uniq_annual_tax_artifact_matrix_process',
            ),
        ]

    def __str__(self):
        return f'Matriz DDJJ/F22 {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_matriz = _normalize_hash(self.hash_matriz)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_matriz', self.resumen_matriz)
        if has_text(self.hash_matriz) and not _is_sha256(self.hash_matriz):
            errors['hash_matriz'] = 'hash_matriz debe ser SHA-256 hexadecimal de 64 caracteres.'
        if self.ddjj_items_total + self.f22_items_total != self.items_total:
            errors['items_total'] = 'items_total debe coincidir con la suma de DDJJ y F22.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa de la matriz.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'La matriz debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa de la matriz.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualTaxArtifactMatrix requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario de la matriz.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualTaxArtifactMatrix requiere TaxYearRuleSet aprobado.'

        if isinstance(self.resumen_matriz, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('items_total', self.items_total),
                ('ddjj_items_total', self.ddjj_items_total),
                ('f22_items_total', self.f22_items_total),
            ):
                value = self.resumen_matriz.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_matriz'] = (
                    'resumen_matriz debe coincidir con empresa, proceso, fuente, regla, anio y totales.'
                )
            expected_hash = _payload_hash(self.resumen_matriz)
            if self.hash_matriz and self.hash_matriz != expected_hash:
                errors['hash_matriz'] = 'hash_matriz debe corresponder al resumen_matriz.'
        elif self.resumen_matriz:
            errors['resumen_matriz'] = 'resumen_matriz debe ser un objeto JSON.'

        if self.estado == EstadoAnnualTaxArtifactMatrix.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxArtifactMatrix')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualTaxArtifactMatrix preparada requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxArtifactMatrix preparada requiere responsible_ref no sensible.'
            if not self.resumen_matriz:
                errors['resumen_matriz'] = 'AnnualTaxArtifactMatrix preparada requiere resumen_matriz.'
            if not has_text(self.hash_matriz):
                errors['hash_matriz'] = 'AnnualTaxArtifactMatrix preparada requiere hash_matriz.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxArtifactMatrixItem(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'target_code',
        'medio_sii',
        'source_model',
        'source_hash',
        'formula_ref',
        'evidencia_ref',
        'responsible_ref',
        'hash_item',
    )

    matrix = models.ForeignKey(
        AnnualTaxArtifactMatrix,
        on_delete=models.CASCADE,
        related_name='items',
    )
    target_kind = models.CharField(max_length=8, choices=TipoAnnualTaxArtifactTarget.choices)
    target_code = models.CharField(max_length=64)
    medio_sii = models.CharField(max_length=64)
    source_kind = models.CharField(max_length=32, choices=SourceKindAnnualTaxArtifact.choices)
    source_model = models.CharField(max_length=64)
    source_object_id = models.PositiveIntegerField()
    source_hash = models.CharField(max_length=64, blank=True)
    review_state = models.CharField(
        max_length=24,
        choices=EstadoAnnualTaxArtifactReview.choices,
        default=EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW,
    )
    formula_ref = models.CharField(max_length=255, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_item = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['matrix_id', 'target_kind', 'target_code', 'source_kind', 'source_model', 'source_object_id']
        constraints = [
            models.UniqueConstraint(
                fields=['matrix', 'target_kind', 'target_code', 'source_kind', 'source_model', 'source_object_id'],
                name='uniq_annual_tax_artifact_matrix_item_source',
            ),
        ]

    def __str__(self):
        return f'{self.matrix_id} {self.target_kind}:{self.target_code}'

    def clean(self):
        super().clean()
        self.source_hash = _normalize_hash(self.source_hash)
        self.hash_item = _normalize_hash(self.hash_item)
        errors = {}
        _add_non_sensitive_reference_error(errors, self, 'formula_ref')
        _add_non_sensitive_reference_error(errors, self, 'evidencia_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'warnings', self.warnings)
        _add_non_sensitive_payload_error(errors, 'source_payload', self.source_payload)
        if self.warnings and not isinstance(self.warnings, list):
            errors['warnings'] = 'warnings debe ser una lista JSON.'
        if self.source_payload and not isinstance(self.source_payload, dict):
            errors['source_payload'] = 'source_payload debe ser un objeto JSON.'
        if has_text(self.source_hash) and not _is_sha256(self.source_hash):
            errors['source_hash'] = 'source_hash debe ser SHA-256 hexadecimal de 64 caracteres.'
        if has_text(self.hash_item) and not _is_sha256(self.hash_item):
            errors['hash_item'] = 'hash_item debe ser SHA-256 hexadecimal de 64 caracteres.'

        try:
            matrix = self.matrix
        except ObjectDoesNotExist:
            matrix = None
        if matrix is not None and isinstance(self.source_payload, dict):
            for key, expected in (
                ('empresa_id', matrix.empresa_id),
                ('proceso_renta_anual_id', matrix.proceso_renta_anual_id),
                ('anio_tributario', matrix.anio_tributario),
                ('anio_comercial', matrix.anio_comercial),
            ):
                value = self.source_payload.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    errors['source_payload'] = 'source_payload debe coincidir con la matriz DDJJ/F22.'
                    break

        expected_hash = _payload_hash(_annual_tax_artifact_matrix_item_integrity_payload(self))
        if self.hash_item and self.hash_item != expected_hash:
            errors['hash_item'] = 'hash_item debe corresponder al item de matriz DDJJ/F22.'

        if self.estado == EstadoRegistro.ACTIVE:
            if not has_text(self.target_code):
                errors['target_code'] = 'Item activo requiere target_code.'
            if not has_text(self.medio_sii):
                errors['medio_sii'] = 'Item activo requiere medio_sii.'
            if not has_text(self.source_model):
                errors['source_model'] = 'Item activo requiere source_model.'
            if not self.source_object_id:
                errors['source_object_id'] = 'Item activo requiere source_object_id.'
            if not has_text(self.formula_ref):
                errors['formula_ref'] = 'Item activo requiere formula_ref no sensible.'
            if not has_text(self.evidencia_ref):
                errors['evidencia_ref'] = 'Item activo requiere evidencia_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'Item activo requiere responsible_ref no sensible.'
            if not self.source_payload:
                errors['source_payload'] = 'Item activo requiere source_payload trazable.'
            if not has_text(self.hash_item):
                errors['hash_item'] = 'Item activo requiere hash_item.'
            if self.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW and self.warnings:
                errors['review_state'] = 'Items con warnings no pueden quedar listo_revision.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxDossier(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'dossier_ref',
        'hash_dossier',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_dossiers',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='tax_dossiers',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='tax_dossiers',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='tax_dossiers',
    )
    artifact_matrix = models.ForeignKey(
        AnnualTaxArtifactMatrix,
        on_delete=models.PROTECT,
        related_name='tax_dossiers',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    dossier_ref = models.CharField(max_length=255, blank=True)
    review_state = models.CharField(
        max_length=24,
        choices=EstadoAnnualTaxArtifactReview.choices,
        default=EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW,
    )
    monthly_facts_total = models.PositiveIntegerField(default=0)
    workbooks_total = models.PositiveIntegerField(default=0)
    enterprise_registers_total = models.PositiveIntegerField(default=0)
    real_estate_sections_total = models.PositiveIntegerField(default=0)
    artifact_matrix_items_total = models.PositiveIntegerField(default=0)
    warnings_total = models.PositiveIntegerField(default=0)
    resumen_dossier = models.JSONField(default=dict, blank=True)
    hash_dossier = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxDossier.choices,
        default=EstadoAnnualTaxDossier.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual'],
                name='uniq_annual_tax_dossier_process',
            ),
        ]

    def __str__(self):
        return f'Dossier renta {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_dossier = _normalize_hash(self.hash_dossier)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_reference_error(errors, self, 'dossier_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_dossier', self.resumen_dossier)
        if has_text(self.hash_dossier) and not _is_sha256(self.hash_dossier):
            errors['hash_dossier'] = 'hash_dossier debe ser SHA-256 hexadecimal de 64 caracteres.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa del dossier.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'El dossier debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa del dossier.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualTaxDossier requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario del dossier.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualTaxDossier requiere TaxYearRuleSet aprobado.'

        try:
            artifact_matrix = self.artifact_matrix
        except ObjectDoesNotExist:
            artifact_matrix = None
        if artifact_matrix is not None:
            if artifact_matrix.empresa_id != self.empresa_id:
                errors['artifact_matrix'] = 'AnnualTaxArtifactMatrix debe pertenecer a la misma empresa del dossier.'
            elif artifact_matrix.proceso_renta_anual_id != self.proceso_renta_anual_id:
                errors['artifact_matrix'] = 'AnnualTaxArtifactMatrix debe corresponder al mismo proceso anual.'
            elif artifact_matrix.estado != EstadoAnnualTaxArtifactMatrix.PREPARED:
                errors['artifact_matrix'] = 'AnnualTaxDossier requiere AnnualTaxArtifactMatrix preparada.'

        if isinstance(self.resumen_dossier, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('artifact_matrix_id', self.artifact_matrix_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('monthly_facts_total', self.monthly_facts_total),
                ('workbooks_total', self.workbooks_total),
                ('enterprise_registers_total', self.enterprise_registers_total),
                ('real_estate_sections_total', self.real_estate_sections_total),
                ('artifact_matrix_items_total', self.artifact_matrix_items_total),
                ('warnings_total', self.warnings_total),
            ):
                value = self.resumen_dossier.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_dossier'] = (
                    'resumen_dossier debe coincidir con empresa, proceso, fuente, regla, matriz, anio y totales.'
                )
            if self.resumen_dossier.get('review_state') and self.resumen_dossier.get('review_state') != self.review_state:
                errors['resumen_dossier'] = 'resumen_dossier debe coincidir con review_state.'
            expected_hash = _payload_hash(self.resumen_dossier)
            if self.hash_dossier and self.hash_dossier != expected_hash:
                errors['hash_dossier'] = 'hash_dossier debe corresponder al resumen_dossier.'
        elif self.resumen_dossier:
            errors['resumen_dossier'] = 'resumen_dossier debe ser un objeto JSON.'

        if self.estado == EstadoAnnualTaxDossier.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxDossier')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualTaxDossier preparado requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxDossier preparado requiere responsible_ref no sensible.'
            if not has_text(self.dossier_ref):
                errors['dossier_ref'] = 'AnnualTaxDossier preparado requiere dossier_ref no sensible.'
            if self.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW and self.warnings_total:
                errors['review_state'] = 'Dossier con warnings no puede quedar listo_revision.'
            if not self.resumen_dossier:
                errors['resumen_dossier'] = 'AnnualTaxDossier preparado requiere resumen_dossier.'
            if not has_text(self.hash_dossier):
                errors['hash_dossier'] = 'AnnualTaxDossier preparado requiere hash_dossier.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxExport(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'export_ref',
        'hash_export',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_exports',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='tax_exports',
    )
    dossier = models.ForeignKey(
        AnnualTaxDossier,
        on_delete=models.PROTECT,
        related_name='tax_exports',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='tax_exports',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='tax_exports',
    )
    artifact_matrix = models.ForeignKey(
        AnnualTaxArtifactMatrix,
        on_delete=models.PROTECT,
        related_name='tax_exports',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    export_kind = models.CharField(
        max_length=32,
        choices=TipoAnnualTaxExport.choices,
        default=TipoAnnualTaxExport.PREVIEW_PACKAGE,
    )
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    export_ref = models.CharField(max_length=255, blank=True)
    review_state = models.CharField(
        max_length=24,
        choices=EstadoAnnualTaxArtifactReview.choices,
        default=EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW,
    )
    target_items_total = models.PositiveIntegerField(default=0)
    ddjj_items_total = models.PositiveIntegerField(default=0)
    f22_items_total = models.PositiveIntegerField(default=0)
    warnings_total = models.PositiveIntegerField(default=0)
    official_format = models.BooleanField(default=False)
    sii_submission = models.BooleanField(default=False)
    final_tax_calculation = models.BooleanField(default=False)
    export_payload = models.JSONField(default=dict, blank=True)
    hash_export = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxExport.choices,
        default=EstadoAnnualTaxExport.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'export_kind', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual', 'export_kind'],
                name='uniq_annual_tax_export_process_kind',
            ),
        ]

    def __str__(self):
        return f'Export renta {self.empresa_id} AT{self.anio_tributario} {self.export_kind}'

    def clean(self):
        super().clean()
        self.hash_export = _normalize_hash(self.hash_export)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_reference_error(errors, self, 'export_ref')
        _add_non_sensitive_payload_error(errors, 'export_payload', self.export_payload)
        if has_text(self.hash_export) and not _is_sha256(self.hash_export):
            errors['hash_export'] = 'hash_export debe ser SHA-256 hexadecimal de 64 caracteres.'
        if self.ddjj_items_total + self.f22_items_total != self.target_items_total:
            errors['target_items_total'] = 'target_items_total debe coincidir con la suma de DDJJ y F22.'
        if self.official_format:
            errors['official_format'] = 'AnnualTaxExport v1 no declara formato oficial SII.'
        if self.sii_submission:
            errors['sii_submission'] = 'AnnualTaxExport v1 no registra presentacion SII.'
        if self.final_tax_calculation:
            errors['final_tax_calculation'] = 'AnnualTaxExport v1 no declara calculo fiscal final.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa del export.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'El export debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa del export.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualTaxExport requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario del export.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualTaxExport requiere TaxYearRuleSet aprobado.'

        try:
            artifact_matrix = self.artifact_matrix
        except ObjectDoesNotExist:
            artifact_matrix = None
        if artifact_matrix is not None:
            if artifact_matrix.empresa_id != self.empresa_id:
                errors['artifact_matrix'] = 'AnnualTaxArtifactMatrix debe pertenecer a la misma empresa del export.'
            elif artifact_matrix.proceso_renta_anual_id != self.proceso_renta_anual_id:
                errors['artifact_matrix'] = 'AnnualTaxArtifactMatrix debe corresponder al mismo proceso anual.'
            elif artifact_matrix.estado != EstadoAnnualTaxArtifactMatrix.PREPARED:
                errors['artifact_matrix'] = 'AnnualTaxExport requiere AnnualTaxArtifactMatrix preparada.'

        try:
            dossier = self.dossier
        except ObjectDoesNotExist:
            dossier = None
        if dossier is not None:
            if dossier.empresa_id != self.empresa_id:
                errors['dossier'] = 'AnnualTaxDossier debe pertenecer a la misma empresa del export.'
            elif dossier.proceso_renta_anual_id != self.proceso_renta_anual_id:
                errors['dossier'] = 'AnnualTaxDossier debe corresponder al mismo proceso anual.'
            elif dossier.anio_tributario != self.anio_tributario:
                errors['dossier'] = 'AnnualTaxDossier debe corresponder al mismo anio_tributario.'
            elif dossier.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'AnnualTaxExport debe usar la misma fuente congelada del dossier.'
            elif dossier.rule_set_id != self.rule_set_id:
                errors['rule_set'] = 'AnnualTaxExport debe usar el mismo TaxYearRuleSet del dossier.'
            elif dossier.artifact_matrix_id != self.artifact_matrix_id:
                errors['artifact_matrix'] = 'AnnualTaxExport debe usar la misma matriz DDJJ/F22 del dossier.'
            elif dossier.estado != EstadoAnnualTaxDossier.PREPARED:
                errors['dossier'] = 'AnnualTaxExport requiere AnnualTaxDossier preparado.'
            elif dossier.review_state == EstadoAnnualTaxArtifactReview.BLOCKED:
                errors['dossier'] = 'AnnualTaxExport no puede generarse desde un dossier bloqueado.'

        if isinstance(self.export_payload, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('dossier_id', self.dossier_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('artifact_matrix_id', self.artifact_matrix_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('target_items_total', self.target_items_total),
                ('ddjj_items_total', self.ddjj_items_total),
                ('f22_items_total', self.f22_items_total),
                ('warnings_total', self.warnings_total),
            ):
                value = self.export_payload.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['export_payload'] = (
                    'export_payload debe coincidir con empresa, proceso, fuente, regla, matriz, dossier, anio y totales.'
                )
            for key, expected in (
                ('export_kind', self.export_kind),
                ('review_state', self.review_state),
                ('official_format', self.official_format),
                ('sii_submission', self.sii_submission),
                ('final_tax_calculation', self.final_tax_calculation),
            ):
                if key in self.export_payload and self.export_payload.get(key) != expected:
                    errors['export_payload'] = 'export_payload debe coincidir con estado, tipo y flags de gate.'
            if self.export_payload.get('sii_submission_attempted'):
                errors['export_payload'] = 'AnnualTaxExport v1 no registra intentos de presentacion SII.'
            expected_hash = _payload_hash(self.export_payload)
            if self.hash_export and self.hash_export != expected_hash:
                errors['hash_export'] = 'hash_export debe corresponder al export_payload.'
        elif self.export_payload:
            errors['export_payload'] = 'export_payload debe ser un objeto JSON.'

        if self.estado == EstadoAnnualTaxExport.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxExport')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualTaxExport preparado requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxExport preparado requiere responsible_ref no sensible.'
            if not has_text(self.export_ref):
                errors['export_ref'] = 'AnnualTaxExport preparado requiere export_ref no sensible.'
            if self.review_state == EstadoAnnualTaxArtifactReview.BLOCKED:
                errors['review_state'] = 'AnnualTaxExport preparado no puede quedar bloqueado.'
            if not self.export_payload:
                errors['export_payload'] = 'AnnualTaxExport preparado requiere export_payload.'
            if not has_text(self.hash_export):
                errors['hash_export'] = 'AnnualTaxExport preparado requiere hash_export.'
            if self.target_items_total <= 0:
                errors['target_items_total'] = 'AnnualTaxExport preparado requiere items DDJJ/F22 trazables.'
        if errors:
            raise ValidationError(errors)


class ProcesoRentaAnual(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('paquete_ddjj_ref', 'borrador_f22_ref', 'responsable_revision_ref')

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
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='procesos_renta_anual',
        null=True,
        blank=True,
    )
    fecha_preparacion = models.DateTimeField(null=True, blank=True)
    resumen_anual = models.JSONField(default=dict, blank=True)
    paquete_ddjj_ref = models.CharField(max_length=255, blank=True)
    borrador_f22_ref = models.CharField(max_length=255, blank=True)
    responsable_revision_ref = models.CharField(max_length=255, blank=True, default='')

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
        _add_required_review_responsible_error(errors, self, 'estado')
        _add_non_sensitive_reference_error(errors, self, 'paquete_ddjj_ref')
        _add_non_sensitive_reference_error(errors, self, 'borrador_f22_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsable_revision_ref')
        _add_active_fiscal_config_error(errors, self, 'ProcesoRentaAnual')
        _add_non_sensitive_payload_error(errors, 'resumen_anual', self.resumen_anual)
        _add_annual_summary_year_error(errors, 'resumen_anual', self.resumen_anual, self.anio_tributario)
        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'source_bundle debe pertenecer a la misma empresa del ProcesoRentaAnual.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'source_bundle debe corresponder al mismo anio_tributario del ProcesoRentaAnual.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'ProcesoRentaAnual requiere AnnualTaxSourceBundle congelado.'
        if errors:
            raise ValidationError(errors)


class DDJJPreparacionAnual(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('paquete_ref', 'responsable_revision_ref', 'observaciones')

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
    responsable_revision_ref = models.CharField(max_length=255, blank=True, default='')
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
        _add_required_review_responsible_error(errors, self, 'estado_preparacion')
        _add_non_sensitive_reference_error(errors, self, 'paquete_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsable_revision_ref')
        _add_non_sensitive_text_error(errors, 'observaciones', self.observaciones)
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


class F22PreparacionAnual(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = ('borrador_ref', 'responsable_revision_ref', 'observaciones')

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
    responsable_revision_ref = models.CharField(max_length=255, blank=True, default='')
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
        _add_required_review_responsible_error(errors, self, 'estado_preparacion')
        _add_non_sensitive_reference_error(errors, self, 'borrador_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsable_revision_ref')
        _add_non_sensitive_text_error(errors, 'observaciones', self.observaciones)
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
