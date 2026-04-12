from __future__ import annotations

from django.db.models import Q, QuerySet

from core.scope_access import scope_queryset_for_user
from documentos.scope import scope_documento_queryset
from documentos.models import DocumentoEmitido

from .models import MensajeSaliente


def scope_mensaje_queryset(queryset: QuerySet[MensajeSaliente], user):
    contract_scoped = scope_queryset_for_user(
        queryset,
        user,
        property_paths=('contrato__mandato_operacion__propiedad_id', 'arrendatario__contratos__mandato_operacion__propiedad_id'),
        bank_account_paths=('contrato__mandato_operacion__cuenta_recaudadora_id', 'arrendatario__contratos__mandato_operacion__cuenta_recaudadora_id'),
    )
    visible_document_ids = list(scope_documento_queryset(DocumentoEmitido.objects.all(), user).values_list('id', flat=True))
    if not visible_document_ids:
        return contract_scoped.distinct()
    return queryset.filter(
        Q(pk__in=contract_scoped.values('pk')) | Q(documento_emitido_id__in=visible_document_ids)
    ).distinct()
