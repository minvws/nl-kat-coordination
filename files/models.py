import datetime
import uuid
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models


def raw_file_name(instance, directory: str | None = None):
    return f"files/{datetime.date.today()}/{directory}/{uuid.uuid4()}"


class File(models.Model):
    file = models.FileField(upload_to=raw_file_name)  # the name kwarg will determine the rest of the path
    type = models.CharField(max_length=128, blank=True)
    organizations = models.ManyToManyField("openkat.organization", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def path(self):
        return Path(self.file.name)

class GenericContent(ContentFile):
    def __init__(self, content: str | bytes):
        super().__init__(content, name="data")


class PluginContent(ContentFile):
    def __init__(self, content: str | bytes, plugin_id: str):
        super().__init__(content, name=plugin_id)


class ReportContent(ContentFile):
    def __init__(self, content: str | bytes):
        super().__init__(content, name="reports")
