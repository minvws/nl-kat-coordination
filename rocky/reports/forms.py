from django import forms
from django.utils.translation import gettext_lazy as _

from rocky.reports.report_types.definitions import get_ooi_types_with_report
from rocky.tools.forms.base import BaseRockyForm

SORTED_OOI_TYPES_FOR_REPORT = sorted([ooi_class.ooi_type for ooi_class in get_ooi_types_with_report()])

OOI_TYPE_CHOICES_FOR_REPORT = ((ooi_type, ooi_type) for ooi_type in SORTED_OOI_TYPES_FOR_REPORT)


class OOITypeMultiCheckboxForReportForm(BaseRockyForm):
    ooi_type = forms.MultipleChoiceField(
        label=_("Filter by OOI types"),
        required=False,
        choices=OOI_TYPE_CHOICES_FOR_REPORT,
        widget=forms.CheckboxSelectMultiple,
    )
