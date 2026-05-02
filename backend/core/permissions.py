from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission


ROLE_ADMIN = 'AdministradorGlobal'
ROLE_OPERATOR = 'OperadorDeCartera'
ROLE_PARTNER = 'Socio'
ROLE_REVIEWER = 'RevisorFiscalExterno'

ROLE_ALIASES = {
    'administradorglobal': ROLE_ADMIN,
    'operadordecartera': ROLE_OPERATOR,
    'operator': ROLE_OPERATOR,
    'socio': ROLE_PARTNER,
    'revisorfiscalexterno': ROLE_REVIEWER,
}


def normalize_role_code(role_code: str | None) -> str | None:
    if not role_code:
        return None
    normalized = str(role_code).strip()
    return ROLE_ALIASES.get(normalized.lower(), normalized)


def get_effective_role_codes(user) -> set[str]:
    role_codes: set[str] = set()
    default_role = normalize_role_code(getattr(user, 'default_role_code', ''))
    if default_role:
        role_codes.add(default_role)

    assignments = getattr(user, 'scope_assignments', None)
    if assignments is not None:
        for assignment in assignments.filter(effective_to__isnull=True).select_related('role'):
            normalized = normalize_role_code(getattr(assignment.role, 'code', ''))
            if normalized:
                role_codes.add(normalized)
    return role_codes


class RolePermission(BasePermission):
    read_roles: set[str] = set()
    write_roles: set[str] = set()

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, 'is_superuser', False):
            return True

        effective_roles = get_effective_role_codes(user)
        allowed_roles = self.read_roles if request.method in SAFE_METHODS else self.write_roles
        return bool(effective_roles & allowed_roles)


class OperationalModulePermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_OPERATOR}
    write_roles = {ROLE_ADMIN, ROLE_OPERATOR}


class OperationalReadAdminWritePermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_OPERATOR}
    write_roles = {ROLE_ADMIN}


class AuditReadPermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_REVIEWER}
    write_roles = set()


class AuditResolutionPermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_OPERATOR}
    write_roles = {ROLE_ADMIN, ROLE_OPERATOR}


class AuditSnapshotPermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_OPERATOR, ROLE_REVIEWER}
    write_roles = set()


class ControlModulePermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_REVIEWER}
    write_roles = {ROLE_ADMIN}


class ReportingPermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_REVIEWER}
    write_roles = set()


class PartnerOwnSummaryPermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_REVIEWER, ROLE_PARTNER}
    write_roles = set()

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        effective_roles = get_effective_role_codes(request.user)
        if ROLE_PARTNER not in effective_roles or effective_roles & {ROLE_ADMIN, ROLE_OPERATOR, ROLE_REVIEWER}:
            return True

        expected_socio_id = getattr(request.user, 'metadata', {}).get('socio_id')
        if expected_socio_id is None:
            return False
        return str(expected_socio_id) == str(view.kwargs.get('pk'))


class AdminOnlyPermission(RolePermission):
    read_roles = {ROLE_ADMIN}
    write_roles = {ROLE_ADMIN}


class OperationalOverviewPermission(RolePermission):
    read_roles = {ROLE_ADMIN, ROLE_OPERATOR}
    write_roles = set()
