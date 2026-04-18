from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import (
    AuditReadPermission,
    AuditResolutionPermission,
    AuditSnapshotPermission,
    ROLE_ADMIN,
    ROLE_OPERATOR,
    ROLE_REVIEWER,
    get_effective_role_codes,
)
from .models import AuditEvent, ManualResolution
from .serializers import (
    AuditEventSerializer,
    ResolveChargeMovementSerializer,
    ManualResolutionSerializer,
    ResolveMigrationPropertyOwnerSerializer,
    ResolveUnknownIncomeSerializer,
)
from .services import resolve_migration_property_owner_manual_resolution
from conciliacion.services import resolve_charge_movement_manual_resolution, resolve_unknown_income_manual_resolution


class AuditEventListView(generics.ListAPIView):
    permission_classes = [AuditReadPermission]
    serializer_class = AuditEventSerializer
    queryset = AuditEvent.objects.select_related('actor_user').all()[:100]


class AuditSnapshotView(APIView):
    permission_classes = [AuditSnapshotPermission]

    def get(self, request):
        roles = get_effective_role_codes(request.user)
        can_read_events = bool(roles & {ROLE_ADMIN, ROLE_REVIEWER})
        can_read_resolutions = bool(roles & {ROLE_ADMIN, ROLE_OPERATOR})

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
                    for item in (AuditEvent.objects.select_related('actor_user').order_by('-created_at')[:100] if can_read_events else [])
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
                    for item in (ManualResolution.objects.order_by('-created_at') if can_read_resolutions else [])
                ],
            }
        )


class ManualResolutionListCreateView(generics.ListCreateAPIView):
    permission_classes = [AuditResolutionPermission]
    serializer_class = ManualResolutionSerializer
    queryset = ManualResolution.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
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


class ResolveMigrationPropertyOwnerView(APIView):
    permission_classes = [AuditResolutionPermission]

    def post(self, request, pk):
        resolution = generics.get_object_or_404(ManualResolution, pk=pk)
        serializer = ResolveMigrationPropertyOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = resolve_migration_property_owner_manual_resolution(
                resolution=resolution,
                nombre_comunidad=serializer.validated_data['nombre_comunidad'],
                representante_socio_id=serializer.validated_data['representante_socio_id'],
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
        resolution = generics.get_object_or_404(ManualResolution, pk=pk)
        serializer = ResolveUnknownIncomeSerializer(data=request.data, context={'request': request})
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
        resolution = generics.get_object_or_404(ManualResolution, pk=pk)
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
