from django.urls import path

from .views import (
    ArchivoExpedienteDetailView,
    ArchivoExpedienteListCreateView,
    DocumentsSnapshotView,
    DocumentoEmitidoDetailView,
    DocumentoEmitidoListCreateView,
    DocumentoFormalizarView,
    DocumentoGenerarPDFView,
    DocumentoPrevisualizarPDFView,
    ExpedienteDocumentalDetailView,
    ExpedienteDocumentalListCreateView,
    PlantillaDocumentalDetailView,
    PlantillaDocumentalListCreateView,
    PoliticaFirmaYNotariaDetailView,
    PoliticaFirmaYNotariaListCreateView,
)

urlpatterns = [
    path('snapshot/', DocumentsSnapshotView.as_view(), name='documentos-snapshot'),
    path('expedientes/', ExpedienteDocumentalListCreateView.as_view(), name='documentos-expediente-list'),
    path('expedientes/<int:pk>/', ExpedienteDocumentalDetailView.as_view(), name='documentos-expediente-detail'),
    path('politicas-firma/', PoliticaFirmaYNotariaListCreateView.as_view(), name='documentos-politica-list'),
    path('politicas-firma/<int:pk>/', PoliticaFirmaYNotariaDetailView.as_view(), name='documentos-politica-detail'),
    path('plantillas-documentales/', PlantillaDocumentalListCreateView.as_view(), name='documentos-plantilla-list'),
    path('plantillas-documentales/<int:pk>/', PlantillaDocumentalDetailView.as_view(), name='documentos-plantilla-detail'),
    path('documentos-emitidos/', DocumentoEmitidoListCreateView.as_view(), name='documentos-documento-list'),
    path('documentos-emitidos/previsualizar-pdf/', DocumentoPrevisualizarPDFView.as_view(), name='documentos-documento-previsualizar-pdf'),
    path('documentos-emitidos/generar-pdf/', DocumentoGenerarPDFView.as_view(), name='documentos-documento-generar-pdf'),
    path('documentos-emitidos/<int:pk>/', DocumentoEmitidoDetailView.as_view(), name='documentos-documento-detail'),
    path('documentos-emitidos/<int:pk>/formalizar/', DocumentoFormalizarView.as_view(), name='documentos-documento-formalizar'),
    path('archivos-expediente/', ArchivoExpedienteListCreateView.as_view(), name='documentos-archivo-expediente-list'),
    path('archivos-expediente/<int:pk>/', ArchivoExpedienteDetailView.as_view(), name='documentos-archivo-expediente-detail'),
]
