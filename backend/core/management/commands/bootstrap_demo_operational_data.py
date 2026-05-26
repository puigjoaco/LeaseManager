from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from audit.services import create_audit_event
from cobranza.models import (
    CANONICAL_UF_SOURCE_KEYS,
    EFFECTIVE_CODE_APPLIED_EVENT_TYPE,
    MANUAL_UF_SOURCE_KEYS,
    PagoMensual,
    ValorUFDiario,
)
from cobranza.services import calculate_monthly_amount, rebuild_account_state, save_uf_value, sync_payment_distribution
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
            default="",
            help="Fuente UF canonica para valores UF insertados o actualizados.",
        )
        parser.add_argument(
            "--uf-evidence-ref",
            default="",
            help="Referencia no sensible de evidencia para cargas UF manuales.",
        )
        parser.add_argument(
            "--uf-motive",
            default="",
            help="Motivo auditable para cargas UF manuales.",
        )
        parser.add_argument(
            "--uf-responsible-ref",
            default="",
            help="Referencia no sensible al responsable de cargas UF manuales.",
        )

    def handle(self, *args, **options):
        months = self._parse_months(options.get("months") or [])
        if not months:
            raise CommandError("Debes indicar al menos un --month YYYY-MM.")

        uf_values = self._parse_uf_values(options.get("uf_values") or [])
        source_key = (options["source_key"] or "").strip()
        uf_evidence_ref = options["uf_evidence_ref"]
        uf_motive = options["uf_motive"]
        uf_responsible_ref = options["uf_responsible_ref"]
        if uf_values and not source_key:
            raise CommandError(
                "La carga UF requiere --source-key con UF.BancoCentral, UF.CMF, "
                "UF.MiIndicador o UF.CargaManualExtraordinaria."
            )
        if source_key and source_key not in CANONICAL_UF_SOURCE_KEYS:
            raise CommandError(
                "source_key UF invalido. Usa UF.BancoCentral, UF.CMF, "
                "UF.MiIndicador o UF.CargaManualExtraordinaria."
            )
        if uf_values and source_key in MANUAL_UF_SOURCE_KEYS and not all([uf_evidence_ref, uf_motive, uf_responsible_ref]):
            raise CommandError(
                "La carga manual UF requiere --uf-evidence-ref, --uf-motive y --uf-responsible-ref."
            )
        company_ids = options.get("company_ids") or []
        skip_account_state_rebuild = options["skip_account_state_rebuild"]

        uf_created = 0
        uf_updated = 0
        for uf_date, uf_value in uf_values.items():
            uf_record = ValorUFDiario.objects.filter(fecha=uf_date).first()
            created = uf_record is None
            try:
                save_uf_value(
                    uf_value=uf_record,
                    validated_data={
                        'fecha': uf_date,
                        'valor': uf_value,
                        'source_key': source_key,
                        'evidencia_ref': uf_evidence_ref,
                        'motivo_carga': uf_motive,
                        'responsable_ref': uf_responsible_ref,
                    },
                    actor_identifier='bootstrap_demo_operational_data',
                )
            except (ValidationError, ValueError) as error:
                raise CommandError(f"Valor UF invalido para {uf_date}: {error}") from error
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
                        monto_efecto_codigo_efectivo_clp=calculation["monto_efecto_codigo_efectivo_clp"],
                        fecha_vencimiento=calculation["fecha_vencimiento"],
                        codigo_conciliacion_efectivo=calculation["codigo_conciliacion_efectivo"],
                    )
                    sync_payment_distribution(payment)
                    self._create_effective_code_audit_event(payment)
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

    def _create_effective_code_audit_event(self, payment: PagoMensual) -> None:
        effect = payment.monto_efecto_codigo_efectivo_clp
        if not effect:
            return
        create_audit_event(
            event_type=EFFECTIVE_CODE_APPLIED_EVENT_TYPE,
            entity_type='pago_mensual',
            entity_id=str(payment.pk),
            summary=f'Codigo efectivo aplicado a pago {payment.anio}-{payment.mes:02d}',
            actor_identifier='bootstrap_demo_operational_data',
            metadata={
                'contrato_id': payment.contrato_id,
                'anio': payment.anio,
                'mes': payment.mes,
                'codigo_conciliacion_efectivo': payment.codigo_conciliacion_efectivo,
                'monto_facturable_clp': self._format_clp_amount(payment.monto_facturable_clp),
                'monto_calculado_clp': self._format_clp_amount(payment.monto_calculado_clp),
                'monto_efecto_codigo_efectivo_clp': self._format_clp_amount(effect),
            },
        )

    def _format_clp_amount(self, value: Decimal) -> str:
        return f'{Decimal(value):.2f}'
