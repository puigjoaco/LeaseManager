from django.urls import path

from .views import (
    ExportacionContentView,
    ExportacionPrepareView,
    ExportacionRevokeView,
    ExportacionSensibleDetailView,
    ExportacionSensibleListView,
    PoliticaRetencionDatosDetailView,
    PoliticaRetencionDatosListCreateView,
)

urlpatterns = [
    path('politicas-retencion/', PoliticaRetencionDatosListCreateView.as_view(), name='compliance-politica-list'),
    path('politicas-retencion/<int:pk>/', PoliticaRetencionDatosDetailView.as_view(), name='compliance-politica-detail'),
    path('exportes/', ExportacionSensibleListView.as_view(), name='compliance-export-list'),
    path('exportes/<int:pk>/', ExportacionSensibleDetailView.as_view(), name='compliance-export-detail'),
    path('exportes/preparar/', ExportacionPrepareView.as_view(), name='compliance-export-prepare'),
    path('exportes/<int:pk>/contenido/', ExportacionContentView.as_view(), name='compliance-export-content'),
    path('exportes/<int:pk>/revocar/', ExportacionRevokeView.as_view(), name='compliance-export-revoke'),
]
