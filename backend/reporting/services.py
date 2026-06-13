from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone

from audit.models import AuditEvent, ManualResolution
from audit.scope_filters import scope_manual_resolution_queryset
from canales.models import EstadoMensajeSaliente, MensajeSaliente
from cobranza.models import (
    DistribucionCobroMensual,
    EstadoCuentaArrendatario,
    EstadoIntentoPagoWebPay,
    GarantiaContractual,
    IntentoPagoWebPay,
    PagoMensual,
)
from conciliacion.models import (
    CuadraturaBancaria,
    EstadoConciliacionMovimiento,
    EstadoCuadraturaBancaria,
    IngresoDesconocido,
    MovimientoBancarioImportado,
)
from core.reference_validation import (
    contains_sensitive_reference,
    is_non_sensitive_reference,
    redact_sensitive_payload,
    redact_sensitive_reference,
)
from core.scope_access import ScopeAccess, scope_queryset_for_access
from core.state_transition_audit_readiness import transition_event_has_transition_metadata
from contabilidad.models import (
    AsientoContable,
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoAsientoContable,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    EventoContable,
    LibroDiario,
    LibroMayor,
    ObligacionTributariaMensual,
)
from contabilidad.services import (
    get_company_period_unresolved_bank_movements,
    summarize_company_period_bank_square,
)
from contratos.models import AvisoTermino, Contrato, EstadoAvisoTermino
from operacion.models import CuentaRecaudadora, IdentidadDeEnvio, MandatoOperacion
from patrimonio.models import ComunidadPatrimonial, Empresa, ParticipacionPatrimonial, Propiedad, Socio
from sii.models import DDJJPreparacionAnual, DTEEmitido, F22PreparacionAnual, F29PreparacionMensual, ProcesoRentaAnual

REPORTING_CACHE_TTL_SECONDS = 15
SOCIO_SCOPE_PATHS = (
    'propiedades_directas__id',
    'representaciones_comunidad__comunidad__propiedades__id',
    'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
    'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
)
ANNUAL_TRACEABLE_STATES = {
    EstadoPreparacionTributaria.PREPARED,
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}
ANNUAL_STATES_REQUIRING_REF = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}
ANNUAL_STATUS_AUDIT_TARGETS = (
    ('DDJJPreparacionAnual', 'sii.ddjj_preparacion.status_updated', 'ddjj_preparacion'),
    ('F22PreparacionAnual', 'sii.f22_preparacion.status_updated', 'f22_preparacion'),
)
MONTHLY_CONTROL_READY_TAX_STATES = {
    EstadoPreparacionTributaria.NOT_APPLICABLE,
    EstadoPreparacionTributaria.PREPARED,
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.RECTIFIED,
}
BANK_UNCLASSIFIED_STATES = {
    EstadoConciliacionMovimiento.PENDING,
    EstadoConciliacionMovimiento.UNKNOWN_INCOME,
    EstadoConciliacionMovimiento.MANUAL_REQUIRED,
}
BANK_DIFFERENCE_STATES = {
    EstadoCuadraturaBancaria.OPEN_DIFFERENCE,
    EstadoCuadraturaBancaria.EXPLAINED_DIFFERENCE,
}
CLOSE_BLOCKED_STATES = {
    EstadoCierreMensual.DRAFT,
    EstadoCierreMensual.PREPARED,
    EstadoCierreMensual.REOPENED,
}


class ReportingTraceabilityError(ValueError):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _cache_key(prefix: str) -> str:
    return f'reporting:{prefix}'


def _decimal_str(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal('0.01')))


def _period_label(anio, mes) -> str:
    return f'{int(anio):04d}-{int(mes):02d}'


def _annual_summary_fiscal_year(summary) -> int | None:
    if not isinstance(summary, dict) or not summary.get('fiscal_year'):
        return None
    try:
        return int(summary.get('fiscal_year'))
    except (TypeError, ValueError):
        return None


def _annual_summary_is_traceable(summary) -> bool:
    if not isinstance(summary, dict):
        return False
    obligations = summary.get('obligaciones')
    return _annual_summary_fiscal_year(summary) is not None and isinstance(obligations, list) and bool(obligations)


def _annual_summary_fiscal_year_mismatch(summary, anio_tributario) -> bool:
    fiscal_year = _annual_summary_fiscal_year(summary)
    return fiscal_year is not None and fiscal_year != int(anio_tributario) - 1


def _annual_document_process_mismatch(document, process) -> bool:
    return (
        document.proceso_renta_anual_id != process.id
        or document.empresa_id != process.empresa_id
        or document.anio_tributario != process.anio_tributario
    )


def _has_text(value) -> bool:
    return bool(str(value or '').strip())


def _sensitive_reference(value) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and not is_non_sensitive_reference(normalized)


def _sensitive_payload(value) -> bool:
    return contains_sensitive_reference(value or {}, include_sensitive_keys=True)


def _annual_status_audit_metadata_missing(*, ddjj_items, f22_items) -> list[dict[str, object]]:
    ids_by_document = {
        'DDJJPreparacionAnual': {str(item.id) for item in ddjj_items if item.id is not None},
        'F22PreparacionAnual': {str(item.id) for item in f22_items if item.id is not None},
    }
    missing: list[dict[str, object]] = []

    for document_label, event_type, entity_type in ANNUAL_STATUS_AUDIT_TARGETS:
        entity_ids = ids_by_document[document_label]
        if not entity_ids:
            continue
        events = AuditEvent.objects.filter(
            event_type=event_type,
            entity_type=entity_type,
            entity_id__in=entity_ids,
        ).only('metadata')
        count = sum(1 for event in events if not transition_event_has_transition_metadata(event))
        if count:
            missing.append(
                {
                    'documento': document_label,
                    'event_type': event_type,
                    'eventos_incompletos': count,
                }
            )

    return missing


def _values_set(queryset, field: str) -> set[int]:
    return {value for value in queryset.values_list(field, flat=True).distinct() if value is not None}


def _count_contracts_near_expiry(contracts, reference_date) -> int:
    total = 0
    for contract in (
        contracts.filter(estado='vigente')
        .only('id', 'fecha_fin_vigente', 'dias_prealerta_admin')
        .distinct()
    ):
        days_until_end = (contract.fecha_fin_vigente - reference_date).days
        if 0 <= days_until_end <= int(contract.dias_prealerta_admin or 0):
            total += 1
    return total


def _count_incomplete_guarantees(guarantees) -> int:
    total = 0
    for guarantee in guarantees.only(
        'id',
        'monto_pactado',
        'monto_recibido',
        'monto_devuelto',
        'monto_aplicado',
        'aceptacion_parcial_ref',
    ).distinct():
        if guarantee.garantia_incompleta:
            total += 1
    return total


