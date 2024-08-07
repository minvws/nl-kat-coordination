from datetime import datetime, timezone

from django import forms
from django.utils.translation import gettext_lazy as _

from tools.forms.base import DateInput


class TaskFilterForm(forms.Form):
    min_created_at = forms.DateField(
        label=_("From"),
        widget=DateInput(format="%Y-%m-%d"),
        required=False,
    )
    max_created_at = forms.DateField(
        label=_("To"),
        widget=DateInput(format="%Y-%m-%d"),
        required=False,
    )
    status = forms.ChoiceField(
        choices=(
            ("", _("All")),
            ("cancelled", _("Cancelled")),
            ("completed", _("Completed")),
            ("dispatched", _("Dispatched")),
            ("failed", _("Failed")),
            ("pending", _("Pending")),
            ("queued", _("Queued")),
            ("running", _("Running")),
        ),
        required=False,
    )
    input_ooi = forms.CharField(
        label=_("Search"),
        widget=forms.TextInput(attrs={"placeholder": _("Search by object name")}),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()

        min_created_at = cleaned_data.get("min_created_at")
        max_created_at = cleaned_data.get("max_created_at")

        date_message = _("The selected date is in the future. Please select a different date.")

        now = datetime.now(tz=timezone.utc)

        if min_created_at is not None and min_created_at > now.date():
            self.add_error("min_created_at", date_message)

        if max_created_at is not None and max_created_at > now.date():
            self.add_error("max_created_at", date_message)

        return cleaned_data


class ScheduleFilterForm(forms.Form):
    enabled = forms.BooleanField(initial=True, required=False)
    min_deadline_at = forms.DateField(
        label=_("Start schedule date"),
        widget=DateInput(format="%Y-%m-%d"),
        required=False,
    )
    max_deadline_at = forms.DateField(
        label=_("End schedule date"),
        widget=DateInput(format="%Y-%m-%d"),
        required=False,
    )

    min_created_at = forms.DateField(
        label=_("Created date from"),
        widget=DateInput(format="%Y-%m-%d"),
        required=False,
    )
    max_created_at = forms.DateField(
        label=_("Created date till"),
        widget=DateInput(format="%Y-%m-%d"),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()

        min_created_at = cleaned_data.get("min_created_at")
        max_created_at = cleaned_data.get("max_created_at")

        date_message = _("The selected date is in the future. Please select a different date.")

        now = datetime.now(tz=timezone.utc)

        if min_created_at is not None and min_created_at > now.date():
            self.add_error("min_created_at", date_message)

        if max_created_at is not None and max_created_at > now.date():
            self.add_error("max_created_at", date_message)

        return cleaned_data


class OOIDetailTaskFilterForm(TaskFilterForm):
    """
    Task filter at OOI detail to pass observed_at and ooi_id values.
    """

    observed_at = forms.CharField(widget=forms.HiddenInput(), required=False)
    ooi_id = forms.CharField(widget=forms.HiddenInput(), required=False)

    # No need to search for OOI if you are already at the OOI detail page.
    input_ooi = None
