from django.db.models import Q
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from contratos.models import Contrato
from core.scope_access import get_scope_access
from core.permissions import (
    AuditReadPermission,
    AuditResolutionPermission,
    AuditSnapshotPermission,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_REVIEWER,
    get_effective_role_codes,
)
from patrimonio.models import Propiedad
from .models import AuditEvent, ManualResolution
from .scope_filters import scope_manual_resolution_queryset
from .serializers import (
    AuditEventSerializer,
    ResolveChargeMovementSerializer,
    ManualResolutionSerializer,
    ResolveMigrationPropertyOwnerSerializer,
    ResolveUnknownIncomeSerializer,
)
from .services import resolve_migration_property_owner_manual_resolution
from conciliacion.services import resolve_charge_movement_manual_resolution, resolve_unknown_income_manual_resolution


def _scoped_manual_resolution_queryset(queryset, user):
    return scope_manual_resolution_queryset(queryset, get_scope_access(user))


def _scoped_audit_event_queryset(user):
    access = get_scope_access(user)
    queryset = AuditEvent.objects.select_related('actor_user')
    if not access.restricted:
        return queryset

    visible_contract_ids = set()
    visible_community_ids = set()
    if access.visible_property_ids:
        visible_contract_ids = set(
            Contrato.objects.filter(mandato_operacion__propiedad_id__in=access.visible_property_ids)
            .values_list('id', flat=True)
        )
        visible_community_ids = {
            comunidad_id
            for comunidad_id in Propiedad.objects.filter(pk__in=access.visible_property_ids)
            .exclude(comunidad_owner_id__isnull=True)
            .values_list('comunidad_owner_id', flat=True)
        }

    scoped_filter = Q(pk__in=[])
    for company_id in access.company_ids:
        scoped_filter |= Q(entity_type='empresa', entity_id=str(company_id))
        scoped_filter |= Q(metadata__empresa_id=company_id)
        scoped_filter |= Q(metadata__resolved_empresa_id=company_id)
    for property_id in access.visible_property_ids:
        scoped_filter |= Q(entity_type='propiedad', entity_id=str(property_id))
        scoped_filter |= Q(metadata__canonical_property_id=property_id)
    for community_id in visible_community_ids:
        scoped_filter |= Q(entity_type='comunidad', entity_id=str(community_id))
        scoped_filter |= Q(metadata__canonical_comunidad_id=community_id)
    for contract_id in visible_contract_ids:
        scoped_filter |= Q(entity_type='contrato', entity_id=str(contract_id))
        scoped_filter |= Q(metadata__contrato_id=contract_id)
        scoped_filter |= Q(metadata__resolved_contract_id=contract_id)
    for bank_id in access.visible_bank_account_ids:
        scoped_filter |= Q(entity_type='cuenta_recaudadora', entity_id=str(bank_id))
        scoped_filter |= Q(metadata__cuenta_recaudadora_id=bank_id)

    return queryset.filter(scoped_filter).distinct()


def _manual_resolution_queryset_for_user(user):
    return _scoped_manual_resolution_queryset(ManualResolution.objects.all(), user)


class AuditEventListView(generics.ListAPIView):
    permission_classes = [AuditReadPermission]
    serializer_class = AuditEventSerializer
    queryset = AuditEvent.objects.select_related('actor_user').all()[:100]

    def get_queryset(self):
        return _scoped_audit_event_queryset(self.request.user).order_by('-created_at')[:100]


class AuditSnapshotView(APIView):
    permission_classes = [AuditSnapshotPermission]

    def get(self, request):
        roles = get_effective_role_codes(request.user)
        can_read_events = bool(roles & {ROLE_ADMIN, ROLE_REVIEWER})
        can_read_resolutions = bool(roles & {ROLE_ADMIN, ROLE_OPERATOR})
        manual_resolutions = _manual_resolution_queryset_for_user(request.user).order_by('-created_at') if can_read_resolutions else []

        return Response(
            {
                'events': [
                    {
                        'id': item.id,
                        'actor_user_display': item.actor_user.display_name or item.actor_user.username if item.actor_user_id else (item.actor_identifier or 'Sistema'),
                        'event_type': item.event_type,
                        'severity': item.severity,
                        'entity_type': item.entity_type,
                        'entity_id': item.entity_id,
                        'summary': item.summary,
                        'created_at': item.created_at,
                    }
                    for item in (_scoped_audit_event_queryset(request.user).order_by('-created_at')[:100] if can_read_events else [])
                ],
                'manual_resolutions': [
                    {
                        'id': str(item.id),
                        'category': item.category,
                        'status': item.status,
                        'scope_type': item.scope_type,
                        'scope_reference': item.scope_reference,
                        'summary': item.summary,
                        'rationale': item.rationale,
                        'requested_by': item.requested_by_id,
                        'requested_by_display': item.requested_by.display_name or item.requested_by.username if item.requested_by_id else '',
                        'resolved_by': item.resolved_by_id,
                        'resolved_by_display': item.resolved_by.display_name or item.resolved_by.username if item.resolved_by_id else '',
                        'metadata': item.metadata,
                        'created_at': item.created_at,
                        'resolved_at': item.resolved_at,
                    }
                    for item in manual_resolutions
                ],
            }
        )


