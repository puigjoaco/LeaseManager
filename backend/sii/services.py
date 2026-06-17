import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import transaction
from django.db.models import Q

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    CuentaContable,
    EstadoCierreMensual,
    EstadoLiquidacionMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    LineaLiquidacionMensual,
    ObligacionTributariaMensual,
    TipoOwnerLiquidacion,
)
from cobranza.models import DistribucionCobroMensual
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from documentos.models import (
    DocumentoEmitido,
    EstadoDocumento,
    EstadoPlantillaDocumental,
    EstadoPoliticaFirma,
    ExpedienteDocumental,
    ModoFirmaPermitido,
    PlantillaDocumental,
    PoliticaFirmaYNotaria,
    TipoDocumental,
)
from documentos.pdf_generation import (
    build_generated_pdf_payload,
    emit_generated_pdf_document,
    preview_generated_pdf_document,
)

from .models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDDJJFormLayout,
    AnnualTaxF22ExportLayout,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxReviewChecklist,
    AnnualTaxSourceBundle,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES,
    CapacidadSII,
    DDJJPreparacionAnual,
    DestinoMapeoTributarioAnual,
    DTEEmitido,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualRealEstateSection,
    EstadoAnnualTaxArtifactMatrix,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDDJJLayout,
    EstadoAnnualTaxF22ExportLayout,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxOfficialSource,
    EstadoAnnualTaxReviewChecklist,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    EstadoDTE,
    EstadoGateSII,
    EstadoMonthlyTaxFact,
    EstadoReglaTributariaAnual,
    F22PreparacionAnual,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    SII_AUTOMATED_REGIME_CODE,
    EstadoAnnualTaxSourceBundle,
    SourceKindRentaAnual,
    SourceKindAnnualTaxArtifact,
    SignoAnnualTaxLine,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualTaxArtifactTarget,
    TipoAnnualTaxExport,
    TipoAnnualEnterpriseRegister,
    TipoAnnualTaxOfficialSource,
    TipoAnnualTaxWorkbook,
    TipoDTE,
    has_text,
)
from patrimonio.models import ParticipacionPatrimonial, Propiedad


DTE_EXTERNAL_STATES = {
    EstadoDTE.SENT_MANUAL,
    EstadoDTE.ACCEPTED,
    EstadoDTE.REJECTED,
    EstadoDTE.CANCELED,
}
DTE_STATUS_QUERY_STATES = {
    EstadoDTE.ACCEPTED,
    EstadoDTE.REJECTED,
    EstadoDTE.CANCELED,
}
ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION = 'stage6-v1'

TAX_STATUS_REQUIRING_REF = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}
TAX_STATUS_REQUIRING_GATE = {
    EstadoPreparacionTributaria.PREPARED,
    *TAX_STATUS_REQUIRING_REF,
}


def _first_readiness_error(errors):
    if not errors:
        return ''
    field, message = next(iter(errors.items()))
    return f'{field}: {message}'


def _first_validation_error(error):
    if hasattr(error, 'message_dict'):
        field, messages = next(iter(error.message_dict.items()))
        if isinstance(messages, (list, tuple)):
            message = messages[0] if messages else ''
        else:
            message = messages
        return f'{field}: {message}'

    messages = getattr(error, 'messages', None)
    if messages:
        return str(messages[0])
    return str(error)


def _ensure_artifact_valid_for_status_transition(instance, label):
    try:
        instance.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'{label} no cumple validacion de dominio para avanzar estado: {reason}') from error


def _ensure_non_sensitive_reference(value, field_name):
    normalized = str(value or '').strip()
    if normalized and not is_non_sensitive_reference(normalized):
        raise ValueError(f'{field_name} debe ser una referencia no sensible; no use URLs, tokens, credenciales ni correos.')
    return normalized


def _ensure_non_sensitive_text(value, field_name):
    normalized = str(value or '').strip()
    if normalized and contains_sensitive_reference(normalized):
        raise ValueError(f'{field_name} no debe contener URLs, tokens, credenciales ni correos.')
    return normalized


def ensure_sii_capability_ready(capability, capability_label=None):
    capability_label = capability_label or capability.capacidad_key
    if capability.estado_gate != EstadoGateSII.OPEN:
        raise ValueError(f'La capacidad {capability_label} no esta habilitada por gate para esta empresa.')
    reason = _first_readiness_error(capability.readiness_errors())
    if reason:
        raise ValueError(f'La capacidad {capability_label} no cumple readiness SII: {reason}')
    try:
        capability.full_clean()
    except ValidationError as error:
        errors = error.message_dict if hasattr(error, 'message_dict') else {'capacidad': error.messages}
        reason = _first_readiness_error(errors)
        raise ValueError(f'La capacidad {capability_label} no cumple readiness SII: {reason}') from error
    return capability


def resolve_facturadora_company(payment):
    distributions = list(
        payment.distribuciones_cobro.filter(requiere_dte=True).select_related('beneficiario_empresa_owner')
    )
    if not distributions:
        return None
    if len(distributions) > 1:
        raise ValueError('El boundary actual no soporta multiples distribuciones facturables por el mismo pago.')
    return distributions[0].beneficiario_empresa_owner


def get_active_dte_capability(empresa):
    if empresa is None:
        raise ValueError('El pago no tiene una entidad facturadora configurada.')

    capability = empresa.capacidades_sii.filter(capacidad_key=CapacidadSII.DTE_EMISION).first()
    if not capability:
        raise ValueError('La empresa no tiene configurada la capacidad DTEEmision.')
    return ensure_sii_capability_ready(capability, CapacidadSII.DTE_EMISION)


def get_active_dte_status_capability(empresa):
    capability = empresa.capacidades_sii.filter(capacidad_key=CapacidadSII.DTE_CONSULTA).first()
    if not capability:
        raise ValueError('La empresa no tiene configurada la capacidad DTEConsultaEstado.')
    return ensure_sii_capability_ready(capability, CapacidadSII.DTE_CONSULTA)


def validate_company_fiscal_readiness(empresa):
    config = getattr(empresa, 'configuracion_fiscal', None)
    if not config or config.estado != 'activa':
        raise ValueError('La empresa no tiene una configuracion fiscal activa para emitir DTE.')
    if config.regimen_tributario.codigo_regimen != SII_AUTOMATED_REGIME_CODE:
        raise ValueError('La empresa no pertenece al regimen fiscal automatizable del v1.')
    return config


def generate_dte_draft(payment, tipo_dte='34'):
    if tipo_dte != TipoDTE.FACTURA_EXENTA:
        raise ValueError('La emision desde pago mensual solo soporta DTE tipo 34 (Factura Exenta).')
    if payment.estado_pago not in {'pagado', 'pagado_via_repactacion', 'pagado_por_acuerdo_termino'}:
        raise ValueError('Solo se puede generar DTE desde pagos efectivamente cobrados.')

    distributions = list(
        payment.distribuciones_cobro.filter(requiere_dte=True).select_related('beneficiario_empresa_owner')
    )
    if not distributions:
        raise ValueError('El pago no tiene una distribucion facturable configurada.')
    if len(distributions) > 1:
        raise ValueError('El boundary actual no soporta multiples distribuciones facturables por un mismo pago.')

    distribution = distributions[0]
    empresa = distribution.beneficiario_empresa_owner
    capability = get_active_dte_capability(empresa)
    validate_company_fiscal_readiness(empresa)

    dte = DTEEmitido.objects.filter(pago_mensual=payment).first()
    if dte:
        return dte, False

    dte = DTEEmitido.objects.create(
        empresa=empresa,
        capacidad_tributaria=capability,
        contrato=payment.contrato,
        pago_mensual=payment,
        distribucion_cobro_mensual=distribution,
        arrendatario=payment.contrato.arrendatario,
        tipo_dte=tipo_dte,
        monto_neto_clp=distribution.monto_facturable_clp,
        fecha_emision=payment.fecha_deposito_banco or payment.fecha_deteccion_sistema or timezone.localdate(),
        estado_dte=EstadoDTE.DRAFT,
    )
    return dte, True


def register_dte_status(dte, *, estado_dte, sii_track_id='', ultimo_estado_sii='', observaciones=''):
    input_track_id = _ensure_non_sensitive_reference(sii_track_id, 'sii_track_id')
    input_observaciones = _ensure_non_sensitive_text(observaciones, 'observaciones')
    next_track_id = input_track_id or dte.sii_track_id
    next_sii_status = str(ultimo_estado_sii or '').strip() or dte.ultimo_estado_sii
    if estado_dte in DTE_EXTERNAL_STATES:
        if not next_track_id:
            raise ValueError('Actualizar estado SII controlado requiere sii_track_id trazable.')
        _ensure_non_sensitive_reference(next_track_id, 'sii_track_id')
        if estado_dte in DTE_STATUS_QUERY_STATES and not next_sii_status:
            raise ValueError('Actualizar aceptacion/rechazo/anulacion requiere ultimo_estado_sii trazable.')
        if estado_dte in DTE_STATUS_QUERY_STATES:
            get_active_dte_status_capability(dte.empresa)
        else:
            ensure_sii_capability_ready(dte.capacidad_tributaria, dte.capacidad_tributaria.capacidad_key)

    dte.estado_dte = estado_dte
    if input_track_id:
        dte.sii_track_id = input_track_id
    if ultimo_estado_sii:
        dte.ultimo_estado_sii = ultimo_estado_sii
    if input_observaciones:
        dte.observaciones = input_observaciones
    if estado_dte in DTE_EXTERNAL_STATES:
        _ensure_artifact_valid_for_status_transition(dte, 'DTE')
    dte.save(update_fields=['estado_dte', 'sii_track_id', 'ultimo_estado_sii', 'observaciones', 'updated_at'])
    return dte


def get_active_f29_capability(empresa):
    capability = empresa.capacidades_sii.filter(capacidad_key=CapacidadSII.F29_PREPARACION).first()
    if not capability:
        raise ValueError('La empresa no tiene configurada la capacidad F29Preparacion.')
    return ensure_sii_capability_ready(capability, CapacidadSII.F29_PREPARACION)


def generate_f29_draft(empresa, anio, mes):
    capability = get_active_f29_capability(empresa)
    config = validate_company_fiscal_readiness(empresa)

    close = empresa.cierres_mensuales_contables.filter(anio=anio, mes=mes).first()
    if not close or close.estado != 'aprobado':
        raise ValueError('F29Preparacion requiere un cierre mensual contable aprobado para el periodo.')

    obligations = list(
        ObligacionTributariaMensual.objects.filter(empresa=empresa, anio=anio, mes=mes).order_by('obligacion_tipo')
    )
    if not obligations:
        raise ValueError('No existen obligaciones tributarias mensuales para preparar el F29.')

    states = {obligation.estado_preparacion for obligation in obligations}
    draft_state = (
        EstadoPreparacionTributaria.PREPARED
        if states.issubset({EstadoPreparacionTributaria.PREPARED, EstadoPreparacionTributaria.APPROVED})
        else EstadoPreparacionTributaria.PENDING_DATA
    )

    draft, created = F29PreparacionMensual.objects.get_or_create(
        empresa=empresa,
        anio=anio,
        mes=mes,
        defaults={
            'capacidad_tributaria': capability,
            'cierre_mensual': close,
            'estado_preparacion': draft_state,
        },
    )
    draft.capacidad_tributaria = capability
    draft.cierre_mensual = close
    draft.estado_preparacion = draft_state
    draft.resumen_formulario = {
        'empresa_id': empresa.id,
        'regimen_tributario': config.regimen_tributario.codigo_regimen,
        'obligaciones': [
            {
                'tipo': obligation.obligacion_tipo,
                'base_imponible': str(obligation.base_imponible),
                'monto_calculado': str(obligation.monto_calculado),
                'estado_preparacion': obligation.estado_preparacion,
            }
            for obligation in obligations
        ],
    }
    draft.save()
    return draft, created


def register_f29_status(draft, *, estado_preparacion, borrador_ref='', responsable_revision_ref='', observaciones=''):
    if estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
        raise ValueError('SII.F29Presentacion requiere gate propio y no se registra desde preparacion local.')
    input_ref = _ensure_non_sensitive_reference(borrador_ref, 'borrador_ref')
    input_responsable = _ensure_non_sensitive_reference(responsable_revision_ref, 'responsable_revision_ref')
    input_observaciones = _ensure_non_sensitive_text(observaciones, 'observaciones')
    next_ref = input_ref or draft.borrador_ref
    next_responsable = input_responsable or draft.responsable_revision_ref
    if estado_preparacion in TAX_STATUS_REQUIRING_GATE:
        ensure_sii_capability_ready(draft.capacidad_tributaria, draft.capacidad_tributaria.capacidad_key)
    if estado_preparacion in TAX_STATUS_REQUIRING_REF:
        if not next_ref:
            raise ValueError('Aprobar u observar F29 requiere borrador_ref trazable.')
        _ensure_non_sensitive_reference(next_ref, 'borrador_ref')
        if not next_responsable:
            raise ValueError('Aprobar u observar F29 requiere responsable_revision_ref trazable.')
        _ensure_non_sensitive_reference(next_responsable, 'responsable_revision_ref')

    draft.estado_preparacion = estado_preparacion
    if input_ref:
        draft.borrador_ref = input_ref
    if input_responsable:
        draft.responsable_revision_ref = input_responsable
    if input_observaciones:
        draft.observaciones = input_observaciones
    if estado_preparacion in TAX_STATUS_REQUIRING_GATE:
        _ensure_artifact_valid_for_status_transition(draft, 'F29')
    draft.save(update_fields=['estado_preparacion', 'borrador_ref', 'responsable_revision_ref', 'observaciones', 'updated_at'])
    return draft


def get_active_annual_capability(empresa, capability_key):
    capability = empresa.capacidades_sii.filter(capacidad_key=capability_key).first()
    if not capability:
        raise ValueError(f'La empresa no tiene configurada la capacidad {capability_key}.')
    return ensure_sii_capability_ready(capability, capability_key)


def _tax_mapping_counts_by_target(rule_set):
    counts = {}
    for mapping in rule_set.code_mappings.filter(estado=EstadoRegistro.ACTIVE).order_by('destino'):
        counts[mapping.destino] = counts.get(mapping.destino, 0) + 1
    return counts


def get_approved_tax_year_rule_set(config, anio_tributario):
    rule_set = (
        TaxYearRuleSet.objects.filter(
            anio_tributario=anio_tributario,
            regimen_tributario=config.regimen_tributario,
            estado=EstadoReglaTributariaAnual.APPROVED,
        )
        .select_related('regimen_tributario')
        .first()
    )
    if not rule_set:
        raise ValueError('La preparacion anual requiere TaxYearRuleSet aprobado para el año tributario y regimen fiscal.')
    try:
        rule_set.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'TaxYearRuleSet aprobado no cumple validacion de dominio: {reason}') from error

    active_mappings = list(
        TaxCodeMapping.objects.filter(rule_set=rule_set, estado=EstadoRegistro.ACTIVE).select_related('rule_set')
    )
    if not active_mappings:
        raise ValueError('TaxYearRuleSet aprobado requiere al menos un TaxCodeMapping activo y trazable.')
    for mapping in active_mappings:
        try:
            mapping.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'TaxCodeMapping activo no cumple validacion de dominio: {reason}') from error
    return rule_set


def _canonical_source_payload(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)


def _source_bundle_hash(payload):
    return hashlib.sha256(_canonical_source_payload(payload).encode('utf-8')).hexdigest()


def _metadata_real_estate_contribution_values(source):
    if source is None or not isinstance(source.metadata, dict):
        return {}
    values = (
        source.metadata.get('values_by_property_id')
        or source.metadata.get('real_estate_contributions_by_property_id')
        or {}
    )
    return values if isinstance(values, dict) else {}


def _find_real_estate_contribution_source_for_year(anio_tributario, regime_code=''):
    candidates = (
        AnnualTaxOfficialSource.objects.filter(
            anio_tributario=anio_tributario,
            estado__in=ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES,
        )
        .filter(
            Q(source_type=TipoAnnualTaxOfficialSource.SII_REAL_ESTATE_CONTRIBUTIONS)
            | Q(
                source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
                applies_to__in=[
                    DestinoMapeoTributarioAnual.F22,
                    DestinoMapeoTributarioAnual.DOSSIER,
                ],
            )
        )
        .filter(Q(regime_code='') | Q(regime_code=regime_code))
        .order_by('source_type', 'source_key', 'id')
    )
    for source in candidates:
        if source.source_type == TipoAnnualTaxOfficialSource.SII_REAL_ESTATE_CONTRIBUTIONS:
            return source
        if isinstance(source.metadata, dict) and source.metadata.get('real_estate_contributions') is True:
            return source
    return None


def _source_matches_f22_export_format(source):
    if source is None:
        return False
    if has_text(source.applies_to) and source.applies_to != DestinoMapeoTributarioAnual.F22:
        return False
    if has_text(source.form_code) and str(source.form_code).strip() != 'F22':
        return False
    if source.source_type == TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION:
        return True
    metadata = source.metadata if isinstance(source.metadata, dict) else {}
    return (
        source.source_type == TipoAnnualTaxOfficialSource.EXPERT_REVIEW
        and (
            metadata.get('f22_export_format') is True
            or metadata.get('f22_certification') is True
        )
    )


def _find_f22_export_format_source_for_year(anio_tributario, regime_code=''):
    candidates = list(
        AnnualTaxOfficialSource.objects.filter(
            anio_tributario=anio_tributario,
            estado__in=ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES,
        )
        .filter(
            Q(source_type=TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION)
            | Q(
                source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
                applies_to=DestinoMapeoTributarioAnual.F22,
            )
        )
        .filter(Q(applies_to='') | Q(applies_to=DestinoMapeoTributarioAnual.F22))
        .filter(Q(regime_code='') | Q(regime_code=regime_code))
        .order_by('source_type', 'source_key', 'id')
    )
    for source in candidates:
        if source.source_type == TipoAnnualTaxOfficialSource.SII_F22_CERTIFICATION and _source_matches_f22_export_format(source):
            return source
    for source in candidates:
        if _source_matches_f22_export_format(source):
            return source
    return None


def _f22_export_format_summary(source):
    return {
        'source': 'official_or_expert_review' if source else 'not_loaded_v1',
        'official_source_id': source.id if source else None,
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
        'requires_official_format_gate': True,
        'requires_explicit_submission_authorization': True,
    }


def build_annual_tax_source_summary(empresa, fiscal_year, config, rule_set):
    approved_closes = CierreMensualContable.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
        estado=EstadoCierreMensual.APPROVED,
    ).order_by('mes')
    obligations = ObligacionTributariaMensual.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
    ).order_by('mes', 'obligacion_tipo')
    f29s = F29PreparacionMensual.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
    ).order_by('mes')
    rent_distributions = DistribucionCobroMensual.objects.filter(
        beneficiario_empresa_owner=empresa,
        pago_mensual__anio=fiscal_year,
    ).select_related('pago_mensual')
    real_estate_properties = Propiedad.objects.filter(
        Q(empresa_owner=empresa)
        | Q(
            contrato_propiedades__contrato__pagos_mensuales__distribuciones_cobro__beneficiario_empresa_owner=empresa,
            contrato_propiedades__contrato__pagos_mensuales__anio=fiscal_year,
        ),
        estado='activa',
    ).distinct()
    real_estate_contribution_source = _find_real_estate_contribution_source_for_year(
        rule_set.anio_tributario,
        config.regimen_tributario.codigo_regimen,
    )
    real_estate_contribution_values = _metadata_real_estate_contribution_values(real_estate_contribution_source)
    f22_export_format_source = _find_f22_export_format_source_for_year(
        rule_set.anio_tributario,
        config.regimen_tributario.codigo_regimen,
    )
    liquidation_lines = LineaLiquidacionMensual.objects.filter(
        liquidacion__owner_tipo=TipoOwnerLiquidacion.COMPANY,
        liquidacion__empresa=empresa,
        liquidacion__anio=fiscal_year,
        liquidacion__estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED],
    ).select_related('liquidacion')
    monthly_facts = MonthlyTaxFact.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
        estado=EstadoMonthlyTaxFact.NORMALIZED,
    ).order_by('mes')
    obligation_months = sorted(set(obligations.values_list('mes', flat=True)))
    obligation_total = sum((item.monto_calculado for item in obligations), 0)
    f29_traceable_states = {
        EstadoPreparacionTributaria.PREPARED,
        EstadoPreparacionTributaria.APPROVED,
        EstadoPreparacionTributaria.OBSERVED,
        EstadoPreparacionTributaria.RECTIFIED,
    }
    return {
        'empresa_id': empresa.id,
        'anio_comercial': fiscal_year,
        'regimen_tributario': config.regimen_tributario.codigo_regimen,
        'moneda_funcional': config.moneda_funcional,
        'approved_close_months': list(approved_closes.values_list('mes', flat=True)),
        'approved_closes_total': approved_closes.count(),
        'obligation_months': obligation_months,
        'obligations_total': obligations.count(),
        'obligations_total_amount': str(obligation_total),
        'obligations_by_type': sorted(set(obligations.values_list('obligacion_tipo', flat=True))),
        'monthly_tax_fact_months': sorted(set(monthly_facts.values_list('mes', flat=True))),
        'monthly_tax_facts_total': monthly_facts.count(),
        'f29_preparations_total': f29s.count(),
        'f29_traceable_months': sorted(
            set(
                f29s.filter(estado_preparacion__in=f29_traceable_states)
                .values_list('mes', flat=True)
            )
        ),
        'rent_distribution_months': sorted(set(rent_distributions.values_list('pago_mensual__mes', flat=True))),
        'rent_distributions_total': rent_distributions.count(),
        'rent_distributions_total_devengado': str(
            sum((item.monto_devengado_clp for item in rent_distributions), 0)
        ),
        'real_estate_properties_total': real_estate_properties.count(),
        'real_estate_property_ids': list(real_estate_properties.order_by('codigo_propiedad', 'id').values_list('id', flat=True)),
        'real_estate_contribuciones': {
            'source': 'official_or_expert_review' if real_estate_contribution_source else 'not_loaded_v1',
            'official_source_id': real_estate_contribution_source.id if real_estate_contribution_source else None,
            'values_by_property_id': real_estate_contribution_values,
            'final_tax_calculation': False,
        },
        'f22_export_format': _f22_export_format_summary(f22_export_format_source),
        'liquidation_line_months': sorted(set(liquidation_lines.values_list('liquidacion__mes', flat=True))),
        'liquidation_lines_total': liquidation_lines.count(),
        'liquidation_lines_total_amount': str(sum((item.monto_clp for item in liquidation_lines), 0)),
        'tax_year_rule_set': {
            'id': rule_set.id,
            'anio_tributario': rule_set.anio_tributario,
            'regimen_tributario': rule_set.regimen_tributario.codigo_regimen,
            'version': rule_set.version,
            'hash_normativo': rule_set.hash_normativo,
            'active_mapping_count': rule_set.code_mappings.filter(estado=EstadoRegistro.ACTIVE).count(),
            'mapeos_activos_por_destino': _tax_mapping_counts_by_target(rule_set),
        },
    }


