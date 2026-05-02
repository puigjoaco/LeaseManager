from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PlatformSetting, Scope
from .permissions import get_effective_role_codes
from .scope_access import get_scope_access


class PlatformBootstrapView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_assignments = request.user.scope_assignments.filter(effective_to__isnull=True).select_related('scope', 'role')
        if not get_scope_access(request.user).restricted:
            available_scopes = Scope.objects.filter(is_active=True).order_by('code', 'id')
        else:
            scope_ids = [assignment.scope_id for assignment in active_assignments if assignment.scope_id]
            available_scopes = Scope.objects.filter(is_active=True, id__in=scope_ids).order_by('code', 'id')
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

