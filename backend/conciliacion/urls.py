from django.urls import path

from .views import (
    ConexionBancariaDetailView,
    ConexionBancariaListCreateView,
    IngresoDesconocidoDetailView,
    IngresoDesconocidoListView,
    MovimientoBancarioDetailView,
    MovimientoBancarioListCreateView,
    MovimientoBancarioRetryMatchView,
)

urlpatterns = [
    path('conexiones-bancarias/', ConexionBancariaListCreateView.as_view(), name='conciliacion-conexion-list'),
    path('conexiones-bancarias/<int:pk>/', ConexionBancariaDetailView.as_view(), name='conciliacion-conexion-detail'),
    path('movimientos/', MovimientoBancarioListCreateView.as_view(), name='conciliacion-movimiento-list'),
    path('movimientos/<int:pk>/', MovimientoBancarioDetailView.as_view(), name='conciliacion-movimiento-detail'),
    path('movimientos/<int:pk>/match-exacto/', MovimientoBancarioRetryMatchView.as_view(), name='conciliacion-movimiento-match'),
    path('ingresos-desconocidos/', IngresoDesconocidoListView.as_view(), name='conciliacion-ingreso-list'),
    path('ingresos-desconocidos/<int:pk>/', IngresoDesconocidoDetailView.as_view(), name='conciliacion-ingreso-detail'),
]
