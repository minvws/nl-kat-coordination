import logging
from datetime import datetime, timezone
from typing import Set, Type, List, Dict, Optional, Tuple
from time import sleep
import requests.exceptions
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator, EmptyPage
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django_otp.decorators import otp_required
from octopoes.api.models import Declaration
from octopoes.connector import ObjectNotFoundException
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models import OOI, Reference, DeclaredScanProfile
from octopoes.models.ooi.findings import Finding
from octopoes.models.origin import Origin, OriginType
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import get_relations, get_collapsed_types, type_by_name
from pydantic import ValidationError, BaseModel
from two_factor.views.utils import class_view_decorator
from rocky.bytes_client import get_bytes_client
from katalogus.client import Boefje, get_katalogus
from tools.forms import BaseRockyForm, ObservedAtForm, DEPTH_MAX, DEPTH_DEFAULT
from tools.models import SCAN_LEVEL, Organization
from tools.ooi_form import OOIForm
from tools.ooi_helpers import (
    get_knowledge_base_data_for_ooi_store,
)
from tools.view_helpers import (
    get_ooi_url,
    get_mandatory_fields,
    convert_date_to_datetime,
    BreadcrumbsMixin,
    Breadcrumb,
)

logger = logging.getLogger(__name__)


class OOIAttributeError(AttributeError):
    pass


class OctopoesAPIImproperlyConfigured(ImproperlyConfigured):
    pass


class OOIBreadcrumbsMixin(BreadcrumbsMixin):
    def build_breadcrumbs(self) -> List[Breadcrumb]:
        if isinstance(self.ooi, Finding):
            start = {"url": reverse("finding_list"), "text": _("Findings")}
        else:
            start = {"url": reverse("ooi_list"), "text": _("Objects")}
        return [
            start,
            {
                "url": get_ooi_url("ooi_detail", self.ooi.primary_key),
                "text": self.ooi.human_readable,
            },
        ]


class OriginData(BaseModel):
    origin: Origin
    normalizer: Optional[dict]
    boefje: Optional[Boefje]