def _operational_dashboard_blocker_counts(
    *,
    contratos,
    movimientos_bancarios,
    cuadraturas,
    avisos_termino,
    garantias,
    mensajes,
    intentos_webpay,
    cierres,
):
    return {
        'movimientos_sin_clasificar': movimientos_bancarios.filter(
            estado_conciliacion__in=BANK_UNCLASSIFIED_STATES,
        ).count(),
        'diferencias_banco_sistema': cuadraturas.filter(
            Q(estado__in=BANK_DIFFERENCE_STATES) | ~Q(diferencia_clp=Decimal('0.00')),
        ).count(),
        'contratos_por_vencer': _count_contracts_near_expiry(contratos, timezone.localdate()),
        'avisos_termino_registrados': avisos_termino.filter(
            estado=EstadoAvisoTermino.REGISTERED,
        ).count(),
        'garantias_incompletas': _count_incomplete_guarantees(garantias),
        'fallas_integracion': (
            mensajes.filter(estado=EstadoMensajeSaliente.FAILED).count()
            + intentos_webpay.filter(estado=EstadoIntentoPagoWebPay.FAILED).count()
        ),
        'cierres_bloqueados': cierres.filter(estado__in=CLOSE_BLOCKED_STATES).count(),
    }


def _active_fiscal_company_ids(company_ids: set[int]) -> set[int]:
    if not company_ids:
        return set()
    return set(
        ConfiguracionFiscalEmpresa.objects.filter(
            empresa_id__in=company_ids,
            estado=EstadoRegistro.ACTIVE,
        ).values_list('empresa_id', flat=True)
    )


def _traceability_payload(*, report_type: str, sources: list[str], checks: dict | None = None):
    return {
        'estado': 'verificado',
        'tipo_reporte': report_type,
        'fuentes': sources,
        'controles': checks or {},
    }


def _raise_traceability_error(code: str, message: str, details: dict | None = None):
    raise ReportingTraceabilityError(code, message, details)


def _scoped_socios_queryset(access: ScopeAccess):
    return scope_queryset_for_access(
        Socio.objects.all(),
        access,
        property_paths=SOCIO_SCOPE_PATHS,
    )


def _assert_financial_monthly_traceability(
    *,
    anio,
    mes,
    empresa_id,
    access: ScopeAccess,
    events,
    obligations,
    closures,
    dtes,
    f29s,
):
    period_distributions = scope_queryset_for_access(
        DistribucionCobroMensual.objects.filter(pago_mensual__anio=anio, pago_mensual__mes=mes),
        access,
        company_paths=('beneficiario_empresa_owner_id',),
        property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
    )
    if empresa_id is not None:
        period_distributions = period_distributions.filter(beneficiario_empresa_owner_id=empresa_id)

    company_ids = set()
    if empresa_id is not None:
        company_ids.add(empresa_id)
    company_ids.update(_values_set(period_distributions, 'beneficiario_empresa_owner_id'))
    company_ids.update(_values_set(events, 'empresa_id'))
    company_ids.update(_values_set(obligations, 'empresa_id'))
    company_ids.update(_values_set(dtes, 'empresa_id'))
    company_ids.update(_values_set(f29s, 'empresa_id'))

    if company_ids:
        approved_company_ids = _values_set(
            closures.filter(empresa_id__in=company_ids, estado=EstadoCierreMensual.APPROVED),
            'empresa_id',
        )
        missing_closes = sorted(company_ids - approved_company_ids)
        if missing_closes:
            _raise_traceability_error(
                'reporting.monthly_close_missing',
                'El reporte financiero mensual requiere cierre mensual aprobado para cada empresa incluida.',
                {'periodo': _period_label(anio, mes), 'empresas_sin_cierre_aprobado': missing_closes},
            )

    missing_event_origin_count = events.filter(Q(entidad_origen_tipo='') | Q(entidad_origen_id='')).count()
    if missing_event_origin_count:
        _raise_traceability_error(
            'reporting.event_origin_missing',
            'El reporte financiero mensual contiene eventos contables sin origen trazable.',
            {'periodo': _period_label(anio, mes), 'eventos_sin_origen': missing_event_origin_count},
        )

    missing_asiento_count = events.filter(asiento_contable__isnull=True).count()
    if missing_asiento_count:
        _raise_traceability_error(
            'reporting.accounting_entry_missing',
            'El reporte financiero mensual contiene eventos contabilizados sin asiento contable asociado.',
            {'periodo': _period_label(anio, mes), 'eventos_sin_asiento': missing_asiento_count},
        )

    asientos = AsientoContable.objects.filter(evento_contable__in=events).prefetch_related('movimientos')
    asientos_no_posteados = [
        asiento.id
        for asiento in asientos
        if asiento.estado != EstadoAsientoContable.POSTED
    ]
    if asientos_no_posteados:
        _raise_traceability_error(
            'reporting.accounting_entry_not_posted',
            'El reporte financiero mensual contiene asientos no posteados.',
            {'periodo': _period_label(anio, mes), 'asientos_no_posteados': asientos_no_posteados},
        )

    asientos_descuadrados = [
        asiento.id
        for asiento in asientos
        if asiento.debe_total != asiento.haber_total
    ]
    if asientos_descuadrados:
        _raise_traceability_error(
            'reporting.accounting_entry_unbalanced',
            'El reporte financiero mensual contiene asientos descuadrados.',
            {'periodo': _period_label(anio, mes), 'asientos_descuadrados': asientos_descuadrados},
        )

    posted_asientos = [asiento for asiento in asientos if asiento.estado == EstadoAsientoContable.POSTED]
    asientos_sin_hash = [asiento.id for asiento in posted_asientos if not _has_text(asiento.hash_integridad)]
    if asientos_sin_hash:
        _raise_traceability_error(
            'reporting.accounting_entry_hash_missing',
            'El reporte financiero mensual contiene asientos contabilizados sin hash de integridad.',
            {'periodo': _period_label(anio, mes), 'asientos_sin_hash': asientos_sin_hash},
        )

    asientos_hash_desactualizado = [
        asiento.id
        for asiento in posted_asientos
        if _has_text(asiento.hash_integridad) and not asiento.hash_integridad_matches()
    ]
    if asientos_hash_desactualizado:
        _raise_traceability_error(
            'reporting.accounting_entry_hash_mismatch',
            'El reporte financiero mensual contiene asientos con hash de integridad desactualizado.',
            {'periodo': _period_label(anio, mes), 'asientos_hash_desactualizado': asientos_hash_desactualizado},
        )

    asientos_sin_movimientos = [asiento.id for asiento in asientos if not asiento.movimientos.exists()]
    if asientos_sin_movimientos:
        _raise_traceability_error(
            'reporting.accounting_entry_movements_missing',
            'El reporte financiero mensual contiene asientos sin movimientos contables trazables.',
            {'periodo': _period_label(anio, mes), 'asientos_sin_movimientos': asientos_sin_movimientos},
        )

    return _traceability_payload(
        report_type='financiero_mensual',
        sources=[
            'PagoMensual',
            'DistribucionCobroMensual',
            'EventoContable',
            'AsientoContable',
            'ObligacionTributariaMensual',
            'CierreMensualContable',
            'DTEEmitido',
            'F29PreparacionMensual',
        ],
        checks={
            'periodo': _period_label(anio, mes),
            'empresas_con_cierre_aprobado': len(company_ids),
            'eventos_con_asiento': asientos.count(),
        },
    )


