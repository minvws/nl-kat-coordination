from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from tools.view_helpers import StepsMixin

from reports.views.base import get_selection


class KatGenerateReportStepsMixin(StepsMixin):
    def build_steps(self):
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        steps = [
            {
                "text": _("1: Select objects"),
                "url": reverse_lazy("generate_report_select_oois", kwargs=kwargs) + selection,
            },
            {
                "text": _("2: Choose report types"),
                "url": reverse_lazy("generate_report_select_report_types", kwargs=kwargs) + selection,
            },
            {
                "text": _("3: Configuration"),
                "url": reverse_lazy("generate_report_setup_scan", kwargs=kwargs) + selection,
            },
        ]
        return steps


class KatAggregateReportStepsMixin(StepsMixin):
    def build_steps(self):
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        steps = [
            {
                "text": _("1: Select objects"),
                "url": reverse_lazy("aggregate_report_select_oois", kwargs=kwargs) + selection,
            },
            {
                "text": _("2: Choose report types"),
                "url": reverse_lazy("aggregate_report_select_report_types", kwargs=kwargs) + selection,
            },
            {
                "text": _("3: Configuration"),
                "url": reverse_lazy("aggregate_report_setup_scan", kwargs=kwargs) + selection,
            },
        ]
        return steps


class KatMultiReportStepsMixin(StepsMixin):
    def build_steps(self):
        kwargs = self.get_kwargs()
        selection = get_selection(self.request)
        steps = [
            {
                "text": _("1: Select objects"),
                "url": reverse_lazy("multi_report_select_oois", kwargs=kwargs) + selection,
            },
            {
                "text": _("2: Choose report types"),
                "url": reverse_lazy("multi_report_select_report_types", kwargs=kwargs) + selection,
            },
        ]
        return steps
