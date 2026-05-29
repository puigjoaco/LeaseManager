from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from core.permissions import (
    AdminOnlyPermission,
    ROLE_ADMIN,
    SensitiveExportPermission,
    get_effective_role_codes,
)
from core.scope_access import get_scope_access, scope_queryset_for_access
from patrimonio.models import Empresa, Socio
from reporting.services import SOCIO_SCOPE_PATHS, ReportingTraceabilityError

from .audit import (
    EXPORT_ACCESSED_EVENT_TYPE,
    EXPORT_ACCESS_DENIED_EVENT_TYPE,
    create_export_audit_event,
)
from .models import ExportacionSensible, PoliticaRetencionDatos
from .serializers import (
    ExportacionPrepareSerializer,
    ExportacionRevokeSerializer,
    ExportacionSensibleSerializer,
    PoliticaRetencionDatosSerializer,
)
from .services import get_export_payload, prepare_sensitive_export, render_export_payload, revoke_export


SCOPE_REQUIRED_ERROR = 'Las exportaciones sensibles requieren un scope explicito para usuarios no administradores.'
SCOPE_DENIED_ERROR = 'La exportacion sensible solicitada queda fuera del scope asignado para este usuario.'


def _has_global_sensitive_export_access(user):
    return getattr(user, 'is_superuser', False) or ROLE_ADMIN in get_effective_role_codes(user)


def _scope_access_for_sensitive_export(user):
    access = get_scope_access(user)
    if _has_global_sensitive_export_access(user):
        return access
    if not access.restricted:
        raise PermissionDenied(SCOPE_REQUIRED_ERROR)
    return access


def _ensure_company_scope(access, empresa_id):
    if empresa_id in (None, ''):
        return
    if not scope_queryset_for_access(
        Empresa.objects.filter(pk=empresa_id),
        access,
        company_paths=('id',),
    ).exists():
        raise PermissionDenied(SCOPE_DENIED_ERROR)


def _ensure_partner_scope(access, socio_id):
    if not scope_queryset_for_access(
        Socio.objects.filter(pk=socio_id),
        access,
        property_paths=SOCIO_SCOPE_PATHS,
    ).exists():
        raise PermissionDenied(SCOPE_DENIED_ERROR)


def _ensure_export_scope_allowed(user, export_kind, scope_resumen):
    access = _scope_access_for_sensitive_export(user)
    if _has_global_sensitive_export_access(user):
        return access

    if export_kind in {'financiero_mensual', 'tributario_anual', 'libros_periodo'}:
        _ensure_company_scope(access, scope_resumen.get('empresa_id'))
    if export_kind == 'socio_resumen':
        _ensure_partner_scope(access, scope_resumen.get('socio_id'))
    return access


def _export_queryset_for_user(queryset, user):
    if _has_global_sensitive_export_access(user):
        return queryset
    _scope_access_for_sensitive_export(user)
    return queryset.filter(created_by=user)


class AuditCreateUpdateMixin:
    audit_entity_type = ''
    audit_entity_label = ''

    def perform_create(self, serializer):
        instance = serializer.save()
        self._create_audit_event(instance=instance, action='created')

    def perform_update(self, serializer):
        previous_state = self._extract_state(serializer.instance)
        instance = serializer.save()
        self._create_audit_event(instance=instance, action='updated')
        if previous_state != self._extract_state(instance):
            self._create_audit_event(
                instance=instance,
                action='state_changed',
                summary=f'Se cambio el estado de {self.audit_entity_label} {instance.pk}',
            )

    def _extract_state(self, instance):
        if hasattr(instance, 'estado'):
            return instance.estado
        return None

    def _create_audit_event(self, *, instance, action, summary=''):
        create_audit_event(
            event_type=f'compliance.{self.audit_entity_type}.{action}',
            entity_type=self.audit_entity_type,
            entity_id=str(instance.pk),
            summary=summary or f'{self.audit_entity_label} {action}',
            actor_user=self.request.user,
            ip_address=self.request.META.get('REMOTE_ADDR'),
        )


