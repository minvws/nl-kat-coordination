from django import forms
from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.findings import (
    ADRFindingType,
    CAPECFindingType,
    CVEFindingType,
    CWEFindingType,
    KATFindingType,
    RetireJSFindingType,
    RiskLevelSeverity,
    SnykFindingType,
)
from tools.forms.base import BaseRockyForm

FINDING_TYPES_LIST = [
    ADRFindingType,
    CVEFindingType,
    CWEFindingType,
    CAPECFindingType,
    RetireJSFindingType,
    SnykFindingType,
    KATFindingType,
]
FINDING_TYPES_CHOICES = (
    (str(finding_type.__name__), str(finding_type.__name__)) for finding_type in FINDING_TYPES_LIST
)

FINDINGS_SEVERITIES_CHOICES = (
    (str(severity.name).lower(), str(severity.value).lower()) for severity in RiskLevelSeverity
)

MUTED_FINDINGS_CHOICES = (
    ("show", _("Show Muted Findings")),
    ("exclude", _("Exclude Muted Findings")),
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


class MutedFindingSelectionForm(BaseRockyForm):
    muted_findings = forms.ChoiceField(
        required=False, label=_("Filter by Muted Findings"), choices=MUTED_FINDINGS_CHOICES, widget=forms.RadioSelect()
    )


class FindingTypesMultiSelectForm(BaseRockyForm):
    finding_types = forms.MultipleChoiceField(
        label=_("Filter by FindingTypes"),
        required=False,
        choices=FINDING_TYPES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
