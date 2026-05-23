from django.utils import timezone
from django.core.exceptions import ValidationError

from contabilidad.services import DEFAULT_REGIME_CODE
from contabilidad.models import EstadoPreparacionTributaria, ObligacionTributariaMensual
from core.reference_validation import is_non_sensitive_reference

from .models import (
    CapacidadSII,
    DDJJPreparacionAnual,
    DTEEmitido,
    EstadoDTE,
    EstadoGateSII,
    F22PreparacionAnual,
    F29PreparacionMensual,
    ProcesoRentaAnual,
    TipoDTE,
)


DTE_EXTERNAL_STATES = {
    EstadoDTE.SENT_MANUAL,
    EstadoDTE.ACCEPTED,
    EstadoDTE.REJECTED,
    EstadoDTE.CANCELED,
}

TAX_STATUS_REQUIRING_REF = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}


def _first_readiness_error(errors):
    if not errors:
        return ''
    field, message = next(iter(errors.items()))
    return f'{field}: {message}'


def _ensure_non_sensitive_reference(value, field_name):
    normalized = str(value or '').strip()
    if normalized and not is_non_sensitive_reference(normalized):
        raise ValueError(f'{field_name} debe ser una referencia no sensible; no use URLs, tokens, credenciales ni correos.')
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


def validate_company_fiscal_readiness(empresa):
    config = getattr(empresa, 'configuracion_fiscal', None)
    if not config or config.estado != 'activa':
        raise ValueError('La empresa no tiene una configuracion fiscal activa para emitir DTE.')
    if config.regimen_tributario.codigo_regimen != DEFAULT_REGIME_CODE:
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
    next_track_id = input_track_id or dte.sii_track_id
    next_sii_status = str(ultimo_estado_sii or '').strip() or dte.ultimo_estado_sii
    if estado_dte in DTE_EXTERNAL_STATES:
        ensure_sii_capability_ready(dte.capacidad_tributaria, dte.capacidad_tributaria.capacidad_key)
        if not next_track_id:
            raise ValueError('Actualizar estado SII controlado requiere sii_track_id trazable.')
        _ensure_non_sensitive_reference(next_track_id, 'sii_track_id')
        if estado_dte in {EstadoDTE.ACCEPTED, EstadoDTE.REJECTED, EstadoDTE.CANCELED} and not next_sii_status:
            raise ValueError('Actualizar aceptacion/rechazo/anulacion requiere ultimo_estado_sii trazable.')

    dte.estado_dte = estado_dte
    if input_track_id:
        dte.sii_track_id = input_track_id
    if ultimo_estado_sii:
        dte.ultimo_estado_sii = ultimo_estado_sii
    if observaciones:
        dte.observaciones = observaciones
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


def register_f29_status(draft, *, estado_preparacion, borrador_ref='', observaciones=''):
    if estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
        raise ValueError('SII.F29Presentacion requiere gate propio y no se registra desde preparacion local.')
    input_ref = _ensure_non_sensitive_reference(borrador_ref, 'borrador_ref')
    next_ref = input_ref or draft.borrador_ref
    if estado_preparacion in TAX_STATUS_REQUIRING_REF:
        ensure_sii_capability_ready(draft.capacidad_tributaria, draft.capacidad_tributaria.capacidad_key)
        if not next_ref:
            raise ValueError('Aprobar u observar F29 requiere borrador_ref trazable.')
        _ensure_non_sensitive_reference(next_ref, 'borrador_ref')

    draft.estado_preparacion = estado_preparacion
    if input_ref:
        draft.borrador_ref = input_ref
    if observaciones:
        draft.observaciones = observaciones
    draft.save(update_fields=['estado_preparacion', 'borrador_ref', 'observaciones', 'updated_at'])
    return draft


def get_active_annual_capability(empresa, capability_key):
    capability = empresa.capacidades_sii.filter(capacidad_key=capability_key).first()
    if not capability:
        raise ValueError(f'La empresa no tiene configurada la capacidad {capability_key}.')
    return ensure_sii_capability_ready(capability, capability_key)


def validate_annual_readiness(empresa, anio_tributario):
    config = validate_company_fiscal_readiness(empresa)
    fiscal_year = anio_tributario - 1
    approved_closes = empresa.cierres_mensuales_contables.filter(anio=fiscal_year, estado='aprobado').count()
    if approved_closes != 12:
        raise ValueError('La preparacion anual requiere doce cierres mensuales aprobados del año comercial.')
    return config, fiscal_year


def build_annual_summary(empresa, fiscal_year):
    obligations = ObligacionTributariaMensual.objects.filter(empresa=empresa, anio=fiscal_year)
    total_obligations = obligations.count()
    total_monto = sum((item.monto_calculado for item in obligations), 0)
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
    }


def generate_annual_preparation(empresa, anio_tributario):
    config, fiscal_year = validate_annual_readiness(empresa, anio_tributario)
    summary = build_annual_summary(empresa, fiscal_year)
    process, _ = ProcesoRentaAnual.objects.get_or_create(
        empresa=empresa,
        anio_tributario=anio_tributario,
    )
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


def register_annual_status(document, *, estado_preparacion, ref_value='', observaciones=''):
    if estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
        raise ValueError('SII.PresentacionAnualFinal esta podada del v1 y requiere reemision formal del set.')
    current_ref = ''
    if hasattr(document, 'paquete_ref'):
        current_ref = document.paquete_ref
    if hasattr(document, 'borrador_ref'):
        current_ref = document.borrador_ref
    input_ref = _ensure_non_sensitive_reference(ref_value, 'ref_value')
    next_ref = input_ref or current_ref
    if estado_preparacion in TAX_STATUS_REQUIRING_REF:
        ensure_sii_capability_ready(document.capacidad_tributaria, document.capacidad_tributaria.capacidad_key)
        if not next_ref:
            raise ValueError('Aprobar u observar preparacion anual requiere referencia trazable.')
        _ensure_non_sensitive_reference(next_ref, 'ref_value')

    document.estado_preparacion = estado_preparacion
    if hasattr(document, 'paquete_ref') and input_ref:
        document.paquete_ref = input_ref
    if hasattr(document, 'borrador_ref') and input_ref:
        document.borrador_ref = input_ref
    if observaciones:
        document.observaciones = observaciones
    fields = ['estado_preparacion', 'updated_at']
    if hasattr(document, 'paquete_ref'):
        fields.append('paquete_ref')
    if hasattr(document, 'borrador_ref'):
        fields.append('borrador_ref')
    if hasattr(document, 'observaciones'):
        fields.append('observaciones')
    document.save(update_fields=fields)

    process = getattr(document, 'proceso_renta_anual', None)
    if process and input_ref:
        if hasattr(document, 'paquete_ref'):
            process.paquete_ddjj_ref = input_ref
        if hasattr(document, 'borrador_ref'):
            process.borrador_f22_ref = input_ref
        process.save(update_fields=['paquete_ddjj_ref', 'borrador_f22_ref', 'updated_at'])
    return document
