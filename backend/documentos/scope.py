from __future__ import annotations

from django.db.models import Q, QuerySet

from contratos.models import Contrato
from core.scope_access import get_scope_access
from operacion.models import MandatoOperacion

from .models import DocumentoEmitido, ExpedienteDocumental


def _visible_mandato_ids(user) -> set[int]:
    access = get_scope_access(user)
    if not access.restricted:
        return set(MandatoOperacion.objects.values_list('id', flat=True))

    filters = Q()
    if access.visible_property_ids:
        filters |= Q(propiedad_id__in=access.visible_property_ids)
    if access.visible_bank_account_ids:
        filters |= Q(cuenta_recaudadora_id__in=access.visible_bank_account_ids)
    if not filters:
        return set()
    return set(MandatoOperacion.objects.filter(filters).values_list('id', flat=True).distinct())


def _visible_contrato_ids(user) -> set[int]:
    access = get_scope_access(user)
    if not access.restricted:
        return set(Contrato.objects.values_list('id', flat=True))

    filters = Q()
    if access.visible_property_ids:
        filters |= Q(mandato_operacion__propiedad_id__in=access.visible_property_ids)
    if access.visible_bank_account_ids:
        filters |= Q(mandato_operacion__cuenta_recaudadora_id__in=access.visible_bank_account_ids)
    if not filters:
        return set()
    return set(Contrato.objects.filter(filters).values_list('id', flat=True).distinct())


def scope_expediente_queryset(queryset: QuerySet[ExpedienteDocumental], user):
    access = get_scope_access(user)
    if not access.restricted:
        return queryset

    contrato_ids = _visible_contrato_ids(user)
    mandato_ids = _visible_mandato_ids(user)
    mandato_tokens = [f'mandato:{item}' for item in mandato_ids]

    scope_filter = Q()
    if contrato_ids:
        contract_filter = Q(entidad_tipo='contrato', entidad_id__in=[str(item) for item in contrato_ids])
        if mandato_tokens:
            contract_filter &= Q(owner_operativo__in=mandato_tokens) | ~Q(owner_operativo__startswith='mandato:')
        else:
            contract_filter &= ~Q(owner_operativo__startswith='mandato:')
        scope_filter |= contract_filter
    if mandato_tokens:
        scope_filter |= ~Q(entidad_tipo='contrato') & Q(owner_operativo__in=mandato_tokens)

    if not scope_filter:
        return queryset.none()

    return queryset.filter(scope_filter).distinct()


def scope_documento_queryset(queryset: QuerySet[DocumentoEmitido], user):
    scoped_expedientes = scope_expediente_queryset(ExpedienteDocumental.objects.all(), user)
    return queryset.filter(expediente__in=scoped_expedientes).distinct()
