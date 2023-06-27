from django import forms
from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.findings import RiskLevelSeverity
from tools.forms.base import BaseRockyForm

FINDINGS_SEVERITIES_CHOICES = (
    (str(severity.name).lower(), str(severity.value).lower()) for severity in RiskLevelSeverity
)


class FindingSeverityMultiSelectForm(forms.Form):
    severity = forms.MultipleChoiceField(
        label=_("Filter by severity"),
        required=False,
        choices=FINDINGS_SEVERITIES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )


class FindingRiskScoreNumberForm(forms.Form):
    risk_score_greater_than = forms.FloatField(
        label=_("Filter risk scores greater than"),
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={"placeholder": "Enter a decimal number between 1 and 10"}),
    )
    risk_score_smaller_than = forms.FloatField(
        label=_("Filter risk scores smaller than"),
        required=False,
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={"placeholder": "Enter a decimal number between 1 and 10"}),
    )


class FindingMutedSelectionForm(BaseRockyForm):
    exclude_muted = forms.BooleanField(label=_("Exclude Muted Findings"), required=False)
