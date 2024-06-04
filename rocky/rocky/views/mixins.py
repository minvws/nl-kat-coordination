import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from operator import attrgetter

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import Http404, HttpRequest
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from httpx import HTTPError
from katalogus.client import Boefje, get_katalogus
from pydantic import BaseModel
from tools.forms.base import ObservedAtForm
from tools.forms.settings import DEPTH_DEFAULT, DEPTH_MAX
from tools.models import Organization
from tools.ooi_helpers import get_knowledge_base_data_for_ooi_store
from tools.view_helpers import convert_date_to_datetime, get_ooi_url

from octopoes.connector import ObjectNotFoundException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference, ScanLevel, ScanProfileType
from octopoes.models.explanation import InheritanceSection
from octopoes.models.ooi.findings import Finding, FindingType, RiskLevelSeverity
from octopoes.models.ooi.reports import Report
from octopoes.models.origin import Origin, OriginType
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import get_relations
from rocky.bytes_client import get_bytes_client

logger = logging.getLogger(__name__)


@dataclass
class HydratedFinding:
    finding: Finding
    ooi: OOI
    finding_type: FindingType


class OriginData(BaseModel):
    origin: Origin
    normalizer: dict | None = None
    boefje: Boefje | None = None
    params: dict[str, str] | None = None


class OOIAttributeError(AttributeError):
    pass


class ObservedAtMixin:
    request: HttpRequest

    @cached_property
    def observed_at(self) -> datetime:
        observed_at = self.request.GET.get("observed_at", None)
        if not observed_at:
            return datetime.now(timezone.utc)

        try:
            datetime_format = "%Y-%m-%d"
            date_time = convert_date_to_datetime(datetime.strptime(observed_at, datetime_format))
            if date_time.date() > datetime.now(timezone.utc).date():
                messages.warning(
                    self.request,
                    _("The selected date is in the future."),
                )
            return date_time
        except ValueError:
            try:
                ret = datetime.fromisoformat(observed_at)
                if not ret.tzinfo:
                    ret = ret.replace(tzinfo=timezone.utc)

                return ret
            except ValueError:
                messages.error(self.request, _("Can not parse date, falling back to show current date."))
                return datetime.now(timezone.utc)


class OctopoesView(ObservedAtMixin, OrganizationView):
    def get_single_ooi(self, pk: str) -> OOI:
        try:
            ref = Reference.from_str(pk)
            ooi = self.octopoes_api_connector.get(ref, valid_time=self.observed_at)
        except Exception as e:
            # TODO: raise the exception but let the handling be done by  the method that implements "get_single_ooi"
            self.handle_connector_exception(e)

        return ooi

    def get_origins(
        self,
        reference: Reference,
        organization: Organization,
    ) -> tuple[list[OriginData], list[OriginData], list[OriginData]]:
        try:
            origins = self.octopoes_api_connector.list_origins(self.observed_at, result=reference)
            origin_data = [OriginData(origin=origin) for origin in origins]

            for origin in origin_data:
                if origin.origin.origin_type != OriginType.OBSERVATION or not origin.origin.task_id:
                    continue

                try:
                    client = get_bytes_client(organization.code)
                    client.login()

                    normalizer_data = client.get_normalizer_meta(origin.origin.task_id)
                    boefje_id = normalizer_data["raw_data"]["boefje_meta"]["boefje"]["id"]
                    origin.normalizer = normalizer_data
                    origin.boefje = get_katalogus(organization.code).get_plugin(boefje_id)
                except HTTPError as e:
                    logger.error(e)

            return (
                [origin for origin in origin_data if origin.origin.origin_type == OriginType.DECLARATION],
                [origin for origin in origin_data if origin.origin.origin_type == OriginType.OBSERVATION],
                [origin for origin in origin_data if origin.origin.origin_type == OriginType.INFERENCE],
            )
        except Exception as e:
            logger.error(e)
            return [], [], []

    def handle_connector_exception(self, exception: Exception):
        if isinstance(exception, ObjectNotFoundException):
            raise Http404("OOI not found")

        raise exception

    def get_scan_profile_inheritance(self, ooi: OOI) -> list[InheritanceSection]:
        return self.octopoes_api_connector.get_scan_profile_inheritance(ooi.reference, self.observed_at)


