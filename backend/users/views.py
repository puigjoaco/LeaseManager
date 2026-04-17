import secrets

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache
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

LOGIN_BOOTSTRAP_CACHE_TTL_SECONDS = 15
DEMO_LOGIN_RESPONSE_CACHE_TTL_SECONDS = 15


def _login_bootstrap_cache_key(user, role, access):
    return (
        'auth:login-bootstrap:'
        f'user={user.id}:role={role}:'
        f'restricted={int(access.restricted)}:'
        f'companies={",".join(map(str, sorted(access.company_ids)))}:'
        f'properties={",".join(map(str, sorted(access.property_ids)))}:'
        f'bank_accounts={",".join(map(str, sorted(access.bank_account_ids)))}'
    )


def build_login_bootstrap(user):
    role = normalize_role_code(getattr(user, 'default_role_code', ''))
    access = get_scope_access(user)
    cache_key = _login_bootstrap_cache_key(user, role, access)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload

    payload = {}
    if role in {ROLE_ADMIN, ROLE_OPERATOR}:
        payload = {
            'overview': {
                'dashboard': build_operational_dashboard(access=access, include_secondary=False, use_cache=True),
            }
        }
    elif role == ROLE_REVIEWER:
        payload = {
            'control': build_control_snapshot_payload(access, mode='core', use_cache=True),
        }

    cache.set(cache_key, payload, LOGIN_BOOTSTRAP_CACHE_TTL_SECONDS)
    return payload


def _demo_login_response_cache_key_for_username(username: str):
    return f'auth:demo-login-response:username={username}'


def clear_demo_login_response_cache(user):
    cache.delete(_demo_login_response_cache_key_for_username(user.username))


def build_demo_login_response_payload(user):
    cache_key = _demo_login_response_cache_key_for_username(user.username)
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        if Token.objects.filter(user=user, key=cached_payload.get('token')).exists():
            return cached_payload
        cache.delete(cache_key)

    token, _ = Token.objects.get_or_create(user=user)
    payload = {
        'token': token.key,
        'user': CurrentUserSerializer(user).data,
        'bootstrap': build_login_bootstrap(user),
    }
    cache.set(cache_key, payload, DEMO_LOGIN_RESPONSE_CACHE_TTL_SECONDS)
    return payload


def resolve_demo_login_user(*, username: str, password: str):
    if username not in settings.DEMO_LOGIN_USERS:
        return None
    if not secrets.compare_digest(password, settings.DEMO_LOGIN_PASSWORD):
        return None
    return get_demo_login_user(username)


def get_demo_login_user(username: str):
    from .models import User

    return User.objects.filter(username=username, is_active=True).first()


def get_cached_demo_login_response_payload(*, username: str, password: str):
    if username not in settings.DEMO_LOGIN_USERS:
        return None
    if not secrets.compare_digest(password, settings.DEMO_LOGIN_PASSWORD):
        return None
    return cache.get(_demo_login_response_cache_key_for_username(username))


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cached_demo_payload = get_cached_demo_login_response_payload(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        if cached_demo_payload is not None:
            return Response(cached_demo_payload)

        demo_user = resolve_demo_login_user(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )

        if demo_user:
            return Response(build_demo_login_response_payload(demo_user))

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
        clear_demo_login_response_cache(request.user)
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
