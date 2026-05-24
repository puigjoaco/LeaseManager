from django.urls import path

from .views import (
    ConciliacionSnapshotView,
    CuadraturaBancariaDetailView,
    CuadraturaBancariaListCreateView,
    ConexionBancariaDetailView,
    ConexionBancariaListCreateView,
    IngresoDesconocidoDetailView,
    IngresoDesconocidoListView,
    MovimientoBancarioDetailView,
    MovimientoBancarioListCreateView,
    MovimientoBancarioRetryMatchView,
    TransferenciaIntercuentaDetailView,
    TransferenciaIntercuentaListView,
)

urlpatterns = [
    path('snapshot/', ConciliacionSnapshotView.as_view(), name='conciliacion-snapshot'),
    path('conexiones-bancarias/', ConexionBancariaListCreateView.as_view(), name='conciliacion-conexion-list'),
    path('conexiones-bancarias/<int:pk>/', ConexionBancariaDetailView.as_view(), name='conciliacion-conexion-detail'),
    path('movimientos/', MovimientoBancarioListCreateView.as_view(), name='conciliacion-movimiento-list'),
    path('movimientos/<int:pk>/', MovimientoBancarioDetailView.as_view(), name='conciliacion-movimiento-detail'),
    path('movimientos/<int:pk>/match-exacto/', MovimientoBancarioRetryMatchView.as_view(), name='conciliacion-movimiento-match'),
    path('ingresos-desconocidos/', IngresoDesconocidoListView.as_view(), name='conciliacion-ingreso-list'),
    path('ingresos-desconocidos/<int:pk>/', IngresoDesconocidoDetailView.as_view(), name='conciliacion-ingreso-detail'),
    path('cuadraturas-bancarias/', CuadraturaBancariaListCreateView.as_view(), name='conciliacion-cuadratura-list'),
    path('cuadraturas-bancarias/<int:pk>/', CuadraturaBancariaDetailView.as_view(), name='conciliacion-cuadratura-detail'),
    path('transferencias-intercuenta/', TransferenciaIntercuentaListView.as_view(), name='conciliacion-transferencia-list'),
    path(
        'transferencias-intercuenta/<int:pk>/',
        TransferenciaIntercuentaDetailView.as_view(),
        name='conciliacion-transferencia-detail',
    ),
]