class OctopoesMixin:
    api_connector: OctopoesAPIConnector = None

    def get_api_connector(self) -> OctopoesAPIConnector:
        # needs obvious check, because of execution order
        if not self.request.user.is_verified():
            return None

        if not self.request.active_organization:
            raise OctopoesAPIImproperlyConfigured("Organization missing")

        if not self.request.active_organization.code:
            raise OctopoesAPIImproperlyConfigured("Organization missing code")

        if self.request.octopoes_api_connector is None:
            raise OctopoesAPIImproperlyConfigured("No Octopoes connector set.")

        return self.request.octopoes_api_connector

    def get_single_ooi(self, pk: str, observed_at: Optional[datetime] = None) -> OOI:
        try:
            ref = Reference.from_str(pk)
            return self.get_api_connector().get(ref, valid_time=observed_at)
        except Exception as e:
            # TODO: raise the exception but let the handling be done by  the method that implements "get_single_ooi"
            self.handle_connector_exception(e)

    def get_ooi_tree(
        self, pk: str, depth: int, observed_at: Optional[datetime] = None
    ) -> ReferenceTree:
        try:
            ref = Reference.from_str(pk)
            return self.get_api_connector().get_tree(
                ref, depth=depth, valid_time=observed_at
            )
        except Exception as e:
            self.handle_connector_exception(e)

    def get_origins(
        self,
        reference: Reference,
        valid_time: Optional[datetime],
        organization: Organization,
    ) -> Tuple[List[OriginData], List[OriginData], List[OriginData]]:
        try:
            origins = self.api_connector.list_origins(reference, valid_time)
            origin_data = [OriginData(origin=origin) for origin in origins]

            for origin in origin_data:

                if origin.origin.origin_type != OriginType.OBSERVATION:
                    continue

                try:
                    client = get_bytes_client()
                    client.login()

                    normalizer_data = client.get_normalizer_meta(origin.origin.task_id)
                    boefje_id = normalizer_data["boefje_meta"]["boefje"]["id"]
                    origin.normalizer = normalizer_data
                    origin.boefje = get_katalogus(organization.code).get_boefje(
                        boefje_id
                    )
                except requests.exceptions.RequestException as e:
                    logger.error(e)

            return (
                [
                    origin
                    for origin in origin_data
                    if origin.origin.origin_type == OriginType.DECLARATION
                ],
                [
                    origin
                    for origin in origin_data
                    if origin.origin.origin_type == OriginType.OBSERVATION
                ],
                [
                    origin
                    for origin in origin_data
                    if origin.origin.origin_type == OriginType.INFERENCE
                ],
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
            return convert_date_to_datetime(
                datetime.strptime(self.request.GET.get("observed_at"), datetime_format)
            )
        except ValueError:
            return datetime.now(timezone.utc)

    def get_depth(self, default_depth=DEPTH_DEFAULT) -> int:
        try:
            depth = int(self.request.GET.get("depth", default_depth))
            return min(depth, DEPTH_MAX)
        except ValueError:
            return default_depth

    def declare_scan_level(self, reference: Reference, level: int) -> None:
        self.api_connector.save_scan_profile(
            DeclaredScanProfile(
                reference=reference,
                level=level,
            ),
            datetime.now(timezone.utc),
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


class SingleOOIMixin(OctopoesMixin):
    ooi: OOI

    def get_ooi_id(self) -> str:
        if "ooi_id" not in self.request.GET:
            raise OOIAttributeError("OOI primary key missing")

        return self.request.GET["ooi_id"]

    def get_ooi(
        self, pk: Optional[str] = None, observed_at: Optional[datetime] = None
    ) -> OOI:
        if pk is None:
            pk = self.get_ooi_id()

        return self.get_single_ooi(pk, observed_at)

    def get_breadcrumb_list(self):
        start = {"url": reverse("ooi_list"), "text": "Objects"}
        if isinstance(self.ooi, Finding):
            start = {"url": reverse("finding_list"), "text": "Findings"}

        return [
            start,
            {
                "url": get_ooi_url("ooi_detail", self.ooi.primary_key),
                "text": self.ooi.human_readable,
            },
        ]

    def get_ooi_properties(self, ooi: OOI):
        class_relations = get_relations(ooi.__class__)
        props = {
            field_name: value
            for field_name, value in ooi
            if field_name not in class_relations
        }

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

    def get_object_from_tree(
        self, pk: str, observed_at: Optional[datetime] = None
    ) -> OOI:
        self.tree = self.get_ooi_tree(pk, self.depth, observed_at)

        return self.tree.store[str(self.tree.root.reference)]


class MultipleOOIMixin(OctopoesMixin):
    allow_empty = False
    ooi_types: Set[Type[OOI]] = None
    ooi_type_filters: List = []
    filtered_ooi_types: List[str] = []

    def get_list(self, observed_at: datetime):
        try:
            self.api_connector = self.get_api_connector()

            ooi_types = self.ooi_types
            if self.filtered_ooi_types:
                ooi_types = {type_by_name(t) for t in self.filtered_ooi_types}

            return self.api_connector.list(
                ooi_types, valid_time=observed_at, limit=5000
            )
        except Exception as e:
            self.handle_connector_exception(e)

    def get_filtered_ooi_types(self):
        return self.request.GET.getlist("ooi_type", [])

    def get_ooi_type_filters(self):
        ooi_type_filters = [
            {
                "label": ooi_class.get_ooi_type(),
                "value": ooi_class.get_ooi_type(),
                "checked": not self.filtered_ooi_types
                or ooi_class.get_ooi_type() in self.filtered_ooi_types,
            }
            for ooi_class in get_collapsed_types()
        ]

        ooi_type_filters = sorted(
            ooi_type_filters, key=lambda filter_: filter_["label"]
        )
        return ooi_type_filters

    def get_ooi_types_display(self):
        if not self.filtered_ooi_types or len(self.filtered_ooi_types) == len(
            get_collapsed_types()
        ):
            return _("All")

        return ", ".join(self.filtered_ooi_types)


@class_view_decorator(otp_required)
class BaseOOIListView(MultipleOOIMixin, ConnectorFormMixin, TemplateView):
    connector_form_class = ObservedAtForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        observed_at = self.get_observed_at()

        items_per_page = 150
        paginator = Paginator(self.get_list(observed_at), items_per_page)
        page_number = self.request.GET.get("page")

        try:
            page_obj = paginator.get_page(page_number)
        except EmptyPage:
            page_obj = paginator.get_page(1)

        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at_form"] = self.get_connector_form()
        context["observed_at"] = observed_at
        try:
            context["ooi_list"] = page_obj
        except OctopoesAPIImproperlyConfigured as e:
            context["ooi_list"] = []
            messages.add_message(self.request, messages.ERROR, str(e))

        return context


@class_view_decorator(otp_required)
class BaseOOIDetailView(SingleOOITreeMixin, ConnectorFormMixin, TemplateView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def get(self, request, *args, **kwargs):
        self.ooi = self.get_ooi()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["ooi"] = self.ooi
        context["mandatory_fields"] = get_mandatory_fields(self.request)
        context["observed_at"] = self.get_observed_at()

        return context


@class_view_decorator(otp_required)
class BaseOOIFormView(SingleOOIMixin, FormView):
    ooi_class: Type[OOI] = None
    form_class = OOIForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def get_ooi_class(self):
        return self.ooi.__class__ if hasattr(self, "ooi") else None

    def get_form(self, form_class=None) -> BaseRockyForm:
        if form_class is None:
            form_class = self.get_form_class()

        kwargs = self.get_form_kwargs()
        form = form_class(**kwargs)

        # Disable natural key attributes
        if self.get_readonly_fields():
            for readonly_field in self.get_readonly_fields():
                form.fields[readonly_field].disabled = True

        return form

    def get_form_kwargs(self):
        kwargs = {
            "ooi_class": self.get_ooi_class(),
            "connector": self.get_api_connector(),
        }
        kwargs.update(super().get_form_kwargs())

        return kwargs

    def save_ooi(self, data) -> OOI:
        api_connector = self.get_api_connector()
        new_ooi = self.ooi_class.parse_obj(data)
        api_connector.save_declaration(
            Declaration(ooi=new_ooi, valid_time=datetime.now(timezone.utc))
        )
        return new_ooi

    def form_valid(self, form):
        # Transform into OOI
        try:
            new_ooi = self.save_ooi(form.cleaned_data)
            sleep(1)
            return redirect(self.get_success_url(new_ooi))
        except ValidationError as exception:
            for error in exception.errors():
                form.add_error(error["loc"][0], error["msg"])
            return self.form_invalid(form)
        except Exception as exception:
            form.add_error("__all__", str(exception))
            return self.form_invalid(form)

    def get_success_url(self, ooi) -> str:
        return get_ooi_url("ooi_detail", ooi.primary_key)

    def get_readonly_fields(self) -> List:
        if not hasattr(self, "ooi"):
            return []

        return self.ooi._natural_key_attrs


@class_view_decorator(otp_required)
class BaseDeleteOOIView(SingleOOIMixin, TemplateView):
    success_url = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.api_connector = self.get_api_connector()

    def delete(self, request):
        self.api_connector.delete(self.ooi.reference)

        return HttpResponseRedirect(self.success_url)

    # Add support for browsers which only accept GET and POST for now.
    def post(self, request):
        return self.delete(request)
