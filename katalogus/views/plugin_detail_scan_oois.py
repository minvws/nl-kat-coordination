from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from octopoes.models.types import type_by_name

from rocky.views import OrganizationIndemnificationMixin, verify_may_update_scan_profile
from tools.forms import SelectOOIForm, SelectOOIFilterForm
from katalogus.views.mixins import BoefjeMixin


@class_view_decorator(otp_required)
class PluginDetailScanOOI(BoefjeMixin, TemplateView, OrganizationIndemnificationMixin):
    limit_ooi_list = 9999

    def post(self, request, *args, **kwargs):
        if not verify_may_update_scan_profile(self.request):
            return self.get(request, *args, **kwargs)

        """Start scanning oois at plugin detail page."""
        selected_oois = request.POST.getlist("ooi")
        plugin_id = request.POST.get("boefje_id")
        if selected_oois and plugin_id:
            boefje = self.katalogus_client.get_boefje(plugin_id)
            oois_with_clearance_level = self.get_oois_with_clearance_level(selected_oois)
            if oois_with_clearance_level:
                self.run_boefje_for_oois(
                    boefje=boefje,
                    oois=oois_with_clearance_level,
                    organization=self.organization,
                    api_connector=self.get_api_connector(),
                )
            oois_without_clearance_level = self.get_oois_without_clearance_level(selected_oois)
            if oois_without_clearance_level:
                request.session["selected_oois"] = oois_without_clearance_level
                return redirect(
                    reverse(
                        "change_clearance_level",
                        kwargs={
                            "plugin_type": self.plugin["type"],
                            "plugin_id": plugin_id,
                            "scan_level": self.plugin["scan_level"],
                        },
                    )
                )
        else:
            messages.add_message(self.request, messages.ERROR, _("Scanning has failed to start."))
            return self.get(request, *args, **kwargs)
        messages.add_message(self.request, messages.SUCCESS, _("Scanning successfully scheduled."))
        return redirect(reverse("task_list"))

    def get_form_consumable_oois(self):
        """Get all available OOIS that plugin can consume."""
        ooi_types = self.plugin["consumes"]
        ooi_types = {type_by_name(ooi_type) for ooi_type in ooi_types}
        oois = self.get_api_connector().list(ooi_types, limit=self.limit_ooi_list)
        return oois.items

    def get_form_filtered_consumable_oois(self):
        """Return a list of oois that is filtered for oois that meets clearance level."""
        oois = self.get_form_consumable_oois()
        return [ooi for ooi in oois if ooi.scan_profile.level >= self.plugin["scan_level"]]

    def get_oois_with_clearance_level(self, selected_oois):
        """Return a list of selected oois that meets clearance level."""
        oois_with_clearance_level = []
        for ooi in selected_oois:
            ooi_object = self.get_single_ooi(ooi)
            if ooi_object.scan_profile.level >= self.plugin["scan_level"]:
                oois_with_clearance_level.append(ooi_object)
        return oois_with_clearance_level

    def get_oois_without_clearance_level(self, selected_oois):
        """Return a list from selected oois without clearance level for scanning"""
        oois_without_clearance_level = []
        for ooi in selected_oois:
            ooi_object = self.get_single_ooi(ooi)
            if ooi_object.scan_profile.level < self.plugin["scan_level"]:
                oois_without_clearance_level.append(ooi_object.primary_key)
        return oois_without_clearance_level

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["select_ooi_filter_form"] = SelectOOIFilterForm
        if "show_all" in self.request.GET:
            context["select_oois_form"] = SelectOOIForm(oois=self.get_form_consumable_oois())
        else:
            context["select_oois_form"] = SelectOOIForm(oois=self.get_form_filtered_consumable_oois())
        return context
