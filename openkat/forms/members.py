from django import forms
from django.utils.translation import gettext_lazy as _

from openkat.forms.base import BaseOpenKATForm


class MemberFilterForm(BaseOpenKATForm):
    blocked = forms.MultipleChoiceField(
        label=_("Account status"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=((True, _("Blocked")), (False, _("Not blocked"))),
    )

    def clean_blocked(self):
        blocked = self.cleaned_data["blocked"]
        return blocked if blocked else [True, False]
