from django.urls import path

from .views import DemoWarmupView, LoginView, LogoutView, MeView

urlpatterns = [
    path('demo-warmup/', DemoWarmupView.as_view(), name='demo-warmup'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
]