def _f29_total_from_summary(summary):
    if not isinstance(summary, dict):
        return Decimal('0.00')
    obligations = summary.get('obligaciones')
    if not isinstance(obligations, list):
        return Decimal('0.00')
    total = Decimal('0.00')
    for item in obligations:
        if not isinstance(item, dict):
            continue
        raw_amount = item.get('monto_calculado') or '0.00'
        try:
            total += Decimal(str(raw_amount))
        except Exception:
            continue
    return total


def _sum_decimal(values):
    total = Decimal('0.00')
    for value in values:
        total += Decimal(str(value or '0.00'))
    return total


MONTHLY_FACT_SOURCE_METRICS = {
    'monthly_tax_facts.obligations_total_amount': 'obligations_total_amount',
    'monthly_tax_facts.rent_distributions_total_devengado': 'rent_distributions_total_devengado',
    'monthly_tax_facts.liquidation_lines_total_amount': 'liquidation_lines_total_amount',
}

TRIAL_BALANCE_SOURCE_METRICS = {
    'annual_trial_balance.sumas_debe_clp': 'sumas_debe_clp',
    'annual_trial_balance.sumas_haber_clp': 'sumas_haber_clp',
    'annual_trial_balance.saldo_deudor_clp': 'saldo_deudor_clp',
    'annual_trial_balance.saldo_acreedor_clp': 'saldo_acreedor_clp',
    'annual_trial_balance.inventario_activo_clp': 'inventario_activo_clp',
    'annual_trial_balance.inventario_pasivo_clp': 'inventario_pasivo_clp',
    'annual_trial_balance.resultado_perdida_clp': 'resultado_perdida_clp',
    'annual_trial_balance.resultado_ganancia_clp': 'resultado_ganancia_clp',
}

TRIAL_BALANCE_ROW_KEYS = (
    'lineas_balance_8_columnas',
    'eight_column_lines',
    'trial_balance_lines',
    'lines',
    'cuentas',
)


def _metadata_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        return []
    normalized = []
    for item in items:
        text = str(item or '').strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _decimal_from_monthly_payload(payload, key):
    if not isinstance(payload, dict):
        return Decimal('0.00')
    try:
        return Decimal(str(payload.get(key) or '0.00'))
    except Exception:
        return Decimal('0.00')


def _decimal_from_row(payload, *keys):
    if not isinstance(payload, dict):
        return Decimal('0.00')
    for key in keys:
        if key not in payload:
            continue
        try:
            return Decimal(str(payload.get(key) or '0.00'))
        except Exception:
            return Decimal('0.00')
    return Decimal('0.00')


def _balance_rows_from_summary(summary):
    if not isinstance(summary, dict):
        return []
    for key in TRIAL_BALANCE_ROW_KEYS:
        rows = summary.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    return []


def _text_from_row(payload, *keys):
    if not isinstance(payload, dict):
        return ''
    for key in keys:
        value = str(payload.get(key) or '').strip()
        if value:
            return value
    return ''


def _trial_balance_official_source(rule_set):
    ready_states = {
        EstadoAnnualTaxOfficialSource.REVIEWED,
        EstadoAnnualTaxOfficialSource.APPROVED,
    }
    regime_code = getattr(rule_set.regimen_tributario, 'codigo_regimen', '')
    candidates = AnnualTaxOfficialSource.objects.filter(
        anio_tributario=rule_set.anio_tributario,
        estado__in=ready_states,
        source_type__in=[
            TipoAnnualTaxOfficialSource.SII_DJ1847_INSTRUCTIONS,
            TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
        ],
    ).filter(
        Q(regime_code='') | Q(regime_code=regime_code)
    ).order_by('source_type', 'source_key', 'id')
    source = candidates.first()
    if source:
        return source
    if rule_set.official_source_id and rule_set.official_source.estado in ready_states:
        return rule_set.official_source
    return None


def _line_amount_from_mapping(mapping, monthly_facts, trial_balance=None):
    metadata = mapping.metadata if isinstance(mapping.metadata, dict) else {}
    source_metric = str(metadata.get('source_metric') or '').strip()
    warnings = []
    if source_metric in TRIAL_BALANCE_SOURCE_METRICS:
        amount_field = TRIAL_BALANCE_SOURCE_METRICS[source_metric]
        classifier = str(metadata.get('trial_balance_classifier') or '').strip()
        classifiers = _metadata_string_list(metadata.get('trial_balance_classifiers')) or (
            [classifier] if classifier else []
        )
        if trial_balance is None:
            warnings.append('annual_tax_trial_balance_missing')
            return Decimal('0.00'), source_metric, warnings, {
                'source': 'annual_tax_trial_balance',
                'source_metric': source_metric,
                'amount_field': amount_field,
                'trial_balance_classifier': classifier,
                'trial_balance_classifiers': classifiers,
            }
        if not classifiers:
            warnings.append('trial_balance_classifier_missing')
            return Decimal('0.00'), source_metric, warnings, {
                'source': 'annual_tax_trial_balance',
                'source_metric': source_metric,
                'amount_field': amount_field,
                'trial_balance_id': trial_balance.id,
                'trial_balance_hash': trial_balance.hash_balance,
            }
        lines = list(
            trial_balance.lines.filter(
                estado=EstadoRegistro.ACTIVE,
                clasificador_dj1847__in=classifiers,
            ).order_by('codigo_cuenta', 'id')
        )
        amount = _sum_decimal(getattr(line, amount_field) for line in lines)
        if not lines:
            warnings.append('trial_balance_classifier_without_lines')
        return amount, source_metric, warnings, {
            'source': 'annual_tax_trial_balance',
            'source_metric': source_metric,
            'amount_field': amount_field,
            'trial_balance_id': trial_balance.id,
            'trial_balance_hash': trial_balance.hash_balance,
            'trial_balance_classifier': classifier,
            'trial_balance_classifiers': classifiers,
            'trial_balance_line_ids': [line.id for line in lines],
        }

    if source_metric not in MONTHLY_FACT_SOURCE_METRICS:
        warnings.append('source_metric_missing_or_unsupported')
        return Decimal('0.00'), source_metric, warnings, {
            'source': 'unknown',
            'source_metric': source_metric,
        }

    payload_key = MONTHLY_FACT_SOURCE_METRICS[source_metric]
    amount = Decimal('0.00')
    months = []
    for fact in monthly_facts:
        amount += _decimal_from_monthly_payload(fact.resumen_hecho, payload_key)
        months.append(fact.mes)
    if sorted(set(months)) != list(range(1, 13)):
        warnings.append('monthly_tax_facts_not_complete')
    return amount, source_metric, warnings, {
        'source': 'monthly_tax_facts',
        'source_metric': source_metric,
        'monthly_tax_fact_ids': [fact.id for fact in monthly_facts],
        'months': months,
    }


def _line_hash_payload(line_payload):
    return hashlib.sha256(_canonical_source_payload(line_payload).encode('utf-8')).hexdigest()


def _workbook_line_hash_payload(line):
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


def _annual_tax_workbook_warning_counts(active_lines):
    warning_count = 0
    warning_reviewed_count = 0
    warning_pending_review_count = 0
    for line in active_lines:
        warnings = line.warnings if isinstance(line.warnings, list) else []
        warning_count += len(warnings)
        if warnings and is_non_sensitive_reference(line.warning_review_ref):
            warning_reviewed_count += len(warnings)
        elif warnings:
            warning_pending_review_count += len(warnings)
    return warning_count, warning_reviewed_count, warning_pending_review_count


def sync_annual_tax_trial_balance(process, rule_set, source_bundle):
    fiscal_year = process.anio_tributario - 1
    periodo_cierre = f'{fiscal_year}-12'
    source_balance = (
        BalanceComprobacion.objects.filter(
            empresa=process.empresa,
            periodo=periodo_cierre,
            estado_snapshot=EstadoCierreMensual.APPROVED,
        )
        .order_by('-updated_at', '-id')
        .first()
    )
    if source_balance is None:
        AnnualTaxTrialBalance.objects.filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        ).update(estado=EstadoAnnualTaxTrialBalance.RETIRED)
        return None

    official_source = _trial_balance_official_source(rule_set)
    if official_source is None:
        AnnualTaxTrialBalance.objects.filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        ).update(estado=EstadoAnnualTaxTrialBalance.RETIRED)
        return None

    trial_balance, _ = AnnualTaxTrialBalance.objects.update_or_create(
        proceso_renta_anual=process,
        defaults={
            'empresa': process.empresa,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'official_source': official_source,
            'source_balance': source_balance,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': fiscal_year,
            'periodo_cierre': periodo_cierre,
            'source_ref': f'annual-tax-trial-balance-{process.empresa_id}-at{process.anio_tributario}',
            'responsible_ref': 'system-annual-tax-trial-balance-normalizer',
            'estado': EstadoAnnualTaxTrialBalance.DRAFT,
        },
    )

    active_line_ids = []
    summary = source_balance.resumen if isinstance(source_balance.resumen, dict) else {}
    rows = _balance_rows_from_summary(summary)
    accounts_by_code = {
        account.codigo: account
        for account in CuentaContable.objects.filter(
            empresa=process.empresa,
            estado=EstadoRegistro.ACTIVE,
        ).order_by('codigo')
    }
    missing_account_rows = 0
    for index, row in enumerate(rows, start=1):
        account_code = _text_from_row(row, 'codigo_cuenta', 'cuenta_codigo', 'codigo', 'account_code')
        account = accounts_by_code.get(account_code)
        if account is None:
            missing_account_rows += 1
            continue
        classifier = _text_from_row(
            row,
            'clasificador_dj1847',
            'codigo_dj1847',
            'dj1847_classifier',
            'tax_classifier',
            'clasificador',
        )
        warnings = []
        if not classifier:
            classifier = 'dj1847-classifier-pending'
            warnings.append('dj1847_classifier_missing')
        line_source_payload = {
            'source': 'balance_comprobacion',
            'source_balance_id': source_balance.id,
            'source_balance_periodo': source_balance.periodo,
            'row_index': index,
            'codigo_cuenta': account.codigo,
            'clasificador_dj1847': classifier,
        }
        line_payload = {
            'trial_balance_id': trial_balance.id,
            'cuenta_contable_id': account.id,
            'codigo_cuenta': account.codigo,
            'nombre_cuenta': account.nombre,
            'clasificador_dj1847': classifier,
            'sumas_debe_clp': str(_decimal_from_row(row, 'sumas_debe_clp', 'debe', 'debitos')),
            'sumas_haber_clp': str(_decimal_from_row(row, 'sumas_haber_clp', 'haber', 'creditos')),
            'saldo_deudor_clp': str(_decimal_from_row(row, 'saldo_deudor_clp', 'saldo_deudor')),
            'saldo_acreedor_clp': str(_decimal_from_row(row, 'saldo_acreedor_clp', 'saldo_acreedor')),
            'inventario_activo_clp': str(_decimal_from_row(row, 'inventario_activo_clp', 'activo')),
            'inventario_pasivo_clp': str(_decimal_from_row(row, 'inventario_pasivo_clp', 'pasivo')),
            'resultado_perdida_clp': str(_decimal_from_row(row, 'resultado_perdida_clp', 'perdida')),
            'resultado_ganancia_clp': str(_decimal_from_row(row, 'resultado_ganancia_clp', 'ganancia')),
            'formula_ref': _text_from_row(row, 'formula_ref') or f'dj1847-balance-line-at{process.anio_tributario}',
            'evidencia_ref': _text_from_row(row, 'evidencia_ref') or f'balance-comprobacion-{source_balance.periodo}-{source_balance.id}',
            'warnings': warnings,
            'source_payload': line_source_payload,
        }
        line, _ = AnnualTaxTrialBalanceLine.objects.update_or_create(
            trial_balance=trial_balance,
            codigo_cuenta=account.codigo,
            defaults={
                'cuenta_contable': account,
                'nombre_cuenta': account.nombre,
                'clasificador_dj1847': classifier,
                'sumas_debe_clp': Decimal(line_payload['sumas_debe_clp']),
                'sumas_haber_clp': Decimal(line_payload['sumas_haber_clp']),
                'saldo_deudor_clp': Decimal(line_payload['saldo_deudor_clp']),
                'saldo_acreedor_clp': Decimal(line_payload['saldo_acreedor_clp']),
                'inventario_activo_clp': Decimal(line_payload['inventario_activo_clp']),
                'inventario_pasivo_clp': Decimal(line_payload['inventario_pasivo_clp']),
                'resultado_perdida_clp': Decimal(line_payload['resultado_perdida_clp']),
                'resultado_ganancia_clp': Decimal(line_payload['resultado_ganancia_clp']),
                'formula_ref': line_payload['formula_ref'],
                'evidencia_ref': line_payload['evidencia_ref'],
                'warnings': warnings,
                'source_payload': line_source_payload,
                'hash_linea': _line_hash_payload(line_payload),
                'estado': EstadoRegistro.ACTIVE,
            },
        )
        try:
            line.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'AnnualTaxTrialBalanceLine no cumple validacion de dominio: {reason}') from error
        line.save()
        active_line_ids.append(line.id)

    trial_balance.lines.exclude(id__in=active_line_ids).update(estado=EstadoRegistro.INACTIVE)
    active_lines = list(trial_balance.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_cuenta', 'id'))
    line_warning_count = sum(len(line.warnings or []) for line in active_lines if isinstance(line.warnings, list))
    warning_count = line_warning_count + missing_account_rows
    balance_summary = {
        'empresa_id': process.empresa_id,
        'proceso_renta_anual_id': process.id,
        'source_bundle_id': source_bundle.id,
        'rule_set_id': rule_set.id,
        'official_source_id': official_source.id,
        'source_balance_id': source_balance.id,
        'anio_tributario': process.anio_tributario,
        'anio_comercial': fiscal_year,
        'periodo_cierre': periodo_cierre,
        'lines_total': len(active_lines),
        'warnings_total': warning_count,
        'line_warnings_total': line_warning_count,
        'missing_account_rows': missing_account_rows,
        'line_hashes': [line.hash_linea for line in active_lines],
        'source': 'BalanceComprobacion + AnnualTaxOfficialSource',
        'final_tax_calculation': False,
    }
    trial_balance.lines_total = len(active_lines)
    trial_balance.warnings_total = warning_count
    trial_balance.resumen_balance = balance_summary
    trial_balance.hash_balance = _source_bundle_hash(balance_summary)
    trial_balance.estado = EstadoAnnualTaxTrialBalance.PREPARED
    try:
        trial_balance.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxTrialBalance no cumple validacion de dominio: {reason}') from error
    trial_balance.save()
    return trial_balance


def _controlled_no_declaration_f29_payload(existing_fact: MonthlyTaxFact | None) -> dict | None:
    if existing_fact is None or not isinstance(existing_fact.resumen_hecho, dict):
        return None
    f29_payload = existing_fact.resumen_hecho.get('f29')
    if not isinstance(f29_payload, dict):
        return None
    resumen = f29_payload.get('resumen')
    if (
        f29_payload.get('estado_preparacion') == EstadoPreparacionTributaria.NOT_APPLICABLE
        and isinstance(resumen, dict)
        and resumen.get('no_declaration') is True
    ):
        return {
            'estado_preparacion': EstadoPreparacionTributaria.NOT_APPLICABLE,
            'resumen': {
                'no_declaration': True,
                'source': str(resumen.get('source') or 'preserved_monthly_tax_fact'),
            },
        }
    return None


def sync_monthly_tax_facts(empresa, fiscal_year):
    closes = CierreMensualContable.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
        estado=EstadoCierreMensual.APPROVED,
    ).order_by('mes', 'id')
    normalized_facts = []

    for close in closes:
        obligations = list(
            ObligacionTributariaMensual.objects.filter(
                empresa=empresa,
                anio=fiscal_year,
                mes=close.mes,
            ).order_by('obligacion_tipo', 'id')
        )
        f29 = F29PreparacionMensual.objects.filter(
            empresa=empresa,
            anio=fiscal_year,
            mes=close.mes,
        ).order_by('-id').first()
        existing_fact = MonthlyTaxFact.objects.filter(
            empresa=empresa,
            anio=fiscal_year,
            mes=close.mes,
        ).first()
        controlled_no_declaration_f29 = None if f29 else _controlled_no_declaration_f29_payload(existing_fact)
        distributions = list(
            DistribucionCobroMensual.objects.filter(
                beneficiario_empresa_owner=empresa,
                pago_mensual__anio=fiscal_year,
                pago_mensual__mes=close.mes,
            ).select_related('pago_mensual').order_by('id')
        )
        liquidation_lines = list(
            LineaLiquidacionMensual.objects.filter(
                liquidacion__owner_tipo=TipoOwnerLiquidacion.COMPANY,
                liquidacion__empresa=empresa,
                liquidacion__anio=fiscal_year,
                liquidacion__mes=close.mes,
                liquidacion__estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED],
            ).select_related('liquidacion').order_by('id')
        )
        liquidation = liquidation_lines[0].liquidacion if liquidation_lines else None
        close_summary = close.resumen_obligaciones if isinstance(close.resumen_obligaciones, dict) else {}
        f29_summary = f29.resumen_formulario if f29 and isinstance(f29.resumen_formulario, dict) else {}
        payload = {
            'empresa_id': empresa.id,
            'anio': fiscal_year,
            'mes': close.mes,
            'cierre_mensual_id': close.pk,
            'cierre_estado': close.estado,
            'cierre_resumen_keys': sorted(close_summary.keys()),
            'obligations_total': len(obligations),
            'obligations_total_amount': str(_sum_decimal(obligation.monto_calculado for obligation in obligations)),
            'obligations': [
                {
                    'id': obligation.pk,
                    'tipo': obligation.obligacion_tipo,
                    'base_imponible': str(obligation.base_imponible),
                    'monto_calculado': str(obligation.monto_calculado),
                    'estado_preparacion': obligation.estado_preparacion,
                }
                for obligation in obligations
            ],
            'f29_preparacion': {
                'id': f29.pk,
                'estado_preparacion': f29.estado_preparacion,
                'has_borrador_ref': bool(f29.borrador_ref),
                'resumen_formulario_keys': sorted(f29_summary.keys()),
                'total_obligaciones_formulario': str(_f29_total_from_summary(f29_summary)),
            } if f29 else None,
            'rent_distributions_total': len(distributions),
            'rent_distributions_total_devengado': str(
                _sum_decimal(distribution.monto_devengado_clp for distribution in distributions)
            ),
            'rent_distributions': [
                {
                    'id': distribution.pk,
                    'pago_mensual_id': distribution.pago_mensual_id,
                    'monto_devengado_clp': str(distribution.monto_devengado_clp),
                    'monto_conciliado_clp': str(distribution.monto_conciliado_clp),
                    'monto_facturable_clp': str(distribution.monto_facturable_clp),
                    'requiere_dte': distribution.requiere_dte,
                    'origen_atribucion': distribution.origen_atribucion,
                }
                for distribution in distributions
            ],
            'liquidation_lines_total': len(liquidation_lines),
            'liquidation_lines_total_amount': str(
                _sum_decimal(line.monto_clp for line in liquidation_lines)
            ),
            'liquidation_lines': [
                {
                    'id': line.pk,
                    'liquidacion_id': line.liquidacion_id,
                    'tipo_linea': line.tipo_linea,
                    'monto_clp': str(line.monto_clp),
                    'has_evidencia_ref': bool(line.evidencia_ref),
                }
                for line in liquidation_lines
            ],
        }
        if controlled_no_declaration_f29 is not None:
            payload['f29'] = controlled_no_declaration_f29
        fact, _ = MonthlyTaxFact.objects.update_or_create(
            empresa=empresa,
            anio=fiscal_year,
            mes=close.mes,
            defaults={
                'cierre_mensual': close,
                'f29_preparacion': f29,
                'liquidacion_mensual': liquidation,
                'source_ref': f'monthly-tax-fact-{empresa.id}-{fiscal_year}-{close.mes:02d}',
                'responsible_ref': 'system-monthly-tax-normalizer',
                'resumen_hecho': payload,
                'hash_hecho': _source_bundle_hash(payload),
                'estado': EstadoMonthlyTaxFact.NORMALIZED,
            },
        )
        try:
            fact.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'MonthlyTaxFact no cumple validacion de dominio: {reason}') from error
        fact.save()
        normalized_facts.append(fact)

    MonthlyTaxFact.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
        estado=EstadoMonthlyTaxFact.NORMALIZED,
    ).exclude(pk__in=[fact.pk for fact in normalized_facts]).update(estado=EstadoMonthlyTaxFact.RETIRED)
    return normalized_facts


