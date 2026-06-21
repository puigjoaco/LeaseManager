from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import re
from typing import Any

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
    EstadoRegistro,
)
from core.annual_tax_source_manifest import payload_hash
from core.reference_validation import contains_sensitive_reference, is_non_sensitive_reference
from patrimonio.models import Empresa
from sii.models import (
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxTrialBalance,
    AnnualTaxTrialBalanceLine,
    AnnualTaxWorkbook,
    AnnualTaxWorkbookLine,
    EstadoAnnualTaxArtifactReview,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxSourceBundle,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    F29PreparacionMensual,
    MonthlyTaxFact,
    ProcesoRentaAnual,
    SII_AUTOMATED_REGIME_CODE,
    TipoAnnualTaxArtifactTarget,
    TipoAnnualTaxWorkbook,
)


MONTHS = tuple(range(1, 13))
SHA256_PATTERN = re.compile(r'^[0-9a-f]{64}$')
PREPARED_OR_BETTER_TAX_STATES = {
    EstadoPreparacionTributaria.PREPARED,
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
}
COMPANY_ACCOUNTING_REVIEW_BOUNDARY = {
    'meaning_when_ready': 'paquete_local_preparado_para_revision_responsable',
    'autonomous_accounting': False,
    'final_tax_calculation': False,
    'sii_submission': False,
    'requires_responsible_review': True,
    'requires_expert_or_official_validation': True,
    'allowed_next_action': 'revision_asistida_por_responsable',
    'not_allowed_actions': [
        'contabilidad_autonoma',
        'calculo_tributario_final_sin_revision',
        'presentacion_sii_automatica',
    ],
}
COMPANY_ACCOUNTING_SELECTION_BOUNDARY = {
    'purpose': 'seleccionar_empresa_y_ano_para_revision_asistida',
    'uses_external_sources': False,
    'opens_external_gates': False,
    'autonomous_accounting': False,
    'final_tax_calculation': False,
    'sii_submission': False,
}


@dataclass(frozen=True)
class ProgressPhase:
    key: str
    label: str
    expected: int
    completed: int
    missing: list[Any]
    blocking_issue_code: str
    message: str

    @property
    def ready(self) -> bool:
        return self.completed >= self.expected and not self.missing

    @property
    def status(self) -> str:
        if self.ready:
            return 'listo'
        if self.completed <= 0:
            return 'pendiente'
        return 'parcial'

    def as_dict(self) -> dict[str, Any]:
        return {
            'label': self.label,
            'status': self.status,
            'ready': self.ready,
            'expected': self.expected,
            'completed': self.completed,
            'missing': self.missing,
        }


def _period(year: int, month: int) -> str:
    return f'{year:04d}-{month:02d}'


def _has_text(value: Any) -> bool:
    return bool(str(value or '').strip())


def _is_sha256(value: Any) -> bool:
    return bool(SHA256_PATTERN.match(str(value or '').strip()))


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _year_from_period(value: Any) -> int | None:
    try:
        year = int(str(value)[:4])
    except (TypeError, ValueError):
        return None
    if year <= 0:
        return None
    return year


def _issue(code: str, message: str, *, count: int = 1, severity: str = 'blocking') -> dict[str, Any]:
    return {
        'code': code,
        'severity': severity,
        'count': int(count),
        'message': message,
    }


def _month_phase(
    *,
    key: str,
    label: str,
    completed_months: set[int],
    blocking_issue_code: str,
    message: str,
) -> ProgressPhase:
    missing = [month for month in MONTHS if month not in completed_months]
    return ProgressPhase(
        key=key,
        label=label,
        expected=12,
        completed=len(completed_months),
        missing=missing,
        blocking_issue_code=blocking_issue_code,
        message=message,
    )


def _single_phase(
    *,
    key: str,
    label: str,
    exists: bool,
    blocking_issue_code: str,
    message: str,
    missing_label: str = 'required',
) -> ProgressPhase:
    return ProgressPhase(
        key=key,
        label=label,
        expected=1,
        completed=1 if exists else 0,
        missing=[] if exists else [missing_label],
        blocking_issue_code=blocking_issue_code,
        message=message,
    )


def _classification(phases: list[ProgressPhase]) -> str:
    if all(phase.ready for phase in phases):
        return 'preparado'
    if all(phase.completed == 0 for phase in phases):
        return 'sin_datos'
    return 'parcial'


