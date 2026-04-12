from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from compliance.models import ExportacionSensible, EstadoExportacionSensible
from compliance.services import prepare_sensitive_export, render_export_payload


@dataclass(frozen=True)
class ExportPlan:
    categoria_dato: str
    export_kind: str
    scope_resumen: dict
    motivo: str
    hold_activo: bool


class Command(BaseCommand):
    help = (
        "Prepara exportaciones sensibles demo a partir de dashboard/reporting ya existente, "
        "evitando duplicados activos con el mismo tipo y scope."
    )

    def add_arguments(self, parser):
        parser.add_argument("--created-by", default="demo-admin", help="Usuario creador de las exportaciones.")
        parser.add_argument("--empresa-id", type=int, default=1, help="Empresa para export financiero. Default: 1")
        parser.add_argument("--socio-id", type=int, default=3, help="Socio para export de resumen. Default: 3")
        parser.add_argument("--anio", type=int, default=2026, help="Año financiero. Default: 2026")
        parser.add_argument("--mes", type=int, default=5, help="Mes financiero. Default: 5")

    def handle(self, *args, **options):
        username = options["created_by"]
        empresa_id = options["empresa_id"]
        socio_id = options["socio_id"]
        anio = options["anio"]
        mes = options["mes"]

        user_model = get_user_model()
        try:
            created_by = user_model.objects.get(username=username)
        except user_model.DoesNotExist as error:
            raise CommandError(f"El usuario {username} no existe.") from error

        plans = [
            ExportPlan(
                categoria_dato="operativo",
                export_kind="dashboard_operativo",
                scope_resumen={},
                motivo="Bootstrap demo dashboard",
                hold_activo=False,
            ),
            ExportPlan(
                categoria_dato="financiero",
                export_kind="financiero_mensual",
                scope_resumen={"anio": anio, "mes": mes, "empresa_id": empresa_id},
                motivo="Bootstrap demo public financial month",
                hold_activo=False,
            ),
            ExportPlan(
                categoria_dato="documental_sensible",
                export_kind="socio_resumen",
                scope_resumen={"socio_id": socio_id},
                motivo="Bootstrap demo socio summary",
                hold_activo=True,
            ),
        ]

        created = 0
        skipped = 0
        for plan in plans:
            existing = ExportacionSensible.objects.filter(
                export_kind=plan.export_kind,
                categoria_dato=plan.categoria_dato,
                scope_resumen=plan.scope_resumen,
                estado=EstadoExportacionSensible.PREPARED,
            ).first()
            if existing is not None:
                skipped += 1
                self.stdout.write(
                    f"- skip {plan.export_kind} {plan.scope_resumen} -> export {existing.id} ya preparada"
                )
                continue

            payload = render_export_payload(plan.export_kind, plan.scope_resumen)
            export = prepare_sensitive_export(
                categoria_dato=plan.categoria_dato,
                export_kind=plan.export_kind,
                scope_resumen=plan.scope_resumen,
                motivo=plan.motivo,
                payload=payload,
                created_by=created_by,
                hold_activo=plan.hold_activo,
            )
            created += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"- created export {export.id} {plan.export_kind} {plan.scope_resumen}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Bootstrap de exportaciones demo completado. created={created} skipped={skipped}"
            )
        )
