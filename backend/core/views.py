from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PlatformSetting, Scope
from .permissions import get_effective_role_codes


class PlatformBootstrapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_assignments = request.user.scope_assignments.filter(effective_to__isnull=True).select_related('scope', 'role')
        if getattr(request.user, 'is_superuser', False):
            available_scopes = Scope.objects.filter(is_active=True)
        else:
            scope_ids = [assignment.scope_id for assignment in active_assignments if assignment.scope_id]
            available_scopes = Scope.objects.filter(is_active=True, id__in=scope_ids)
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
                'available_roles': sorted(get_effective_role_codes(request.user)),
                'available_scopes': list(available_scopes.values('code', 'name', 'scope_type')),
                'settings_count': PlatformSetting.objects.filter(is_active=True).count(),
            }
        )

