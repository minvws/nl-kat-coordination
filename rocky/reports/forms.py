from typing import Set

from django import forms
from django.utils.translation import gettext_lazy as _
from tools.forms.base import BaseRockyForm

from reports.report_types.definitions import Report


class OOITypeMultiCheckboxForReportForm(BaseRockyForm):
    ooi_type = forms.MultipleChoiceField(
        label=_("Filter by OOI types"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, ooi_types: Set[Report], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ooi_type"].choices = ((ooi_type, ooi_type) for ooi_type in ooi_types)


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
