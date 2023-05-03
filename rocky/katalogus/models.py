from django.db import models
from django.utils.translation import gettext_lazy as _
from octopoes.models.types import ALL_TYPES


SORTED_OOI_TYPES = (
    (sorted_ooi_type, sorted_ooi_type) for sorted_ooi_type in sorted([ooi_type.__name__ for ooi_type in ALL_TYPES])
)


class Source(models.Model):
    ooi_type = models.CharField(max_length=128, blank=False, choices=SORTED_OOI_TYPES)
    name = models.CharField(max_length=128, blank=False)
    link = models.URLField(max_length=256, blank=False)
    content = models.CharField(max_length=128, blank=False)

    def __str__(self):
        return self.name