def summarize_annual_tax_trial_balances(process):
    trial_balances = AnnualTaxTrialBalance.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxTrialBalance.PREPARED,
    ).order_by('id')
    by_id = {}
    for trial_balance in trial_balances:
        active_lines = trial_balance.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_cuenta', 'id')
        warning_count = 0
        for line in active_lines:
            warnings = line.warnings if isinstance(line.warnings, list) else []
            warning_count += len(warnings)
        warnings_total = max(trial_balance.warnings_total, warning_count)
        by_id[str(trial_balance.id)] = {
            'id': trial_balance.id,
            'hash_balance': trial_balance.hash_balance,
            'source_balance_id': trial_balance.source_balance_id,
            'official_source_id': trial_balance.official_source_id,
            'periodo_cierre': trial_balance.periodo_cierre,
            'lines_total': active_lines.count(),
            'warnings_total': warnings_total,
        }
    return {
        'total': trial_balances.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
    }


def summarize_annual_tax_workbooks(process):
    workbooks = AnnualTaxWorkbook.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
    ).order_by('tipo')
    by_type = {}
    for workbook in workbooks:
        active_lines = workbook.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'codigo_destino')
        warning_count = 0
        warning_reviewed_count = 0
        warning_pending_review_count = 0
        for line in active_lines:
            warnings = line.warnings if isinstance(line.warnings, list) else []
            warning_count += len(warnings)
            if warnings and is_non_sensitive_reference(line.warning_review_ref):
                warning_reviewed_count += len(warnings)
            elif warnings:
                warning_pending_review_count += len(warnings)
        by_type[workbook.tipo] = {
            'id': workbook.id,
            'hash_workbook': workbook.hash_workbook,
            'lines_total': active_lines.count(),
            'warnings_total': warning_count,
            'warnings_reviewed_total': warning_reviewed_count,
            'warnings_pending_review_total': warning_pending_review_count,
        }
    return {
        'total': workbooks.count(),
        'types': sorted(by_type.keys()),
        'by_type': by_type,
    }


def summarize_annual_enterprise_registers(process):
    registers = AnnualEnterpriseRegisterSet.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualEnterpriseRegister.PREPARED,
    ).order_by('tipo_registro')
    by_type = {}
    for register in registers:
        active_movements = register.movements.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'origen')
        warning_count = 0
        warning_reviewed_count = 0
        warning_pending_review_count = 0
        for movement in active_movements:
            warnings = movement.warnings if isinstance(movement.warnings, list) else []
            warning_count += len(warnings)
            if warnings and is_non_sensitive_reference(movement.warning_review_ref):
                warning_reviewed_count += len(warnings)
            elif warnings:
                warning_pending_review_count += len(warnings)
        by_type[register.tipo_registro] = {
            'id': register.id,
            'hash_registro': register.hash_registro,
            'saldo_inicial_clp': str(register.saldo_inicial_clp),
            'movimientos_total_clp': str(register.movimientos_total_clp),
            'saldo_final_clp': str(register.saldo_final_clp),
            'movements_total': active_movements.count(),
            'warnings_total': warning_count,
            'warnings_reviewed_total': warning_reviewed_count,
            'warnings_pending_review_total': warning_pending_review_count,
        }
    return {
        'total': registers.count(),
        'types': sorted(by_type.keys()),
        'by_type': by_type,
    }


def summarize_annual_real_estate_sections(process):
    sections = AnnualRealEstateSection.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualRealEstateSection.PREPARED,
    ).order_by('id')
    by_id = {}
    for section in sections:
        active_items = section.items.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_propiedad_snapshot', 'id')
        warning_count = 0
        for item in active_items:
            warnings = item.warnings if isinstance(item.warnings, list) else []
            warning_count += len(warnings)
        section_payload = section.resumen_seccion if isinstance(section.resumen_seccion, dict) else {}
        by_id[str(section.id)] = {
            'id': section.id,
            'hash_seccion': section.hash_seccion,
            'official_contribution_source_id': section.official_contribution_source_id,
            'propiedades_total': section.propiedades_total,
            'arriendo_devengado_total_clp': str(section.arriendo_devengado_total_clp),
            'arriendo_conciliado_total_clp': str(section.arriendo_conciliado_total_clp),
            'arriendo_facturable_total_clp': str(section.arriendo_facturable_total_clp),
            'contribuciones_total_clp': str(section.contribuciones_total_clp),
            'contribuciones_source': section_payload.get('contribuciones_source') or (
                'official_or_expert_review'
                if section.official_contribution_source_id
                else 'not_loaded_v1'
            ),
            'contribuciones_loaded_items_total': section_payload.get('contribuciones_loaded_items_total', 0),
            'contribuciones_missing_items_total': section_payload.get('contribuciones_missing_items_total', active_items.count()),
            'items_total': active_items.count(),
            'warnings_total': warning_count,
        }
    return {
        'total': sections.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
    }


def summarize_annual_tax_ddjj_layouts(process):
    try:
        config = process.empresa.configuracion_fiscal
    except ObjectDoesNotExist:
        config = None
    configured_forms = sorted(str(code) for code in (getattr(config, 'ddjj_habilitadas', None) or []))
    layouts = AnnualTaxDDJJFormLayout.objects.filter(
        anio_tributario=process.anio_tributario,
        form_code__in=configured_forms,
        estado=EstadoAnnualTaxDDJJLayout.PREPARED,
    ).order_by('form_code')
    by_form_code = {}
    warnings_total = 0
    for layout in layouts:
        warnings = layout.warnings if isinstance(layout.warnings, list) else []
        warnings_total += len(warnings)
        by_form_code[layout.form_code] = {
            'id': layout.id,
            'form_code': layout.form_code,
            'title': layout.title,
            'periodicidad': layout.periodicidad,
            'medio_preferente': layout.medio_preferente,
            'due_date_label': layout.due_date_label,
            'certificate_code': layout.certificate_code,
            'certificate_due_label': layout.certificate_due_label,
            'declaration_status': layout.declaration_status,
            'hash_layout': layout.hash_layout,
            'warnings_total': len(warnings),
        }
    return {
        'total': layouts.count(),
        'configured_form_codes': configured_forms,
        'form_codes': sorted(by_form_code.keys()),
        'missing_form_codes': sorted(set(configured_forms) - set(by_form_code.keys())),
        'warnings_total': warnings_total,
        'by_form_code': by_form_code,
    }


def summarize_annual_tax_f22_export_layouts(process):
    layouts = AnnualTaxF22ExportLayout.objects.filter(
        anio_tributario=process.anio_tributario,
        form_code='F22',
        estado=EstadoAnnualTaxF22ExportLayout.PREPARED,
    ).order_by('form_code')
    by_form_code = {}
    warnings_total = 0
    for layout in layouts:
        warnings = layout.warnings if isinstance(layout.warnings, list) else []
        warnings_total += len(warnings)
        by_form_code[layout.form_code] = {
            'id': layout.id,
            'form_code': layout.form_code,
            'title': layout.title,
            'medio_preferente': layout.medio_preferente,
            'allows_local_preview': layout.allows_local_preview,
            'allows_certified_file': layout.allows_certified_file,
            'allows_supervised_portal': layout.allows_supervised_portal,
            'official_certification_source_id': layout.official_certification_source_id,
            'official_instructions_source_id': layout.official_instructions_source_id,
            'hash_layout': layout.hash_layout,
            'warnings_total': len(warnings),
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
        }
    return {
        'total': layouts.count(),
        'form_codes': sorted(by_form_code.keys()),
        'missing_form_codes': [] if 'F22' in by_form_code else ['F22'],
        'warnings_total': warnings_total,
        'by_form_code': by_form_code,
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
    }


def summarize_annual_tax_artifact_matrices(process):
    matrices = AnnualTaxArtifactMatrix.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
    ).order_by('id')
    by_id = {}
    for matrix in matrices:
        active_items = matrix.items.filter(estado=EstadoRegistro.ACTIVE).order_by(
            'target_kind',
            'target_code',
            'source_kind',
            'source_model',
            'source_object_id',
        )
        warning_count = 0
        warning_reviewed_count = 0
        warning_pending_review_count = 0
        review_state_counts = {}
        for item in active_items:
            warnings = item.warnings if isinstance(item.warnings, list) else []
            warning_count += len(warnings)
            if (
                warnings
                and item.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
                and is_non_sensitive_reference(item.warning_review_ref)
            ):
                warning_reviewed_count += len(warnings)
            elif warnings:
                warning_pending_review_count += len(warnings)
            review_state_counts[item.review_state] = review_state_counts.get(item.review_state, 0) + 1
        by_id[str(matrix.id)] = {
            'id': matrix.id,
            'hash_matriz': matrix.hash_matriz,
            'items_total': matrix.items_total,
            'ddjj_items_total': matrix.ddjj_items_total,
            'f22_items_total': matrix.f22_items_total,
            'active_items_total': active_items.count(),
            'warnings_total': warning_count,
            'warnings_reviewed_total': warning_reviewed_count,
            'warnings_pending_review_total': warning_pending_review_count,
            'review_state_counts': dict(sorted(review_state_counts.items())),
        }
    return {
        'total': matrices.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
    }


def summarize_annual_tax_dossiers(process):
    dossiers = AnnualTaxDossier.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxDossier.PREPARED,
    ).order_by('id')
    by_id = {}
    for dossier in dossiers:
        summary = dossier.resumen_dossier if isinstance(dossier.resumen_dossier, dict) else {}
        by_id[str(dossier.id)] = {
            'id': dossier.id,
            'hash_dossier': dossier.hash_dossier,
            'artifact_matrix_id': dossier.artifact_matrix_id,
            'artifact_matrix_hash': summary.get('artifact_matrix_hash'),
            'review_state': dossier.review_state,
            'monthly_facts_total': dossier.monthly_facts_total,
            'workbooks_total': dossier.workbooks_total,
            'enterprise_registers_total': dossier.enterprise_registers_total,
            'real_estate_sections_total': dossier.real_estate_sections_total,
            'artifact_matrix_items_total': dossier.artifact_matrix_items_total,
            'warnings_total': dossier.warnings_total,
            'source_bundle_id': dossier.source_bundle_id,
            'rule_set_id': dossier.rule_set_id,
        }
    return {
        'total': dossiers.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
    }


def summarize_annual_tax_exports(process):
    exports = AnnualTaxExport.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxExport.PREPARED,
    ).order_by('id')
    by_id = {}
    for export in exports:
        payload = export.export_payload if isinstance(export.export_payload, dict) else {}
        by_id[str(export.id)] = {
            'id': export.id,
            'export_kind': export.export_kind,
            'hash_export': export.hash_export,
            'dossier_id': export.dossier_id,
            'dossier_hash': payload.get('dossier_hash'),
            'source_bundle_id': export.source_bundle_id,
            'rule_set_id': export.rule_set_id,
            'artifact_matrix_id': export.artifact_matrix_id,
            'official_format_source_id': export.official_format_source_id,
            'official_format_source': payload.get('official_format_source'),
            'f22_export_layout_id': payload.get('f22_export_layout_id'),
            'f22_export_layout_hash': payload.get('f22_export_layout_hash'),
            'f22_export_layout_medio': payload.get('f22_export_layout_medio'),
            'review_state': export.review_state,
            'target_items_total': export.target_items_total,
            'ddjj_items_total': export.ddjj_items_total,
            'f22_items_total': export.f22_items_total,
            'export_contracts_total': payload.get('export_contracts_total'),
            'ddjj_export_contracts_total': payload.get('ddjj_export_contracts_total'),
            'f22_export_contracts_total': payload.get('f22_export_contracts_total'),
            'export_files_total': payload.get('export_files_total'),
            'ddjj_export_files_total': payload.get('ddjj_export_files_total'),
            'f22_export_files_total': payload.get('f22_export_files_total'),
            'export_file_manifest_hash': payload.get('export_file_manifest_hash'),
            'warnings_total': export.warnings_total,
            'official_format': export.official_format,
            'sii_submission': export.sii_submission,
            'final_tax_calculation': export.final_tax_calculation,
        }
    return {
        'total': exports.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
    }


def summarize_annual_tax_review_checklists(process):
    checklists = AnnualTaxReviewChecklist.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxReviewChecklist.PREPARED,
    ).order_by('id')
    by_id = {}
    for checklist in checklists:
        by_id[str(checklist.id)] = {
            'id': checklist.id,
            'hash_checklist': checklist.hash_checklist,
            'dossier_id': checklist.dossier_id,
            'annual_export_id': checklist.annual_export_id,
            'source_bundle_id': checklist.source_bundle_id,
            'rule_set_id': checklist.rule_set_id,
            'artifact_matrix_id': checklist.artifact_matrix_id,
            'items_total': checklist.items_total,
            'completed_items_total': checklist.completed_items_total,
            'blockers_total': checklist.blockers_total,
            'warnings_total': checklist.warnings_total,
        }
    return {
        'total': checklists.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
    }


def _finalize_annual_tax_workbook(workbook):
    active_lines = list(workbook.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'codigo_destino'))
    warning_count, warning_reviewed_count, warning_pending_review_count = _annual_tax_workbook_warning_counts(active_lines)
    workbook_summary = {
        'empresa_id': workbook.empresa_id,
        'proceso_renta_anual_id': workbook.proceso_renta_anual_id,
        'source_bundle_id': workbook.source_bundle_id,
        'rule_set_id': workbook.rule_set_id,
        'anio_tributario': workbook.anio_tributario,
        'anio_comercial': workbook.anio_comercial,
        'tipo': workbook.tipo,
        'lines_total': len(active_lines),
        'warnings_total': warning_count,
        'warnings_reviewed_total': warning_reviewed_count,
        'warnings_pending_review_total': warning_pending_review_count,
        'line_hashes': [line.hash_linea for line in active_lines],
        'annual_tax_trial_balance_id': None,
        'annual_tax_trial_balance_hash': '',
        'source': 'TaxCodeMapping + MonthlyTaxFact + AnnualTaxTrialBalance',
        'final_tax_calculation': False,
    }
    trial_balance_ids = {
        payload.get('annual_tax_trial_balance_id')
        for line in active_lines
        for payload in [line.source_payload if isinstance(line.source_payload, dict) else {}]
        if payload.get('annual_tax_trial_balance_id')
    }
    trial_balance_hashes = {
        payload.get('annual_tax_trial_balance_hash')
        for line in active_lines
        for payload in [line.source_payload if isinstance(line.source_payload, dict) else {}]
        if payload.get('annual_tax_trial_balance_hash')
    }
    if len(trial_balance_ids) == 1:
        workbook_summary['annual_tax_trial_balance_id'] = next(iter(trial_balance_ids))
    if len(trial_balance_hashes) == 1:
        workbook_summary['annual_tax_trial_balance_hash'] = next(iter(trial_balance_hashes))
    workbook.resumen_workbook = workbook_summary
    workbook.hash_workbook = _source_bundle_hash(workbook_summary)
    workbook.estado = EstadoAnnualTaxWorkbook.PREPARED
    try:
        workbook.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxWorkbook no cumple validacion de dominio: {reason}') from error
    workbook.save()
    return workbook


def sync_annual_tax_workbooks(process, rule_set, source_bundle):
    fiscal_year = process.anio_tributario - 1
    monthly_facts = list(
        MonthlyTaxFact.objects.filter(
            empresa=process.empresa,
            anio=fiscal_year,
            estado=EstadoMonthlyTaxFact.NORMALIZED,
        ).order_by('mes')
    )
    trial_balance = AnnualTaxTrialBalance.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxTrialBalance.PREPARED,
    ).order_by('-updated_at', '-id').first()
    workbooks = []
    for workbook_type in (TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT):
        mappings = list(
            TaxCodeMapping.objects.filter(
                rule_set=rule_set,
                destino=workbook_type,
                estado=EstadoRegistro.ACTIVE,
            ).order_by('codigo_interno', 'codigo_destino')
        )
        workbook, _ = AnnualTaxWorkbook.objects.update_or_create(
            proceso_renta_anual=process,
            tipo=workbook_type,
            defaults={
                'empresa': process.empresa,
                'source_bundle': source_bundle,
                'rule_set': rule_set,
                'anio_tributario': process.anio_tributario,
                'anio_comercial': fiscal_year,
                'source_ref': f'annual-tax-workbook-{process.empresa_id}-at{process.anio_tributario}-{workbook_type.lower()}',
                'responsible_ref': 'system-annual-tax-workbook-normalizer',
                'estado': EstadoAnnualTaxWorkbook.DRAFT,
            },
        )
        active_line_ids = []
        for mapping in mappings:
            metadata = mapping.metadata if isinstance(mapping.metadata, dict) else {}
            amount, source_metric, warnings, source_detail = _line_amount_from_mapping(
                mapping,
                monthly_facts,
                trial_balance,
            )
            uses_trial_balance = (
                source_detail.get('source') == 'annual_tax_trial_balance'
                or source_metric in TRIAL_BALANCE_SOURCE_METRICS
            )
            line_source_payload = {
                **source_detail,
                'mapping_id': mapping.id,
                'rule_set_id': rule_set.id,
                'annual_tax_trial_balance_required': uses_trial_balance,
                'annual_tax_trial_balance_id': trial_balance.id if uses_trial_balance and trial_balance else None,
                'annual_tax_trial_balance_hash': trial_balance.hash_balance if uses_trial_balance and trial_balance else '',
            }
            for artifact_key in ('expected_output_artifacts', 'expected_enterprise_register_artifacts'):
                if artifact_key in metadata:
                    line_source_payload[artifact_key] = _metadata_string_list(metadata.get(artifact_key))
            existing_line = AnnualTaxWorkbookLine.objects.filter(
                workbook=workbook,
                codigo_interno=mapping.codigo_interno,
                codigo_destino=mapping.codigo_destino,
            ).first()
            existing_warnings = existing_line.warnings if existing_line and isinstance(existing_line.warnings, list) else []
            warning_review_ref = (
                existing_line.warning_review_ref
                if (
                    warnings
                    and existing_warnings == warnings
                    and is_non_sensitive_reference(existing_line.warning_review_ref)
                )
                else ''
            )
            line_payload = {
                'workbook_id': workbook.id,
                'mapping_id': mapping.id,
                'codigo_interno': mapping.codigo_interno,
                'codigo_destino': mapping.codigo_destino,
                'origen': 'monthly_tax_facts',
                'signo': SignoAnnualTaxLine.INFO,
                'monto_clp': str(amount),
                'formula_ref': mapping.formula_ref,
                'evidencia_ref': mapping.evidencia_ref,
                'warning_review_ref': warning_review_ref,
                'warnings': warnings,
                'source_payload': line_source_payload,
            }
            line, _ = AnnualTaxWorkbookLine.objects.update_or_create(
                workbook=workbook,
                codigo_interno=mapping.codigo_interno,
                codigo_destino=mapping.codigo_destino,
                defaults={
                    'mapping': mapping,
                    'origen': 'monthly_tax_facts',
                    'signo': SignoAnnualTaxLine.INFO,
                    'monto_clp': amount,
                    'formula_ref': mapping.formula_ref,
                    'evidencia_ref': mapping.evidencia_ref,
                    'warning_review_ref': warning_review_ref,
                    'warnings': warnings,
                    'source_payload': line_source_payload,
                    'hash_linea': _line_hash_payload(line_payload),
                    'estado': EstadoRegistro.ACTIVE,
                },
            )
            try:
                line.full_clean()
            except ValidationError as error:
                reason = _first_validation_error(error)
                raise ValueError(f'AnnualTaxWorkbookLine no cumple validacion de dominio: {reason}') from error
            line.save()
            active_line_ids.append(line.id)

        workbook.lines.exclude(id__in=active_line_ids).update(estado=EstadoRegistro.INACTIVE)
        _finalize_annual_tax_workbook(workbook)
        workbooks.append(workbook)

    AnnualTaxWorkbook.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
    ).exclude(id__in=[workbook.id for workbook in workbooks]).update(estado=EstadoAnnualTaxWorkbook.RETIRED)
    return workbooks


