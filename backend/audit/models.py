import uuid

from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    class Severity(models.TextChoices):
        INFO = 'info', 'Info'
        WARNING = 'warning', 'Warning'
        CRITICAL = 'critical', 'Critical'

    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    actor_identifier = models.CharField(max_length=255, blank=True)
    event_type = models.CharField(max_length=120)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO)
    entity_type = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=255, blank=True)
    summary = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ManualResolution(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_REVIEW = 'in_review', 'In Review'
        RESOLVED = 'resolved', 'Resolved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    scope_type = models.CharField(max_length=120)
    scope_reference = models.CharField(max_length=255)
    summary = models.TextField()
    rationale = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_resolutions_requested',
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manual_resolutions_resolved',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
