from __future__ import annotations

from django.db.models import Q, QuerySet

from canales.models import MensajeSaliente
from conciliacion.models import MovimientoBancarioImportado
from core.scope_access import ScopeAccess, scope_queryset_for_access
from patrimonio.models import Propiedad


CONCILIACION_MANUAL_RESOLUTION_CATEGORIES = (
    'conciliacion.ingreso_desconocido',
    'conciliacion.movimiento_cargo',
)


def scope_manual_resolution_queryset(queryset: QuerySet, access: ScopeAccess) -> QuerySet:
    queryset = queryset.select_related('requested_by', 'resolved_by')
    if not access.restricted:
        return queryset

    scoped_filter = Q(pk__in=[])

    visible_movement_ids = scope_queryset_for_access(
        MovimientoBancarioImportado.objects.all(),
        access,
        company_paths=('conexion_bancaria__cuenta_recaudadora__empresa_owner_id',),
        property_paths=('pago_mensual__contrato__mandato_operacion__propiedad_id',),
        bank_account_paths=('conexion_bancaria__cuenta_recaudadora_id',),
    ).values_list('pk', flat=True)
    visible_movement_refs = [str(item) for item in visible_movement_ids]
    if visible_movement_refs:
        scoped_filter |= Q(
            category__in=CONCILIACION_MANUAL_RESOLUTION_CATEGORIES,
            scope_type='movimiento_bancario',
            scope_reference__in=visible_movement_refs,
        )

    visible_message_ids = scope_queryset_for_access(
        MensajeSaliente.objects.all(),
        access,
        property_paths=(
            'contrato__mandato_operacion__propiedad_id',
            'arrendatario__contratos__mandato_operacion__propiedad_id',
        ),
    ).values_list('pk', flat=True)
    visible_message_refs = [str(item) for item in visible_message_ids]
    if visible_message_refs:
        scoped_filter |= Q(
            category__startswith='canales.',
            scope_type='canales',
            scope_reference__in=visible_message_refs,
        )

    migration_property_by_resolution_id = {}
    for resolution in queryset.filter(category__startswith='migration.'):
        metadata = resolution.metadata or {}
        property_id = metadata.get('resolved_canonical_property_id')
        if property_id in (None, ''):
            continue
        try:
            migration_property_by_resolution_id[resolution.pk] = int(property_id)
        except (TypeError, ValueError):
            continue

    if migration_property_by_resolution_id:
        visible_property_ids = set(
            scope_queryset_for_access(
                Propiedad.objects.filter(pk__in=set(migration_property_by_resolution_id.values())),
                access,
                property_paths=('id',),
            ).values_list('pk', flat=True)
        )
        visible_migration_resolution_ids = [
            resolution_id
            for resolution_id, property_id in migration_property_by_resolution_id.items()
            if property_id in visible_property_ids
        ]
        if visible_migration_resolution_ids:
            scoped_filter |= Q(pk__in=visible_migration_resolution_ids)

    return queryset.filter(scoped_filter).distinct()
