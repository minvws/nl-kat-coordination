from django import forms

from octopoes.models.ooi.findings import RiskLevelSeverity

FINDING_SEVERITIES_CHOICES = (
    (str(severity.name).lower(), str(severity.value).lower()) for severity in RiskLevelSeverity
)


class FindingSeveritiesForm(forms.Form):
    severity = forms.MultipleChoiceField(
        required=False,
        choices=FINDING_SEVERITIES_CHOICES,
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["severity"].label = ""
