from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import OperationalOverviewPermission, PartnerOwnSummaryPermission, ReportingPermission
from core.scope_access import get_scope_access
from .services import (
    build_annual_tax_summary,
    build_financial_monthly_summary,
    build_manual_resolution_summary,
    build_migration_manual_resolution_summary,
    build_operational_dashboard,
    build_operational_overview_counts,
    build_partner_summary,
    build_period_books_summary,
    build_reporting_reference_options,
)


def _use_cache(request) -> bool:
    return request.query_params.get('refresh') != '1'


def _required_int_query_param(request, name: str) -> int:
    raw_value = request.query_params.get(name)
    if raw_value in (None, ''):
        raise ValidationError({name: 'Este parametro es obligatorio.'})
    try:
        return int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValidationError({name: 'Debe ser un entero valido.'}) from error


def _optional_int_query_param(request, name: str) -> int | None:
    raw_value = request.query_params.get(name)
    if raw_value in (None, ''):
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValidationError({name: 'Debe ser un entero valido.'}) from error


def _required_query_param(request, name: str) -> str:
    raw_value = request.query_params.get(name)
    if raw_value in (None, ''):
        raise ValidationError({name: 'Este parametro es obligatorio.'})
    return raw_value


class OperationalDashboardView(APIView):
    permission_classes = [OperationalOverviewPermission]

    def get(self, request):
        mode = request.query_params.get('mode', 'full')
        include_secondary = mode != 'summary'
        return Response(
            build_operational_dashboard(
                access=get_scope_access(request.user),
                include_secondary=include_secondary,
                use_cache=_use_cache(request),
            )
        )


class OverviewSecondaryCountsView(APIView):
    permission_classes = [OperationalOverviewPermission]

    def get(self, request):
        return Response(build_operational_overview_counts(access=get_scope_access(request.user), use_cache=_use_cache(request)))


class FinancialMonthlySummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        anio = _required_int_query_param(request, 'anio')
        mes = _required_int_query_param(request, 'mes')
        empresa_id = _optional_int_query_param(request, 'empresa_id')
        return Response(
            build_financial_monthly_summary(
                anio,
                mes,
                empresa_id,
                access=get_scope_access(request.user),
            )
        )


class PartnerSummaryView(APIView):
    permission_classes = [PartnerOwnSummaryPermission]

    def get(self, request, pk):
        from patrimonio.models import Socio

        try:
            payload = build_partner_summary(pk, access=get_scope_access(request.user))
        except Socio.DoesNotExist as error:
            raise NotFound('Socio no encontrado.') from error
        return Response(payload)


class ReportingReferenceOptionsView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        return Response(build_reporting_reference_options(access=get_scope_access(request.user)))


class PeriodBooksSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        empresa_id = _required_int_query_param(request, 'empresa_id')
        periodo = _required_query_param(request, 'periodo')
        return Response(build_period_books_summary(empresa_id, periodo, access=get_scope_access(request.user)))


class AnnualTaxSummaryView(APIView):
    permission_classes = [ReportingPermission]

    def get(self, request):
        anio_tributario = _required_int_query_param(request, 'anio_tributario')
        empresa_id = _optional_int_query_param(request, 'empresa_id')
        return Response(
            build_annual_tax_summary(
                anio_tributario,
                empresa_id,
                access=get_scope_access(request.user),
            )
        )


class MigrationManualResolutionSummaryView(APIView):
    permission_classes = [OperationalOverviewPermission]

    def get(self, request):
        status = request.query_params.get('status', 'open')
        return Response(
            build_migration_manual_resolution_summary(
                status=status,
                access=get_scope_access(request.user),
                use_cache=_use_cache(request),
            )
        )


class ManualResolutionSummaryView(APIView):
    permission_classes = [OperationalOverviewPermission]

    def get(self, request):
        status = request.query_params.get('status', 'open')
        return Response(
            build_manual_resolution_summary(
                status=status,
                access=get_scope_access(request.user),
                use_cache=_use_cache(request),
            )
        )
