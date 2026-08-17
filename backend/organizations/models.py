from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=150, unique=True)
    logo = models.ImageField(upload_to="org_logos/", blank=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    employee_count = models.PositiveIntegerField(null=True, blank=True)
    funding_stage = models.CharField(max_length=50, blank=True)  # e.g. "Series C"
    industry = models.CharField(max_length=80, blank=True)  # e.g. "SaaS"
    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
