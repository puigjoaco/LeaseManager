from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from patrimonio.models import Empresa, Socio


DEFAULT_MONTHS = ("2026-04", "2026-05")
DEFAULT_SHOWCASE_MONTH = "2026-05"
DEFAULT_ANNUAL_YEAR = 2027
DEFAULT_CREATED_BY = "demo-admin"
DEFAULT_UF_VALUES = {
    date(2026, 4, 1): Decimal("39841.72"),
    date(2026, 5, 1): Decimal("40133.50"),
}


@dataclass(frozen=True)
class OperationalMonth:
    year: int
    month: int

    @property
    def text(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    @property
    def first_day(self) -> date:
        return date(self.year, self.month, 1)


class Command(BaseCommand):
    help = (
        "Orquesta el baseline demo publico del greenfield: usuarios demo, datos operativos, "
        "control mensual, flujo tributario mensual/anual y Compliance."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            action="append",
            type=int,
            dest="company_ids",
            help="Empresa a incluir. Se puede repetir. Default: todas las activas.",
        )
        parser.add_argument(
            "--month",
            action="append",
            dest="months",
            help="Mes operativo a poblar en formato YYYY-MM. Se puede repetir. Default: 2026-04 y 2026-05.",
        )
        parser.add_argument(
            "--showcase-month",
            default=DEFAULT_SHOWCASE_MONTH,
            help=f"Mes principal para control/tributario mensual. Default: {DEFAULT_SHOWCASE_MONTH}",
        )
        parser.add_argument(
            "--annual-year",
            type=int,
            default=DEFAULT_ANNUAL_YEAR,
            help=f"Año tributario para el flujo anual demo. Default: {DEFAULT_ANNUAL_YEAR}",
        )
        parser.add_argument(
            "--uf",
            action="append",
            dest="uf_values",
            help="Valor UF explícito en formato YYYY-MM-DD=VALOR. Se puede repetir.",
        )
        parser.add_argument(
            "--socio-id",
            type=int,
            help="Socio a usar para export demo de Compliance. Default: primer socio activo.",
        )
        parser.add_argument(
            "--created-by",
            default=DEFAULT_CREATED_BY,
            help=f"Usuario creador de exportes de Compliance. Default: {DEFAULT_CREATED_BY}",
        )
        parser.add_argument(
            "--skip-seed-access",
            action="store_true",
            help="No ejecutar seed_demo_access.",
        )
        parser.add_argument(
            "--skip-compliance",
            action="store_true",
            help="No ejecutar bootstrap de Compliance.",
        )
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Falla ante cualquier subpaso que no se pueda completar.",
        )

    def handle(self, *args, **options):
        company_ids = self._resolve_company_ids(options.get("company_ids") or [])
        months = self._parse_months(options.get("months") or list(DEFAULT_MONTHS))
        showcase_month = self._parse_month(options["showcase_month"])
        uf_values = self._build_uf_values(months, options.get("uf_values") or [])
        annual_year = options["annual_year"]
        created_by = options["created_by"].strip() or DEFAULT_CREATED_BY
        strict = options["strict"]

        socio_id = self._resolve_socio_id(options.get("socio_id"))
        warnings: list[str] = []

        self.stdout.write(self.style.SUCCESS("Iniciando bootstrap demo publico orquestado."))
        self.stdout.write(
            f"- empresas={company_ids} | months={[item.text for item in months]} | showcase_month={showcase_month.text} | annual_year={annual_year}"
        )

        if not options["skip_seed_access"]:
            self._run_step(
                "seed_demo_access",
                warnings,
                strict,
                prefix="demo",
                password="demo12345",
                company_id=company_ids[0],
                socio_id=socio_id,
            )
            self._run_step(
                "bootstrap_demo_showcase_access",
                warnings,
                strict,
                username="demo-revisor",
                role_code="RevisorFiscalExterno",
                company_ids=company_ids,
            )

        self._run_step(
            "bootstrap_demo_operational_data",
            warnings,
            strict,
            months=[item.text for item in months],
            uf_values=[f"{uf_date.isoformat()}={value}" for uf_date, value in uf_values.items()],
            company_ids=company_ids,
        )

        monthly_flow_success = 0
        annual_flow_success = 0
        for company_id in company_ids:
            self._run_step(
                "bootstrap_demo_control_baseline",
                warnings,
                strict,
                company_id=company_id,
            )
            self._run_step(
                "bootstrap_demo_control_activity",
                warnings,
                strict,
                company_id=company_id,
                anio=showcase_month.year,
                mes=showcase_month.month,
                ensure_demo_sii_refs=True,
            )
            if self._run_step(
                "bootstrap_demo_tax_monthly_flow",
                warnings,
                strict,
                company_id=company_id,
                anio=showcase_month.year,
                mes=showcase_month.month,
            ):
                monthly_flow_success += 1
            if self._run_step(
                "bootstrap_demo_tax_annual_flow",
                warnings,
                strict,
                company_id=company_id,
                anio_tributario=annual_year,
            ):
                annual_flow_success += 1

        if not options["skip_compliance"]:
            self._run_step("bootstrap_demo_compliance_policies", warnings, strict)
            self._run_step(
                "bootstrap_demo_compliance_exports",
                warnings,
                strict,
                created_by=created_by,
                empresa_id=company_ids[0],
                socio_id=socio_id,
                anio=showcase_month.year,
                mes=showcase_month.month,
            )

        self.stdout.write(self.style.SUCCESS("Bootstrap demo publico completado."))
        self.stdout.write(
            f"- empresas_totales={len(company_ids)} | flujo_mensual_exitoso={monthly_flow_success} | flujo_anual_exitoso={annual_flow_success}"
        )
        if warnings:
            self.stdout.write(self.style.WARNING(f"- advertencias={len(warnings)}"))
            for warning in warnings:
                self.stdout.write(f"  * {warning}")

    def _resolve_company_ids(self, explicit_company_ids: list[int]) -> list[int]:
        if explicit_company_ids:
            found = list(Empresa.objects.filter(pk__in=explicit_company_ids).values_list("id", flat=True))
            missing = sorted(set(explicit_company_ids) - set(found))
            if missing:
                raise CommandError(f"Empresas inexistentes: {missing}")
            return sorted(found)

        active = list(Empresa.objects.filter(estado="activa").order_by("id").values_list("id", flat=True))
        if active:
            return active
        any_company = list(Empresa.objects.order_by("id").values_list("id", flat=True))
        if any_company:
            return any_company
        raise CommandError("No existen empresas para construir el showcase demo.")

    def _resolve_socio_id(self, explicit_socio_id: int | None) -> int:
        if explicit_socio_id is not None:
            if not Socio.objects.filter(pk=explicit_socio_id).exists():
                raise CommandError(f"El socio {explicit_socio_id} no existe.")
            return explicit_socio_id

        socio = Socio.objects.filter(activo=True).order_by("id").first() or Socio.objects.order_by("id").first()
        if socio is None:
            raise CommandError("No existe un socio para el export demo de Compliance.")
        return socio.id

    def _parse_month(self, raw_value: str) -> OperationalMonth:
        try:
            year_text, month_text = raw_value.split("-", 1)
            year = int(year_text)
            month = int(month_text)
        except ValueError as error:
            raise CommandError(f"Mes invalido: {raw_value}. Usa YYYY-MM.") from error
        if month < 1 or month > 12:
            raise CommandError(f"Mes invalido: {raw_value}.")
        return OperationalMonth(year=year, month=month)

    def _parse_months(self, raw_values: list[str]) -> list[OperationalMonth]:
        return [self._parse_month(raw_value) for raw_value in raw_values]

    def _build_uf_values(self, months: list[OperationalMonth], raw_values: list[str]) -> dict[date, Decimal]:
        values = {
            month.first_day: DEFAULT_UF_VALUES[month.first_day]
            for month in months
            if month.first_day in DEFAULT_UF_VALUES
        }
        for raw_value in raw_values:
            try:
                uf_date_text, uf_amount_text = raw_value.split("=", 1)
                uf_date = date.fromisoformat(uf_date_text)
                uf_amount = Decimal(uf_amount_text)
            except (ValueError, InvalidOperation) as error:
                raise CommandError(f"UF invalido: {raw_value}. Usa YYYY-MM-DD=VALOR.") from error
            values[uf_date] = uf_amount

        missing = [month.first_day.isoformat() for month in months if month.first_day not in values]
        if missing:
            raise CommandError(
                f"Faltan valores UF para {missing}. Pásalos con --uf YYYY-MM-DD=VALOR o agrega defaults explícitos."
            )
        return values

    def _run_step(self, command_name: str, warnings: list[str], strict: bool, **kwargs) -> bool:
        buffer = StringIO()
        try:
            call_command(command_name, stdout=buffer, stderr=buffer, **kwargs)
            output = buffer.getvalue().strip()
            self.stdout.write(self.style.HTTP_INFO(f"[ok] {command_name}"))
            if output:
                for line in output.splitlines():
                    self.stdout.write(f"    {line}")
            return True
        except Exception as error:  # noqa: BLE001
            message = f"{command_name}: {error}"
            if strict:
                raise CommandError(message) from error
            warnings.append(message)
            self.stdout.write(self.style.WARNING(f"[warn] {message}"))
            output = buffer.getvalue().strip()
            if output:
                for line in output.splitlines():
                    self.stdout.write(f"    {line}")
            return False
