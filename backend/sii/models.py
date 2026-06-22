import hashlib
import json
from urllib.parse import urlparse

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from cobranza.models import DistribucionCobroMensual, PagoMensual
from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    CuentaContable,
    EstadoCierreMensual,
    EstadoLiquidacionMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    LiquidacionMensual,
    RegimenTributarioEmpresa,
)
from contratos.models import Contrato
from core.reference_validation import (
    contains_sensitive_control_reference,
    contains_sensitive_reference,
    is_non_sensitive_control_reference,
)
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
    if has_text(value) and not is_non_sensitive_control_reference(value):
        errors[field_name] = (
            f'{field_name} debe ser una referencia no sensible, sin URL, token, credencial, RUT ni ruta local.'
        )


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
    if value and contains_sensitive_control_reference(value, include_sensitive_keys=True):
        _add_error(
            errors,
            field_name,
            f'{field_name} no debe contener URLs, tokens, credenciales, correos, RUT, rutas locales ni claves sensibles.',
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
    SII_REAL_ESTATE_CONTRIBUTIONS = 'sii_real_estate_contributions', 'SII contribuciones bienes raices'
    SII_F29_CERTIFICATION = 'sii_f29_certification', 'SII certificacion F29'
    SII_DTE_TECHNICAL = 'sii_dte_technical', 'SII tecnico DTE'
    EXPERT_REVIEW = 'expert_review', 'Revision experta'


class EstadoAnnualTaxOfficialSource(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    REVIEWED = 'revisada', 'Revisada'
    APPROVED = 'aprobada', 'Aprobada'
    RETIRED = 'retirada', 'Retirada'


ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES = {
    EstadoAnnualTaxOfficialSource.REVIEWED,
    EstadoAnnualTaxOfficialSource.APPROVED,
}


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


class EstadoAnnualTaxTrialBalance(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualTaxDDJJLayout(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualTaxF22ExportLayout(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class MedioAnnualTaxDDJJ(models.TextChoices):
    ELECTRONIC_FORM = 'formulario_electronico', 'Formulario electronico'
    FILE_IMPORTER = 'transferencia_archivos_importador', 'Transferencia importador'
    FILE_UPLOAD = 'transferencia_archivos_upload', 'Transferencia upload'
    COMMERCIAL_SOFTWARE = 'software_comercial', 'Software comercial'
    ASSISTANT = 'asistente', 'Asistente'


class MedioAnnualTaxF22Export(models.TextChoices):
    LOCAL_PREVIEW = 'preview_local_controlado', 'Preview local controlado'
    CERTIFIED_FILE = 'archivo_certificado_sii', 'Archivo certificado SII'
    SUPERVISED_PORTAL = 'portal_sii_supervisado', 'Portal SII supervisado'


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


class EstadoAnnualTaxReviewChecklist(models.TextChoices):
    DRAFT = 'borrador', 'Borrador'
    PREPARED = 'preparado', 'Preparado'
    RETIRED = 'retirado', 'Retirado'


class EstadoAnnualTaxReviewDecision(models.TextChoices):
    PREPARED = 'preparado', 'Preparado'
    OBSERVED = 'observado', 'Observado'
    APPROVED_FOR_PRESENTATION = 'aprobado_para_presentacion', 'Aprobado para presentacion'


class TipoAnnualTaxExport(models.TextChoices):
    PREVIEW_PACKAGE = 'preview_package', 'Preview package'


class TipoAnnualTaxArtifactTarget(models.TextChoices):
    DDJJ = 'DDJJ', 'DDJJ'
    F22 = 'F22', 'F22'


class SourceKindAnnualTaxArtifact(models.TextChoices):
    SOURCE_BUNDLE = 'source_bundle', 'Source bundle'
    TAX_MAPPING = 'tax_mapping', 'Tax code mapping'
    DDJJ_LAYOUT = 'ddjj_layout', 'DDJJ layout'
    F22_EXPORT_LAYOUT = 'f22_export_layout', 'F22 export layout'
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
    'alerce.sii.cl',
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


def _add_official_source_link_errors(
    errors,
    obj,
    field_name,
    *,
    anio_tributario,
    applies_to='',
    regime_code='',
):
    try:
        source = getattr(obj, field_name)
    except ObjectDoesNotExist:
        source = None
    if source is None:
        errors[field_name] = 'Requiere AnnualTaxOfficialSource revisada/aprobada.'
        return
    try:
        source.full_clean()
    except ValidationError:
        errors[field_name] = 'AnnualTaxOfficialSource vinculada no pasa validacion de dominio.'
        return
    if source.anio_tributario != anio_tributario:
        errors[field_name] = 'AnnualTaxOfficialSource debe corresponder al mismo ano tributario.'
        return
    if source.estado not in ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES:
        errors[field_name] = 'AnnualTaxOfficialSource debe estar revisada o aprobada.'
        return
    if has_text(applies_to) and has_text(source.applies_to) and source.applies_to != applies_to:
        errors[field_name] = 'AnnualTaxOfficialSource no corresponde al destino tributario del mapeo.'
        return
    if has_text(regime_code) and has_text(source.regime_code) and source.regime_code != regime_code:
        errors[field_name] = 'AnnualTaxOfficialSource no corresponde al regimen tributario.'


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
        'warning_review_ref': line.warning_review_ref,
        'warnings': line.warnings,
        'source_payload': line.source_payload,
    }


def _trial_balance_line_integrity_payload(line):
    return {
        'trial_balance_id': line.trial_balance_id,
        'cuenta_contable_id': line.cuenta_contable_id,
        'codigo_cuenta': line.codigo_cuenta,
        'nombre_cuenta': line.nombre_cuenta,
        'clasificador_dj1847': line.clasificador_dj1847,
        'sumas_debe_clp': str(line.sumas_debe_clp),
        'sumas_haber_clp': str(line.sumas_haber_clp),
        'saldo_deudor_clp': str(line.saldo_deudor_clp),
        'saldo_acreedor_clp': str(line.saldo_acreedor_clp),
        'inventario_activo_clp': str(line.inventario_activo_clp),
        'inventario_pasivo_clp': str(line.inventario_pasivo_clp),
        'resultado_perdida_clp': str(line.resultado_perdida_clp),
        'resultado_ganancia_clp': str(line.resultado_ganancia_clp),
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
        'warning_review_ref': movement.warning_review_ref,
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
        'official_contribution_source_id': item.section.official_contribution_source_id if item.section_id else None,
        'formula_ref': item.formula_ref,
        'evidencia_ref': item.evidencia_ref,
        'warnings': item.warnings,
        'source_payload': item.source_payload,
    }


def _annual_tax_ddjj_layout_integrity_payload(layout):
    return {
        'anio_tributario': layout.anio_tributario,
        'form_code': layout.form_code,
        'title': layout.title,
        'periodicidad': layout.periodicidad,
        'allows_electronic_form': layout.allows_electronic_form,
        'allows_file_importer': layout.allows_file_importer,
        'allows_file_upload': layout.allows_file_upload,
        'allows_commercial_software': layout.allows_commercial_software,
        'allows_assistant': layout.allows_assistant,
        'medio_preferente': layout.medio_preferente,
        'due_date_label': layout.due_date_label,
        'certificate_code': layout.certificate_code,
        'certificate_due_label': layout.certificate_due_label,
        'resolution_ref': layout.resolution_ref,
        'declaration_status': layout.declaration_status,
        'layout_ref': layout.layout_ref,
        'instructions_ref': layout.instructions_ref,
        'responsible_ref': layout.responsible_ref,
        'official_media_source_id': layout.official_media_source_id,
        'official_form_source_id': layout.official_form_source_id,
        'official_software_source_id': layout.official_software_source_id,
        'warnings': layout.warnings,
        'source_payload': layout.source_payload,
    }


def _annual_tax_f22_export_layout_integrity_payload(layout):
    return {
        'anio_tributario': layout.anio_tributario,
        'form_code': layout.form_code,
        'title': layout.title,
        'allows_local_preview': layout.allows_local_preview,
        'allows_certified_file': layout.allows_certified_file,
        'allows_supervised_portal': layout.allows_supervised_portal,
        'medio_preferente': layout.medio_preferente,
        'certification_ref': layout.certification_ref,
        'format_ref': layout.format_ref,
        'instructions_ref': layout.instructions_ref,
        'responsible_ref': layout.responsible_ref,
        'official_certification_source_id': layout.official_certification_source_id,
        'official_instructions_source_id': layout.official_instructions_source_id,
        'warnings': layout.warnings,
        'source_payload': layout.source_payload,
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
        'warning_review_ref': item.warning_review_ref,
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
    official_source = models.ForeignKey(
        'AnnualTaxOfficialSource',
        on_delete=models.PROTECT,
        related_name='rule_sets',
        null=True,
        blank=True,
    )
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
            _add_official_source_link_errors(
                errors,
                self,
                'official_source',
                anio_tributario=self.anio_tributario,
                regime_code=getattr(regimen_tributario, 'codigo_regimen', ''),
            )
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
    official_source = models.ForeignKey(
        'AnnualTaxOfficialSource',
        on_delete=models.PROTECT,
        related_name='code_mappings',
        null=True,
        blank=True,
    )
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
            regime_code = ''
            try:
                regime_code = rule_set.regimen_tributario.codigo_regimen
            except ObjectDoesNotExist:
                regime_code = ''
            _add_official_source_link_errors(
                errors,
                self,
                'official_source',
                anio_tributario=rule_set.anio_tributario,
                applies_to=self.destino,
                regime_code=regime_code,
            )
            metadata = self.metadata if isinstance(self.metadata, dict) else {}
            source_metric = str(metadata.get('source_metric') or '').strip()
            if source_metric.startswith('annual_trial_balance.'):
                if self.destino not in {DestinoMapeoTributarioAnual.RLI, DestinoMapeoTributarioAnual.CPT}:
                    _add_error(
                        errors,
                        'metadata',
                        'Metricas annual_trial_balance solo pueden alimentar mappings RLI/CPT.',
                    )
                if not has_text(metadata.get('trial_balance_classifier')):
                    _add_error(
                        errors,
                        'metadata',
                        'Metricas annual_trial_balance requieren trial_balance_classifier DJ1847 trazable.',
                    )
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
            elif self.retrieved_on > timezone.localdate():
                errors['retrieved_on'] = 'Fuente revisada no puede tener retrieved_on futuro.'
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


class AnnualTaxDDJJFormLayout(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'form_code',
        'title',
        'periodicidad',
        'medio_preferente',
        'due_date_label',
        'certificate_code',
        'certificate_due_label',
        'resolution_ref',
        'declaration_status',
        'layout_ref',
        'instructions_ref',
        'responsible_ref',
        'hash_layout',
    )

    anio_tributario = models.PositiveSmallIntegerField()
    form_code = models.CharField(max_length=32)
    title = models.CharField(max_length=180)
    periodicidad = models.CharField(max_length=32, default='Anual')
    allows_electronic_form = models.BooleanField(default=False)
    allows_file_importer = models.BooleanField(default=False)
    allows_file_upload = models.BooleanField(default=False)
    allows_commercial_software = models.BooleanField(default=False)
    allows_assistant = models.BooleanField(default=False)
    medio_preferente = models.CharField(max_length=64, choices=MedioAnnualTaxDDJJ.choices)
    due_date_label = models.CharField(max_length=64, blank=True)
    certificate_code = models.CharField(max_length=64, blank=True)
    certificate_due_label = models.CharField(max_length=64, blank=True)
    resolution_ref = models.CharField(max_length=255, blank=True)
    declaration_status = models.CharField(max_length=64, blank=True)
    layout_ref = models.CharField(max_length=255, blank=True)
    instructions_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    official_media_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='ddjj_media_layouts',
        null=True,
        blank=True,
    )
    official_form_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='ddjj_form_layouts',
        null=True,
        blank=True,
    )
    official_software_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='ddjj_software_layouts',
        null=True,
        blank=True,
    )
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_layout = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxDDJJLayout.choices,
        default=EstadoAnnualTaxDDJJLayout.DRAFT,
    )

    class Meta:
        ordering = ['-anio_tributario', 'form_code']
        constraints = [
            models.UniqueConstraint(
                fields=['anio_tributario', 'form_code'],
                name='uniq_annual_tax_ddjj_layout_form',
            ),
        ]

    def __str__(self):
        return f'DDJJ {self.form_code} AT{self.anio_tributario}'

    def compute_hash_layout(self):
        return _payload_hash(_annual_tax_ddjj_layout_integrity_payload(self))

    def _allowed_media(self):
        media = set()
        if self.allows_electronic_form:
            media.add(MedioAnnualTaxDDJJ.ELECTRONIC_FORM)
        if self.allows_file_importer:
            media.add(MedioAnnualTaxDDJJ.FILE_IMPORTER)
        if self.allows_file_upload:
            media.add(MedioAnnualTaxDDJJ.FILE_UPLOAD)
        if self.allows_commercial_software:
            media.add(MedioAnnualTaxDDJJ.COMMERCIAL_SOFTWARE)
        if self.allows_assistant:
            media.add(MedioAnnualTaxDDJJ.ASSISTANT)
        return media

    def _add_source_type_error(self, errors, field_name, allowed_types):
        try:
            source = getattr(self, field_name)
        except ObjectDoesNotExist:
            source = None
        if source is None:
            return
        if source.source_type not in allowed_types:
            errors[field_name] = 'AnnualTaxOfficialSource no corresponde al tipo de fuente requerido.'
            return
        if has_text(source.form_code) and source.form_code != self.form_code:
            errors[field_name] = 'AnnualTaxOfficialSource no corresponde al formulario DDJJ del layout.'

    def clean(self):
        super().clean()
        self.hash_layout = _normalize_hash(self.hash_layout)
        errors = {}
        if self.anio_tributario < 2000:
            errors['anio_tributario'] = 'anio_tributario debe ser un ano tributario valido.'
        if not has_text(self.form_code):
            errors['form_code'] = 'AnnualTaxDDJJFormLayout requiere form_code.'
        elif not str(self.form_code).isdigit():
            errors['form_code'] = 'form_code debe ser numerico para formularios DDJJ SII.'
        _add_non_sensitive_reference_error(errors, self, 'resolution_ref')
        _add_non_sensitive_reference_error(errors, self, 'layout_ref')
        _add_non_sensitive_reference_error(errors, self, 'instructions_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'warnings', self.warnings)
        _add_non_sensitive_payload_error(errors, 'source_payload', self.source_payload)
        if self.warnings and not isinstance(self.warnings, list):
            errors['warnings'] = 'warnings debe ser una lista JSON.'
        if self.source_payload and not isinstance(self.source_payload, dict):
            errors['source_payload'] = 'source_payload debe ser un objeto JSON.'

        allowed_media = self._allowed_media()
        if self.medio_preferente and self.medio_preferente not in allowed_media:
            errors['medio_preferente'] = 'medio_preferente debe estar permitido para el formulario DDJJ.'

        if has_text(self.hash_layout) and not _is_sha256(self.hash_layout):
            errors['hash_layout'] = 'hash_layout debe ser SHA-256 hexadecimal de 64 caracteres.'
        expected_hash = self.compute_hash_layout()
        if self.hash_layout and self.hash_layout != expected_hash:
            errors['hash_layout'] = 'hash_layout debe corresponder al layout DDJJ normalizado.'

        if self.estado == EstadoAnnualTaxDDJJLayout.PREPARED:
            if not allowed_media:
                errors['medio_preferente'] = 'Layout DDJJ preparado requiere al menos un medio SII habilitado.'
            for field_name in (
                'title',
                'periodicidad',
                'medio_preferente',
                'due_date_label',
                'layout_ref',
                'instructions_ref',
                'responsible_ref',
            ):
                if not has_text(getattr(self, field_name)):
                    errors[field_name] = f'Layout DDJJ preparado requiere {field_name}.'
            if not self.source_payload:
                errors['source_payload'] = 'Layout DDJJ preparado requiere source_payload trazable.'
            if not has_text(self.hash_layout):
                errors['hash_layout'] = 'Layout DDJJ preparado requiere hash_layout.'

            _add_official_source_link_errors(
                errors,
                self,
                'official_media_source',
                anio_tributario=self.anio_tributario,
                applies_to=DestinoMapeoTributarioAnual.DDJJ,
            )
            _add_official_source_link_errors(
                errors,
                self,
                'official_form_source',
                anio_tributario=self.anio_tributario,
                applies_to=DestinoMapeoTributarioAnual.DDJJ,
            )
            if self.official_software_source_id:
                _add_official_source_link_errors(
                    errors,
                    self,
                    'official_software_source',
                    anio_tributario=self.anio_tributario,
                    applies_to=DestinoMapeoTributarioAnual.DDJJ,
                )
            self._add_source_type_error(
                errors,
                'official_media_source',
                {TipoAnnualTaxOfficialSource.SII_DDJJ_MEDIA, TipoAnnualTaxOfficialSource.EXPERT_REVIEW},
            )
            self._add_source_type_error(
                errors,
                'official_form_source',
                {TipoAnnualTaxOfficialSource.SII_DDJJ_FORMS, TipoAnnualTaxOfficialSource.EXPERT_REVIEW},
            )
            self._add_source_type_error(
                errors,
                'official_software_source',
                {TipoAnnualTaxOfficialSource.SII_DDJJ_SOFTWARE_HOUSES, TipoAnnualTaxOfficialSource.EXPERT_REVIEW},
            )
        if errors:
            raise ValidationError(errors)


class AnnualTaxF22ExportLayout(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'form_code',
        'title',
        'medio_preferente',
        'certification_ref',
        'format_ref',
        'instructions_ref',
        'responsible_ref',
        'hash_layout',
    )

    anio_tributario = models.PositiveSmallIntegerField()
    form_code = models.CharField(max_length=16, default='F22')
    title = models.CharField(max_length=180)
    allows_local_preview = models.BooleanField(default=True)
    allows_certified_file = models.BooleanField(default=False)
    allows_supervised_portal = models.BooleanField(default=False)
    medio_preferente = models.CharField(max_length=64, choices=MedioAnnualTaxF22Export.choices)
    certification_ref = models.CharField(max_length=255, blank=True)
    format_ref = models.CharField(max_length=255, blank=True)
    instructions_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    official_certification_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='f22_export_certification_layouts',
        null=True,
        blank=True,
    )
    official_instructions_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='f22_export_instruction_layouts',
        null=True,
        blank=True,
    )
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_layout = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxF22ExportLayout.choices,
        default=EstadoAnnualTaxF22ExportLayout.DRAFT,
    )

    class Meta:
        ordering = ['-anio_tributario', 'form_code']
        constraints = [
            models.UniqueConstraint(
                fields=['anio_tributario', 'form_code'],
                name='uniq_annual_tax_f22_export_layout_form',
            ),
        ]

    def __str__(self):
        return f'F22 layout AT{self.anio_tributario}'

    def compute_hash_layout(self):
        return _payload_hash(_annual_tax_f22_export_layout_integrity_payload(self))

    def _allowed_media(self):
        media = set()
        if self.allows_local_preview:
            media.add(MedioAnnualTaxF22Export.LOCAL_PREVIEW)
        if self.allows_certified_file:
            media.add(MedioAnnualTaxF22Export.CERTIFIED_FILE)
        if self.allows_supervised_portal:
            media.add(MedioAnnualTaxF22Export.SUPERVISED_PORTAL)
        return media

    def _add_source_type_error(self, errors, field_name, allowed_types):
        try:
            source = getattr(self, field_name)
        except ObjectDoesNotExist:
            source = None
        if source is None:
            return
        if source.source_type not in allowed_types:
            errors[field_name] = 'AnnualTaxOfficialSource no corresponde al tipo de fuente requerido.'
            return
        if has_text(source.form_code) and source.form_code != self.form_code:
            errors[field_name] = 'AnnualTaxOfficialSource no corresponde al formulario F22 del layout.'

    def clean(self):
        super().clean()
        self.form_code = str(self.form_code or '').strip().upper()
        self.hash_layout = _normalize_hash(self.hash_layout)
        errors = {}
        if self.anio_tributario < 2000:
            errors['anio_tributario'] = 'anio_tributario debe ser un ano tributario valido.'
        if self.form_code != 'F22':
            errors['form_code'] = 'AnnualTaxF22ExportLayout solo admite form_code F22.'
        _add_non_sensitive_reference_error(errors, self, 'certification_ref')
        _add_non_sensitive_reference_error(errors, self, 'format_ref')
        _add_non_sensitive_reference_error(errors, self, 'instructions_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'warnings', self.warnings)
        _add_non_sensitive_payload_error(errors, 'source_payload', self.source_payload)
        if self.warnings and not isinstance(self.warnings, list):
            errors['warnings'] = 'warnings debe ser una lista JSON.'
        if self.source_payload and not isinstance(self.source_payload, dict):
            errors['source_payload'] = 'source_payload debe ser un objeto JSON.'
        elif isinstance(self.source_payload, dict):
            for key in (
                'official_format',
                'sii_submission',
                'sii_submission_attempted',
                'final_tax_calculation',
            ):
                if bool(self.source_payload.get(key)):
                    errors['source_payload'] = 'AnnualTaxF22ExportLayout v1 no habilita formato oficial, envio SII ni calculo fiscal final.'
                    break

        allowed_media = self._allowed_media()
        if self.medio_preferente and self.medio_preferente not in allowed_media:
            errors['medio_preferente'] = 'medio_preferente debe estar permitido para F22.'

        if has_text(self.hash_layout) and not _is_sha256(self.hash_layout):
            errors['hash_layout'] = 'hash_layout debe ser SHA-256 hexadecimal de 64 caracteres.'
        expected_hash = self.compute_hash_layout()
        if self.hash_layout and self.hash_layout != expected_hash:
            errors['hash_layout'] = 'hash_layout debe corresponder al layout F22 normalizado.'

        if self.estado == EstadoAnnualTaxF22ExportLayout.PREPARED:
            if not allowed_media:
                errors['medio_preferente'] = 'Layout F22 preparado requiere al menos un medio habilitado.'
            for field_name in (
                'title',
                'medio_preferente',
                'certification_ref',
                'format_ref',
                'instructions_ref',
                'responsible_ref',
            ):
                if not has_text(getattr(self, field_name)):
                    errors[field_name] = f'Layout F22 preparado requiere {field_name}.'
            if not self.source_payload:
                errors['source_payload'] = 'Layout F22 preparado requiere source_payload trazable.'
            if not has_text(self.hash_layout):
                errors['hash_layout'] = 'Layout F22 preparado requiere hash_layout.'
            _add_official_source_link_errors(
                errors,
                self,
                'official_certification_source',
                anio_tributario=self.anio_tributario,
                applies_to=DestinoMapeoTributarioAnual.F22,
            )
            _add_official_source_link_errors(
                errors,
                self,
                'official_instructions_source',
                anio_tributario=self.anio_tributario,
                applies_to=DestinoMapeoTributarioAnual.F22,
            )
            self._add_source_type_error(
                errors,
                'official_certification_source',
                {TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION, TipoAnnualTaxOfficialSource.EXPERT_REVIEW},
            )
            self._add_source_type_error(
                errors,
                'official_instructions_source',
                {TipoAnnualTaxOfficialSource.SII_F22_INSTRUCTIONS, TipoAnnualTaxOfficialSource.EXPERT_REVIEW},
            )
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
            monthly_tax_fact_months = summary.get('monthly_tax_fact_months') or []
            try:
                normalized_monthly_tax_fact_months = sorted({int(month) for month in monthly_tax_fact_months})
            except (TypeError, ValueError):
                normalized_monthly_tax_fact_months = []
            if (
                normalized_obligation_months != list(range(1, 13))
                and normalized_monthly_tax_fact_months != list(range(1, 13))
            ):
                _add_error(
                    errors,
                    'resumen_fuentes',
                    'AnnualTaxSourceBundle congelado requiere obligaciones o hechos tributarios mensuales trazables para los doce meses.',
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


class AnnualTaxTrialBalance(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'source_ref',
        'responsible_ref',
        'hash_balance',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_trial_balances',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='trial_balances',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='trial_balances',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='trial_balances',
    )
    official_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='trial_balances',
    )
    source_balance = models.ForeignKey(
        BalanceComprobacion,
        on_delete=models.PROTECT,
        related_name='annual_tax_trial_balances',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    periodo_cierre = models.CharField(max_length=7)
    source_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    lines_total = models.PositiveIntegerField(default=0)
    warnings_total = models.PositiveIntegerField(default=0)
    resumen_balance = models.JSONField(default=dict, blank=True)
    hash_balance = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxTrialBalance.choices,
        default=EstadoAnnualTaxTrialBalance.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'periodo_cierre']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual'],
                name='uniq_annual_tax_trial_balance_process',
            ),
        ]

    def __str__(self):
        return f'Balance tributario {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_balance = _normalize_hash(self.hash_balance)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        expected_period = f'{self.anio_comercial}-12'
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        if self.periodo_cierre != expected_period:
            errors['periodo_cierre'] = f'periodo_cierre debe ser {expected_period}.'
        _add_non_sensitive_reference_error(errors, self, 'source_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_payload_error(errors, 'resumen_balance', self.resumen_balance)
        if has_text(self.hash_balance) and not _is_sha256(self.hash_balance):
            errors['hash_balance'] = 'hash_balance debe ser SHA-256 hexadecimal de 64 caracteres.'

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa del balance tributario.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'El balance tributario debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            source_bundle = self.source_bundle
        except ObjectDoesNotExist:
            source_bundle = None
        if source_bundle is not None:
            if source_bundle.empresa_id != self.empresa_id:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe pertenecer a la misma empresa del balance tributario.'
            elif source_bundle.anio_tributario != self.anio_tributario:
                errors['source_bundle'] = 'AnnualTaxSourceBundle debe corresponder al mismo anio_tributario.'
            elif source_bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                errors['source_bundle'] = 'AnnualTaxTrialBalance requiere AnnualTaxSourceBundle congelado.'

        try:
            rule_set = self.rule_set
        except ObjectDoesNotExist:
            rule_set = None
        if rule_set is not None:
            if rule_set.anio_tributario != self.anio_tributario:
                errors['rule_set'] = 'TaxYearRuleSet debe corresponder al mismo anio_tributario del balance tributario.'
            elif rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
                errors['rule_set'] = 'AnnualTaxTrialBalance requiere TaxYearRuleSet aprobado.'

        _add_official_source_link_errors(
            errors,
            self,
            'official_source',
            anio_tributario=self.anio_tributario,
        )
        if self.official_source_id:
            allowed_source_types = {
                TipoAnnualTaxOfficialSource.SII_DJ1847_INSTRUCTIONS,
                TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            }
            if self.official_source.source_type not in allowed_source_types:
                errors['official_source'] = 'El balance tributario anual requiere fuente DJ1847 SII o revision experta.'

        try:
            source_balance = self.source_balance
        except ObjectDoesNotExist:
            source_balance = None
        if source_balance is not None:
            if source_balance.empresa_id != self.empresa_id:
                errors['source_balance'] = 'BalanceComprobacion debe pertenecer a la misma empresa.'
            elif source_balance.periodo != self.periodo_cierre:
                errors['source_balance'] = 'BalanceComprobacion debe corresponder al periodo de cierre anual.'
            elif source_balance.estado_snapshot != EstadoCierreMensual.APPROVED:
                errors['source_balance'] = 'BalanceComprobacion anual requiere snapshot aprobado.'

        if isinstance(self.resumen_balance, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('official_source_id', self.official_source_id),
                ('source_balance_id', self.source_balance_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('periodo_cierre', self.periodo_cierre),
            ):
                value = self.resumen_balance.get(key)
                if value is None:
                    continue
                if key == 'periodo_cierre':
                    matches = str(value) == str(expected)
                else:
                    try:
                        matches = int(value) == int(expected)
                    except (TypeError, ValueError):
                        matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['resumen_balance'] = 'resumen_balance debe coincidir con empresa, proceso, fuente, regla y periodo.'
            expected_hash = _payload_hash(self.resumen_balance)
            if self.hash_balance and self.hash_balance != expected_hash:
                errors['hash_balance'] = 'hash_balance debe corresponder al resumen_balance.'
        elif self.resumen_balance:
            errors['resumen_balance'] = 'resumen_balance debe ser un objeto JSON.'

        if self.estado == EstadoAnnualTaxTrialBalance.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxTrialBalance')
            if not has_text(self.source_ref):
                errors['source_ref'] = 'AnnualTaxTrialBalance preparado requiere source_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxTrialBalance preparado requiere responsible_ref no sensible.'
            if not self.lines_total:
                errors['lines_total'] = 'AnnualTaxTrialBalance preparado requiere lineas de balance.'
            if not self.resumen_balance:
                errors['resumen_balance'] = 'AnnualTaxTrialBalance preparado requiere resumen_balance.'
            if not has_text(self.hash_balance):
                errors['hash_balance'] = 'AnnualTaxTrialBalance preparado requiere hash_balance.'
        if errors:
            raise ValidationError(errors)


class AnnualTaxTrialBalanceLine(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'codigo_cuenta',
        'nombre_cuenta',
        'clasificador_dj1847',
        'formula_ref',
        'evidencia_ref',
        'hash_linea',
    )

    trial_balance = models.ForeignKey(
        AnnualTaxTrialBalance,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    cuenta_contable = models.ForeignKey(
        CuentaContable,
        on_delete=models.PROTECT,
        related_name='annual_tax_trial_balance_lines',
    )
    codigo_cuenta = models.CharField(max_length=64)
    nombre_cuenta = models.CharField(max_length=255)
    clasificador_dj1847 = models.CharField(max_length=64)
    sumas_debe_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    sumas_haber_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    saldo_deudor_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    saldo_acreedor_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    inventario_activo_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    inventario_pasivo_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    resultado_perdida_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    resultado_ganancia_clp = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    formula_ref = models.CharField(max_length=255, blank=True)
    evidencia_ref = models.CharField(max_length=255, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    source_payload = models.JSONField(default=dict, blank=True)
    hash_linea = models.CharField(max_length=64, blank=True)
    estado = models.CharField(max_length=16, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVE)

    class Meta:
        ordering = ['trial_balance_id', 'codigo_cuenta']
        constraints = [
            models.UniqueConstraint(
                fields=['trial_balance', 'codigo_cuenta'],
                name='uniq_annual_tax_trial_balance_line_account',
            ),
        ]

    def __str__(self):
        return f'{self.trial_balance_id} {self.codigo_cuenta}'

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
            trial_balance = self.trial_balance
        except ObjectDoesNotExist:
            trial_balance = None
        try:
            cuenta = self.cuenta_contable
        except ObjectDoesNotExist:
            cuenta = None
        if trial_balance is not None and cuenta is not None:
            if cuenta.empresa_id != trial_balance.empresa_id:
                errors['cuenta_contable'] = 'La cuenta contable debe pertenecer a la misma empresa del balance tributario.'
            if self.codigo_cuenta != cuenta.codigo:
                errors['codigo_cuenta'] = 'codigo_cuenta debe coincidir con CuentaContable.codigo.'
            if self.nombre_cuenta != cuenta.nombre:
                errors['nombre_cuenta'] = 'nombre_cuenta debe coincidir con CuentaContable.nombre.'

        non_negative_fields = (
            'sumas_debe_clp',
            'sumas_haber_clp',
            'saldo_deudor_clp',
            'saldo_acreedor_clp',
            'inventario_activo_clp',
            'inventario_pasivo_clp',
            'resultado_perdida_clp',
            'resultado_ganancia_clp',
        )
        for field_name in non_negative_fields:
            if getattr(self, field_name) < 0:
                errors[field_name] = f'{field_name} no puede ser negativo.'
        if self.saldo_deudor_clp and self.saldo_acreedor_clp:
            errors['saldo_deudor_clp'] = 'Una linea no puede tener saldo deudor y acreedor simultaneamente.'
        if self.inventario_activo_clp and self.inventario_pasivo_clp:
            errors['inventario_activo_clp'] = 'Una linea no puede clasificar inventario activo y pasivo simultaneamente.'
        if self.resultado_perdida_clp and self.resultado_ganancia_clp:
            errors['resultado_perdida_clp'] = 'Una linea no puede clasificar perdida y ganancia simultaneamente.'

        expected_hash = _payload_hash(_trial_balance_line_integrity_payload(self))
        if self.hash_linea and self.hash_linea != expected_hash:
            errors['hash_linea'] = 'hash_linea debe corresponder a la linea de balance tributario.'

        if self.estado == EstadoRegistro.ACTIVE:
            if not has_text(self.codigo_cuenta):
                errors['codigo_cuenta'] = 'Linea activa requiere codigo_cuenta.'
            if not has_text(self.nombre_cuenta):
                errors['nombre_cuenta'] = 'Linea activa requiere nombre_cuenta.'
            if not has_text(self.clasificador_dj1847):
                errors['clasificador_dj1847'] = 'Linea activa requiere clasificador_dj1847 trazable.'
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
        'warning_review_ref',
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
    warning_review_ref = models.CharField(max_length=255, blank=True)
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
        _add_non_sensitive_reference_error(errors, self, 'warning_review_ref')
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
    warning_review_ref = models.CharField(max_length=255, blank=True)
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
        _add_non_sensitive_reference_error(errors, self, 'warning_review_ref')
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
    official_contribution_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='real_estate_contribution_sections',
        null=True,
        blank=True,
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

        try:
            contribution_source = self.official_contribution_source
        except ObjectDoesNotExist:
            contribution_source = None
        if contribution_source is not None:
            try:
                contribution_source.full_clean()
            except ValidationError:
                errors['official_contribution_source'] = 'AnnualTaxOfficialSource de contribuciones no pasa validacion de dominio.'
            else:
                allowed_source_types = {
                    TipoAnnualTaxOfficialSource.SII_REAL_ESTATE_CONTRIBUTIONS,
                    TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
                }
                allowed_destinations = {
                    '',
                    DestinoMapeoTributarioAnual.F22,
                    DestinoMapeoTributarioAnual.DOSSIER,
                }
                if contribution_source.anio_tributario != self.anio_tributario:
                    errors['official_contribution_source'] = 'Fuente de contribuciones debe corresponder al mismo anio_tributario.'
                elif contribution_source.estado not in ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES:
                    errors['official_contribution_source'] = 'Fuente de contribuciones debe estar revisada o aprobada.'
                elif contribution_source.source_type not in allowed_source_types:
                    errors['official_contribution_source'] = 'Fuente de contribuciones debe ser SII bienes raices o revision experta.'
                elif contribution_source.applies_to not in allowed_destinations:
                    errors['official_contribution_source'] = 'Fuente de contribuciones solo puede aplicar a F22, Dossier o alcance general.'
                if 'official_contribution_source' not in errors and has_text(contribution_source.regime_code):
                    try:
                        regime_code = self.empresa.configuracion_fiscal.regimen_tributario.codigo_regimen
                    except ObjectDoesNotExist:
                        regime_code = ''
                    if has_text(regime_code) and contribution_source.regime_code != regime_code:
                        errors['official_contribution_source'] = 'Fuente de contribuciones debe corresponder al regimen tributario de la empresa.'
                if (
                    'official_contribution_source' not in errors
                    and contribution_source.source_type == TipoAnnualTaxOfficialSource.EXPERT_REVIEW
                    and contribution_source.applies_to not in {
                        DestinoMapeoTributarioAnual.F22,
                        DestinoMapeoTributarioAnual.DOSSIER,
                    }
                ):
                    errors['official_contribution_source'] = 'Revision experta de contribuciones debe declarar alcance F22 o Dossier.'
                if (
                    'official_contribution_source' not in errors
                    and contribution_source.source_type == TipoAnnualTaxOfficialSource.EXPERT_REVIEW
                    and not (
                        isinstance(contribution_source.metadata, dict)
                        and contribution_source.metadata.get('real_estate_contributions') is True
                    )
                ):
                    errors['official_contribution_source'] = 'Revision experta de contribuciones debe declarar metadata real_estate_contributions.'

        if isinstance(self.resumen_seccion, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('official_contribution_source_id', self.official_contribution_source_id),
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
        'warning_review_ref',
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
    warning_review_ref = models.CharField(max_length=255, blank=True)
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
        _add_non_sensitive_reference_error(errors, self, 'warning_review_ref')
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
            if (
                self.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
                and self.warnings
                and not has_text(self.warning_review_ref)
            ):
                errors['warning_review_ref'] = 'Items con warnings listos para revision requieren warning_review_ref.'
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
                _add_error(errors, 'resumen_dossier', 'resumen_dossier debe coincidir con review_state.')
            if self.resumen_dossier.get('official_format') not in (False, None):
                _add_error(errors, 'resumen_dossier', 'AnnualTaxDossier v1 no declara formato oficial SII.')
            if self.resumen_dossier.get('sii_submission') not in (False, None):
                _add_error(errors, 'resumen_dossier', 'AnnualTaxDossier v1 no registra presentacion SII.')
            if self.resumen_dossier.get('sii_submission_attempted'):
                _add_error(errors, 'resumen_dossier', 'AnnualTaxDossier v1 no registra intentos de presentacion SII.')
            if self.resumen_dossier.get('final_tax_calculation') not in (False, None):
                _add_error(errors, 'resumen_dossier', 'AnnualTaxDossier v1 no declara calculo fiscal final.')
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
            pending_warning_reviews = self.warnings_total
            if isinstance(self.resumen_dossier, dict):
                try:
                    pending_warning_reviews = int(
                        self.resumen_dossier.get('warnings_pending_review_total', pending_warning_reviews) or 0
                    )
                except (TypeError, ValueError):
                    pending_warning_reviews = self.warnings_total
            if self.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW and pending_warning_reviews:
                errors['review_state'] = 'Dossier con warnings pendientes no puede quedar listo_revision.'
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
    official_format_source = models.ForeignKey(
        AnnualTaxOfficialSource,
        on_delete=models.PROTECT,
        related_name='annual_tax_exports',
        null=True,
        blank=True,
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
            official_format_source = self.official_format_source
        except ObjectDoesNotExist:
            official_format_source = None
        if official_format_source is not None:
            _add_official_source_link_errors(
                errors,
                self,
                'official_format_source',
                anio_tributario=self.anio_tributario,
                applies_to=DestinoMapeoTributarioAnual.F22,
            )
            if official_format_source.source_type not in {
                TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION,
                TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            }:
                errors['official_format_source'] = (
                    'AnnualTaxOfficialSource no corresponde a formato/certificacion F22.'
                )
            if has_text(official_format_source.form_code) and official_format_source.form_code != 'F22':
                errors['official_format_source'] = 'AnnualTaxOfficialSource debe corresponder a F22.'
            source_metadata = official_format_source.metadata if isinstance(official_format_source.metadata, dict) else {}
            if (
                official_format_source.source_type == TipoAnnualTaxOfficialSource.EXPERT_REVIEW
                and source_metadata.get('f22_export_format') is not True
                and source_metadata.get('f22_certification') is not True
            ):
                errors['official_format_source'] = (
                    'Revision experta F22 requiere metadata f22_export_format o f22_certification.'
                )

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
                ('official_format_source_id', self.official_format_source_id),
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
            contracts = self.export_payload.get('export_artifact_contracts')
            contract_artifact_ids = set()
            if self.estado == EstadoAnnualTaxExport.PREPARED and not isinstance(contracts, list):
                _add_error(errors, 'export_payload', 'AnnualTaxExport preparado requiere export_artifact_contracts.')
            elif isinstance(contracts, list):
                target_counts = {TipoAnnualTaxArtifactTarget.DDJJ: 0, TipoAnnualTaxArtifactTarget.F22: 0}
                invalid_contracts = 0
                boundary_contracts = 0
                for contract in contracts:
                    if not isinstance(contract, dict):
                        invalid_contracts += 1
                        continue
                    if has_text(contract.get('artifact_matrix_item_id')):
                        contract_artifact_ids.add(str(contract.get('artifact_matrix_item_id')))
                    target_kind = contract.get('target_kind')
                    if target_kind in target_counts:
                        target_counts[target_kind] += 1
                    else:
                        invalid_contracts += 1
                    if contract.get('contract_version') != 'annual-tax-export-artifact-contract-v1':
                        invalid_contracts += 1
                    if not has_text(contract.get('target_code')):
                        invalid_contracts += 1
                    if contract.get('delivery_kind') != 'local_controlled_preview':
                        invalid_contracts += 1
                    if not has_text(contract.get('artifact_matrix_item_id')):
                        invalid_contracts += 1
                    if not has_text(contract.get('hash_item')):
                        invalid_contracts += 1
                    if not has_text(contract.get('review_state')):
                        invalid_contracts += 1
                    if contract.get('requires_official_format_gate') is not True:
                        invalid_contracts += 1
                    if contract.get('requires_explicit_submission_authorization') is not True:
                        invalid_contracts += 1
                    if (
                        contract.get('official_format') not in (False, None)
                        or contract.get('sii_submission') not in (False, None)
                        or contract.get('final_tax_calculation') not in (False, None)
                    ):
                        boundary_contracts += 1
                if len(contracts) != self.target_items_total:
                    _add_error(errors, 'export_payload', 'export_artifact_contracts debe cubrir todos los items DDJJ/F22.')
                if target_counts[TipoAnnualTaxArtifactTarget.DDJJ] != self.ddjj_items_total:
                    _add_error(errors, 'export_payload', 'export_artifact_contracts DDJJ no coincide con ddjj_items_total.')
                if target_counts[TipoAnnualTaxArtifactTarget.F22] != self.f22_items_total:
                    _add_error(errors, 'export_payload', 'export_artifact_contracts F22 no coincide con f22_items_total.')
                for key, expected in (
                    ('export_contracts_total', self.target_items_total),
                    ('ddjj_export_contracts_total', self.ddjj_items_total),
                    ('f22_export_contracts_total', self.f22_items_total),
                ):
                    if key in self.export_payload:
                        try:
                            matches = int(self.export_payload.get(key) or 0) == int(expected)
                        except (TypeError, ValueError):
                            matches = False
                        if not matches:
                            _add_error(errors, 'export_payload', f'{key} debe coincidir con los contratos exportables.')
                if invalid_contracts:
                    _add_error(errors, 'export_payload', 'export_artifact_contracts contiene contratos invalidos.')
                if boundary_contracts:
                    _add_error(errors, 'export_payload', 'export_artifact_contracts no puede declarar formato oficial, presentacion SII ni calculo final.')
            file_manifest = self.export_payload.get('export_file_manifest')
            file_artifact_ids = set()
            if self.estado == EstadoAnnualTaxExport.PREPARED and not isinstance(file_manifest, list):
                _add_error(errors, 'export_payload', 'AnnualTaxExport preparado requiere export_file_manifest.')
            elif isinstance(file_manifest, list):
                file_counts = {TipoAnnualTaxArtifactTarget.DDJJ: 0, TipoAnnualTaxArtifactTarget.F22: 0}
                invalid_files = 0
                boundary_files = 0
                seen_file_names = set()
                for entry in file_manifest:
                    if not isinstance(entry, dict):
                        invalid_files += 1
                        continue
                    artifact_id = entry.get('artifact_matrix_item_id')
                    if has_text(artifact_id):
                        file_artifact_ids.add(str(artifact_id))
                    else:
                        invalid_files += 1
                    target_kind = entry.get('target_kind')
                    if target_kind in file_counts:
                        file_counts[target_kind] += 1
                    else:
                        invalid_files += 1
                    file_name = str(entry.get('file_name') or '').strip()
                    if file_name in seen_file_names:
                        invalid_files += 1
                    seen_file_names.add(file_name)
                    if (
                        entry.get('file_manifest_version') != 'annual-tax-export-file-manifest-v1'
                        or not has_text(entry.get('target_code'))
                        or not file_name.lower().endswith('.json')
                        or '/' in file_name
                        or '\\' in file_name
                        or entry.get('content_type') != 'application/json'
                        or entry.get('encoding') != 'utf-8'
                        or entry.get('schema_ref') != 'annual-tax-export-file-payload-v1'
                        or entry.get('delivery_kind') != 'local_controlled_export_file'
                        or entry.get('source_contract_version') != 'annual-tax-export-artifact-contract-v1'
                        or not _is_sha256(entry.get('payload_hash'))
                        or entry.get('requires_official_format_gate') is not True
                        or entry.get('requires_explicit_submission_authorization') is not True
                    ):
                        invalid_files += 1
                    try:
                        valid_size = int(entry.get('payload_size_bytes') or 0) > 0
                    except (TypeError, ValueError):
                        valid_size = False
                    if not valid_size:
                        invalid_files += 1
                    if (
                        entry.get('official_format') not in (False, None)
                        or entry.get('sii_submission') not in (False, None)
                        or entry.get('final_tax_calculation') not in (False, None)
                    ):
                        boundary_files += 1
                if len(file_manifest) != self.target_items_total:
                    _add_error(errors, 'export_payload', 'export_file_manifest debe cubrir todos los items DDJJ/F22.')
                if file_counts[TipoAnnualTaxArtifactTarget.DDJJ] != self.ddjj_items_total:
                    _add_error(errors, 'export_payload', 'export_file_manifest DDJJ no coincide con ddjj_items_total.')
                if file_counts[TipoAnnualTaxArtifactTarget.F22] != self.f22_items_total:
                    _add_error(errors, 'export_payload', 'export_file_manifest F22 no coincide con f22_items_total.')
                if contract_artifact_ids and file_artifact_ids != contract_artifact_ids:
                    _add_error(errors, 'export_payload', 'export_file_manifest debe coincidir con los contratos exportables.')
                for key, expected in (
                    ('export_files_total', self.target_items_total),
                    ('ddjj_export_files_total', self.ddjj_items_total),
                    ('f22_export_files_total', self.f22_items_total),
                ):
                    if key in self.export_payload:
                        try:
                            matches = int(self.export_payload.get(key) or 0) == int(expected)
                        except (TypeError, ValueError):
                            matches = False
                        if not matches:
                            _add_error(errors, 'export_payload', f'{key} debe coincidir con el manifiesto exportable.')
                manifest_hash = self.export_payload.get('export_file_manifest_hash')
                if manifest_hash is not None and not _is_sha256(manifest_hash):
                    _add_error(errors, 'export_payload', 'export_file_manifest_hash debe ser SHA-256.')
                if invalid_files:
                    _add_error(errors, 'export_payload', 'export_file_manifest contiene archivos invalidos.')
                if boundary_files:
                    _add_error(errors, 'export_payload', 'export_file_manifest no puede declarar formato oficial, presentacion SII ni calculo final.')
            package_manifest = self.export_payload.get('export_file_package_manifest')
            if self.estado == EstadoAnnualTaxExport.PREPARED and not isinstance(package_manifest, list):
                _add_error(errors, 'export_payload', 'AnnualTaxExport preparado requiere export_file_package_manifest.')
            elif isinstance(package_manifest, list):
                package_counts = {TipoAnnualTaxArtifactTarget.DDJJ: 0, TipoAnnualTaxArtifactTarget.F22: 0}
                package_artifact_ids = set()
                invalid_package_files = 0
                boundary_package_files = 0
                seen_package_file_names = set()
                for entry in package_manifest:
                    if not isinstance(entry, dict):
                        invalid_package_files += 1
                        continue
                    artifact_id = entry.get('artifact_matrix_item_id')
                    if has_text(artifact_id):
                        package_artifact_ids.add(str(artifact_id))
                    else:
                        invalid_package_files += 1
                    target_kind = entry.get('target_kind')
                    if target_kind in package_counts:
                        package_counts[target_kind] += 1
                    else:
                        invalid_package_files += 1
                    file_name = str(entry.get('file_name') or '').strip()
                    if file_name in seen_package_file_names:
                        invalid_package_files += 1
                    seen_package_file_names.add(file_name)
                    if (
                        entry.get('package_entry_version') != 'annual-tax-export-file-package-manifest-v1'
                        or not has_text(entry.get('target_code'))
                        or not file_name.lower().endswith('.json')
                        or '/' in file_name
                        or '\\' in file_name
                        or entry.get('content_type') != 'application/json'
                        or entry.get('encoding') != 'utf-8'
                        or entry.get('schema_ref') != 'annual-tax-export-file-payload-v1'
                        or entry.get('delivery_kind') != 'local_controlled_export_package'
                        or entry.get('materialized_from') != 'annual-tax-export-file-payload-v1'
                        or entry.get('canonical_json') != 'sort_keys_ascii_compact'
                        or not _is_sha256(entry.get('payload_hash'))
                        or not _is_sha256(entry.get('manifest_payload_hash'))
                        or entry.get('payload_hash') != entry.get('manifest_payload_hash')
                        or entry.get('requires_official_format_gate') is not True
                        or entry.get('requires_explicit_submission_authorization') is not True
                    ):
                        invalid_package_files += 1
                    try:
                        payload_size = int(entry.get('payload_size_bytes') or 0)
                        manifest_size = int(entry.get('manifest_payload_size_bytes') or 0)
                        valid_size = payload_size > 0 and payload_size == manifest_size
                    except (TypeError, ValueError):
                        valid_size = False
                    if not valid_size:
                        invalid_package_files += 1
                    if (
                        entry.get('official_format') not in (False, None)
                        or entry.get('sii_submission') not in (False, None)
                        or entry.get('final_tax_calculation') not in (False, None)
                    ):
                        boundary_package_files += 1
                if len(package_manifest) != self.target_items_total:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest debe cubrir todos los items DDJJ/F22.')
                if package_counts[TipoAnnualTaxArtifactTarget.DDJJ] != self.ddjj_items_total:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest DDJJ no coincide con ddjj_items_total.')
                if package_counts[TipoAnnualTaxArtifactTarget.F22] != self.f22_items_total:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest F22 no coincide con f22_items_total.')
                if contract_artifact_ids and package_artifact_ids != contract_artifact_ids:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest debe coincidir con los contratos exportables.')
                if file_artifact_ids and package_artifact_ids != file_artifact_ids:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest debe coincidir con export_file_manifest.')
                for key, expected in (
                    ('export_file_package_files_total', self.target_items_total),
                    ('ddjj_export_package_files_total', self.ddjj_items_total),
                    ('f22_export_package_files_total', self.f22_items_total),
                ):
                    if key in self.export_payload:
                        try:
                            matches = int(self.export_payload.get(key) or 0) == int(expected)
                        except (TypeError, ValueError):
                            matches = False
                        if not matches:
                            _add_error(errors, 'export_payload', f'{key} debe coincidir con el paquete exportable.')
                if self.export_payload.get('export_file_package_version') not in (None, 'annual-tax-export-file-package-v1'):
                    _add_error(errors, 'export_payload', 'export_file_package_version debe ser annual-tax-export-file-package-v1.')
                package_hash = self.export_payload.get('export_file_package_hash')
                if package_hash is not None and not _is_sha256(package_hash):
                    _add_error(errors, 'export_payload', 'export_file_package_hash debe ser SHA-256.')
                elif package_hash is not None and package_hash != _payload_hash(package_manifest):
                    _add_error(errors, 'export_payload', 'export_file_package_hash debe corresponder al manifiesto de paquete.')
                if invalid_package_files:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest contiene archivos invalidos.')
                if boundary_package_files:
                    _add_error(errors, 'export_payload', 'export_file_package_manifest no puede declarar formato oficial, presentacion SII ni calculo final.')
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


class AnnualTaxReviewChecklist(OperationalSIITextNormalizationMixin, TimestampedModel):
    operational_text_fields = (
        'checklist_ref',
        'responsible_ref',
        'evidence_ref',
        'review_decision_ref',
        'hash_checklist',
    )

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.PROTECT,
        related_name='annual_tax_review_checklists',
    )
    proceso_renta_anual = models.ForeignKey(
        'sii.ProcesoRentaAnual',
        on_delete=models.PROTECT,
        related_name='tax_review_checklists',
    )
    dossier = models.ForeignKey(
        AnnualTaxDossier,
        on_delete=models.PROTECT,
        related_name='review_checklists',
    )
    annual_export = models.ForeignKey(
        AnnualTaxExport,
        on_delete=models.PROTECT,
        related_name='review_checklists',
    )
    source_bundle = models.ForeignKey(
        AnnualTaxSourceBundle,
        on_delete=models.PROTECT,
        related_name='tax_review_checklists',
    )
    rule_set = models.ForeignKey(
        TaxYearRuleSet,
        on_delete=models.PROTECT,
        related_name='tax_review_checklists',
    )
    artifact_matrix = models.ForeignKey(
        AnnualTaxArtifactMatrix,
        on_delete=models.PROTECT,
        related_name='tax_review_checklists',
    )
    anio_tributario = models.PositiveSmallIntegerField()
    anio_comercial = models.PositiveSmallIntegerField()
    checklist_ref = models.CharField(max_length=255, blank=True)
    responsible_ref = models.CharField(max_length=255, blank=True)
    evidence_ref = models.CharField(max_length=255, blank=True)
    items_total = models.PositiveIntegerField(default=0)
    completed_items_total = models.PositiveIntegerField(default=0)
    blockers_total = models.PositiveIntegerField(default=0)
    warnings_total = models.PositiveIntegerField(default=0)
    review_decision_state = models.CharField(
        max_length=32,
        choices=EstadoAnnualTaxReviewDecision.choices,
        default=EstadoAnnualTaxReviewDecision.PREPARED,
    )
    review_decision_ref = models.CharField(max_length=255, blank=True)
    review_decision_evidence_ref = models.CharField(max_length=255, blank=True)
    review_payload = models.JSONField(default=dict, blank=True)
    hash_checklist = models.CharField(max_length=64, blank=True)
    estado = models.CharField(
        max_length=16,
        choices=EstadoAnnualTaxReviewChecklist.choices,
        default=EstadoAnnualTaxReviewChecklist.DRAFT,
    )

    class Meta:
        ordering = ['empresa_id', '-anio_tributario', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['proceso_renta_anual'],
                name='uniq_annual_tax_review_checklist_process',
            ),
        ]

    def __str__(self):
        return f'Checklist renta {self.empresa_id} AT{self.anio_tributario}'

    def clean(self):
        super().clean()
        self.hash_checklist = _normalize_hash(self.hash_checklist)
        errors = {}
        expected_commercial_year = self.anio_tributario - 1
        if self.anio_comercial != expected_commercial_year:
            errors['anio_comercial'] = (
                f'anio_comercial debe ser {expected_commercial_year} para AT{self.anio_tributario}.'
            )
        _add_non_sensitive_reference_error(errors, self, 'checklist_ref')
        _add_non_sensitive_reference_error(errors, self, 'responsible_ref')
        _add_non_sensitive_reference_error(errors, self, 'evidence_ref')
        _add_non_sensitive_reference_error(errors, self, 'review_decision_ref')
        _add_non_sensitive_reference_error(errors, self, 'review_decision_evidence_ref')
        _add_non_sensitive_payload_error(errors, 'review_payload', self.review_payload)
        if has_text(self.hash_checklist) and not _is_sha256(self.hash_checklist):
            errors['hash_checklist'] = 'hash_checklist debe ser SHA-256 hexadecimal de 64 caracteres.'
        if self.completed_items_total > self.items_total:
            errors['completed_items_total'] = 'completed_items_total no puede superar items_total.'
        checklist_is_complete = (
            self.items_total > 0
            and self.completed_items_total == self.items_total
            and self.blockers_total == 0
            and self.warnings_total == 0
        )
        if self.review_decision_state == EstadoAnnualTaxReviewDecision.PREPARED and not checklist_is_complete:
            errors['review_decision_state'] = 'Decision preparada requiere checklist completo y sin observaciones.'
        if self.review_decision_state == EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION:
            if not checklist_is_complete:
                errors['review_decision_state'] = 'Aprobacion para presentacion requiere checklist completo y sin observaciones.'
            if not has_text(self.review_decision_ref):
                errors['review_decision_ref'] = 'Aprobacion para presentacion requiere decision_ref trazable no sensible.'
            if not has_text(self.review_decision_evidence_ref):
                errors['review_decision_evidence_ref'] = (
                    'Aprobacion para presentacion requiere evidencia de decision trazable no sensible.'
                )

        try:
            process = self.proceso_renta_anual
        except ObjectDoesNotExist:
            process = None
        if process is not None:
            if process.empresa_id != self.empresa_id:
                errors['proceso_renta_anual'] = 'El proceso anual debe pertenecer a la misma empresa del checklist.'
            elif process.anio_tributario != self.anio_tributario:
                errors['proceso_renta_anual'] = 'El proceso anual debe corresponder al mismo anio_tributario.'
            if process.source_bundle_id and process.source_bundle_id != self.source_bundle_id:
                errors['source_bundle'] = 'El checklist debe usar el mismo AnnualTaxSourceBundle del proceso anual.'

        try:
            dossier = self.dossier
        except ObjectDoesNotExist:
            dossier = None
        if dossier is not None:
            if dossier.empresa_id != self.empresa_id:
                errors['dossier'] = 'AnnualTaxDossier debe pertenecer a la misma empresa del checklist.'
            elif dossier.proceso_renta_anual_id != self.proceso_renta_anual_id:
                errors['dossier'] = 'AnnualTaxDossier debe corresponder al mismo proceso anual.'
            elif dossier.anio_tributario != self.anio_tributario:
                errors['dossier'] = 'AnnualTaxDossier debe corresponder al mismo anio_tributario.'
            elif dossier.estado != EstadoAnnualTaxDossier.PREPARED:
                errors['dossier'] = 'AnnualTaxReviewChecklist requiere AnnualTaxDossier preparado.'

        try:
            annual_export = self.annual_export
        except ObjectDoesNotExist:
            annual_export = None
        if annual_export is not None:
            if annual_export.empresa_id != self.empresa_id:
                errors['annual_export'] = 'AnnualTaxExport debe pertenecer a la misma empresa del checklist.'
            elif annual_export.proceso_renta_anual_id != self.proceso_renta_anual_id:
                errors['annual_export'] = 'AnnualTaxExport debe corresponder al mismo proceso anual.'
            elif annual_export.anio_tributario != self.anio_tributario:
                errors['annual_export'] = 'AnnualTaxExport debe corresponder al mismo anio_tributario.'
            elif annual_export.estado != EstadoAnnualTaxExport.PREPARED:
                errors['annual_export'] = 'AnnualTaxReviewChecklist requiere AnnualTaxExport preparado.'
            elif annual_export.dossier_id != self.dossier_id:
                errors['annual_export'] = 'AnnualTaxExport debe apuntar al mismo dossier del checklist.'

        for field_name, related_object, expected_state, message in (
            ('source_bundle', getattr(self, 'source_bundle', None), EstadoAnnualTaxSourceBundle.FROZEN, 'AnnualTaxSourceBundle congelado'),
            ('rule_set', getattr(self, 'rule_set', None), EstadoReglaTributariaAnual.APPROVED, 'TaxYearRuleSet aprobado'),
            ('artifact_matrix', getattr(self, 'artifact_matrix', None), EstadoAnnualTaxArtifactMatrix.PREPARED, 'AnnualTaxArtifactMatrix preparada'),
        ):
            try:
                obj = related_object
            except ObjectDoesNotExist:
                obj = None
            if obj is None:
                continue
            if getattr(obj, 'anio_tributario', self.anio_tributario) != self.anio_tributario:
                errors[field_name] = f'{message} debe corresponder al mismo anio_tributario.'
            elif getattr(obj, 'estado', None) != expected_state:
                errors[field_name] = f'AnnualTaxReviewChecklist requiere {message}.'

        if isinstance(self.review_payload, dict):
            identity_errors = []
            for key, expected in (
                ('empresa_id', self.empresa_id),
                ('proceso_renta_anual_id', self.proceso_renta_anual_id),
                ('dossier_id', self.dossier_id),
                ('annual_export_id', self.annual_export_id),
                ('source_bundle_id', self.source_bundle_id),
                ('rule_set_id', self.rule_set_id),
                ('artifact_matrix_id', self.artifact_matrix_id),
                ('anio_tributario', self.anio_tributario),
                ('anio_comercial', self.anio_comercial),
                ('items_total', self.items_total),
                ('completed_items_total', self.completed_items_total),
                ('blockers_total', self.blockers_total),
                ('warnings_total', self.warnings_total),
            ):
                value = self.review_payload.get(key)
                if value is None:
                    continue
                try:
                    matches = int(value) == int(expected)
                except (TypeError, ValueError):
                    matches = False
                if not matches:
                    identity_errors.append(key)
            if identity_errors:
                errors['review_payload'] = (
                    'review_payload debe coincidir con empresa, proceso, dossier, export, fuente, regla, matriz, anio y totales.'
                )
            if self.review_payload.get('review_decision_state') not in (self.review_decision_state, None):
                _add_error(errors, 'review_payload', 'review_decision_state debe coincidir con la decision del checklist.')
            if self.review_payload.get('review_decision_ref') not in (self.review_decision_ref, None):
                _add_error(errors, 'review_payload', 'review_decision_ref debe coincidir con la decision del checklist.')
            if self.review_payload.get('review_decision_evidence_ref') not in (self.review_decision_evidence_ref, None):
                _add_error(errors, 'review_payload', 'review_decision_evidence_ref debe coincidir con la evidencia de decision.')
            review_decision = self.review_payload.get('review_decision')
            if review_decision is not None and not isinstance(review_decision, dict):
                _add_error(errors, 'review_payload', 'review_decision debe ser un objeto JSON.')
            elif isinstance(review_decision, dict):
                decision_state = review_decision.get('state')
                if decision_state != self.review_decision_state:
                    _add_error(errors, 'review_payload', 'review_decision.state debe coincidir con la decision del checklist.')
                ready_for_presentation = review_decision.get('ready_for_presentation')
                if (
                    self.review_decision_state == EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION
                    and ready_for_presentation is not True
                ):
                    _add_error(errors, 'review_payload', 'Aprobacion para presentacion requiere ready_for_presentation=true.')
                if (
                    self.review_decision_state != EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION
                    and ready_for_presentation not in (False, None)
                ):
                    _add_error(errors, 'review_payload', 'Solo una decision aprobada puede marcar ready_for_presentation.')
                if review_decision.get('automatic_approval') not in (False, None):
                    _add_error(errors, 'review_payload', 'La aprobacion de revision tributaria no puede ser automatica.')
                if self.review_decision_state == EstadoAnnualTaxReviewDecision.APPROVED_FOR_PRESENTATION:
                    if not has_text(review_decision.get('decision_ref')):
                        _add_error(errors, 'review_payload', 'Aprobacion requiere decision_ref no sensible en review_decision.')
                    if not has_text(review_decision.get('responsible_ref')):
                        _add_error(errors, 'review_payload', 'Aprobacion requiere responsible_ref no sensible en review_decision.')
                    if not has_text(review_decision.get('evidence_ref')):
                        _add_error(errors, 'review_payload', 'Aprobacion requiere evidence_ref no sensible en review_decision.')
                if (
                    review_decision.get('decision_ref') not in (self.review_decision_ref, None)
                    or review_decision.get('evidence_ref') not in (self.review_decision_evidence_ref, None)
                ):
                    _add_error(errors, 'review_payload', 'review_decision debe coincidir con refs de decision del checklist.')
            for key in ('official_format', 'sii_submission', 'final_tax_calculation'):
                if self.review_payload.get(key) not in (False, None):
                    _add_error(errors, 'review_payload', 'Checklist anual no declara formato oficial, presentacion SII ni calculo fiscal final.')
            if self.review_payload.get('sii_submission_attempted'):
                _add_error(errors, 'review_payload', 'Checklist anual no registra intentos de presentacion SII.')
            expected_hash = _payload_hash(self.review_payload)
            if self.hash_checklist and self.hash_checklist != expected_hash:
                errors['hash_checklist'] = 'hash_checklist debe corresponder al review_payload.'
        elif self.review_payload:
            errors['review_payload'] = 'review_payload debe ser un objeto JSON.'

        if self.estado == EstadoAnnualTaxReviewChecklist.PREPARED:
            _add_active_fiscal_config_error(errors, self, 'AnnualTaxReviewChecklist')
            if not has_text(self.checklist_ref):
                errors['checklist_ref'] = 'AnnualTaxReviewChecklist preparado requiere checklist_ref no sensible.'
            if not has_text(self.responsible_ref):
                errors['responsible_ref'] = 'AnnualTaxReviewChecklist preparado requiere responsible_ref no sensible.'
            if not has_text(self.evidence_ref):
                errors['evidence_ref'] = 'AnnualTaxReviewChecklist preparado requiere evidence_ref no sensible.'
            if not self.review_payload:
                errors['review_payload'] = 'AnnualTaxReviewChecklist preparado requiere review_payload.'
            if not has_text(self.hash_checklist):
                errors['hash_checklist'] = 'AnnualTaxReviewChecklist preparado requiere hash_checklist.'
            if self.items_total <= 0:
                errors['items_total'] = 'AnnualTaxReviewChecklist preparado requiere items de revision.'
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