class PoliticaRetencionDatosListCreateView(AuditCreateUpdateMixin, generics.ListCreateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PoliticaRetencionDatosSerializer
    queryset = PoliticaRetencionDatos.objects.all()
    audit_entity_type = 'politica_retencion'
    audit_entity_label = 'politica de retencion'


class PoliticaRetencionDatosDetailView(AuditCreateUpdateMixin, generics.RetrieveUpdateAPIView):
    permission_classes = [AdminOnlyPermission]
    serializer_class = PoliticaRetencionDatosSerializer
    queryset = PoliticaRetencionDatos.objects.all()
    audit_entity_type = 'politica_retencion'
    audit_entity_label = 'politica de retencion'


class ExportacionSensibleListView(generics.ListAPIView):
    permission_classes = [SensitiveExportPermission]
    serializer_class = ExportacionSensibleSerializer
    queryset = ExportacionSensible.objects.select_related('created_by').all()

    def get_queryset(self):
        return _export_queryset_for_user(super().get_queryset(), self.request.user)


class ExportacionSensibleDetailView(generics.RetrieveAPIView):
    permission_classes = [SensitiveExportPermission]
    serializer_class = ExportacionSensibleSerializer
    queryset = ExportacionSensible.objects.select_related('created_by').all()

    def get_queryset(self):
        return _export_queryset_for_user(super().get_queryset(), self.request.user)

    def get_object(self):
        export = super().get_object()
        _ensure_export_scope_allowed(self.request.user, export.export_kind, export.scope_resumen)
        return export


class ExportacionPrepareView(APIView):
    permission_classes = [SensitiveExportPermission]

    def post(self, request):
        serializer = ExportacionPrepareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scope_resumen = {key: value for key, value in data.items() if key not in {'categoria_dato', 'export_kind', 'motivo', 'hold_activo'}}
        access = _ensure_export_scope_allowed(request.user, data['export_kind'], scope_resumen)
        try:
            payload = render_export_payload(data['export_kind'], scope_resumen, access=access)
        except ReportingTraceabilityError as error:
            raise ValidationError(
                {
                    'traceability': {
                        'code': error.code,
                        'detail': str(error),
                        'details': error.details,
                    }
                }
            ) from error
        export = prepare_sensitive_export(
            categoria_dato=data['categoria_dato'],
            export_kind=data['export_kind'],
            scope_resumen=scope_resumen,
            motivo=data['motivo'],
            payload=payload,
            created_by=request.user,
            hold_activo=data.get('hold_activo', False),
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(ExportacionSensibleSerializer(export).data, status=status.HTTP_201_CREATED)


class ExportacionContentView(APIView):
    permission_classes = [SensitiveExportPermission]

    def get(self, request, pk):
        export = generics.get_object_or_404(
            _export_queryset_for_user(ExportacionSensible.objects.all(), request.user),
            pk=pk,
        )
        _ensure_export_scope_allowed(request.user, export.export_kind, export.scope_resumen)
        try:
            payload = get_export_payload(export)
        except ValueError as error:
            create_export_audit_event(
                event_type=EXPORT_ACCESS_DENIED_EVENT_TYPE,
                export=export,
                summary='Acceso a exportacion sensible denegado',
                severity='warning',
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
            )
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        create_export_audit_event(
            event_type=EXPORT_ACCESSED_EVENT_TYPE,
            export=export,
            summary='Contenido de exportacion sensible accedido',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(
            {
                'id': export.id,
                'export_kind': export.export_kind,
                'payload_hash': export.payload_hash,
                'payload': payload,
            },
            status=status.HTTP_200_OK,
        )


class ExportacionRevokeView(APIView):
    permission_classes = [SensitiveExportPermission]

    def post(self, request, pk):
        export = generics.get_object_or_404(
            _export_queryset_for_user(ExportacionSensible.objects.all(), request.user),
            pk=pk,
        )
        _ensure_export_scope_allowed(request.user, export.export_kind, export.scope_resumen)
        serializer = ExportacionRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            export = revoke_export(
                export,
                actor_user=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                revocation_reason=serializer.validated_data['motivo'],
            )
        except ValueError as error:
            return Response({'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExportacionSensibleSerializer(export).data, status=status.HTTP_200_OK)
