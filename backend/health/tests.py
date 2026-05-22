from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from health.views import SERVICE_DOWN_DETAIL, get_services_status


class HealthEndpointTests(APITestCase):
    @patch(
        'health.views.get_services_status',
        return_value={
            'database': {'status': 'up'},
            'redis': {'status': 'down', 'detail': 'redis://secret@internal-host'},
        },
    )
    def test_health_endpoint_returns_service_snapshot(self, mocked_services):
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['service'], 'leasemanager-api')
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['services']['database']['status'], 'up')
        self.assertEqual(response.data['services']['redis']['status'], 'down')
        self.assertEqual(response.data['services']['redis']['detail'], SERVICE_DOWN_DETAIL)
        self.assertNotIn('internal-host', str(response.data))
        mocked_services.assert_called_once()

    @patch(
        'health.views.get_services_status',
        return_value={
            'database': {'status': 'up'},
            'redis': {'status': 'up'},
        },
    )
    def test_ready_endpoint_returns_200_when_all_services_are_up(self, mocked_services):
        response = self.client.get(reverse('health-ready'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['ready'])
        self.assertEqual(response.data['services']['database']['status'], 'up')
        self.assertEqual(response.data['services']['redis']['status'], 'up')
        mocked_services.assert_called_once()

    @patch(
        'health.views.get_services_status',
        return_value={
            'database': {'status': 'up'},
            'redis': {'status': 'down', 'detail': 'redis://secret@internal-host'},
        },
    )
    def test_ready_endpoint_returns_503_when_any_service_is_down(self, mocked_services):
        response = self.client.get(reverse('health-ready'))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data['ready'])
        self.assertEqual(response.data['services']['redis']['status'], 'down')
        self.assertEqual(response.data['services']['redis']['detail'], SERVICE_DOWN_DETAIL)
        self.assertNotIn('internal-host', str(response.data))
        mocked_services.assert_called_once()

    def test_get_services_status_redacts_dependency_exception_details(self):
        redis_client = MagicMock()
        redis_client.ping.side_effect = RuntimeError(
            'redis://secret@redis.internal:6379 leaked from ping'
        )

        with (
            patch('health.views.connections') as mocked_connections,
            patch('health.views.Redis.from_url', return_value=redis_client),
        ):
            mocked_connections.__getitem__.side_effect = RuntimeError(
                'database internal-db password=secret failed'
            )

            services = get_services_status()

        self.assertEqual(services['database']['status'], 'down')
        self.assertEqual(services['database']['detail'], SERVICE_DOWN_DETAIL)
        self.assertEqual(services['redis']['status'], 'down')
        self.assertEqual(services['redis']['detail'], SERVICE_DOWN_DETAIL)
        self.assertNotIn('internal-db', str(services))
        self.assertNotIn('redis.internal', str(services))
        self.assertNotIn('secret', str(services))
