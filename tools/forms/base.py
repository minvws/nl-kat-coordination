import datetime
import pytz
from django import forms
from django.utils.translation import gettext_lazy as _
from typing import Dict, List, Union, Any, Optional
from tools.forms import (
    Choices,
    ChoicesGroups,
    OBSERVED_AT_HELP_TEXT,
    SCAN_LEVEL_CHOICES,
)


class BaseRockyModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix


class BaseRockyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""  # Removes : as label suffix

    def set_choices_for_field(
        self, field: str, choices: Union[Choices, ChoicesGroups]
    ) -> None:
        if field in self.fields:
            self.fields[field].choices = choices

    def set_choices_for_widget(
        self, field: str, choices: Union[Choices, ChoicesGroups]
    ) -> None:
        self.fields[field].widget.choices = choices

    def set_required_options_for_widget(
        self, field: str, required_options: List[str]
    ) -> None:
        """For multiselect widgets, set the required options."""
        self.fields[field].widget.required_options = required_options


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class DataListInput(forms.Select):
    input_type = "text"
    template_name = "forms/widgets/datalist.html"

    def __init__(self, attrs=None, choices=()):
        super().__init__(attrs)
        self.choices = list(choices)

    def format_value(self, value):
        """Return selected value as string."""
        if value is None:
            return ""
        return str(value)


class DeclaredScanProfileForm(BaseRockyForm):
    scan_profile = forms.CharField(
        label=_("Scan profile"),
        widget=forms.Select(choices=SCAN_LEVEL_CHOICES),
        required=True,
    )


class ObservedAtForm(BaseRockyForm):
    observed_at = forms.DateField(
        label=_("Date"),
        widget=DateInput(format="%Y-%m-%d"),
        initial=datetime.datetime.now(tz=pytz.UTC),
        required=True,
        help_text=OBSERVED_AT_HELP_TEXT,
    )


class CheckboxGroup(forms.CheckboxSelectMultiple):
    input_type = "checkbox"
    template_name = "forms/widgets/checkbox_group_columns.html"
    option_template_name = "forms/widgets/checkbox_option.html"
    required_options: List[str] = None
    toggle_all_button = None
    wrap_label = True

    def __init__(
        self,
        required_options: Optional[List[str]] = None,
        toggle_all_button: Optional[bool] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if toggle_all_button is not None:
            self.toggle_all_button = toggle_all_button
        self.required_options = required_options or []

    def get_context(self, name, value, attrs) -> Dict[str, Any]:
        context = super().get_context(name, value, attrs)
        context["toggle_all_button"] = self.toggle_all_button
        return context

    def create_option(self, *arg, **kwargs) -> Dict[str, Any]:
        option = super().create_option(*arg, **kwargs)
        option["wrap_label"] = self.wrap_label
        option["attrs"]["required"] = self.is_required_option(option["value"])
        return option

    def is_required_option(self, value: str) -> bool:
        return value in self.required_options


class CheckboxGroupTable(CheckboxGroup):
    template_name = "forms/widgets/checkbox_group_table.html"
    wrap_label = False