def mark_annual_tax_workbook_warnings_reviewed(process, *, warning_review_ref):
    warning_review_ref = _ensure_non_sensitive_reference(warning_review_ref, 'warning_review_ref')
    if not warning_review_ref:
        raise ValueError('warning_review_ref es obligatorio para revisar warnings de workbooks RLI/CPT.')
    reviewed_warnings_total = 0
    reviewed_lines_total = 0
    touched_workbooks = {}
    lines = (
        AnnualTaxWorkbookLine.objects.filter(
            workbook__proceso_renta_anual=process,
            workbook__estado=EstadoAnnualTaxWorkbook.PREPARED,
            estado=EstadoRegistro.ACTIVE,
        )
        .select_related('workbook', 'mapping')
        .order_by('workbook_id', 'id')
    )
    for line in lines:
        warnings = line.warnings if isinstance(line.warnings, list) else []
        if not warnings:
            continue
        line.warning_review_ref = warning_review_ref
        line.hash_linea = _line_hash_payload(_workbook_line_hash_payload(line))
        try:
            line.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'AnnualTaxWorkbookLine revisada no cumple validacion de dominio: {reason}') from error
        line.save(update_fields=['warning_review_ref', 'hash_linea', 'updated_at'])
        reviewed_warnings_total += len(warnings)
        reviewed_lines_total += 1
        touched_workbooks[line.workbook_id] = line.workbook

    for workbook in touched_workbooks.values():
        _finalize_annual_tax_workbook(workbook)

    return {
        'process_id': process.id,
        'warning_review_ref': warning_review_ref,
        'reviewed_workbooks_total': len(touched_workbooks),
        'reviewed_lines_total': reviewed_lines_total,
        'reviewed_warnings_total': reviewed_warnings_total,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def _enterprise_register_mapping(rule_set, destino):
    return (
        TaxCodeMapping.objects.filter(
            rule_set=rule_set,
            destino=destino,
            estado=EstadoRegistro.ACTIVE,
        )
        .order_by('codigo_interno', 'codigo_destino')
        .first()
    )


def _workbook_lines_for_register(process, workbook_type):
    return list(
        AnnualTaxWorkbookLine.objects.filter(
            workbook__proceso_renta_anual=process,
            workbook__tipo=workbook_type,
            workbook__estado=EstadoAnnualTaxWorkbook.PREPARED,
            estado=EstadoRegistro.ACTIVE,
        )
        .select_related('workbook', 'mapping')
        .order_by('codigo_interno', 'codigo_destino')
    )


def _active_participations_for_enterprise_register(empresa, fiscal_year):
    period_start = date(fiscal_year, 1, 1)
    period_end = date(fiscal_year, 12, 31)
    return list(
        ParticipacionPatrimonial.objects.filter(
            empresa_owner=empresa,
            activo=True,
            vigente_desde__lte=period_end,
        )
        .filter(Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=period_start))
        .order_by('id')
    )


def _save_enterprise_movement(
    register,
    *,
    source_workbook_line=None,
    codigo_interno,
    origen,
    monto,
    formula_ref,
    evidencia_ref,
    warnings=None,
    source_payload=None,
):
    warnings = warnings or []
    source_payload = source_payload or {}
    monto = _quantize_clp(monto)
    existing_movement = AnnualEnterpriseRegisterMovement.objects.filter(
        register_set=register,
        codigo_interno=codigo_interno,
        origen=origen,
    ).first()
    existing_warnings = (
        existing_movement.warnings
        if existing_movement is not None and isinstance(existing_movement.warnings, list)
        else []
    )
    warning_review_ref = (
        existing_movement.warning_review_ref
        if (
            warnings
            and existing_warnings == warnings
            and existing_movement is not None
            and is_non_sensitive_reference(existing_movement.warning_review_ref)
        )
        else ''
    )
    movement, _ = AnnualEnterpriseRegisterMovement.objects.update_or_create(
        register_set=register,
        codigo_interno=codigo_interno,
        origen=origen,
        defaults={
            'source_workbook_line': source_workbook_line,
            'signo': SignoAnnualTaxLine.INFO,
            'monto_clp': monto,
            'formula_ref': formula_ref,
            'evidencia_ref': evidencia_ref,
            'warning_review_ref': warning_review_ref,
            'warnings': warnings,
            'source_payload': source_payload,
            'estado': EstadoRegistro.ACTIVE,
        },
    )
    movement.hash_movimiento = _source_bundle_hash(_enterprise_movement_hash_payload(movement))
    try:
        movement.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualEnterpriseRegisterMovement no cumple validacion de dominio: {reason}') from error
    movement.save()
    return movement


def _enterprise_movement_hash_payload(movement):
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


def _sync_workbook_backed_enterprise_register(register, register_type, source_lines, target_mapping):
    active_movement_ids = []
    if not source_lines:
        warnings = ['source_workbook_lines_missing']
        if target_mapping is None:
            warnings.append('tax_code_mapping_missing')
        movement = _save_enterprise_movement(
            register,
            codigo_interno=f'{register_type.lower()}.missing-source',
            origen='annual_tax_workbook_missing',
            monto=Decimal('0.00'),
            formula_ref=getattr(target_mapping, 'formula_ref', '') or f'{register_type.lower()}-formula-pending',
            evidencia_ref=getattr(target_mapping, 'evidencia_ref', '') or f'{register_type.lower()}-evidence-pending',
            warnings=warnings,
            source_payload={
                'source': 'annual_tax_workbook',
                'register_type': register_type,
                'mapping_id': getattr(target_mapping, 'id', None),
                'final_tax_calculation': False,
            },
        )
        return [movement.id]

    for source_line in source_lines:
        warnings = []
        if target_mapping is None:
            warnings.append('tax_code_mapping_missing')
        code_suffix = source_line.codigo_destino.lower().replace('_', '-').replace('.', '-')
        source_line_payload = source_line.source_payload if isinstance(source_line.source_payload, dict) else {}
        expected_artifacts = None
        if 'expected_enterprise_register_artifacts' in source_line_payload:
            expected_artifacts = _metadata_string_list(
                source_line_payload.get('expected_enterprise_register_artifacts')
            )
        movement_source_payload = {
            'source': 'annual_tax_workbook_line',
            'register_type': register_type,
            'source_workbook_id': source_line.workbook_id,
            'source_workbook_hash': source_line.workbook.hash_workbook,
            'source_line_id': source_line.id,
            'source_line_hash': source_line.hash_linea,
            'target_mapping_id': getattr(target_mapping, 'id', None),
            'final_tax_calculation': False,
        }
        if expected_artifacts is not None:
            movement_source_payload['expected_output_artifacts'] = expected_artifacts
        movement = _save_enterprise_movement(
            register,
            source_workbook_line=source_line,
            codigo_interno=f'{register_type.lower()}.{source_line.id}',
            origen=f'annual_tax_workbook:{source_line.workbook.tipo}:{code_suffix}'[:64],
            monto=source_line.monto_clp,
            formula_ref=getattr(target_mapping, 'formula_ref', '') or source_line.formula_ref,
            evidencia_ref=getattr(target_mapping, 'evidencia_ref', '') or source_line.evidencia_ref,
            warnings=warnings,
            source_payload=movement_source_payload,
        )
        active_movement_ids.append(movement.id)
    return active_movement_ids


def _sync_participation_enterprise_register(register, register_type, participations):
    active_movement_ids = []
    if not participations:
        movement = _save_enterprise_movement(
            register,
            codigo_interno=f'{register_type.lower()}.missing-participations',
            origen='participacion_patrimonial_missing',
            monto=Decimal('0.00'),
            formula_ref=f'{register_type.lower()}-ownership-formula-pending',
            evidencia_ref=f'{register_type.lower()}-ownership-evidence-pending',
            warnings=['participation_source_missing'],
            source_payload={
                'source': 'participacion_patrimonial',
                'register_type': register_type,
                'final_tax_calculation': False,
            },
        )
        return [movement.id]

    for participation in participations:
        participant_type = 'empresa' if participation.participante_empresa_id else 'socio'
        participant_id = participation.participante_empresa_id or participation.participante_socio_id
        movement = _save_enterprise_movement(
            register,
            codigo_interno=f'{register_type.lower()}.participacion.{participation.id}',
            origen='participacion_patrimonial',
            monto=Decimal('0.00'),
            formula_ref=f'{register_type.lower()}-ownership-structure',
            evidencia_ref=f'participacion-patrimonial-{participation.id}',
            warnings=[],
            source_payload={
                'source': 'participacion_patrimonial',
                'participacion_id': participation.id,
                'participant_type': participant_type,
                'participant_id': participant_id,
                'porcentaje': str(participation.porcentaje),
                'vigente_desde': participation.vigente_desde.isoformat() if participation.vigente_desde else None,
                'vigente_hasta': participation.vigente_hasta.isoformat() if participation.vigente_hasta else None,
                'final_tax_calculation': False,
            },
        )
        active_movement_ids.append(movement.id)
    return active_movement_ids


def sync_annual_enterprise_registers(process, rule_set, source_bundle):
    fiscal_year = process.anio_tributario - 1
    register_specs = (
        (
            TipoAnnualEnterpriseRegister.RAI,
            _workbook_lines_for_register(process, TipoAnnualTaxWorkbook.RLI),
            _enterprise_register_mapping(rule_set, DestinoMapeoTributarioAnual.RAI),
        ),
        (
            TipoAnnualEnterpriseRegister.SAC,
            _workbook_lines_for_register(process, TipoAnnualTaxWorkbook.CPT),
            _enterprise_register_mapping(rule_set, DestinoMapeoTributarioAnual.SAC),
        ),
    )
    participations = _active_participations_for_enterprise_register(process.empresa, fiscal_year)
    registers = []
    for register_type, source_lines, target_mapping in register_specs:
        register, _ = AnnualEnterpriseRegisterSet.objects.update_or_create(
            proceso_renta_anual=process,
            tipo_registro=register_type,
            defaults={
                'empresa': process.empresa,
                'source_bundle': source_bundle,
                'rule_set': rule_set,
                'anio_tributario': process.anio_tributario,
                'anio_comercial': fiscal_year,
                'source_ref': f'annual-enterprise-register-{process.empresa_id}-at{process.anio_tributario}-{register_type.lower()}',
                'responsible_ref': 'system-annual-enterprise-register-normalizer',
                'estado': EstadoAnnualEnterpriseRegister.DRAFT,
            },
        )
        active_movement_ids = _sync_workbook_backed_enterprise_register(
            register,
            register_type,
            source_lines,
            target_mapping,
        )
        register.movements.exclude(id__in=active_movement_ids).update(estado=EstadoRegistro.INACTIVE)
        _finalize_enterprise_register(register, fiscal_year, source='AnnualTaxWorkbook + TaxCodeMapping')
        registers.append(register)

    for register_type in (TipoAnnualEnterpriseRegister.RETIROS, TipoAnnualEnterpriseRegister.DIVIDENDOS):
        register, _ = AnnualEnterpriseRegisterSet.objects.update_or_create(
            proceso_renta_anual=process,
            tipo_registro=register_type,
            defaults={
                'empresa': process.empresa,
                'source_bundle': source_bundle,
                'rule_set': rule_set,
                'anio_tributario': process.anio_tributario,
                'anio_comercial': fiscal_year,
                'source_ref': f'annual-enterprise-register-{process.empresa_id}-at{process.anio_tributario}-{register_type.lower()}',
                'responsible_ref': 'system-annual-enterprise-register-normalizer',
                'estado': EstadoAnnualEnterpriseRegister.DRAFT,
            },
        )
        active_movement_ids = _sync_participation_enterprise_register(register, register_type, participations)
        register.movements.exclude(id__in=active_movement_ids).update(estado=EstadoRegistro.INACTIVE)
        _finalize_enterprise_register(register, fiscal_year, source='ParticipacionPatrimonial')
        registers.append(register)

    AnnualEnterpriseRegisterSet.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualEnterpriseRegister.PREPARED,
    ).exclude(id__in=[register.id for register in registers]).update(estado=EstadoAnnualEnterpriseRegister.RETIRED)
    return registers


def _finalize_enterprise_register(register, fiscal_year, *, source):
    active_movements = list(register.movements.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'origen'))
    warning_count = sum(
        len(movement.warnings or [])
        for movement in active_movements
        if isinstance(movement.warnings, list)
    )
    warning_reviewed_count = sum(
        len(movement.warnings or [])
        for movement in active_movements
        if (
            isinstance(movement.warnings, list)
            and movement.warnings
            and is_non_sensitive_reference(movement.warning_review_ref)
        )
    )
    warning_pending_review_count = warning_count - warning_reviewed_count
    movement_total = _sum_decimal(movement.monto_clp for movement in active_movements)
    register.saldo_inicial_clp = Decimal('0.00')
    register.movimientos_total_clp = movement_total
    register.saldo_final_clp = register.saldo_inicial_clp + register.movimientos_total_clp
    register.resumen_registro = {
        'empresa_id': register.empresa_id,
        'proceso_renta_anual_id': register.proceso_renta_anual_id,
        'source_bundle_id': register.source_bundle_id,
        'rule_set_id': register.rule_set_id,
        'anio_tributario': register.anio_tributario,
        'anio_comercial': fiscal_year,
        'tipo_registro': register.tipo_registro,
        'saldo_inicial_clp': str(register.saldo_inicial_clp),
        'movimientos_total_clp': str(register.movimientos_total_clp),
        'saldo_final_clp': str(register.saldo_final_clp),
        'movements_total': len(active_movements),
        'warnings_total': warning_count,
        'warnings_reviewed_total': warning_reviewed_count,
        'warnings_pending_review_total': warning_pending_review_count,
        'movement_hashes': [movement.hash_movimiento for movement in active_movements],
        'source': source,
        'final_tax_calculation': False,
    }
    register.hash_registro = _source_bundle_hash(register.resumen_registro)
    register.estado = EstadoAnnualEnterpriseRegister.PREPARED
    try:
        register.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualEnterpriseRegisterSet no cumple validacion de dominio: {reason}') from error
    register.save()


