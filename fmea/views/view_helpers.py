from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from tools.view_helpers import BreadcrumbsMixin, StepsMixin


class FMEABreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"text": _("FMEA"), "url": reverse_lazy("fmea_intro")},
    ]


class FailureModeBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"text": _("FMEA"), "url": reverse_lazy("fmea_intro")},
        {"text": _("Failure modes"), "url": reverse_lazy("fmea_failure_mode_list")},
    ]


class FailureModeEffectBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"text": _("FMEA"), "url": reverse_lazy("fmea_intro")},
        {
            "text": _("Failure mode effects"),
            "url": reverse_lazy("fmea_failure_mode_effect_list"),
        },
    ]


class AffectedObjectBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"text": _("FMEA"), "url": reverse_lazy("fmea_intro")},
        {
            "text": _("Failure Mode Affected Objects"),
            "url": reverse_lazy("fmea_failure_mode_affected_object_list"),
        },
    ]
