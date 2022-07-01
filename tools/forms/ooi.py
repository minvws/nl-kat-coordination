from django import forms
from django.utils.translation import gettext_lazy as _
from typing import List, Union, Type, Set, Optional
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import Reference, OOI
from rocky.katalogus import Boefje
from tools.models import SCAN_LEVEL
from tools.forms import (
    BaseRockyForm,
    Choice,
    Choices,
    ChoicesGroup,
    ChoicesGroups,
    ObservedAtForm,
    CheckboxGroup,
    CheckboxGroupTable,
    DEPTH_DEFAULT,
    DEPTH_HELP_TEXT,
    DEPTH_MAX,
    BLANK_CHOICE,
)


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
        widget=CheckboxGroupTable(),
    )

    def __init__(
        self,
        boefje: Boefje,
        connector: OctopoesAPIConnector,
        ooi_reference: Optional[Reference],
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.boefje = boefje
        self.octopoes_connector = connector
        self.ooi_reference = ooi_reference
        self._build_form()

    def _build_form(self) -> None:
        self.set_choices_for_field("ooi", self._get_choices(self.boefje.consumes))
        if len(self.fields["ooi"].choices) == 1:
            self.fields["ooi"].initial = self.fields["ooi"].choices[0][0]

    def _get_choices(self, types: Set[Type[OOI]]) -> Union[Choices, ChoicesGroups]:
        if self.ooi_reference:
            return [self._to_choice(self.ooi_reference)]

        return self._choices_from_parameters(types)

    def _choices_from_parameters(self, types: Set[Type[OOI]]) -> ChoicesGroups:
        types = map(self._group_from_type, types)

        return list(filter(lambda ooi_type: ooi_type[1], types))

    def _group_from_type(self, ooi_type: Type[OOI]) -> ChoicesGroup:
        refs = self.octopoes_connector.list({ooi_type}, limit=1000)
        group_name = ooi_type.get_ooi_type()

        return group_name, [self._to_choice(ref) for ref in refs]

    @staticmethod
    def _to_choice(reference: Reference) -> Choice:
        return str(reference), reference.human_readable


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
