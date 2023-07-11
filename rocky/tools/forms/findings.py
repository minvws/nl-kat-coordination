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
    CAPECFindingType,
    CVEFindingType,
    CWEFindingType,
    KATFindingType,
    RetireJSFindingType,
    SnykFindingType,
]

FINDING_TYPES_CHOICES = (
    (str(finding_type.__name__), str(finding_type.__name__)) for finding_type in FINDING_TYPES_LIST
)

FINDINGS_SEVERITIES_CHOICES = (
    (str(severity.name).lower(), str(severity.value).lower()) for severity in RiskLevelSeverity
)

MUTED_FINDINGS_CHOICES = (
    ("show", _("Show muted findings")),
    ("exclude", _("Exclude muted findings")),
)


class FindingSeverityMultiSelectForm(forms.Form):
    severity = forms.MultipleChoiceField(
        label=_("Filter by severity"),
        required=False,
        choices=FINDINGS_SEVERITIES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )


class FindingRiskScoreRangeForm(BaseRockyForm):
    risk_score_min = forms.FloatField(
        min_value=0,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={"step": "0.1"}),
        label=_("Minimum risk score (one decimal place)"),
    )
    risk_score_max = forms.FloatField(
        min_value=0,
        max_value=10,
        required=False,
        widget=forms.NumberInput(attrs={"step": "0.1"}),
        label=_("Maximum risk score (one decimal place)"),
    )


class MutedFindingSelectionForm(BaseRockyForm):
    muted_findings = forms.ChoiceField(
        required=False, label=_("Filter by muted findings"), choices=MUTED_FINDINGS_CHOICES, widget=forms.RadioSelect()
    )


class FindingTypesMultiSelectForm(BaseRockyForm):
    finding_types = forms.MultipleChoiceField(
        label=_("Filter by finding types"),
        required=False,
        choices=FINDING_TYPES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )
