from datetime import datetime, timezone
from uuid import uuid4

from django.shortcuts import redirect
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView

from account.mixins import OrganizationView
from octopoes.api.models import Declaration
from octopoes.models.ooi.findings import KATFindingType
from openkat.forms.finding_type import FindingTypeAddForm
from openkat.view_helpers import get_ooi_url


class FindingTypeAddView(OrganizationView, FormView):
    template_name = "finding_type_add.html"
    form_class = FindingTypeAddForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["breadcrumbs"] = [
            {
                "url": reverse("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            },
            {
                "url": reverse("finding_type_add", kwargs={"organization_code": self.organization.code}),
                "text": _("Add finding type"),
            },
        ]

        return context

    def form_valid(self, form):
        self.api_connector = self.octopoes_api_connector
        form_data = form.cleaned_data
        finding_type = KATFindingType(id=form_data["id"])

        task_id = uuid4()
        declaration = Declaration(ooi=finding_type, valid_time=datetime.now(timezone.utc), task_id=str(task_id))
        self.api_connector.save_declaration(declaration)

        return redirect(get_ooi_url("ooi_detail", finding_type.primary_key, self.organization.code))
