from __future__ import annotations

from collections import Counter
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from contabilidad.models import (
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
    ObligacionTributariaMensual,
)
from core.reference_validation import contains_sensitive_reference
from core.state_transition_audit_readiness import count_audit_events_without_transition_metadata
from documentos.models import DocumentoEmitido, EstadoDocumento, TipoDocumental
from sii.models import (
    AmbienteSII,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    EstadoGateSII,
    F22PreparacionAnual,
    ProcesoRentaAnual,
    has_text,
)


SENSITIVE_REFERENCE_PATTERN = re.compile(
    r'(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)',
    re.IGNORECASE,
)

AUTHORIZED_STAGE6_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
STAGE6_ANNUAL_STATUS_UPDATE_EVENT_TYPES = (
    'sii.ddjj_preparacion.status_updated',
    'sii.f22_preparacion.status_updated',
)

ANNUAL_TRACEABLE_STATES = {
    EstadoPreparacionTributaria.PREPARED,
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}

ANNUAL_REF_REQUIRED_STATES = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}


def _non_sensitive_reference(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and not SENSITIVE_REFERENCE_PATTERN.search(normalized)


def _sensitive_reference(value: str) -> bool:
    normalized = str(value or '').strip()
    return bool(normalized) and not _non_sensitive_reference(normalized)


def _issue(code: str, message: str, *, count: int = 1, severity: str = 'blocking') -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _count_invalid(queryset) -> int:
    invalid_count = 0
    for item in queryset:
        try:
            item.full_clean()
        except ValidationError:
            invalid_count += 1
    return invalid_count


def _count_by(queryset, field_name: str) -> dict[str, int]:
    counter = Counter()
    for row in queryset.values(field_name):
        counter[row[field_name] or 'sin_valor'] += 1
    return dict(sorted(counter.items()))


def _count_without_active_fiscal_config(items, active_fiscal_company_ids: set[int]) -> int:
    return sum(1 for item in items if item.empresa_id not in active_fiscal_company_ids)


def _annual_summary_is_traceable(summary: Any) -> bool:
    if not isinstance(summary, dict):
        return False
    obligations = summary.get('obligaciones')
    return _annual_summary_fiscal_year(summary) is not None and isinstance(obligations, list) and bool(obligations)


def _annual_summary_fiscal_year(summary: Any) -> int | None:
    if not isinstance(summary, dict) or not summary.get('fiscal_year'):
        return None
    try:
        return int(summary.get('fiscal_year'))
    except (TypeError, ValueError):
        return None


def _annual_summary_fiscal_year_mismatch(summary: Any, anio_tributario: int) -> bool:
    fiscal_year = _annual_summary_fiscal_year(summary)
    return fiscal_year is not None and fiscal_year != anio_tributario - 1


def _approved_close_months(*, empresa_id: int, fiscal_year: int) -> set[int]:
    return set(
        CierreMensualContable.objects.filter(
            empresa_id=empresa_id,
            anio=fiscal_year,
            estado=EstadoCierreMensual.APPROVED,
        ).values_list('mes', flat=True)
    )


def _collect_process_issues(processes) -> dict[str, int]:
    counts = Counter()
    expected_months = set(range(1, 13))
    for process in processes:
        try:
            process.full_clean()
        except ValidationError:
            counts['process_invalid_model'] += 1

        if process.estado == EstadoPreparacionTributaria.PRESENTED:
            counts['process_presented_boundary'] += 1
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            counts['process_not_traceable'] += 1
        if not _annual_summary_is_traceable(process.resumen_anual):
            counts['process_summary_missing'] += 1
        if _annual_summary_fiscal_year_mismatch(process.resumen_anual, process.anio_tributario):
            counts['process_fiscal_year_mismatch'] += 1
        if contains_sensitive_reference(process.resumen_anual or {}, include_sensitive_keys=True):
            counts['process_sensitive_payload'] += 1
        if _sensitive_reference(process.paquete_ddjj_ref):
            counts['process_ddjj_ref_sensitive'] += 1
        if _sensitive_reference(process.borrador_f22_ref):
            counts['process_f22_ref_sensitive'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        fiscal_year = _annual_summary_fiscal_year(summary) or process.anio_tributario - 1
        if _approved_close_months(empresa_id=process.empresa_id, fiscal_year=fiscal_year) != expected_months:
            counts['twelve_closes_missing'] += 1
        if not ObligacionTributariaMensual.objects.filter(empresa=process.empresa, anio=fiscal_year).exists():
            counts['annual_obligations_missing'] += 1

        if process.estado in ANNUAL_REF_REQUIRED_STATES:
            if not has_text(process.paquete_ddjj_ref):
                counts['process_ddjj_ref_missing'] += 1
            if not has_text(process.borrador_f22_ref):
                counts['process_f22_ref_missing'] += 1

    return dict(sorted(counts.items()))


def _collect_annual_document_issues(processes, ddjj_preparations, f22_preparations) -> dict[str, int]:
    counts = Counter()
    ddjj_by_process = {item.proceso_renta_anual_id: item for item in ddjj_preparations}
    f22_by_process = {item.proceso_renta_anual_id: item for item in f22_preparations}

    for process in processes:
        if process.id not in ddjj_by_process:
            counts['ddjj_missing_for_process'] += 1
        if process.id not in f22_by_process:
            counts['f22_missing_for_process'] += 1

    for ddjj in ddjj_preparations:
        try:
            ddjj.full_clean()
        except ValidationError:
            counts['ddjj_invalid_model'] += 1
        if ddjj.estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
            counts['ddjj_presented_boundary'] += 1
        if ddjj.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            counts['ddjj_not_traceable'] += 1
        if not ddjj.resumen_paquete:
            counts['ddjj_summary_missing'] += 1
        ddjj_summary = ddjj.resumen_paquete.get('resumen_anual') if isinstance(ddjj.resumen_paquete, dict) else None
        if _annual_summary_fiscal_year_mismatch(ddjj_summary, ddjj.anio_tributario):
            counts['ddjj_summary_fiscal_year_mismatch'] += 1
        if contains_sensitive_reference(ddjj.resumen_paquete or {}, include_sensitive_keys=True):
            counts['ddjj_sensitive_payload'] += 1
        if _sensitive_reference(ddjj.paquete_ref):
            counts['ddjj_ref_sensitive'] += 1
        if ddjj.estado_preparacion in ANNUAL_REF_REQUIRED_STATES and not has_text(ddjj.paquete_ref):
            counts['ddjj_ref_missing'] += 1

    for f22 in f22_preparations:
        try:
            f22.full_clean()
        except ValidationError:
            counts['f22_invalid_model'] += 1
        if f22.estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
            counts['f22_presented_boundary'] += 1
        if f22.estado_preparacion not in ANNUAL_TRACEABLE_STATES:
            counts['f22_not_traceable'] += 1
        if not f22.resumen_f22:
            counts['f22_summary_missing'] += 1
        f22_summary = f22.resumen_f22.get('resumen_anual') if isinstance(f22.resumen_f22, dict) else None
        if _annual_summary_fiscal_year_mismatch(f22_summary, f22.anio_tributario):
            counts['f22_summary_fiscal_year_mismatch'] += 1
        if contains_sensitive_reference(f22.resumen_f22 or {}, include_sensitive_keys=True):
            counts['f22_sensitive_payload'] += 1
        if _sensitive_reference(f22.borrador_ref):
            counts['f22_ref_sensitive'] += 1
        if f22.estado_preparacion in ANNUAL_REF_REQUIRED_STATES and not has_text(f22.borrador_ref):
            counts['f22_ref_missing'] += 1

    return dict(sorted(counts.items()))


def collect_stage6_renta_anual_readiness(
    *,
    stage5_evidence_ref: str = '',
    stage4_sii_evidence_ref: str = '',
    fiscal_rule_ref: str = '',
    certificates_proof_ref: str = '',
    responsible_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
    fiscal_configs = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario')
    active_fiscal_configs = fiscal_configs.filter(estado=EstadoRegistro.ACTIVE)
    active_fiscal_company_ids = set(active_fiscal_configs.values_list('empresa_id', flat=True))
    invalid_active_fiscal_configs = _count_invalid(active_fiscal_configs)

    capabilities = CapacidadTributariaSII.objects.select_related('empresa')
    open_capabilities = capabilities.filter(estado_gate=EstadoGateSII.OPEN)
    annual_open_capabilities = open_capabilities.filter(
        capacidad_key__in=[CapacidadSII.DDJJ_PREPARACION, CapacidadSII.F22_PREPARACION]
    )
    invalid_annual_open_capabilities = _count_invalid(annual_open_capabilities)
    open_ddjj_capabilities = annual_open_capabilities.filter(capacidad_key=CapacidadSII.DDJJ_PREPARACION)
    open_f22_capabilities = annual_open_capabilities.filter(capacidad_key=CapacidadSII.F22_PREPARACION)
    annual_production_capabilities = annual_open_capabilities.filter(ambiente=AmbienteSII.PRODUCTION)

    approved_closes = CierreMensualContable.objects.filter(estado=EstadoCierreMensual.APPROVED)
    obligations = ObligacionTributariaMensual.objects.all()

    annual_processes = ProcesoRentaAnual.objects.select_related('empresa')
    process_issues = _collect_process_issues(annual_processes)

    ddjj_preparations = DDJJPreparacionAnual.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'proceso_renta_anual',
    )
    f22_preparations = F22PreparacionAnual.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'proceso_renta_anual',
    )
    annual_document_issues = _collect_annual_document_issues(
        annual_processes,
        ddjj_preparations,
        f22_preparations,
    )
    open_annual_capabilities_without_fiscal_config = _count_without_active_fiscal_config(
        annual_open_capabilities,
        active_fiscal_company_ids,
    )
    annual_processes_without_fiscal_config = _count_without_active_fiscal_config(
        annual_processes,
        active_fiscal_company_ids,
    )
    ddjj_without_fiscal_config = _count_without_active_fiscal_config(
        ddjj_preparations,
        active_fiscal_company_ids,
    )
    f22_without_fiscal_config = _count_without_active_fiscal_config(
        f22_preparations,
        active_fiscal_company_ids,
    )

    tax_support_documents = DocumentoEmitido.objects.filter(tipo_documental=TipoDocumental.TAX_SUPPORT)
    usable_tax_support_documents = tax_support_documents.filter(
        estado__in=[EstadoDocumento.ISSUED, EstadoDocumento.FORMALIZED, EstadoDocumento.ARCHIVED]
    )
    invalid_tax_support_documents = _count_invalid(usable_tax_support_documents)

    final_evidence = {
        'stage5_evidence_ref': _non_sensitive_reference(stage5_evidence_ref),
        'stage4_sii_evidence_ref': _non_sensitive_reference(stage4_sii_evidence_ref),
        'fiscal_rule_ref': _non_sensitive_reference(fiscal_rule_ref),
        'certificates_proof_ref': _non_sensitive_reference(certificates_proof_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    final_evidence_sensitive = {
        'stage5_evidence_ref': _sensitive_reference(stage5_evidence_ref),
        'stage4_sii_evidence_ref': _sensitive_reference(stage4_sii_evidence_ref),
        'fiscal_rule_ref': _sensitive_reference(fiscal_rule_ref),
        'certificates_proof_ref': _sensitive_reference(certificates_proof_ref),
        'responsible_ref': _sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_trace_sensitive = {
        'source_label': _sensitive_reference(source_label),
        'authorization_ref': _sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE6_SOURCE_KINDS
    annual_status_transition_metadata_missing = count_audit_events_without_transition_metadata(
        event_types=STAGE6_ANNUAL_STATUS_UPDATE_EVENT_TYPES
    )

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage6.source_kind_not_authorized',
                'La readiness local de Etapa 6 no puede cerrar Renta anual sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, missing_code, sensitive_code, missing_message, sensitive_message in [
            (
                'source_label',
                'stage6.source_label_missing',
                'stage6.source_label_sensitive',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 6.',
                'La etiqueta de fuente autorizada de Etapa 6 contiene una referencia sensible.',
            ),
            (
                'authorization_ref',
                'stage6.authorization_ref_missing',
                'stage6.authorization_ref_sensitive',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 6.',
                'La referencia de autorizacion de Etapa 6 contiene valores sensibles.',
            ),
        ]:
            if source_trace_sensitive[key]:
                issues.append(_issue(sensitive_code, sensitive_message))
            elif not source_trace[key]:
                issues.append(_issue(missing_code, missing_message))
    if annual_status_transition_metadata_missing:
        issues.append(
            _issue(
                'stage6.audit.annual_status_transition_metadata_missing',
                'Existen eventos status_updated de DDJJ/F22 sin campo_estado, estado_anterior o estado_nuevo.',
                count=annual_status_transition_metadata_missing,
            )
        )
    if active_fiscal_configs.count() == 0:
        issues.append(
            _issue(
                'stage6.fiscal_config_missing',
                'Etapa 6 requiere ConfiguracionFiscalEmpresa activa para preparar renta anual.',
            )
        )
    if invalid_active_fiscal_configs:
        issues.append(
            _issue(
                'stage6.fiscal_config_invalid',
                'Existen configuraciones fiscales activas que no pasan validacion de dominio.',
                count=invalid_active_fiscal_configs,
            )
        )
    if open_ddjj_capabilities.count() == 0:
        issues.append(
            _issue(
                'stage6.ddjj.open_capability_missing',
                'Etapa 6 requiere capacidad DDJJPreparacion abierta y trazable.',
            )
        )
    if open_f22_capabilities.count() == 0:
        issues.append(
            _issue(
                'stage6.f22.open_capability_missing',
                'Etapa 6 requiere capacidad F22Preparacion abierta y trazable.',
            )
        )
    if invalid_annual_open_capabilities:
        issues.append(
            _issue(
                'stage6.annual_capability_invalid',
                'Existen capacidades anuales SII abiertas que no pasan readiness de dominio.',
                count=invalid_annual_open_capabilities,
            )
        )
    if open_annual_capabilities_without_fiscal_config:
        issues.append(
            _issue(
                'stage6.annual_capability_fiscal_config_missing',
                'Existen capacidades anuales SII abiertas para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=open_annual_capabilities_without_fiscal_config,
            )
        )
    if annual_processes.count() == 0:
        issues.append(
            _issue(
                'stage6.annual_process_missing',
                'Etapa 6 requiere al menos un ProcesoRentaAnual preparado.',
            )
        )
    if annual_processes_without_fiscal_config:
        issues.append(
            _issue(
                'stage6.annual_process_fiscal_config_missing',
                'Existen procesos de renta anual para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=annual_processes_without_fiscal_config,
            )
        )
    if approved_closes.count() < 12:
        issues.append(
            _issue(
                'stage6.twelve_approved_closes_missing',
                'Etapa 6 requiere doce cierres mensuales aprobados del ano comercial.',
            )
        )
    if obligations.count() == 0:
        issues.append(
            _issue(
                'stage6.annual_obligations_missing',
                'Etapa 6 requiere obligaciones tributarias mensuales trazables para consolidar renta anual.',
            )
        )
    if ddjj_preparations.count() == 0:
        issues.append(_issue('stage6.ddjj_missing', 'Etapa 6 requiere preparacion DDJJ anual.'))
    if ddjj_without_fiscal_config:
        issues.append(
            _issue(
                'stage6.ddjj_fiscal_config_missing',
                'Existen DDJJ anuales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=ddjj_without_fiscal_config,
            )
        )
    if f22_preparations.count() == 0:
        issues.append(_issue('stage6.f22_missing', 'Etapa 6 requiere preparacion F22 anual.'))
    if f22_without_fiscal_config:
        issues.append(
            _issue(
                'stage6.f22_fiscal_config_missing',
                'Existen F22 anuales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
                count=f22_without_fiscal_config,
            )
        )
    if usable_tax_support_documents.count() == 0:
        issues.append(
            _issue(
                'stage6.tax_support_document_missing',
                'Etapa 6 requiere respaldo tributario PDF/certificado generado o cargado de forma controlada.',
            )
        )
    if invalid_tax_support_documents:
        issues.append(
            _issue(
                'stage6.tax_support_document_invalid',
                'Existen respaldos tributarios que no pasan validacion documental.',
                count=invalid_tax_support_documents,
            )
        )

    for key, code, message in [
        (
            'process_invalid_model',
            'stage6.annual_process_invalid',
            'Existen procesos de renta anual que no pasan validacion de dominio.',
        ),
        (
            'process_not_traceable',
            'stage6.annual_process_not_traceable',
            'Existen procesos de renta anual sin estado trazable de preparacion.',
        ),
        (
            'process_presented_boundary',
            'stage6.annual_process_presented_boundary',
            'PresentacionAnualFinal no se registra desde el flujo local sin gate formal.',
        ),
        (
            'process_summary_missing',
            'stage6.annual_process_summary_missing',
            'ProcesoRentaAnual requiere resumen_anual con fiscal_year y obligaciones.',
        ),
        (
            'process_fiscal_year_mismatch',
            'stage6.annual_process_fiscal_year_mismatch',
            'ProcesoRentaAnual tiene resumen_anual de un ano comercial distinto al ano tributario.',
        ),
        (
            'process_sensitive_payload',
            'stage6.annual_process_sensitive_payload',
            'ProcesoRentaAnual contiene resumen_anual sensible.',
        ),
        (
            'process_ddjj_ref_sensitive',
            'stage6.process_ddjj_ref_sensitive',
            'Proceso anual contiene paquete_ddjj_ref sensible.',
        ),
        (
            'process_f22_ref_sensitive',
            'stage6.process_f22_ref_sensitive',
            'Proceso anual contiene borrador_f22_ref sensible.',
        ),
        (
            'twelve_closes_missing',
            'stage6.process_twelve_closes_missing',
            'Existen procesos anuales sin doce cierres aprobados del ano comercial.',
        ),
        (
            'annual_obligations_missing',
            'stage6.process_obligations_missing',
            'Existen procesos anuales sin obligaciones mensuales trazables.',
        ),
        (
            'process_ddjj_ref_missing',
            'stage6.process_ddjj_ref_missing',
            'Proceso anual aprobado/observado/rectificado requiere paquete_ddjj_ref.',
        ),
        (
            'process_f22_ref_missing',
            'stage6.process_f22_ref_missing',
            'Proceso anual aprobado/observado/rectificado requiere borrador_f22_ref.',
        ),
    ]:
        if process_issues.get(key):
            issues.append(_issue(code, message, count=process_issues[key]))

    for key, code, message in [
        (
            'ddjj_missing_for_process',
            'stage6.ddjj_missing_for_process',
            'Existen procesos anuales sin DDJJ asociada.',
        ),
        (
            'f22_missing_for_process',
            'stage6.f22_missing_for_process',
            'Existen procesos anuales sin F22 asociado.',
        ),
        (
            'ddjj_invalid_model',
            'stage6.ddjj_invalid',
            'Existen DDJJ preparadas que no pasan validacion de dominio.',
        ),
        (
            'f22_invalid_model',
            'stage6.f22_invalid',
            'Existen F22 preparados que no pasan validacion de dominio.',
        ),
        (
            'ddjj_presented_boundary',
            'stage6.ddjj_presented_boundary',
            'DDJJ presentada queda fuera del flujo local sin gate formal.',
        ),
        (
            'f22_presented_boundary',
            'stage6.f22_presented_boundary',
            'F22 presentado queda fuera del flujo local sin gate formal.',
        ),
        (
            'ddjj_not_traceable',
            'stage6.ddjj_not_traceable',
            'Existen DDJJ sin estado trazable de preparacion.',
        ),
        (
            'f22_not_traceable',
            'stage6.f22_not_traceable',
            'Existen F22 sin estado trazable de preparacion.',
        ),
        (
            'ddjj_summary_missing',
            'stage6.ddjj_summary_missing',
            'DDJJ requiere resumen_paquete trazable.',
        ),
        (
            'ddjj_summary_fiscal_year_mismatch',
            'stage6.ddjj_summary_fiscal_year_mismatch',
            'DDJJ contiene resumen anual de un ano comercial distinto al ano tributario.',
        ),
        (
            'ddjj_sensitive_payload',
            'stage6.ddjj_sensitive_payload',
            'DDJJ contiene resumen_paquete sensible.',
        ),
        (
            'ddjj_ref_sensitive',
            'stage6.ddjj_ref_sensitive',
            'DDJJ contiene paquete_ref sensible.',
        ),
        (
            'f22_summary_missing',
            'stage6.f22_summary_missing',
            'F22 requiere resumen_f22 trazable.',
        ),
        (
            'f22_summary_fiscal_year_mismatch',
            'stage6.f22_summary_fiscal_year_mismatch',
            'F22 contiene resumen anual de un ano comercial distinto al ano tributario.',
        ),
        (
            'f22_sensitive_payload',
            'stage6.f22_sensitive_payload',
            'F22 contiene resumen_f22 sensible.',
        ),
        (
            'f22_ref_sensitive',
            'stage6.f22_ref_sensitive',
            'F22 contiene borrador_ref sensible.',
        ),
        (
            'ddjj_ref_missing',
            'stage6.ddjj_ref_missing',
            'DDJJ aprobada, observada o rectificada requiere paquete_ref.',
        ),
        (
            'f22_ref_missing',
            'stage6.f22_ref_missing',
            'F22 aprobado, observado o rectificado requiere borrador_ref.',
        ),
    ]:
        if annual_document_issues.get(key):
            issues.append(_issue(code, message, count=annual_document_issues[key]))

    for key, missing_code, sensitive_code, missing_message, sensitive_message in [
        (
            'stage5_evidence_ref',
            'stage6.stage5_evidence_ref_missing',
            'stage6.stage5_evidence_ref_sensitive',
            'Falta referencia no sensible a cierre mensual/ledger habilitante.',
            'La referencia a cierre mensual/ledger habilitante contiene valores sensibles.',
        ),
        (
            'stage4_sii_evidence_ref',
            'stage6.stage4_sii_evidence_ref_missing',
            'stage6.stage4_sii_evidence_ref_sensitive',
            'Falta referencia no sensible a readiness SII anual.',
            'La referencia a readiness SII anual contiene valores sensibles.',
        ),
        (
            'fiscal_rule_ref',
            'stage6.fiscal_rule_ref_missing',
            'stage6.fiscal_rule_ref_sensitive',
            'Falta referencia no sensible a regla fiscal anual validada.',
            'La referencia a regla fiscal anual validada contiene valores sensibles.',
        ),
        (
            'certificates_proof_ref',
            'stage6.certificates_proof_ref_missing',
            'stage6.certificates_proof_ref_sensitive',
            'Falta referencia no sensible a certificados o respaldos tributarios anuales.',
            'La referencia a certificados o respaldos tributarios anuales contiene valores sensibles.',
        ),
        (
            'responsible_ref',
            'stage6.responsible_ref_missing',
            'stage6.responsible_ref_sensitive',
            'Falta referencia no sensible a responsables tributarios anuales.',
            'La referencia a responsables tributarios anuales contiene valores sensibles.',
        ),
    ]:
        if final_evidence_sensitive[key]:
            issues.append(_issue(sensitive_code, sensitive_message))
        elif not final_evidence[key]:
            issues.append(_issue(missing_code, missing_message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 6 - Renta anual',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_STAGE6_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage6_renta_anual': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'fiscal_setup': {
                'configs_total': fiscal_configs.count(),
                'active_configs': active_fiscal_configs.count(),
                'invalid_active_configs': invalid_active_fiscal_configs,
            },
            'annual_capabilities': {
                'total': capabilities.count(),
                'annual_open_total': annual_open_capabilities.count(),
                'open_ddjj': open_ddjj_capabilities.count(),
                'open_f22': open_f22_capabilities.count(),
                'open_production': annual_production_capabilities.count(),
                'invalid_open': invalid_annual_open_capabilities,
                'open_without_active_fiscal_config': open_annual_capabilities_without_fiscal_config,
                'by_capability': _count_by(annual_open_capabilities, 'capacidad_key'),
            },
            'monthly_sources': {
                'approved_closes': approved_closes.count(),
                'approved_closes_by_year': _count_by(approved_closes, 'anio'),
                'obligations_total': obligations.count(),
                'obligations_by_year': _count_by(obligations, 'anio'),
                'obligations_by_state': _count_by(obligations, 'estado_preparacion'),
            },
            'annual_process': {
                'processes_total': annual_processes.count(),
                'processes_by_state': _count_by(annual_processes, 'estado'),
                'without_active_fiscal_config': annual_processes_without_fiscal_config,
                **process_issues,
            },
            'annual_documents': {
                'ddjj_total': ddjj_preparations.count(),
                'ddjj_by_state': _count_by(ddjj_preparations, 'estado_preparacion'),
                'ddjj_without_active_fiscal_config': ddjj_without_fiscal_config,
                'f22_total': f22_preparations.count(),
                'f22_by_state': _count_by(f22_preparations, 'estado_preparacion'),
                'f22_without_active_fiscal_config': f22_without_fiscal_config,
                **annual_document_issues,
            },
            'tax_support_documents': {
                'total': tax_support_documents.count(),
                'usable': usable_tax_support_documents.count(),
                'invalid_usable': invalid_tax_support_documents,
                'by_state': _count_by(tax_support_documents, 'estado'),
            },
            'audit': {
                'annual_status_transition_metadata_missing': annual_status_transition_metadata_missing,
            },
            'final_evidence': final_evidence,
            'final_evidence_sensitive': final_evidence_sensitive,
            'source_trace': source_trace,
            'source_trace_sensitive': source_trace_sensitive,
        },
        'limitations': [
            'Auditoria local de solo lectura; no presenta DDJJ, F22 ni declaraciones finales.',
            'No usa secretos, certificados reales, .env, datos reales ni ambientes SII externos.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No cierra Etapa 6 sin configuracion fiscal activa por empresa, doce cierres evidenciados, regla fiscal validada y certificados/respaldos controlados.',
        ],
    }
