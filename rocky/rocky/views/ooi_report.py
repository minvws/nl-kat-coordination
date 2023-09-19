from datetime import datetime
from typing import List, Set, Type

from account.mixins import OrganizationView
from django.contrib import messages
from django.core.exceptions import BadRequest
from django.http import FileResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from katalogus.client import get_katalogus
from tools.forms.ooi import OOIReportSettingsForm
from tools.models import Organization
from tools.view_helpers import convert_date_to_datetime, get_ooi_url

from octopoes.models import OOI
from octopoes.models.ooi.dns.records import (
    DNSAAAARecord,
    DNSARecord,
    DNSMXRecord,
    DNSNSRecord,
    DNSSOARecord,
)
from octopoes.models.ooi.dns.zone import Hostname
from rocky.keiko import (
    FindingReportQuery,
    GeneratingReportFailed,
    OOIReportQuery,
    ReportNotFoundException,
    ReportsService,
    build_findings_list_from_store,
    keiko_client,
)
from rocky.views.finding_list import generate_findings_metadata
from rocky.views.mixins import FindingList, OctopoesView, SeveritiesMixin, SingleOOITreeMixin
from rocky.views.ooi_view import BaseOOIDetailView


class OOIReportView(BaseOOIDetailView):
    template_name = "oois/ooi_report.html"
    connector_form_class = OOIReportSettingsForm

    def dispatch(self, request, *args, **kwargs):
        if "ooi_id" not in request.GET:
            raise BadRequest("Missing ooi_id parameter")
        ooi_id = request.GET["ooi_id"]

        if self.get_observed_at() > convert_date_to_datetime(datetime.now(timezone.utc)):
            messages.error(
                request,
                _("You can't generate a report for an OOI on a date in the future."),
            )
            return redirect(get_ooi_url("ooi_detail", ooi_id, self.organization.code))
        return super().dispatch(request, *args, **kwargs)

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.depth = self.get_depth()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        findings_list = build_findings_list_from_store(self.tree.store)
        context["breadcrumbs"].append(
            {
                "url": get_ooi_url("ooi_report", self.ooi.primary_key, self.organization.code),
                "text": _("Findings report"),
            }
        )
        context["observed_at_form"] = self.get_connector_form()
        context["findings_list"] = findings_list
        return context


class OOIReportPDFView(SingleOOITreeMixin):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.octopoes_api_connector
        self.depth = self.get_depth()

    def get(self, request, *args, **kwargs):
        self.setup(request, *args, **kwargs)
        self.ooi = self.get_ooi()
        valid_time = self.get_observed_at()
        reports_service = ReportsService(keiko_client)

        try:
            report = reports_service.get_report(
                valid_time,
                self.ooi.object_type,
                self.ooi.human_readable,
                self.tree.store,
                OOIReportQuery(
                    self.organization.code,
                    valid_time.date(),
                    self.ooi,
                    self.depth,
                    origin=f"{request.scheme}://{request.get_host()}",
                ),
            )
        except GeneratingReportFailed:
            messages.error(self.request, _("Generating report failed. See Keiko logs for more information."))
            return redirect(get_ooi_url("ooi_report", self.ooi.primary_key, self.organization.code))
        except ReportNotFoundException:
            messages.error(self.request, _("Timeout reached generating report. See Keiko logs for more information."))
            return redirect(get_ooi_url("ooi_report", self.ooi.primary_key, self.organization.code))

        return FileResponse(
            report,
            as_attachment=True,
            filename=ReportsService.ooi_report_file_name(valid_time, self.organization.code, self.ooi.primary_key),
        )


class FindingReportPDFView(SeveritiesMixin, OctopoesView):
    """Used from the FindingListView. The request to this endpoint inherits all query parameters from this page, so that
    the report shows the same filtered findings.
    """

    paginate_by = None

    def get(self, request, *args, **kwargs):
        severities = self.get_severities()
        muted_findings = request.GET.get("muted_findings", "non-muted")

        exclude_muted = muted_findings == "non-muted"
        only_muted = muted_findings == "muted"

        findings = FindingList(
            self.octopoes_api_connector,
            self.get_observed_at(),
            severities,
            exclude_muted=exclude_muted,
            only_muted=only_muted,
        )

        reports_service = ReportsService(keiko_client)

        try:
            report = reports_service.get_organization_finding_report(
                self.get_observed_at(),
                self.organization.name,
                generate_findings_metadata(findings, severities),
                FindingReportQuery(
                    self.organization.code,
                    self.get_observed_at().date(),
                    severities,
                    origin=f"{request.scheme}://{request.get_host()}",
                    exclude_muted=exclude_muted,
                    only_muted=only_muted,
                ),
            )
        except GeneratingReportFailed:
            messages.error(request, _("Generating report failed. See Keiko logs for more information."))
            return redirect(reverse("finding_list", kwargs={"organization_code": self.organization.code}))
        except ReportNotFoundException:
            messages.error(request, _("Timeout reached generating report. See Keiko logs for more information."))
            return redirect(reverse("finding_list", kwargs={"organization_code": self.organization.code}))

        return FileResponse(
            report,
            as_attachment=True,
            filename=ReportsService.organization_report_file_name(self.organization.code),
        )


# Generates report from a starting point OOI with a filtered set of it's sub OOI's
# and a filtered set of findings belonging to those OOIs.

# boefjes_required - Set of possible boefjes
# boefjes_optional - Set of possible boefjes
# start_ooi - OOI that is the starting point of the report
# allowed_oois - Set of OOIs that are interesting for this specific report
# allowed_finding_types - Set of finding types that are interesting for this report


class Report(OrganizationView):
    boefjes_required: Set = None  # type: ignore
    boefjes_optional: Set = None  # type: ignore
    start_ooi: OOI = None  # type: ignore
    allowed_ooi_types: List[Type[OOI]] = None  # type: ignore
    allowed_finding_types: List[str] = None  # type: ignore
    boefjes: List = []

    @classmethod
    def get_finding_filter(cls):
        return cls.allowed_finding_types

    @classmethod
    def get_ooi_type_filter(cls):
        return [ooi.get_ooi_type() for ooi in cls.allowed_ooi_types]

    @classmethod
    def get_boefjes(cls, organization: Organization):
        cls.boefjes = []

        katalogus_boefjes = get_katalogus(organization.code).get_boefjes()
        for boefje in katalogus_boefjes:
            if boefje.id in cls.boefjes_required:
                cls.add_boefje(boefje, True)
            elif boefje.id in cls.boefjes_optional:
                cls.add_boefje(boefje, False)

        return cls.boefjes

    @classmethod
    def add_boefje(cls, boefje, required):
        cls.boefjes.append({"id": boefje.id, "required": required, "boefje": boefje})


class DNSReport(Report):
    boefjes_required = {"dns-records", "dns-zone"}
    boefjes_optional = {"dns-sec"}
    allowed_ooi_types = [
        DNSARecord,
        DNSAAAARecord,
        DNSMXRecord,
        DNSNSRecord,
        DNSSOARecord,
        Hostname,
    ]
    allowed_finding_types = [
        "KAT-WEBSERVER-NO-IPV6",
        "KAT-NAMESERVER-NO-IPV6",
        "KAT-NAMESERVER-NO-TWO-IPV6",
    ]