def _annual_export_has_ready_local_package(
    *,
    export_payload: Any,
    target_items_total: int,
    ddjj_items_total: int,
    f22_items_total: int,
    official_format: bool,
    sii_submission: bool,
    final_tax_calculation: bool,
) -> bool:
    if official_format or sii_submission or final_tax_calculation:
        return False
    if not isinstance(export_payload, dict):
        return False
    if (
        export_payload.get('official_format') not in (False, None)
        or export_payload.get('sii_submission') not in (False, None)
        or bool(export_payload.get('sii_submission_attempted'))
        or export_payload.get('final_tax_calculation') not in (False, None)
    ):
        return False

    package_manifest = export_payload.get('export_file_package_manifest')
    if not isinstance(package_manifest, list):
        return False
    if export_payload.get('export_file_package_version') != 'annual-tax-export-file-package-v1':
        return False
    package_files_total = _int_or_none(export_payload.get('export_file_package_files_total'))
    ddjj_package_files_total = _int_or_none(export_payload.get('ddjj_export_package_files_total'))
    f22_package_files_total = _int_or_none(export_payload.get('f22_export_package_files_total'))
    if target_items_total <= 0 or f22_items_total <= 0:
        return False
    if package_files_total != target_items_total:
        return False
    if ddjj_package_files_total != ddjj_items_total:
        return False
    if f22_package_files_total != f22_items_total:
        return False

    package_hash = export_payload.get('export_file_package_hash')
    if not _is_sha256(package_hash) or package_hash != payload_hash(package_manifest):
        return False

    package_counts = {TipoAnnualTaxArtifactTarget.DDJJ: 0, TipoAnnualTaxArtifactTarget.F22: 0}
    seen_file_names = set()
    for entry in package_manifest:
        if not isinstance(entry, dict):
            return False
        target_kind = entry.get('target_kind')
        if target_kind not in package_counts:
            return False
        package_counts[target_kind] += 1
        file_name = str(entry.get('file_name') or '').strip()
        if file_name in seen_file_names:
            return False
        seen_file_names.add(file_name)
        try:
            payload_size = int(entry.get('payload_size_bytes') or 0)
            manifest_size = int(entry.get('manifest_payload_size_bytes') or 0)
        except (TypeError, ValueError):
            return False
        if (
            entry.get('package_entry_version') != 'annual-tax-export-file-package-manifest-v1'
            or not _has_text(entry.get('artifact_matrix_item_id'))
            or not _has_text(entry.get('target_code'))
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
            or payload_size <= 0
            or payload_size != manifest_size
            or entry.get('requires_official_format_gate') is not True
            or entry.get('requires_explicit_submission_authorization') is not True
            or entry.get('official_format') not in (False, None)
            or entry.get('sii_submission') not in (False, None)
            or entry.get('final_tax_calculation') not in (False, None)
        ):
            return False

    return (
        len(package_manifest) == target_items_total
        and package_counts[TipoAnnualTaxArtifactTarget.DDJJ] == ddjj_items_total
        and package_counts[TipoAnnualTaxArtifactTarget.F22] == f22_items_total
    )


def _annual_trial_balance_has_materialized_lines(*, lines_total: Any, active_lines_total: int) -> bool:
    declared_lines_total = _int_or_none(lines_total)
    return (
        declared_lines_total is not None
        and declared_lines_total > 0
        and active_lines_total > 0
        and declared_lines_total == active_lines_total
    )


def _annual_workbook_has_materialized_lines(*, active_lines_total: int) -> bool:
    return active_lines_total > 0


def _annual_dossier_has_reviewable_summary(item: dict[str, Any]) -> bool:
    resumen = item.get('resumen_dossier')
    if not isinstance(resumen, dict) or not resumen:
        return False
    if not _has_text(item.get('responsible_ref')) or not _has_text(item.get('dossier_ref')):
        return False
    if item.get('review_state') != EstadoAnnualTaxArtifactReview.READY_FOR_REVIEW:
        return False
    if resumen.get('review_state') != item.get('review_state'):
        return False

    hash_dossier = item.get('hash_dossier')
    if not _is_sha256(hash_dossier) or hash_dossier != payload_hash(resumen):
        return False
    if not _is_sha256(resumen.get('artifact_matrix_hash')):
        return False
    if (
        resumen.get('official_format') not in (False, None)
        or resumen.get('sii_submission') not in (False, None)
        or bool(resumen.get('sii_submission_attempted'))
        or resumen.get('final_tax_calculation') not in (False, None)
    ):
        return False
    if _int_or_none(resumen.get('warnings_pending_review_total')) != 0:
        return False

    required_positive_totals = {
        'monthly_facts_total': 1,
        'workbooks_total': 2,
        'artifact_matrix_items_total': 1,
    }
    for field, minimum in required_positive_totals.items():
        value = _int_or_none(item.get(field))
        if value is None or value < minimum:
            return False

    expected_summary_fields = (
        'empresa_id',
        'proceso_renta_anual_id',
        'source_bundle_id',
        'rule_set_id',
        'artifact_matrix_id',
        'anio_tributario',
        'anio_comercial',
        'monthly_facts_total',
        'workbooks_total',
        'enterprise_registers_total',
        'real_estate_sections_total',
        'artifact_matrix_items_total',
        'warnings_total',
    )
    for field in expected_summary_fields:
        if _int_or_none(resumen.get(field)) != _int_or_none(item.get(field)):
            return False

    process_summary = item.get('proceso_renta_anual__resumen_anual')
    if not isinstance(process_summary, dict):
        return False
    dossier_summary = process_summary.get('annual_tax_dossiers')
    if not isinstance(dossier_summary, dict):
        return False
    dossier_id = item.get('id')
    dossier_id_text = str(dossier_id)
    summary_ids = {str(value) for value in (dossier_summary.get('ids') or [])}
    if _int_or_none(dossier_summary.get('total')) != 1 or summary_ids != {dossier_id_text}:
        return False

    by_id = dossier_summary.get('by_id')
    if not isinstance(by_id, dict):
        return False
    item_summary = by_id.get(dossier_id_text)
    if not isinstance(item_summary, dict):
        return False
    if (
        _int_or_none(item_summary.get('id')) != _int_or_none(dossier_id)
        or item_summary.get('hash_dossier') != hash_dossier
        or _int_or_none(item_summary.get('artifact_matrix_id')) != _int_or_none(item.get('artifact_matrix_id'))
        or item_summary.get('artifact_matrix_hash') != resumen.get('artifact_matrix_hash')
        or item_summary.get('review_state') != item.get('review_state')
    ):
        return False

    for field in (
        'source_bundle_id',
        'rule_set_id',
        'monthly_facts_total',
        'workbooks_total',
        'enterprise_registers_total',
        'real_estate_sections_total',
        'artifact_matrix_items_total',
        'warnings_total',
    ):
        if _int_or_none(item_summary.get(field)) != _int_or_none(item.get(field)):
            return False

    return True