class OOIList:
    HARD_LIMIT = 99_999_999

    def __init__(
        self,
        octopoes_connector: OctopoesAPIConnector,
        ooi_types: set[type[OOI]],
        valid_time: datetime,
        scan_level: set[ScanLevel],
        scan_profile_type: set[ScanProfileType],
    ):
        self.octopoes_connector = octopoes_connector
        self.ooi_types = ooi_types
        self.valid_time = valid_time
        self.ordered = True
        self._count = 0
        self.scan_level = scan_level
        self.scan_profile_type = scan_profile_type

    @cached_property
    def count(self) -> int:
        return self.octopoes_connector.list_objects(
            self.ooi_types,
            valid_time=self.valid_time,
            limit=0,
            scan_level=self.scan_level,
            scan_profile_type=self.scan_profile_type,
        ).count

    def __len__(self):
        return self.count

    def __getitem__(self, key: int | slice) -> list[OOI]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = OOIList.HARD_LIMIT
            if key.stop:
                limit = key.stop - offset

            return self.octopoes_connector.list_objects(
                self.ooi_types,
                valid_time=self.valid_time,
                offset=offset,
                limit=limit,
                scan_level=self.scan_level,
                scan_profile_type=self.scan_profile_type,
            ).items

        elif isinstance(key, int):
            return self.octopoes_connector.list_objects(
                self.ooi_types,
                valid_time=self.valid_time,
                offset=key,
                limit=1,
                scan_level=self.scan_level,
                scan_profile_type=self.scan_profile_type,
            ).items


class FindingList:
    HARD_LIMIT = 99_999_999

    def __init__(
        self,
        octopoes_connector: OctopoesAPIConnector,
        valid_time: datetime,
        severities: set[RiskLevelSeverity],
        exclude_muted: bool = True,
        only_muted: bool = False,
    ):
        self.octopoes_connector = octopoes_connector
        self.valid_time = valid_time
        self.ordered = True
        self._count = None
        self.severities = severities
        self.exclude_muted = exclude_muted
        self.only_muted = only_muted

    @cached_property
    def count(self) -> int:
        return self.octopoes_connector.list_findings(
            severities=self.severities,
            valid_time=self.valid_time,
            exclude_muted=self.exclude_muted,
            only_muted=self.only_muted,
            limit=0,
        ).count

    def __len__(self):
        return self.count

    def __getitem__(self, key: int | slice) -> list[HydratedFinding]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = self.HARD_LIMIT
            if key.stop:
                limit = key.stop - offset
            findings = self.octopoes_connector.list_findings(
                severities=self.severities,
                valid_time=self.valid_time,
                exclude_muted=self.exclude_muted,
                only_muted=self.only_muted,
                offset=offset,
                limit=limit,
            ).items
            ooi_references = {finding.ooi for finding in findings}
            finding_type_references = {finding.finding_type for finding in findings}
            objects = self.octopoes_connector.load_objects_bulk(
                ooi_references | finding_type_references, valid_time=self.valid_time
            )

            hydrated_findings = []
            for finding in findings:
                if finding.ooi not in objects or finding.finding_type not in objects:
                    continue
                hydrated_findings.append(
                    HydratedFinding(
                        finding=finding, finding_type=objects[finding.finding_type], ooi=objects[finding.ooi]
                    )
                )
            return hydrated_findings

        raise NotImplementedError("FindingList only supports slicing")


class HydratedReport:
    parent_report: Report
    children_reports: list[Report] | None
    total_children_reports: int
    total_objects: int
    report_type_summary: dict[str, int]


