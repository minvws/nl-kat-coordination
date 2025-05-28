from typing import Any

from django import forms
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm
from tools.models import Organization


class MemberFilterForm(BaseRockyForm):
    status = forms.MultipleChoiceField(
        label=_("Current status"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=(("active", _("Active")), ("new", _("New"))),
    )

    blocked = forms.MultipleChoiceField(
        label=_("Account status"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=((True, _("Blocked")), (False, _("Not blocked"))),
    )

    def clean_status(self):
        status = self.cleaned_data["status"]
        return status if status else ["active", "new"]

    def clean_blocked(self):
        blocked = self.cleaned_data["blocked"]
        return blocked if blocked else [True, False]

    def filter_members(self, organization: Organization, qs: QuerySet[Any]):
        if self.is_valid():
            current_status = self.cleaned_data.get("status")
            account_status = self.cleaned_data.get("blocked")
            return qs.filter(organization=organization, status__in=current_status, blocked__in=account_status)
        return qs
