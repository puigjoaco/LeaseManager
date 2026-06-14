from __future__ import annotations

from collections import Counter
import re
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditEvent
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
    AnnualEnterpriseRegisterMovement,
    AnnualEnterpriseRegisterSet,
    AnnualRealEstateItem,
    AnnualRealEstateSection,
    AnnualTaxArtifactMatrix,
    AnnualTaxArtifactMatrixItem,
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxOfficialSource,
    AnnualTaxSourceBundle,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    CapacidadSII,
    CapacidadTributariaSII,
    DDJJPreparacionAnual,
    EstadoAnnualEnterpriseRegister,
    EstadoAnnualRealEstateSection,
    EstadoAnnualTaxArtifactMatrix,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxOfficialSource,
    EstadoAnnualTaxSourceBundle,
    EstadoAnnualTaxWorkbook,
    EstadoReglaTributariaAnual,
    EstadoGateSII,
    EstadoMonthlyTaxFact,
    F22PreparacionAnual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualEnterpriseRegister,
    TipoAnnualTaxWorkbook,
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


def _count_annual_status_review_responsible_issues() -> dict[str, int]:
    counts = Counter()
    required_states = {str(state) for state in ANNUAL_REF_REQUIRED_STATES}
    events = AuditEvent.objects.filter(event_type__in=STAGE6_ANNUAL_STATUS_UPDATE_EVENT_TYPES).only('metadata')
    for event in events:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        if str(metadata.get('estado_nuevo') or '').strip() not in required_states:
            continue
        responsible_ref = str(metadata.get('responsable_revision_ref') or '').strip()
        if not responsible_ref:
            counts['missing'] += 1
        elif _sensitive_reference(responsible_ref):
            counts['sensitive'] += 1
    return dict(sorted(counts.items()))


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
        if _sensitive_reference(process.responsable_revision_ref):
            counts['process_responsible_ref_sensitive'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        fiscal_year = _annual_summary_fiscal_year(summary) or process.anio_tributario - 1
        if _approved_close_months(empresa_id=process.empresa_id, fiscal_year=fiscal_year) != expected_months:
            counts['twelve_closes_missing'] += 1
        if not ObligacionTributariaMensual.objects.filter(empresa=process.empresa, anio=fiscal_year).exists():
            counts['annual_obligations_missing'] += 1

        if process.estado in ANNUAL_TRACEABLE_STATES:
            if not process.source_bundle_id:
                counts['process_source_bundle_missing'] += 1
            else:
                bundle = process.source_bundle
                if bundle.empresa_id != process.empresa_id or bundle.anio_tributario != process.anio_tributario:
                    counts['process_source_bundle_mismatch'] += 1
                if bundle.estado != EstadoAnnualTaxSourceBundle.FROZEN:
                    counts['process_source_bundle_not_frozen'] += 1
                bundle_summary = summary.get('annual_tax_source_bundle') if isinstance(summary, dict) else None
                if not isinstance(bundle_summary, dict):
                    counts['process_source_bundle_summary_missing'] += 1
                elif (
                    bundle_summary.get('id') != bundle.id
                    or bundle_summary.get('hash_fuentes') != bundle.hash_fuentes
                ):
                    counts['process_source_bundle_summary_mismatch'] += 1

        if process.estado in ANNUAL_REF_REQUIRED_STATES:
            if not has_text(process.paquete_ddjj_ref):
                counts['process_ddjj_ref_missing'] += 1
            if not has_text(process.borrador_f22_ref):
                counts['process_f22_ref_missing'] += 1
            if not has_text(process.responsable_revision_ref):
                counts['process_responsible_ref_missing'] += 1

    return dict(sorted(counts.items()))


def _collect_source_bundle_issues(source_bundles, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    invalid_source_bundles = _count_invalid(source_bundles)
    if invalid_source_bundles:
        counts['source_bundle_invalid'] = invalid_source_bundles
    without_fiscal_config = _count_without_active_fiscal_config(source_bundles, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['source_bundle_fiscal_config_missing'] = without_fiscal_config
    return dict(sorted(counts.items()))


def _collect_official_source_issues(official_sources) -> dict[str, int]:
    counts = Counter()
    invalid_sources = _count_invalid(official_sources)
    if invalid_sources:
        counts['official_source_invalid'] = invalid_sources
    return dict(sorted(counts.items()))


def _collect_monthly_tax_fact_issues(monthly_tax_facts, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    expected_months = set(range(1, 13))
    invalid_facts = _count_invalid(monthly_tax_facts)
    if invalid_facts:
        counts['monthly_tax_fact_invalid'] = invalid_facts
    without_fiscal_config = _count_without_active_fiscal_config(monthly_tax_facts, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['monthly_tax_fact_fiscal_config_missing'] = without_fiscal_config

    normalized_facts = monthly_tax_facts.filter(estado=EstadoMonthlyTaxFact.NORMALIZED)
    fact_months_by_company_year = {}
    for empresa_id, anio, mes in normalized_facts.values_list('empresa_id', 'anio', 'mes'):
        fact_months_by_company_year.setdefault((empresa_id, anio), set()).add(mes)

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        fiscal_year = process.anio_tributario - 1
        months = fact_months_by_company_year.get((process.empresa_id, fiscal_year), set())
        if not months:
            counts['process_monthly_tax_facts_missing'] += 1
        elif months != expected_months:
            counts['process_monthly_tax_fact_months_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        fact_summary = summary.get('annual_tax_monthly_facts')
        if not isinstance(fact_summary, dict):
            counts['process_monthly_tax_fact_summary_missing'] += 1
            continue
        summary_months = fact_summary.get('months') or []
        try:
            normalized_summary_months = {int(month) for month in summary_months}
        except (TypeError, ValueError):
            normalized_summary_months = set()
        try:
            summary_total = int(fact_summary.get('total') or 0)
        except (TypeError, ValueError):
            summary_total = -1
        if normalized_summary_months != months or summary_total != len(months):
            counts['process_monthly_tax_fact_summary_mismatch'] += 1

    return dict(sorted(counts.items()))


def _collect_annual_tax_workbook_issues(workbooks, lines, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    expected_types = {TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT}
    invalid_workbooks = _count_invalid(workbooks)
    if invalid_workbooks:
        counts['tax_workbook_invalid'] = invalid_workbooks
    invalid_lines = _count_invalid(lines)
    if invalid_lines:
        counts['tax_workbook_line_invalid'] = invalid_lines
    without_fiscal_config = _count_without_active_fiscal_config(workbooks, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['tax_workbook_fiscal_config_missing'] = without_fiscal_config

    prepared_workbooks = workbooks.filter(estado=EstadoAnnualTaxWorkbook.PREPARED)
    workbooks_by_process = {}
    for workbook in prepared_workbooks:
        workbooks_by_process.setdefault(workbook.proceso_renta_anual_id, {})[workbook.tipo] = workbook

    active_line_counts = Counter()
    warning_line_counts = Counter()
    for line in lines.filter(estado=EstadoRegistro.ACTIVE).select_related('workbook'):
        active_line_counts[line.workbook_id] += 1
        warnings = line.warnings if isinstance(line.warnings, list) else []
        if warnings:
            warning_line_counts[line.workbook_id] += 1

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        process_workbooks = workbooks_by_process.get(process.id, {})
        present_types = set(process_workbooks.keys())
        if not present_types:
            counts['process_tax_workbooks_missing'] += 1
        elif present_types != expected_types:
            counts['process_tax_workbook_types_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        workbook_summary = summary.get('annual_tax_workbooks')
        if not isinstance(workbook_summary, dict):
            counts['process_tax_workbook_summary_missing'] += 1
        else:
            by_type = workbook_summary.get('by_type') if isinstance(workbook_summary.get('by_type'), dict) else {}
            try:
                summary_total = int(workbook_summary.get('total') or 0)
            except (TypeError, ValueError):
                summary_total = -1
            summary_types = set(workbook_summary.get('types') or [])
            if summary_total != len(process_workbooks) or summary_types != present_types:
                counts['process_tax_workbook_summary_mismatch'] += 1
            else:
                for workbook_type, workbook in process_workbooks.items():
                    type_summary = by_type.get(workbook_type)
                    if not isinstance(type_summary, dict):
                        counts['process_tax_workbook_summary_mismatch'] += 1
                        break
                    if (
                        type_summary.get('id') != workbook.id
                        or type_summary.get('hash_workbook') != workbook.hash_workbook
                        or int(type_summary.get('lines_total') or 0) != active_line_counts[workbook.id]
                    ):
                        counts['process_tax_workbook_summary_mismatch'] += 1
                        break

        for workbook in process_workbooks.values():
            if active_line_counts[workbook.id] == 0:
                counts['tax_workbook_line_missing'] += 1
            if warning_line_counts[workbook.id]:
                counts['tax_workbook_line_warning_review_required'] += warning_line_counts[workbook.id]

    return dict(sorted(counts.items()))


def _collect_annual_enterprise_register_issues(registers, movements, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    expected_types = {
        TipoAnnualEnterpriseRegister.RAI,
        TipoAnnualEnterpriseRegister.SAC,
        TipoAnnualEnterpriseRegister.RETIROS,
        TipoAnnualEnterpriseRegister.DIVIDENDOS,
    }
    invalid_registers = _count_invalid(registers)
    if invalid_registers:
        counts['enterprise_register_invalid'] = invalid_registers
    invalid_movements = _count_invalid(movements)
    if invalid_movements:
        counts['enterprise_register_movement_invalid'] = invalid_movements
    without_fiscal_config = _count_without_active_fiscal_config(registers, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['enterprise_register_fiscal_config_missing'] = without_fiscal_config

    prepared_registers = registers.filter(estado=EstadoAnnualEnterpriseRegister.PREPARED)
    registers_by_process = {}
    for register in prepared_registers:
        registers_by_process.setdefault(register.proceso_renta_anual_id, {})[register.tipo_registro] = register

    active_movement_counts = Counter()
    warning_movement_counts = Counter()
    for movement in movements.filter(estado=EstadoRegistro.ACTIVE).select_related('register_set'):
        active_movement_counts[movement.register_set_id] += 1
        warnings = movement.warnings if isinstance(movement.warnings, list) else []
        if warnings:
            warning_movement_counts[movement.register_set_id] += 1

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        process_registers = registers_by_process.get(process.id, {})
        present_types = set(process_registers.keys())
        if not present_types:
            counts['process_enterprise_registers_missing'] += 1
        elif present_types != expected_types:
            counts['process_enterprise_register_types_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        register_summary = summary.get('annual_enterprise_registers')
        if not isinstance(register_summary, dict):
            counts['process_enterprise_register_summary_missing'] += 1
        else:
            by_type = register_summary.get('by_type') if isinstance(register_summary.get('by_type'), dict) else {}
            try:
                summary_total = int(register_summary.get('total') or 0)
            except (TypeError, ValueError):
                summary_total = -1
            summary_types = set(register_summary.get('types') or [])
            if summary_total != len(process_registers) or summary_types != present_types:
                counts['process_enterprise_register_summary_mismatch'] += 1
            else:
                for register_type, register in process_registers.items():
                    type_summary = by_type.get(register_type)
                    if not isinstance(type_summary, dict):
                        counts['process_enterprise_register_summary_mismatch'] += 1
                        break
                    if (
                        type_summary.get('id') != register.id
                        or type_summary.get('hash_registro') != register.hash_registro
                        or str(type_summary.get('saldo_inicial_clp')) != str(register.saldo_inicial_clp)
                        or str(type_summary.get('movimientos_total_clp')) != str(register.movimientos_total_clp)
                        or str(type_summary.get('saldo_final_clp')) != str(register.saldo_final_clp)
                        or int(type_summary.get('movements_total') or 0) != active_movement_counts[register.id]
                    ):
                        counts['process_enterprise_register_summary_mismatch'] += 1
                        break

        for register in process_registers.values():
            if active_movement_counts[register.id] == 0:
                counts['enterprise_register_movement_missing'] += 1
            if warning_movement_counts[register.id]:
                counts['enterprise_register_movement_warning_review_required'] += warning_movement_counts[register.id]

    return dict(sorted(counts.items()))


def _collect_annual_real_estate_issues(sections, items, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    invalid_sections = _count_invalid(sections)
    if invalid_sections:
        counts['real_estate_section_invalid'] = invalid_sections
    invalid_items = _count_invalid(items)
    if invalid_items:
        counts['real_estate_item_invalid'] = invalid_items
    without_fiscal_config = _count_without_active_fiscal_config(sections, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['real_estate_section_fiscal_config_missing'] = without_fiscal_config

    prepared_sections = sections.filter(estado=EstadoAnnualRealEstateSection.PREPARED)
    sections_by_process = {}
    for section in prepared_sections:
        sections_by_process.setdefault(section.proceso_renta_anual_id, []).append(section)

    active_item_counts = Counter()
    warning_item_counts = Counter()
    for item in items.filter(estado=EstadoRegistro.ACTIVE).select_related('section'):
        active_item_counts[item.section_id] += 1
        warnings = item.warnings if isinstance(item.warnings, list) else []
        if warnings:
            warning_item_counts[item.section_id] += 1

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        process_sections = sections_by_process.get(process.id, [])
        if not process_sections:
            counts['process_real_estate_section_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        section_summary = summary.get('annual_real_estate_sections')
        if not isinstance(section_summary, dict):
            counts['process_real_estate_section_summary_missing'] += 1
        else:
            by_id = section_summary.get('by_id') if isinstance(section_summary.get('by_id'), dict) else {}
            try:
                summary_total = int(section_summary.get('total') or 0)
            except (TypeError, ValueError):
                summary_total = -1
            summary_ids = set(str(value) for value in (section_summary.get('ids') or []))
            section_ids = set(str(section.id) for section in process_sections)
            if summary_total != len(process_sections) or summary_ids != section_ids:
                counts['process_real_estate_section_summary_mismatch'] += 1
            else:
                for section in process_sections:
                    type_summary = by_id.get(str(section.id))
                    if not isinstance(type_summary, dict):
                        counts['process_real_estate_section_summary_mismatch'] += 1
                        break
                    if (
                        type_summary.get('id') != section.id
                        or type_summary.get('hash_seccion') != section.hash_seccion
                        or int(type_summary.get('propiedades_total') or 0) != section.propiedades_total
                        or str(type_summary.get('arriendo_devengado_total_clp')) != str(section.arriendo_devengado_total_clp)
                        or str(type_summary.get('arriendo_conciliado_total_clp')) != str(section.arriendo_conciliado_total_clp)
                        or str(type_summary.get('arriendo_facturable_total_clp')) != str(section.arriendo_facturable_total_clp)
                        or str(type_summary.get('contribuciones_total_clp')) != str(section.contribuciones_total_clp)
                        or int(type_summary.get('items_total') or 0) != active_item_counts[section.id]
                    ):
                        counts['process_real_estate_section_summary_mismatch'] += 1
                        break

        for section in process_sections:
            if active_item_counts[section.id] == 0:
                counts['real_estate_item_missing'] += 1
            if warning_item_counts[section.id]:
                counts['real_estate_item_warning_review_required'] += warning_item_counts[section.id]

    return dict(sorted(counts.items()))


def _collect_annual_artifact_matrix_issues(matrices, items, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    invalid_matrices = _count_invalid(matrices)
    if invalid_matrices:
        counts['artifact_matrix_invalid'] = invalid_matrices
    invalid_items = _count_invalid(items)
    if invalid_items:
        counts['artifact_matrix_item_invalid'] = invalid_items
    without_fiscal_config = _count_without_active_fiscal_config(matrices, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['artifact_matrix_fiscal_config_missing'] = without_fiscal_config

    prepared_matrices = matrices.filter(estado=EstadoAnnualTaxArtifactMatrix.PREPARED)
    matrices_by_process = {}
    for matrix in prepared_matrices:
        matrices_by_process.setdefault(matrix.proceso_renta_anual_id, []).append(matrix)

    active_item_counts = Counter()
    ddjj_item_counts = Counter()
    f22_item_counts = Counter()
    warning_item_counts = Counter()
    blocked_item_counts = Counter()
    for item in items.filter(estado=EstadoRegistro.ACTIVE).select_related('matrix'):
        active_item_counts[item.matrix_id] += 1
        if item.target_kind == 'DDJJ':
            ddjj_item_counts[item.matrix_id] += 1
        if item.target_kind == 'F22':
            f22_item_counts[item.matrix_id] += 1
        warnings = item.warnings if isinstance(item.warnings, list) else []
        if warnings or item.review_state == EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW:
            warning_item_counts[item.matrix_id] += 1
        if item.review_state == EstadoAnnualTaxArtifactReview.BLOCKED:
            blocked_item_counts[item.matrix_id] += 1

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        process_matrices = matrices_by_process.get(process.id, [])
        if not process_matrices:
            counts['process_artifact_matrix_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        matrix_summary = summary.get('annual_tax_artifact_matrices')
        if not isinstance(matrix_summary, dict):
            counts['process_artifact_matrix_summary_missing'] += 1
        else:
            by_id = matrix_summary.get('by_id') if isinstance(matrix_summary.get('by_id'), dict) else {}
            try:
                summary_total = int(matrix_summary.get('total') or 0)
            except (TypeError, ValueError):
                summary_total = -1
            summary_ids = set(str(value) for value in (matrix_summary.get('ids') or []))
            matrix_ids = set(str(matrix.id) for matrix in process_matrices)
            if summary_total != len(process_matrices) or summary_ids != matrix_ids:
                counts['process_artifact_matrix_summary_mismatch'] += 1
            else:
                for matrix in process_matrices:
                    item_summary = by_id.get(str(matrix.id))
                    if not isinstance(item_summary, dict):
                        counts['process_artifact_matrix_summary_mismatch'] += 1
                        break
                    if (
                        item_summary.get('id') != matrix.id
                        or item_summary.get('hash_matriz') != matrix.hash_matriz
                        or int(item_summary.get('items_total') or 0) != matrix.items_total
                        or int(item_summary.get('ddjj_items_total') or 0) != matrix.ddjj_items_total
                        or int(item_summary.get('f22_items_total') or 0) != matrix.f22_items_total
                        or int(item_summary.get('active_items_total') or 0) != active_item_counts[matrix.id]
                    ):
                        counts['process_artifact_matrix_summary_mismatch'] += 1
                        break

        for matrix in process_matrices:
            if active_item_counts[matrix.id] == 0:
                counts['artifact_matrix_item_missing'] += 1
            if f22_item_counts[matrix.id] == 0:
                counts['artifact_matrix_f22_item_missing'] += 1
            if ddjj_item_counts[matrix.id] == 0:
                counts['artifact_matrix_ddjj_item_missing'] += 1
            if warning_item_counts[matrix.id]:
                counts['artifact_matrix_item_warning_review_required'] += warning_item_counts[matrix.id]
            if blocked_item_counts[matrix.id]:
                counts['artifact_matrix_item_blocked'] += blocked_item_counts[matrix.id]

    return dict(sorted(counts.items()))


def _collect_annual_tax_dossier_issues(dossiers, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    invalid_dossiers = _count_invalid(dossiers)
    if invalid_dossiers:
        counts['tax_dossier_invalid'] = invalid_dossiers
    without_fiscal_config = _count_without_active_fiscal_config(dossiers, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['tax_dossier_fiscal_config_missing'] = without_fiscal_config

    prepared_dossiers = dossiers.filter(estado=EstadoAnnualTaxDossier.PREPARED)
    dossiers_by_process = {}
    for dossier in prepared_dossiers:
        dossiers_by_process.setdefault(dossier.proceso_renta_anual_id, []).append(dossier)

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        process_dossiers = dossiers_by_process.get(process.id, [])
        if not process_dossiers:
            counts['process_tax_dossier_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        dossier_summary = summary.get('annual_tax_dossiers')
        if not isinstance(dossier_summary, dict):
            counts['process_tax_dossier_summary_missing'] += 1
        else:
            by_id = dossier_summary.get('by_id') if isinstance(dossier_summary.get('by_id'), dict) else {}
            try:
                summary_total = int(dossier_summary.get('total') or 0)
            except (TypeError, ValueError):
                summary_total = -1
            summary_ids = set(str(value) for value in (dossier_summary.get('ids') or []))
            dossier_ids = set(str(dossier.id) for dossier in process_dossiers)
            if summary_total != len(process_dossiers) or summary_ids != dossier_ids:
                counts['process_tax_dossier_summary_mismatch'] += 1
            else:
                for dossier in process_dossiers:
                    item_summary = by_id.get(str(dossier.id))
                    if not isinstance(item_summary, dict):
                        counts['process_tax_dossier_summary_mismatch'] += 1
                        break
                    resumen = dossier.resumen_dossier if isinstance(dossier.resumen_dossier, dict) else {}
                    if (
                        item_summary.get('id') != dossier.id
                        or item_summary.get('hash_dossier') != dossier.hash_dossier
                        or item_summary.get('artifact_matrix_id') != dossier.artifact_matrix_id
                        or item_summary.get('artifact_matrix_hash') != resumen.get('artifact_matrix_hash')
                        or item_summary.get('review_state') != dossier.review_state
                        or int(item_summary.get('monthly_facts_total') or 0) != dossier.monthly_facts_total
                        or int(item_summary.get('workbooks_total') or 0) != dossier.workbooks_total
                        or int(item_summary.get('enterprise_registers_total') or 0) != dossier.enterprise_registers_total
                        or int(item_summary.get('real_estate_sections_total') or 0) != dossier.real_estate_sections_total
                        or int(item_summary.get('artifact_matrix_items_total') or 0) != dossier.artifact_matrix_items_total
                        or int(item_summary.get('warnings_total') or 0) != dossier.warnings_total
                    ):
                        counts['process_tax_dossier_summary_mismatch'] += 1
                        break

        for dossier in process_dossiers:
            if not has_text(dossier.responsible_ref):
                counts['tax_dossier_responsible_missing'] += 1
            if not has_text(dossier.dossier_ref):
                counts['tax_dossier_ref_missing'] += 1
            if dossier.review_state == EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW:
                counts['tax_dossier_review_required'] += 1
            if dossier.review_state == EstadoAnnualTaxArtifactReview.BLOCKED:
                counts['tax_dossier_blocked'] += 1

    return dict(sorted(counts.items()))


def _collect_annual_tax_export_issues(exports, processes, active_fiscal_company_ids: set[int]) -> dict[str, int]:
    counts = Counter()
    invalid_exports = _count_invalid(exports)
    if invalid_exports:
        counts['tax_export_invalid'] = invalid_exports
    without_fiscal_config = _count_without_active_fiscal_config(exports, active_fiscal_company_ids)
    if without_fiscal_config:
        counts['tax_export_fiscal_config_missing'] = without_fiscal_config

    prepared_exports = exports.filter(estado=EstadoAnnualTaxExport.PREPARED)
    exports_by_process = {}
    for export in prepared_exports:
        exports_by_process.setdefault(export.proceso_renta_anual_id, []).append(export)

    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        process_exports = exports_by_process.get(process.id, [])
        if not process_exports:
            counts['process_tax_export_missing'] += 1

        summary = process.resumen_anual if isinstance(process.resumen_anual, dict) else {}
        export_summary = summary.get('annual_tax_exports')
        if not isinstance(export_summary, dict):
            counts['process_tax_export_summary_missing'] += 1
        else:
            by_id = export_summary.get('by_id') if isinstance(export_summary.get('by_id'), dict) else {}
            try:
                summary_total = int(export_summary.get('total') or 0)
            except (TypeError, ValueError):
                summary_total = -1
            summary_ids = set(str(value) for value in (export_summary.get('ids') or []))
            export_ids = set(str(export.id) for export in process_exports)
            if summary_total != len(process_exports) or summary_ids != export_ids:
                counts['process_tax_export_summary_mismatch'] += 1
            else:
                for export in process_exports:
                    item_summary = by_id.get(str(export.id))
                    if not isinstance(item_summary, dict):
                        counts['process_tax_export_summary_mismatch'] += 1
                        break
                    payload = export.export_payload if isinstance(export.export_payload, dict) else {}
                    if (
                        item_summary.get('id') != export.id
                        or item_summary.get('hash_export') != export.hash_export
                        or item_summary.get('export_kind') != export.export_kind
                        or item_summary.get('dossier_id') != export.dossier_id
                        or item_summary.get('dossier_hash') != payload.get('dossier_hash')
                        or item_summary.get('source_bundle_id') != export.source_bundle_id
                        or item_summary.get('rule_set_id') != export.rule_set_id
                        or item_summary.get('artifact_matrix_id') != export.artifact_matrix_id
                        or item_summary.get('review_state') != export.review_state
                        or int(item_summary.get('target_items_total') or 0) != export.target_items_total
                        or int(item_summary.get('ddjj_items_total') or 0) != export.ddjj_items_total
                        or int(item_summary.get('f22_items_total') or 0) != export.f22_items_total
                        or int(item_summary.get('warnings_total') or 0) != export.warnings_total
                        or item_summary.get('official_format') is not False
                        or item_summary.get('sii_submission') is not False
                        or item_summary.get('final_tax_calculation') is not False
                    ):
                        counts['process_tax_export_summary_mismatch'] += 1
                        break

        for export in process_exports:
            payload = export.export_payload if isinstance(export.export_payload, dict) else {}
            if not has_text(export.responsible_ref):
                counts['tax_export_responsible_missing'] += 1
            if not has_text(export.export_ref):
                counts['tax_export_ref_missing'] += 1
            if export.review_state == EstadoAnnualTaxArtifactReview.REQUIRES_REVIEW:
                counts['tax_export_review_required'] += 1
            if export.review_state == EstadoAnnualTaxArtifactReview.BLOCKED:
                counts['tax_export_blocked'] += 1
            if export.official_format or payload.get('official_format') not in (False, None):
                counts['tax_export_official_format_boundary'] += 1
            if export.sii_submission or payload.get('sii_submission') not in (False, None) or bool(payload.get('sii_submission_attempted')):
                counts['tax_export_sii_submission_boundary'] += 1
            if export.final_tax_calculation or payload.get('final_tax_calculation') not in (False, None):
                counts['tax_export_final_calculation_boundary'] += 1

    return dict(sorted(counts.items()))


def _collect_tax_year_rule_issues(processes, active_fiscal_configs) -> dict[str, int]:
    counts = Counter()
    fiscal_config_by_company_id = {
        config.empresa_id: config
        for config in active_fiscal_configs
    }
    for process in processes:
        if process.estado not in ANNUAL_TRACEABLE_STATES:
            continue
        fiscal_config = fiscal_config_by_company_id.get(process.empresa_id)
        if fiscal_config is None:
            continue
        approved_rule_sets = TaxYearRuleSet.objects.filter(
            anio_tributario=process.anio_tributario,
            regimen_tributario_id=fiscal_config.regimen_tributario_id,
            estado=EstadoReglaTributariaAnual.APPROVED,
        )
        if not approved_rule_sets.exists():
            counts['tax_year_ruleset_missing'] += 1
            continue
        for rule_set in approved_rule_sets:
            if not rule_set.code_mappings.filter(estado=EstadoRegistro.ACTIVE).exists():
                counts['tax_code_mapping_missing'] += 1

    invalid_rule_sets = _count_invalid(TaxYearRuleSet.objects.all())
    if invalid_rule_sets:
        counts['tax_year_ruleset_invalid'] = invalid_rule_sets
    invalid_mappings = _count_invalid(TaxCodeMapping.objects.select_related('rule_set'))
    if invalid_mappings:
        counts['tax_code_mapping_invalid'] = invalid_mappings
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
        if _sensitive_reference(ddjj.responsable_revision_ref):
            counts['ddjj_responsible_ref_sensitive'] += 1
        if ddjj.estado_preparacion in ANNUAL_REF_REQUIRED_STATES:
            if not has_text(ddjj.paquete_ref):
                counts['ddjj_ref_missing'] += 1
            if not has_text(ddjj.responsable_revision_ref):
                counts['ddjj_responsible_ref_missing'] += 1

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
        if _sensitive_reference(f22.responsable_revision_ref):
            counts['f22_responsible_ref_sensitive'] += 1
        if f22.estado_preparacion in ANNUAL_REF_REQUIRED_STATES:
            if not has_text(f22.borrador_ref):
                counts['f22_ref_missing'] += 1
            if not has_text(f22.responsable_revision_ref):
                counts['f22_responsible_ref_missing'] += 1

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

    annual_processes = ProcesoRentaAnual.objects.select_related('empresa', 'source_bundle')
    process_issues = _collect_process_issues(annual_processes)
    tax_year_rule_issues = _collect_tax_year_rule_issues(annual_processes, active_fiscal_configs)
    source_bundles = AnnualTaxSourceBundle.objects.select_related('empresa')
    source_bundle_issues = _collect_source_bundle_issues(source_bundles, active_fiscal_company_ids)
    official_sources = AnnualTaxOfficialSource.objects.all()
    official_source_issues = _collect_official_source_issues(official_sources)
    monthly_tax_facts = MonthlyTaxFact.objects.select_related(
        'empresa',
        'cierre_mensual',
        'f29_preparacion',
        'liquidacion_mensual',
    )
    monthly_tax_fact_issues = _collect_monthly_tax_fact_issues(
        monthly_tax_facts,
        annual_processes,
        active_fiscal_company_ids,
    )
    annual_tax_workbooks = AnnualTaxWorkbook.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    )
    annual_tax_workbook_lines = AnnualTaxWorkbookLine.objects.select_related(
        'workbook',
        'workbook__empresa',
        'mapping',
    )
    annual_tax_workbook_issues = _collect_annual_tax_workbook_issues(
        annual_tax_workbooks,
        annual_tax_workbook_lines,
        annual_processes,
        active_fiscal_company_ids,
    )
    annual_enterprise_registers = AnnualEnterpriseRegisterSet.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    )
    annual_enterprise_register_movements = AnnualEnterpriseRegisterMovement.objects.select_related(
        'register_set',
        'register_set__empresa',
        'source_workbook_line',
    )
    annual_enterprise_register_issues = _collect_annual_enterprise_register_issues(
        annual_enterprise_registers,
        annual_enterprise_register_movements,
        annual_processes,
        active_fiscal_company_ids,
    )
    annual_real_estate_sections = AnnualRealEstateSection.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    )
    annual_real_estate_items = AnnualRealEstateItem.objects.select_related(
        'section',
        'section__empresa',
        'propiedad',
    )
    annual_real_estate_issues = _collect_annual_real_estate_issues(
        annual_real_estate_sections,
        annual_real_estate_items,
        annual_processes,
        active_fiscal_company_ids,
    )
    annual_tax_artifact_matrices = AnnualTaxArtifactMatrix.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
    )
    annual_tax_artifact_matrix_items = AnnualTaxArtifactMatrixItem.objects.select_related(
        'matrix',
        'matrix__empresa',
    )
    annual_artifact_matrix_issues = _collect_annual_artifact_matrix_issues(
        annual_tax_artifact_matrices,
        annual_tax_artifact_matrix_items,
        annual_processes,
        active_fiscal_company_ids,
    )
    annual_tax_dossiers = AnnualTaxDossier.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
    )
    annual_tax_dossier_issues = _collect_annual_tax_dossier_issues(
        annual_tax_dossiers,
        annual_processes,
        active_fiscal_company_ids,
    )
    annual_tax_exports = AnnualTaxExport.objects.select_related(
        'empresa',
        'proceso_renta_anual',
        'source_bundle',
        'rule_set',
        'artifact_matrix',
        'dossier',
    )
    annual_tax_export_issues = _collect_annual_tax_export_issues(
        annual_tax_exports,
        annual_processes,
        active_fiscal_company_ids,
    )

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
    annual_status_review_responsible_issues = _count_annual_status_review_responsible_issues()

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
    if annual_status_review_responsible_issues.get('missing'):
        issues.append(
            _issue(
                'stage6.audit.annual_status_responsible_ref_missing',
                'Existen eventos status_updated de DDJJ/F22 avanzados sin responsable_revision_ref auditado.',
                count=annual_status_review_responsible_issues['missing'],
            )
        )
    if annual_status_review_responsible_issues.get('sensitive'):
        issues.append(
            _issue(
                'stage6.audit.annual_status_responsible_ref_sensitive',
                'Existen eventos status_updated de DDJJ/F22 avanzados con responsable_revision_ref sensible.',
                count=annual_status_review_responsible_issues['sensitive'],
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
    if source_bundles.count() == 0:
        issues.append(
            _issue(
                'stage6.source_bundle_missing',
                'Etapa 6 requiere AnnualTaxSourceBundle congelado antes de preparar Renta anual.',
            )
        )
    if monthly_tax_facts.filter(estado=EstadoMonthlyTaxFact.NORMALIZED).count() == 0:
        issues.append(
            _issue(
                'stage6.monthly_tax_fact_missing',
                'Etapa 6 requiere hechos tributarios mensuales normalizados antes de preparar Renta anual.',
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
    for key, code, message in [
        (
            'source_bundle_invalid',
            'stage6.source_bundle_invalid',
            'Existen AnnualTaxSourceBundle que no pasan validacion de dominio o contienen trazas no permitidas.',
        ),
        (
            'source_bundle_fiscal_config_missing',
            'stage6.source_bundle_fiscal_config_missing',
            'Existen AnnualTaxSourceBundle para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
    ]:
        if source_bundle_issues.get(key):
            issues.append(_issue(code, message, count=source_bundle_issues[key]))
    for key, code, message in [
        (
            'official_source_invalid',
            'stage6.official_source_invalid',
            'Existen fuentes oficiales AT registradas que no pasan validacion de dominio o contienen trazas no permitidas.',
        ),
    ]:
        if official_source_issues.get(key):
            issues.append(_issue(code, message, count=official_source_issues[key]))
    for key, code, message in [
        (
            'monthly_tax_fact_invalid',
            'stage6.monthly_tax_fact_invalid',
            'Existen MonthlyTaxFact que no pasan validacion de dominio o contienen trazas no permitidas.',
        ),
        (
            'monthly_tax_fact_fiscal_config_missing',
            'stage6.monthly_tax_fact_fiscal_config_missing',
            'Existen MonthlyTaxFact para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_monthly_tax_facts_missing',
            'stage6.process_monthly_tax_facts_missing',
            'ProcesoRentaAnual trazable requiere hechos tributarios mensuales normalizados.',
        ),
        (
            'process_monthly_tax_fact_months_missing',
            'stage6.process_monthly_tax_fact_months_missing',
            'ProcesoRentaAnual trazable requiere MonthlyTaxFact normalizado para los doce meses.',
        ),
        (
            'process_monthly_tax_fact_summary_missing',
            'stage6.process_monthly_tax_fact_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de MonthlyTaxFact en resumen_anual.',
        ),
        (
            'process_monthly_tax_fact_summary_mismatch',
            'stage6.process_monthly_tax_fact_summary_mismatch',
            'ProcesoRentaAnual conserva resumen de MonthlyTaxFact desalineado con hechos mensuales vigentes.',
        ),
    ]:
        if monthly_tax_fact_issues.get(key):
            issues.append(_issue(code, message, count=monthly_tax_fact_issues[key]))
    for key, code, message in [
        (
            'tax_workbook_invalid',
            'stage6.tax_workbook_invalid',
            'Existen AnnualTaxWorkbook RLI/CPT que no pasan validacion de dominio.',
        ),
        (
            'tax_workbook_line_invalid',
            'stage6.tax_workbook_line_invalid',
            'Existen lineas RLI/CPT que no pasan validacion de dominio o referencias.',
        ),
        (
            'tax_workbook_fiscal_config_missing',
            'stage6.tax_workbook_fiscal_config_missing',
            'Existen AnnualTaxWorkbook para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_tax_workbooks_missing',
            'stage6.process_tax_workbooks_missing',
            'ProcesoRentaAnual trazable requiere workbooks RLI/CPT preparados.',
        ),
        (
            'process_tax_workbook_types_missing',
            'stage6.process_tax_workbook_types_missing',
            'ProcesoRentaAnual trazable requiere ambos workbooks RLI y CPT.',
        ),
        (
            'process_tax_workbook_summary_missing',
            'stage6.process_tax_workbook_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de workbooks RLI/CPT en resumen_anual.',
        ),
        (
            'process_tax_workbook_summary_mismatch',
            'stage6.process_tax_workbook_summary_mismatch',
            'ProcesoRentaAnual conserva resumen RLI/CPT desalineado con workbooks vigentes.',
        ),
        (
            'tax_workbook_line_missing',
            'stage6.tax_workbook_line_missing',
            'AnnualTaxWorkbook preparado requiere lineas activas trazadas.',
        ),
        (
            'tax_workbook_line_warning_review_required',
            'stage6.tax_workbook_line_warning_review_required',
            'Existen lineas RLI/CPT con warnings que requieren revision antes de cierre.',
        ),
    ]:
        if annual_tax_workbook_issues.get(key):
            issues.append(_issue(code, message, count=annual_tax_workbook_issues[key]))
    for key, code, message in [
        (
            'enterprise_register_invalid',
            'stage6.enterprise_register_invalid',
            'Existen registros empresariales RAI/SAC/retiros/dividendos que no pasan validacion de dominio.',
        ),
        (
            'enterprise_register_movement_invalid',
            'stage6.enterprise_register_movement_invalid',
            'Existen movimientos de registros empresariales que no pasan validacion de dominio o referencias.',
        ),
        (
            'enterprise_register_fiscal_config_missing',
            'stage6.enterprise_register_fiscal_config_missing',
            'Existen registros empresariales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_enterprise_registers_missing',
            'stage6.process_enterprise_registers_missing',
            'ProcesoRentaAnual trazable requiere registros empresariales RAI/SAC/retiros/dividendos preparados.',
        ),
        (
            'process_enterprise_register_types_missing',
            'stage6.process_enterprise_register_types_missing',
            'ProcesoRentaAnual trazable requiere registros RAI, SAC, retiros y dividendos.',
        ),
        (
            'process_enterprise_register_summary_missing',
            'stage6.process_enterprise_register_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de registros empresariales en resumen_anual.',
        ),
        (
            'process_enterprise_register_summary_mismatch',
            'stage6.process_enterprise_register_summary_mismatch',
            'ProcesoRentaAnual conserva resumen de registros empresariales desalineado con registros vigentes.',
        ),
        (
            'enterprise_register_movement_missing',
            'stage6.enterprise_register_movement_missing',
            'Registro empresarial preparado requiere movimientos activos trazados.',
        ),
        (
            'enterprise_register_movement_warning_review_required',
            'stage6.enterprise_register_movement_warning_review_required',
            'Existen movimientos de registros empresariales con warnings que requieren revision antes de cierre.',
        ),
    ]:
        if annual_enterprise_register_issues.get(key):
            issues.append(_issue(code, message, count=annual_enterprise_register_issues[key]))
    for key, code, message in [
        (
            'real_estate_section_invalid',
            'stage6.real_estate_section_invalid',
            'Existen secciones anuales de bienes raices que no pasan validacion de dominio.',
        ),
        (
            'real_estate_item_invalid',
            'stage6.real_estate_item_invalid',
            'Existen items anuales de bienes raices/arriendos que no pasan validacion de dominio o referencias.',
        ),
        (
            'real_estate_section_fiscal_config_missing',
            'stage6.real_estate_section_fiscal_config_missing',
            'Existen secciones de bienes raices para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_real_estate_section_missing',
            'stage6.process_real_estate_section_missing',
            'ProcesoRentaAnual trazable requiere seccion anual de bienes raices/arriendos preparada.',
        ),
        (
            'process_real_estate_section_summary_missing',
            'stage6.process_real_estate_section_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de bienes raices/arriendos en resumen_anual.',
        ),
        (
            'process_real_estate_section_summary_mismatch',
            'stage6.process_real_estate_section_summary_mismatch',
            'ProcesoRentaAnual conserva resumen de bienes raices/arriendos desalineado con la seccion vigente.',
        ),
        (
            'real_estate_item_missing',
            'stage6.real_estate_item_missing',
            'AnnualRealEstateSection preparada requiere items activos por propiedad trazada.',
        ),
        (
            'real_estate_item_warning_review_required',
            'stage6.real_estate_item_warning_review_required',
            'Existen items de bienes raices/arriendos con warnings que requieren revision antes de cierre.',
        ),
    ]:
        if annual_real_estate_issues.get(key):
            issues.append(_issue(code, message, count=annual_real_estate_issues[key]))
    for key, code, message in [
        (
            'artifact_matrix_invalid',
            'stage6.artifact_matrix_invalid',
            'Existen matrices DDJJ/F22 que no pasan validacion de dominio.',
        ),
        (
            'artifact_matrix_item_invalid',
            'stage6.artifact_matrix_item_invalid',
            'Existen items de matriz DDJJ/F22 que no pasan validacion de dominio o referencias.',
        ),
        (
            'artifact_matrix_fiscal_config_missing',
            'stage6.artifact_matrix_fiscal_config_missing',
            'Existen matrices DDJJ/F22 para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_artifact_matrix_missing',
            'stage6.process_artifact_matrix_missing',
            'ProcesoRentaAnual trazable requiere matriz DDJJ/F22 preparada.',
        ),
        (
            'process_artifact_matrix_summary_missing',
            'stage6.process_artifact_matrix_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de matriz DDJJ/F22 en resumen_anual.',
        ),
        (
            'process_artifact_matrix_summary_mismatch',
            'stage6.process_artifact_matrix_summary_mismatch',
            'ProcesoRentaAnual conserva resumen de matriz DDJJ/F22 desalineado con la matriz vigente.',
        ),
        (
            'artifact_matrix_item_missing',
            'stage6.artifact_matrix_item_missing',
            'AnnualTaxArtifactMatrix preparada requiere items activos.',
        ),
        (
            'artifact_matrix_f22_item_missing',
            'stage6.artifact_matrix_f22_item_missing',
            'AnnualTaxArtifactMatrix preparada requiere al menos un item F22.',
        ),
        (
            'artifact_matrix_ddjj_item_missing',
            'stage6.artifact_matrix_ddjj_item_missing',
            'AnnualTaxArtifactMatrix preparada requiere al menos un item DDJJ.',
        ),
        (
            'artifact_matrix_item_warning_review_required',
            'stage6.artifact_matrix_item_warning_review_required',
            'Existen items de matriz DDJJ/F22 con warnings o revision pendiente antes de cierre.',
        ),
        (
            'artifact_matrix_item_blocked',
            'stage6.artifact_matrix_item_blocked',
            'Existen items de matriz DDJJ/F22 bloqueados.',
        ),
    ]:
        if annual_artifact_matrix_issues.get(key):
            issues.append(_issue(code, message, count=annual_artifact_matrix_issues[key]))
    for key, code, message in [
        (
            'tax_dossier_invalid',
            'stage6.tax_dossier_invalid',
            'Existen dossiers anuales que no pasan validacion de dominio o referencias.',
        ),
        (
            'tax_dossier_fiscal_config_missing',
            'stage6.tax_dossier_fiscal_config_missing',
            'Existen dossiers anuales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_tax_dossier_missing',
            'stage6.process_tax_dossier_missing',
            'ProcesoRentaAnual trazable requiere dossier anual revisable preparado.',
        ),
        (
            'process_tax_dossier_summary_missing',
            'stage6.process_tax_dossier_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de dossier anual en resumen_anual.',
        ),
        (
            'process_tax_dossier_summary_mismatch',
            'stage6.process_tax_dossier_summary_mismatch',
            'ProcesoRentaAnual conserva resumen de dossier anual desalineado con el dossier vigente.',
        ),
        (
            'tax_dossier_responsible_missing',
            'stage6.tax_dossier_responsible_missing',
            'AnnualTaxDossier preparado requiere responsable de revision trazable.',
        ),
        (
            'tax_dossier_ref_missing',
            'stage6.tax_dossier_ref_missing',
            'AnnualTaxDossier preparado requiere dossier_ref trazable.',
        ),
        (
            'tax_dossier_review_required',
            'stage6.tax_dossier_review_required',
            'AnnualTaxDossier conserva warnings o revision tributaria pendiente.',
        ),
        (
            'tax_dossier_blocked',
            'stage6.tax_dossier_blocked',
            'AnnualTaxDossier esta bloqueado por artefactos anuales pendientes.',
        ),
    ]:
        if annual_tax_dossier_issues.get(key):
            issues.append(_issue(code, message, count=annual_tax_dossier_issues[key]))
    for key, code, message in [
        (
            'tax_export_invalid',
            'stage6.tax_export_invalid',
            'Existen exports anuales que no pasan validacion de dominio o referencias.',
        ),
        (
            'tax_export_fiscal_config_missing',
            'stage6.tax_export_fiscal_config_missing',
            'Existen exports anuales para empresas sin ConfiguracionFiscalEmpresa activa propia.',
        ),
        (
            'process_tax_export_missing',
            'stage6.process_tax_export_missing',
            'ProcesoRentaAnual trazable requiere export/preview controlado preparado.',
        ),
        (
            'process_tax_export_summary_missing',
            'stage6.process_tax_export_summary_missing',
            'ProcesoRentaAnual debe conservar resumen de export anual en resumen_anual.',
        ),
        (
            'process_tax_export_summary_mismatch',
            'stage6.process_tax_export_summary_mismatch',
            'ProcesoRentaAnual conserva resumen de export anual desalineado con el export vigente.',
        ),
        (
            'tax_export_responsible_missing',
            'stage6.tax_export_responsible_missing',
            'AnnualTaxExport preparado requiere responsable de revision trazable.',
        ),
        (
            'tax_export_ref_missing',
            'stage6.tax_export_ref_missing',
            'AnnualTaxExport preparado requiere export_ref trazable.',
        ),
        (
            'tax_export_review_required',
            'stage6.tax_export_review_required',
            'AnnualTaxExport conserva revision tributaria pendiente.',
        ),
        (
            'tax_export_blocked',
            'stage6.tax_export_blocked',
            'AnnualTaxExport esta bloqueado por dossier o matriz anual pendiente.',
        ),
        (
            'tax_export_official_format_boundary',
            'stage6.tax_export_official_format_boundary',
            'AnnualTaxExport no puede declarar formato oficial SII sin gate/certificacion vigente.',
        ),
        (
            'tax_export_sii_submission_boundary',
            'stage6.tax_export_sii_submission_boundary',
            'AnnualTaxExport no puede registrar presentacion SII desde el flujo local.',
        ),
        (
            'tax_export_final_calculation_boundary',
            'stage6.tax_export_final_calculation_boundary',
            'AnnualTaxExport no puede declarar calculo fiscal final autonomo.',
        ),
    ]:
        if annual_tax_export_issues.get(key):
            issues.append(_issue(code, message, count=annual_tax_export_issues[key]))
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
            'tax_year_ruleset_missing',
            'stage6.tax_year_ruleset_missing',
            'Existen procesos anuales trazables sin TaxYearRuleSet aprobado para su ano tributario y regimen.',
        ),
        (
            'tax_code_mapping_missing',
            'stage6.tax_code_mapping_missing',
            'Existen TaxYearRuleSet aprobados sin mapeos activos trazables para RLI/CPT/DDJJ/F22.',
        ),
        (
            'tax_year_ruleset_invalid',
            'stage6.tax_year_ruleset_invalid',
            'Existen TaxYearRuleSet que no pasan validacion de dominio o referencias.',
        ),
        (
            'tax_code_mapping_invalid',
            'stage6.tax_code_mapping_invalid',
            'Existen TaxCodeMapping que no pasan validacion de dominio o referencias.',
        ),
    ]:
        if tax_year_rule_issues.get(key):
            issues.append(_issue(code, message, count=tax_year_rule_issues[key]))

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
            'process_source_bundle_missing',
            'stage6.process_source_bundle_missing',
            'ProcesoRentaAnual preparado requiere AnnualTaxSourceBundle congelado.',
        ),
        (
            'process_source_bundle_mismatch',
            'stage6.process_source_bundle_mismatch',
            'ProcesoRentaAnual apunta a AnnualTaxSourceBundle de otra empresa o ano tributario.',
        ),
        (
            'process_source_bundle_not_frozen',
            'stage6.process_source_bundle_not_frozen',
            'ProcesoRentaAnual apunta a AnnualTaxSourceBundle no congelado.',
        ),
        (
            'process_source_bundle_summary_missing',
            'stage6.process_source_bundle_summary_missing',
            'ProcesoRentaAnual debe conservar metadata del AnnualTaxSourceBundle en resumen_anual.',
        ),
        (
            'process_source_bundle_summary_mismatch',
            'stage6.process_source_bundle_summary_mismatch',
            'ProcesoRentaAnual conserva metadata de AnnualTaxSourceBundle desalineada con la fuente congelada.',
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
            'process_responsible_ref_sensitive',
            'stage6.process_responsible_ref_sensitive',
            'Proceso anual contiene responsable_revision_ref sensible.',
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
        (
            'process_responsible_ref_missing',
            'stage6.process_responsible_ref_missing',
            'Proceso anual aprobado/observado/rectificado requiere responsable_revision_ref.',
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
            'ddjj_responsible_ref_sensitive',
            'stage6.ddjj_responsible_ref_sensitive',
            'DDJJ contiene responsable_revision_ref sensible.',
        ),
        (
            'f22_responsible_ref_sensitive',
            'stage6.f22_responsible_ref_sensitive',
            'F22 contiene responsable_revision_ref sensible.',
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
        (
            'ddjj_responsible_ref_missing',
            'stage6.ddjj_responsible_ref_missing',
            'DDJJ aprobada, observada o rectificada requiere responsable_revision_ref.',
        ),
        (
            'f22_responsible_ref_missing',
            'stage6.f22_responsible_ref_missing',
            'F22 aprobado, observado o rectificado requiere responsable_revision_ref.',
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
            'annual_source_bundles': {
                'bundles_total': source_bundles.count(),
                'frozen_bundles': source_bundles.filter(estado=EstadoAnnualTaxSourceBundle.FROZEN).count(),
                'bundles_by_state': _count_by(source_bundles, 'estado'),
                'bundles_by_source_kind': _count_by(source_bundles, 'source_kind'),
                **source_bundle_issues,
            },
            'annual_tax_official_sources': {
                'sources_total': official_sources.count(),
                'approved_sources': official_sources.filter(estado=EstadoAnnualTaxOfficialSource.APPROVED).count(),
                'reviewed_sources': official_sources.filter(estado=EstadoAnnualTaxOfficialSource.REVIEWED).count(),
                'sources_by_state': _count_by(official_sources, 'estado'),
                'sources_by_type': _count_by(official_sources, 'source_type'),
                'sources_by_target': _count_by(official_sources, 'applies_to'),
                **official_source_issues,
            },
            'monthly_tax_facts': {
                'facts_total': monthly_tax_facts.count(),
                'normalized_facts': monthly_tax_facts.filter(estado=EstadoMonthlyTaxFact.NORMALIZED).count(),
                'facts_by_state': _count_by(monthly_tax_facts, 'estado'),
                'facts_by_year': _count_by(monthly_tax_facts, 'anio'),
                **monthly_tax_fact_issues,
            },
            'annual_tax_workbooks': {
                'workbooks_total': annual_tax_workbooks.count(),
                'prepared_workbooks': annual_tax_workbooks.filter(estado=EstadoAnnualTaxWorkbook.PREPARED).count(),
                'workbooks_by_state': _count_by(annual_tax_workbooks, 'estado'),
                'workbooks_by_type': _count_by(annual_tax_workbooks, 'tipo'),
                'lines_total': annual_tax_workbook_lines.count(),
                'active_lines': annual_tax_workbook_lines.filter(estado=EstadoRegistro.ACTIVE).count(),
                **annual_tax_workbook_issues,
            },
            'annual_enterprise_registers': {
                'registers_total': annual_enterprise_registers.count(),
                'prepared_registers': annual_enterprise_registers.filter(estado=EstadoAnnualEnterpriseRegister.PREPARED).count(),
                'registers_by_state': _count_by(annual_enterprise_registers, 'estado'),
                'registers_by_type': _count_by(annual_enterprise_registers, 'tipo_registro'),
                'movements_total': annual_enterprise_register_movements.count(),
                'active_movements': annual_enterprise_register_movements.filter(estado=EstadoRegistro.ACTIVE).count(),
                **annual_enterprise_register_issues,
            },
            'annual_real_estate_sections': {
                'sections_total': annual_real_estate_sections.count(),
                'prepared_sections': annual_real_estate_sections.filter(estado=EstadoAnnualRealEstateSection.PREPARED).count(),
                'sections_by_state': _count_by(annual_real_estate_sections, 'estado'),
                'items_total': annual_real_estate_items.count(),
                'active_items': annual_real_estate_items.filter(estado=EstadoRegistro.ACTIVE).count(),
                **annual_real_estate_issues,
            },
            'annual_tax_artifact_matrices': {
                'matrices_total': annual_tax_artifact_matrices.count(),
                'prepared_matrices': annual_tax_artifact_matrices.filter(estado=EstadoAnnualTaxArtifactMatrix.PREPARED).count(),
                'matrices_by_state': _count_by(annual_tax_artifact_matrices, 'estado'),
                'items_total': annual_tax_artifact_matrix_items.count(),
                'active_items': annual_tax_artifact_matrix_items.filter(estado=EstadoRegistro.ACTIVE).count(),
                'items_by_target': _count_by(annual_tax_artifact_matrix_items, 'target_kind'),
                'items_by_review_state': _count_by(annual_tax_artifact_matrix_items, 'review_state'),
                **annual_artifact_matrix_issues,
            },
            'annual_tax_dossiers': {
                'dossiers_total': annual_tax_dossiers.count(),
                'prepared_dossiers': annual_tax_dossiers.filter(estado=EstadoAnnualTaxDossier.PREPARED).count(),
                'dossiers_by_state': _count_by(annual_tax_dossiers, 'estado'),
                'dossiers_by_review_state': _count_by(annual_tax_dossiers, 'review_state'),
                **annual_tax_dossier_issues,
            },
            'annual_tax_exports': {
                'exports_total': annual_tax_exports.count(),
                'prepared_exports': annual_tax_exports.filter(estado=EstadoAnnualTaxExport.PREPARED).count(),
                'exports_by_state': _count_by(annual_tax_exports, 'estado'),
                'exports_by_kind': _count_by(annual_tax_exports, 'export_kind'),
                'exports_by_review_state': _count_by(annual_tax_exports, 'review_state'),
                **annual_tax_export_issues,
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
            'tax_year_rules': {
                'rule_sets_total': TaxYearRuleSet.objects.count(),
                'approved_rule_sets': TaxYearRuleSet.objects.filter(estado=EstadoReglaTributariaAnual.APPROVED).count(),
                'code_mappings_total': TaxCodeMapping.objects.count(),
                'active_code_mappings': TaxCodeMapping.objects.filter(estado=EstadoRegistro.ACTIVE).count(),
                'rule_sets_by_state': _count_by(TaxYearRuleSet.objects.all(), 'estado'),
                'code_mappings_by_target': _count_by(TaxCodeMapping.objects.all(), 'destino'),
                **tax_year_rule_issues,
            },
            'audit': {
                'annual_status_transition_metadata_missing': annual_status_transition_metadata_missing,
                'annual_status_responsible_ref_missing': annual_status_review_responsible_issues.get('missing', 0),
                'annual_status_responsible_ref_sensitive': annual_status_review_responsible_issues.get('sensitive', 0),
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
