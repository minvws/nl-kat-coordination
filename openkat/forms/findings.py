from django import forms
from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.findings import RiskLevelSeverity
from openkat.forms.base import BaseOpenKATForm

FINDINGS_SEVERITIES_CHOICES = (
    (str(severity.name).lower(), str(severity.value).lower()) for severity in RiskLevelSeverity
)

MUTED_FINDINGS_CHOICES = (
    ("non-muted", _("Show non-muted findings")),
    ("muted", _("Show muted findings")),
    ("all", _("Show muted and non-muted findings")),
)


class FindingSeverityMultiSelectForm(forms.Form):
    severity = forms.MultipleChoiceField(
        label=_("Filter by severity"),
        required=False,
        choices=FINDINGS_SEVERITIES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )


class MutedFindingSelectionForm(BaseOpenKATForm):
    muted_findings = forms.ChoiceField(
        initial="non-muted",
        label=_("Filter by muted findings"),
        required=False,
        choices=MUTED_FINDINGS_CHOICES,
        widget=forms.RadioSelect,
    )


class FindingSearchForm(BaseOpenKATForm):
    search = forms.CharField(
        label=_("Search"), required=False, max_length=256, help_text=_("Object ID contains (case sensitive)")
    )


class OrderByFindingTypeForm(BaseOpenKATForm):
    order_by = forms.CharField(widget=forms.HiddenInput(attrs={"value": "finding_type"}), required=False)


class OrderBySeverityForm(BaseOpenKATForm):
    order_by = forms.CharField(widget=forms.HiddenInput(attrs={"value": "score"}), required=False)
