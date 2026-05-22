from django.urls import path

from .views import OperationalObservabilityView, PlatformBootstrapView

urlpatterns = [
    path('bootstrap/', PlatformBootstrapView.as_view(), name='platform-bootstrap'),
    path(
        'operational-observability/',
        OperationalObservabilityView.as_view(),
        name='platform-operational-observability',
    ),
]
