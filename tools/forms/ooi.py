from typing import List, Type, Set, Optional, Tuple, Any

from django import forms
from django.utils.translation import gettext_lazy as _
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI

from rocky.katalogus import Boefje
from tools.forms import (
    BaseRockyForm,
    Choice,
    Choices,
    ObservedAtForm,
    CheckboxGroup,
    CheckboxTable,
    DEPTH_DEFAULT,
    DEPTH_HELP_TEXT,
    DEPTH_MAX,
    BLANK_CHOICE,
    LabeledCheckboxInput,
)
from tools.models import SCAN_LEVEL


class OOIReportSettingsForm(ObservedAtForm):
    depth = forms.IntegerField(
        initial=DEPTH_DEFAULT,
        min_value=1,
        max_value=DEPTH_MAX,
        required=False,
        help_text=DEPTH_HELP_TEXT,
    )


class OoiTreeSettingsForm(OOIReportSettingsForm):
    ooi_type = forms.MultipleChoiceField(
        label=_("filter types"),
        widget=CheckboxGroup(toggle_all_button=True),
        required=False,
    )

    def __init__(self, ooi_types: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_ooi_types(ooi_types)

    def set_ooi_types(self, ooi_types: List[str]) -> None:
        if not ooi_types:
            self.fields.pop("ooi_type", None)
            return

        ooi_types_choices = [(type_, _(type_)) for type_ in ooi_types]
        self.set_choices_for_field("ooi_type", ooi_types_choices)


class SelectOOIForm(BaseRockyForm):
    ooi = forms.MultipleChoiceField(
        label=_("Objects"),
        widget=CheckboxTable(
            column_names=("Type", "OOI", "Scan Level"),
            column_templates=(None, None, "partials/scan_level_indicator.html"),
        ),
    )

    def __init__(
        self,
        oois: List[OOI],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.set_choices_for_field("ooi", [self._to_choice(ooi) for ooi in oois])
        if len(self.fields["ooi"].choices) == 1:
            self.fields["ooi"].initial = self.fields["ooi"].choices[0][0]

    @staticmethod
    def _to_choice(ooi: OOI) -> Tuple[str, Any]:
        return str(ooi), (
            ooi.get_ooi_type(),
            ooi.human_readable,
            ooi.scan_profile.level,
        )


class SelectOOIFilterForm(BaseRockyForm):
    show_all = forms.NullBooleanField(
        widget=LabeledCheckboxInput(
            label=_("Show objects that don't meet the Boefjes scan level"),
            autosubmit=True,
        ),
    )


class SetClearanceLevelForm(forms.Form):

    level = forms.IntegerField(
        label=_("Clearance level"),
        help_text=_(
            "Boefjes that has a scan level below or equal to the clearance level, is permitted to scan an object."
        ),
        error_messages={
            "level": {
                "required": _("Please select a clearance level to proceed."),
            },
        },
        widget=forms.Select(
            choices=[BLANK_CHOICE] + SCAN_LEVEL.choices,
            attrs={
                "aria-describedby": _("explanation-clearance-level"),
            },
        ),
    )
