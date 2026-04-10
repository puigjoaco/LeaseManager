from django.contrib import admin

from .models import AuditEvent, ManualResolution

admin.site.register(AuditEvent)
admin.site.register(ManualResolution)
