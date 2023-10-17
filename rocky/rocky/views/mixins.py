import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from typing import Dict, List, Optional, Set, Tuple, Type, Union

import requests.exceptions
from account.mixins import OrganizationView
from django.contrib import messages
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from katalogus.client import Boefje, get_katalogus
from pydantic import BaseModel
from tools.forms.base import ObservedAtForm
from tools.forms.settings import DEPTH_DEFAULT, DEPTH_MAX
from tools.models import Organization
from tools.ooi_helpers import (
    get_knowledge_base_data_for_ooi_store,
)
from tools.view_helpers import (
    convert_date_to_datetime,
    get_ooi_url,
)

from octopoes.connector import ObjectNotFoundException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference, ScanLevel, ScanProfileType
from octopoes.models.explanation import InheritanceSection
from octopoes.models.ooi.findings import Finding, FindingType, RiskLevelSeverity
from octopoes.models.origin import Origin, OriginType
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import get_relations, type_by_name
from rocky.bytes_client import get_bytes_client

logger = logging.getLogger(__name__)


@dataclass
class HydratedFinding:
    finding: Finding
    ooi: OOI
    finding_type: FindingType


class OriginData(BaseModel):
    origin: Origin
    normalizer: Optional[dict]
    boefje: Optional[Boefje]
    params: Optional[Dict[str, str]]


class OOIAttributeError(AttributeError):
    pass


class OctopoesView(OrganizationView):
    def get_single_ooi(self, pk: str, observed_at: Optional[datetime] = None) -> OOI:
        try:
            ref = Reference.from_str(pk)
            return self.octopoes_api_connector.get(ref, valid_time=observed_at)
        except Exception as e:
            # TODO: raise the exception but let the handling be done by  the method that implements "get_single_ooi"
            self.handle_connector_exception(e)

    def get_ooi_tree(self, pk: str, depth: int, observed_at: Optional[datetime] = None) -> ReferenceTree:
        try:
            ref = Reference.from_str(pk)
            return self.octopoes_api_connector.get_tree(ref, depth=depth, valid_time=observed_at)
        except Exception as e:
            self.handle_connector_exception(e)

    def get_origins(
        self,
        reference: Reference,
        valid_time: Optional[datetime],
        organization: Organization,
    ) -> Tuple[List[OriginData], List[OriginData], List[OriginData]]:
        try:
            origins = self.octopoes_api_connector.list_origins(valid_time, result=reference)
            origin_data = [OriginData(origin=origin) for origin in origins]

            for origin in origin_data:
                if origin.origin.origin_type != OriginType.OBSERVATION:
                    continue

                try:
                    client = get_bytes_client(organization.code)
                    client.login()

                    normalizer_data = client.get_normalizer_meta(origin.origin.task_id)
                    boefje_id = normalizer_data["raw_data"]["boefje_meta"]["boefje"]["id"]
                    origin.normalizer = normalizer_data
                    origin.boefje = get_katalogus(organization.code).get_plugin(boefje_id)
                except requests.exceptions.RequestException as e:
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

    def get_observed_at(self) -> datetime:
        observed_at = self.request.GET.get("observed_at", None)
        if not observed_at:
            return datetime.now(timezone.utc)

        try:
            datetime_format = "%Y-%m-%dT%H:%M:%S"
            return convert_date_to_datetime(datetime.strptime(observed_at, datetime_format))
        except ValueError:
            try:
                datetime_format = "%Y-%m-%d"
                return convert_date_to_datetime(datetime.strptime(observed_at, datetime_format))
            except ValueError:
                messages.error(self.request, _("Can not parse date, falling back to show current date."))
                return datetime.now(timezone.utc)

    def get_depth(self, default_depth=DEPTH_DEFAULT) -> int:
        try:
            depth = int(self.request.GET.get("depth", default_depth))
            return min(depth, DEPTH_MAX)
        except ValueError:
            return default_depth

    def get_scan_profile_inheritance(self, ooi: OOI) -> List[InheritanceSection]:
        return self.octopoes_api_connector.get_scan_profile_inheritance(ooi.reference)


