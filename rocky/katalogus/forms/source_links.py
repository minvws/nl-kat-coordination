from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.settings import BLANK_CHOICE

from katalogus.models import Source
from octopoes.models.types import ALL_TYPES

SORTED_OOI_TYPES = [BLANK_CHOICE] + [
    (sorted_ooi_type, sorted_ooi_type) for sorted_ooi_type in sorted([ooi_type.__name__ for ooi_type in ALL_TYPES])
]


class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = "__all__"
        widgets = {"ooi_type": forms.Select(choices=SORTED_OOI_TYPES)}
        help_texts = {
            "ooi_type": _("Choose an OOI-type where the source link will be bounded to."),
            "name": _("Name your plugin which can be found in the KAT-alogus."),
            "content": _("This is the link text."),
            "link": _(
                "Insert your link including the link parameters. "
                "Example: https://cve.mitre.org/cgi-bin/cvename.cgi?name=[cvecode]"
            ),
        }
