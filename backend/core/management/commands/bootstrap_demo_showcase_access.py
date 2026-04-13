from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Role, RoleScope, Scope, UserScopeAssignment
from patrimonio.models import Empresa
from users.models import User


DEFAULT_USERNAME = "demo-revisor"
DEFAULT_ROLE_CODE = "RevisorFiscalExterno"


class Command(BaseCommand):
    help = (
        "Amplía el scope del usuario demo de showcase sin cambiar su rol: "
        "agrega scopes de empresa adicionales para que un perfil read-only pueda ver más cartera."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=DEFAULT_USERNAME,
            help=f"Usuario demo objetivo. Default: {DEFAULT_USERNAME}",
        )
        parser.add_argument(
            "--role-code",
            default=DEFAULT_ROLE_CODE,
            help=f"Rol esperado del usuario demo. Default: {DEFAULT_ROLE_CODE}",
        )
        parser.add_argument(
            "--company-id",
            action="append",
            type=int,
            dest="company_ids",
            help="Empresa a agregar al scope. Se puede repetir. Default: todas las activas.",
        )
    def handle(self, *args, **options):
        username = options["username"].strip()
        role_code = options["role_code"].strip()
        if not username:
            raise CommandError("username no puede venir vacío.")
        if not role_code:
            raise CommandError("role-code no puede venir vacío.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as error:
            raise CommandError(f"El usuario {username} no existe.") from error

        try:
            role = Role.objects.get(code=role_code)
        except Role.DoesNotExist as error:
            raise CommandError(f"El rol {role_code} no existe.") from error

        company_ids = self._resolve_company_ids(options.get("company_ids") or [])
        created = 0
        reused = 0

        for index, company in enumerate(Empresa.objects.filter(pk__in=company_ids).order_by("id")):
            scope, _ = Scope.objects.update_or_create(
                code=f"company-{company.pk}",
                defaults={
                    "name": f"Empresa {company.razon_social}",
                    "scope_type": Scope.ScopeType.COMPANY,
                    "external_reference": str(company.pk),
                    "metadata": {
                        "seed_source": "bootstrap_demo_showcase_access",
                        "model": "Empresa",
                        "label": company.razon_social,
                    },
                    "is_active": True,
                },
            )
            RoleScope.objects.update_or_create(
                role=role,
                scope=scope,
                defaults={"permission_set": ["read"]},
            )
            assignment, assignment_created = UserScopeAssignment.objects.get_or_create(
                user=user,
                role=role,
                scope=scope,
                defaults={
                    "is_primary": index == 0,
                    "metadata": {"seed_source": "bootstrap_demo_showcase_access"},
                    "effective_to": None,
                },
            )
            if assignment_created:
                created += 1
            else:
                reused += 1
            assignment.effective_to = None
            assignment.metadata = {"seed_source": "bootstrap_demo_showcase_access"}
            assignment.is_primary = index == 0
            assignment.save(update_fields=["effective_to", "metadata", "is_primary"])

        UserScopeAssignment.objects.filter(
            user=user,
            role=role,
            effective_to__isnull=True,
        ).exclude(scope__code__in=[f"company-{company_id}" for company_id in company_ids]).update(
            effective_to=timezone.now(),
            is_primary=False,
        )

        self.stdout.write(self.style.SUCCESS("Scope de showcase aplicado correctamente."))
        self.stdout.write(
            f"- user={user.username} | role={role.code} | company_ids={company_ids} | created={created} | reused={reused}"
        )

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
        raise CommandError("No existen empresas para ampliar el scope de showcase.")
