from django.db import models
from common.models import BaseModel


class Project(BaseModel):
    """Top-level container for agents and workflows"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'projects_project'
        ordering = ['-created_at']
