from django.urls import path

from .views import (
    AsignacionCanalOperacionDetailView,
    AsignacionCanalOperacionListCreateView,
    CuentaRecaudadoraDetailView,
    CuentaRecaudadoraListCreateView,
    IdentidadDeEnvioDetailView,
    IdentidadDeEnvioListCreateView,
    MandatoOperacionDetailView,
    MandatoOperacionListCreateView,
)

urlpatterns = [
    path('cuentas-recaudadoras/', CuentaRecaudadoraListCreateView.as_view(), name='operacion-cuenta-list'),
    path('cuentas-recaudadoras/<int:pk>/', CuentaRecaudadoraDetailView.as_view(), name='operacion-cuenta-detail'),
    path('identidades-envio/', IdentidadDeEnvioListCreateView.as_view(), name='operacion-identidad-list'),
    path('identidades-envio/<int:pk>/', IdentidadDeEnvioDetailView.as_view(), name='operacion-identidad-detail'),
    path('mandatos/', MandatoOperacionListCreateView.as_view(), name='operacion-mandato-list'),
    path('mandatos/<int:pk>/', MandatoOperacionDetailView.as_view(), name='operacion-mandato-detail'),
    path(
        'asignaciones-canal/',
        AsignacionCanalOperacionListCreateView.as_view(),
        name='operacion-asignacion-list',
    ),
    path(
        'asignaciones-canal/<int:pk>/',
        AsignacionCanalOperacionDetailView.as_view(),
        name='operacion-asignacion-detail',
    ),
]
