from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cobranza.models import PagoMensual, ValorUFDiario
from cobranza.services import calculate_monthly_amount, rebuild_account_state, sync_payment_distribution
from contratos.models import Arrendatario, Contrato


@dataclass(frozen=True)
class OperationalMonth:
    year: int
    month: int

    @property
    def month_start(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-01"


class Command(BaseCommand):
    help = (
        "Carga valores UF explicitos, genera pagos mensuales faltantes para contratos vigentes "
        "y recalcula estados de cuenta para dejar un entorno demo mas representativo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--month",
            action="append",
            dest="months",
            help="Mes operativo en formato YYYY-MM. Se puede repetir.",
        )
        parser.add_argument(
            "--uf",
            action="append",
            dest="uf_values",
            help="Valor UF explicito en formato YYYY-MM-DD=VALOR. Se puede repetir.",
        )
        parser.add_argument(
            "--company-id",
            action="append",
            type=int,
            dest="company_ids",
            help="Filtra contratos por empresa owner. Se puede repetir.",
        )
        parser.add_argument(
            "--skip-account-state-rebuild",
            action="store_true",
            help="No recalcula estados de cuenta al final.",
        )
        parser.add_argument(
            "--source-key",
            default="bootstrap_demo_operational_data",
            help="source_key para valores UF insertados o actualizados.",
        )

    def handle(self, *args, **options):
        months = self._parse_months(options.get("months") or [])
        if not months:
            raise CommandError("Debes indicar al menos un --month YYYY-MM.")

        uf_values = self._parse_uf_values(options.get("uf_values") or [])
        source_key = options["source_key"]
        company_ids = options.get("company_ids") or []
        skip_account_state_rebuild = options["skip_account_state_rebuild"]

        uf_created = 0
        uf_updated = 0
        for uf_date, uf_value in uf_values.items():
            _, created = ValorUFDiario.objects.update_or_create(
                fecha=uf_date,
                defaults={"valor": uf_value, "source_key": source_key},
            )
            if created:
                uf_created += 1
            else:
                uf_updated += 1

        contracts = self._get_contracts(company_ids)
        if not contracts:
            raise CommandError("No se encontraron contratos para el filtro indicado.")

        created_count = 0
        existing_count = 0
        errors: list[str] = []
        affected_arrendatario_ids: set[int] = set()

        for contract in contracts:
            affected_arrendatario_ids.add(contract.arrendatario_id)
            for operational_month in months:
                existing = PagoMensual.objects.filter(
                    contrato=contract,
                    anio=operational_month.year,
                    mes=operational_month.month,
                ).first()
                if existing:
                    existing_count += 1
                    continue

                try:
                    calculation = calculate_monthly_amount(
                        contract,
                        operational_month.year,
                        operational_month.month,
                    )
                except ValueError as error:
                    errors.append(
                        f"contrato {contract.id} {contract.codigo_contrato} {operational_month.year}-{operational_month.month:02d}: {error}"
                    )
                    continue

                with transaction.atomic():
                    payment = PagoMensual.objects.create(
                        contrato=contract,
                        periodo_contractual=calculation["periodo_contractual"],
                        mes=operational_month.month,
                        anio=operational_month.year,
                        monto_facturable_clp=calculation["monto_facturable_clp"],
                        monto_calculado_clp=calculation["monto_calculado_clp"],
                        fecha_vencimiento=calculation["fecha_vencimiento"],
                        codigo_conciliacion_efectivo=calculation["codigo_conciliacion_efectivo"],
                    )
                    sync_payment_distribution(payment)
                created_count += 1

        rebuilt_count = 0
        if not skip_account_state_rebuild:
            for arrendatario in Arrendatario.objects.filter(pk__in=affected_arrendatario_ids).order_by("id"):
                rebuild_account_state(arrendatario)
                rebuilt_count += 1

        self.stdout.write(self.style.SUCCESS("Bootstrap operacional demo completado."))
        self.stdout.write(
            f"- contratos considerados: {len(contracts)} | pagos creados: {created_count} | pagos existentes: {existing_count}"
        )
        self.stdout.write(f"- UF creados: {uf_created} | UF actualizados: {uf_updated}")
        self.stdout.write(f"- estados de cuenta recalculados: {rebuilt_count}")
        if errors:
            self.stdout.write(self.style.WARNING(f"- errores controlados: {len(errors)}"))
            for item in errors[:20]:
                self.stdout.write(f"  * {item}")

    def _get_contracts(self, company_ids: list[int]):
        queryset = Contrato.objects.select_related("arrendatario", "mandato_operacion").order_by("id")
        if company_ids:
            queryset = queryset.filter(mandato_operacion__propietario_empresa_owner_id__in=company_ids).distinct()
        return list(queryset)

    def _parse_months(self, raw_values: list[str]) -> list[OperationalMonth]:
        months: list[OperationalMonth] = []
        for raw_value in raw_values:
            try:
                year_text, month_text = raw_value.split("-", 1)
                year = int(year_text)
                month = int(month_text)
            except ValueError as error:
                raise CommandError(f"Mes invalido: {raw_value}. Usa YYYY-MM.") from error
            if month < 1 or month > 12:
                raise CommandError(f"Mes invalido: {raw_value}.")
            months.append(OperationalMonth(year=year, month=month))
        return months

    def _parse_uf_values(self, raw_values: list[str]) -> dict[date, Decimal]:
        values: dict[date, Decimal] = {}
        for raw_value in raw_values:
            try:
                uf_date_text, uf_amount_text = raw_value.split("=", 1)
            except ValueError as error:
                raise CommandError(f"UF invalido: {raw_value}. Usa YYYY-MM-DD=VALOR.") from error
            try:
                uf_date = date.fromisoformat(uf_date_text)
            except ValueError as error:
                raise CommandError(f"Fecha UF invalida: {raw_value}. Usa YYYY-MM-DD=VALOR.") from error
            try:
                uf_amount = Decimal(uf_amount_text)
            except InvalidOperation as error:
                raise CommandError(f"Valor UF invalido: {raw_value}.") from error
            values[uf_date] = uf_amount
        return values
