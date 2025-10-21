from django.contrib.postgres.fields import ArrayField
from django.db import models

from files.models import File


class Report(models.Model):
    file = models.OneToOneField(File, on_delete=models.CASCADE, related_name="report")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    organizations = models.ManyToManyField("openkat.organization", blank=True, related_name="filtered_reports")
    finding_types = ArrayField(models.CharField(max_length=255), default=list, blank=True)
    object_set = models.ForeignKey(
        "tasks.ObjectSet", on_delete=models.SET_NULL, related_name="reports", null=True, blank=True
    )

    # Store the complete report data for HTML rendering
    data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.created_at}"