class OOIList:
    HARD_LIMIT = 99_999_999

    def __init__(
        self,
        octopoes_connector: OctopoesAPIConnector,
        ooi_types: Set[Type[OOI]],
        valid_time: datetime,
        scan_level: Set[ScanLevel],
        scan_profile_type: Set[ScanProfileType],
    ):
        self.octopoes_connector = octopoes_connector
        self.ooi_types = ooi_types
        self.valid_time = valid_time
        self.ordered = True
        self._count = None
        self.scan_level = scan_level
        self.scan_profile_type = scan_profile_type

    @cached_property
    def count(self) -> int:
        return self.octopoes_connector.list(
            self.ooi_types,
            valid_time=self.valid_time,
            limit=0,
            scan_level=self.scan_level,
            scan_profile_type=self.scan_profile_type,
        ).count

    def __len__(self):
        return self.count

    def __getitem__(self, key) -> List[OOI]:
        if isinstance(key, slice):
            return self.octopoes_connector.list(
                self.ooi_types,
                valid_time=self.valid_time,
                offset=key.start or 0,
                limit=key.stop - (key.start or 0),
                scan_level=self.scan_level,
                scan_profile_type=self.scan_profile_type,
            ).items
        elif isinstance(key, int):
            return self.octopoes_connector.list(
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
        severities: Set[RiskLevelSeverity],
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
            exclude_muted=self.exclude_muted,
            only_muted=self.only_muted,
            valid_time=self.valid_time,
            limit=0,
        ).count

    def __len__(self):
        return self.count

    def __getitem__(self, key: Union[int, slice]) -> List[HydratedFinding]:
        if isinstance(key, slice):
            offset = key.start or 0
            limit = key.stop - offset
            findings = self.octopoes_connector.list_findings(
                severities=self.severities,
                exclude_muted=self.exclude_muted,
                only_muted=self.only_muted,
                valid_time=self.valid_time,
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


class MultipleOOIMixin(OctopoesView):
    ooi_types: Set[Type[OOI]] = None
    ooi_type_filters: List = []
    filtered_ooi_types: List[str] = []

    def get_list(
        self,
        observed_at: datetime,
        scan_level: Set[ScanLevel],
        scan_profile_type: Set[ScanProfileType],
    ) -> OOIList:
        ooi_types = self.ooi_types
        if self.filtered_ooi_types:
            ooi_types = {type_by_name(t) for t in self.filtered_ooi_types}
        return OOIList(
            self.octopoes_api_connector,
            ooi_types,
            observed_at,
            scan_level=scan_level,
            scan_profile_type=scan_profile_type,
        )


class ConnectorFormMixin:
    connector_form_class: Type[ObservedAtForm] = None
    connector_form_initial = {}

    def get_connector_form_kwargs(self) -> Dict:
        kwargs = {
            "initial": self.connector_form_initial.copy(),
        }

        if "observed_at" in self.request.GET:
            kwargs.update({"data": self.request.GET})
        return kwargs

    def get_connector_form(self) -> ObservedAtForm:
        return self.connector_form_class(**self.get_connector_form_kwargs())


class SingleOOIMixin(OctopoesView):
    ooi: OOI
    tree: ReferenceTree

    def get_ooi_id(self) -> str:
        if "ooi_id" not in self.request.GET:
            raise OOIAttributeError("OOI primary key missing")

        return self.request.GET["ooi_id"]

    def get_ooi(self, pk: Optional[str] = None, observed_at: Optional[datetime] = None) -> OOI:
        if pk is None:
            pk = self.get_ooi_id()

        return self.get_single_ooi(pk, observed_at)

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
    depth: int = 2
    tree: ReferenceTree

    def get_ooi(self, pk: str = None, observed_at: Optional[datetime] = None) -> OOI:
        if pk is None:
            pk = self.get_ooi_id()

        if observed_at is None:
            observed_at = self.get_observed_at()

        if self.depth == 1:
            return self.get_single_ooi(pk, observed_at)

        return self.get_object_from_tree(pk, observed_at)

    def get_object_from_tree(self, pk: str, observed_at: Optional[datetime] = None) -> OOI:
        self.tree = self.get_ooi_tree(pk, self.depth, observed_at)

        return self.tree.store[str(self.tree.root.reference)]


class SeveritiesMixin:
    def get_severities(self) -> Set[RiskLevelSeverity]:
        severities = set()
        for severity in self.request.GET.getlist("severity"):
            try:
                severities.add(RiskLevelSeverity(severity))
            except ValueError as e:
                messages.error(self.request, _(str(e)))

        return severities
