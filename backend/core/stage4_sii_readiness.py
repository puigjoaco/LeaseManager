from __future__ import annotations

from collections import Counter
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoPreparacionTributaria, EstadoRegistro
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from sii.models import (
    AmbienteSII,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    DTEEmitido,
    EstadoDTE,
    EstadoGateSII,
    F22PreparacionAnual,
    F29PreparacionMensual,
    ProcesoRentaAnual,
    has_text,
)


DTE_EXTERNAL_STATES = {
    EstadoDTE.SENT_MANUAL,
    EstadoDTE.ACCEPTED,
    EstadoDTE.REJECTED,
    EstadoDTE.CANCELED,
}

DTE_FINAL_STATES = {
    EstadoDTE.ACCEPTED,
    EstadoDTE.REJECTED,
    EstadoDTE.CANCELED,
}

TAX_REF_REQUIRED_STATES = {
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}

AUTHORIZED_STAGE4_SOURCE_KINDS = {'snapshot_controlado', 'real_autorizado'}
CAPABILITY_REFERENCE_FIELDS = (
    'certificado_ref',
    'evidencia_ref',
    'prueba_flujo_ref',
    'autorizacion_ambiente_ref',
    'regla_fiscal_ref',
)


def _non_sensitive_reference(value: str) -> bool:
    return is_non_sensitive_reference(value)


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


def _capability_has_sensitive_reference(capability) -> bool:
    return any(
        has_text(getattr(capability, field_name, ''))
        and not is_non_sensitive_reference(getattr(capability, field_name, ''))
        for field_name in CAPABILITY_REFERENCE_FIELDS
    ) or contains_sensitive_reference(capability.ultimo_resultado or {})


def _collect_dte_issues(dtes) -> dict[str, int]:
    counts = Counter()
    for dte in dtes:
        try:
            dte.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        if dte.estado_dte in DTE_EXTERNAL_STATES and not has_text(dte.sii_track_id):
            counts['external_tracking_missing'] += 1
        if has_text(dte.sii_track_id) and not is_non_sensitive_reference(dte.sii_track_id):
            counts['sensitive_tracking_ref'] += 1
        if dte.estado_dte in DTE_FINAL_STATES and not has_text(dte.ultimo_estado_sii):
            counts['external_status_missing'] += 1

    return dict(sorted(counts.items()))


def _collect_f29_issues(f29_drafts) -> dict[str, int]:
    counts = Counter()
    for draft in f29_drafts:
        try:
            draft.full_clean()
        except ValidationError:
            counts['invalid_model'] += 1

        if draft.estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
            counts['presented_boundary'] += 1
        if draft.estado_preparacion in TAX_REF_REQUIRED_STATES and not has_text(draft.borrador_ref):
            counts['approved_ref_missing'] += 1
        if has_text(draft.borrador_ref) and not is_non_sensitive_reference(draft.borrador_ref):
            counts['sensitive_ref'] += 1

    return dict(sorted(counts.items()))


def _collect_annual_issues(processes, ddjj_preparations, f22_preparations) -> dict[str, int]:
    counts = Counter()
    for process in processes:
        if process.estado == EstadoPreparacionTributaria.PRESENTED:
            counts['process_presented_boundary'] += 1
        if process.estado in {
            EstadoPreparacionTributaria.PREPARED,
            EstadoPreparacionTributaria.APPROVED,
        } and not process.resumen_anual:
            counts['process_summary_missing'] += 1
        if (
            has_text(process.paquete_ddjj_ref)
            and not is_non_sensitive_reference(process.paquete_ddjj_ref)
        ) or (
            has_text(process.borrador_f22_ref)
            and not is_non_sensitive_reference(process.borrador_f22_ref)
        ):
            counts['sensitive_ref'] += 1

    for ddjj in ddjj_preparations:
        try:
            ddjj.full_clean()
        except ValidationError:
            counts['ddjj_invalid_model'] += 1
        if ddjj.estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
            counts['ddjj_presented_boundary'] += 1
        if ddjj.estado_preparacion in TAX_REF_REQUIRED_STATES and not has_text(ddjj.paquete_ref):
            counts['ddjj_ref_missing'] += 1
        if has_text(ddjj.paquete_ref) and not is_non_sensitive_reference(ddjj.paquete_ref):
            counts['sensitive_ref'] += 1

    for f22 in f22_preparations:
        try:
            f22.full_clean()
        except ValidationError:
            counts['f22_invalid_model'] += 1
        if f22.estado_preparacion == EstadoPreparacionTributaria.PRESENTED:
            counts['f22_presented_boundary'] += 1
        if f22.estado_preparacion in TAX_REF_REQUIRED_STATES and not has_text(f22.borrador_ref):
            counts['f22_ref_missing'] += 1
        if has_text(f22.borrador_ref) and not is_non_sensitive_reference(f22.borrador_ref):
            counts['sensitive_ref'] += 1

    return dict(sorted(counts.items()))


