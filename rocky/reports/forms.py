from datetime import datetime, timezone
from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm, DateInput

from reports.report_types.definitions import Report


class OOITypeMultiCheckboxForReportForm(BaseRockyForm):
    ooi_type = forms.MultipleChoiceField(
        label=_("Filter by OOI types"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, ooi_types: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ooi_type"].choices = ((ooi_type, ooi_type) for ooi_type in ooi_types)


class ReportTypeMultiselectForm(BaseRockyForm):
    report_type = forms.MultipleChoiceField(
        label=_("Report types"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, report_types: set[Report], *args, **kwargs):
        super().__init__(*args, **kwargs)
        report_types_choices = ((report_type.id, report_type.name) for report_type in report_types)
        self.fields["report_type"].choices = report_types_choices


class ReportReferenceDateForm(BaseRockyForm):
    choose_date = forms.ChoiceField(
        label="",
        required=False,
        widget=forms.RadioSelect(attrs={"class": "submit-on-click"}),
        choices=(("today", _("Today")), ("schedule", _("Different date"))),
        initial="today",
    )
    start_date = forms.DateField(
        label="",
        widget=forms.HiddenInput(),
        initial=lambda: datetime.now(tz=timezone.utc).date(),
        required=False,
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data.get("choose_date") == "schedule":
            self.fields["start_date"].widget = DateInput(format="%Y-%m-%d")
        return cleaned_data


class ReportRecurrenceForm(BaseRockyForm):
    choose_recurrence = forms.ChoiceField(
        label="",
        required=False,
        widget=forms.RadioSelect(attrs={"class": "submit-on-click"}),
        choices=(("once", _("No, just once")), ("repeat", _("Yes, repeat"))),
        initial="once",
    )
    recurrence = forms.ChoiceField(
        label="",
        required=False,
        widget=forms.Select,
        choices=[
            ("daily", _("Daily")),
            ("weekly", _("Weekly")),
            ("monthly", _("Monthly")),
            ("yearly", _("Yearly")),
        ],
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data.get("choose_recurrence") == "once":
            self.fields["recurrence"].widget = forms.HiddenInput()
            self.fields["recurrence"].choices = [("no_repeat", _("No Repeat"))]
        return cleaned_data


class ReportScheduleForm(ReportReferenceDateForm, ReportRecurrenceForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget = forms.HiddenInput()


class CustomReportScheduleForm(BaseRockyForm):
    start_date = forms.DateField(
        label=_("Start date"),
        widget=DateInput(format="%Y-%m-%d"),
        initial=lambda: datetime.now(tz=timezone.utc).date(),
        required=False,
    )
    repeating_number = forms.IntegerField(initial=1, required=False, min_value=1, max_value=100)
    repeating_term = forms.ChoiceField(
        widget=forms.Select,
        choices=[
            ("day", _("day")),
            ("week", _("week")),
            ("month", _("month")),
            ("year", _("year")),
        ],
    )
    on_weekdays = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[
            ("monday", "M"),
            ("tuesday", "T"),
            ("wednesday", "W"),
            ("thursday", "T"),
            ("friday", "F"),
            ("saturday", "S"),
            ("sunday", "S"),
        ],
    )
    recurrence_ends = forms.ChoiceField(
        widget=forms.RadioSelect,
        choices=[
            ("never", _("Never")),
            ("on", _("On")),  # user choses a specific date
            ("after", _("After")),  # after how many occurrences? Shows drop down with occurrences
        ],
    )

    end_date = forms.DateField(
        label=_(""),
        widget=forms.HiddenInput(),
        initial=lambda: datetime.now(tz=timezone.utc).date(),
        required=False,
    )


class ParentReportNameForm(BaseRockyForm):
    parent_report_name = forms.CharField(
        label=_("Report name format"), required=False, initial="{report type} for {ooi}"
    )


class ChildReportNameForm(BaseRockyForm):
    child_report_name = forms.CharField(
        label=_("Subreports name format"), required=True, initial="{report type} for {ooi}"
    )


class ReportNameForm(ParentReportNameForm, ChildReportNameForm):
    pass
