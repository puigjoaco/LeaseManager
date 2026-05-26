from django.urls import path

from .views import (
    ArrendatarioDetailView,
    ArrendatarioListCreateView,
    ArrendatarioWhatsappBlockView,
    ArrendatarioWhatsappRehabilitateView,
    AvisoTerminoDetailView,
    AvisoTerminoListCreateView,
    CodeudorSolidarioDetailView,
    CodeudorSolidarioListView,
    ContactoPagoArrendatarioDetailView,
    ContactoPagoArrendatarioListCreateView,
    ContratoAutomaticRenewalView,
    ContratoDetailView,
    ContratoListCreateView,
    ContratoPropiedadDetailView,
    ContratoPropiedadListView,
    ContratoTenantReplacementView,
    ContractsSnapshotView,
    PeriodoContractualDetailView,
    PeriodoContractualListView,
)

urlpatterns = [
    path('snapshot/', ContractsSnapshotView.as_view(), name='contratos-snapshot'),
    path('arrendatarios/', ArrendatarioListCreateView.as_view(), name='contratos-arrendatario-list'),
    path('arrendatarios/<int:pk>/', ArrendatarioDetailView.as_view(), name='contratos-arrendatario-detail'),
    path(
        'arrendatarios/<int:pk>/whatsapp-bloquear/',
        ArrendatarioWhatsappBlockView.as_view(),
        name='contratos-arrendatario-whatsapp-bloquear',
    ),
    path(
        'arrendatarios/<int:pk>/whatsapp-rehabilitar/',
        ArrendatarioWhatsappRehabilitateView.as_view(),
        name='contratos-arrendatario-whatsapp-rehabilitar',
    ),
    path(
        'contactos-pago/',
        ContactoPagoArrendatarioListCreateView.as_view(),
        name='contratos-contacto-pago-list',
    ),
    path(
        'contactos-pago/<int:pk>/',
        ContactoPagoArrendatarioDetailView.as_view(),
        name='contratos-contacto-pago-detail',
    ),
    path('contratos/', ContratoListCreateView.as_view(), name='contratos-contrato-list'),
    path(
        'contratos/<int:pk>/renovacion-automatica/',
        ContratoAutomaticRenewalView.as_view(),
        name='contratos-contrato-renovacion-automatica',
    ),
    path(
        'contratos/<int:pk>/cambio-arrendatario/',
        ContratoTenantReplacementView.as_view(),
        name='contratos-contrato-cambio-arrendatario',
    ),
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
