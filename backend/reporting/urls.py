from django.urls import path

from .views import (
    AnnualTaxSummaryView,
    FinancialMonthlySummaryView,
    ManualResolutionSummaryView,
    MigrationManualResolutionSummaryView,
    OperationalDashboardView,
    OverviewSecondaryCountsView,
    PartnerSummaryView,
    PeriodBooksSummaryView,
    ReportingReferenceOptionsView,
)

urlpatterns = [
    path('dashboard/operativo/', OperationalDashboardView.as_view(), name='reporting-dashboard-operativo'),
    path('dashboard/overview-secondary/', OverviewSecondaryCountsView.as_view(), name='reporting-overview-secondary'),
    path('manual-resolutions/summary/', ManualResolutionSummaryView.as_view(), name='reporting-manual-resolutions-summary'),
    path('financiero/mensual/', FinancialMonthlySummaryView.as_view(), name='reporting-financiero-mensual'),
    path('contabilidad/libros-periodo/', PeriodBooksSummaryView.as_view(), name='reporting-libros-periodo'),
    path('migracion/resoluciones-manuales/', MigrationManualResolutionSummaryView.as_view(), name='reporting-migration-manual-resolutions'),
    path('references/', ReportingReferenceOptionsView.as_view(), name='reporting-reference-options'),
    path('tributario/anual/', AnnualTaxSummaryView.as_view(), name='reporting-tributario-anual'),
    path('socios/<int:pk>/resumen/', PartnerSummaryView.as_view(), name='reporting-socio-resumen'),
]
