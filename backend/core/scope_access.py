from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cached_property

from django.db.models import Q, QuerySet
from rest_framework.exceptions import PermissionDenied

from operacion.models import CuentaRecaudadora, MandatoOperacion
from patrimonio.models import Propiedad

from .models import Scope
from .permissions import ROLE_ADMIN, get_effective_role_codes


SCOPE_CODE_PATTERNS = {
    Scope.ScopeType.COMPANY: re.compile(r'^company-(?P<object_id>\d+)$'),
    Scope.ScopeType.PROPERTY: re.compile(r'^property-(?P<object_id>\d+)$'),
    Scope.ScopeType.BANK_ACCOUNT: re.compile(r'^bank-account-(?P<object_id>\d+)$'),
}


def _coerce_scope_identifier(scope: Scope) -> int | None:
    candidates = [
        scope.external_reference,
        scope.metadata.get('id') if isinstance(scope.metadata, dict) else None,
        scope.metadata.get('object_id') if isinstance(scope.metadata, dict) else None,
    ]
    for candidate in candidates:
        if candidate in (None, ''):
            continue
        try:
            return int(candidate)
        except (TypeError, ValueError):
            continue

    pattern = SCOPE_CODE_PATTERNS.get(scope.scope_type)
    if pattern is None:
        return None
    match = pattern.fullmatch(scope.code or '')
    if match is None:
        return None
    return int(match.group('object_id'))


@dataclass
class ScopeAccess:
    restricted: bool
    company_ids: set[int]
    property_ids: set[int]
    bank_account_ids: set[int]

    @cached_property
    def visible_property_ids(self) -> set[int]:
        visible_ids = set(self.property_ids)
        if self.company_ids:
            visible_ids.update(
                Propiedad.objects.filter(
                    Q(empresa_owner_id__in=self.company_ids)
                    | Q(comunidad_owner__participaciones__participante_empresa_id__in=self.company_ids)
                    | Q(mandatos_operacion__administrador_empresa_owner_id__in=self.company_ids)
                    | Q(mandatos_operacion__recaudador_empresa_owner_id__in=self.company_ids)
                    | Q(mandatos_operacion__entidad_facturadora_id__in=self.company_ids)
                )
                .distinct()
                .values_list('id', flat=True)
            )
        if self.bank_account_ids:
            visible_ids.update(
                Propiedad.objects.filter(mandatos_operacion__cuenta_recaudadora_id__in=self.bank_account_ids)
                .distinct()
                .values_list('id', flat=True)
            )
        return visible_ids

    @cached_property
    def visible_bank_account_ids(self) -> set[int]:
        visible_ids = set(self.bank_account_ids)
        if self.company_ids:
            visible_ids.update(
                CuentaRecaudadora.objects.filter(empresa_owner_id__in=self.company_ids).values_list('id', flat=True)
            )
        if self.visible_property_ids:
            visible_ids.update(
                MandatoOperacion.objects.filter(propiedad_id__in=self.visible_property_ids).values_list(
                    'cuenta_recaudadora_id', flat=True
                )
            )
        return visible_ids


def get_scope_access(user) -> ScopeAccess:
    if not user or not getattr(user, 'is_authenticated', False):
        return ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    effective_roles = get_effective_role_codes(user)
    if getattr(user, 'is_superuser', False) or ROLE_ADMIN in effective_roles:
        return ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    assignments = list(user.scope_assignments.filter(effective_to__isnull=True).select_related('scope'))
    if not assignments:
        return ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    scoped_assignments = [assignment for assignment in assignments if assignment.scope_id]
    if not scoped_assignments:
        return ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    if any(assignment.scope_id is None for assignment in assignments):
        return ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    if any(assignment.scope.scope_type == Scope.ScopeType.GLOBAL for assignment in scoped_assignments):
        return ScopeAccess(restricted=False, company_ids=set(), property_ids=set(), bank_account_ids=set())

    company_ids: set[int] = set()
    property_ids: set[int] = set()
    bank_account_ids: set[int] = set()

    for assignment in scoped_assignments:
        scope = assignment.scope
        scope_id = _coerce_scope_identifier(scope)
        if scope_id is None:
            continue
        if scope.scope_type == Scope.ScopeType.COMPANY:
            company_ids.add(scope_id)
        elif scope.scope_type == Scope.ScopeType.PROPERTY:
            property_ids.add(scope_id)
        elif scope.scope_type == Scope.ScopeType.BANK_ACCOUNT:
            bank_account_ids.add(scope_id)

    return ScopeAccess(
        restricted=True,
        company_ids=company_ids,
        property_ids=property_ids,
        bank_account_ids=bank_account_ids,
    )


def scope_queryset_for_access(
    queryset: QuerySet,
    access: ScopeAccess,
    *,
    company_paths: tuple[str, ...] = (),
    property_paths: tuple[str, ...] = (),
    bank_account_paths: tuple[str, ...] = (),
) -> QuerySet:
    if not access.restricted:
        return queryset

    scope_filter = Q()
    if company_paths and access.company_ids:
        for path in company_paths:
            scope_filter |= Q(**{f'{path}__in': access.company_ids})

    if property_paths and access.visible_property_ids:
        for path in property_paths:
            scope_filter |= Q(**{f'{path}__in': access.visible_property_ids})

    if bank_account_paths and access.visible_bank_account_ids:
        for path in bank_account_paths:
            scope_filter |= Q(**{f'{path}__in': access.visible_bank_account_ids})

    if not scope_filter:
        return queryset.none()

    return queryset.filter(scope_filter).distinct()


def scope_queryset_for_user(
    queryset: QuerySet,
    user,
    *,
    company_paths: tuple[str, ...] = (),
    property_paths: tuple[str, ...] = (),
    bank_account_paths: tuple[str, ...] = (),
) -> QuerySet:
    return scope_queryset_for_access(
        queryset,
        get_scope_access(user),
        company_paths=company_paths,
        property_paths=property_paths,
        bank_account_paths=bank_account_paths,
    )


def ensure_queryset_scope(
    queryset: QuerySet,
    user,
    *,
    company_paths: tuple[str, ...] = (),
    property_paths: tuple[str, ...] = (),
    bank_account_paths: tuple[str, ...] = (),
) -> None:
    scoped_queryset = scope_queryset_for_user(
        queryset,
        user,
        company_paths=company_paths,
        property_paths=property_paths,
        bank_account_paths=bank_account_paths,
    )
    if not scoped_queryset.exists():
        raise PermissionDenied('El recurso solicitado queda fuera del scope asignado para este usuario.')


class ScopedQuerysetMixin:
    company_scope_paths: tuple[str, ...] = ()
    property_scope_paths: tuple[str, ...] = ()
    bank_account_scope_paths: tuple[str, ...] = ()

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_queryset_for_user(
            queryset,
            self.request.user,
            company_paths=self.company_scope_paths,
            property_paths=self.property_scope_paths,
            bank_account_paths=self.bank_account_scope_paths,
        )
