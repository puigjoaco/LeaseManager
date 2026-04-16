from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event
from contabilidad.views import build_control_snapshot_payload
from core.permissions import ROLE_ADMIN, ROLE_OPERATOR, ROLE_REVIEWER, normalize_role_code
from core.scope_access import get_scope_access
from reporting.services import build_operational_dashboard

from .serializers import CurrentUserSerializer, LoginSerializer


def build_login_bootstrap(user):
    role = normalize_role_code(getattr(user, 'default_role_code', ''))
    access = get_scope_access(user)

    if role in {ROLE_ADMIN, ROLE_OPERATOR}:
        return {
            'overview': {
                'dashboard': build_operational_dashboard(access=access, include_secondary=False, use_cache=True),
            }
        }

    if role == ROLE_REVIEWER:
        return {
            'control': build_control_snapshot_payload(access, mode='core', use_cache=True),
        }

    return {}


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        if not user:
            create_audit_event(
                event_type='auth.login.failed',
                entity_type='user',
                summary='Intento de login fallido',
                actor_identifier=serializer.validated_data['username'],
                ip_address=request.META.get('REMOTE_ADDR'),
                severity='warning',
            )
            return Response({'detail': 'Credenciales inválidas.'}, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        create_audit_event(
            event_type='auth.login.succeeded',
            entity_type='user',
            entity_id=str(user.id),
            summary='Login exitoso en PlataformaBase',
            actor_user=user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        user_payload = CurrentUserSerializer(user).data
        return Response({'token': token.key, 'user': user_payload, 'bootstrap': build_login_bootstrap(user)})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        create_audit_event(
            event_type='auth.logout',
            entity_type='user',
            entity_id=str(request.user.id),
            summary='Logout ejecutado',
            actor_user=request.user,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user).data)
