from datetime import datetime
from logging import getLogger

from django.core.paginator import Paginator, Page
from django.http import FileResponse
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from account.mixins import OrganizationView
from katalogus.client import get_katalogus
from katalogus.views import PluginSettingsListView
from katalogus.views.mixins import KATalogusMixin
from katalogus.views.plugin_detail_scan_oois import PluginDetailScanOOI
from rocky import scheduler

logger = getLogger(__name__)


class PluginCoverImgView(OrganizationView):
    """Get the cover image of a plugin."""

    def get(self, request, *args, **kwargs):
        return FileResponse(get_katalogus(self.organization.code).get_cover(kwargs["plugin_id"]))


@class_view_decorator(otp_required)
class PluginDetailView(
    KATalogusMixin,
    PluginSettingsListView,
    PluginDetailScanOOI,
):
    """Detail view for a specific plugin. Shows plugin settings and consumable oois for scanning."""

    template_name = "plugin_detail.html"
    scan_history_limit = 10

    def get_scan_history(self) -> Page:
        scheduler_id = f"{self.plugin['type']}-{self.organization.code}"

        filters = [
            {
                "field": f"data__{self.plugin['type']}__id",
                "operator": "eq",
                "value": self.plugin_id,
            }
        ]

        if self.request.GET.get("scan_history_search"):
            filters.append(
                {
                    "field": "data__input_ooi",
                    "operator": "eq",
                    "value": self.request.GET.get("scan_history_search"),
                }
            )

        page = int(self.request.GET.get("scan_history_page", 1))

        status = self.request.GET.get("scan_history_status")

        min_created_at = None
        if self.request.GET.get("scan_history_from"):
            min_created_at = datetime.strptime(self.request.GET.get("scan_history_from"), "%Y-%m-%d")

        max_created_at = None
        if self.request.GET.get("scan_history_to"):
            max_created_at = datetime.strptime(self.request.GET.get("scan_history_to"), "%Y-%m-%d")

        scan_history = scheduler.client.get_lazy_task_list(
            scheduler_id=scheduler_id,
            status=status,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
            filters=filters,
        )

        return Paginator(scan_history, self.scan_history_limit).page(page)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugin"] = self.plugin
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
            {
                "url": reverse(
                    "plugin_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_type": self.plugin["type"],
                        "plugin_id": self.plugin_id,
                    },
                ),
                "text": self.plugin["name"],
            },
        ]

        context["scan_history"] = self.get_scan_history()
        context["scan_history_form_fields"] = [
            "scan_history_from",
            "scan_history_to",
            "scan_history_status",
            "scan_history_search",
            "scan_history_page",
        ]

        return context
