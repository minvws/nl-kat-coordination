from django.db import models


class Source(models.Model):
    ooi_type = models.CharField(max_length=128, blank=False)
    name = models.CharField(max_length=128, blank=False)
    content = models.CharField(max_length=128, blank=False)
    link = models.URLField(max_length=256, blank=False)

    def __str__(self):
        return self.name
