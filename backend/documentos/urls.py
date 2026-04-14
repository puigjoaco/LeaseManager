from django.urls import path

from .views import (
    DocumentsSnapshotView,
    DocumentoEmitidoDetailView,
    DocumentoEmitidoListCreateView,
    DocumentoFormalizarView,
    ExpedienteDocumentalDetailView,
    ExpedienteDocumentalListCreateView,
    PoliticaFirmaYNotariaDetailView,
    PoliticaFirmaYNotariaListCreateView,
)

urlpatterns = [
    path('snapshot/', DocumentsSnapshotView.as_view(), name='documentos-snapshot'),
    path('expedientes/', ExpedienteDocumentalListCreateView.as_view(), name='documentos-expediente-list'),
    path('expedientes/<int:pk>/', ExpedienteDocumentalDetailView.as_view(), name='documentos-expediente-detail'),
    path('politicas-firma/', PoliticaFirmaYNotariaListCreateView.as_view(), name='documentos-politica-list'),
    path('politicas-firma/<int:pk>/', PoliticaFirmaYNotariaDetailView.as_view(), name='documentos-politica-detail'),
    path('documentos-emitidos/', DocumentoEmitidoListCreateView.as_view(), name='documentos-documento-list'),
    path('documentos-emitidos/<int:pk>/', DocumentoEmitidoDetailView.as_view(), name='documentos-documento-detail'),
    path('documentos-emitidos/<int:pk>/formalizar/', DocumentoFormalizarView.as_view(), name='documentos-documento-formalizar'),
]
