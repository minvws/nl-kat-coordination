from datetime import date, datetime, timezone

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


class ReportScheduleForm(BaseRockyForm):
    start_date = forms.DateField(
        label=_("Start date"),
        widget=DateInput(format="%Y-%m-%d", attrs={"form": "generate_report"}),
        initial=lambda: datetime.now(tz=timezone.utc).date(),
        required=False,
    )

    recurrence = forms.ChoiceField(
        label=_("Recurrence"),
        required=False,
        widget=forms.Select(
            attrs={"form": "generate_report"},
        ),
        choices=[
            ("no_repeat", _("Does not repeat")),
            ("daily", _("Daily")),
            ("weekly", _("Weekly")),
            ("monthly", _("Monthly")),
            ("yearly", _("Yearly")),
        ],
    )

    def is_valid_day_for_monthly_recurrence(self, start_date: date, recurrence: str) -> bool:
        day = start_date.day
        if recurrence == "monthly":
            if day == 29:
                self.add_error("start_date", _("Warning: Recurrence is set in February only for leap years."))
                return False
            if day == 30:
                self.add_error("start_date", _("Warning: Recurrence is not set for February."))
                return False
            if day == 31:
                self.add_error("start_date", _("Warning: Recurrence will skip months that does not have 31 days."))
                return False
        return True

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        recurrence = cleaned_data.get("recurrence")

        if start_date and recurrence:
            self.is_valid_day_for_monthly_recurrence(start_date, recurrence)

        return cleaned_data


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
