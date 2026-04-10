from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_event

from .serializers import CurrentUserSerializer, LoginSerializer


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
        return Response({'token': token.key, 'user': CurrentUserSerializer(user).data})


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
