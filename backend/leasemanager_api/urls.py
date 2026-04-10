"""
URL configuration for leasemanager_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('users.urls')),
    path('api/v1/platform/', include('core.urls')),
    path('api/v1/audit/', include('audit.urls')),
    path('api/v1/health/', include('health.urls')),
    path('api/v1/patrimonio/', include('patrimonio.urls')),
    path('api/v1/operacion/', include('operacion.urls')),
    path('api/v1/contratos/', include('contratos.urls')),
    path('api/v1/cobranza/', include('cobranza.urls')),
    path('api/v1/conciliacion/', include('conciliacion.urls')),
    path('api/v1/contabilidad/', include('contabilidad.urls')),
    path('api/v1/documentos/', include('documentos.urls')),
    path('api/v1/canales/', include('canales.urls')),
    path('api/v1/sii/', include('sii.urls')),
    path('api/v1/reporting/', include('reporting.urls')),
    path('api/v1/compliance/', include('compliance.urls')),
]

