from datetime import datetime, timezone
from typing import List, Dict

from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from octopoes.api.models import Declaration
from octopoes.models import Reference
from octopoes.models.ooi.findings import (
    CVEFindingType,
    KATFindingType,
    Finding,
    RetireJSFindingType,
    SnykFindingType,
    FindingType,
)
from octopoes.models.types import OOI_TYPES

from rocky.views.ooi_view import BaseOOIFormView
from tools.forms import FindingAddForm
from tools.view_helpers import get_ooi_url


def get_finding_type_from_id(
    finding_type_id: str,
) -> FindingType:
    finding_type_id = finding_type_id.upper()

    if finding_type_id.upper().startswith("CVE"):
        # Fetch CVE info
        finding_type = CVEFindingType(id=finding_type_id)
    elif finding_type_id.upper().startswith("RetireJS"):
        # Fetch RetireJS info
        finding_type = RetireJSFindingType(id=finding_type_id)
    elif finding_type_id.upper().startswith("SNYK"):
        # Fetch RetireJS info
        finding_type = SnykFindingType(id=finding_type_id)
    else:
        finding_type = KATFindingType(id=finding_type_id)

    return finding_type


class FindingAddView(BaseOOIFormView):
    template_name = "findings/finding_add.html"
    form_class = FindingAddForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.initial = {"ooi_id": request.GET.get("ooi_id")}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {"url": reverse("finding_list"), "text": "Findings"},
            {"url": reverse("finding_add"), "text": _("Add Finding")},
        ]

        return context

    def get_form_kwargs(self):
        kwargs = {
            "connector": self.get_api_connector(),
            "ooi_list": self.get_ooi_options(),
        }
        kwargs.update(super().get_form_kwargs())

        if "ooi_class" in kwargs:
            del kwargs["ooi_class"]

        return kwargs

    def get_form(self, form_class=None) -> FindingAddForm:
        if form_class is None:
            form_class = self.get_form_class()

        return form_class(**self.get_form_kwargs())

    def form_valid(self, form):
        form_data = form.cleaned_data

        ooi_id = form_data["ooi_id"]

        s: str = form_data["finding_type_ids"]
        finding_type_ids = s.replace(",", "\n").splitlines()
        finding_type_ids = [
            x.strip()
            for x in finding_type_ids
            if x.strip().startswith(("KAT-", "CVE-", "CWE-"))
        ]

        observed_at = datetime.combine(
            form_data.get("date"), datetime.min.time(), tzinfo=timezone.utc
        )

        # Create finding for each finding type
        ooi_ref = Reference.from_str(ooi_id)
        oois = []

        for f_id in finding_type_ids:
            finding_type = get_finding_type_from_id(f_id)
            finding = Finding(
                ooi=ooi_ref,
                finding_type=finding_type.reference,
                proof=form_data.get("proof"),
                description=form_data.get("description"),
                reproduce=form_data.get("reproduce"),
            )
            self.api_connector.save_declaration(
                Declaration(ooi=finding, valid_time=observed_at)
            )
            self.api_connector.save_declaration(
                Declaration(ooi=finding_type, valid_time=observed_at)
            )

        return redirect(get_ooi_url("ooi_detail", ooi_id))

    def get_ooi_options(self) -> List[Dict[str, str]]:
        # Query to render form options
        ooi_set = set(OOI_TYPES.values()).difference({Finding, FindingType})
        objects = self.api_connector.list(ooi_set)

        # generate options
        options = [(o.primary_key, o.get_ooi_type()) for o in objects]

        return options
