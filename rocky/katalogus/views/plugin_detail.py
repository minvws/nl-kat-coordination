from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from account.mixins import OrganizationView
from django.contrib import messages
from django.core.exceptions import BadRequest
from django.core.paginator import Page, Paginator
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from tools.forms.ooi import SelectOOIFilterForm, SelectOOIForm

from katalogus.client import get_katalogus
from katalogus.views.mixins import BoefjeMixin
from katalogus.views.plugin_settings_list import PluginSettingsListView
from rocky import scheduler

logger = getLogger(__name__)


class PluginCoverImgView(OrganizationView):
    """Get the cover image of a plugin."""

    def get(self, request, *args, **kwargs):
        file = FileResponse(get_katalogus(self.organization.code).get_cover(kwargs["plugin_id"]))
        file.headers["Cache-Control"] = "max-age=604800"
        return file


class PluginDetailView(PluginSettingsListView, TemplateView):
    task_history_limit = 10

    def get_task_history(self) -> Page:
        scheduler_id = f"{self.plugin.type}-{self.organization.code}"
        plugin_type = self.plugin.type
        plugin_id = self.plugin.id
        input_ooi = self.request.GET.get("task_history_search")
        status = self.request.GET.get("task_history_status")

        if self.request.GET.get("task_history_from"):
            min_created_at = datetime.strptime(self.request.GET.get("task_history_from"), "%Y-%m-%d")
        else:
            min_created_at = None

        if self.request.GET.get("task_history_to"):
            max_created_at = datetime.strptime(self.request.GET.get("task_history_to"), "%Y-%m-%d")
        else:
            max_created_at = None

        page = int(self.request.GET.get("task_history_page", 1))

        task_history = scheduler.client.get_lazy_task_list(
            scheduler_id=scheduler_id,
            task_type=plugin_type,
            plugin_id=plugin_id,
            input_ooi=input_ooi,
            status=status,
            min_created_at=min_created_at,
            max_created_at=max_created_at,
        )

        return Paginator(task_history, self.task_history_limit).page(page)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["plugin"] = self.plugin.dict()
        context["task_history"] = self.get_task_history()
        context["task_history_form_fields"] = [
            "task_history_from",
            "task_history_to",
            "task_history_status",
            "task_history_search",
            "task_history_page",
        ]

        return context


class NormalizerDetailView(PluginDetailView):
    template_name = "normalizer_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
            {
                "url": reverse(
                    "normalizer_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                    },
                ),
                "text": self.plugin.name,
            },
        ]

        return context


class BoefjeDetailView(BoefjeMixin, PluginDetailView):
    """Detail view for a specific boefje. Shows boefje settings and consumable oois for scanning."""

    template_name = "boefje_detail.html"
    limit_ooi_list = 9999

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["select_ooi_filter_form"] = SelectOOIFilterForm
        if "show_all" in self.request.GET:
            context["select_oois_form"] = SelectOOIForm(
                oois=self.get_form_consumable_oois(), organization_code=self.organization.code
            )
        else:
            context["select_oois_form"] = SelectOOIForm(
                oois=self.get_form_filtered_consumable_oois(), organization_code=self.organization.code
            )
        context["plugin"] = self.plugin.dict()
        context["breadcrumbs"] = [
            {
                "url": reverse("katalogus", kwargs={"organization_code": self.organization.code}),
                "text": _("KAT-alogus"),
            },
            {
                "url": reverse(
                    "boefje_detail",
                    kwargs={
                        "organization_code": self.organization.code,
                        "plugin_id": self.plugin.id,
                    },
                ),
                "text": self.plugin.name,
            },
        ]

        return context

    def post(self, request, *args, **kwargs):
        """Start scanning oois at plugin detail page."""
        if not self.indemnification_present:
            return self.get(request, *args, **kwargs)

        if "boefje_id" not in request.POST:
            raise BadRequest("No boefje_id provided")

        selected_oois = request.POST.getlist("ooi")
        plugin_id = request.POST["boefje_id"]
        if selected_oois and plugin_id:
            oois = self.get_oois(selected_oois)
            boefje = self.katalogus_client.get_plugin(plugin_id)

            oois_with_clearance_level = oois["oois_with_clearance"]
            oois_without_clearance_level = oois["oois_without_clearance"]

            if oois_with_clearance_level:
                self.run_boefje_for_oois(
                    boefje=boefje,
                    oois=oois_with_clearance_level,
                )

            if oois_without_clearance_level:
                if not self.organization_member.has_perm("tools.can_set_clearance_level"):
                    messages.add_message(
                        self.request,
                        messages.ERROR,
                        _(
                            "Some selected OOIs needs an increase of clearance level to perform scans."
                            " You do not have the permission to change clearance level."
                        ),
                    )
                else:
                    request.session["selected_oois"] = oois_without_clearance_level
                    return redirect(
                        reverse(
                            "change_clearance_level",
                            kwargs={
                                "organization_code": self.organization.code,
                                "plugin_id": plugin_id,
                                "scan_level": self.plugin.scan_level.value,
                            },
                        )
                    )
            return redirect(reverse("task_list", kwargs={"organization_code": self.organization.code}))

        messages.add_message(self.request, messages.ERROR, _("Please select an OOI to start scan."))
        return self.get(request, *args, **kwargs)

    def get_form_consumable_oois(self):
        """Get all available OOIS that plugin can consume."""
        return self.octopoes_api_connector.list(self.plugin.consumes, limit=self.limit_ooi_list).items

    def get_form_filtered_consumable_oois(self):
        """Return a list of oois that is filtered for oois that meets clearance level."""
        oois = self.get_form_consumable_oois()
        return [ooi for ooi in oois if ooi.scan_profile.level >= self.plugin.scan_level.value]

    def get_oois(self, selected_oois: List[str]) -> Dict[str, Any]:
        oois_with_clearance = []
        oois_without_clearance = []
        for ooi in selected_oois:
            ooi_object = self.get_single_ooi(pk=ooi)
            if ooi_object.scan_profile.level >= self.plugin.scan_level.value:
                oois_with_clearance.append(ooi_object)
            else:
                oois_without_clearance.append(ooi_object.primary_key)
        return {
            "oois_with_clearance": oois_with_clearance,
            "oois_without_clearance": oois_without_clearance,
        }
