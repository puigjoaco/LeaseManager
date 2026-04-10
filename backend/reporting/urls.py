from django.urls import path

from .views import (
    AnnualTaxSummaryView,
    FinancialMonthlySummaryView,
    MigrationManualResolutionSummaryView,
    OperationalDashboardView,
    PartnerSummaryView,
    PeriodBooksSummaryView,
)

urlpatterns = [
    path('dashboard/operativo/', OperationalDashboardView.as_view(), name='reporting-dashboard-operativo'),
    path('financiero/mensual/', FinancialMonthlySummaryView.as_view(), name='reporting-financiero-mensual'),
    path('contabilidad/libros-periodo/', PeriodBooksSummaryView.as_view(), name='reporting-libros-periodo'),
    path('migracion/resoluciones-manuales/', MigrationManualResolutionSummaryView.as_view(), name='reporting-migration-manual-resolutions'),
    path('tributario/anual/', AnnualTaxSummaryView.as_view(), name='reporting-tributario-anual'),
    path('socios/<int:pk>/resumen/', PartnerSummaryView.as_view(), name='reporting-socio-resumen'),
]
