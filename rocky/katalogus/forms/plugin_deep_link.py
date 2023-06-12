from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyModelForm
from tools.forms.settings import BLANK_CHOICE

from katalogus.models import PluginDeepLink
from octopoes.models.types import ALL_TYPES

SORTED_OOI_TYPES = [BLANK_CHOICE] + [
    (sorted_ooi_type, sorted_ooi_type) for sorted_ooi_type in sorted([ooi_type.__name__ for ooi_type in ALL_TYPES])
]


class PluginDeepLinkForm(BaseRockyModelForm):
    enable = forms.BooleanField(required=False)

    class Meta:
        model = PluginDeepLink
        fields = "__all__"
        widgets = {"ooi_type": forms.Select(choices=SORTED_OOI_TYPES)}
        help_texts = {
            "ooi_type": _("Choose an OOI-type where this plugin will be bound to."),
            "name": _("Give your plugin a unique name."),
            "content": _("This is the link text."),
            "link": _(
                "Insert your link including the link parameters. "
                "Example: https://cve.mitre.org/cgi-bin/cvename.cgi?name=[id]"
            ),
            "enable": _("To use and show this link you must first enable it."),
        }
