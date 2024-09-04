from typing import Any

from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from tools.enums import SCAN_LEVEL

Choice = tuple[Any, str]
Choices = list[Choice]
ChoicesGroup = tuple[str, Choices]
ChoicesGroups = list[ChoicesGroup]

BLANK_CHOICE = ("", _("--- Please select one of the available options ----"))
FILTER_BLANK_CHOICE = ("", _("--- Show all ----"))

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

CLEARANCE_TYPE_CHOICES = [
    ("declared", _("Declared")),
    ("inherited", _("Inherited")),
    ("empty", _("Empty")),
]
SCAN_LEVEL_CHOICES = [BLANK_CHOICE] + SCAN_LEVEL.choices

MANUAL_FINDING_ID_PREFIX = "KAT-"

FINDING_TYPE_IDS_HELP_TEXT = _("Add one finding type ID per line.")

FINDING_DATETIME_HELP_TEXT = _("Add the date and time of your finding (UTC)")

RAW_FILE_DATETIME_HELP_TEXT = _("Add the date and time of when the raw file was generated (UTC)")

OBSERVED_AT_HELP_TEXT = _(
    "OpenKAT stores a time indication with every observation, "
    "so it is possible to see the status of your network through time. "
    "Select a datetime to change the view to represent that moment in time."
)

BOEFJE_SCHEMA_HELP_TEXT = mark_safe(
    _(
        "If any other settings are needed for your Boefje, add these as a JSON Schema, "
        "otherwise, leave the field empty or 'null'. "
        "More information about how to do this can be found here: "
        "<a href='https://json-schema.org/learn/getting-started-step-by-step'>JSON Schema</a> "
        "For inspiration, check the 'schema.json' files of other Boefjes in the repo. "
    )
)
BOEFJE_CONSUMES_HELP_TEXT = _(
    "Select the object type(s) that your Boefje consumes. "
    "To select multiple objects, press and hold the 'ctrl'/'command' key "
    "and then click the items you want to select. "
)

BOEFJE_PRODUCES_HELP_TEXT = mark_safe(
    _(
        "<p>Add a set of mime types, separated by commas, for example:</p><p><i>'text/html, image/jpeg'</i> or "
        "<i>'boefje/dns-records'</i>.</p><p>Mime types are used to match the correct normalizer to a raw file. "
        "When the mime type 'boefje/dns-records' is added, the normalizer expects the raw file to contain dns "
        "scan information.</p>"
    )
)
BOEFJE_SCAN_LEVEL_HELP_TEXT = mark_safe(
    _(
        "Select a clearance level for your Boefje. For more information about the different "
        "clearance levels please check the documentation: "
        "<a href='https://docs.openkat.nl/manual/usermanual.html#scan-levels-clearance-indemnities'> "
        "OpenKAT User Manual</a> "
    )
)

DEPTH_DEFAULT = 9
DEPTH_MAX = 15
DEPTH_HELP_TEXT = _("Depth of the tree.")
