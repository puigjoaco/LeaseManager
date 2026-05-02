from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class HealthEndpointTests(APITestCase):
    @patch(
        'health.views.get_services_status',
        return_value={
            'database': {'status': 'up'},
            'redis': {'status': 'down', 'detail': 'redis unavailable'},
        },
    )
    def test_health_endpoint_returns_service_snapshot(self, mocked_services):
        response = self.client.get(reverse('health'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['service'], 'leasemanager-api')
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['services']['database']['status'], 'up')
        self.assertEqual(response.data['services']['redis']['status'], 'down')
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
            'redis': {'status': 'down', 'detail': 'redis unavailable'},
        },
    )
    def test_ready_endpoint_returns_503_when_any_service_is_down(self, mocked_services):
        response = self.client.get(reverse('health-ready'))

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(response.data['ready'])
        self.assertEqual(response.data['services']['redis']['status'], 'down')
        mocked_services.assert_called_once()
