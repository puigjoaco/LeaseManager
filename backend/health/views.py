from django.conf import settings
from django.db import connections
from redis import Redis
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def get_services_status():
    services = {
        'database': {'status': 'down'},
        'redis': {'status': 'down'},
    }

    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        services['database'] = {'status': 'up'}
    except Exception as error:
        services['database'] = {'status': 'down', 'detail': str(error)}

    try:
        Redis.from_url(settings.CELERY_BROKER_URL).ping()
        services['redis'] = {'status': 'up'}
    except Exception as error:
        services['redis'] = {'status': 'down', 'detail': str(error)}

    return services


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                'service': 'leasemanager-api',
                'status': 'ok',
                'environment': 'development' if settings.DEBUG else 'production',
                'services': get_services_status(),
            }
        )


class ReadyCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        services = get_services_status()
        all_up = all(service['status'] == 'up' for service in services.values())
        return Response(
            {'ready': all_up, 'services': services},
            status=status.HTTP_200_OK if all_up else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
