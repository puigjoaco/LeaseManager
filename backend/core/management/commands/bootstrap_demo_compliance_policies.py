from __future__ import annotations

from django.core.management.base import BaseCommand

from compliance.models import CategoriaDato, EstadoRegistro, PoliticaRetencionDatos


DEFAULT_EVENT_START = "ultimo_evento_relevante"
DEFAULT_MIN_YEARS = 6

# Keep the demo seed aligned with the compliance API tests and the PRD minimum.
DEFAULT_POLICIES = (
    (CategoriaDato.OPERATIONAL, False),
    (CategoriaDato.FINANCIAL, False),
    (CategoriaDato.TAX, True),
    (CategoriaDato.DOCUMENT, True),
    (CategoriaDato.SECRET, False),
)


class Command(BaseCommand):
    help = (
        "Crea o actualiza un baseline demo reproducible de PoliticaRetencionDatos "
        "para que Compliance no dependa de carga manual."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--event-start",
            default=DEFAULT_EVENT_START,
            help=f"Evento de inicio para todas las políticas. Default: {DEFAULT_EVENT_START}",
        )
        parser.add_argument(
            "--min-years",
            type=int,
            default=DEFAULT_MIN_YEARS,
            help=f"Plazo mínimo en años para todas las políticas. Default: {DEFAULT_MIN_YEARS}",
        )

    def handle(self, *args, **options):
        event_start = options["event_start"].strip()
        min_years = options["min_years"]

        created = 0
        updated = 0
        for category, requires_hold in DEFAULT_POLICIES:
            _, was_created = PoliticaRetencionDatos.objects.update_or_create(
                categoria_dato=category,
                defaults={
                    "evento_inicio": event_start,
                    "plazo_minimo_anos": min_years,
                    "permite_borrado_logico": True,
                    "permite_purga_fisica": False,
                    "requiere_hold": requires_hold,
                    "estado": EstadoRegistro.ACTIVE,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS("Baseline demo de políticas de retención aplicado correctamente."))
        self.stdout.write(
            f"- políticas creadas={created} | políticas actualizadas={updated} | plazo={min_years} | evento_inicio={event_start}"
        )