def _build_monthly_close_control(*, anio, mes, empresa_id, access, events, obligations, closures, dtes, f29s):
    period_distributions = scope_queryset_for_access(
        DistribucionCobroMensual.objects.filter(pago_mensual__anio=anio, pago_mensual__mes=mes),
        access,
        company_paths=('beneficiario_empresa_owner_id',),
        property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
    )
    if empresa_id is not None:
        period_distributions = period_distributions.filter(beneficiario_empresa_owner_id=empresa_id)

    company_ids = set()
    if empresa_id is not None:
        company_ids.add(empresa_id)
    company_ids.update(_values_set(period_distributions, 'beneficiario_empresa_owner_id'))
    company_ids.update(_values_set(events, 'empresa_id'))
    company_ids.update(_values_set(obligations, 'empresa_id'))
    company_ids.update(_values_set(closures, 'empresa_id'))
    company_ids.update(_values_set(dtes, 'empresa_id'))
    company_ids.update(_values_set(f29s, 'empresa_id'))
    if not company_ids:
        return []

    scoped_companies = scope_queryset_for_access(
        Empresa.objects.filter(id__in=company_ids),
        access,
        company_paths=('id',),
    )
    companies_by_id = {company.id: company for company in scoped_companies}
    active_configs = scope_queryset_for_access(
        ConfiguracionFiscalEmpresa.objects.filter(
            empresa_id__in=companies_by_id,
            estado=EstadoRegistro.ACTIVE,
        ),
        access,
        company_paths=('empresa_id',),
    )
    configs_by_company = {config.empresa_id: config for config in active_configs}
    closures_by_company = {close.empresa_id: close for close in closures.order_by('empresa_id')}
    f29_by_company = {draft.empresa_id: draft for draft in f29s.order_by('empresa_id')}
    obligations_by_company: dict[int, list[ObligacionTributariaMensual]] = {}
    for obligation in obligations.order_by('empresa_id', 'obligacion_tipo'):
        obligations_by_company.setdefault(obligation.empresa_id, []).append(obligation)

    rows = []
    for company_id in sorted(companies_by_id):
        company = companies_by_id[company_id]
        close = closures_by_company.get(company_id)
        config = configs_by_company.get(company_id)
        company_obligations = obligations_by_company.get(company_id, [])
        f29 = f29_by_company.get(company_id)
        bank_square = summarize_company_period_bank_square(company, anio, mes)
        unresolved_bank_movements = get_company_period_unresolved_bank_movements(company, anio, mes).count()

        obligations_required = bool(config and (config.aplica_ppm or config.afecta_iva_arriendo))
        pending_obligations = [
            obligation
            for obligation in company_obligations
            if obligation.estado_preparacion not in MONTHLY_CONTROL_READY_TAX_STATES
        ]
        f29_required = obligations_required
        f29_state = (
            f29.estado_preparacion
            if f29 is not None
            else ('faltante' if f29_required else EstadoPreparacionTributaria.NOT_APPLICABLE)
        )

        blockers = []
        if config is None:
            blockers.append('configuracion_fiscal_faltante')
        if close is None or close.estado != EstadoCierreMensual.APPROVED:
            blockers.append('cierre_contable_no_aprobado')
        if unresolved_bank_movements:
            blockers.append('movimientos_bancarios_sin_resolver')
        if bank_square['cuadraturas_bancarias_faltantes']:
            blockers.append('cuadratura_bancaria_faltante')
        if bank_square['cuadraturas_bancarias_no_cuadradas']:
            blockers.append('banco_no_cuadrado')
        if obligations_required and not company_obligations:
            blockers.append('obligaciones_mensuales_faltantes')
        if pending_obligations:
            blockers.append('obligaciones_mensuales_pendientes')
        if f29_required and f29 is None:
            blockers.append('f29_faltante')
        elif f29_required and f29.estado_preparacion not in MONTHLY_CONTROL_READY_TAX_STATES:
            blockers.append('f29_no_preparado')

        rows.append(
            {
                'empresa_id': company_id,
                'cierre_contable_estado': close.estado if close else 'faltante',
                'cierre_contable_aprobado': bool(close and close.estado == EstadoCierreMensual.APPROVED),
                'banco_cuadrado': (
                    bank_square['cuadraturas_bancarias_faltantes'] == 0
                    and bank_square['cuadraturas_bancarias_no_cuadradas'] == 0
                ),
                'movimientos_bancarios_sin_resolver': unresolved_bank_movements,
                **bank_square,
                'configuracion_fiscal_activa': config is not None,
                'obligaciones_requeridas': obligations_required,
                'obligaciones_total': len(company_obligations),
                'obligaciones_pendientes': len(pending_obligations),
                'f29_requerido': f29_required,
                'f29_estado': f29_state,
                'estado_control': 'listo' if not blockers else 'bloqueado',
                'bloqueadores_periodo': blockers,
            }
        )
    return rows


def _assert_period_books_traceability(*, empresa_id, periodo, libro_diario, libro_mayor, balance):
    snapshots = {
        'libro_diario': libro_diario,
        'libro_mayor': libro_mayor,
        'balance_comprobacion': balance,
    }
    missing = [name for name, snapshot in snapshots.items() if snapshot is None]
    if missing:
        _raise_traceability_error(
            'reporting.books_snapshot_missing',
            'El reporte de libros requiere libro diario, libro mayor y balance de comprobacion existentes.',
            {'empresa_id': empresa_id, 'periodo': periodo, 'faltantes': missing},
        )

    not_approved = [
        name
        for name, snapshot in snapshots.items()
        if snapshot.estado_snapshot != EstadoCierreMensual.APPROVED
    ]
    if not_approved:
        _raise_traceability_error(
            'reporting.books_snapshot_not_approved',
            'El reporte de libros requiere snapshots contables aprobados.',
            {'empresa_id': empresa_id, 'periodo': periodo, 'snapshots_no_aprobados': not_approved},
        )

    empty_summaries = [name for name, snapshot in snapshots.items() if not snapshot.resumen]
    if empty_summaries:
        _raise_traceability_error(
            'reporting.books_snapshot_summary_missing',
            'El reporte de libros requiere resumen contable trazable en cada snapshot.',
            {'empresa_id': empresa_id, 'periodo': periodo, 'snapshots_sin_resumen': empty_summaries},
        )

    if balance.resumen.get('cuadrado') is not True:
        _raise_traceability_error(
            'reporting.books_balance_not_square',
            'El reporte de libros requiere balance de comprobacion cuadrado.',
            {'empresa_id': empresa_id, 'periodo': periodo},
        )

    try:
        anio_raw, mes_raw = periodo.split('-', 1)
        anio = int(anio_raw)
        mes = int(mes_raw)
    except (TypeError, ValueError) as error:
        raise ReportingTraceabilityError(
            'reporting.books_period_invalid',
            'El reporte de libros requiere periodo con formato YYYY-MM.',
            {'empresa_id': empresa_id, 'periodo': periodo},
        ) from error

    approved_close = CierreMensualContable.objects.filter(
        empresa_id=empresa_id,
        anio=anio,
        mes=mes,
        estado=EstadoCierreMensual.APPROVED,
    ).exists()
    if not approved_close:
        _raise_traceability_error(
            'reporting.books_close_missing',
            'El reporte de libros requiere cierre mensual aprobado para el periodo.',
            {'empresa_id': empresa_id, 'periodo': periodo},
        )

    return _traceability_payload(
        report_type='libros_periodo',
        sources=['LibroDiario', 'LibroMayor', 'BalanceComprobacion', 'CierreMensualContable'],
        checks={'empresa_id': empresa_id, 'periodo': periodo, 'snapshots_aprobados': 3},
    )


