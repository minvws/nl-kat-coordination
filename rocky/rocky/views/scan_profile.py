from datetime import datetime, timezone
from typing import Any, Dict, List

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from tools.forms.ooi import SetClearanceLevelForm
from tools.models import Indemnification
from tools.view_helpers import (
    Breadcrumb,
    get_mandatory_fields,
    get_ooi_url,
)

from octopoes.models import EmptyScanProfile, InheritedScanProfile
from rocky.exceptions import (
    AcknowledgedClearanceLevelTooLowException,
    IndemnificationNotPresentException,
    TrustedClearanceLevelTooLowException,
)
from rocky.views.ooi_detail import OOIDetailView


class ScanProfileDetailView(OOIDetailView, FormView):
    template_name = "scan_profiles/scan_profile_detail.html"
    form_class = SetClearanceLevelForm

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["user"] = self.organization_member
        context["organization_indemnification"] = Indemnification.objects.filter(
            organization=self.organization
        ).exists()
        return context

    def post(self, request, *args, **kwargs):
        if not self.indemnification_present:
            return self.get(request, status_code=403, *args, **kwargs)

        super().post(request, *args, **kwargs)
        form = self.get_form()
        if form.is_valid():
            level = form.cleaned_data["level"]
            try:
                self.raise_clearance_level(self.ooi.reference, level)
            except IndemnificationNotPresentException:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    _(
                        "Could not raise clearance level of %s to L%s. \
                        Indemnification not present at organization %s."
                    )
                    % (
                        self.ooi.reference.human_readable,
                        level,
                        self.organization.name,
                    ),
                )
                return self.get(request, status=403, *args, **kwargs)
            except TrustedClearanceLevelTooLowException:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    _(
                        "Could not raise clearance level of %s to L%s. "
                        "You were trusted a clearance level of L%s. "
                        "Contact your administrator to receive a higher clearance."
                    )
                    % (
                        self.ooi.reference.human_readable,
                        level,
                        self.organization_member.trusted_clearance_level,
                    ),
                )
                return self.get(request, status=403, *args, **kwargs)
            except AcknowledgedClearanceLevelTooLowException:
                messages.add_message(
                    self.request,
                    messages.ERROR,
                    _(
                        "Could not raise clearance level of %s to L%s. "
                        "You acknowledged a clearance level of L%s. "
                        "Please accept the clearance level below to proceed."
                    )
                    % (
                        self.ooi.reference.human_readable,
                        level,
                        self.organization_member.acknowledged_clearance_level,
                    ),
                )
                return redirect(reverse("account_detail", kwargs={"organization_code": self.organization.code}))

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
        result = super().get(request, *args, **kwargs)
        if self.ooi.scan_profile.scan_profile_type != "declared":
            messages.add_message(
                self.request,
                messages.WARNING,
                _("Can not reset scan level. Scan level of {ooi_name} not declared").format(
                    ooi_name=self.ooi.human_readable
                ),
            )
            return redirect(get_ooi_url("scan_profile_detail", self.ooi.primary_key, self.organization.code))

        return result

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        self.octopoes_api_connector.save_scan_profile(
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
