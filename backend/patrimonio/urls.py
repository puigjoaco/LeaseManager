from django.urls import path

from .views import (
    ComunidadDetailView,
    ComunidadListCreateView,
    EmpresaDetailView,
    EmpresaListCreateView,
    PatrimonioSnapshotView,
    ParticipacionDetailView,
    ParticipacionListView,
    PropiedadDetailView,
    PropiedadListCreateView,
    ServicioPropiedadDetailView,
    ServicioPropiedadListCreateView,
    SocioDetailView,
    SocioListCreateView,
)

urlpatterns = [
    path('snapshot/', PatrimonioSnapshotView.as_view(), name='patrimonio-snapshot'),
    path('socios/', SocioListCreateView.as_view(), name='patrimonio-socio-list'),
    path('socios/<int:pk>/', SocioDetailView.as_view(), name='patrimonio-socio-detail'),
    path('empresas/', EmpresaListCreateView.as_view(), name='patrimonio-empresa-list'),
    path('empresas/<int:pk>/', EmpresaDetailView.as_view(), name='patrimonio-empresa-detail'),
    path('comunidades/', ComunidadListCreateView.as_view(), name='patrimonio-comunidad-list'),
    path('comunidades/<int:pk>/', ComunidadDetailView.as_view(), name='patrimonio-comunidad-detail'),
    path('propiedades/', PropiedadListCreateView.as_view(), name='patrimonio-propiedad-list'),
    path('propiedades/<int:pk>/', PropiedadDetailView.as_view(), name='patrimonio-propiedad-detail'),
    path('servicios-propiedad/', ServicioPropiedadListCreateView.as_view(), name='patrimonio-servicio-propiedad-list'),
    path(
        'servicios-propiedad/<int:pk>/',
        ServicioPropiedadDetailView.as_view(),
        name='patrimonio-servicio-propiedad-detail',
    ),
    path('participaciones/', ParticipacionListView.as_view(), name='patrimonio-participacion-list'),
    path('participaciones/<int:pk>/', ParticipacionDetailView.as_view(), name='patrimonio-participacion-detail'),
]
