from datetime import timezone, datetime
from typing import List, Union

from django.urls.base import reverse
from django.views.generic import TemplateView
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator

from octopoes.connector import RemoteException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.ooi.findings import Finding
from rocky.settings import OCTOPOES_API
from rocky.views.ooi_report import build_findings_list_from_store
from rocky.views.ooi_view import ConnectorFormMixin
from tools.forms.base import ObservedAtForm
from tools.models import Organization, OrganizationMember
from tools.view_helpers import BreadcrumbsMixin, convert_date_to_datetime


class CrisisRoomBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": "", "text": "Crisis Room"},
    ]


@class_view_decorator(otp_required)
class CrisisRoomView(CrisisRoomBreadcrumbsMixin, ConnectorFormMixin, TemplateView):
    ooi_types = {Finding}
    template_name = "crisis_room/crisis_room.html"
    connector_form_class = ObservedAtForm

    def sort_finding_list_by_total(self, finding_list) -> List:
        is_desc = self.request.GET.get("sort_total_by", "desc") != "asc"
        _finding_list = finding_list.copy()
        _finding_list.sort(key=lambda x: x["meta"]["total"], reverse=is_desc)
        return _finding_list

    def sort_finding_list_by_critical(self, finding_list) -> List:
        is_desc = self.request.GET.get("sort_critical_by", "desc") != "asc"
        finding_list.sort(key=lambda x: x["meta"]["total_by_severity"]["critical"], reverse=is_desc)
        return finding_list

    def get_user_organizations(self) -> List:
        members = OrganizationMember.objects.filter(user=self.request.user)
        return [member.organization for member in members]

    def get_list_for_org(self, organization: Organization) -> Union[List, None]:
        try:
            api_connector = OctopoesAPIConnector(OCTOPOES_API, organization.code)

            return api_connector.list(self.ooi_types, valid_time=self.get_observed_at()).items
        except RemoteException:
            return []

    def get_observed_at(self) -> datetime:
        if "observed_at" not in self.request.GET:
            return datetime.now(timezone.utc)

        try:
            datetime_format = "%Y-%m-%d"
            return convert_date_to_datetime(datetime.strptime(self.request.GET.get("observed_at"), datetime_format))
        except ValueError:
            return datetime.now(timezone.utc)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_superuser:
            organizations = Organization.objects.all()
        else:
            organizations = self.get_user_organizations()
        findings_per_org = []
        for org in organizations:
            findings = self.get_list_for_org(org)
            findings_store = {finding.primary_key: finding for finding in findings}

            findings_ = build_findings_list_from_store(findings_store)
            findings_["organization"] = org
            findings_per_org.append(findings_)

        context["breadcrumb_list"] = [
            {"url": reverse("crisis_room"), "text": "CRISIS ROOM"},
        ]
        context["findings_per_org_total"] = self.sort_finding_list_by_total(findings_per_org)
        context["findings_per_org_critical"] = self.sort_finding_list_by_critical(findings_per_org)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = self.get_observed_at().date()

        return context
