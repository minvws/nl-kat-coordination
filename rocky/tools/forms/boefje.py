from typing import Any, Dict, List, Union

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from katalogus.client import Boefje

from tools.forms.base import BaseRockyForm, CheckboxGroup, Choices, ChoicesGroups
from tools.forms.settings import Choice
from tools.models import Organization


class CheckboxGroupBoefjeTiles(CheckboxGroup):
    template_name = "forms/widgets/checkbox_group_boefje_tiles.html"
    option_template_name = "partials/boefje_tile_option.html"
    wrap_label = False

    def __init__(self):
        super().__init__()
        self.boefjes: List[Boefje] = self.attrs.get("boefjes", [])
        self.organization = self.attrs.get(
            "organization",
        )

    def create_option(self, *arg, **kwargs) -> Dict[str, Any]:
        option = super().create_option(*arg, **kwargs)
        option["boefje"] = [boefje for boefje in self.boefjes if boefje["id"] == option["value"]][0]
        return option

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["organization"] = self.organization
        return context


class SelectBoefjeForm(BaseRockyForm):
    boefje = forms.MultipleChoiceField(
        label=_("Boefjes"),
        widget=CheckboxGroupBoefjeTiles(),
    )

    def __init__(
        self,
        boefjes: List[Boefje],
        organization: Organization,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.boefjes = boefjes
        self.organization = organization
        self._build_form()

    def clean(self):
        data = self.cleaned_data["boefje"]

        for boefje in self.boefjes:
            if boefje["required"] and boefje["id"] not in data:
                raise ValidationError(_("Not all required boefjes are selected. Please select all required boefjes."))

        return data

    def _build_form(self) -> None:
        self.set_choices_for_field("boefje", self._get_choices(self.boefjes))
        self.set_required_options_for_widget(
            "boefje",
            [item["id"] for item in self.boefjes if item.get("required", False)],
        )
        self.fields["boefje"].widget.boefjes = self.boefjes
        self.fields["boefje"].widget.organization = self.organization

    def _get_choices(self, boefjes: List[Boefje]) -> Union[Choices, ChoicesGroups]:
        return [("Boefje", [self._choice_from_boefje(item["boefje"]) for item in boefjes])]

    def _choice_from_boefje(self, boefje: Boefje) -> Choice:
        return boefje.id, boefje.name
