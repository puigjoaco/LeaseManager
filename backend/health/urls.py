from django.urls import path

from .views import HealthCheckView, ReadyCheckView

urlpatterns = [
    path('', HealthCheckView.as_view(), name='health'),
    path('ready/', ReadyCheckView.as_view(), name='health-ready'),
]
