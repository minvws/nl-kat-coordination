import datetime
import uuid

from django.core.files.base import ContentFile
from django.db import models


# Create your models here.
def raw_file_name(instance, filename: str | None = None):
    if filename:
        return f"raw_files/{datetime.date.today()}/{filename}"

    return f"raw_files/{datetime.date.today()}/{instance.id}"


class File(models.Model):
    file = models.FileField(upload_to=raw_file_name)  # the name kwarg will determine the rest of the path
    type = models.CharField(max_length=128, blank=True)
    organizations = models.ManyToManyField("openkat.organization", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class NamedContent(ContentFile):
    def __init__(self, content: str | bytes):
        super().__init__(content, name=str(uuid.uuid4()))
