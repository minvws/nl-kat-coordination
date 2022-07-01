import uuid
from django.http import QueryDict
from django.utils.translation import gettext_lazy as _
from django.urls.base import reverse_lazy, reverse
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional, List, TypedDict, Dict, Any
from urllib.parse import urlparse, urlunparse, urlencode

from django.contrib import messages
from django.http.request import HttpRequest
from octopoes.connector.octopoes import OctopoesAPIConnector
from octopoes.models.types import OOI_TYPES

from tools.models import Organization


class RockyHttpRequest(HttpRequest):
    active_organization: Optional[Organization]
    octopoes_api_connector: Optional[OctopoesAPIConnector]


def convert_date_to_datetime(d: date) -> datetime:
    # returning 23:59 of date_object in UTC timezone
    return datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc)


def get_mandatory_fields(request):
    mandatory_fields = []

    params = ["observed_at", "depth", "view"]

    for param in params:
        if param in request.GET:
            mandatory_fields.append((param, request.GET.get(param)))

    for type_ in request.GET.getlist("ooi_type", []):
        mandatory_fields.append(("ooi_type", type_))

    return mandatory_fields


def generate_job_id():
    return str(uuid.uuid4())


def url_with_querystring(path, **kwargs) -> str:
    parsed_route = urlparse(path)

    return str(
        urlunparse(
            (
                parsed_route.scheme,
                parsed_route.netloc,
                parsed_route.path,
                parsed_route.params,
                urlencode(kwargs),
                parsed_route.fragment,
            )
        )
    )


def get_ooi_url(routename: str, ooi_id: str, **kwargs) -> str:
    kwargs["ooi_id"] = ooi_id

    if "query" in kwargs:
        kwargs.update(kwargs["query"])
        del kwargs["query"]

    return url_with_querystring(reverse(routename), **kwargs)


def existing_ooi_type(ooi_type: str):
    if not ooi_type:
        return False

    return ooi_type in [x.__name__ for x in OOI_TYPES.values()]


class Breadcrumb(TypedDict):
    text: str
    url: str


class BreadcrumbsMixin:
    breadcrumbs: List[Breadcrumb] = []

    def build_breadcrumbs(self) -> List[Breadcrumb]:
        return self.breadcrumbs.copy()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.build_breadcrumbs()
        return context


class PageActionMixin:
    class PageActions(Enum):
        pass

    def is_allowed_page_action(self, page_action: str) -> bool:
        return page_action in [item.value for item in self.PageActions]

    def handle_page_action(self, page_action: str) -> None:
        if not self.is_allowed_page_action(page_action):
            messages.add_message(
                self.request, messages.WARNING, f"Action not allowed: {page_action}"
            )
            return self.get(self.request)

        # Does the page_action exist?
        if not hasattr(self, page_action):
            messages.add_message(
                self.request,
                messages.ERROR,
                f"Action not implemented: {page_action}",
            )
            return self.get(self.request)

        try:
            getattr(self, page_action)(self.get_page_action_args(page_action))
        except Exception as e:
            messages.add_message(
                self.request, messages.ERROR, f"{page_action} failed: '{e}'"
            )

    def get_page_action_args(self, page_action) -> QueryDict:
        return self.request.POST

    def get_page_actions(self) -> List[Dict[str, bool]]:
        return [
            {page_action.value: self.is_allowed_page_action(page_action)}
            for page_action in self.PageActions
        ]

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["page_actions"] = self.get_page_actions()
        return context


class Step(TypedDict):
    text: str
    url: str


class StepsMixin:
    steps: List[Step] = []
    current_step: int = None

    def get_current_step(self):
        if self.current_step is None:
            return int(self.request.GET.get("current_step"))
        return self.current_step

    def set_current_stepper_url(self, url):
        self.steps[self.get_current_step() - 1]["url"] = url

    def build_steps(self) -> List[Step]:
        return self.steps.copy()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["steps"] = self.build_steps()
        context["current_step"] = self.get_current_step()

        return context


class OrganizationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [
        {"url": reverse_lazy("organization_list"), "text": _("Organizations")}
    ]


class OrganizationMemberBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumb_object: Organization = None

    def set_breadcrumb_object(self, organization: Organization):
        self.breadcrumb_object = organization

    def build_breadcrumbs(self):
        if self.request.user.has_perm("tools.can_switch_organization"):
            breadcrumbs = [
                {"url": reverse("organization_list"), "text": _("Organizations")},
                {
                    "url": reverse(
                        "organization_detail", kwargs={"pk": self.breadcrumb_object.pk}
                    ),
                    "text": self.breadcrumb_object.name,
                },
            ]
        else:
            breadcrumbs = [
                {
                    "url": reverse("crisis_room"),
                    "text": self.breadcrumb_object.name,
                }
            ]

        breadcrumbs.append(
            {
                "url": reverse(
                    "organization_member_list", kwargs={"pk": self.breadcrumb_object.pk}
                ),
                "text": _("Members"),
            }
        )

        return breadcrumbs


class ObjectsBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [{"url": reverse_lazy("ooi_list"), "text": _("Objects")}]
