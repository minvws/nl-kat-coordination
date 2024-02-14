from django.http import HttpResponse
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View
from django.views.generic.detail import DetailView
from tools.view_helpers import Breadcrumb

from fmea.models import (
    DEPARTMENTS,
    FailureMode,
    FailureModeAffectedObject,
)
from fmea.tools import html_to_pdf
from fmea.views.view_helpers import FMEABreadcrumbsMixin


class FailureModeReportView(FMEABreadcrumbsMixin, DetailView):
    """
    View for a report based on a failure mode
    """

    template_name = "fmea/fmea_failure_mode_report.html"

    def get_failure_mode_affected_object(self, **kwargs):
        failure_mode = self.get_object().failure_mode
        failure_mode_affected_objects = FailureModeAffectedObject.objects.filter(
            failure_mode__failure_mode__contains=failure_mode
        )
        return failure_mode_affected_objects

    def build_breadcrumbs(self) -> list[dict[str, str]]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "text": _("Report"),
                "url": reverse("fmea_failure_mode_report", kwargs={"pk": self.kwargs["pk"]}),
            }
        )
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["failure_mode_affected_departments"] = self.get_failure_mode_affected_object(**kwargs).values(
            "affected_department"
        )
        context["failure_mode_affected_ooi_types"] = self.get_failure_mode_affected_object(**kwargs).values(
            "affected_ooi_type"
        )
        return context


class GenerateFailureModePDF(View):
    def get(self, request, *args, **kwargs):
        template = "fmea/fmea_failure_mode_report.html"
        pdf = html_to_pdf(template)
        return HttpResponse(pdf, content_type="application/pdf")


class FMEADepartmentHeatmapView(FMEABreadcrumbsMixin, TemplateView):
    template_name = "fmea/fmea_department_heatmap.html"

    def populate_heatmap_data(self):
        heatmap_data = []
        failure_mode_data = []
        failure_mode_objects = FailureMode.objects.all()
        for failure_mode in failure_mode_objects:
            failure_mode_data = {}
            failure_mode_affected_objects = FailureModeAffectedObject.objects.filter(
                failure_mode__failure_mode__contains=failure_mode.failure_mode
            )
            failure_mode_data["failure_mode"] = failure_mode.failure_mode
            failure_mode_data["risk_class"] = failure_mode.risk_class
            affected_departments = []
            for affected_objects in failure_mode_affected_objects:
                affected_departments.append(affected_objects.affected_department)
            failure_mode_data["affected_departments"] = affected_departments
            heatmap_data.append(failure_mode_data)
        return heatmap_data

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append({"text": _("Heatmap"), "url": reverse("fmea_department_heatmap")})
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["heatmap_data"] = self.populate_heatmap_data()
        context["departments"] = DEPARTMENTS
        return context