def mark_annual_enterprise_register_warnings_reviewed(process, *, warning_review_ref):
    warning_review_ref = _ensure_non_sensitive_reference(warning_review_ref, 'warning_review_ref')
    if not warning_review_ref:
        raise ValueError('warning_review_ref es obligatorio para revisar warnings de registros empresariales.')

    reviewed_register_ids = set()
    reviewed_movements_total = 0
    reviewed_warnings_total = 0
    for movement in AnnualEnterpriseRegisterMovement.objects.filter(
        register_set__proceso_renta_anual=process,
        estado=EstadoRegistro.ACTIVE,
    ).select_related('register_set'):
        warnings = movement.warnings if isinstance(movement.warnings, list) else []
        if not warnings:
            continue
        movement.warning_review_ref = warning_review_ref
        movement.hash_movimiento = _source_bundle_hash(_enterprise_movement_hash_payload(movement))
        movement.full_clean()
        movement.save(update_fields=['warning_review_ref', 'hash_movimiento', 'updated_at'])
        reviewed_register_ids.add(movement.register_set_id)
        reviewed_movements_total += 1
        reviewed_warnings_total += len(warnings)

    fiscal_year = process.anio_tributario - 1
    for register in AnnualEnterpriseRegisterSet.objects.filter(id__in=reviewed_register_ids):
        _finalize_enterprise_register(register, fiscal_year, source='AnnualEnterpriseRegisterMovement warning review')

    return {
        'process_id': process.id,
        'warning_review_ref': warning_review_ref,
        'reviewed_registers_total': len(reviewed_register_ids),
        'reviewed_movements_total': reviewed_movements_total,
        'reviewed_warnings_total': reviewed_warnings_total,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def _quantize_clp(value):
    return Decimal(str(value or '0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _real_estate_contribution_summary(source_bundle):
    summary = source_bundle.resumen_fuentes if isinstance(source_bundle.resumen_fuentes, dict) else {}
    contribution_summary = summary.get('real_estate_contribuciones')
    if not isinstance(contribution_summary, dict):
        contribution_summary = {}
    legacy_values = summary.get('real_estate_contributions_by_property_id')
    values_by_property = contribution_summary.get('values_by_property_id')
    if not isinstance(values_by_property, dict):
        values_by_property = legacy_values if isinstance(legacy_values, dict) else {}
    return {
        'source': str(contribution_summary.get('source') or summary.get('real_estate_contribuciones_source') or 'not_loaded_v1'),
        'official_source_id': contribution_summary.get('official_source_id')
        or summary.get('real_estate_contribution_official_source_id'),
        'values_by_property_id': values_by_property,
    }


def _real_estate_contribution_entry(source_bundle, propiedad_id):
    contribution_summary = _real_estate_contribution_summary(source_bundle)
    values_by_property = contribution_summary['values_by_property_id']
    raw_entry = values_by_property.get(str(propiedad_id))
    if raw_entry is None:
        raw_entry = values_by_property.get(propiedad_id)
    if raw_entry is None:
        return None
    if isinstance(raw_entry, dict):
        raw_amount = (
            raw_entry.get('contribuciones_clp')
            or raw_entry.get('monto_clp')
            or raw_entry.get('amount_clp')
            or raw_entry.get('amount')
        )
        return {
            'contribuciones_clp': _quantize_clp(raw_amount),
            'codigo_f22': str(raw_entry.get('codigo_f22') or '').strip(),
            'evidencia_ref': str(raw_entry.get('evidencia_ref') or raw_entry.get('source_ref') or '').strip(),
        }
    return {
        'contribuciones_clp': _quantize_clp(raw_entry),
        'codigo_f22': '',
        'evidencia_ref': '',
    }


def _allocated_amount(amount, percentage):
    return _quantize_clp(Decimal(str(amount or '0.00')) * Decimal(str(percentage or '0.00')) / Decimal('100.00'))


def _empty_property_source(propiedad):
    return {
        'propiedad': propiedad,
        'arriendo_devengado_clp': Decimal('0.00'),
        'arriendo_conciliado_clp': Decimal('0.00'),
        'arriendo_facturable_clp': Decimal('0.00'),
        'contribuciones_clp': Decimal('0.00'),
        'contract_ids': set(),
        'payment_ids': set(),
        'distribution_ids': set(),
        'allocation_sources': [],
    }


def _real_estate_property_sources(empresa, fiscal_year):
    sources_by_property_id = {}
    direct_properties = Propiedad.objects.filter(
        empresa_owner=empresa,
        estado='activa',
    ).order_by('codigo_propiedad', 'id')
    for propiedad in direct_properties:
        sources_by_property_id[propiedad.id] = _empty_property_source(propiedad)

    distributions = (
        DistribucionCobroMensual.objects.filter(
            beneficiario_empresa_owner=empresa,
            pago_mensual__anio=fiscal_year,
        )
        .select_related('pago_mensual', 'pago_mensual__contrato')
        .prefetch_related('pago_mensual__contrato__contrato_propiedades__propiedad')
        .order_by('pago_mensual__mes', 'id')
    )
    for distribution in distributions:
        contract = distribution.pago_mensual.contrato
        links = list(contract.contrato_propiedades.all())
        for link in links:
            propiedad = link.propiedad
            source = sources_by_property_id.setdefault(propiedad.id, _empty_property_source(propiedad))
            source['arriendo_devengado_clp'] += _allocated_amount(
                distribution.monto_devengado_clp,
                link.porcentaje_distribucion_interna,
            )
            source['arriendo_conciliado_clp'] += _allocated_amount(
                distribution.monto_conciliado_clp,
                link.porcentaje_distribucion_interna,
            )
            source['arriendo_facturable_clp'] += _allocated_amount(
                distribution.monto_facturable_clp,
                link.porcentaje_distribucion_interna,
            )
            source['contract_ids'].add(contract.id)
            source['payment_ids'].add(distribution.pago_mensual_id)
            source['distribution_ids'].add(distribution.id)
            source['allocation_sources'].append(
                {
                    'contrato_id': contract.id,
                    'pago_mensual_id': distribution.pago_mensual_id,
                    'distribucion_cobro_id': distribution.id,
                    'porcentaje_distribucion_interna': str(link.porcentaje_distribucion_interna),
                }
            )

    return [
        sources_by_property_id[key]
        for key in sorted(
            sources_by_property_id.keys(),
            key=lambda property_id: (
                sources_by_property_id[property_id]['propiedad'].codigo_propiedad,
                property_id,
            ),
        )
    ]


def _real_estate_item_hash_payload(section, propiedad, payload):
    return {
        'section_id': section.id,
        'propiedad_id': propiedad.id,
        'codigo_propiedad_snapshot': propiedad.codigo_propiedad,
        'rol_avaluo_snapshot': propiedad.rol_avaluo,
        'direccion_snapshot': propiedad.direccion,
        'comuna_snapshot': propiedad.comuna,
        'region_snapshot': propiedad.region,
        'tipo_inmueble_snapshot': propiedad.tipo_inmueble,
        'owner_tipo_snapshot': propiedad.owner_tipo,
        'owner_id_snapshot': propiedad.owner_id,
        'arriendo_devengado_clp': str(payload['arriendo_devengado_clp']),
        'arriendo_conciliado_clp': str(payload['arriendo_conciliado_clp']),
        'arriendo_facturable_clp': str(payload['arriendo_facturable_clp']),
        'contribuciones_clp': str(payload['contribuciones_clp']),
        'official_contribution_source_id': section.official_contribution_source_id,
        'formula_ref': 'real-estate-annual-section-v1',
        'evidencia_ref': f'real-estate-property-{propiedad.id}-annual-source',
        'warnings': payload['warnings'],
        'source_payload': payload['source_payload'],
    }


def _save_real_estate_item(section, source):
    propiedad = source['propiedad']
    contribution_source = section.official_contribution_source
    contribution_source_id = section.official_contribution_source_id
    contribution_entry = source.get('contribution_entry')
    contribution_warnings = []
    if not contribution_source_id:
        contribution_warnings.append('contribuciones_source_not_loaded_v1')
    elif contribution_entry is None:
        contribution_warnings.append('contribuciones_value_not_loaded_v1')
    contribution_loaded = bool(contribution_source_id and contribution_entry is not None)
    contribution_source_state = 'not_loaded_v1'
    if contribution_loaded:
        contribution_source_state = 'official_or_expert_review'
    elif contribution_source_id:
        contribution_source_state = 'official_or_expert_review_missing_value'
    source_payload = {
        'empresa_id': section.empresa_id,
        'proceso_renta_anual_id': section.proceso_renta_anual_id,
        'anio_tributario': section.anio_tributario,
        'anio_comercial': section.anio_comercial,
        'propiedad_id': propiedad.id,
        'codigo_propiedad': propiedad.codigo_propiedad,
        'rol_avaluo_present': bool(propiedad.rol_avaluo),
        'contract_ids': sorted(source['contract_ids']),
        'payment_ids': sorted(source['payment_ids']),
        'distribution_ids': sorted(source['distribution_ids']),
        'allocation_sources': source['allocation_sources'],
        'rent_allocation': 'ContratoPropiedad.porcentaje_distribucion_interna',
        'contribuciones_source': contribution_source_state,
        'contribuciones_loaded': contribution_loaded,
        'official_contribution_source_id': contribution_source_id,
        'official_contribution_source_type': contribution_source.source_type if contribution_source else '',
        'official_contribution_source_ref_present': bool(contribution_source.source_ref) if contribution_source else False,
        'contribuciones_evidence_ref_present': bool(contribution_entry and contribution_entry.get('evidencia_ref')),
        'codigo_f22_contribuciones': contribution_entry.get('codigo_f22', '') if contribution_entry else '',
        'final_tax_calculation': False,
    }
    payload = {
        'arriendo_devengado_clp': _quantize_clp(source['arriendo_devengado_clp']),
        'arriendo_conciliado_clp': _quantize_clp(source['arriendo_conciliado_clp']),
        'arriendo_facturable_clp': _quantize_clp(source['arriendo_facturable_clp']),
        'contribuciones_clp': (
            contribution_entry['contribuciones_clp']
            if contribution_entry is not None
            else _quantize_clp(source['contribuciones_clp'])
        ),
        'warnings': contribution_warnings,
        'source_payload': source_payload,
    }
    item_hash_payload = _real_estate_item_hash_payload(section, propiedad, payload)
    item, _ = AnnualRealEstateItem.objects.update_or_create(
        section=section,
        propiedad=propiedad,
        defaults={
            'codigo_propiedad_snapshot': propiedad.codigo_propiedad,
            'rol_avaluo_snapshot': propiedad.rol_avaluo,
            'direccion_snapshot': propiedad.direccion,
            'comuna_snapshot': propiedad.comuna,
            'region_snapshot': propiedad.region,
            'tipo_inmueble_snapshot': propiedad.tipo_inmueble,
            'owner_tipo_snapshot': propiedad.owner_tipo,
            'owner_id_snapshot': propiedad.owner_id,
            'arriendo_devengado_clp': payload['arriendo_devengado_clp'],
            'arriendo_conciliado_clp': payload['arriendo_conciliado_clp'],
            'arriendo_facturable_clp': payload['arriendo_facturable_clp'],
            'contribuciones_clp': payload['contribuciones_clp'],
            'formula_ref': item_hash_payload['formula_ref'],
            'evidencia_ref': item_hash_payload['evidencia_ref'],
            'warnings': payload['warnings'],
            'source_payload': source_payload,
            'hash_item': _source_bundle_hash(item_hash_payload),
            'estado': EstadoRegistro.ACTIVE,
        },
    )
    try:
        item.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualRealEstateItem no cumple validacion de dominio: {reason}') from error
    item.save()
    return item


def _finalize_real_estate_section(section, fiscal_year):
    active_items = list(section.items.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_propiedad_snapshot', 'id'))
    warning_count = sum(len(item.warnings or []) for item in active_items if isinstance(item.warnings, list))
    loaded_contribution_count = sum(
        1
        for item in active_items
        if isinstance(item.source_payload, dict) and item.source_payload.get('contribuciones_loaded') is True
    )
    missing_contribution_count = max(len(active_items) - loaded_contribution_count, 0)
    contribution_source_state = 'not_loaded_v1'
    if section.official_contribution_source_id:
        contribution_source_state = (
            'official_or_expert_review'
            if missing_contribution_count == 0
            else 'official_or_expert_review_missing_values'
        )
    section.propiedades_total = len(active_items)
    section.arriendo_devengado_total_clp = _sum_decimal(item.arriendo_devengado_clp for item in active_items)
    section.arriendo_conciliado_total_clp = _sum_decimal(item.arriendo_conciliado_clp for item in active_items)
    section.arriendo_facturable_total_clp = _sum_decimal(item.arriendo_facturable_clp for item in active_items)
    section.contribuciones_total_clp = _sum_decimal(item.contribuciones_clp for item in active_items)
    section.resumen_seccion = {
        'empresa_id': section.empresa_id,
        'proceso_renta_anual_id': section.proceso_renta_anual_id,
        'source_bundle_id': section.source_bundle_id,
        'rule_set_id': section.rule_set_id,
        'anio_tributario': section.anio_tributario,
        'anio_comercial': fiscal_year,
        'propiedades_total': section.propiedades_total,
        'arriendo_devengado_total_clp': str(section.arriendo_devengado_total_clp),
        'arriendo_conciliado_total_clp': str(section.arriendo_conciliado_total_clp),
        'arriendo_facturable_total_clp': str(section.arriendo_facturable_total_clp),
        'contribuciones_total_clp': str(section.contribuciones_total_clp),
        'items_total': len(active_items),
        'warnings_total': warning_count,
        'item_hashes': [item.hash_item for item in active_items],
        'source': 'Propiedad + DistribucionCobroMensual',
        'official_contribution_source_id': section.official_contribution_source_id,
        'contribuciones_source': contribution_source_state,
        'contribuciones_loaded_items_total': loaded_contribution_count,
        'contribuciones_missing_items_total': missing_contribution_count,
        'final_tax_calculation': False,
    }
    section.hash_seccion = _source_bundle_hash(section.resumen_seccion)
    section.estado = EstadoAnnualRealEstateSection.PREPARED
    try:
        section.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualRealEstateSection no cumple validacion de dominio: {reason}') from error
    section.save()


def _find_real_estate_contribution_source(anio_tributario, source_bundle):
    source_id = _real_estate_contribution_summary(source_bundle)['official_source_id']
    if not source_id:
        return None
    try:
        source_id = int(source_id)
    except (TypeError, ValueError):
        return None
    candidates = (
        AnnualTaxOfficialSource.objects.filter(
            id=source_id,
            anio_tributario=anio_tributario,
            estado__in=ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES,
        )
        .filter(
            Q(source_type=TipoAnnualTaxOfficialSource.SII_REAL_ESTATE_CONTRIBUTIONS)
            | Q(
                source_type=TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
                applies_to__in=[
                    DestinoMapeoTributarioAnual.F22,
                    DestinoMapeoTributarioAnual.DOSSIER,
                ],
            )
        )
        .order_by('source_type', 'source_key', 'id')
    )
    for source in candidates:
        if source.source_type == TipoAnnualTaxOfficialSource.SII_REAL_ESTATE_CONTRIBUTIONS:
            return source
        if isinstance(source.metadata, dict) and source.metadata.get('real_estate_contributions') is True:
            return source
    return None


def sync_annual_real_estate_section(process, rule_set, source_bundle):
    fiscal_year = process.anio_tributario - 1
    contribution_source = _find_real_estate_contribution_source(process.anio_tributario, source_bundle)
    section, _ = AnnualRealEstateSection.objects.update_or_create(
        proceso_renta_anual=process,
        defaults={
            'empresa': process.empresa,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'official_contribution_source': contribution_source,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': fiscal_year,
            'source_ref': f'annual-real-estate-section-{process.empresa_id}-at{process.anio_tributario}',
            'responsible_ref': 'system-annual-real-estate-normalizer',
            'estado': EstadoAnnualRealEstateSection.DRAFT,
        },
    )
    active_item_ids = []
    for source in _real_estate_property_sources(process.empresa, fiscal_year):
        source['contribution_entry'] = _real_estate_contribution_entry(source_bundle, source['propiedad'].id)
        item = _save_real_estate_item(section, source)
        active_item_ids.append(item.id)
    section.items.exclude(id__in=active_item_ids).update(estado=EstadoRegistro.INACTIVE)
    _finalize_real_estate_section(section, fiscal_year)
    return section


def _artifact_matrix_common_payload(matrix):
    return {
        'empresa_id': matrix.empresa_id,
        'proceso_renta_anual_id': matrix.proceso_renta_anual_id,
        'source_bundle_id': matrix.source_bundle_id,
        'rule_set_id': matrix.rule_set_id,
        'anio_tributario': matrix.anio_tributario,
        'anio_comercial': matrix.anio_comercial,
    }


def _artifact_review_state(warnings, warning_review_ref=''):
    return (
        EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        if warnings and not is_non_sensitive_reference(warning_review_ref)
        else EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
    )


def _artifact_matrix_item_hash_payload(matrix, spec):
    return {
        'matrix_id': matrix.id,
        'target_kind': spec['target_kind'],
        'target_code': spec['target_code'],
        'medio_sii': spec['medio_sii'],
        'source_kind': spec['source_kind'],
        'source_model': spec['source_model'],
        'source_object_id': spec['source_object_id'],
        'source_hash': spec.get('source_hash', ''),
        'review_state': spec['review_state'],
        'formula_ref': spec['formula_ref'],
        'evidencia_ref': spec['evidencia_ref'],
        'responsible_ref': spec['responsible_ref'],
        'warning_review_ref': spec.get('warning_review_ref', ''),
        'warnings': spec['warnings'],
        'source_payload': spec['source_payload'],
    }


def _artifact_matrix_item_requires_warning_review(item):
    warnings = item.warnings if isinstance(item.warnings, list) else []
    return bool(warnings) and (
        item.review_state != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
        or not is_non_sensitive_reference(item.warning_review_ref)
    )


def _artifact_matrix_item_spec_from_instance(item):
    return {
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
        'warnings': item.warnings if isinstance(item.warnings, list) else [],
        'source_payload': item.source_payload if isinstance(item.source_payload, dict) else {},
    }


def _artifact_matrix_warning_list(items):
    warnings = []
    for item in items:
        item_warnings = item.warnings if isinstance(item.warnings, list) else []
        warnings.extend(item_warnings)
    return warnings


def _artifact_matrix_add_spec(specs, matrix, *, target_kind, target_code, source_kind, source_model,
                              source_object_id, formula_ref, evidencia_ref, source_payload,
                              source_hash='', medio_sii='preparacion_local_revisable',
                              responsible_ref='system-annual-artifact-matrix', warnings=None):
    normalized_warnings = list(warnings or [])
    payload = {
        **_artifact_matrix_common_payload(matrix),
        **source_payload,
        'target_kind': target_kind,
        'target_code': target_code,
        'medio_sii': medio_sii,
        'source_kind': source_kind,
        'source_model': source_model,
        'source_object_id': source_object_id,
        'final_tax_calculation': False,
    }
    specs.append({
        'target_kind': target_kind,
        'target_code': target_code,
        'medio_sii': medio_sii,
        'source_kind': source_kind,
        'source_model': source_model,
        'source_object_id': source_object_id,
        'source_hash': source_hash,
        'review_state': _artifact_review_state(normalized_warnings),
        'formula_ref': formula_ref,
        'evidencia_ref': evidencia_ref,
        'responsible_ref': responsible_ref,
        'warning_review_ref': '',
        'warnings': normalized_warnings,
        'source_payload': payload,
    })


def _ddjj_layout_source_payload(layout):
    return {
        'ddjj_form_code': layout.form_code,
        'layout_id': layout.id,
        'hash_layout': layout.hash_layout,
        'periodicidad': layout.periodicidad,
        'due_date_label': layout.due_date_label,
        'certificate_code': layout.certificate_code,
        'certificate_due_label': layout.certificate_due_label,
        'declaration_status': layout.declaration_status,
        'allowed_media': {
            'formulario_electronico': layout.allows_electronic_form,
            'transferencia_archivos_importador': layout.allows_file_importer,
            'transferencia_archivos_upload': layout.allows_file_upload,
            'software_comercial': layout.allows_commercial_software,
            'asistente': layout.allows_assistant,
        },
        'official_media_source_id': layout.official_media_source_id,
        'official_form_source_id': layout.official_form_source_id,
        'official_software_source_id': layout.official_software_source_id,
        'source': 'AnnualTaxDDJJFormLayout',
    }


def _f22_export_layout_source_payload(layout):
    return {
        'f22_form_code': layout.form_code,
        'layout_id': layout.id,
        'hash_layout': layout.hash_layout,
        'medio_preferente': layout.medio_preferente,
        'allowed_media': {
            'preview_local_controlado': layout.allows_local_preview,
            'archivo_certificado_sii': layout.allows_certified_file,
            'portal_sii_supervisado': layout.allows_supervised_portal,
        },
        'official_certification_source_id': layout.official_certification_source_id,
        'official_instructions_source_id': layout.official_instructions_source_id,
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
        'source': 'AnnualTaxF22ExportLayout',
    }


def _artifact_matrix_specs(matrix, rule_set, source_bundle, config):
    specs = []
    ddjj_enabled = bool(config.ddjj_habilitadas)
    ddjj_form_codes = sorted(str(code) for code in (config.ddjj_habilitadas or []))
    ddjj_layouts = {
        layout.form_code: layout
        for layout in AnnualTaxDDJJFormLayout.objects.filter(
            anio_tributario=matrix.anio_tributario,
            form_code__in=ddjj_form_codes,
            estado=EstadoAnnualTaxDDJJLayout.PREPARED,
        )
    }
    for form_code in ddjj_form_codes:
        layout = ddjj_layouts.get(form_code)
        if layout is not None:
            layout_warnings = layout.warnings if isinstance(layout.warnings, list) else []
            _artifact_matrix_add_spec(
                specs,
                matrix,
                target_kind=TipoAnnualTaxArtifactTarget.DDJJ,
                target_code=f'DDJJ-{form_code}',
                medio_sii=layout.medio_preferente,
                source_kind=SourceKindAnnualTaxArtifact.DDJJ_LAYOUT,
                source_model='AnnualTaxDDJJFormLayout',
                source_object_id=layout.id,
                source_hash=layout.hash_layout,
                formula_ref=layout.instructions_ref,
                evidencia_ref=layout.layout_ref,
                responsible_ref=layout.responsible_ref,
                warnings=layout_warnings,
                source_payload=_ddjj_layout_source_payload(layout),
            )
            continue
        _artifact_matrix_add_spec(
            specs,
            matrix,
            target_kind=TipoAnnualTaxArtifactTarget.DDJJ,
            target_code=f'DDJJ-{form_code}',
            source_kind=SourceKindAnnualTaxArtifact.FISCAL_CONFIG,
            source_model='ConfiguracionFiscalEmpresa',
            source_object_id=config.id,
            source_hash='',
            formula_ref='ddjj-enabled-config-v1',
            evidencia_ref=f'fiscal-config-{config.id}-ddjj-{form_code}',
            source_payload={
                'ddjj_form_code': form_code,
                'regimen_tributario_id': config.regimen_tributario_id,
                'source': 'ConfiguracionFiscalEmpresa.ddjj_habilitadas',
            },
            warnings=['ddjj_layout_missing'],
        )

    f22_layout = AnnualTaxF22ExportLayout.objects.filter(
        anio_tributario=matrix.anio_tributario,
        form_code='F22',
        estado=EstadoAnnualTaxF22ExportLayout.PREPARED,
    ).first()
    if f22_layout is not None:
        layout_warnings = f22_layout.warnings if isinstance(f22_layout.warnings, list) else []
        _artifact_matrix_add_spec(
            specs,
            matrix,
            target_kind=TipoAnnualTaxArtifactTarget.F22,
            target_code='F22-FORMATO',
            medio_sii=f22_layout.medio_preferente,
            source_kind=SourceKindAnnualTaxArtifact.F22_EXPORT_LAYOUT,
            source_model='AnnualTaxF22ExportLayout',
            source_object_id=f22_layout.id,
            source_hash=f22_layout.hash_layout,
            formula_ref=f22_layout.instructions_ref,
            evidencia_ref=f22_layout.format_ref,
            responsible_ref=f22_layout.responsible_ref,
            warnings=layout_warnings,
            source_payload=_f22_export_layout_source_payload(f22_layout),
        )
    else:
        _artifact_matrix_add_spec(
            specs,
            matrix,
            target_kind=TipoAnnualTaxArtifactTarget.F22,
            target_code='F22-FORMATO',
            source_kind=SourceKindAnnualTaxArtifact.FISCAL_CONFIG,
            source_model='ConfiguracionFiscalEmpresa',
            source_object_id=config.id,
            source_hash='',
            formula_ref='f22-export-layout-missing-v1',
            evidencia_ref=f'fiscal-config-{config.id}-f22-export-layout',
            source_payload={
                'form_code': 'F22',
                'regimen_tributario_id': config.regimen_tributario_id,
                'source': 'ConfiguracionFiscalEmpresa',
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
            },
            warnings=['f22_export_layout_missing'],
        )

    mappings = TaxCodeMapping.objects.filter(
        rule_set=rule_set,
        destino__in=[DestinoMapeoTributarioAnual.DDJJ, DestinoMapeoTributarioAnual.F22],
        estado=EstadoRegistro.ACTIVE,
    ).order_by('destino', 'codigo_interno', 'codigo_destino', 'id')
    for mapping in mappings:
        _artifact_matrix_add_spec(
            specs,
            matrix,
            target_kind=mapping.destino,
            target_code=mapping.codigo_destino,
            source_kind=SourceKindAnnualTaxArtifact.TAX_MAPPING,
            source_model='TaxCodeMapping',
            source_object_id=mapping.id,
            source_hash=rule_set.hash_normativo,
            formula_ref=mapping.formula_ref,
            evidencia_ref=mapping.evidencia_ref,
            source_payload={
                'tax_code_mapping_id': mapping.id,
                'codigo_interno': mapping.codigo_interno,
                'codigo_destino': mapping.codigo_destino,
                'destino': mapping.destino,
                'rule_set_version': rule_set.version,
            },
        )

    _artifact_matrix_add_spec(
        specs,
        matrix,
        target_kind=TipoAnnualTaxArtifactTarget.F22,
        target_code='F22-PREVIEW',
        source_kind=SourceKindAnnualTaxArtifact.ANNUAL_SUMMARY,
        source_model='ProcesoRentaAnual',
        source_object_id=matrix.proceso_renta_anual_id,
        source_hash=source_bundle.hash_fuentes,
        formula_ref='f22-preview-summary-v1',
        evidencia_ref=f'proceso-renta-anual-{matrix.proceso_renta_anual_id}-summary',
        source_payload={
            'summary_sections': sorted((matrix.proceso_renta_anual.resumen_anual or {}).keys()),
            'source_bundle_hash': source_bundle.hash_fuentes,
            'rule_set_hash': rule_set.hash_normativo,
        },
    )

    workbooks = AnnualTaxWorkbook.objects.filter(
        proceso_renta_anual=matrix.proceso_renta_anual,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
    ).prefetch_related('lines').order_by('tipo', 'id')
    for workbook in workbooks:
        active_lines = list(workbook.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'id'))
        _artifact_matrix_add_spec(
            specs,
            matrix,
            target_kind=TipoAnnualTaxArtifactTarget.F22,
            target_code=f'F22-{workbook.tipo}',
            source_kind=SourceKindAnnualTaxArtifact.ANNUAL_WORKBOOK,
            source_model='AnnualTaxWorkbook',
            source_object_id=workbook.id,
            source_hash=workbook.hash_workbook,
            formula_ref=f'f22-{workbook.tipo.lower()}-artifact-source-v1',
            evidencia_ref=f'annual-tax-workbook-{workbook.id}',
            warnings=_artifact_matrix_warning_list(active_lines),
            source_payload={
                'workbook_id': workbook.id,
                'tipo': workbook.tipo,
                'lines_total': len(active_lines),
                'hash_workbook': workbook.hash_workbook,
            },
        )

    registers = AnnualEnterpriseRegisterSet.objects.filter(
        proceso_renta_anual=matrix.proceso_renta_anual,
        estado=EstadoAnnualEnterpriseRegister.PREPARED,
    ).prefetch_related('movements').order_by('tipo_registro', 'id')
    for register in registers:
        active_movements = list(register.movements.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'id'))
        _artifact_matrix_add_spec(
            specs,
            matrix,
            target_kind=TipoAnnualTaxArtifactTarget.F22,
            target_code=f'F22-{register.tipo_registro}',
            source_kind=SourceKindAnnualTaxArtifact.ENTERPRISE_REGISTER,
            source_model='AnnualEnterpriseRegisterSet',
            source_object_id=register.id,
            source_hash=register.hash_registro,
            formula_ref=f'f22-{register.tipo_registro.lower()}-register-source-v1',
            evidencia_ref=f'annual-enterprise-register-{register.id}',
            warnings=_artifact_matrix_warning_list(active_movements),
            source_payload={
                'register_id': register.id,
                'tipo_registro': register.tipo_registro,
                'movements_total': len(active_movements),
                'hash_registro': register.hash_registro,
            },
        )
        if ddjj_enabled and register.tipo_registro in {
            TipoAnnualEnterpriseRegister.RETIROS,
            TipoAnnualEnterpriseRegister.DIVIDENDOS,
        }:
            _artifact_matrix_add_spec(
                specs,
                matrix,
                target_kind=TipoAnnualTaxArtifactTarget.DDJJ,
                target_code=f'DDJJ-{register.tipo_registro}',
                source_kind=SourceKindAnnualTaxArtifact.ENTERPRISE_REGISTER,
                source_model='AnnualEnterpriseRegisterSet',
                source_object_id=register.id,
                source_hash=register.hash_registro,
                formula_ref=f'ddjj-{register.tipo_registro.lower()}-register-source-v1',
                evidencia_ref=f'annual-enterprise-register-{register.id}',
                warnings=_artifact_matrix_warning_list(active_movements),
                source_payload={
                    'register_id': register.id,
                    'tipo_registro': register.tipo_registro,
                    'movements_total': len(active_movements),
                    'hash_registro': register.hash_registro,
                },
            )

    real_estate_sections = AnnualRealEstateSection.objects.filter(
        proceso_renta_anual=matrix.proceso_renta_anual,
        estado=EstadoAnnualRealEstateSection.PREPARED,
    ).prefetch_related('items').order_by('id')
    for section in real_estate_sections:
        active_items = list(section.items.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_propiedad_snapshot', 'id'))
        for target_kind, target_code, formula_ref in (
            (TipoAnnualTaxArtifactTarget.F22, 'F22-BIENES-RAICES', 'f22-real-estate-source-v1'),
            (TipoAnnualTaxArtifactTarget.DDJJ, 'DDJJ-BIENES-RAICES', 'ddjj-real-estate-source-v1'),
        ):
            if target_kind == TipoAnnualTaxArtifactTarget.DDJJ and not ddjj_enabled:
                continue
            _artifact_matrix_add_spec(
                specs,
                matrix,
                target_kind=target_kind,
                target_code=target_code,
                source_kind=SourceKindAnnualTaxArtifact.REAL_ESTATE,
                source_model='AnnualRealEstateSection',
                source_object_id=section.id,
                source_hash=section.hash_seccion,
                formula_ref=formula_ref,
                evidencia_ref=f'annual-real-estate-section-{section.id}',
                warnings=_artifact_matrix_warning_list(active_items),
                source_payload={
                    'real_estate_section_id': section.id,
                    'items_total': len(active_items),
                    'hash_seccion': section.hash_seccion,
                    'official_contribution_source_id': section.official_contribution_source_id,
                    'contribuciones_source': (
                        section.resumen_seccion.get('contribuciones_source')
                        if isinstance(section.resumen_seccion, dict)
                        else 'not_loaded_v1'
                    ),
                    'contribuciones_loaded_items_total': (
                        section.resumen_seccion.get('contribuciones_loaded_items_total')
                        if isinstance(section.resumen_seccion, dict)
                        else 0
                    ),
                },
            )
    return specs


def _save_artifact_matrix_item(matrix, spec):
    existing = AnnualTaxArtifactMatrixItem.objects.filter(
        matrix=matrix,
        target_kind=spec['target_kind'],
        target_code=spec['target_code'],
        source_kind=spec['source_kind'],
        source_model=spec['source_model'],
        source_object_id=spec['source_object_id'],
    ).first()
    warning_review_ref = ''
    if (
        existing is not None
        and is_non_sensitive_reference(existing.warning_review_ref)
        and list(existing.warnings if isinstance(existing.warnings, list) else []) == list(spec['warnings'])
        and existing.medio_sii == spec['medio_sii']
        and existing.source_hash == spec.get('source_hash', '')
        and existing.formula_ref == spec['formula_ref']
        and existing.evidencia_ref == spec['evidencia_ref']
        and existing.responsible_ref == spec['responsible_ref']
        and (existing.source_payload if isinstance(existing.source_payload, dict) else {}) == spec['source_payload']
        and spec['warnings']
    ):
        warning_review_ref = existing.warning_review_ref
    spec = {
        **spec,
        'warning_review_ref': warning_review_ref,
        'review_state': _artifact_review_state(spec['warnings'], warning_review_ref),
    }
    hash_payload = _artifact_matrix_item_hash_payload(matrix, spec)
    item, _ = AnnualTaxArtifactMatrixItem.objects.update_or_create(
        matrix=matrix,
        target_kind=spec['target_kind'],
        target_code=spec['target_code'],
        source_kind=spec['source_kind'],
        source_model=spec['source_model'],
        source_object_id=spec['source_object_id'],
        defaults={
            'medio_sii': spec['medio_sii'],
            'source_hash': spec.get('source_hash', ''),
            'review_state': spec['review_state'],
            'formula_ref': spec['formula_ref'],
            'evidencia_ref': spec['evidencia_ref'],
            'responsible_ref': spec['responsible_ref'],
            'warning_review_ref': spec['warning_review_ref'],
            'warnings': spec['warnings'],
            'source_payload': spec['source_payload'],
            'hash_item': _source_bundle_hash(hash_payload),
            'estado': EstadoRegistro.ACTIVE,
        },
    )
    try:
        item.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxArtifactMatrixItem no cumple validacion de dominio: {reason}') from error
    item.save()
    return item


def _finalize_artifact_matrix(matrix):
    active_items = list(
        matrix.items.filter(estado=EstadoRegistro.ACTIVE).order_by(
            'target_kind',
            'target_code',
            'source_kind',
            'source_model',
            'source_object_id',
        )
    )
    target_counts = {}
    review_state_counts = {}
    warning_count = 0
    warning_reviewed_count = 0
    warning_pending_review_count = 0
    for item in active_items:
        target_counts[item.target_kind] = target_counts.get(item.target_kind, 0) + 1
        review_state_counts[item.review_state] = review_state_counts.get(item.review_state, 0) + 1
        warnings = item.warnings if isinstance(item.warnings, list) else []
        warning_count += len(warnings)
        if (
            warnings
            and item.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
            and is_non_sensitive_reference(item.warning_review_ref)
        ):
            warning_reviewed_count += len(warnings)
        elif warnings:
            warning_pending_review_count += len(warnings)
    matrix.items_total = len(active_items)
    matrix.ddjj_items_total = target_counts.get(TipoAnnualTaxArtifactTarget.DDJJ, 0)
    matrix.f22_items_total = target_counts.get(TipoAnnualTaxArtifactTarget.F22, 0)
    matrix.resumen_matriz = {
        'empresa_id': matrix.empresa_id,
        'proceso_renta_anual_id': matrix.proceso_renta_anual_id,
        'source_bundle_id': matrix.source_bundle_id,
        'rule_set_id': matrix.rule_set_id,
        'anio_tributario': matrix.anio_tributario,
        'anio_comercial': matrix.anio_comercial,
        'items_total': matrix.items_total,
        'ddjj_items_total': matrix.ddjj_items_total,
        'f22_items_total': matrix.f22_items_total,
        'target_counts': dict(sorted(target_counts.items())),
        'review_state_counts': dict(sorted(review_state_counts.items())),
        'warnings_total': warning_count,
        'warnings_reviewed_total': warning_reviewed_count,
        'warnings_pending_review_total': warning_pending_review_count,
        'item_hashes': [item.hash_item for item in active_items],
        'source': 'LeaseManager annual tax intermediate artifacts',
        'final_tax_calculation': False,
        'sii_submission': False,
    }
    matrix.hash_matriz = _source_bundle_hash(matrix.resumen_matriz)
    matrix.estado = EstadoAnnualTaxArtifactMatrix.PREPARED
    try:
        matrix.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxArtifactMatrix no cumple validacion de dominio: {reason}') from error
    matrix.save()


def mark_annual_tax_artifact_matrix_warnings_reviewed(matrix, *, warning_review_ref):
    warning_review_ref = _ensure_non_sensitive_reference(warning_review_ref, 'warning_review_ref')
    if not warning_review_ref:
        raise ValueError('warning_review_ref es obligatorio para revisar warnings de matriz anual.')
    reviewed_warnings_total = 0
    reviewed_items_total = 0
    for item in matrix.items.filter(estado=EstadoRegistro.ACTIVE).order_by('id'):
        warnings = item.warnings if isinstance(item.warnings, list) else []
        if not warnings or item.review_state == EstadoAnnualTaxArtifactReview.BLOCKED:
            continue
        item.warning_review_ref = warning_review_ref
        item.review_state = EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
        item.hash_item = _source_bundle_hash(_artifact_matrix_item_hash_payload(matrix, _artifact_matrix_item_spec_from_instance(item)))
        try:
            item.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'AnnualTaxArtifactMatrixItem revisado no cumple validacion de dominio: {reason}') from error
        item.save(update_fields=['warning_review_ref', 'review_state', 'hash_item', 'updated_at'])
        reviewed_warnings_total += len(warnings)
        reviewed_items_total += 1
    _finalize_artifact_matrix(matrix)
    return {
        'matrix_id': matrix.id,
        'warning_review_ref': warning_review_ref,
        'reviewed_items_total': reviewed_items_total,
        'reviewed_warnings_total': reviewed_warnings_total,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def _pending_generated_warning_review_summary(process):
    workbook_pending_lines_total = 0
    workbook_pending_warnings_total = 0
    for line in AnnualTaxWorkbookLine.objects.filter(
        workbook__proceso_renta_anual=process,
        workbook__estado=EstadoAnnualTaxWorkbook.PREPARED,
        estado=EstadoRegistro.ACTIVE,
    ):
        warnings = line.warnings if isinstance(line.warnings, list) else []
        if warnings and not is_non_sensitive_reference(line.warning_review_ref):
            workbook_pending_lines_total += 1
            workbook_pending_warnings_total += len(warnings)

    enterprise_pending_movements_total = 0
    enterprise_pending_warnings_total = 0
    for movement in AnnualEnterpriseRegisterMovement.objects.filter(
        register_set__proceso_renta_anual=process,
        register_set__estado=EstadoAnnualEnterpriseRegister.PREPARED,
        estado=EstadoRegistro.ACTIVE,
    ):
        warnings = movement.warnings if isinstance(movement.warnings, list) else []
        if warnings and not is_non_sensitive_reference(movement.warning_review_ref):
            enterprise_pending_movements_total += 1
            enterprise_pending_warnings_total += len(warnings)

    artifact_pending_items_total = 0
    artifact_pending_warnings_total = 0
    for item in AnnualTaxArtifactMatrixItem.objects.filter(
        matrix__proceso_renta_anual=process,
        matrix__estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
        estado=EstadoRegistro.ACTIVE,
    ):
        warnings = item.warnings if isinstance(item.warnings, list) else []
        if warnings and (
            item.review_state != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
            or not is_non_sensitive_reference(item.warning_review_ref)
        ):
            artifact_pending_items_total += 1
            artifact_pending_warnings_total += len(warnings)

    return {
        'workbook_pending_lines_total': workbook_pending_lines_total,
        'workbook_pending_warnings_total': workbook_pending_warnings_total,
        'enterprise_pending_movements_total': enterprise_pending_movements_total,
        'enterprise_pending_warnings_total': enterprise_pending_warnings_total,
        'artifact_pending_items_total': artifact_pending_items_total,
        'artifact_pending_warnings_total': artifact_pending_warnings_total,
        'pending_warnings_total': (
            workbook_pending_warnings_total
            + enterprise_pending_warnings_total
            + artifact_pending_warnings_total
        ),
    }


def summarize_annual_tax_generated_warning_review(process):
    return _pending_generated_warning_review_summary(process)


def _refresh_annual_review_process_summary(process, *, rule_set, source_bundle):
    summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
    process.resumen_anual = {
        **summary,
        'annual_tax_workbooks': summarize_annual_tax_workbooks(process),
        'annual_enterprise_registers': summarize_annual_enterprise_registers(process),
        'annual_tax_artifact_matrices': summarize_annual_tax_artifact_matrices(process),
    }
    process.save(update_fields=['resumen_anual', 'updated_at'])

    sync_annual_tax_dossier(process, rule_set, source_bundle)
    process.resumen_anual = {
        **process.resumen_anual,
        'annual_tax_dossiers': summarize_annual_tax_dossiers(process),
    }
    process.save(update_fields=['resumen_anual', 'updated_at'])

    sync_annual_tax_export(process, rule_set, source_bundle)
    process.resumen_anual = {
        **process.resumen_anual,
        'annual_tax_exports': summarize_annual_tax_exports(process),
    }
    process.save(update_fields=['resumen_anual', 'updated_at'])

    sync_annual_tax_review_checklist(process, rule_set, source_bundle)
    process.resumen_anual = {
        **process.resumen_anual,
        'annual_tax_review_checklists': summarize_annual_tax_review_checklists(process),
    }
    process.save(update_fields=['resumen_anual', 'updated_at'])
    return sync_annual_tax_support_document(process)


def mark_annual_tax_generated_warnings_reviewed(process, *, warning_review_ref, apply=False):
    warning_review_ref = _ensure_non_sensitive_reference(warning_review_ref, 'warning_review_ref')
    if not warning_review_ref:
        raise ValueError('warning_review_ref es obligatorio para revisar warnings generados de renta anual.')

    before = _pending_generated_warning_review_summary(process)
    if not apply:
        return {
            'process_id': process.id,
            'applied': False,
            'warning_review_ref': warning_review_ref,
            'before': before,
            'after': before,
            'workbooks': {},
            'enterprise_registers': {},
            'artifact_matrices': [],
            'ready_for_generated_artifact_review': before['pending_warnings_total'] == 0,
            'safety': {
                'writes_database': False,
                'uses_sii_real': False,
                'uses_credentials': False,
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
            },
        }

    with transaction.atomic():
        dossier = AnnualTaxDossier.objects.select_related('source_bundle', 'rule_set').filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualTaxDossier.PREPARED,
        ).first()
        if dossier is None:
            raise ValueError('ProcesoRentaAnual requiere AnnualTaxDossier preparado antes de revisar la cadena generada.')
        source_bundle = dossier.source_bundle
        rule_set = dossier.rule_set

        workbooks = mark_annual_tax_workbook_warnings_reviewed(
            process,
            warning_review_ref=warning_review_ref,
        )
        enterprise_registers = mark_annual_enterprise_register_warnings_reviewed(
            process,
            warning_review_ref=warning_review_ref,
        )
        matrix_results = []
        for matrix in AnnualTaxArtifactMatrix.objects.filter(
            proceso_renta_anual=process,
            estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
        ).order_by('id'):
            matrix_results.append(
                mark_annual_tax_artifact_matrix_warnings_reviewed(
                    matrix,
                    warning_review_ref=warning_review_ref,
                )
            )

        process.refresh_from_db()
        support_document = _refresh_annual_review_process_summary(
            process,
            rule_set=rule_set,
            source_bundle=source_bundle,
        )
        process.refresh_from_db()
        after = _pending_generated_warning_review_summary(process)

    return {
        'process_id': process.id,
        'applied': True,
        'warning_review_ref': warning_review_ref,
        'before': before,
        'after': after,
        'workbooks': workbooks,
        'enterprise_registers': enterprise_registers,
        'artifact_matrices': matrix_results,
        'support_document_id': support_document.id,
        'ready_for_generated_artifact_review': after['pending_warnings_total'] == 0,
        'safety': {
            'writes_database': True,
            'uses_sii_real': False,
            'uses_credentials': False,
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
        },
    }

def sync_annual_tax_artifact_matrix(process, rule_set, source_bundle, config):
    fiscal_year = process.anio_tributario - 1
    matrix, _ = AnnualTaxArtifactMatrix.objects.update_or_create(
        proceso_renta_anual=process,
        defaults={
            'empresa': process.empresa,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': fiscal_year,
            'source_ref': f'annual-tax-artifact-matrix-{process.empresa_id}-at{process.anio_tributario}',
            'responsible_ref': 'system-annual-artifact-matrix',
            'estado': EstadoAnnualTaxArtifactMatrix.DRAFT,
        },
    )
    active_item_ids = []
    for spec in _artifact_matrix_specs(matrix, rule_set, source_bundle, config):
        item = _save_artifact_matrix_item(matrix, spec)
        active_item_ids.append(item.id)
    matrix.items.exclude(id__in=active_item_ids).update(estado=EstadoRegistro.INACTIVE)
    _finalize_artifact_matrix(matrix)
    return matrix


def _annual_tax_dossier_review_state(matrix):
    active_items = matrix.items.filter(estado=EstadoRegistro.ACTIVE)
    if active_items.filter(review_state=EstadoAnnualTaxArtifactReview.BLOCKED).exists():
        return EstadoAnnualTaxArtifactReview.BLOCKED
    if active_items.exclude(review_state=EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW).exists():
        return EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
    for item in active_items:
        if _artifact_matrix_item_requires_warning_review(item):
            return EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
    return EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW


def _annual_tax_dossier_summary(process, rule_set, source_bundle, matrix):
    process_summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
    matrix_summary = summarize_annual_tax_artifact_matrices(process)
    monthly_summary = process_summary.get('annual_tax_monthly_facts', {})
    workbook_summary = process_summary.get('annual_tax_workbooks', {})
    register_summary = process_summary.get('annual_enterprise_registers', {})
    real_estate_summary = process_summary.get('annual_real_estate_sections', {})
    ddjj_layout_summary = process_summary.get('annual_tax_ddjj_layouts', {})
    f22_export_layout_summary = process_summary.get('annual_tax_f22_export_layouts', {})
    active_items = matrix.items.filter(estado=EstadoRegistro.ACTIVE).order_by(
        'target_kind',
        'target_code',
        'source_kind',
        'source_model',
        'source_object_id',
    )
    warnings_total = 0
    warnings_reviewed_total = 0
    warnings_pending_review_total = 0
    review_state_counts = {}
    item_refs = []
    for item in active_items:
        warnings = item.warnings if isinstance(item.warnings, list) else []
        warnings_total += len(warnings)
        if (
            warnings
            and item.review_state == EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW
            and is_non_sensitive_reference(item.warning_review_ref)
        ):
            warnings_reviewed_total += len(warnings)
        elif warnings:
            warnings_pending_review_total += len(warnings)
        review_state_counts[item.review_state] = review_state_counts.get(item.review_state, 0) + 1
        item_refs.append(
            {
                'id': item.id,
                'target_kind': item.target_kind,
                'target_code': item.target_code,
                'medio_sii': item.medio_sii,
                'source_kind': item.source_kind,
                'source_model': item.source_model,
                'source_object_id': item.source_object_id,
                'source_hash': item.source_hash,
                'hash_item': item.hash_item,
                'review_state': item.review_state,
                'warning_review_ref': item.warning_review_ref,
            }
        )
    try:
        monthly_facts_total = int(monthly_summary.get('total') or 0)
    except (AttributeError, TypeError, ValueError):
        monthly_facts_total = 0
    try:
        workbooks_total = int(workbook_summary.get('total') or 0)
    except (AttributeError, TypeError, ValueError):
        workbooks_total = 0
    try:
        enterprise_registers_total = int(register_summary.get('total') or 0)
    except (AttributeError, TypeError, ValueError):
        enterprise_registers_total = 0
    try:
        real_estate_sections_total = int(real_estate_summary.get('total') or 0)
    except (AttributeError, TypeError, ValueError):
        real_estate_sections_total = 0
    artifact_matrix_items_total = active_items.count()
    review_state = _annual_tax_dossier_review_state(matrix)
    return {
        'empresa_id': process.empresa_id,
        'proceso_renta_anual_id': process.id,
        'source_bundle_id': source_bundle.id,
        'rule_set_id': rule_set.id,
        'artifact_matrix_id': matrix.id,
        'anio_tributario': process.anio_tributario,
        'anio_comercial': process.anio_tributario - 1,
        'source_bundle_hash': source_bundle.hash_fuentes,
        'rule_set_hash': rule_set.hash_normativo,
        'artifact_matrix_hash': matrix.hash_matriz,
        'monthly_facts_total': monthly_facts_total,
        'workbooks_total': workbooks_total,
        'enterprise_registers_total': enterprise_registers_total,
        'real_estate_sections_total': real_estate_sections_total,
        'artifact_matrix_items_total': artifact_matrix_items_total,
        'components': {
            'annual_tax_source_bundle': process_summary.get('annual_tax_source_bundle', {}),
            'annual_tax_monthly_facts': monthly_summary,
            'annual_tax_workbooks': workbook_summary,
            'annual_enterprise_registers': register_summary,
            'annual_real_estate_sections': real_estate_summary,
            'annual_tax_ddjj_layouts': ddjj_layout_summary,
            'annual_tax_f22_export_layouts': f22_export_layout_summary,
            'annual_tax_artifact_matrices': matrix_summary,
        },
        'matrix_items_total': artifact_matrix_items_total,
        'ddjj_items_total': matrix.ddjj_items_total,
        'f22_items_total': matrix.f22_items_total,
        'warnings_total': warnings_total,
        'warnings_reviewed_total': warnings_reviewed_total,
        'warnings_pending_review_total': warnings_pending_review_total,
        'review_state': review_state,
        'review_state_counts': dict(sorted(review_state_counts.items())),
        'item_refs': item_refs,
        'final_tax_calculation': False,
        'sii_submission': False,
    }


def sync_annual_tax_dossier(process, rule_set, source_bundle):
    matrix = AnnualTaxArtifactMatrix.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxArtifactMatrix.PREPARED,
    )
    summary = _annual_tax_dossier_summary(process, rule_set, source_bundle, matrix)
    dossier, _ = AnnualTaxDossier.objects.update_or_create(
        proceso_renta_anual=process,
        defaults={
            'empresa': process.empresa,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'artifact_matrix': matrix,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': process.anio_tributario - 1,
            'source_ref': f'annual-tax-dossier-source-{process.empresa_id}-at{process.anio_tributario}',
            'responsible_ref': 'annual-tax-review-owner',
            'dossier_ref': f'annual-tax-dossier-{process.empresa_id}-{process.anio_tributario}-review-package-v1',
            'review_state': summary['review_state'],
            'monthly_facts_total': summary['monthly_facts_total'],
            'workbooks_total': summary['workbooks_total'],
            'enterprise_registers_total': summary['enterprise_registers_total'],
            'real_estate_sections_total': summary['real_estate_sections_total'],
            'artifact_matrix_items_total': summary['artifact_matrix_items_total'],
            'warnings_total': summary['warnings_total'],
            'resumen_dossier': summary,
            'hash_dossier': _source_bundle_hash(summary),
            'estado': EstadoAnnualTaxDossier.PREPARED,
        },
    )
    try:
        dossier.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxDossier no cumple validacion de dominio: {reason}') from error
    dossier.save()
    AnnualTaxDossier.objects.filter(
        empresa=process.empresa,
        anio_tributario=process.anio_tributario,
        estado=EstadoAnnualTaxDossier.PREPARED,
    ).exclude(pk=dossier.pk).update(estado=EstadoAnnualTaxDossier.RETIRED)
    return dossier


def _f22_export_format_source_from_bundle(source_bundle):
    summary = source_bundle.resumen_fuentes if isinstance(source_bundle.resumen_fuentes, dict) else {}
    f22_export_format = summary.get('f22_export_format') if isinstance(summary.get('f22_export_format'), dict) else {}
    source_id = f22_export_format.get('official_source_id')
    if not source_id:
        return None
    try:
        return AnnualTaxOfficialSource.objects.get(
            pk=source_id,
            anio_tributario=source_bundle.anio_tributario,
            estado__in=ANNUAL_TAX_OFFICIAL_SOURCE_READY_STATES,
        )
    except AnnualTaxOfficialSource.DoesNotExist:
        return None


def _annual_tax_export_artifact_contract(item):
    target_kind = str(item.get('target_kind') or '')
    export_role = 'ddjj_package_part' if target_kind == TipoAnnualTaxArtifactTarget.DDJJ else 'f22_preview_part'
    return {
        'contract_version': 'annual-tax-export-artifact-contract-v1',
        'artifact_matrix_item_id': item.get('id'),
        'target_kind': target_kind,
        'target_code': item.get('target_code'),
        'export_role': export_role,
        'delivery_kind': 'local_controlled_preview',
        'medio_sii': item.get('medio_sii'),
        'source_kind': item.get('source_kind'),
        'source_model': item.get('source_model'),
        'source_object_id': item.get('source_object_id'),
        'source_hash': item.get('source_hash'),
        'hash_item': item.get('hash_item'),
        'review_state': item.get('review_state'),
        'structural_validation': 'contract_ready_for_responsible_review',
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
        'requires_official_format_gate': True,
        'requires_explicit_submission_authorization': True,
    }


def _annual_tax_export_artifact_contracts(item_refs):
    return [
        _annual_tax_export_artifact_contract(item)
        for item in item_refs
        if item.get('target_kind') in {
            TipoAnnualTaxArtifactTarget.DDJJ,
            TipoAnnualTaxArtifactTarget.F22,
        }
    ]


def _annual_tax_export_file_slug(value):
    slug = ''.join(
        character if character.isalnum() else '-'
        for character in str(value or '').strip().upper()
    )
    slug = '-'.join(part for part in slug.split('-') if part)
    return slug or 'ARTIFACTO'


def _annual_tax_export_file_payload(process, contract):
    return {
        'schema': 'annual-tax-export-file-payload-v1',
        'anio_tributario': process.anio_tributario,
        'anio_comercial': process.anio_tributario - 1,
        'artifact_matrix_item_id': contract.get('artifact_matrix_item_id'),
        'target_kind': contract.get('target_kind'),
        'target_code': contract.get('target_code'),
        'medio_sii': contract.get('medio_sii'),
        'source_kind': contract.get('source_kind'),
        'source_model': contract.get('source_model'),
        'source_object_id': contract.get('source_object_id'),
        'source_hash': contract.get('source_hash'),
        'hash_item': contract.get('hash_item'),
        'review_state': contract.get('review_state'),
        'artifact_contract_version': contract.get('contract_version'),
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
    }


def _annual_tax_export_file_manifest_entry(process, contract):
    file_payload = _annual_tax_export_file_payload(process, contract)
    payload_bytes = json.dumps(
        file_payload,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True,
        default=str,
    ).encode('utf-8')
    target_kind = str(contract.get('target_kind') or '')
    target_code = _annual_tax_export_file_slug(contract.get('target_code'))
    artifact_id = _annual_tax_export_file_slug(contract.get('artifact_matrix_item_id'))
    return {
        'file_manifest_version': 'annual-tax-export-file-manifest-v1',
        'artifact_matrix_item_id': contract.get('artifact_matrix_item_id'),
        'target_kind': target_kind,
        'target_code': contract.get('target_code'),
        'file_role': 'ddjj_local_export_candidate' if target_kind == TipoAnnualTaxArtifactTarget.DDJJ else 'f22_local_export_candidate',
        'file_name': f'AT{process.anio_tributario}_{target_kind}_{target_code}_{artifact_id}.json',
        'content_type': 'application/json',
        'encoding': 'utf-8',
        'schema_ref': 'annual-tax-export-file-payload-v1',
        'delivery_kind': 'local_controlled_export_file',
        'medio_sii': contract.get('medio_sii'),
        'source_contract_version': contract.get('contract_version'),
        'payload_hash': hashlib.sha256(payload_bytes).hexdigest(),
        'payload_size_bytes': len(payload_bytes),
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
        'requires_official_format_gate': True,
        'requires_explicit_submission_authorization': True,
    }


def _annual_tax_export_file_manifest(process, contracts):
    return [
        _annual_tax_export_file_manifest_entry(process, contract)
        for contract in contracts
        if contract.get('target_kind') in {
            TipoAnnualTaxArtifactTarget.DDJJ,
            TipoAnnualTaxArtifactTarget.F22,
        }
    ]


def _annual_tax_export_summary(process, dossier, ddjj, f22, official_format_source=None):
    dossier_summary = dossier.resumen_dossier if isinstance(dossier.resumen_dossier, dict) else {}
    process_summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
    f22_layout_summary = process_summary.get('annual_tax_f22_export_layouts', {})
    f22_layout = (
        f22_layout_summary.get('by_form_code', {}).get('F22')
        if isinstance(f22_layout_summary.get('by_form_code'), dict)
        else None
    )
    item_refs = dossier_summary.get('item_refs') if isinstance(dossier_summary.get('item_refs'), list) else []
    export_items = [
        {
            'target_kind': item.get('target_kind'),
            'target_code': item.get('target_code'),
            'source_kind': item.get('source_kind'),
            'source_model': item.get('source_model'),
            'source_object_id': item.get('source_object_id'),
            'source_hash': item.get('source_hash'),
            'hash_item': item.get('hash_item'),
            'review_state': item.get('review_state'),
        }
        for item in item_refs
    ]
    ddjj_items_total = dossier_summary.get('ddjj_items_total', dossier.artifact_matrix.ddjj_items_total)
    f22_items_total = dossier_summary.get('f22_items_total', dossier.artifact_matrix.f22_items_total)
    try:
        ddjj_items_total = int(ddjj_items_total or 0)
    except (TypeError, ValueError):
        ddjj_items_total = 0
    try:
        f22_items_total = int(f22_items_total or 0)
    except (TypeError, ValueError):
        f22_items_total = 0
    export_artifact_contracts = _annual_tax_export_artifact_contracts(item_refs)
    ddjj_export_contracts_total = sum(
        1 for contract in export_artifact_contracts if contract.get('target_kind') == TipoAnnualTaxArtifactTarget.DDJJ
    )
    f22_export_contracts_total = sum(
        1 for contract in export_artifact_contracts if contract.get('target_kind') == TipoAnnualTaxArtifactTarget.F22
    )
    export_file_manifest = _annual_tax_export_file_manifest(process, export_artifact_contracts)
    ddjj_export_files_total = sum(
        1 for entry in export_file_manifest if entry.get('target_kind') == TipoAnnualTaxArtifactTarget.DDJJ
    )
    f22_export_files_total = sum(
        1 for entry in export_file_manifest if entry.get('target_kind') == TipoAnnualTaxArtifactTarget.F22
    )
    return {
        'empresa_id': process.empresa_id,
        'proceso_renta_anual_id': process.id,
        'dossier_id': dossier.id,
        'anio_tributario': process.anio_tributario,
        'anio_comercial': process.anio_tributario - 1,
        'export_kind': TipoAnnualTaxExport.PREVIEW_PACKAGE,
        'format_kind': 'local_controlled_preview',
        'dossier_hash': dossier.hash_dossier,
        'artifact_matrix_id': dossier.artifact_matrix_id,
        'artifact_matrix_hash': dossier_summary.get('artifact_matrix_hash'),
        'source_bundle_id': dossier.source_bundle_id,
        'source_bundle_hash': dossier_summary.get('source_bundle_hash'),
        'rule_set_id': dossier.rule_set_id,
        'rule_set_hash': dossier_summary.get('rule_set_hash'),
        'official_format_source_id': official_format_source.id if official_format_source else None,
        'official_format_source': _f22_export_format_summary(official_format_source),
        'ddjj_preparacion_id': ddjj.id if ddjj else None,
        'ddjj_estado_preparacion': ddjj.estado_preparacion if ddjj else '',
        'f22_preparacion_id': f22.id if f22 else None,
        'f22_estado_preparacion': f22.estado_preparacion if f22 else '',
        'f22_export_layout_id': f22_layout.get('id') if isinstance(f22_layout, dict) else None,
        'f22_export_layout_hash': f22_layout.get('hash_layout') if isinstance(f22_layout, dict) else '',
        'f22_export_layout_medio': f22_layout.get('medio_preferente') if isinstance(f22_layout, dict) else '',
        'target_items_total': ddjj_items_total + f22_items_total,
        'ddjj_items_total': ddjj_items_total,
        'f22_items_total': f22_items_total,
        'export_contracts_total': len(export_artifact_contracts),
        'ddjj_export_contracts_total': ddjj_export_contracts_total,
        'f22_export_contracts_total': f22_export_contracts_total,
        'export_files_total': len(export_file_manifest),
        'ddjj_export_files_total': ddjj_export_files_total,
        'f22_export_files_total': f22_export_files_total,
        'export_file_manifest_hash': _source_bundle_hash(export_file_manifest),
        'warnings_total': dossier.warnings_total,
        'review_state': dossier.review_state,
        'export_items': export_items,
        'export_artifact_contracts': export_artifact_contracts,
        'export_file_manifest': export_file_manifest,
        'official_format': False,
        'sii_submission': False,
        'final_tax_calculation': False,
        'sii_submission_attempted': False,
        'requires_official_format_gate': True,
        'requires_explicit_submission_authorization': True,
    }


def sync_annual_tax_export(process, rule_set, source_bundle):
    dossier = AnnualTaxDossier.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxDossier.PREPARED,
    )
    ddjj = DDJJPreparacionAnual.objects.filter(proceso_renta_anual=process).first()
    f22 = F22PreparacionAnual.objects.filter(proceso_renta_anual=process).first()
    if ddjj is None or f22 is None:
        raise ValueError('AnnualTaxExport requiere DDJJ y F22 preparados antes de emitir preview controlado.')
    official_format_source = _f22_export_format_source_from_bundle(source_bundle)
    summary = _annual_tax_export_summary(process, dossier, ddjj, f22, official_format_source)
    export, _ = AnnualTaxExport.objects.update_or_create(
        proceso_renta_anual=process,
        export_kind=TipoAnnualTaxExport.PREVIEW_PACKAGE,
        defaults={
            'empresa': process.empresa,
            'dossier': dossier,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'artifact_matrix': dossier.artifact_matrix,
            'official_format_source': official_format_source,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': process.anio_tributario - 1,
            'source_ref': f'annual-tax-export-source-{process.empresa_id}-at{process.anio_tributario}',
            'responsible_ref': dossier.responsible_ref,
            'export_ref': f'annual-tax-export-{process.empresa_id}-{process.anio_tributario}-controlled-preview-v1',
            'review_state': summary['review_state'],
            'target_items_total': summary['target_items_total'],
            'ddjj_items_total': summary['ddjj_items_total'],
            'f22_items_total': summary['f22_items_total'],
            'warnings_total': summary['warnings_total'],
            'official_format': False,
            'sii_submission': False,
            'final_tax_calculation': False,
            'export_payload': summary,
            'hash_export': _source_bundle_hash(summary),
            'estado': EstadoAnnualTaxExport.PREPARED,
        },
    )
    try:
        export.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxExport no cumple validacion de dominio: {reason}') from error
    export.save()
    AnnualTaxExport.objects.filter(
        empresa=process.empresa,
        anio_tributario=process.anio_tributario,
        estado=EstadoAnnualTaxExport.PREPARED,
    ).exclude(pk=export.pk).update(estado=EstadoAnnualTaxExport.RETIRED)
    return export


