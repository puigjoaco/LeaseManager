from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditEvent, ManualResolution
from .serializers import (
    AuditEventSerializer,
    ManualResolutionSerializer,
    ResolveMigrationPropertyOwnerSerializer,
)
from .services import resolve_migration_property_owner_manual_resolution


class AuditEventListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AuditEventSerializer
    queryset = AuditEvent.objects.all()[:100]


class ManualResolutionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [IsAuthenticated]
    serializer_class = ManualResolutionSerializer
    queryset = ManualResolution.objects.all()


class ResolveMigrationPropertyOwnerView(APIView):
    permission_classes = [IsAuthenticated]

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
