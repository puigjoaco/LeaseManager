import hashlib
import json
from decimal import Decimal

from django.utils import timezone
from django.core.exceptions import ValidationError

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
    AnnualTaxSourceBundle,
    CapacidadSII,
    DDJJPreparacionAnual,
    DTEEmitido,
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
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoDTE,
)


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


def build_annual_summary(empresa, fiscal_year, rule_set, source_bundle):
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
    return {
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
        },
        'annual_tax_monthly_facts': {
            'total': monthly_facts.count(),
            'months': monthly_fact_months,
            **monthly_fact_totals,
        },
    }


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
