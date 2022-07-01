import json, csv
from django.http import HttpResponse, Http404
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy
from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.types import get_collapsed_types
from rocky.views import BaseOOIListView
from tools.view_helpers import BreadcrumbsMixin


class OOIListView(BreadcrumbsMixin, BaseOOIListView):
    breadcrumbs = [{"url": reverse_lazy("ooi_list"), "text": _("Objects")}]
    template_name = "oois/ooi_list.html"
    ooi_types = get_collapsed_types().difference({Finding, FindingType})

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.filtered_ooi_types = self.get_filtered_ooi_types()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["types_display"] = self.get_ooi_types_display()
        context["object_type_filters"] = self.get_ooi_type_filters()

        return context


class OOIListExportView(OOIListView):
    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        file_type = request.GET.get("file_type")
        observed_at = self.get_observed_at()
        filters = self.get_ooi_types_display()
        ooi_list = self.get_list(observed_at)
        exports = [
            {
                "observed_at": str(observed_at),
                "filters": str(filters),
            }
        ]

        for ooi in ooi_list:
            exports.append(
                {
                    "key": ooi.primary_key,
                    "name": ooi.human_readable,
                    "ooi_type": ooi.ooi_type,
                }
            )

        if file_type == "json":

            response = HttpResponse(
                json.dumps(exports),
                content_type="application/json",
                headers={
                    "Content-Disposition": "attachment; filename=ooi_list_"
                    + str(observed_at)
                    + ".json"
                },
            )

            return response

        elif file_type == "csv":

            response = HttpResponse(
                content_type="text/csv",
                headers={
                    "Content-Disposition": "attachment; filename=ooi_list_"
                    + str(observed_at)
                    + ".csv"
                },
            )

            writer = csv.writer(response)
            writer.writerow(["observed_at", "filters"])
            writer.writerow([str(observed_at), str(filters)])
            writer.writerow(["key", "name", "ooi_type"])
            for ooi in ooi_list:
                writer.writerow(
                    [
                        ooi.primary_key,
                        ooi.human_readable,
                        ooi.ooi_type,
                    ]
                )

            return response

        else:

            raise Http404("Export type not found")
