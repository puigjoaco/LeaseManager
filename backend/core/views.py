from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PlatformSetting, Scope


class PlatformBootstrapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                'project': 'LeaseManager',
                'modules': [
                    'PlataformaBase',
                    'Patrimonio',
                    'Operacion',
                    'Contratos',
                    'CobranzaActiva',
                    'Conciliacion',
                    'Contabilidad',
                    'Documentos',
                    'Canales',
                    'SII',
                    'Reporting',
                ],
                'available_roles': list(request.user.scope_assignments.values_list('role__code', flat=True)),
                'available_scopes': list(Scope.objects.filter(is_active=True).values('code', 'name', 'scope_type')),
                'settings_count': PlatformSetting.objects.filter(is_active=True).count(),
            }
        )