class ReportList:
    HARD_LIMIT = 99_999_999

    def __init__(
        self, octopoes_connector: OctopoesAPIConnector, valid_time: datetime, parent_report_id: str | None = None
    ):
        self.octopoes_connector = octopoes_connector
        self.valid_time = valid_time
        self.ordered = True
        self._count = None
        self.parent_report_id = parent_report_id

        self.subreports = None
        if self.parent_report_id and self.parent_report_id is not None:
            self.subreports = self.get_subreports(self.parent_report_id)

    @cached_property
    def count(self) -> int:
        if self.subreports is not None:
            return len(self.subreports)
        return self.octopoes_connector.list_reports(
            valid_time=self.valid_time,
            limit=0,
        ).count

    def __len__(self):
        return self.count

    def __getitem__(self, key: int | slice) -> list[HydratedReport | Report]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = self.HARD_LIMIT
            if key.stop:
                limit = key.stop - offset
            reports = self.octopoes_connector.list_reports(
                valid_time=self.valid_time,
                offset=offset,
                limit=limit,
            ).items
            if self.subreports is not None:
                return self.subreports[offset : offset + limit]

            return self.hydrate_report_list(reports)

        raise NotImplementedError("ReportList only supports slicing")

    def get_subreports(self, report_id: str) -> list[Report]:
        """
        Get child reports with parent id.
        """
        # TODO: is better to use query over query_many as we use one parent id.
        # query will only return 50 items as we do not have pagination (offset and limit)
        # yet implemented for query requests. We use query_many to get more then 50 items at once.

        subreports = self.octopoes_connector.query_many(
            "Report.<parent_report [is Report]",
            self.valid_time,
            [report_id],
        )

        return subreports

    def hydrate_report_list(self, reports: list[Report]) -> list[HydratedReport]:
        hydrated_reports: list[HydratedReport] = []

        for report in reports:
            hydrated_report: HydratedReport = HydratedReport()

            parent_report, children_reports = report

            hydrated_report.total_children_reports = len(children_reports)
            hydrated_report.total_objects = self.get_total_objects(children_reports)
            hydrated_report.report_type_summary = self.report_type_summary(children_reports)

            if not parent_report.has_parent:
                hydrated_children_reports: list[Report] = []
                for child_report in children_reports:
                    if str(child_report.parent_report) == str(parent_report):
                        hydrated_children_reports.append(child_report)
                    if len(hydrated_children_reports) >= 5:  # We want to show only 5 children reports
                        break

                hydrated_report.children_reports = sorted(hydrated_children_reports, key=attrgetter("name"))

            hydrated_report.parent_report = parent_report
            hydrated_reports.append(hydrated_report)

        return hydrated_reports

    @staticmethod
    def get_total_objects(reports: list[Report]) -> int:
        return len({report.input_ooi for report in reports})

    @staticmethod
    def report_type_summary(reports: list[Report]) -> dict[str, int]:
        """
        Calculates per report type how many objects it consumed.
        """
        report_types = set()
        summary = {}

        for report in reports:
            report_types.add(report.report_type)

        for report_type in report_types:
            objects = []
            for report in reports:
                if report_type == report.report_type:
                    objects.append(report.input_ooi)

            summary[report_type] = len(objects)

        return summary


class ConnectorFormMixin:
    connector_form_class: type[ObservedAtForm]
    request: HttpRequest

    def get_connector_form_kwargs(self) -> dict:
        if "observed_at" in self.request.GET:
            return {"data": self.request.GET}
        else:
            return {}

    def get_connector_form(self) -> ObservedAtForm:
        return self.connector_form_class(**self.get_connector_form_kwargs())


class SingleOOIMixin(OctopoesView):
    ooi: OOI

    def get_ooi_id(self) -> str:
        if "ooi_id" not in self.request.GET:
            raise OOIAttributeError("OOI primary key missing")

        return self.request.GET["ooi_id"]

    def get_ooi(self, pk: str | None = None) -> OOI:
        if pk is None:
            pk = self.get_ooi_id()

        return self.get_single_ooi(pk)

    def get_breadcrumb_list(self):
        start = {
            "url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}),
            "text": "Objects",
        }
        if isinstance(self.ooi, Finding):
            start = {
                "url": reverse("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": "Findings",
            }

        return [
            start,
            {
                "url": get_ooi_url("ooi_detail", self.ooi.primary_key, self.organization.code),
                "text": self.ooi.human_readable,
            },
        ]

    def get_ooi_properties(self, ooi: OOI):
        class_relations = get_relations(ooi.__class__)
        props = {field_name: value for field_name, value in ooi if field_name not in class_relations}

        knowledge_base = get_knowledge_base_data_for_ooi_store({ooi.primary_key: ooi})

        if knowledge_base[ooi.get_information_id()]:
            props.update(knowledge_base[ooi.get_information_id()])

        props.pop("scan_profile")
        props.pop("primary_key")

        return props


class SingleOOITreeMixin(SingleOOIMixin):
    tree: ReferenceTree

    def get_depth(self):
        try:
            return min(int(self.request.GET.get("depth", DEPTH_DEFAULT)), DEPTH_MAX)
        except ValueError:
            return DEPTH_DEFAULT

    def get_ooi(self, pk: str | None = None, observed_at: datetime | None = None) -> OOI:
        if pk is None:
            pk = self.get_ooi_id()

        if observed_at is None:
            observed_at = self.observed_at

        ref = Reference.from_str(pk)
        depth = self.get_depth()

        try:
            self.tree = self.octopoes_api_connector.get_tree(ref, valid_time=observed_at, depth=depth)
        except Exception as e:
            self.handle_connector_exception(e)

        return self.tree.store[str(self.tree.root.reference)]


class SeveritiesMixin:
    request: HttpRequest

    def get_severities(self) -> set[RiskLevelSeverity]:
        severities = set()
        for severity in self.request.GET.getlist("severity"):
            try:
                severities.add(RiskLevelSeverity(severity))
            except ValueError as e:
                messages.error(self.request, _(str(e)))

        return severities
