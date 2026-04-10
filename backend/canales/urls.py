from django.urls import path

from .views import (
    CanalMensajeriaDetailView,
    CanalMensajeriaListCreateView,
    MensajePrepararView,
    MensajeRegistrarEnvioView,
    MensajeSalienteDetailView,
    MensajeSalienteListView,
)

urlpatterns = [
    path('gates/', CanalMensajeriaListCreateView.as_view(), name='canales-gate-list'),
    path('gates/<int:pk>/', CanalMensajeriaDetailView.as_view(), name='canales-gate-detail'),
    path('mensajes/', MensajeSalienteListView.as_view(), name='canales-mensaje-list'),
    path('mensajes/<int:pk>/', MensajeSalienteDetailView.as_view(), name='canales-mensaje-detail'),
    path('mensajes/preparar/', MensajePrepararView.as_view(), name='canales-mensaje-preparar'),
    path('mensajes/<int:pk>/registrar-envio/', MensajeRegistrarEnvioView.as_view(), name='canales-mensaje-enviar'),
]
