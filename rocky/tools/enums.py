from django.db import models


class SCAN_LEVEL(models.IntegerChoices):
    L0 = 0, "L0"
    L1 = 1, "L1"
    L2 = 2, "L2"
    L3 = 3, "L3"
    L4 = 4, "L4"


class CUSTOM_SCAN_LEVEL(models.Choices):
    inherit = "inherit"
    l0 = 0
    l1 = 1
    l2 = 2
    l3 = 3
    l4 = 4
