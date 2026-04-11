from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import PartnerOwnSummaryPermission, ReportingPermission
from .services import (
    build_annual_tax_summary,
    build_financial_monthly_summary,
    build_migration_manual_resolution_summary,
    build_operational_dashboard,
    build_partner_summary,
    build_period_books_summary,
)


class OperationalDashboardView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(build_operational_dashboard())


class FinancialMonthlySummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        anio = int(request.query_params.get('anio'))
        mes = int(request.query_params.get('mes'))
        empresa_id = request.query_params.get('empresa_id')
        return Response(build_financial_monthly_summary(anio, mes, int(empresa_id) if empresa_id else None))


class PartnerSummaryView(APIView):
    permission_classes = [PartnerOwnSummaryPermission]

    def get(self, request, pk):
        return Response(build_partner_summary(pk))


class PeriodBooksSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        empresa_id = int(request.query_params.get('empresa_id'))
        periodo = request.query_params.get('periodo')
        return Response(build_period_books_summary(empresa_id, periodo))


class AnnualTaxSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        anio_tributario = int(request.query_params.get('anio_tributario'))
        empresa_id = request.query_params.get('empresa_id')
        return Response(build_annual_tax_summary(anio_tributario, int(empresa_id) if empresa_id else None))


class MigrationManualResolutionSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        status = request.query_params.get('status', 'open')
        return Response(build_migration_manual_resolution_summary(status=status))