def _summary_warning_total(summary, key='by_id'):
    items = summary.get(key) if isinstance(summary, dict) else {}
    if not isinstance(items, dict):
        return 0
    total = 0
    for item in items.values():
        if not isinstance(item, dict):
            continue
        try:
            total += int(item.get('warnings_total') or 0)
        except (TypeError, ValueError):
            continue
    return total


def _summary_metric_total(summary, metric, key='by_id'):
    items = summary.get(key) if isinstance(summary, dict) else {}
    if not isinstance(items, dict):
        return 0
    total = 0
    for item in items.values():
        if not isinstance(item, dict):
            continue
        try:
            total += int(item.get(metric) or 0)
        except (TypeError, ValueError):
            continue
    return total


def _checklist_item(code, label, status, *, evidence_ref='', details=None):
    return {
        'code': code,
        'label': label,
        'status': status,
        'evidence_ref': evidence_ref,
        'details': details or {},
    }


def _annual_tax_review_checklist_summary(process, rule_set, source_bundle, dossier, annual_export):
    process_summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
    monthly_summary = process_summary.get('annual_tax_monthly_facts', {})
    workbook_summary = process_summary.get('annual_tax_workbooks', {})
    register_summary = process_summary.get('annual_enterprise_registers', {})
    real_estate_summary = process_summary.get('annual_real_estate_sections', {})
    ddjj_layout_summary = process_summary.get('annual_tax_ddjj_layouts', {})
    f22_export_layout_summary = process_summary.get('annual_tax_f22_export_layouts', {})
    matrix_summary = process_summary.get('annual_tax_artifact_matrices', {})
    dossier_summary = process_summary.get('annual_tax_dossiers', {})
    export_summary = process_summary.get('annual_tax_exports', {})
    matrix = dossier.artifact_matrix

    months = set(monthly_summary.get('months') or []) if isinstance(monthly_summary, dict) else set()
    workbook_types = set(workbook_summary.get('types') or []) if isinstance(workbook_summary, dict) else set()
    register_types = set(register_summary.get('types') or []) if isinstance(register_summary, dict) else set()
    matrix_review_counts = (
        next(iter(matrix_summary.get('by_id', {}).values()), {}).get('review_state_counts', {})
        if isinstance(matrix_summary.get('by_id'), dict)
        else {}
    )
    matrix_blocked = int(matrix_review_counts.get(EstadoAnnualTaxArtifactReview.BLOCKED) or 0)
    matrix_review_required = int(matrix_review_counts.get(EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW) or 0)
    matrix_warnings = _summary_warning_total(matrix_summary)
    matrix_pending_warnings = _summary_metric_total(matrix_summary, 'warnings_pending_review_total')
    workbook_warnings = _summary_warning_total(workbook_summary, key='by_type')
    workbook_pending_warnings = _summary_metric_total(workbook_summary, 'warnings_pending_review_total', key='by_type')
    register_warnings = _summary_warning_total(register_summary, key='by_type')
    register_pending_warnings = _summary_metric_total(register_summary, 'warnings_pending_review_total', key='by_type')
    real_estate_warnings = _summary_warning_total(real_estate_summary)
    ddjj_layout_missing = len(ddjj_layout_summary.get('missing_form_codes') or []) if isinstance(ddjj_layout_summary, dict) else 0
    ddjj_layout_warnings = _summary_warning_total(ddjj_layout_summary, key='by_form_code')
    f22_layout_missing = len(f22_export_layout_summary.get('missing_form_codes') or []) if isinstance(f22_export_layout_summary, dict) else 1
    f22_layout_warnings = _summary_warning_total(f22_export_layout_summary, key='by_form_code')

    items = [
        _checklist_item(
            'source_bundle_frozen',
            'AnnualTaxSourceBundle congelado y enlazado',
            'complete' if source_bundle.estado == EstadoAnnualTaxSourceBundle.FROZEN else 'blocking',
            evidence_ref=source_bundle.hash_fuentes,
            details={'source_bundle_id': source_bundle.id, 'source_kind': source_bundle.source_kind},
        ),
        _checklist_item(
            'tax_rules_approved',
            'Reglas tributarias anuales aprobadas y versionadas',
            'complete' if rule_set.estado == EstadoReglaTributariaAnual.APPROVED else 'blocking',
            evidence_ref=rule_set.hash_normativo,
            details={'rule_set_id': rule_set.id, 'official_source_id': rule_set.official_source_id},
        ),
        _checklist_item(
            'monthly_facts_complete',
            'Doce hechos tributarios mensuales normalizados',
            'complete' if set(range(1, 13)).issubset(months) else 'blocking',
            details={'months': sorted(months), 'total': monthly_summary.get('total') if isinstance(monthly_summary, dict) else 0},
        ),
        _checklist_item(
            'workbooks_rli_cpt',
            'Workbooks RLI y CPT preparados',
            'warning' if workbook_pending_warnings else ('complete' if {TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT}.issubset(workbook_types) else 'blocking'),
            details={
                'types': sorted(workbook_types),
                'warnings_total': workbook_warnings,
                'warnings_pending_review_total': workbook_pending_warnings,
            },
        ),
        _checklist_item(
            'enterprise_registers',
            'Registros empresariales preparados',
            'warning' if register_pending_warnings else ('complete' if register_types else 'blocking'),
            details={
                'types': sorted(register_types),
                'warnings_total': register_warnings,
                'warnings_pending_review_total': register_pending_warnings,
            },
        ),
        _checklist_item(
            'real_estate_support',
            'Bienes raices y contribuciones trazados como respaldo anual',
            'warning' if real_estate_warnings else ('complete' if int(real_estate_summary.get('total') or 0) > 0 else 'blocking'),
            details={'sections_total': real_estate_summary.get('total') if isinstance(real_estate_summary, dict) else 0, 'warnings_total': real_estate_warnings},
        ),
        _checklist_item(
            'ddjj_layouts',
            'Formularios DDJJ habilitados con medio, vencimiento y layout trazable',
            'blocking' if ddjj_layout_missing else ('warning' if ddjj_layout_warnings else 'complete'),
            details={
                'configured_form_codes': ddjj_layout_summary.get('configured_form_codes') if isinstance(ddjj_layout_summary, dict) else [],
                'form_codes': ddjj_layout_summary.get('form_codes') if isinstance(ddjj_layout_summary, dict) else [],
                'missing_form_codes': ddjj_layout_summary.get('missing_form_codes') if isinstance(ddjj_layout_summary, dict) else [],
                'warnings_total': ddjj_layout_warnings,
            },
        ),
        _checklist_item(
            'f22_export_layout',
            'F22 preparado contra layout/formato revisable sin presentacion automatica',
            'blocking' if f22_layout_missing else ('warning' if f22_layout_warnings else 'complete'),
            details={
                'form_codes': f22_export_layout_summary.get('form_codes') if isinstance(f22_export_layout_summary, dict) else [],
                'missing_form_codes': f22_export_layout_summary.get('missing_form_codes') if isinstance(f22_export_layout_summary, dict) else ['F22'],
                'warnings_total': f22_layout_warnings,
                'official_format': False,
                'sii_submission': False,
                'final_tax_calculation': False,
            },
        ),
        _checklist_item(
            'artifact_matrix',
            'Matriz DDJJ/F22 preparada y trazable',
            'blocking' if matrix_blocked else ('warning' if matrix_review_required or matrix_pending_warnings else 'complete'),
            evidence_ref=matrix.hash_matriz,
            details={
                'artifact_matrix_id': matrix.id,
                'items_total': matrix.items_total,
                'ddjj_items_total': matrix.ddjj_items_total,
                'f22_items_total': matrix.f22_items_total,
                'warnings_total': matrix_warnings,
                'warnings_pending_review_total': matrix_pending_warnings,
                'review_state_counts': matrix_review_counts,
            },
        ),
        _checklist_item(
            'dossier_review_package',
            'Dossier anual preparado para revision responsable',
            'blocking' if dossier.review_state == EstadoAnnualTaxArtifactReview.BLOCKED else (
                'warning' if dossier.review_state == EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW else 'complete'
            ),
            evidence_ref=dossier.hash_dossier,
            details={'dossier_id': dossier.id, 'review_state': dossier.review_state, 'warnings_total': dossier.warnings_total},
        ),
        _checklist_item(
            'local_export_preview',
            'Export local controlado preparado sin formato oficial ni presentacion',
            'blocking' if annual_export.review_state == EstadoAnnualTaxArtifactReview.BLOCKED else (
                'warning' if annual_export.review_state == EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW else 'complete'
            ),
            evidence_ref=annual_export.hash_export,
            details={'annual_export_id': annual_export.id, 'review_state': annual_export.review_state, 'warnings_total': annual_export.warnings_total},
        ),
        _checklist_item(
            'external_boundary',
            'Frontera externa mantiene F22 oficial, presentacion SII y calculo final fuera del motor local',
            'complete' if (
                annual_export.official_format is False
                and annual_export.sii_submission is False
                and annual_export.final_tax_calculation is False
            ) else 'blocking',
            details={
                'official_format': annual_export.official_format,
                'sii_submission': annual_export.sii_submission,
                'final_tax_calculation': annual_export.final_tax_calculation,
                'requires_explicit_submission_authorization': True,
            },
        ),
    ]
    items_total = len(items)
    completed_items_total = sum(1 for item in items if item['status'] == 'complete')
    blockers_total = sum(1 for item in items if item['status'] == 'blocking')
    warnings_total = sum(1 for item in items if item['status'] == 'warning')
    return {
        'empresa_id': process.empresa_id,
        'proceso_renta_anual_id': process.id,
        'dossier_id': dossier.id,
        'annual_export_id': annual_export.id,
        'source_bundle_id': source_bundle.id,
        'rule_set_id': rule_set.id,
        'artifact_matrix_id': matrix.id,
        'anio_tributario': process.anio_tributario,
        'anio_comercial': process.anio_tributario - 1,
        'items_total': items_total,
        'completed_items_total': completed_items_total,
        'blockers_total': blockers_total,
        'warnings_total': warnings_total,
        'items': items,
        'component_summaries': {
            'annual_tax_ddjj_layouts': ddjj_layout_summary,
            'annual_tax_f22_export_layouts': f22_export_layout_summary,
            'annual_tax_dossiers': dossier_summary,
            'annual_tax_exports': export_summary,
        },
        'official_format': False,
        'sii_submission': False,
        'sii_submission_attempted': False,
        'final_tax_calculation': False,
        'requires_responsible_review': True,
        'leasemanager_boundary': 'preparation_and_evidence_only',
    }