class ManualResolutionListCreateView(generics.ListCreateAPIView):
    permission_classes = [AuditResolutionPermission]
    serializer_class = ManualResolutionSerializer
    queryset = ManualResolution.objects.all()

    def get_queryset(self):
        queryset = _manual_resolution_queryset_for_user(self.request.user)
        status_value = self.request.query_params.get('status')
        category = self.request.query_params.get('category')
        scope_type = self.request.query_params.get('scope_type')
        scope_reference = self.request.query_params.get('scope_reference')

        if status_value:
            queryset = queryset.filter(status=status_value)
        if category:
            queryset = queryset.filter(category=category)
        if scope_type:
            queryset = queryset.filter(scope_type=scope_type)
        if scope_reference:
            queryset = queryset.filter(scope_reference=scope_reference)
        return queryset


class ManualResolutionDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [AuditResolutionPermission]
    serializer_class = ManualResolutionSerializer
    queryset = ManualResolution.objects.all()

    def get_queryset(self):
        return _manual_resolution_queryset_for_user(self.request.user)


class ResolveMigrationPropertyOwnerView(APIView):
    permission_classes = [AuditResolutionPermission]

    def post(self, request, pk):
        resolution = generics.get_object_or_404(_manual_resolution_queryset_for_user(request.user), pk=pk)
        serializer = ResolveMigrationPropertyOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = resolve_migration_property_owner_manual_resolution(
                resolution=resolution,
                nombre_comunidad=serializer.validated_data['nombre_comunidad'],
                representante_socio_id=serializer.validated_data.get('representante_socio_id'),
                representante_modo=serializer.validated_data.get('representante_modo'),
                participaciones=serializer.validated_data.get('participaciones'),
                region=serializer.validated_data.get('region', ''),
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'resolution_id': str(result['resolution'].pk),
                'comunidad_id': result['comunidad'].pk,
                'propiedad_id': result['propiedad'].pk,
            },
            status=status.HTTP_200_OK,
        )


class ResolveUnknownIncomeView(APIView):
    permission_classes = [AuditResolutionPermission]

    def post(self, request, pk):
        resolution = generics.get_object_or_404(_manual_resolution_queryset_for_user(request.user), pk=pk)
        serializer = ResolveUnknownIncomeSerializer(data=request.data, context={'request': request, 'resolution': resolution})
        serializer.is_valid(raise_exception=True)

        try:
            result = resolve_unknown_income_manual_resolution(
                resolution=resolution,
                payment=serializer.context['pago_mensual'],
                rationale=serializer.validated_data.get('rationale', ''),
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'resolution_id': str(result['resolution'].pk),
                'movimiento_bancario_id': result['movimiento'].pk,
                'pago_mensual_id': result['payment'].pk,
                'contrato_id': result['payment'].contrato_id,
            },
            status=status.HTTP_200_OK,
        )


class ResolveChargeMovementView(APIView):
    permission_classes = [AuditResolutionPermission]

    def post(self, request, pk):
        resolution = generics.get_object_or_404(_manual_resolution_queryset_for_user(request.user), pk=pk)
        serializer = ResolveChargeMovementSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            result = resolve_charge_movement_manual_resolution(
                resolution=resolution,
                rationale=serializer.validated_data.get('rationale', ''),
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'resolution_id': str(result['resolution'].pk),
                'movimiento_bancario_id': result['movimiento'].pk,
                'evento_contable_id': result['event'].pk,
                'empresa_id': result['empresa'].pk,
            },
            status=status.HTTP_200_OK,
        )