def _progress_percent(phases: list[ProgressPhase]) -> int:
    expected = sum(phase.expected for phase in phases)
    if expected <= 0:
        return 0
    completed = sum(min(phase.completed, phase.expected) for phase in phases)
    return round((completed / expected) * 100)


def _review_boundary() -> dict[str, Any]:
    return {
        **COMPANY_ACCOUNTING_REVIEW_BOUNDARY,
        'not_allowed_actions': list(COMPANY_ACCOUNTING_REVIEW_BOUNDARY['not_allowed_actions']),
    }


def _responsible_review_gate(phases: list[ProgressPhase]) -> dict[str, Any]:
    next_blocking_phase = next((phase for phase in phases if not phase.ready), None)
    local_layers_ready = next_blocking_phase is None
    if local_layers_ready:
        state = 'responsible_review_required'
        next_action_ref = 'audit_or_materialize_responsible_answers'
        blocking_issue_code = 'company_accounting.responsible_review_missing'
    else:
        state = 'local_layers_incomplete'
        next_action_ref = f'complete_local_phase:{next_blocking_phase.key}'
        blocking_issue_code = next_blocking_phase.blocking_issue_code

    return {
        'state': state,
        'local_layers_ready_for_review': local_layers_ready,
        'review_manifest_required': local_layers_ready,
        'ready_for_responsible_decision_handoff': False,
        'ready_for_productive_accounting_review': False,
        'ready_for_final_tax_calculation': False,
        'ready_for_sii_submission': False,
        'requires_responsible_review': True,
        'requires_external_or_controlled_review_artifact': local_layers_ready,
        'blocking_issue_code': blocking_issue_code,
        'next_action_ref': next_action_ref,
        'raw_paths_returned': False,
    }


def _prepared_balance_months(empresa: Empresa, fiscal_year: int) -> tuple[set[int], set[int]]:
    approved = set()
    squared = set()
    balances = BalanceComprobacion.objects.filter(
        empresa=empresa,
        periodo__in=[_period(fiscal_year, month) for month in MONTHS],
    )
    for balance in balances:
        try:
            month = int(str(balance.periodo)[5:7])
        except (TypeError, ValueError):
            continue
        if balance.estado_snapshot == EstadoCierreMensual.APPROVED:
            approved.add(month)
        if balance.estado_snapshot == EstadoCierreMensual.APPROVED and balance.resumen.get('cuadrado') is True:
            squared.add(month)
    return approved, squared


def _is_controlled_f29_no_declaration(resumen_hecho: Any) -> bool:
    if not isinstance(resumen_hecho, dict):
        return False
    f29_payload = resumen_hecho.get('f29')
    if not isinstance(f29_payload, dict):
        return False
    resumen = f29_payload.get('resumen')
    return (
        f29_payload.get('estado_preparacion') == EstadoPreparacionTributaria.NOT_APPLICABLE
        and isinstance(resumen, dict)
        and resumen.get('no_declaration') is True
    )


def _f29_preparation_has_reviewable_payload(item: dict[str, Any]) -> bool:
    resumen = item.get('resumen_formulario')
    return (
        item.get('mes') in MONTHS
        and isinstance(resumen, dict)
        and bool(resumen)
        and not contains_sensitive_reference(resumen, include_sensitive_keys=True)
        and is_non_sensitive_reference(item.get('borrador_ref'))
        and is_non_sensitive_reference(item.get('responsable_revision_ref'))
    )


