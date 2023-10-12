import uuid
from datetime import date, datetime, timezone
from typing import List, TypedDict
from urllib.parse import urlencode, urlparse, urlunparse

from account.mixins import OrganizationView
from django.contrib import messages
from django.http import HttpRequest
from django.urls.base import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

from octopoes.models.types import OOI_TYPES
from rocky.scheduler import (
    BadRequestError,
    ConflictError,
    QueuePrioritizedItem,
    SchedulerError,
    TooManyRequestsError,
    client,
)


def convert_date_to_datetime(d: date) -> datetime:
    # returning 23:59 of date_object in UTC timezone
    return datetime.combine(d, datetime.max.time(), tzinfo=timezone.utc)


def get_mandatory_fields(request, params: List[str] = None):
    mandatory_fields = []

    if not params:
        params = ["observed_at", "depth", "view"]

        for type_ in request.GET.getlist("ooi_type", []):
            mandatory_fields.append(("ooi_type", type_))

    for param in params:
        if param in request.GET:
            mandatory_fields.append((param, request.GET.get(param)))

    return mandatory_fields


def generate_job_id():
    return str(uuid.uuid4())


def url_with_querystring(path, doseq=False, **kwargs) -> str:
    parsed_route = urlparse(path)

    return str(
        urlunparse(
            (
                parsed_route.scheme,
                parsed_route.netloc,
                parsed_route.path,
                parsed_route.params,
                urlencode(kwargs, doseq),
                parsed_route.fragment,
            )
        )
    )


def get_ooi_url(routename: str, ooi_id: str, organization_code: str, **kwargs) -> str:
    if ooi_id:
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


class OrganizationDetailBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
    def build_breadcrumbs(self):
        breadcrumbs = [
            {
                "url": reverse("organization_settings", kwargs={"organization_code": self.organization.code}),
                "text": _("Settings"),
            },
        ]

        return breadcrumbs


class OrganizationMemberBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
    def build_breadcrumbs(self):
        breadcrumbs = [
            {
                "url": reverse("organization_member_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Members"),
            },
        ]

        return breadcrumbs


class ObjectsBreadcrumbsMixin(BreadcrumbsMixin, OrganizationView):
    def build_breadcrumbs(self):
        return [
            {
                "url": reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Objects"),
            }
        ]


def schedule_task(request: HttpRequest, organization_code: str, task: QueuePrioritizedItem) -> None:
    try:
        client.push_task(f"{task.data.type}-{organization_code}", task)
    except (BadRequestError, TooManyRequestsError, ConflictError, SchedulerError) as error:
        messages.error(request, error.message)
    else:
        messages.success(
            request,
            _(
                "Your task is scheduled and will soon be started in the background. "
                "Results will be added to the object list when they are in. "
                "It may take some time, a refresh of the page may be needed to show the results."
            ),
        )
