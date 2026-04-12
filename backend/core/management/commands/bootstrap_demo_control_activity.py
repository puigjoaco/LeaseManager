from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from contabilidad.models import CierreMensualContable, EstadoCierreMensual, EventoContable
from contabilidad.services import (
    create_accounting_event,
    approve_monthly_close,
    prepare_monthly_close,
)
from patrimonio.models import Empresa
from sii.models import CapacidadSII
from sii.services import generate_f29_draft


DEFAULT_AMOUNT = "100000.00"
DEFAULT_EVENT_TYPE = "PagoConciliadoArriendo"
DEFAULT_ORIGIN_TYPE = "manual_demo"


class Command(BaseCommand):
    help = (
        "Crea actividad demo reproducible para Contabilidad/SII en un periodo mensual: "
        "evento contable, cierre mensual y borrador F29 cuando la capacidad lo permite."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True, help="Empresa objetivo.")
        parser.add_argument("--anio", type=int, required=True, help="Año del periodo.")
        parser.add_argument("--mes", type=int, required=True, help="Mes del periodo.")
        parser.add_argument(
            "--amount",
            default=DEFAULT_AMOUNT,
            help=f"Monto base CLP para el evento demo. Default: {DEFAULT_AMOUNT}",
        )
        parser.add_argument(
            "--event-type",
            default=DEFAULT_EVENT_TYPE,
            help=f"Tipo de evento contable. Default: {DEFAULT_EVENT_TYPE}",
        )
        parser.add_argument(
            "--origin-type",
            default=DEFAULT_ORIGIN_TYPE,
            help=f"Entidad origen para el evento demo. Default: {DEFAULT_ORIGIN_TYPE}",
        )
        parser.add_argument(
            "--origin-id",
            default="",
            help="Entidad origen id para el evento demo. Default: YYYY-MM de la corrida.",
        )
        parser.add_argument(
            "--currency",
            default="CLP",
            help="Moneda del evento demo. Default: CLP",
        )
        parser.add_argument(
            "--ensure-demo-sii-refs",
            action="store_true",
            help="Completa certificado_ref demo para capacidades SII vacías antes de generar F29.",
        )

    def handle(self, *args, **options):
        empresa = self._get_company(options["company_id"])
        anio = options["anio"]
        mes = options["mes"]
        if mes < 1 or mes > 12:
            raise CommandError("mes debe estar entre 1 y 12.")

        amount = self._parse_amount(options["amount"])
        event_type = options["event_type"].strip() or DEFAULT_EVENT_TYPE
        origin_type = options["origin_type"].strip() or DEFAULT_ORIGIN_TYPE
        origin_id = options["origin_id"].strip() or f"{anio:04d}-{mes:02d}"
        currency = options["currency"].strip() or "CLP"
        ensure_demo_sii_refs = options["ensure_demo_sii_refs"]

        event_key = f"bootstrap_demo_control_activity:{empresa.pk}:{anio:04d}-{mes:02d}:{event_type}"
        event, event_created = create_accounting_event(
            empresa=empresa,
            evento_tipo=event_type,
            entidad_origen_tipo=origin_type,
            entidad_origen_id=origin_id,
            fecha_operativa=date(anio, mes, 10),
            moneda=currency,
            monto_base=amount,
            payload_resumen={
                "seed_source": "bootstrap_demo_control_activity",
                "demo": True,
                "periodo": f"{anio:04d}-{mes:02d}",
            },
            idempotency_key=event_key,
        )

        close = self._prepare_or_reuse_close(empresa=empresa, anio=anio, mes=mes)
        close_approved = False
        if close.estado == EstadoCierreMensual.PREPARED:
            close = approve_monthly_close(close)
            close_approved = True

        capability_updates = 0
        if ensure_demo_sii_refs:
            capability_updates = self._ensure_demo_sii_refs(empresa)

        f29 = None
        f29_created = False
        f29_warning = None
        try:
            f29, f29_created = generate_f29_draft(empresa, anio, mes)
        except ValueError as error:
            f29_warning = str(error)

        self.stdout.write(self.style.SUCCESS("Bootstrap demo de actividad de control aplicado correctamente."))
        self.stdout.write(
            f"- empresa={empresa.id} | periodo={anio:04d}-{mes:02d} | evento={event.id} | evento_creado={event_created} | estado_evento={event.estado_contable}"
        )
        self.stdout.write(
            f"- cierre={close.id} | estado_cierre={close.estado} | cierre_aprobado_en_esta_corrida={close_approved}"
        )
        if ensure_demo_sii_refs:
            self.stdout.write(f"- capacidades_sii_actualizadas={capability_updates}")
        if f29 is not None:
            self.stdout.write(
                f"- f29={f29.id} | f29_creado={f29_created} | estado_preparacion={f29.estado_preparacion}"
            )
        if f29_warning:
            self.stdout.write(self.style.WARNING(f"- F29 no generado: {f29_warning}"))

    def _get_company(self, company_id: int) -> Empresa:
        try:
            return Empresa.objects.get(pk=company_id)
        except Empresa.DoesNotExist as error:
            raise CommandError(f"La empresa {company_id} no existe.") from error

    def _parse_amount(self, raw_amount: str) -> Decimal:
        try:
            return Decimal(raw_amount)
        except InvalidOperation as error:
            raise CommandError(f"Monto invalido: {raw_amount}") from error

    def _prepare_or_reuse_close(self, *, empresa: Empresa, anio: int, mes: int) -> CierreMensualContable:
        close = CierreMensualContable.objects.filter(empresa=empresa, anio=anio, mes=mes).first()
        if close and close.estado in {EstadoCierreMensual.APPROVED, EstadoCierreMensual.REOPENED}:
            return close
        return prepare_monthly_close(empresa, anio, mes)

    def _ensure_demo_sii_refs(self, empresa: Empresa) -> int:
        updated = 0
        for capability in empresa.capacidades_sii.filter(
            capacidad_key__in=[
                CapacidadSII.DTE_EMISION,
                CapacidadSII.F29_PREPARACION,
                CapacidadSII.DDJJ_PREPARACION,
                CapacidadSII.F22_PREPARACION,
            ]
        ):
            if capability.certificado_ref:
                continue
            capability.certificado_ref = f"demo-cert-{capability.capacidad_key.lower()}-{empresa.pk}"
            capability.save(update_fields=["certificado_ref", "updated_at"])
            updated += 1
        return updated
