from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings


class BaseModel(models.Model):
    """Abstract base model with common audit fields"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="%(app_label)s_%(class)s_created"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
