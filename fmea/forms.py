from django import forms
from django.utils.translation import gettext_lazy as _
from fmea.models import (
    FailureMode,
    FailureModeAffectedObject,
    FailureModeEffect,
)
from fmea.tools import OOI_TYPES, translated_blank_choice, calculate_risk_class
from tools.forms import CheckboxGroup


class FailureModeForm(forms.ModelForm):
    """
    With this form you can create or edit a failure mode for FMEA.
    """

    class Meta:
        model = FailureMode

        fields = [
            "failure_mode",
            "description",
            "frequency_level",
            "detectability_level",
            "effect",
            "risk_class",
        ]

        labels = {
            "failure mode": _("Failure mode"),
            "description": _("Description"),
            "frequency_level": _("Frequency Level"),
            "detectability_level": _("Detectability Level"),
            "effect": _("Effect(s)"),
        }

        help_texts = {
            "failure_mode": _(
                "Describe in one sentence what type of failure mode you are creating."
            ),
            "description": _("Describe the failure mode in details."),
            "frequency_level": _(
                "From 1 to 5, how often does this failure mode occurs. 1: Almost unthinkable and 5: occurs daily."
            ),
            "detectability_level": _(
                "Is this failure mode easy detectable? Give it a score from 1 to 5. 1: always detectable and 5: almost undetectable."
            ),
        }

        widgets = {
            "failure_mode": forms.Textarea(
                attrs={
                    "rows": 1,
                    "placeholder": _("Describe the type of failure mode"),
                    "aria-describedby": _("explanation-failure-mode"),
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 2,
                    "placeholder": _(
                        "Describe in more detail what the failure mode is about."
                    ),
                    "aria-describedby": _("explanation-description"),
                }
            ),
            "frequency_level": forms.Select(
                attrs={
                    "aria-describedby": _("explanation-frequency-level"),
                },
            ),
            "detectability_level": forms.Select(
                attrs={
                    "aria-describedby": _("explanation-detectability_level"),
                },
            ),
            "effect": CheckboxGroup(toggle_all_button=False),
            "risk_class": forms.Textarea(attrs={"rows": 1, "readonly": ""}),
        }

        error_messages = {
            "failure_mode": {
                "required": _("You must at least set a failure mode."),
            },
            "frequency_level": {
                "required": _("Choose a frequency level."),
            },
            "detectability_level": {
                "required": _("Choose a detectability level."),
            },
            "effect": {
                "required": _("Choose at least one effect."),
            },
        }

    def clean(self):
        if (
            "effect" in self.cleaned_data
            and "frequency_level" in self.cleaned_data
            and "detectability_level" in self.cleaned_data
        ):
            frequency_level = self.cleaned_data["frequency_level"]
            detectability_level = self.cleaned_data["detectability_level"]
            all_severity_levels = [
                effect.severity_level for effect in self.cleaned_data["effect"]
            ]
            highest_severity_level = max(all_severity_levels)
            risk_class = calculate_risk_class(
                frequency_level, detectability_level, highest_severity_level
            )
            self.cleaned_data["risk_class"] = risk_class.value
        return self.cleaned_data


class FailureModeAffectedObjectForm(forms.ModelForm):
    """
    With this form you can create or edit the impact a failure  .
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["failure_mode"].empty_label = translated_blank_choice

    class Meta:
        model = FailureModeAffectedObject
        fields = ["failure_mode", "affected_department", "affected_ooi_type"]

        labels = {
            "failure mode": _("Failure mode"),
            "affected_department": _("Affected Department"),
            "affected_ooi_type": _("Affected Objects"),
        }
        help_texts = {
            "failure_mode": _("Choose a failure mode which applies to "),
            "affected_department": _(
                "When this failure mode occurs, which department is affected?"
            ),
            "affected_ooi_type": _(
                "Which objects does this failure mode affect when it occurs?"
            ),
        }
        widgets = {
            "affected_ooi_type": forms.Select(
                choices=OOI_TYPES,
                attrs={
                    "aria-describedby": _("explanation-affected-ooi-type"),
                },
            ),
        }


class FailureModeEffectForm(forms.ModelForm):
    class Meta:
        model = FailureModeEffect
        fields = ["effect", "severity_level"]

        labels = {
            "effect": _("Effect"),
            "severity_level": _("Severity Level"),
        }

        help_texts = {
            "effect": _(
                "Name a possible effect of any type of failure mode that can occur."
            ),
            "severity_level": _(
                "Describe the severity of this effect ex. 1: not severe and 5: catastrophic"
            ),
        }

        widgets = {
            "effect": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": _("Describe a possible effect for FMEA"),
                    "aria-describedby": _("explanation-effect"),
                }
            ),
            "severity_level": forms.Select(
                attrs={
                    "aria-describedby": _("explanation-severity-level"),
                },
            ),
        }

        error_messages = {
            "effect": {
                "required": _("The effect is required."),
                "unique": _("This effect already exists."),
            },
            "severity_level": {
                "required": _("Choose a severity level."),
            },
        }