def collect_stage4_sii_readiness(
    *,
    stage5_evidence_ref: str = '',
    environment_proof_ref: str = '',
    fiscal_rule_ref: str = '',
    responsible_ref: str = '',
    source_label: str = '',
    authorization_ref: str = '',
    source_kind: str = 'local',
) -> dict[str, Any]:
    fiscal_configs = ConfiguracionFiscalEmpresa.objects.select_related('empresa', 'regimen_tributario')
    active_fiscal_configs = fiscal_configs.filter(estado=EstadoRegistro.ACTIVE)
    invalid_active_fiscal_configs = _count_invalid(active_fiscal_configs)
    active_fiscal_company_ids = set(active_fiscal_configs.values_list('empresa_id', flat=True))

    capabilities = CapacidadTributariaSII.objects.select_related('empresa')
    open_capabilities = capabilities.filter(estado_gate=EstadoGateSII.OPEN)
    invalid_open_capabilities = _count_invalid(open_capabilities)
    open_dte_capabilities = open_capabilities.filter(capacidad_key=CapacidadSII.DTE_EMISION)
    open_f29_capabilities = open_capabilities.filter(capacidad_key=CapacidadSII.F29_PREPARACION)
    production_open_capabilities = open_capabilities.filter(ambiente=AmbienteSII.PRODUCTION)
    open_capabilities_without_fiscal_config = _count_without_active_fiscal_config(
        open_capabilities,
        active_fiscal_company_ids,
    )
    open_capabilities_with_sensitive_refs = sum(
        1 for capability in open_capabilities if _capability_has_sensitive_reference(capability)
    )

    dtes = DTEEmitido.objects.select_related(
        'empresa',
        'capacidad_tributaria',
        'contrato',
        'pago_mensual',
        'distribucion_cobro_mensual',
        'arrendatario',
    )
    dte_issues = _collect_dte_issues(dtes)
    dtes_without_fiscal_config = _count_without_active_fiscal_config(dtes, active_fiscal_company_ids)

    f29_drafts = F29PreparacionMensual.objects.select_related('empresa', 'capacidad_tributaria', 'cierre_mensual')
    f29_issues = _collect_f29_issues(f29_drafts)
    f29_without_fiscal_config = _count_without_active_fiscal_config(f29_drafts, active_fiscal_company_ids)

    annual_processes = ProcesoRentaAnual.objects.select_related('empresa')
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
    annual_issues = _collect_annual_issues(annual_processes, ddjj_preparations, f22_preparations)

    final_evidence = {
        'stage5_evidence_ref': _non_sensitive_reference(stage5_evidence_ref),
        'environment_proof_ref': _non_sensitive_reference(environment_proof_ref),
        'fiscal_rule_ref': _non_sensitive_reference(fiscal_rule_ref),
        'responsible_ref': _non_sensitive_reference(responsible_ref),
    }
    source_trace = {
        'source_label': _non_sensitive_reference(source_label),
        'authorization_ref': _non_sensitive_reference(authorization_ref),
    }
    source_kind_authorized_for_close = source_kind in AUTHORIZED_STAGE4_SOURCE_KINDS

    issues: list[dict[str, Any]] = []
    if not source_kind_authorized_for_close:
        issues.append(
            _issue(
                'stage4.source_kind_not_authorized',
                'La readiness local de Etapa 4 no puede cerrar SII sin fuente snapshot_controlado o real_autorizado.',
            )
        )
    else:
        for key, code, message in [
            (
                'source_label',
                'stage4.source_label_missing',
                'Falta etiqueta no sensible de la fuente autorizada de Etapa 4.',
            ),
            (
                'authorization_ref',
                'stage4.authorization_ref_missing',
                'Falta referencia no sensible a la autorizacion de uso de la fuente Etapa 4.',
            ),
        ]:
            if not source_trace[key]:
                issues.append(_issue(code, message))
    if active_fiscal_configs.count() == 0:
        issues.append(
            _issue(
                'stage4.fiscal_config_missing',
                'Etapa 4 requiere al menos una ConfiguracionFiscalEmpresa activa.',
            )
        )
    if invalid_active_fiscal_configs:
        issues.append(
            _issue(
                'stage4.fiscal_config_invalid',
                'Existen configuraciones fiscales activas que no pasan validacion de dominio.',
                count=invalid_active_fiscal_configs,
            )
        )
    if open_dte_capabilities.count() == 0:
        issues.append(
            _issue(
                'stage4.dte.open_capability_missing',
                'Etapa 4 requiere capacidad DTEEmision abierta y trazable para cierre.',
            )
        )
    if open_f29_capabilities.count() == 0:
        issues.append(
            _issue(
                'stage4.f29.open_capability_missing',
                'Etapa 4 requiere capacidad F29Preparacion abierta y trazable para cierre.',
            )
        )
    if invalid_open_capabilities:
        issues.append(
            _issue(
                'stage4.capability_invalid',
                'Existen capacidades SII abiertas que no pasan readiness de dominio.',
                count=invalid_open_capabilities,
            )
        )
    if open_capabilities_with_sensitive_refs:
        issues.append(
            _issue(
                'stage4.capability_sensitive_reference',
                'Existen capacidades SII abiertas con referencias sensibles o payloads de resultado sensibles.',
                count=open_capabilities_with_sensitive_refs,
            )
        )
    if open_capabilities_without_fiscal_config:
        issues.append(
            _issue(
                'stage4.capability_fiscal_config_missing',
                'Existen capacidades SII abiertas sin ConfiguracionFiscalEmpresa activa para la misma empresa.',
                count=open_capabilities_without_fiscal_config,
            )
        )
    if dtes.count() == 0:
        issues.append(
            _issue(
                'stage4.dte_missing',
                'No existen DTE locales para auditar emision o estado controlado.',
            )
        )
    if dte_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage4.dte_invalid',
                'Existen DTE que no pasan validacion de dominio.',
                count=dte_issues['invalid_model'],
            )
        )
    if dte_issues.get('external_tracking_missing'):
        issues.append(
            _issue(
                'stage4.dte_external_tracking_missing',
                'Existen DTE en estado externo sin sii_track_id trazable.',
                count=dte_issues['external_tracking_missing'],
            )
        )
    if dte_issues.get('sensitive_tracking_ref'):
        issues.append(
            _issue(
                'stage4.dte_sensitive_tracking_ref',
                'Existen DTE con sii_track_id sensible; debe ser una referencia no sensible.',
                count=dte_issues['sensitive_tracking_ref'],
            )
        )
    if dte_issues.get('external_status_missing'):
        issues.append(
            _issue(
                'stage4.dte_external_status_missing',
                'Existen DTE aceptados/rechazados/anulados sin ultimo_estado_sii trazable.',
                count=dte_issues['external_status_missing'],
            )
        )
    if dtes_without_fiscal_config:
        issues.append(
            _issue(
                'stage4.dte_fiscal_config_missing',
                'Existen DTE asociados a empresas sin ConfiguracionFiscalEmpresa activa.',
                count=dtes_without_fiscal_config,
            )
        )
    if f29_drafts.count() == 0:
        issues.append(
            _issue(
                'stage4.f29_missing',
                'No existen borradores F29 locales para auditar preparacion mensual.',
            )
        )
    if f29_issues.get('invalid_model'):
        issues.append(
            _issue(
                'stage4.f29_invalid',
                'Existen borradores F29 que no pasan validacion de dominio.',
                count=f29_issues['invalid_model'],
            )
        )
    if f29_issues.get('presented_boundary'):
        issues.append(
            _issue(
                'stage4.f29_presented_boundary',
                'F29Presentacion no se registra desde el flujo local sin gate propio.',
                count=f29_issues['presented_boundary'],
            )
        )
    if f29_issues.get('approved_ref_missing'):
        issues.append(
            _issue(
                'stage4.f29_ref_missing',
                'F29 aprobado, observado o rectificado requiere borrador_ref trazable.',
                count=f29_issues['approved_ref_missing'],
            )
        )
    if f29_issues.get('sensitive_ref'):
        issues.append(
            _issue(
                'stage4.f29_sensitive_ref',
                'Existen borradores F29 con borrador_ref sensible.',
                count=f29_issues['sensitive_ref'],
            )
        )
    if f29_without_fiscal_config:
        issues.append(
            _issue(
                'stage4.f29_fiscal_config_missing',
                'Existen borradores F29 asociados a empresas sin ConfiguracionFiscalEmpresa activa.',
                count=f29_without_fiscal_config,
            )
        )

    for key, code, message in [
        (
            'process_presented_boundary',
            'stage4.annual_process_presented_boundary',
            'PresentacionAnualFinal no se registra desde el flujo local.',
        ),
        (
            'ddjj_presented_boundary',
            'stage4.ddjj_presented_boundary',
            'DDJJ presentada queda fuera del flujo local sin gate formal.',
        ),
        (
            'f22_presented_boundary',
            'stage4.f22_presented_boundary',
            'F22 presentado queda fuera del flujo local sin gate formal.',
        ),
        (
            'process_summary_missing',
            'stage4.annual_process_summary_missing',
            'Proceso anual preparado/aprobado requiere resumen_anual trazable.',
        ),
        (
            'ddjj_invalid_model',
            'stage4.ddjj_invalid',
            'Existen DDJJ preparadas que no pasan validacion de dominio.',
        ),
        (
            'f22_invalid_model',
            'stage4.f22_invalid',
            'Existen F22 preparados que no pasan validacion de dominio.',
        ),
        (
            'ddjj_ref_missing',
            'stage4.ddjj_ref_missing',
            'DDJJ aprobada, observada o rectificada requiere paquete_ref trazable.',
        ),
        (
            'f22_ref_missing',
            'stage4.f22_ref_missing',
            'F22 aprobado, observado o rectificado requiere borrador_ref trazable.',
        ),
        (
            'sensitive_ref',
            'stage4.annual_sensitive_ref',
            'Existen preparaciones anuales con referencias sensibles.',
        ),
    ]:
        if annual_issues.get(key):
            issues.append(_issue(code, message, count=annual_issues[key]))

    for key, code, message in [
        (
            'stage5_evidence_ref',
            'stage4.stage5_evidence_ref_missing',
            'Falta referencia no sensible a ledger/cierre mensual habilitante.',
        ),
        (
            'environment_proof_ref',
            'stage4.environment_proof_ref_missing',
            'Falta referencia no sensible a ambiente SII autorizado o prueba aislada.',
        ),
        (
            'fiscal_rule_ref',
            'stage4.fiscal_rule_ref_missing',
            'Falta referencia no sensible a regla fiscal validada.',
        ),
        (
            'responsible_ref',
            'stage4.responsible_ref_missing',
            'Falta referencia no sensible a responsables tributarios.',
        ),
    ]:
        if not final_evidence[key]:
            issues.append(_issue(code, message))

    issue_counts = Counter(issue['severity'] for issue in issues)
    ready = issue_counts.get('blocking', 0) == 0

    return {
        'generated_at': timezone.now().isoformat(),
        'stage': 'Etapa 4 - SII y DTE',
        'source_kind': source_kind,
        'authorized_source_kinds': sorted(AUTHORIZED_STAGE4_SOURCE_KINDS),
        'source_kind_authorized_for_close': source_kind_authorized_for_close,
        'classification': 'resuelto_confirmado' if ready else 'parcial',
        'ready_for_stage4_sii': ready,
        'issue_counts': dict(sorted(issue_counts.items())),
        'issues': issues,
        'sections': {
            'fiscal_setup': {
                'configs_total': fiscal_configs.count(),
                'active_configs': active_fiscal_configs.count(),
                'invalid_active_configs': invalid_active_fiscal_configs,
            },
            'capabilities': {
                'total': capabilities.count(),
                'by_state': _count_by(capabilities, 'estado_gate'),
                'by_capability': _count_by(capabilities, 'capacidad_key'),
                'open_total': open_capabilities.count(),
                'open_dte': open_dte_capabilities.count(),
                'open_f29': open_f29_capabilities.count(),
                'open_production': production_open_capabilities.count(),
                'invalid_open': invalid_open_capabilities,
                'open_sensitive_refs': open_capabilities_with_sensitive_refs,
                'open_without_active_fiscal_config': open_capabilities_without_fiscal_config,
            },
            'dte': {
                'total': dtes.count(),
                'by_state': _count_by(dtes, 'estado_dte'),
                'without_active_fiscal_config': dtes_without_fiscal_config,
                **dte_issues,
            },
            'f29': {
                'total': f29_drafts.count(),
                'by_state': _count_by(f29_drafts, 'estado_preparacion'),
                'without_active_fiscal_config': f29_without_fiscal_config,
                **f29_issues,
            },
            'annual': {
                'processes_total': annual_processes.count(),
                'processes_by_state': _count_by(annual_processes, 'estado'),
                'ddjj_total': ddjj_preparations.count(),
                'ddjj_by_state': _count_by(ddjj_preparations, 'estado_preparacion'),
                'f22_total': f22_preparations.count(),
                'f22_by_state': _count_by(f22_preparations, 'estado_preparacion'),
                **annual_issues,
            },
            'final_evidence': final_evidence,
            'source_trace': source_trace,
        },
        'limitations': [
            'Auditoria local de solo lectura; no conecta SII ni presenta DTE, F29, DDJJ o F22.',
            'No usa secretos, certificados, .env, datos reales ni ambientes externos.',
            'Local, fixture y demo solo diagnostican; el cierre exige source_kind snapshot_controlado o real_autorizado.',
            'No cierra Etapa 4 sin configuracion fiscal activa por empresa, ambiente autorizado y regla fiscal validada por SII, normativa o experto.',
        ],
    }
