from django.urls import path

from .views import (
    AuditSnapshotView,
    AuditEventListView,
    ManualResolutionDetailView,
    ManualResolutionListCreateView,
    ResolveChargeMovementView,
    ResolveMigrationPropertyOwnerView,
    ResolveUnknownIncomeView,
)

urlpatterns = [
    path('snapshot/', AuditSnapshotView.as_view(), name='audit-snapshot'),
    path('events/', AuditEventListView.as_view(), name='audit-events'),
    path('manual-resolutions/', ManualResolutionListCreateView.as_view(), name='manual-resolution-list'),
    path(
        'manual-resolutions/<uuid:pk>/resolve-property-owner/',
        ResolveMigrationPropertyOwnerView.as_view(),
        name='manual-resolution-resolve-property-owner',
    ),
    path(
        'manual-resolutions/<uuid:pk>/resolve-unknown-income/',
        ResolveUnknownIncomeView.as_view(),
        name='manual-resolution-resolve-unknown-income',
    ),
    path(
        'manual-resolutions/<uuid:pk>/resolve-charge-movement/',
        ResolveChargeMovementView.as_view(),
        name='manual-resolution-resolve-charge-movement',
    ),
    path(
        'manual-resolutions/<uuid:pk>/',
        ManualResolutionDetailView.as_view(),
        name='manual-resolution-detail',
    ),
]
