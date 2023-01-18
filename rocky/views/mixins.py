import logging
from datetime import datetime, timezone
from functools import cached_property
from typing import Set, Type, List, Dict, Optional, Tuple

import requests.exceptions
from django.http import Http404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel

from account.mixins import OrganizationView
from katalogus.client import Plugin, get_katalogus
from octopoes.connector import ObjectNotFoundException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference, ScanLevel, ScanProfileType
from octopoes.models.ooi.findings import Finding
from octopoes.models.origin import Origin, OriginType
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import get_relations, get_collapsed_types, type_by_name
from rocky.bytes_client import get_bytes_client
from tools.forms.settings import DEPTH_MAX, DEPTH_DEFAULT
from tools.forms.base import ObservedAtForm
from tools.models import Organization
from tools.ooi_helpers import (
    get_knowledge_base_data_for_ooi_store,
)
from tools.view_helpers import (
    get_ooi_url,
    convert_date_to_datetime,
    BreadcrumbsMixin,
    Breadcrumb,
)

logger = logging.getLogger(__name__)


class OriginData(BaseModel):
    origin: Origin
    normalizer: Optional[dict]
    boefje: Optional[Plugin]


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
            origins = self.octopoes_api_connector.list_origins(reference, valid_time)
            origin_data = [OriginData(origin=origin) for origin in origins]

            for origin in origin_data:

                if origin.origin.origin_type != OriginType.OBSERVATION:
                    continue

                try:
                    client = get_bytes_client(organization.code)
                    client.login()

                    normalizer_data = client.get_normalizer_meta(origin.origin.task_id)
                    boefje_id = normalizer_data["boefje_meta"]["boefje"]["id"]
                    origin.normalizer = normalizer_data
                    origin.boefje = get_katalogus(organization.code).get_boefje(boefje_id)
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
        if "observed_at" not in self.request.GET:
            return datetime.now(timezone.utc)

        try:
            datetime_format = "%Y-%m-%d"
            return convert_date_to_datetime(datetime.strptime(self.request.GET.get("observed_at"), datetime_format))
        except ValueError:
            return datetime.now(timezone.utc)

    def get_depth(self, default_depth=DEPTH_DEFAULT) -> int:
        try:
            depth = int(self.request.GET.get("depth", default_depth))
            return min(depth, DEPTH_MAX)
        except ValueError:
            return default_depth


class OOIList:
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

    def get_filtered_ooi_types(self):
        return self.request.GET.getlist("ooi_type", [])

    def get_ooi_type_filters(self):
        ooi_type_filters = [
            {
                "label": ooi_class.get_ooi_type(),
                "value": ooi_class.get_ooi_type(),
                "checked": not self.filtered_ooi_types or ooi_class.get_ooi_type() in self.filtered_ooi_types,
            }
            for ooi_class in get_collapsed_types()
        ]

        ooi_type_filters = sorted(ooi_type_filters, key=lambda filter_: filter_["label"])
        return ooi_type_filters

    def get_ooi_types_display(self):
        if not self.filtered_ooi_types or len(self.filtered_ooi_types) == len(get_collapsed_types()):
            return _("All")

        return ", ".join(self.filtered_ooi_types)


class OOIBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
    def build_breadcrumbs(self) -> List[Breadcrumb]:
        if isinstance(self.ooi, Finding):
            start = {
                "url": reverse("finding_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Findings"),
            }
        else:
            start = {
                "url": reverse("ooi_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Objects"),
            }
        return [
            start,
            {
                "url": get_ooi_url("ooi_detail", self.ooi.primary_key, self.organization.code),
                "text": self.ooi.human_readable,
            },
        ]


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
            start = {"url": reverse("finding_list"), "text": "Findings"}

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

        knowledge_base = get_knowledge_base_data_for_ooi_store(self.tree.store)

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
