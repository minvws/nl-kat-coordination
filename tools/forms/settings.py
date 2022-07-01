from typing import List, Tuple, Any

from django.utils.translation import gettext_lazy as _

Choice = Tuple[Any, str]
Choices = List[Choice]
ChoicesGroup = Tuple[str, Choices]
ChoicesGroups = List[ChoicesGroup]

BLANK_CHOICE = ("", _("--- Please select one of the available options ----"))

RISK_RATING_CHOICES: Choices = [
    BLANK_CHOICE,
    ("recommendation", _("recommendation")),
    ("low", _("low")),
    ("medium", _("medium")),
    ("high", _("high")),
    ("very high", _("very high")),
    ("critical", _("critical")),
]

PIE_SCALE_EFFORT_CHOICES: Choices = [
    BLANK_CHOICE,
    ("quickfix", _("quickfix")),
    ("low", _("low")),
    ("medium", _("medium")),
    ("high", _("high")),
]

PIE_SCALE_CHOICES: Choices = [
    BLANK_CHOICE,
    ("low", _("low")),
    ("medium", _("medium")),
    ("high", _("high")),
]

SCAN_LEVEL_CHOICES: Choices = [
    BLANK_CHOICE,
    (1, "L1"),
    (2, "L2"),
    (3, "L3"),
    (4, "L4"),
]

MANUAL_FINDING_ID_PREFIX = "KAT-"

FINDING_TYPE_IDS_HELP_TEXT = _("Add one finding type ID per line.")

FINDING_DATETIME_HELP_TEXT = _("Add the date and time of your finding (UTC)")

OBSERVED_AT_HELP_TEXT = _(
    "KAT stores a time indication with every observation, so it is possible to see the status of your network through time. Select a datetime to change the view to represent that moment in time."
)

DEPTH_DEFAULT = 9
DEPTH_MAX = 15
DEPTH_HELP_TEXT = _("Depth of the tree.")