def sync_annual_tax_review_checklist(process, rule_set, source_bundle):
    dossier = AnnualTaxDossier.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxDossier.PREPARED,
    )
    annual_export = AnnualTaxExport.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxExport.PREPARED,
        export_kind=TipoAnnualTaxExport.PREVIEW_PACKAGE,
    )
    summary = _annual_tax_review_checklist_summary(process, rule_set, source_bundle, dossier, annual_export)
    checklist, _ = AnnualTaxReviewChecklist.objects.update_or_create(
        proceso_renta_anual=process,
        defaults={
            'empresa': process.empresa,
            'dossier': dossier,
            'annual_export': annual_export,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'artifact_matrix': dossier.artifact_matrix,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': process.anio_tributario - 1,
            'checklist_ref': f'annual-tax-review-checklist-{process.empresa_id}-at{process.anio_tributario}-v1',
            'responsible_ref': dossier.responsible_ref or process.responsable_revision_ref or 'annual-tax-review-owner',
            'evidence_ref': f'annual-tax-review-evidence-{process.empresa_id}-at{process.anio_tributario}',
            'items_total': summary['items_total'],
            'completed_items_total': summary['completed_items_total'],
            'blockers_total': summary['blockers_total'],
            'warnings_total': summary['warnings_total'],
            'review_payload': summary,
            'hash_checklist': _source_bundle_hash(summary),
            'estado': EstadoAnnualTaxReviewChecklist.PREPARED,
        },
    )
    try:
        checklist.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxReviewChecklist no cumple validacion de dominio: {reason}') from error
    checklist.save()
    AnnualTaxReviewChecklist.objects.filter(
        empresa=process.empresa,
        anio_tributario=process.anio_tributario,
        estado=EstadoAnnualTaxReviewChecklist.PREPARED,
    ).exclude(pk=checklist.pk).update(estado=EstadoAnnualTaxReviewChecklist.RETIRED)
    return checklist


