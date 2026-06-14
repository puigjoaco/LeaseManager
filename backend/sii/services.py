import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q

from contabilidad.models import (
    CierreMensualContable,
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

from .models import (
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxSourceBundle,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadSII,
    DDJJPreparacionAnual,
    DestinoMapeoTributarioAnual,
    DTEEmitido,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualRealEstateSection,
    EstadoAnnualTaxArtifactMatrix,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
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
    TipoAnnualTaxWorkbook,
    TipoDTE,
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
    liquidation_lines = LineaLiquidacionMensual.objects.filter(
        liquidacion__owner_tipo=TipoOwnerLiquidacion.COMPANY,
        liquidacion__empresa=empresa,
        liquidacion__anio=fiscal_year,
        liquidacion__estado__in=[EstadoLiquidacionMensual.PREPARED, EstadoLiquidacionMensual.APPROVED],
    ).select_related('liquidacion')
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
        'real_estate_contribuciones_source': 'not_loaded_v1',
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


def _decimal_from_monthly_payload(payload, key):
    if not isinstance(payload, dict):
        return Decimal('0.00')
    try:
        return Decimal(str(payload.get(key) or '0.00'))
    except Exception:
        return Decimal('0.00')


def _line_amount_from_mapping(mapping, monthly_facts):
    metadata = mapping.metadata if isinstance(mapping.metadata, dict) else {}
    source_metric = str(metadata.get('source_metric') or '').strip()
    warnings = []
    if source_metric not in MONTHLY_FACT_SOURCE_METRICS:
        warnings.append('source_metric_missing_or_unsupported')
        return Decimal('0.00'), source_metric, warnings

    payload_key = MONTHLY_FACT_SOURCE_METRICS[source_metric]
    amount = Decimal('0.00')
    months = []
    for fact in monthly_facts:
        amount += _decimal_from_monthly_payload(fact.resumen_hecho, payload_key)
        months.append(fact.mes)
    if sorted(set(months)) != list(range(1, 13)):
        warnings.append('monthly_tax_facts_not_complete')
    return amount, source_metric, warnings


def _line_hash_payload(line_payload):
    return hashlib.sha256(_canonical_source_payload(line_payload).encode('utf-8')).hexdigest()


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


def summarize_annual_tax_workbooks(process):
    workbooks = AnnualTaxWorkbook.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
    ).order_by('tipo')
    by_type = {}
    for workbook in workbooks:
        active_lines = workbook.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'codigo_destino')
        warning_count = 0
        for line in active_lines:
            warnings = line.warnings if isinstance(line.warnings, list) else []
            warning_count += len(warnings)
        by_type[workbook.tipo] = {
            'id': workbook.id,
            'hash_workbook': workbook.hash_workbook,
            'lines_total': active_lines.count(),
            'warnings_total': warning_count,
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
        for movement in active_movements:
            warnings = movement.warnings if isinstance(movement.warnings, list) else []
            warning_count += len(warnings)
        by_type[register.tipo_registro] = {
            'id': register.id,
            'hash_registro': register.hash_registro,
            'saldo_inicial_clp': str(register.saldo_inicial_clp),
            'movimientos_total_clp': str(register.movimientos_total_clp),
            'saldo_final_clp': str(register.saldo_final_clp),
            'movements_total': active_movements.count(),
            'warnings_total': warning_count,
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
        by_id[str(section.id)] = {
            'id': section.id,
            'hash_seccion': section.hash_seccion,
            'propiedades_total': section.propiedades_total,
            'arriendo_devengado_total_clp': str(section.arriendo_devengado_total_clp),
            'arriendo_conciliado_total_clp': str(section.arriendo_conciliado_total_clp),
            'arriendo_facturable_total_clp': str(section.arriendo_facturable_total_clp),
            'contribuciones_total_clp': str(section.contribuciones_total_clp),
            'items_total': active_items.count(),
            'warnings_total': warning_count,
        }
    return {
        'total': sections.count(),
        'ids': sorted(by_id.keys()),
        'by_id': by_id,
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
        review_state_counts = {}
        for item in active_items:
            warnings = item.warnings if isinstance(item.warnings, list) else []
            warning_count += len(warnings)
            review_state_counts[item.review_state] = review_state_counts.get(item.review_state, 0) + 1
        by_id[str(matrix.id)] = {
            'id': matrix.id,
            'hash_matriz': matrix.hash_matriz,
            'items_total': matrix.items_total,
            'ddjj_items_total': matrix.ddjj_items_total,
            'f22_items_total': matrix.f22_items_total,
            'active_items_total': active_items.count(),
            'warnings_total': warning_count,
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
            'review_state': export.review_state,
            'target_items_total': export.target_items_total,
            'ddjj_items_total': export.ddjj_items_total,
            'f22_items_total': export.f22_items_total,
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


def sync_annual_tax_workbooks(process, rule_set, source_bundle):
    fiscal_year = process.anio_tributario - 1
    monthly_facts = list(
        MonthlyTaxFact.objects.filter(
            empresa=process.empresa,
            anio=fiscal_year,
            estado=EstadoMonthlyTaxFact.NORMALIZED,
        ).order_by('mes')
    )
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
            amount, source_metric, warnings = _line_amount_from_mapping(mapping, monthly_facts)
            line_source_payload = {
                'source': 'monthly_tax_facts',
                'source_metric': source_metric,
                'monthly_tax_fact_ids': [fact.id for fact in monthly_facts],
                'months': [fact.mes for fact in monthly_facts],
                'mapping_id': mapping.id,
                'rule_set_id': rule_set.id,
            }
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
        active_lines = list(workbook.lines.filter(estado=EstadoRegistro.ACTIVE).order_by('codigo_interno', 'codigo_destino'))
        warning_count = sum(len(line.warnings or []) for line in active_lines if isinstance(line.warnings, list))
        workbook_summary = {
            'empresa_id': process.empresa_id,
            'proceso_renta_anual_id': process.id,
            'source_bundle_id': source_bundle.id,
            'rule_set_id': rule_set.id,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': fiscal_year,
            'tipo': workbook_type,
            'lines_total': len(active_lines),
            'warnings_total': warning_count,
            'line_hashes': [line.hash_linea for line in active_lines],
            'source': 'TaxCodeMapping + MonthlyTaxFact',
            'final_tax_calculation': False,
        }
        workbook.resumen_workbook = workbook_summary
        workbook.hash_workbook = _source_bundle_hash(workbook_summary)
        workbook.estado = EstadoAnnualTaxWorkbook.PREPARED
        try:
            workbook.full_clean()
        except ValidationError as error:
            reason = _first_validation_error(error)
            raise ValueError(f'AnnualTaxWorkbook no cumple validacion de dominio: {reason}') from error
        workbook.save()
        workbooks.append(workbook)

    AnnualTaxWorkbook.objects.filter(
        proceso_renta_anual=process,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
    ).exclude(id__in=[workbook.id for workbook in workbooks]).update(estado=EstadoAnnualTaxWorkbook.RETIRED)
    return workbooks


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
    movement_payload = {
        'register_set_id': register.id,
        'source_workbook_line_id': getattr(source_workbook_line, 'id', None),
        'codigo_interno': codigo_interno,
        'origen': origen,
        'signo': SignoAnnualTaxLine.INFO,
        'monto_clp': str(monto),
        'formula_ref': formula_ref,
        'evidencia_ref': evidencia_ref,
        'warnings': warnings,
        'source_payload': source_payload,
    }
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
            'warnings': warnings,
            'source_payload': source_payload,
            'hash_movimiento': _source_bundle_hash(movement_payload),
            'estado': EstadoRegistro.ACTIVE,
        },
    )
    try:
        movement.full_clean()
    except ValidationError as error:
        reason = _first_validation_error(error)
        raise ValueError(f'AnnualEnterpriseRegisterMovement no cumple validacion de dominio: {reason}') from error
    movement.save()
    return movement


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
        movement = _save_enterprise_movement(
            register,
            source_workbook_line=source_line,
            codigo_interno=f'{register_type.lower()}.{source_line.id}',
            origen=f'annual_tax_workbook:{source_line.workbook.tipo}:{code_suffix}'[:64],
            monto=source_line.monto_clp,
            formula_ref=getattr(target_mapping, 'formula_ref', '') or source_line.formula_ref,
            evidencia_ref=getattr(target_mapping, 'evidencia_ref', '') or source_line.evidencia_ref,
            warnings=warnings,
            source_payload={
                'source': 'annual_tax_workbook_line',
                'register_type': register_type,
                'source_workbook_id': source_line.workbook_id,
                'source_workbook_hash': source_line.workbook.hash_workbook,
                'source_line_id': source_line.id,
                'source_line_hash': source_line.hash_linea,
                'target_mapping_id': getattr(target_mapping, 'id', None),
                'final_tax_calculation': False,
            },
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


def _quantize_clp(value):
    return Decimal(str(value or '0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


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
        'formula_ref': 'real-estate-annual-section-v1',
        'evidencia_ref': f'real-estate-property-{propiedad.id}-annual-source',
        'warnings': [],
        'source_payload': payload['source_payload'],
    }


def _save_real_estate_item(section, source):
    propiedad = source['propiedad']
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
        'contribuciones_source': 'not_loaded_v1',
        'final_tax_calculation': False,
    }
    payload = {
        'arriendo_devengado_clp': _quantize_clp(source['arriendo_devengado_clp']),
        'arriendo_conciliado_clp': _quantize_clp(source['arriendo_conciliado_clp']),
        'arriendo_facturable_clp': _quantize_clp(source['arriendo_facturable_clp']),
        'contribuciones_clp': _quantize_clp(source['contribuciones_clp']),
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
            'warnings': [],
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
        'contribuciones_source': 'not_loaded_v1',
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


def sync_annual_real_estate_section(process, rule_set, source_bundle):
    fiscal_year = process.anio_tributario - 1
    section, _ = AnnualRealEstateSection.objects.update_or_create(
        proceso_renta_anual=process,
        defaults={
            'empresa': process.empresa,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'anio_tributario': process.anio_tributario,
            'anio_comercial': fiscal_year,
            'source_ref': f'annual-real-estate-section-{process.empresa_id}-at{process.anio_tributario}',
            'responsible_ref': 'system-annual-real-estate-normalizer',
            'estado': EstadoAnnualRealEstateSection.DRAFT,
        },
    )
    active_item_ids = []
    for source in _real_estate_property_sources(process.empresa, fiscal_year):
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


def _artifact_review_state(warnings):
    return (
        EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
        if warnings
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
        'warnings': spec['warnings'],
        'source_payload': spec['source_payload'],
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
        'warnings': normalized_warnings,
        'source_payload': payload,
    })


def _artifact_matrix_specs(matrix, rule_set, source_bundle, config):
    specs = []
    ddjj_enabled = bool(config.ddjj_habilitadas)
    for form_code in sorted(config.ddjj_habilitadas or []):
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
                    'contribuciones_source': 'not_loaded_v1',
                },
            )
    return specs


def _save_artifact_matrix_item(matrix, spec):
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
    for item in active_items:
        target_counts[item.target_kind] = target_counts.get(item.target_kind, 0) + 1
        review_state_counts[item.review_state] = review_state_counts.get(item.review_state, 0) + 1
        warnings = item.warnings if isinstance(item.warnings, list) else []
        warning_count += len(warnings)
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
        warnings = item.warnings if isinstance(item.warnings, list) else []
        if warnings:
            return EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW
    return EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW


def _annual_tax_dossier_summary(process, rule_set, source_bundle, matrix):
    process_summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
    matrix_summary = summarize_annual_tax_artifact_matrices(process)
    monthly_summary = process_summary.get('annual_tax_monthly_facts', {})
    workbook_summary = process_summary.get('annual_tax_workbooks', {})
    register_summary = process_summary.get('annual_enterprise_registers', {})
    real_estate_summary = process_summary.get('annual_real_estate_sections', {})
    active_items = matrix.items.filter(estado=EstadoRegistro.ACTIVE).order_by(
        'target_kind',
        'target_code',
        'source_kind',
        'source_model',
        'source_object_id',
    )
    warnings_total = 0
    review_state_counts = {}
    item_refs = []
    for item in active_items:
        warnings = item.warnings if isinstance(item.warnings, list) else []
        warnings_total += len(warnings)
        review_state_counts[item.review_state] = review_state_counts.get(item.review_state, 0) + 1
        item_refs.append(
            {
                'id': item.id,
                'target_kind': item.target_kind,
                'target_code': item.target_code,
                'source_kind': item.source_kind,
                'source_model': item.source_model,
                'source_object_id': item.source_object_id,
                'source_hash': item.source_hash,
                'hash_item': item.hash_item,
                'review_state': item.review_state,
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
            'annual_tax_artifact_matrices': matrix_summary,
        },
        'matrix_items_total': artifact_matrix_items_total,
        'ddjj_items_total': matrix.ddjj_items_total,
        'f22_items_total': matrix.f22_items_total,
        'warnings_total': warnings_total,
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


def _annual_tax_export_summary(process, dossier, ddjj, f22):
    dossier_summary = dossier.resumen_dossier if isinstance(dossier.resumen_dossier, dict) else {}
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
        'ddjj_preparacion_id': ddjj.id if ddjj else None,
        'ddjj_estado_preparacion': ddjj.estado_preparacion if ddjj else '',
        'f22_preparacion_id': f22.id if f22 else None,
        'f22_estado_preparacion': f22.estado_preparacion if f22 else '',
        'target_items_total': ddjj_items_total + f22_items_total,
        'ddjj_items_total': ddjj_items_total,
        'f22_items_total': f22_items_total,
        'warnings_total': dossier.warnings_total,
        'review_state': dossier.review_state,
        'export_items': export_items,
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
    summary = _annual_tax_export_summary(process, dossier, ddjj, f22)
    export, _ = AnnualTaxExport.objects.update_or_create(
        proceso_renta_anual=process,
        export_kind=TipoAnnualTaxExport.PREVIEW_PACKAGE,
        defaults={
            'empresa': process.empresa,
            'dossier': dossier,
            'source_bundle': source_bundle,
            'rule_set': rule_set,
            'artifact_matrix': dossier.artifact_matrix,
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
        summary['annual_tax_workbooks'] = summarize_annual_tax_workbooks(process)
        summary['annual_enterprise_registers'] = summarize_annual_enterprise_registers(process)
        summary['annual_real_estate_sections'] = summarize_annual_real_estate_sections(process)
        summary['annual_tax_artifact_matrices'] = summarize_annual_tax_artifact_matrices(process)
        summary['annual_tax_dossiers'] = summarize_annual_tax_dossiers(process)
        summary['annual_tax_exports'] = summarize_annual_tax_exports(process)
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
