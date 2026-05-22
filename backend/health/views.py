from django.conf import settings
from django.db import connections
from redis import Redis
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


SERVICE_DOWN_DETAIL = 'unavailable'


def service_down_status():
    return {'status': 'down', 'detail': SERVICE_DOWN_DETAIL}


def public_services_status(services):
    return {
        service_name: {'status': 'up'}
        if service.get('status') == 'up'
        else service_down_status()
        for service_name, service in services.items()
    }


def get_services_status():
    services = {
        'database': service_down_status(),
        'redis': service_down_status(),
    }

    try:
        with connections['default'].cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        services['database'] = {'status': 'up'}
    except Exception:
        services['database'] = service_down_status()

    try:
        Redis.from_url(settings.CELERY_BROKER_URL).ping()
        services['redis'] = {'status': 'up'}
    except Exception:
        services['redis'] = service_down_status()

    return services


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        services = public_services_status(get_services_status())
        return Response(
            {
                'service': 'leasemanager-api',
                'status': 'ok',
                'environment': 'development' if settings.DEBUG else 'production',
                'services': services,
            }
        )


class ReadyCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        services = public_services_status(get_services_status())
        all_up = all(service['status'] == 'up' for service in services.values())
        return Response(
            {'ready': all_up, 'services': services},
            status=status.HTTP_200_OK if all_up else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
