from django.urls import path

from .views import (
    ArrendatarioDetailView,
    ArrendatarioListCreateView,
    AvisoTerminoDetailView,
    AvisoTerminoListCreateView,
    CodeudorSolidarioDetailView,
    CodeudorSolidarioListView,
    ContratoDetailView,
    ContratoListCreateView,
    ContratoPropiedadDetailView,
    ContratoPropiedadListView,
    PeriodoContractualDetailView,
    PeriodoContractualListView,
)

urlpatterns = [
    path('arrendatarios/', ArrendatarioListCreateView.as_view(), name='contratos-arrendatario-list'),
    path('arrendatarios/<int:pk>/', ArrendatarioDetailView.as_view(), name='contratos-arrendatario-detail'),
    path('contratos/', ContratoListCreateView.as_view(), name='contratos-contrato-list'),
    path('contratos/<int:pk>/', ContratoDetailView.as_view(), name='contratos-contrato-detail'),
    path('avisos-termino/', AvisoTerminoListCreateView.as_view(), name='contratos-aviso-list'),
    path('avisos-termino/<int:pk>/', AvisoTerminoDetailView.as_view(), name='contratos-aviso-detail'),
    path(
        'contratos-propiedad/',
        ContratoPropiedadListView.as_view(),
        name='contratos-contrato-propiedad-list',
    ),
    path(
        'contratos-propiedad/<int:pk>/',
        ContratoPropiedadDetailView.as_view(),
        name='contratos-contrato-propiedad-detail',
    ),
    path(
        'periodos-contractuales/',
        PeriodoContractualListView.as_view(),
        name='contratos-periodo-list',
    ),
    path(
        'periodos-contractuales/<int:pk>/',
        PeriodoContractualDetailView.as_view(),
        name='contratos-periodo-detail',
    ),
    path(
        'codeudores-solidarios/',
        CodeudorSolidarioListView.as_view(),
        name='contratos-codeudor-list',
    ),
    path(
        'codeudores-solidarios/<int:pk>/',
        CodeudorSolidarioDetailView.as_view(),
        name='contratos-codeudor-detail',
    ),
]
