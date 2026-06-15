from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoPreparacionTributaria,
)
from patrimonio.models import Empresa
from sii.models import (
    AnnualTaxDossier,
    AnnualTaxExport,
    AnnualTaxTrialBalance,
    AnnualTaxWorkbook,
    EstadoAnnualTaxDossier,
    EstadoAnnualTaxExport,
    EstadoAnnualTaxTrialBalance,
    EstadoAnnualTaxWorkbook,
    F29PreparacionMensual,
    ProcesoRentaAnual,
    TipoAnnualTaxWorkbook,
)


MONTHS = tuple(range(1, 13))
PREPARED_OR_BETTER_TAX_STATES = {
    EstadoPreparacionTributaria.PREPARED,
    EstadoPreparacionTributaria.APPROVED,
    EstadoPreparacionTributaria.PRESENTED,
    EstadoPreparacionTributaria.OBSERVED,
    EstadoPreparacionTributaria.RECTIFIED,
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


def _progress_percent(phases: list[ProgressPhase]) -> int:
    expected = sum(phase.expected for phase in phases)
    if expected <= 0:
        return 0
    completed = sum(min(phase.completed, phase.expected) for phase in phases)
    return round((completed / expected) * 100)


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

    for empresa_id in ConfiguracionFiscalEmpresa.objects.filter(
        empresa_id__in=company_ids,
        estado='activa',
    ).values_list('empresa_id', flat=True):
        company_payloads[empresa_id]['fiscal_config_active'] = True

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
    ).values('empresa_id', 'anio', 'mes'):
        f29_months[(item['empresa_id'], item['anio'])].add(item['mes'])
    for (empresa_id, fiscal_year), months in f29_months.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['f29_monthly'] = len(months)

    annual_process_counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in ProcesoRentaAnual.objects.filter(
        empresa_id__in=company_ids,
        estado__in=PREPARED_OR_BETTER_TAX_STATES,
    ).values('empresa_id', 'anio_tributario'):
        annual_process_counts[(item['empresa_id'], item['anio_tributario'] - 1)] += 1
    for (empresa_id, fiscal_year), count in annual_process_counts.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['annual_processes'] = count

    annual_trial_balance_counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in AnnualTaxTrialBalance.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxTrialBalance.PREPARED,
    ).values('empresa_id', 'anio_tributario'):
        annual_trial_balance_counts[(item['empresa_id'], item['anio_tributario'] - 1)] += 1
    for (empresa_id, fiscal_year), count in annual_trial_balance_counts.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['annual_trial_balance'] = count

    workbook_types: dict[tuple[int, int], set[str]] = defaultdict(set)
    for item in AnnualTaxWorkbook.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxWorkbook.PREPARED,
        tipo__in=[TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT],
    ).values('empresa_id', 'anio_tributario', 'tipo'):
        workbook_types[(item['empresa_id'], item['anio_tributario'] - 1)].add(item['tipo'])
    for (empresa_id, fiscal_year), types in workbook_types.items():
        if bucket := year_bucket(empresa_id, fiscal_year):
            bucket['signals']['rli_cpt_workbooks'] = len(types)

    annual_dossier_counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in AnnualTaxDossier.objects.filter(
        empresa_id__in=company_ids,
        estado=EstadoAnnualTaxDossier.PREPARED,
    ).values('empresa_id', 'anio_tributario'):
        annual_dossier_counts[(item['empresa_id'], item['anio_tributario'] - 1)] += 1
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
    ).values('empresa_id', 'anio_tributario'):
        annual_export_counts[(item['empresa_id'], item['anio_tributario'] - 1)] += 1
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
        'summary': {
            'companies_total': len(company_payloads),
            'candidate_companies': len(candidates),
            'candidate_years': sum(len(candidate['years']) for candidate in candidates),
        },
    }


def collect_company_accounting_progress(*, empresa_id: int, fiscal_year: int) -> dict[str, Any]:
    empresa = Empresa.objects.get(pk=empresa_id)
    tax_year = fiscal_year + 1

    fiscal_config_ready = ConfiguracionFiscalEmpresa.objects.filter(
        empresa=empresa,
        estado='activa',
    ).exists()

    approved_close_months = set(
        CierreMensualContable.objects.filter(
            empresa=empresa,
            anio=fiscal_year,
            estado=EstadoCierreMensual.APPROVED,
        ).values_list('mes', flat=True)
    )

    approved_balance_months, squared_balance_months = _prepared_balance_months(empresa, fiscal_year)

    prepared_f29_months = set(
        F29PreparacionMensual.objects.filter(
            empresa=empresa,
            anio=fiscal_year,
            estado_preparacion__in=PREPARED_OR_BETTER_TAX_STATES,
        ).values_list('mes', flat=True)
    )

    annual_process = (
        ProcesoRentaAnual.objects.filter(
            empresa=empresa,
            anio_tributario=tax_year,
            estado__in=PREPARED_OR_BETTER_TAX_STATES,
        )
        .order_by('-id')
        .first()
    )
    if annual_process is None:
        annual_trial_balance_ready = False
        prepared_workbook_types = set()
        annual_dossier_ready = False
        annual_export_ready = False
    else:
        process_filter = {
            'empresa': empresa,
            'anio_tributario': tax_year,
            'proceso_renta_anual': annual_process,
        }
        annual_trial_balance_ready = AnnualTaxTrialBalance.objects.filter(
            **process_filter,
            estado=EstadoAnnualTaxTrialBalance.PREPARED,
        ).exists()

        prepared_workbook_types = set(
            AnnualTaxWorkbook.objects.filter(
                **process_filter,
                estado=EstadoAnnualTaxWorkbook.PREPARED,
                tipo__in=[TipoAnnualTaxWorkbook.RLI, TipoAnnualTaxWorkbook.CPT],
            ).values_list('tipo', flat=True)
        )

        annual_dossier_ready = AnnualTaxDossier.objects.filter(
            **process_filter,
            estado=EstadoAnnualTaxDossier.PREPARED,
        ).exists()
        annual_export_ready = AnnualTaxExport.objects.filter(
            **process_filter,
            estado=EstadoAnnualTaxExport.PREPARED,
            official_format=False,
            sii_submission=False,
            final_tax_calculation=False,
        ).exists()

    phases = [
        _single_phase(
            key='fiscal_config',
            label='Configuracion fiscal activa',
            exists=fiscal_config_ready,
            blocking_issue_code='company_accounting.fiscal_config_missing',
            message='La empresa requiere ConfiguracionFiscalEmpresa activa antes de revision contable/renta.',
        ),
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
            label='Proceso de renta anual preparado',
            exists=annual_process is not None,
            blocking_issue_code='company_accounting.annual_process_missing',
            message='Falta ProcesoRentaAnual preparado o superior para el AT correspondiente.',
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
        'phases': {phase.key: phase.as_dict() for phase in phases},
        'issue_counts': {
            'blocking': len(issues),
        },
        'issues': issues,
        'next_blocking_phase': next((phase.key for phase in phases if not phase.ready), ''),
    }
