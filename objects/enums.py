from typing import TYPE_CHECKING, cast

from django.db import models

if TYPE_CHECKING:
    from enum import Enum


class ScanLevel(models.IntegerChoices):
    L0 = 0, "L0"
    L1 = 1, "L1"
    L2 = 2, "L2"
    L3 = 3, "L3"
    L4 = 4, "L4"


MAX_SCAN_LEVEL = max(scan_level.value for scan_level in cast("type[Enum]", ScanLevel))
