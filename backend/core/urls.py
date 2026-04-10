from django.urls import path

from .views import PlatformBootstrapView

urlpatterns = [
    path('bootstrap/', PlatformBootstrapView.as_view(), name='platform-bootstrap'),
]
