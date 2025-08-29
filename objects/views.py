import datetime
from datetime import timezone
from enum import Enum

from django.urls import reverse
from django.views.generic import ListView
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from octopoes.models.ooi.findings import Finding, FindingType
from octopoes.models.ooi.reports import BaseReport, Report, ReportRecipe, AssetReport, ReportData, HydratedReport
from octopoes.models.types import get_collapsed_types
from openkat.enums import CUSTOM_SCAN_LEVEL
from openkat.forms.ooi_form import OOISearchForm, OOITypeMultiCheckboxForm, _EXCLUDED_OOI_TYPES
from openkat.models import Organization, OrganizationMember
from openkat.view_helpers import get_mandatory_fields
from openkat.views.mixins import OOIList


class PageActions(Enum):
    DELETE = "delete"
    UPDATE_SCAN_PROFILE = "update-scan-profile"


class ObjectListView(ListView):
    template_name = "object_list.html"
    paginate_by = settings.VIEW_DEFAULT_PAGE_SIZE

    def get_queryset(self):
        # TODO: handle
        organization = Organization.objects.first()

        return OOIList(settings.OCTOPOES_FACTORY(organization.code), **self.get_queryset_params())

    def get_queryset_params(self):
        return {
            "valid_time": datetime.datetime.now(timezone.utc),
            "ooi_types": {t for t in get_collapsed_types().difference(
                {Finding, FindingType, BaseReport, Report, ReportRecipe, AssetReport, ReportData, HydratedReport}
            ) if t not in _EXCLUDED_OOI_TYPES},
            "scan_level": settings.DEFAULT_SCAN_LEVEL_FILTER,
            "scan_profile_type": settings.DEFAULT_SCAN_PROFILE_TYPE_FILTER,
            "search_string": "",
            "order_by": "scan_level" if self.request.GET.get("order_by", "") == "scan_level" else "object_type",
            "asc_desc": "desc" if self.request.GET.get("sorting_order", "") == "desc" else "asc",
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [{"url": reverse("object_list"), "text": _("Objects")}]

        context["ooi_type_form"] = OOITypeMultiCheckboxForm(self.request.GET)
        context["ooi_search_form"] = OOISearchForm(self.request.GET)
        context["mandatory_fields"] = get_mandatory_fields(self.request, params=["observed_at"])
        context["member"] = self.request.user
        context["scan_levels"] = [alias for _, alias in CUSTOM_SCAN_LEVEL.choices]

        # TODO: handle
        context["organization"] = Organization.objects.first()
        context["may_update_clearance_level"] = True

        return context
