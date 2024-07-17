from datetime import datetime, timezone
from logging import getLogger
from typing import Any

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from tools.forms.ooi import SelectOOIFilterForm, SelectOOIForm

from katalogus.client import Boefje, Normalizer, get_katalogus
from katalogus.views.plugin_settings_list import PluginSettingsListView
from rocky.views.tasks import TaskListView

logger = getLogger(__name__)


class PluginCoverImgView(OrganizationView):
    """Get the cover image of a plugin."""

    def get(self, request, *args, **kwargs):
        file = FileResponse(get_katalogus(self.organization.code).get_cover(kwargs["plugin_id"]))
        file.headers["Cache-Control"] = "max-age=604800"
        return file


class PluginDetailView(TaskListView, PluginSettingsListView):
    def post(self, request, *args, **kwargs):
        if self.action == self.SCAN_OOIS:
            selected_oois = request.POST.getlist("ooi", [])

            if selected_oois and self.plugin.id:
                oois = self.get_oois(selected_oois)
                boefje = self.katalogus_client.get_plugin(self.plugin.id)

                oois_with_clearance_level = oois["oois_with_clearance"]
                oois_without_clearance_level = oois["oois_without_clearance"]

                if oois_with_clearance_level:
                    self.run_boefje_for_oois(
                        boefje=boefje,
                        oois=oois_with_clearance_level,
                    )

                if oois_without_clearance_level:
                    if not self.organization_member.has_perm("tools.can_set_clearance_level"):
                        messages.error(
                            request,
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
                                    "plugin_type": "boefje",
                                    "organization_code": self.organization.code,
                                    "plugin_id": self.plugin.id,
                                    "scan_level": self.plugin.scan_level.value,
                                },
                            )
                        )
        return super().post(request, *args, **kwargs)

    def get_task_filters(self) -> dict[str, str | datetime | None]:
        filters = super().get_task_filters()
        filters["plugin_id"] = self.plugin.id  # fetch only tasks for a specific plugin by id
        return filters

    def get_oois(self, selected_oois: list[str]) -> dict[str, Any]:
        oois_with_clearance = []
        oois_without_clearance = []
        for ooi in selected_oois:
            ooi_object = self.get_single_ooi(pk=ooi)
            if ooi_object.scan_profile and ooi_object.scan_profile.level >= self.plugin.scan_level.value:
                oois_with_clearance.append(ooi_object)
            else:
                oois_without_clearance.append(ooi_object.primary_key)
        return {
            "oois_with_clearance": oois_with_clearance,
            "oois_without_clearance": oois_without_clearance,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["plugin"] = self.plugin.model_dump()
        context["plugin_settings"] = self.get_plugin_settings()
        return context


class NormalizerDetailView(PluginDetailView):
    template_name = "normalizer_detail.html"
    plugin: Normalizer
    task_type = "normalizer"

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


class BoefjeDetailView(PluginDetailView):
    """Detail view for a specific boefje. Shows boefje settings and consumable oois for scanning."""

    template_name = "boefje_detail.html"
    limit_ooi_list = 9999
    plugin: Boefje
    task_type = "boefje"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["select_ooi_filter_form"] = SelectOOIFilterForm
        if "show_all" in self.request.GET:
            context["select_oois_form"] = SelectOOIForm(
                oois=self.get_form_consumable_oois(),
                organization_code=self.organization.code,
            )
        else:
            context["select_oois_form"] = SelectOOIForm(
                oois=self.get_form_filtered_consumable_oois(),
                organization_code=self.organization.code,
            )

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

    def get_form_consumable_oois(self):
        """Get all available OOIS that plugin can consume."""
        return self.octopoes_api_connector.list_objects(
            self.plugin.consumes,
            valid_time=datetime.now(timezone.utc),
            limit=self.limit_ooi_list,
        ).items

    def get_form_filtered_consumable_oois(self):
        """Return a list of oois that is filtered for oois that meets clearance level."""
        oois = self.get_form_consumable_oois()
        return [ooi for ooi in oois if ooi.scan_profile.level >= self.plugin.scan_level.value]
