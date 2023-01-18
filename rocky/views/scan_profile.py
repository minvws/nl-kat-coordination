from datetime import datetime, timezone
from typing import Dict, Any, List

from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from octopoes.models import InheritedScanProfile, EmptyScanProfile, DeclaredScanProfile

from rocky.views.ooi_detail import OOIDetailView
from tools.forms.ooi import SetClearanceLevelForm
from tools.models import Indemnification, OrganizationMember

from tools.view_helpers import (
    get_mandatory_fields,
    get_ooi_url,
    Breadcrumb,
)


@class_view_decorator(otp_required)
class ScanProfileDetailView(OOIDetailView, FormView):
    template_name = "scan_profiles/scan_profile_detail.html"
    form_class = SetClearanceLevelForm

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code),
                "text": _("Scan profile"),
            }
        )
        return breadcrumbs

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["user"] = OrganizationMember.objects.get(user=self.request.user, organization=self.organization)
        context["organization_indemnification"] = Indemnification.objects.filter(
            organization=self.organization
        ).exists()
        return context

    def post(self, request, *args, **kwargs):
        if not self.verify_may_update_scan_profile():
            return self.get(request, *args, **kwargs)

        super().post(request, *args, **kwargs)
        form = self.get_form()
        if form.is_valid():

            level = form.cleaned_data["level"]
            if (
                level > self.organization_member.trusted_clearance_level
                or level > self.organization_member.acknowledged_clearance_level
            ):
                messages.add_message(
                    request,
                    messages.ERROR,
                    _(
                        "You do not have clearance for level %s. \
                        You are trusted with clearance level %s and you acknowledged a clearance level of %s."
                    )
                    % (
                        level,
                        self.organization_member.trusted_clearance_level,
                        self.organization_member.acknowledged_clearance_level,
                    ),
                )
            else:
                self.api_connector.save_scan_profile(
                    DeclaredScanProfile(
                        reference=self.ooi.reference,
                        level=level,
                    ),
                    valid_time=datetime.now(timezone.utc),
                )
        else:
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Choose a valid level").format(ooi_name=self.ooi.human_readable),
            )
        return redirect(get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code))

    def get_initial(self):
        initial = super().get_initial()

        if not isinstance(self.ooi.scan_profile, InheritedScanProfile):
            initial["level"] = self.ooi.scan_profile.level

        return initial


class ScanProfileResetView(OOIDetailView):
    template_name = "scan_profiles/scan_profile_reset.html"

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)
        if self.ooi.scan_profile.scan_profile_type != "declared":
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Can not reset scan level. Scan level of {ooi_name} not declared").format(
                    ooi_name=self.ooi.human_readable
                ),
            )
            return redirect(get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code))

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.api_connector.save_scan_profile(
            EmptyScanProfile(reference=self.ooi.reference),
            valid_time=datetime.now(timezone.utc),
        )
        return redirect(get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code))

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        breadcrumbs = super().build_breadcrumbs()
        breadcrumbs.append(
            {
                "url": get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code),
                "text": _("Reset"),
            }
        )
        return breadcrumbs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        return context
