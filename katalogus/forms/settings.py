from django import forms
from django.utils.translation import gettext_lazy as _


class PluginSettingsAddForm(forms.Form):
    name = forms.CharField(
        max_length=128,
        required=True,
        label=_("Name"),
        help_text=_("Choose a name for the setting you are going to create."),
    )
    value = forms.CharField(
        max_length=128,
        required=True,
        label=_("Value"),
        help_text=_("Insert a value for this new setting."),
    )


class PluginSettingsEditForm(forms.Form):
    value = forms.CharField(
        max_length=128,
        required=True,
        label=_("Value"),
        help_text=_("Enter a value to update this setting."),
    )
