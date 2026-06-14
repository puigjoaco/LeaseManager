from __future__ import annotations

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