def _ensure_annual_tax_support_policy_and_template():
    policy, _ = PoliticaFirmaYNotaria.objects.get_or_create(
        tipo_documental=TipoDocumental.TAX_SUPPORT,
        defaults={
            'requiere_firma_arrendador': False,
            'requiere_firma_arrendatario': False,
            'requiere_codeudor': False,
            'requiere_notaria': False,
            'modo_firma_permitido': ModoFirmaPermitido.SIMPLE,
            'estado': EstadoPoliticaFirma.ACTIVE,
        },
    )
    if policy.estado != EstadoPoliticaFirma.ACTIVE:
        raise ValueError('Respaldo tributario requiere PoliticaFirmaYNotaria activa.')

    template, _ = PlantillaDocumental.objects.get_or_create(
        tipo_documental=TipoDocumental.TAX_SUPPORT,
        version_plantilla=ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION,
        defaults={
            'plantilla_ref': 'templates/respaldo_tributario/stage6-v1',
            'checksum_plantilla': _source_bundle_hash(
                {
                    'template': 'annual_tax_support_document',
                    'version': ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION,
                    'scope': 'controlled-preview',
                }
            ),
            'descripcion': 'Plantilla controlada para respaldo tributario anual revisable.',
            'estado': EstadoPlantillaDocumental.ACTIVE,
        },
    )
    if template.estado != EstadoPlantillaDocumental.ACTIVE:
        raise ValueError('Respaldo tributario requiere PlantillaDocumental activa.')
    return policy, template


def _annual_tax_support_actor_user():
    UserModel = get_user_model()
    user, created = UserModel.objects.get_or_create(
        username='system-annual-tax-support',
        defaults={'is_active': True},
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=['password'])
    return user


def _annual_tax_support_expediente(process):
    expediente, _ = ExpedienteDocumental.objects.get_or_create(
        entidad_tipo='proceso_renta_anual',
        entidad_id=str(process.pk),
        defaults={'owner_operativo': 'tributario-stage6'},
    )
    try:
        expediente.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'ExpedienteDocumental de respaldo tributario no cumple validacion: {reason}') from error
    return expediente


def _annual_tax_support_lines(process, source_bundle, dossier, annual_export, checklist):
    return [
        f'Proceso renta anual: proceso-renta-anual-{process.pk}',
        f'Empresa ref: empresa-{process.empresa_id}',
        f'AT {process.anio_tributario} / AC {process.anio_tributario - 1}',
        f'Source bundle: {source_bundle.pk} hash {str(source_bundle.hash_fuentes or "")[:16]}',
        f'Dossier: {dossier.pk} hash {str(dossier.hash_dossier or "")[:16]}',
        f'Export preview: {annual_export.pk} hash {str(annual_export.hash_export or "")[:16]}',
        f'Checklist: {checklist.pk} complete {checklist.completed_items_total}/{checklist.items_total}',
        f'Checklist blockers: {checklist.blockers_total} warnings: {checklist.warnings_total}',
        f'Matriz items: {dossier.artifact_matrix.items_total}',
        f'DDJJ items: {dossier.artifact_matrix.ddjj_items_total}',
        f'F22 items: {dossier.artifact_matrix.f22_items_total}',
        'Alcance: preparacion local controlada y revisable.',
        'No acredita formato oficial SII.',
        'No registra presentacion SII.',
        'No es calculo tributario final.',
    ]


def sync_annual_tax_support_document(process):
    source_bundle = process.source_bundle
    if source_bundle is None:
        raise ValueError('Respaldo tributario requiere AnnualTaxSourceBundle enlazado al proceso.')
    dossier = AnnualTaxDossier.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxDossier.PREPARED,
    )
    annual_export = AnnualTaxExport.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxExport.PREPARED,
        export_kind=TipoAnnualTaxExport.PREVIEW_PACKAGE,
    )
    checklist = AnnualTaxReviewChecklist.objects.get(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxReviewChecklist.PREPARED,
    )
    _ensure_annual_tax_support_policy_and_template()
    expediente = _annual_tax_support_expediente(process)
    actor_user = _annual_tax_support_actor_user()
    title = f'Respaldo tributario controlado AT{process.anio_tributario}'
    lines = _annual_tax_support_lines(process, source_bundle, dossier, annual_export, checklist)
    payload = build_generated_pdf_payload(
        tipo_documental=TipoDocumental.TAX_SUPPORT,
        version_plantilla=ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION,
        titulo=title,
        lineas=lines,
    )
    existing = DocumentoEmitido.objects.filter(
        expediente=expediente,
        tipo_documental=TipoDocumental.TAX_SUPPORT,
        version_plantilla=ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION,
        checksum=payload['checksum'],
        storage_ref=payload['storage_ref'],
        estado__in=[EstadoDocumento.ISSUED, EstadoDocumento.FORMALIZED, EstadoDocumento.ARCHIVED],
    ).first()
    if existing is not None:
        try:
            existing.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'DocumentoEmitido de respaldo tributario no cumple validacion: {reason}') from error
        return existing

    preview_generated_pdf_document(
        expediente=expediente,
        tipo_documental=TipoDocumental.TAX_SUPPORT,
        version_plantilla=ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION,
        titulo=title,
        lineas=lines,
        actor_user=actor_user,
    )
    document, _pdf_bytes = emit_generated_pdf_document(
        expediente=expediente,
        tipo_documental=TipoDocumental.TAX_SUPPORT,
        version_plantilla=ANNUAL_TAX_SUPPORT_TEMPLATE_VERSION,
        titulo=title,
        lineas=lines,
        actor_user=actor_user,
    )
    return document


def freeze_annual_tax_source_bundle(
    empresa,
    anio_tributario,
    config,
    rule_set,
    *,
    source_kind=SourceKindRentaAnual.LOCAL,
    source_label='',
    authorization_ref='',
    responsible_ref='',
):
    fiscal_year = anio_tributario - 1
    sync_monthly_tax_facts(empresa, fiscal_year)
    summary = build_annual_tax_source_summary(empresa, fiscal_year, config, rule_set)
    source_label = str(source_label or f'annual-source-{empresa.id}-at{anio_tributario}-{source_kind}').strip()
    responsible_ref = str(responsible_ref or 'system-annual-source-bundle').strip()
    hash_fuentes = _source_bundle_hash(summary)
    bundle = AnnualTaxSourceBundle.objects.filter(
        empresa=empresa,
        anio_tributario=anio_tributario,
        estado=EstadoAnnualTaxSourceBundle.FROZEN,
    ).first()
    if bundle is not None:
        if bundle.hash_fuentes != hash_fuentes:
            raise ValueError(
                'AnnualTaxSourceBundle congelado existente no coincide con las fuentes anuales actuales.'
            )
        try:
            bundle.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'AnnualTaxSourceBundle congelado existente no es valido: {reason}') from error
        sync_monthly_tax_facts(bundle.empresa, bundle.anio_comercial)
        return bundle

    bundle = AnnualTaxSourceBundle(
        empresa=empresa,
        anio_tributario=anio_tributario,
    )
    bundle.anio_comercial = fiscal_year
    bundle.source_kind = source_kind
    bundle.source_label = source_label
    bundle.authorization_ref = str(authorization_ref or '').strip()
    bundle.responsible_ref = responsible_ref
    bundle.hash_fuentes = hash_fuentes
    bundle.resumen_fuentes = summary
    bundle.estado = EstadoAnnualTaxSourceBundle.FROZEN
    try:
        bundle.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualTaxSourceBundle no cumple validacion de dominio: {reason}') from error
    bundle.save()
    sync_monthly_tax_facts(bundle.empresa, bundle.anio_comercial)
    return bundle


def validate_annual_readiness(empresa, anio_tributario):
    config = validate_company_fiscal_readiness(empresa)
    fiscal_year = anio_tributario - 1
    approved_closes = empresa.cierres_mensuales_contables.filter(anio=fiscal_year, estado='aprobado').count()
    if approved_closes != 12:
        raise ValueError('La preparacion anual requiere doce cierres mensuales aprobados del año comercial.')
    rule_set = get_approved_tax_year_rule_set(config, anio_tributario)
    return config, fiscal_year, rule_set


def build_annual_summary(empresa, fiscal_year, rule_set, source_bundle, process=None):
    obligations = ObligacionTributariaMensual.objects.filter(empresa=empresa, anio=fiscal_year)
    total_obligations = obligations.count()
    total_monto = sum((item.monto_calculado for item in obligations), 0)
    monthly_facts = MonthlyTaxFact.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
        estado=EstadoMonthlyTaxFact.NORMALIZED,
    ).order_by('mes')
    monthly_fact_months = sorted(set(monthly_facts.values_list('mes', flat=True)))
    monthly_fact_totals = {
        'obligations_total': 0,
        'rent_distributions_total': 0,
        'liquidation_lines_total': 0,
    }
    for fact in monthly_facts:
        payload = fact.resumen_hecho if isinstance(fact.resumen_hecho, dict) else {}
        for key in monthly_fact_totals:
            try:
                monthly_fact_totals[key] += int(payload.get(key) or 0)
            except (TypeError, ValueError):
                continue
    summary = {
        'fiscal_year': fiscal_year,
        'obligaciones': [
            {
                'anio': item.anio,
                'mes': item.mes,
                'tipo': item.obligacion_tipo,
                'monto_calculado': str(item.monto_calculado),
                'estado_preparacion': item.estado_preparacion,
            }
            for item in obligations.order_by('mes', 'obligacion_tipo')
        ],
        'total_obligaciones': total_obligations,
        'total_monto_calculado': str(total_monto),
        'tax_year_rule_set': {
            'id': rule_set.id,
            'anio_tributario': rule_set.anio_tributario,
            'regimen_tributario': rule_set.regimen_tributario.codigo_regimen,
            'version': rule_set.version,
            'estado': rule_set.estado,
            'hash_normativo': rule_set.hash_normativo,
            'mapeos_activos_por_destino': _tax_mapping_counts_by_target(rule_set),
        },
        'annual_tax_source_bundle': {
            'id': source_bundle.id,
            'source_kind': source_bundle.source_kind,
            'source_label': source_bundle.source_label,
            'hash_fuentes': source_bundle.hash_fuentes,
            'anio_comercial': source_bundle.anio_comercial,
            'approved_closes_total': source_bundle.resumen_fuentes.get('approved_closes_total', 0),
            'obligations_total': source_bundle.resumen_fuentes.get('obligations_total', 0),
            'f29_preparations_total': source_bundle.resumen_fuentes.get('f29_preparations_total', 0),
            'real_estate_properties_total': source_bundle.resumen_fuentes.get('real_estate_properties_total', 0),
        },
        'annual_tax_monthly_facts': {
            'total': monthly_facts.count(),
            'months': monthly_fact_months,
            **monthly_fact_totals,
        },
    }
    if process is not None:
        summary['annual_tax_trial_balances'] = summarize_annual_tax_trial_balances(process)
        summary['annual_tax_workbooks'] = summarize_annual_tax_workbooks(process)
        summary['annual_enterprise_registers'] = summarize_annual_enterprise_registers(process)
        summary['annual_real_estate_sections'] = summarize_annual_real_estate_sections(process)
        summary['annual_tax_ddjj_layouts'] = summarize_annual_tax_ddjj_layouts(process)
        summary['annual_tax_f22_export_layouts'] = summarize_annual_tax_f22_export_layouts(process)
        summary['annual_tax_artifact_matrices'] = summarize_annual_tax_artifact_matrices(process)
        summary['annual_tax_dossiers'] = summarize_annual_tax_dossiers(process)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
        summary['annual_tax_review_checklists'] = summarize_annual_tax_review_checklists(process)
    return summary


def generate_annual_preparation(empresa, anio_tributario):
    config, fiscal_year, rule_set = validate_annual_readiness(empresa, anio_tributario)
    source_bundle = freeze_annual_tax_source_bundle(empresa, anio_tributario, config, rule_set)
    summary = build_annual_summary(empresa, fiscal_year, rule_set, source_bundle)
    process, _ = ProcesoRentaAnual.objects.get_or_create(
        empresa=empresa,
        anio_tributario=anio_tributario,
    )
    process.source_bundle = source_bundle
    process.fecha_preparacion = timezone.now()
    process.resumen_anual = summary
    process.estado = EstadoPreparacionTributaria.PREPARED
    process.save()
    sync_annual_tax_trial_balance(process, rule_set, source_bundle)
    sync_annual_tax_workbooks(process, rule_set, source_bundle)
    sync_annual_enterprise_registers(process, rule_set, source_bundle)
    sync_annual_real_estate_section(process, rule_set, source_bundle)
    summary = build_annual_summary(empresa, fiscal_year, rule_set, source_bundle, process=process)
    process.resumen_anual = summary
    process.save(update_fields=['resumen_anual', 'updated_at'])
    sync_annual_tax_artifact_matrix(process, rule_set, source_bundle, config)
    summary = build_annual_summary(empresa, fiscal_year, rule_set, source_bundle, process=process)
    process.resumen_anual = summary
    process.save(update_fields=['resumen_anual', 'updated_at'])
    sync_annual_tax_dossier(process, rule_set, source_bundle)
    summary = build_annual_summary(empresa, fiscal_year, rule_set, source_bundle, process=process)
    process.resumen_anual = summary
    process.save(update_fields=['resumen_anual', 'updated_at'])

    ddjj_enabled = bool(config.ddjj_habilitadas)
    ddjj_capability = get_active_annual_capability(empresa, CapacidadSII.DDJJ_PREPARACION)
    ddjj_state = EstadoPreparacionTributaria.PREPARED if ddjj_enabled else EstadoPreparacionTributaria.PENDING_DATA
    ddjj, _ = DDJJPreparacionAnual.objects.get_or_create(
        empresa=empresa,
        anio_tributario=anio_tributario,
        defaults={
            'capacidad_tributaria': ddjj_capability,
            'proceso_renta_anual': process,
        },
    )
    ddjj.capacidad_tributaria = ddjj_capability
    ddjj.proceso_renta_anual = process
    ddjj.estado_preparacion = ddjj_state
    ddjj.resumen_paquete = {
        'ddjj_habilitadas': config.ddjj_habilitadas,
        'resumen_anual': summary,
    }
    ddjj.save()

    f22_capability = get_active_annual_capability(empresa, CapacidadSII.F22_PREPARACION)
    f22, _ = F22PreparacionAnual.objects.get_or_create(
        empresa=empresa,
        anio_tributario=anio_tributario,
        defaults={
            'capacidad_tributaria': f22_capability,
            'proceso_renta_anual': process,
        },
    )
    f22.capacidad_tributaria = f22_capability
    f22.proceso_renta_anual = process
    f22.estado_preparacion = EstadoPreparacionTributaria.PREPARED
    f22.resumen_f22 = {
        'resumen_anual': summary,
        'regimen_tributario': config.regimen_tributario.codigo_regimen,
    }
    f22.save()

    process.paquete_ddjj_ref = ddjj.paquete_ref
    process.borrador_f22_ref = f22.borrador_ref
    process.save(update_fields=['paquete_ddjj_ref', 'borrador_f22_ref', 'updated_at'])
    sync_annual_tax_export(process, rule_set, source_bundle)
    summary = build_annual_summary(empresa, fiscal_year, rule_set, source_bundle, process=process)
    process.resumen_anual = summary
    process.save(update_fields=['resumen_anual', 'updated_at'])
    sync_annual_tax_review_checklist(process, rule_set, source_bundle)
    summary = build_annual_summary(empresa, fiscal_year, rule_set, source_bundle, process=process)
    process.resumen_anual = summary
    process.save(update_fields=['resumen_anual', 'updated_at'])
    sync_annual_tax_support_document(process)
    return process, ddjj, f22


def register_annual_status(document, *, estado_preparacion, ref_value='', observaciones='', responsable_revision_ref=''):
    if estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
        raise ValueError('SII.PresentacionAnualFinal esta podada del v1 y requiere reemision formal del set.')
    current_ref = ''
    if hasattr(document, 'paquete_ref'):
        current_ref = document.paquete_ref
    if hasattr(document, 'borrador_ref'):
        current_ref = document.borrador_ref
    input_ref = _ensure_non_sensitive_reference(ref_value, 'ref_value')
    input_responsable = _ensure_non_sensitive_reference(responsable_revision_ref, 'responsable_revision_ref')
    input_observaciones = _ensure_non_sensitive_text(observaciones, 'observaciones')
    next_ref = input_ref or current_ref
    next_responsable = input_responsable or document.responsable_revision_ref
    if estado_preparacion in TAX_STATUS_REQUIRING_GATE:
        ensure_sii_capability_ready(document.capacidad_tributaria, document.capacidad_tributaria.capacidad_key)
    if estado_preparacion in TAX_STATUS_REQUIRING_REF:
        if not next_ref:
            raise ValueError('Aprobar u observar preparacion anual requiere referencia trazable.')
        _ensure_non_sensitive_reference(next_ref, 'ref_value')
        if not next_responsable:
            raise ValueError('Aprobar u observar preparacion anual requiere responsable_revision_ref trazable.')
        _ensure_non_sensitive_reference(next_responsable, 'responsable_revision_ref')

    document.estado_preparacion = estado_preparacion
    if hasattr(document, 'paquete_ref') and input_ref:
        document.paquete_ref = input_ref
    if hasattr(document, 'borrador_ref') and input_ref:
        document.borrador_ref = input_ref
    if input_responsable:
        document.responsable_revision_ref = input_responsable
    if input_observaciones:
        document.observaciones = input_observaciones
    if estado_preparacion in TAX_STATUS_REQUIRING_GATE:
        _ensure_artifact_valid_for_status_transition(document, 'Preparacion anual SII')
    fields = ['estado_preparacion', 'updated_at']
    if hasattr(document, 'paquete_ref'):
        fields.append('paquete_ref')
    if hasattr(document, 'borrador_ref'):
        fields.append('borrador_ref')
    fields.append('responsable_revision_ref')
    if hasattr(document, 'observaciones'):
        fields.append('observaciones')
    document.save(update_fields=fields)

    process = getattr(document, 'proceso_renta_anual', None)
    if process and (input_ref or input_responsable):
        if hasattr(document, 'paquete_ref') and input_ref:
            process.paquete_ddjj_ref = input_ref
        if hasattr(document, 'borrador_ref') and input_ref:
            process.borrador_f22_ref = input_ref
        if input_responsable:
            process.responsable_revision_ref = input_responsable
        process.save(update_fields=['paquete_ddjj_ref', 'borrador_f22_ref', 'responsable_revision_ref', 'updated_at'])
    return document