def _controlled_f29_no_declaration_months(empresa: Empresa, fiscal_year: int) -> set[int]:
    months = set()
    facts = MonthlyTaxFact.objects.filter(
        empresa=empresa,
        anio=fiscal_year,
    ).values('mes', 'resumen_hecho')
    for fact in facts:
        if _is_controlled_f29_no_declaration(fact['resumen_hecho']):
            months.add(fact['mes'])
    return months


def collect_company_accounting_candidates(*, empresa_ids: list[int] | None = None) -> dict[str, Any]:
    empresas = Empresa.objects.all().order_by('razon_social', 'id')
    if empresa_ids is not None:
        empresas = empresas.filter(id__in=empresa_ids)

    company_payloads = {
        empresa.id: {
            'empresa': {
                'id': empresa.id,
                'razon_social': empresa.razon_social,
                'estado': empresa.estado,
            },
            'fiscal_config_active': False,
            'fiscal_regime_code': '',
            'fiscal_regime_supported': False,
            'supported_fiscal_regime_code': SII_AUTOMATED_REGIME_CODE,
            'recommended_fiscal_year': None,
            'years': {},
        }
        for empresa in empresas
    }
    company_ids = set(company_payloads)

    def year_bucket(empresa_id: int, fiscal_year: int) -> dict[str, Any] | None:
        if empresa_id not in company_payloads or fiscal_year <= 0:
            return None
        years = company_payloads[empresa_id]['years']
        if fiscal_year not in years:
            years[fiscal_year] = {
                'fiscal_year': fiscal_year,
                'tax_year': fiscal_year + 1,
                'signals': {
                    'monthly_closes': 0,
                    'monthly_balances': 0,
                    'monthly_balances_squared': 0,
                    'f29_monthly': 0,
                    'annual_processes': 0,
                    'annual_trial_balance': 0,
                    'rli_cpt_workbooks': 0,
                    'annual_dossier': 0,
                    'annual_export': 0,
                },
                'signal_count': 0,
                'recommended': False,
            }
        return years[fiscal_year]

    for config in ConfiguracionFiscalEmpresa.objects.select_related('regimen_tributario').filter(
        empresa_id__in=company_ids,
        estado='activa',
    ):
        regime_code = getattr(config.regimen_tributario, 'codigo_regimen', '') or ''
        payload = company_payloads[config.empresa_id]
        payload['fiscal_config_active'] = True
        payload['fiscal_regime_code'] = regime_code
        payload['fiscal_regime_supported'] = regime_code == SII_AUTOMATED_REGIME_CODE

    close_months: dict[tuple[int, int], set[int]] = defaultdict(set)
    for item in CierreMensualContable.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoCierreMensual.APPROVED,
    ).values('empresa_id', 'anio', 'mes'):
        close_months[(item['empresa_id'], item['anio'])].add(item['mes'])
    for (empresa_id, fiscal_year), months in close_months.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['monthly_closes'] = len(months)

    balance_months: dict[tuple[int, int], set[int]] = defaultdict(set)
    squared_balance_months: dict[tuple[int, int], set[int]] = defaultdict(set)
    for balance in BalanceComprobacion.objects.filter(
        empresa_id__in=company_ids,
        estado_snapshot=EstadoCierreMensual.APPROVED,
    ).values('empresa_id', 'periodo', 'resumen'):
        fiscal_year = _year_from_period(balance['periodo'])
        if fiscal_year is None:
            continue
        try:
            month = int(str(balance['periodo'])[5:7])
        except (TypeError, ValueError):
            continue
        if month not in MONTHS:
            continue
        key = (balance['empresa_id'], fiscal_year)
        balance_months[key].add(month)
        if isinstance(balance['resumen'], dict) and balance['resumen'].get('cuadrado') is True:
            squared_balance_months[key].add(month)
    for (empresa_id, fiscal_year), months in balance_months.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['monthly_balances'] = len(months)
    for (empresa_id, fiscal_year), months in squared_balance_months.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['monthly_balances_squared'] = len(months)

    f29_months: dict[tuple[int, int], set[int]] = defaultdict(set)
    for item in F29PreparacionMensual.objects.filter(
        empresa_id__in=company_ids,
        estado_preparacion__in=PREPARED_OR_BETTER_TAX_STATES,
    ).values(
        'empresa_id',
        'anio',
        'mes',
        'resumen_formulario',
        'borrador_ref',
        'responsable_revision_ref',
    ):
        if not _f29_preparation_has_reviewable_payload(item):
            continue
        f29_months[(item['empresa_id'], item['anio'])].add(item['mes'])
    for item in MonthlyTaxFact.objects.filter(empresa_id__in=company_ids).values(
        'empresa_id',
        'anio',
        'mes',
        'resumen_hecho',
    ):
        if _is_controlled_f29_no_declaration(item['resumen_hecho']):
            f29_months[(item['empresa_id'], item['anio'])].add(item['mes'])
    for (empresa_id, fiscal_year), months in f29_months.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['f29_monthly'] = len(months)

    annual_process_counts: dict[tuple[int, int], int] = defaultdict(int)
    valid_annual_process_ids: dict[int, tuple[int, int]] = {}
    valid_annual_process_source_bundle_ids: dict[int, int] = {}
    for item in ProcesoRentaAnual.objects.filter(
        empresa_id__in=company_ids,
        estado__in=PREPARED_OR_BETTER_TAX_STATES,
        source_bundle__estado=EstadoAnnualTaxSourceBundle.FROZEN,
    ).values('id', 'empresa_id', 'anio_tributario', 'source_bundle_id'):
        key = (item['empresa_id'], item['anio_tributario'] - 1)
        valid_annual_process_ids[item['id']] = key
        valid_annual_process_source_bundle_ids[item['id']] = item['source_bundle_id']
        annual_process_counts[key] += 1
    for (empresa_id, fiscal_year), count in annual_process_counts.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['annual_processes'] = count

    valid_process_id_list = list(valid_annual_process_ids)
    annual_trial_balance_candidates = []
    for item in AnnualTaxTrialBalance.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxTrialBalance.PREPARED,
        proceso_renta_anual_id__in=valid_process_id_list,
    ).values('id', 'proceso_renta_anual_id', 'source_bundle_id', 'lines_total'):
        process_id = item['proceso_renta_anual_id']
        if item['source_bundle_id'] != valid_annual_process_source_bundle_ids.get(process_id):
            continue
        annual_trial_balance_candidates.append(item)
    active_trial_balance_line_counts = Counter(
        AnnualTaxTrialBalanceLine.objects.filter(
            trial_balance_id__in=[item['id'] for item in annual_trial_balance_candidates],
            estado=EstadoRegistro.ACTIVE,
        ).values_list('trial_balance_id', flat=True)
    )
    annual_trial_balance_counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in annual_trial_balance_candidates:
        if not _annual_trial_balance_has_materialized_lines(
            lines_total=item['lines_total'],
            active_lines_total=active_trial_balance_line_counts[item['id']],
        ):
            continue
        annual_trial_balance_counts[valid_annual_process_ids[item['proceso_renta_anual_id']]] += 1
    for (empresa_id, fiscal_year), count in annual_trial_balance_counts.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['annual_trial_balance'] = count

    workbook_candidates = []
    for item in AnnualTaxWorkbook.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
        tipo__in=[TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT],
        proceso_renta_anual_id__in=valid_process_id_list,
    ).values('id', 'proceso_renta_anual_id', 'source_bundle_id', 'tipo'):
        process_id = item['proceso_renta_anual_id']
        if item['source_bundle_id'] != valid_annual_process_source_bundle_ids.get(process_id):
            continue
        workbook_candidates.append(item)
    active_workbook_line_counts = Counter(
        AnnualTaxWorkbookLine.objects.filter(
            workbook_id__in=[item['id'] for item in workbook_candidates],
            estado=EstadoRegistro.ACTIVE,
        ).values_list('workbook_id', flat=True)
    )
    workbook_types: dict[tuple[int, int], set[str]] = defaultdict(set)
    for item in workbook_candidates:
        if not _annual_workbook_has_materialized_lines(
            active_lines_total=active_workbook_line_counts[item['id']],
        ):
            continue
        process_id = item['proceso_renta_anual_id']
        workbook_types[valid_annual_process_ids[process_id]].add(item['tipo'])
    for (empresa_id, fiscal_year), types in workbook_types.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['rli_cpt_workbooks'] = len(types)

    annual_dossier_counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in AnnualTaxDossier.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxDossier.PREPARED,
        proceso_renta_anual_id__in=valid_process_id_list,
    ).values(
        'id',
        'empresa_id',
        'proceso_renta_anual_id',
        'proceso_renta_anual__resumen_anual',
        'source_bundle_id',
        'rule_set_id',
        'artifact_matrix_id',
        'anio_tributario',
        'anio_comercial',
        'responsible_ref',
        'dossier_ref',
        'review_state',
        'monthly_facts_total',
        'workbooks_total',
        'enterprise_registers_total',
        'real_estate_sections_total',
        'artifact_matrix_items_total',
        'warnings_total',
        'resumen_dossier',
        'hash_dossier',
    ):
        process_id = item['proceso_renta_anual_id']
        if item['source_bundle_id'] != valid_annual_process_source_bundle_ids.get(process_id):
            continue
        if not _annual_dossier_has_reviewable_summary(item):
            continue
        annual_dossier_counts[valid_annual_process_ids[process_id]] += 1
    for (empresa_id, fiscal_year), count in annual_dossier_counts.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['annual_dossier'] = count

    annual_export_counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in AnnualTaxExport.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxExport.PREPARED,
        official_format=False,
        sii_submission=False,
        final_tax_calculation=False,
        proceso_renta_anual_id__in=valid_process_id_list,
    ).values(
        'proceso_renta_anual_id',
        'source_bundle_id',
        'dossier__source_bundle_id',
        'export_payload',
        'target_items_total',
        'ddjj_items_total',
        'f22_items_total',
        'official_format',
        'sii_submission',
        'final_tax_calculation',
    ):
        process_id = item['proceso_renta_anual_id']
        expected_source_bundle_id = valid_annual_process_source_bundle_ids.get(process_id)
        if item['source_bundle_id'] != expected_source_bundle_id:
            continue
        if item['dossier__source_bundle_id'] != expected_source_bundle_id:
            continue
        if not _annual_export_has_ready_local_package(
            export_payload=item['export_payload'],
            target_items_total=int(item['target_items_total'] or 0),
            ddjj_items_total=int(item['ddjj_items_total'] or 0),
            f22_items_total=int(item['f22_items_total'] or 0),
            official_format=bool(item['official_format']),
            sii_submission=bool(item['sii_submission']),
            final_tax_calculation=bool(item['final_tax_calculation']),
        ):
            continue
        annual_export_counts[valid_annual_process_ids[process_id]] += 1
    for (empresa_id, fiscal_year), count in annual_export_counts.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['annual_export'] = count

    candidates = []
    for payload in company_payloads.values():
        years = []
        for year_payload in payload['years'].values():
            signals = year_payload['signals']
            year_payload['signal_count'] = (
                signals['monthly_closes']
                + signals['monthly_balances']
                + signals['monthly_balances_squared']
                + signals['f29_monthly']
                + (signals['annual_processes'] * 3)
                + (signals['annual_trial_balance'] * 2)
                + signals['rli_cpt_workbooks']
                + (signals['annual_dossier'] * 2)
                + (signals['annual_export'] * 2)
            )
            years.append(year_payload)
        years.sort(key=lambda item: (item['signal_count'], item['fiscal_year']), reverse=True)
        if years:
            years[0]['recommended'] = True
            payload['recommended_fiscal_year'] = years[0]['fiscal_year']
            payload['years'] = years
            candidates.append(payload)

    candidates.sort(
        key=lambda item: (
            -item['years'][0]['signal_count'],
            -item['years'][0]['fiscal_year'],
            item['empresa']['razon_social'],
        ),
    )

    return {
        'candidates': candidates,
        'selection_boundary': dict(COMPANY_ACCOUNTING_SELECTION_BOUNDARY),
        'summary': {
            'companies_total': len(company_payloads),
            'candidate_companies': len(candidates),
            'candidate_years': sum(len(candidate['years']) for candidate in candidates),
            'unsupported_fiscal_regime_companies': sum(
                1
                for candidate in candidates
                if candidate['fiscal_config_active'] and not candidate['fiscal_regime_supported']
            ),
        },
    }


