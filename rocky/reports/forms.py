from typing import Set

from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm

from reports.report_types.definitions import Report
from reports.report_types.helpers import get_ooi_types_with_report

SORTED_OOI_TYPES_FOR_REPORT = sorted([ooi_class.get_ooi_type() for ooi_class in get_ooi_types_with_report()])

OOI_TYPE_CHOICES_FOR_REPORT = ((ooi_type, ooi_type) for ooi_type in SORTED_OOI_TYPES_FOR_REPORT)


class OOITypeMultiCheckboxForReportForm(BaseRockyForm):
    ooi_type = forms.MultipleChoiceField(
        label=_("Filter by OOI types"),
        required=False,
        choices=OOI_TYPE_CHOICES_FOR_REPORT,
        widget=forms.CheckboxSelectMultiple,
    )


class ReportTypeMultiselectForm(BaseRockyForm):
    report_type = forms.MultipleChoiceField(
        label=_("Report types"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, report_types: Set[Report], *args, **kwargs):
        super().__init__(*args, **kwargs)
        report_types_choices = ((report_type.id, report_type.name) for report_type in report_types)
        self.fields["report_type"].choices = report_types_choices
