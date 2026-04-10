from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    display_name = models.CharField(max_length=255, blank=True)
    default_role_code = models.CharField(max_length=64, default='operator')
    legacy_reference = models.CharField(max_length=255, blank=True)
    is_service_account = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    def save(self, *args, **kwargs):
        if not self.display_name:
            full_name = self.get_full_name().strip()
            self.display_name = full_name or self.username
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name or self.username