def collect_company_accounting_progress(*, empresa_id: int, fiscal_year: int) -> dict[str, Any]:
    empresa = Empresa.objects.get(pk=empresa_id)
    tax_year = fiscal_year + 1

    active_fiscal_config = (
        ConfiguracionFiscalEmpresa.objects.select_related('regimen_tributario')
        .filter(
            empresa=empresa,
            estado='activa',
        )
        .first()
    )
    fiscal_config_active = active_fiscal_config is not None
    fiscal_regime_code = ''
    if active_fiscal_config is not None:
        fiscal_regime_code = getattr(active_fiscal_config.regimen_tributario, 'codigo_regimen', '') or ''
    fiscal_regime_supported = fiscal_regime_code == SII_AUTOMATED_REGIME_CODE

    if not fiscal_config_active:
        fiscal_config_phase = _single_phase(
            key='fiscal_config',
            label='Configuracion fiscal activa soportada',
            exists=False,
            blocking_issue_code='company_accounting.fiscal_config_missing',
            message='La empresa requiere ConfiguracionFiscalEmpresa activa antes de revision contable/renta.',
        )
    elif not fiscal_regime_supported:
        fiscal_config_phase = ProgressPhase(
            key='fiscal_config',
            label='Configuracion fiscal activa soportada',
            expected=1,
            completed=0,
            missing=[fiscal_regime_code or 'regimen_sin_codigo'],
            blocking_issue_code='company_accounting.fiscal_config_unsupported_regime',
            message='La empresa tiene una configuracion fiscal activa fuera del regimen automatizable del v1.',
        )
    else:
        fiscal_config_phase = _single_phase(
            key='fiscal_config',
            label='Configuracion fiscal activa soportada',
            exists=True,
            blocking_issue_code='company_accounting.fiscal_config_missing',
            message='La empresa requiere ConfiguracionFiscalEmpresa activa antes de revision contable/renta.',
        )

    approved_close_months = set(
        CierreMensualContable.objects.filter(
            empresa=empresa,
            anio=fiscal_year,
            estado=EstadoCierreMensual.APPROVED,
        ).values_list('mes', flat=True)
    )

    approved_balance_months, squared_balance_months = _prepared_balance_months(empresa, fiscal_year)

    prepared_f29_months = {
        item['mes']
        for item in F29PreparacionMensual.objects.filter(
            empresa=empresa,
            anio=fiscal_year,
            estado_preparacion__in=PREPARED_OR_BETTER_TAX_STATES,
        ).values(
            'mes',
            'resumen_formulario',
            'borrador_ref',
            'responsable_revision_ref',
        )
        if _f29_preparation_has_reviewable_payload(item)
    }
    prepared_f29_months.update(_controlled_f29_no_declaration_months(empresa, fiscal_year))

    annual_process_candidate = (
        ProcesoRentaAnual.objects.filter(
            empresa=empresa,
            anio_tributario=tax_year,
            estado__in=PREPARED_OR_BETTER_TAX_STATES,
        )
        .select_related('source_bundle')
        .order_by('-id')
        .first()
    )
    annual_process_has_frozen_bundle = (
        annual_process_candidate is not None
        and annual_process_candidate.source_bundle_id is not None
        and annual_process_candidate.source_bundle.estado == EstadoAnnualTaxSourceBundle.FROZEN
    )
    annual_process = annual_process_candidate if annual_process_has_frozen_bundle else None
    if annual_process is None:
        annual_trial_balance_ready = False
        prepared_workbook_types = set()
        annual_dossier_ready = False
        annual_export_ready = False
    else:
        annual_source_bundle_id = annual_process.source_bundle_id
        process_filter = {
            'empresa': empresa,
            'anio_tributario': tax_year,
            'proceso_renta_anual': annual_process,
            'source_bundle_id': annual_source_bundle_id,
        }
        annual_trial_balance_candidates = list(AnnualTaxTrialBalance.objects.filter(
            **process_filter,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        ).values('id', 'lines_total'))
        active_trial_balance_line_counts = Counter(
            AnnualTaxTrialBalanceLine.objects.filter(
                trial_balance_id__in=[item['id'] for item in annual_trial_balance_candidates],
                estado=EstadoRegistro.ACTIVE,
            ).values_list('trial_balance_id', flat=True)
        )
        annual_trial_balance_ready = any(
            _annual_trial_balance_has_materialized_lines(
                lines_total=item['lines_total'],
                active_lines_total=active_trial_balance_line_counts[item['id']],
            )
            for item in annual_trial_balance_candidates
        )

        workbook_candidates = list(
            AnnualTaxWorkbook.objects.filter(
                **process_filter,
                estado=EstadoAnnualTaxWorkbook.PREPARED,
                tipo__in=[TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT],
            ).values('id', 'tipo')
        )
        active_workbook_line_counts = Counter(
            AnnualTaxWorkbookLine.objects.filter(
                workbook_id__in=[item['id'] for item in workbook_candidates],
                estado=EstadoRegistro.ACTIVE,
            ).values_list('workbook_id', flat=True)
        )
        prepared_workbook_types = {
            item['tipo']
            for item in workbook_candidates
            if _annual_workbook_has_materialized_lines(
                active_lines_total=active_workbook_line_counts[item['id']],
            )
        }

        annual_dossier_ready = any(
            _annual_dossier_has_reviewable_summary(dossier)
            for dossier in AnnualTaxDossier.objects.filter(
                **process_filter,
                estado=EstadoAnnualTaxDossier.PREPARED,
            ).values(
                'id',
                'empresa_id',
                'proceso_renta_anual_id',
                'proceso_renta_anual__resumen_anual',
                'source_bundle_id',
                'rule_set_id',
                'artifact_matrix_id',
                'anio_tributario',
                'anio_comercial',
                'responsible_ref',
                'dossier_ref',
                'review_state',
                'monthly_facts_total',
                'workbooks_total',
                'enterprise_registers_total',
                'real_estate_sections_total',
                'artifact_matrix_items_total',
                'warnings_total',
                'resumen_dossier',
                'hash_dossier',
            )
        )
        annual_export_ready = any(
            _annual_export_has_ready_local_package(
                export_payload=export['export_payload'],
                target_items_total=int(export['target_items_total'] or 0),
                ddjj_items_total=int(export['ddjj_items_total'] or 0),
                f22_items_total=int(export['f22_items_total'] or 0),
                official_format=bool(export['official_format']),
                sii_submission=bool(export['sii_submission']),
                final_tax_calculation=bool(export['final_tax_calculation']),
            )
            for export in AnnualTaxExport.objects.filter(
                **process_filter,
                estado=EstadoAnnualTaxExport.PREPARED,
                official_format=False,
                sii_submission=False,
                final_tax_calculation=False,
                dossier__source_bundle_id=annual_source_bundle_id,
            ).values(
                'export_payload',
                'target_items_total',
                'ddjj_items_total',
                'f22_items_total',
                'official_format',
                'sii_submission',
                'final_tax_calculation',
            )
        )

    phases = [
        fiscal_config_phase,
        _month_phase(
            key='monthly_closes',
            label='Cierres mensuales aprobados',
            completed_months=approved_close_months,
            blocking_issue_code='company_accounting.monthly_closes_missing',
            message='Faltan cierres mensuales aprobados para el ano comercial.',
        ),
        _month_phase(
            key='monthly_balances',
            label='Balances mensuales aprobados',
            completed_months=approved_balance_months,
            blocking_issue_code='company_accounting.monthly_balances_missing',
            message='Faltan BalanceComprobacion aprobados por mes.',
        ),
        _month_phase(
            key='monthly_balances_squared',
            label='Balances mensuales cuadrados',
            completed_months=squared_balance_months,
            blocking_issue_code='company_accounting.monthly_balances_not_squared',
            message='Faltan balances mensuales aprobados con resumen.cuadrado=true.',
        ),
        _month_phase(
            key='f29_monthly',
            label='F29 mensuales preparados o superiores',
            completed_months=prepared_f29_months,
            blocking_issue_code='company_accounting.f29_monthly_missing',
            message='Faltan F29 mensuales preparados/aprobados/presentados para el ano comercial.',
        ),
        _single_phase(
            key='annual_process',
            label='Proceso de renta anual trazable preparado',
            exists=annual_process_has_frozen_bundle,
            blocking_issue_code=(
                'company_accounting.annual_process_source_bundle_missing'
                if annual_process_candidate is not None
                else 'company_accounting.annual_process_missing'
            ),
            message=(
                'ProcesoRentaAnual preparado requiere AnnualTaxSourceBundle congelado para ser trazable.'
                if annual_process_candidate is not None
                else 'Falta ProcesoRentaAnual preparado o superior para el AT correspondiente.'
            ),
            missing_label='source_bundle_congelado' if annual_process_candidate is not None else 'required',
        ),
        _single_phase(
            key='annual_trial_balance',
            label='Balance anual tributario preparado',
            exists=annual_trial_balance_ready,
            blocking_issue_code='company_accounting.annual_trial_balance_missing',
            message='Falta AnnualTaxTrialBalance preparado desde BalanceComprobacion de diciembre.',
        ),
        ProgressPhase(
            key='rli_cpt_workbooks',
            label='Workbooks RLI/CPT preparados',
            expected=2,
            completed=len(prepared_workbook_types),
            missing=[kind for kind in [TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT] if kind not in prepared_workbook_types],
            blocking_issue_code='company_accounting.rli_cpt_workbooks_missing',
            message='Faltan workbooks RLI y/o CPT preparados.',
        ),
        _single_phase(
            key='annual_dossier',
            label='Dossier anual revisable preparado',
            exists=annual_dossier_ready,
            blocking_issue_code='company_accounting.annual_dossier_missing',
            message='Falta AnnualTaxDossier preparado y revisable.',
        ),
        _single_phase(
            key='annual_export',
            label='Preview/export anual local preparado',
            exists=annual_export_ready,
            blocking_issue_code='company_accounting.annual_export_missing',
            message='Falta AnnualTaxExport preparado como preview local sin formato oficial ni presentacion SII.',
        ),
    ]

    issues = [
        _issue(phase.blocking_issue_code, phase.message, count=len(phase.missing) or phase.expected - phase.completed)
        for phase in phases
        if not phase.ready
    ]

    return {
        'empresa': {
            'id': empresa.pk,
            'razon_social': empresa.razon_social,
            'estado': empresa.estado,
        },
        'fiscal_year': fiscal_year,
        'tax_year': tax_year,
        'classification': _classification(phases),
        'progress_percent': _progress_percent(phases),
        'ready_for_company_accounting_review': all(phase.ready for phase in phases),
        'review_boundary': _review_boundary(),
        'responsible_review_gate': _responsible_review_gate(phases),
        'fiscal_config': {
            'active': fiscal_config_active,
            'regime_code': fiscal_regime_code,
            'supported': fiscal_regime_supported,
            'supported_regime_code': SII_AUTOMATED_REGIME_CODE,
        },
        'phases': {phase.key: phase.as_dict() for phase in phases},
        'issue_counts': {
            'blocking': len(issues),
        },
        'issues': issues,
        'next_blocking_phase': next((phase.key for phase in phases if not phase.ready), ''),
    }
