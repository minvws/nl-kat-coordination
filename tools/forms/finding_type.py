import datetime
from typing import Dict, List

import pytz
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from octopoes.connector import ObjectNotFoundException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference
from octopoes.models.ooi.findings import KATFindingType

from tools.forms import (
    BaseRockyForm,
    RISK_RATING_CHOICES,
    PIE_SCALE_CHOICES,
    PIE_SCALE_EFFORT_CHOICES,
    MANUAL_FINDING_ID_PREFIX,
    FINDING_TYPE_IDS_HELP_TEXT,
    DataListInput,
)
from tools.forms.base import DateTimeInput
from tools.forms.settings import FINDING_DATETIME_HELP_TEXT
from tools.models import OOIInformation


class FindingTypeAddForm(BaseRockyForm):
    id = forms.CharField(
        label=_("KAT-ID"),
        max_length=120,
        help_text=_("Unique ID within KAT, for this type"),
        widget=forms.TextInput(attrs={"placeholder": "KAT-000000"}),
    )
    title = forms.CharField(
        label=_("Title"),
        max_length=120,
        widget=forms.TextInput(
            attrs={"placeholder": _("Give the finding type a fitting title")}
        ),
    )
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(
            attrs={"placeholder": _("Desribe the finding type"), "rows": 3}
        ),
    )
    risk = forms.CharField(
        label=_("Risk"),
        widget=forms.Select(choices=RISK_RATING_CHOICES),
        required=False,
    )
    solution = forms.CharField(
        label=_("Solution"),
        widget=forms.Textarea(
            attrs={"placeholder": _("How can this be solved?"), "rows": 3}
        ),
        required=False,
        help_text=_("Describe how this type of finding can be solved"),
    )
    references = forms.CharField(
        label=_("References"),
        widget=forms.Textarea(
            attrs={
                "placeholder": _("Please give some references on the solution"),
                "rows": 3,
            }
        ),
        required=False,
        help_text=_("Please give sources and references on the suggested solution"),
    )
    impact_description = forms.CharField(
        label=_("Impact description"),
        widget=forms.Textarea(
            attrs={"placeholder": _("Describe the solutions impact"), "rows": 3}
        ),
        required=False,
    )
    solution_chance = forms.CharField(
        label=_("Solution chance"),
        widget=forms.Select(choices=PIE_SCALE_CHOICES),
        required=False,
    )
    solution_impact = forms.CharField(
        label=_("Solution impact"),
        widget=forms.Select(choices=PIE_SCALE_CHOICES),
        required=False,
    )
    solution_effort = forms.CharField(
        label=_("Solution effort"),
        widget=forms.Select(choices=PIE_SCALE_EFFORT_CHOICES),
        required=False,
    )

    def clean_id(self):
        data = self.cleaned_data["id"]
        self.check_finding_type_existence(data)
        if not data.startswith(MANUAL_FINDING_ID_PREFIX):
            raise ValidationError(_("ID should start with ") + MANUAL_FINDING_ID_PREFIX)

        return data

    def check_finding_type_existence(self, id):
        finding_type = KATFindingType(
            id=id,
        )
        _, created = OOIInformation.objects.get_or_create(id=f"KATFindingType|{id}")

        if not created:
            raise ValidationError(_("Finding type already exists"))


class FindingAddForm(BaseRockyForm):
    ooi_id = forms.CharField(
        label="OOI",
        widget=DataListInput(
            attrs={"placeholder": _("Click to select one of the available options")}
        ),
    )
    finding_type_ids = forms.CharField(
        label=_("Finding types"),
        widget=forms.Textarea(
            # Multi line placeholder because this textarea askes the user for every finding type on a new line.
            attrs={
                "placeholder": """KAT-999
KAT-998
CVE-2021-00000""",
                "rows": 3,
            }
        ),
        help_text=FINDING_TYPE_IDS_HELP_TEXT,
    )
    proof = forms.CharField(
        label=_("Proof"),
        widget=forms.Textarea(
            attrs={"placeholder": _("Provide evidence of your finding"), "rows": 3}
        ),
        required=False,
    )
    description = forms.CharField(
        label=_("Description"),
        widget=forms.Textarea(
            attrs={"placeholder": _("Describe your finding"), "rows": 3}
        ),
    )
    reproduce = forms.CharField(
        label=_("Reproduce finding"),
        widget=forms.Textarea(
            attrs={
                "placeholder": _("Please explain how to reproduce your finding"),
                "rows": 3,
            }
        ),
        required=False,
    )
    date = forms.DateTimeField(
        label=_("Date/Time (UTC)"),
        widget=DateTimeInput(format="%Y-%m-%dT%H:%M"),
        initial=datetime.datetime.now(tz=pytz.UTC),
        help_text=FINDING_DATETIME_HELP_TEXT,
    )

    def __init__(
        self,
        connector: OctopoesAPIConnector,
        ooi_list: List[Dict[str, str]],
        *args,
        **kwargs,
    ):
        self.octopoes_connector = connector
        super().__init__(*args, **kwargs)
        self.set_choices_for_field("ooi_id", ooi_list)

    def set_choices_for_field(self, field, choices: List[Dict[str, str]]):
        self.fields[field].widget.choices = choices

    def clean_date(self):
        data = self.cleaned_data["date"]

        # date should not be in the future
        if data > datetime.datetime.now(tz=pytz.UTC):
            raise ValidationError(
                _("Doc! I'm from the future, I'm here to take you back!")
            )

        return data

    def clean_ooi_id(self):
        try:
            data = self.cleaned_data["ooi_id"]
            self.octopoes_connector.get(Reference.from_str(data))
            return data
        except ObjectNotFoundException:
            raise ValidationError(_("OOI doesn't exist"))
