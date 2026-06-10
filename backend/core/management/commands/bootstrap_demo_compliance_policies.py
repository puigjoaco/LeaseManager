from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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


def _policy_candidate(category, requires_hold, *, event_start, min_years):
    return PoliticaRetencionDatos(
        categoria_dato=category,
        evento_inicio=event_start,
        plazo_minimo_anos=min_years,
        permite_borrado_logico=True,
        permite_purga_fisica=False,
        requiere_hold=requires_hold,
        estado=EstadoRegistro.ACTIVE,
    )


def _validated_policy_candidates(*, event_start, min_years):
    candidates = []
    for category, requires_hold in DEFAULT_POLICIES:
        candidate = _policy_candidate(
            category,
            requires_hold,
            event_start=event_start,
            min_years=min_years,
        )
        try:
            candidate.full_clean()
        except ValidationError as error:
            invalid_fields = ", ".join(sorted(error.message_dict.keys()))
            raise CommandError(
                f"Politica de retencion demo invalida para categoria {candidate.categoria_dato}: "
                f"campos={invalid_fields}."
            ) from error
        candidates.append(candidate)
    return candidates


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
        candidates = _validated_policy_candidates(event_start=event_start, min_years=min_years)

        created = 0
        updated = 0
        with transaction.atomic():
            for candidate in candidates:
                _, was_created = PoliticaRetencionDatos.objects.update_or_create(
                    categoria_dato=candidate.categoria_dato,
                    defaults={
                        "evento_inicio": candidate.evento_inicio,
                        "plazo_minimo_anos": candidate.plazo_minimo_anos,
                        "permite_borrado_logico": candidate.permite_borrado_logico,
                        "permite_purga_fisica": candidate.permite_purga_fisica,
                        "requiere_hold": candidate.requiere_hold,
                        "estado": candidate.estado,
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(self.style.SUCCESS("Baseline demo de políticas de retención aplicado correctamente."))
        self.stdout.write(
            f"- políticas creadas={created} | políticas actualizadas={updated} | plazo={min_years} | evento_inicio_validado=true"
        )
