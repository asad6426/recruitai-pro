from django.db import models


class Skill(models.Model):
    """Shared skill taxonomy referenced by jobs, candidates, and resume analyses."""

    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
