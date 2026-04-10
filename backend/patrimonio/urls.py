from django.urls import path

from .views import (
    ComunidadDetailView,
    ComunidadListCreateView,
    EmpresaDetailView,
    EmpresaListCreateView,
    ParticipacionDetailView,
    ParticipacionListView,
    PropiedadDetailView,
    PropiedadListCreateView,
    SocioDetailView,
    SocioListCreateView,
)

urlpatterns = [
    path('socios/', SocioListCreateView.as_view(), name='patrimonio-socio-list'),
    path('socios/<int:pk>/', SocioDetailView.as_view(), name='patrimonio-socio-detail'),
    path('empresas/', EmpresaListCreateView.as_view(), name='patrimonio-empresa-list'),
    path('empresas/<int:pk>/', EmpresaDetailView.as_view(), name='patrimonio-empresa-detail'),
    path('comunidades/', ComunidadListCreateView.as_view(), name='patrimonio-comunidad-list'),
    path('comunidades/<int:pk>/', ComunidadDetailView.as_view(), name='patrimonio-comunidad-detail'),
    path('propiedades/', PropiedadListCreateView.as_view(), name='patrimonio-propiedad-list'),
    path('propiedades/<int:pk>/', PropiedadDetailView.as_view(), name='patrimonio-propiedad-detail'),
    path('participaciones/', ParticipacionListView.as_view(), name='patrimonio-participacion-list'),
    path('participaciones/<int:pk>/', ParticipacionDetailView.as_view(), name='patrimonio-participacion-detail'),
]
