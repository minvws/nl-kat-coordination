import uuid
from datetime import date, datetime, timezone
from typing import List, TypedDict
from urllib.parse import urlparse, urlunparse, urlencode

from django.urls.base import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _

from account.mixins import OrganizationView
from octopoes.models.types import OOI_TYPES


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


def get_ooi_url(routename: str, ooi_id: str, organization_code: str, **kwargs) -> str:
    kwargs["ooi_id"] = ooi_id

    if "query" in kwargs:
        kwargs["query"] = {key: value for key, value in kwargs["query"] if key not in kwargs}
        kwargs.update(kwargs["query"])

        del kwargs["query"]

    return url_with_querystring(reverse(routename, kwargs={"organization_code": organization_code}), **kwargs)


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
    breadcrumbs = [{"url": reverse_lazy("organization_list"), "text": _("Organizations")}]


class OrganizationMemberBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
    def build_breadcrumbs(self):
        breadcrumbs = [
            {
                "url": reverse("organization_detail", kwargs={"organization_code": self.organization.code}),
                "text": self.organization.name,
            },
        ]
        permission = self.request.user.has_perm("tools.view_organization")
        if permission:
            organization_url = {"url": reverse("organization_list"), "text": _("Organizations")}
            breadcrumbs.insert(0, organization_url)

        return breadcrumbs


class ObjectsBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Objects"),
            }
        ]