def _assert_annual_tax_traceability(*, anio_tributario, empresa_id, processes, ddjj_items, f22_items):
    processes = list(processes)
    ddjj_items = list(ddjj_items)
    f22_items = list(f22_items)

    if not processes:
        _raise_traceability_error(
            'reporting.annual_process_missing',
            'El reporte tributario anual requiere al menos un proceso de renta anual preparado.',
            {'empresa_id': empresa_id, 'anio_tributario': anio_tributario},
        )

    ddjj_by_process = {item.proceso_renta_anual_id: item for item in ddjj_items}
    f22_by_process = {item.proceso_renta_anual_id: item for item in f22_items}
    company_ids = {item.empresa_id for item in [*processes, *ddjj_items, *f22_items]}
    missing_fiscal_config = sorted(company_ids - _active_fiscal_company_ids(company_ids))
    if missing_fiscal_config:
        _raise_traceability_error(
            'reporting.annual_fiscal_config_missing',
            'El reporte tributario anual requiere ConfiguracionFiscalEmpresa activa para cada empresa incluida.',
            {
                'anio_tributario': anio_tributario,
                'empresas_sin_configuracion_fiscal': missing_fiscal_config,
            },
        )

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            _raise_traceability_error(
                'reporting.annual_process_not_traceable',
                'El reporte tributario anual contiene procesos sin estado trazable de preparacion.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario, 'estado': process.estado},
            )
        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        if not _annual_summary_is_traceable(summary):
            _raise_traceability_error(
                'reporting.annual_summary_incomplete',
                'El reporte tributario anual requiere resumen anual generado desde obligaciones mensuales trazables.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if _annual_summary_fiscal_year_mismatch(summary, anio_tributario):
            _raise_traceability_error(
                'reporting.annual_fiscal_year_mismatch',
                'El reporte tributario anual requiere resumen del ano comercial inmediatamente anterior.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'fiscal_year': _annual_summary_fiscal_year(summary),
                    'expected_fiscal_year': int(anio_tributario) - 1,
                },
            )
        if process.estado in ANNUAL_STATES_REQUIRING_REF and _sensitive_payload(process.resumen_anual):
            _raise_traceability_error(
                'reporting.annual_process_sensitive_payload',
                'El reporte tributario anual no puede validar resumen_anual sensible de proceso final.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if process.estado in ANNUAL_STATES_REQUIRING_REF and not _has_text(process.paquete_ddjj_ref):
            _raise_traceability_error(
                'reporting.annual_process_ddjj_ref_missing',
                'El reporte tributario anual requiere paquete_ddjj_ref para procesos aprobados, observados, rectificados o presentados.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if process.estado in ANNUAL_STATES_REQUIRING_REF and not _has_text(process.borrador_f22_ref):
            _raise_traceability_error(
                'reporting.annual_process_f22_ref_missing',
                'El reporte tributario anual requiere borrador_f22_ref para procesos aprobados, observados, rectificados o presentados.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if _sensitive_reference(process.paquete_ddjj_ref):
            _raise_traceability_error(
                'reporting.annual_process_ddjj_ref_sensitive',
                'El reporte tributario anual no puede exponer ni validar paquete_ddjj_ref sensible del proceso anual.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if _sensitive_reference(process.borrador_f22_ref):
            _raise_traceability_error(
                'reporting.annual_process_f22_ref_sensitive',
                'El reporte tributario anual no puede exponer ni validar borrador_f22_ref sensible del proceso anual.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )

        ddjj = ddjj_by_process.get(process.id)
        f22 = f22_by_process.get(process.id)
        if ddjj is None:
            _raise_traceability_error(
                'reporting.annual_ddjj_missing_for_process',
                'El reporte tributario anual requiere DDJJ asociada al proceso anual.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'proceso_renta_anual_id': process.id,
                },
            )
        if f22 is None:
            _raise_traceability_error(
                'reporting.annual_f22_missing_for_process',
                'El reporte tributario anual requiere F22 asociado al proceso anual.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'proceso_renta_anual_id': process.id,
                },
            )
        mismatched_documents = []
        if _annual_document_process_mismatch(ddjj, process):
            mismatched_documents.append('DDJJPreparacionAnual')
        if _annual_document_process_mismatch(f22, process):
            mismatched_documents.append('F22PreparacionAnual')
        if mismatched_documents:
            _raise_traceability_error(
                'reporting.annual_document_process_mismatch',
                'El reporte tributario anual requiere DDJJ y F22 asociados al mismo proceso anual, empresa y ano tributario.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'documentos_desalineados': mismatched_documents,
                },
            )
        if ddjj.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            _raise_traceability_error(
                'reporting.annual_ddjj_not_traceable',
                'El reporte tributario anual requiere DDJJ en estado trazable de preparacion.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'ddjj_id': ddjj.id,
                    'estado': ddjj.estado_preparacion,
                },
            )
        if f22.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            _raise_traceability_error(
                'reporting.annual_f22_not_traceable',
                'El reporte tributario anual requiere F22 en estado trazable de preparacion.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'f22_id': f22.id,
                    'estado': f22.estado_preparacion,
                },
            )
        if not ddjj.resumen_paquete:
            _raise_traceability_error(
                'reporting.annual_ddjj_summary_missing',
                'El reporte tributario anual requiere resumen trazable de DDJJ.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'ddjj_id': ddjj.id,
                },
            )
        if not f22.resumen_f22:
            _raise_traceability_error(
                'reporting.annual_f22_summary_missing',
                'El reporte tributario anual requiere resumen trazable de F22.',
                {
                    'empresa_id': process.empresa_id,
                    'anio_tributario': anio_tributario,
                    'f22_id': f22.id,
                },
            )
        ddjj_summary = ddjj.resumen_paquete.get('resumen_anual') if isinstance(ddjj.resumen_paquete, dict) else None
        f22_summary = f22.resumen_f22.get('resumen_anual') if isinstance(f22.resumen_f22, dict) else None
        if _annual_summary_fiscal_year_mismatch(ddjj_summary, anio_tributario):
            _raise_traceability_error(
                'reporting.annual_ddjj_fiscal_year_mismatch',
                'El reporte tributario anual requiere DDJJ alineada al ano comercial reportado.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if _annual_summary_fiscal_year_mismatch(f22_summary, anio_tributario):
            _raise_traceability_error(
                'reporting.annual_f22_fiscal_year_mismatch',
                'El reporte tributario anual requiere F22 alineado al ano comercial reportado.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if ddjj.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and _sensitive_payload(ddjj.resumen_paquete):
            _raise_traceability_error(
                'reporting.annual_ddjj_sensitive_payload',
                'El reporte tributario anual no puede validar resumen_paquete sensible de DDJJ final.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if f22.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and _sensitive_payload(f22.resumen_f22):
            _raise_traceability_error(
                'reporting.annual_f22_sensitive_payload',
                'El reporte tributario anual no puede validar resumen_f22 sensible de F22 final.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if ddjj.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not _has_text(ddjj.paquete_ref):
            _raise_traceability_error(
                'reporting.annual_ddjj_ref_missing',
                'El reporte tributario anual requiere paquete_ref para DDJJ aprobada, observada, rectificada o presentada.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if ddjj.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and _sensitive_reference(ddjj.paquete_ref):
            _raise_traceability_error(
                'reporting.annual_ddjj_ref_sensitive',
                'El reporte tributario anual no puede validar paquete_ref sensible de DDJJ final.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if f22.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and not _has_text(f22.borrador_ref):
            _raise_traceability_error(
                'reporting.annual_f22_ref_missing',
                'El reporte tributario anual requiere borrador_ref para F22 aprobado, observado, rectificado o presentado.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )
        if f22.estado_preparacion in ANNUAL_STATES_REQUIRING_REF and _sensitive_reference(f22.borrador_ref):
            _raise_traceability_error(
                'reporting.annual_f22_ref_sensitive',
                'El reporte tributario anual no puede validar borrador_ref sensible de F22 final.',
                {'empresa_id': process.empresa_id, 'anio_tributario': anio_tributario},
            )

    annual_status_audit_missing = _annual_status_audit_metadata_missing(ddjj_items=ddjj_items, f22_items=f22_items)
    if annual_status_audit_missing:
        _raise_traceability_error(
            'reporting.annual_status_transition_metadata_missing',
            'El reporte tributario anual requiere auditorias status_updated DDJJ/F22 con metadata minima de transicion.',
            {
                'empresa_id': empresa_id,
                'anio_tributario': anio_tributario,
                'eventos_status_updated_incompletos': annual_status_audit_missing,
            },
        )

    return _traceability_payload(
        report_type='tributario_anual',
        sources=['ProcesoRentaAnual', 'DDJJPreparacionAnual', 'F22PreparacionAnual', 'ObligacionTributariaMensual'],
        checks={'anio_tributario': anio_tributario, 'procesos_trazados': len(processes)},
    )


def build_operational_dashboard(
    access: ScopeAccess | None = None,
    *,
    include_secondary: bool = True,
    use_cache: bool = True,
):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    if use_cache and not access.restricted:
        cache_key = _cache_key(f'operational-dashboard:{"full" if include_secondary else "summary"}')
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    payload = None
    if not access.restricted:
        payload = {
            'propiedades_activas': Propiedad.objects.filter(estado='activa').count(),
            'contratos_vigentes': Contrato.objects.filter(estado='vigente').count(),
            'pagos_pendientes': PagoMensual.objects.filter(estado_pago='pendiente').count(),
            'pagos_atrasados': PagoMensual.objects.filter(estado_pago='atrasado').count(),
            'resoluciones_manuales_abiertas': ManualResolution.objects.filter(status='open').count(),
            'dtes_borrador': DTEEmitido.objects.filter(estado_dte='borrador').count(),
        }
        payload.update(
            _operational_dashboard_blocker_counts(
                contratos=Contrato.objects.all(),
                movimientos_bancarios=MovimientoBancarioImportado.objects.all(),
                cuadraturas=CuadraturaBancaria.objects.all(),
                avisos_termino=AvisoTermino.objects.all(),
                garantias=GarantiaContractual.objects.all(),
                mensajes=MensajeSaliente.objects.all(),
                intentos_webpay=IntentoPagoWebPay.objects.all(),
                cierres=CierreMensualContable.objects.all(),
            )
        )
        if include_secondary:
            payload.update(
                {
                    'contratos_futuros': Contrato.objects.filter(estado='futuro').count(),
                    'mensajes_preparados': MensajeSaliente.objects.filter(estado='preparado').count(),
                }
            )
            payload.update(build_operational_overview_counts(access=access))
            payload.update(
                {
                    'ingresos_desconocidos_abiertos': IngresoDesconocido.objects.filter(estado='pendiente_revision').count(),
                    'cierres_preparados': CierreMensualContable.objects.filter(estado='preparado').count(),
                    'cierres_aprobados': CierreMensualContable.objects.filter(estado='aprobado').count(),
                    'mensajes_bloqueados': MensajeSaliente.objects.filter(estado='bloqueado').count(),
                }
            )
    else:
        propiedades = scope_queryset_for_access(Propiedad.objects.all(), access, property_paths=('id',))
        contratos = scope_queryset_for_access(
            Contrato.objects.all(),
            access,
            property_paths=('mandato_operacion__propiedad_id',),
        )
        pagos = scope_queryset_for_access(
            PagoMensual.objects.all(),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        dtes_borrador = scope_queryset_for_access(
            DTEEmitido.objects.filter(estado_dte='borrador'),
            access,
            company_paths=('empresa_id',),
        )
        mensajes = scope_queryset_for_access(
            MensajeSaliente.objects.all(),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id', 'arrendatario__contratos__mandato_operacion__propiedad_id'),
        )
        resoluciones_abiertas = scope_manual_resolution_queryset(
            ManualResolution.objects.filter(status='open'),
            access,
        )
        movimientos_bancarios = scope_queryset_for_access(
            MovimientoBancarioImportado.objects.all(),
            access,
            bank_account_paths=('conexion_bancaria__cuenta_recaudadora_id',),
        )
        cuadraturas = scope_queryset_for_access(
            CuadraturaBancaria.objects.all(),
            access,
            bank_account_paths=('cuenta_recaudadora_id',),
        )
        avisos_termino = scope_queryset_for_access(
            AvisoTermino.objects.all(),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        garantias = scope_queryset_for_access(
            GarantiaContractual.objects.all(),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        intentos_webpay = scope_queryset_for_access(
            IntentoPagoWebPay.objects.all(),
            access,
            property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
        )
        cierres = scope_queryset_for_access(
            CierreMensualContable.objects.all(),
            access,
            company_paths=('empresa_id',),
        )

        propiedades_counts = propiedades.aggregate(
            activas=Count('id', filter=Q(estado='activa'), distinct=True),
        )
        contratos_counts = contratos.aggregate(
            vigentes=Count('id', filter=Q(estado='vigente'), distinct=True),
            futuros=Count('id', filter=Q(estado='futuro'), distinct=True),
        )
        pagos_counts = pagos.aggregate(
            pendientes=Count('id', filter=Q(estado_pago='pendiente'), distinct=True),
            atrasados=Count('id', filter=Q(estado_pago='atrasado'), distinct=True),
        )
        mensajes_counts = mensajes.aggregate(
            preparados=Count('id', filter=Q(estado='preparado'), distinct=True),
        )
        payload = {
            'propiedades_activas': propiedades_counts['activas'],
            'contratos_vigentes': contratos_counts['vigentes'],
            'pagos_pendientes': pagos_counts['pendientes'],
            'pagos_atrasados': pagos_counts['atrasados'],
            'resoluciones_manuales_abiertas': resoluciones_abiertas.count(),
            'dtes_borrador': dtes_borrador.count(),
        }
        payload.update(
            _operational_dashboard_blocker_counts(
                contratos=contratos,
                movimientos_bancarios=movimientos_bancarios,
                cuadraturas=cuadraturas,
                avisos_termino=avisos_termino,
                garantias=garantias,
                mensajes=mensajes,
                intentos_webpay=intentos_webpay,
                cierres=cierres,
            )
        )
        if include_secondary:
            payload.update(
                {
                    'contratos_futuros': contratos_counts['futuros'],
                    'mensajes_preparados': mensajes_counts['preparados'],
                }
            )
            payload.update(build_operational_overview_counts(access=access))
            ingresos_desconocidos = scope_queryset_for_access(
                IngresoDesconocido.objects.filter(estado='pendiente_revision'),
                access,
                bank_account_paths=('cuenta_recaudadora_id',),
            )
            cierres_counts = cierres.aggregate(
                preparados=Count('id', filter=Q(estado='preparado'), distinct=True),
                aprobados=Count('id', filter=Q(estado='aprobado'), distinct=True),
            )
            mensajes_bloqueados = scope_queryset_for_access(
                MensajeSaliente.objects.filter(estado='bloqueado'),
                access,
                property_paths=('contrato__mandato_operacion__propiedad_id', 'arrendatario__contratos__mandato_operacion__propiedad_id'),
            )
            payload.update(
                {
                    'ingresos_desconocidos_abiertos': ingresos_desconocidos.count(),
                    'cierres_preparados': cierres_counts['preparados'],
                    'cierres_aprobados': cierres_counts['aprobados'],
                    'mensajes_bloqueados': mensajes_bloqueados.count(),
                }
            )

    if use_cache and not access.restricted:
        cache.set(
            _cache_key(f'operational-dashboard:{"full" if include_secondary else "summary"}'),
            payload,
            REPORTING_CACHE_TTL_SECONDS,
        )
    return payload


def build_operational_overview_counts(access: ScopeAccess | None = None, *, use_cache: bool = True):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    if not access.restricted and use_cache:
        cache_key = _cache_key('operational-overview-counts')
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    if not access.restricted:
        payload = {
            'socios_total': Socio.objects.count(),
            'empresas_total': Empresa.objects.count(),
            'comunidades_total': ComunidadPatrimonial.objects.count(),
            'propiedades_total': Propiedad.objects.count(),
            'cuentas_total': CuentaRecaudadora.objects.count(),
            'identidades_total': IdentidadDeEnvio.objects.count(),
            'mandatos_total': MandatoOperacion.objects.count(),
        }
        if use_cache:
            cache.set(_cache_key('operational-overview-counts'), payload, REPORTING_CACHE_TTL_SECONDS)
        return payload

    socios = _scoped_socios_queryset(access)
    empresas = scope_queryset_for_access(
        Empresa.objects.all(),
        access,
        company_paths=('id',),
    )
    comunidades = scope_queryset_for_access(
        ComunidadPatrimonial.objects.all(),
        access,
        property_paths=('propiedades__id',),
    )
    propiedades = scope_queryset_for_access(Propiedad.objects.all(), access, property_paths=('id',))
    cuentas = scope_queryset_for_access(
        CuentaRecaudadora.objects.all(),
        access,
        bank_account_paths=('id',),
    )
    identidades = scope_queryset_for_access(
        IdentidadDeEnvio.objects.all(),
        access,
        company_paths=('empresa_owner_id',),
        property_paths=('asignaciones_operacion__mandato_operacion__propiedad_id',),
    )
    mandatos = scope_queryset_for_access(
        MandatoOperacion.objects.all(),
        access,
        property_paths=('propiedad_id',),
        bank_account_paths=('cuenta_recaudadora_id',),
    )
    return {
        'socios_total': socios.count(),
        'empresas_total': empresas.count(),
        'comunidades_total': comunidades.count(),
        'propiedades_total': propiedades.count(),
        'cuentas_total': cuentas.count(),
        'identidades_total': identidades.count(),
        'mandatos_total': mandatos.count(),
    }


def build_financial_monthly_summary(anio, mes, empresa_id=None, access: ScopeAccess | None = None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    if empresa_id is None:
        payments = scope_queryset_for_access(
            PagoMensual.objects.filter(anio=anio, mes=mes),
            access,
            property_paths=('contrato__mandato_operacion__propiedad_id',),
        )
        pagos_generados = payments.count()
        facturable_total = payments.aggregate(total=Sum('monto_facturable_clp'))['total'] or Decimal('0.00')
        cobrado_total = payments.aggregate(total=Sum('monto_pagado_clp'))['total'] or Decimal('0.00')
    else:
        distributions = scope_queryset_for_access(
            DistribucionCobroMensual.objects.filter(
                pago_mensual__anio=anio,
                pago_mensual__mes=mes,
                beneficiario_empresa_owner_id=empresa_id,
            ),
            access,
            company_paths=('beneficiario_empresa_owner_id',),
            property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
        )
        pagos_generados = distributions.values('pago_mensual_id').distinct().count()
        facturable_total = distributions.aggregate(total=Sum('monto_facturable_clp'))['total'] or Decimal('0.00')
        cobrado_total = distributions.aggregate(total=Sum('monto_conciliado_clp'))['total'] or Decimal('0.00')

    event_filters = Q(fecha_operativa__year=anio, fecha_operativa__month=mes, estado_contable='contabilizado')
    if empresa_id is not None:
        event_filters &= Q(empresa_id=empresa_id)
    events = scope_queryset_for_access(
        EventoContable.objects.filter(event_filters),
        access,
        company_paths=('empresa_id',),
    )
    event_total = events.aggregate(total=Sum('monto_base'))['total'] or Decimal('0.00')

    obligations = scope_queryset_for_access(
        ObligacionTributariaMensual.objects.filter(anio=anio, mes=mes),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        obligations = obligations.filter(empresa_id=empresa_id)

    closures = scope_queryset_for_access(
        CierreMensualContable.objects.filter(anio=anio, mes=mes),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        closures = closures.filter(empresa_id=empresa_id)

    dtes = scope_queryset_for_access(
        DTEEmitido.objects.filter(fecha_emision__year=anio, fecha_emision__month=mes),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        dtes = dtes.filter(empresa_id=empresa_id)

    f29s = scope_queryset_for_access(
        F29PreparacionMensual.objects.filter(anio=anio, mes=mes),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        f29s = f29s.filter(empresa_id=empresa_id)

    trazabilidad = _assert_financial_monthly_traceability(
        anio=anio,
        mes=mes,
        empresa_id=empresa_id,
        access=access,
        events=events,
        obligations=obligations,
        closures=closures,
        dtes=dtes,
        f29s=f29s,
    )
    control_cierre_mensual = _build_monthly_close_control(
        anio=anio,
        mes=mes,
        empresa_id=empresa_id,
        access=access,
        events=events,
        obligations=obligations,
        closures=closures,
        dtes=dtes,
        f29s=f29s,
    )

    return {
        'anio': anio,
        'mes': mes,
        'empresa_id': empresa_id,
        'trazabilidad': trazabilidad,
        'pagos_generados': pagos_generados,
        'monto_facturable_total_clp': _decimal_str(facturable_total),
        'monto_cobrado_total_clp': _decimal_str(cobrado_total),
        'eventos_contables_posteados': events.count(),
        'monto_eventos_total_clp': _decimal_str(event_total),
        'asientos_contables': AsientoContable.objects.filter(evento_contable__in=events).count(),
        'dtes_emitidos': dtes.count(),
        'control_cierre_mensual': control_cierre_mensual,
        'obligaciones': [
            {
                'tipo': obligation.obligacion_tipo,
                'monto_calculado': _decimal_str(obligation.monto_calculado),
                'estado_preparacion': obligation.estado_preparacion,
            }
            for obligation in obligations.order_by('obligacion_tipo')
        ],
        'cierres': [
            {
                'empresa_id': close.empresa_id,
                'estado': close.estado,
                'fecha_preparacion': close.fecha_preparacion.isoformat() if close.fecha_preparacion else None,
                'fecha_aprobacion': close.fecha_aprobacion.isoformat() if close.fecha_aprobacion else None,
            }
            for close in closures.order_by('empresa_id')
        ],
    }


def build_partner_summary(socio_id, access: ScopeAccess | None = None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    socio = scope_queryset_for_access(
        Socio.objects.filter(pk=socio_id),
        access,
        property_paths=(
            'propiedades_directas__id',
            'representaciones_comunidad__comunidad__propiedades__id',
            'participaciones_patrimoniales_como_participante__empresa_owner__propiedades__id',
            'participaciones_patrimoniales_como_participante__comunidad_owner__propiedades__id',
        ),
    ).get()
    participaciones = ParticipacionPatrimonial.objects.filter(participante_socio=socio, activo=True).select_related(
        'participante_socio',
        'participante_empresa',
        'empresa_owner',
        'comunidad_owner',
    )
    participaciones = scope_queryset_for_access(
        participaciones,
        access,
        property_paths=('empresa_owner__propiedades__id', 'comunidad_owner__propiedades__id'),
    )
    direct_properties = scope_queryset_for_access(
        Propiedad.objects.filter(socio_owner=socio).order_by('codigo_propiedad'),
        access,
        property_paths=('id',),
    )

    company_shares = [
        {
            'empresa_id': item.empresa_owner_id,
            'empresa': item.empresa_owner.razon_social,
            'porcentaje': str(item.porcentaje),
        }
        for item in participaciones
        if item.empresa_owner_id
    ]
    community_shares = [
        {
            'comunidad_id': item.comunidad_owner_id,
            'comunidad': item.comunidad_owner.nombre,
            'porcentaje': str(item.porcentaje),
        }
        for item in participaciones
        if item.comunidad_owner_id
    ]

    active_direct_contracts = scope_queryset_for_access(
        Contrato.objects.filter(
            estado__in=['vigente', 'futuro'],
            contrato_propiedades__propiedad__in=direct_properties,
        ).distinct(),
        access,
        property_paths=('mandato_operacion__propiedad_id',),
    )

    state = scope_queryset_for_access(
        EstadoCuentaArrendatario.objects.filter(
            arrendatario__contratos__mandato_operacion__propiedad__socio_owner=socio
        ).distinct(),
        access,
        property_paths=('arrendatario__contratos__mandato_operacion__propiedad_id',),
    )

    return {
        'socio': {
            'id': socio.id,
            'nombre': socio.nombre,
            'rut': socio.rut,
            'email': socio.email,
        },
        'participaciones_empresas': company_shares,
        'participaciones_comunidades': community_shares,
        'propiedades_directas': [
            {
                'propiedad_id': property_item.id,
                'codigo_propiedad': property_item.codigo_propiedad,
                'direccion': property_item.direccion,
                'estado': property_item.estado,
            }
            for property_item in direct_properties
        ],
        'contratos_directos_activos': active_direct_contracts.count(),
        'estados_cuenta_relacionados': state.count(),
    }


def build_reporting_reference_options(access: ScopeAccess | None = None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    empresas = scope_queryset_for_access(
        Empresa.objects.all().order_by('razon_social', 'id'),
        access,
        company_paths=('id',),
    )
    socios = _scoped_socios_queryset(access).order_by('nombre', 'id')
    expose_socio_contact_fields = not access.restricted

    return {
        'empresas': [
            {
                'id': empresa.id,
                'razon_social': empresa.razon_social,
                'rut': empresa.rut,
                'estado': empresa.estado,
                'participaciones_detail': [],
            }
            for empresa in empresas
        ],
        'socios': [
            {
                'id': socio.id,
                'nombre': socio.nombre,
                'rut': socio.rut if expose_socio_contact_fields else '',
                'email': (socio.email or '') if expose_socio_contact_fields else '',
                'telefono': (socio.telefono or '') if expose_socio_contact_fields else '',
                'domicilio': (socio.domicilio or '') if expose_socio_contact_fields else '',
                'activo': socio.activo,
            }
            for socio in socios
        ],
    }


def build_period_books_summary(empresa_id, periodo, access: ScopeAccess | None = None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    libro_diario = scope_queryset_for_access(
        LibroDiario.objects.filter(empresa_id=empresa_id, periodo=periodo),
        access,
        company_paths=('empresa_id',),
    ).first()
    libro_mayor = scope_queryset_for_access(
        LibroMayor.objects.filter(empresa_id=empresa_id, periodo=periodo),
        access,
        company_paths=('empresa_id',),
    ).first()
    balance = scope_queryset_for_access(
        BalanceComprobacion.objects.filter(empresa_id=empresa_id, periodo=periodo),
        access,
        company_paths=('empresa_id',),
    ).first()
    trazabilidad = _assert_period_books_traceability(
        empresa_id=empresa_id,
        periodo=periodo,
        libro_diario=libro_diario,
        libro_mayor=libro_mayor,
        balance=balance,
    )

    return {
        'empresa_id': empresa_id,
        'periodo': periodo,
        'trazabilidad': trazabilidad,
        'libro_diario': {
            'id': libro_diario.id if libro_diario else None,
            'estado_snapshot': libro_diario.estado_snapshot if libro_diario else None,
            'storage_ref': redact_sensitive_reference(libro_diario.storage_ref) if libro_diario else '',
            'resumen': redact_sensitive_payload(libro_diario.resumen) if libro_diario else {},
        },
        'libro_mayor': {
            'id': libro_mayor.id if libro_mayor else None,
            'estado_snapshot': libro_mayor.estado_snapshot if libro_mayor else None,
            'storage_ref': redact_sensitive_reference(libro_mayor.storage_ref) if libro_mayor else '',
            'resumen': redact_sensitive_payload(libro_mayor.resumen) if libro_mayor else {},
        },
        'balance_comprobacion': {
            'id': balance.id if balance else None,
            'estado_snapshot': balance.estado_snapshot if balance else None,
            'storage_ref': redact_sensitive_reference(balance.storage_ref) if balance else '',
            'resumen': redact_sensitive_payload(balance.resumen) if balance else {},
        },
    }


def build_annual_tax_summary(anio_tributario, empresa_id=None, access: ScopeAccess | None = None):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    process_queryset = scope_queryset_for_access(
        ProcesoRentaAnual.objects.filter(anio_tributario=anio_tributario),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        process_queryset = process_queryset.filter(empresa_id=empresa_id)

    ddjj_queryset = scope_queryset_for_access(
        DDJJPreparacionAnual.objects.filter(anio_tributario=anio_tributario),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        ddjj_queryset = ddjj_queryset.filter(empresa_id=empresa_id)

    f22_queryset = scope_queryset_for_access(
        F22PreparacionAnual.objects.filter(anio_tributario=anio_tributario),
        access,
        company_paths=('empresa_id',),
    )
    if empresa_id is not None:
        f22_queryset = f22_queryset.filter(empresa_id=empresa_id)

    process_items = list(process_queryset.order_by('empresa_id'))
    ddjj_items = list(ddjj_queryset.order_by('empresa_id'))
    f22_items = list(f22_queryset.order_by('empresa_id'))
    trazabilidad = _assert_annual_tax_traceability(
        anio_tributario=anio_tributario,
        empresa_id=empresa_id,
        processes=process_items,
        ddjj_items=ddjj_items,
        f22_items=f22_items,
    )

    return {
        'anio_tributario': anio_tributario,
        'empresa_id': empresa_id,
        'trazabilidad': trazabilidad,
        'procesos_renta': [
            {
                'empresa_id': process.empresa_id,
                'estado': process.estado,
                'fecha_preparacion': process.fecha_preparacion.isoformat() if process.fecha_preparacion else None,
                'resumen_anual': redact_sensitive_payload(process.resumen_anual),
            }
            for process in process_items
        ],
        'ddjj_preparadas': [
            {
                'empresa_id': item.empresa_id,
                'estado_preparacion': item.estado_preparacion,
                'paquete_ref': redact_sensitive_reference(item.paquete_ref),
                'resumen_paquete': redact_sensitive_payload(item.resumen_paquete),
            }
            for item in ddjj_items
        ],
        'f22_preparados': [
            {
                'empresa_id': item.empresa_id,
                'estado_preparacion': item.estado_preparacion,
                'borrador_ref': redact_sensitive_reference(item.borrador_ref),
                'resumen_f22': redact_sensitive_payload(item.resumen_f22),
            }
            for item in f22_items
        ],
    }


def build_migration_manual_resolution_summary(
    status='open',
    access: ScopeAccess | None = None,
    *,
    use_cache: bool = True,
):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    if access.restricted:
        return {
            'status': status,
            'total': 0,
            'categorias': [],
            'scope_types': [],
            'propiedades_owner_manual_required': [],
        }
    cache_key = _cache_key(f'migration-manual-resolution-summary:{status}')
    if use_cache:
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    resolutions = ManualResolution.objects.filter(category__startswith='migration.')
    if status:
        resolutions = resolutions.filter(status=status)

    by_category = resolutions.values('category').annotate(total=Count('id')).order_by('category')
    by_scope_type = resolutions.values('scope_type').annotate(total=Count('id')).order_by('scope_type')

    owner_manual_required = resolutions.filter(category='migration.propiedad.owner_manual_required').order_by('created_at')

    payload = {
        'status': status,
        'total': resolutions.count(),
        'categorias': [
            {'category': item['category'], 'total': item['total']}
            for item in by_category
        ],
        'scope_types': [
            {'scope_type': item['scope_type'], 'total': item['total']}
            for item in by_scope_type
        ],
        'propiedades_owner_manual_required': [
            {
                'id': str(item.id),
                'scope_reference': item.scope_reference,
                'summary': item.summary,
                'codigo': item.metadata.get('codigo'),
                'direccion': item.metadata.get('direccion'),
                'candidate_owner_model': item.metadata.get('candidate_owner_model'),
                'participaciones_count': item.metadata.get('participaciones_count'),
                'total_pct': item.metadata.get('total_pct'),
                'blocked_contract_legacy_ids': item.metadata.get('blocked_contract_legacy_ids', []),
                'socios': item.metadata.get('socios', []),
            }
            for item in owner_manual_required
        ],
    }
    if use_cache:
        cache.set(cache_key, payload, REPORTING_CACHE_TTL_SECONDS)
    return payload


def build_manual_resolution_summary(
    status='open',
    access: ScopeAccess | None = None,
    *,
    use_cache: bool = True,
):
    access = access or ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())
    if not access.restricted and use_cache:
        cache_key = _cache_key(f'manual-resolution-summary:{status}')
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return cached_payload

    resolutions = scope_manual_resolution_queryset(ManualResolution.objects.all(), access)
    if status:
        resolutions = resolutions.filter(status=status)

    by_category = resolutions.values('category').annotate(total=Count('id')).order_by('category')
    payload = {
        'status': status,
        'total': resolutions.count(),
        'categorias': [
            {'category': item['category'], 'total': item['total']}
            for item in by_category
        ],
    }

    if not access.restricted and use_cache:
        cache.set(cache_key, payload, REPORTING_CACHE_TTL_SECONDS)
    return payload


def get_cached_migration_manual_resolution_summary(status='open'):
    return cache.get(_cache_key(f'migration-manual-resolution-summary:{status}'))


def get_cached_manual_resolution_summary(status='open'):
    return cache.get(_cache_key(f'manual-resolution-summary:{status}'))
