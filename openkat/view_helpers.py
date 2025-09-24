from typing import Any, TypedDict
from urllib.parse import urlencode, urlparse, urlunparse

from django.http import HttpRequest
from django.http.response import HttpResponseRedirectBase
from django.urls.base import reverse, reverse_lazy
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _

from openkat.models import Organization


def url_with_querystring(path: str, doseq: bool = False, /, **kwargs: Any) -> str:
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


def get_ooi_url(routename: str, ooi_id: str, organization_code: str, **kwargs: Any) -> str:
    if ooi_id:
        kwargs["ooi_id"] = ooi_id

    if "query" in kwargs:
        kwargs["query"] = {key: value for key, value in kwargs["query"] if key not in kwargs}
        kwargs.update(kwargs["query"])

        del kwargs["query"]

    return url_with_querystring(reverse(routename, kwargs={"organization_code": organization_code}), **kwargs)


class Breadcrumb(TypedDict):
    text: str | Promise
    url: str


class BreadcrumbsMixin:
    breadcrumbs: list[Breadcrumb] = []

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        return self.breadcrumbs.copy()

    def get_context_data(self, **kwargs):
        # Mypy doesn't understand the way mixins are used
        context = super().get_context_data(**kwargs)  # type: ignore[misc]
        context["breadcrumbs"] = self.build_breadcrumbs()
        return context


class Step(TypedDict):
    text: str
    url: str


class StepsMixin:
    request: HttpRequest
    steps: list[Step] = []
    current_step: int | None = None

    def get_current_step(self):
        if self.current_step is None:
            return int(self.request.GET.get("current_step"))
        return self.current_step

    def set_current_stepper_url(self, url):
        self.steps[self.get_current_step() - 1]["url"] = url

    def build_steps(self) -> list[Step]:
        return self.steps.copy()

    def get_context_data(self, **kwargs):
        # Mypy doesn't understand the way mixins are used
        context = super().get_context_data(**kwargs)  # type: ignore[misc]
        context["steps"] = self.build_steps()
        context["current_step"] = self.get_current_step()

        return context


class OrganizationBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [{"url": reverse_lazy("organization_list"), "text": _("Organizations")}]


class OrganizationDetailBreadcrumbsMixin(BreadcrumbsMixin):
    organization: Organization

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        return [
            {
                "url": reverse("organization_settings", kwargs={"organization_code": self.organization.code}),
                "text": _("Settings"),
            }
        ]


class OrganizationMemberBreadcrumbsMixin(BreadcrumbsMixin):
    organization: Organization

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        return [
            {
                "url": reverse("organization_member_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Members"),
            }
        ]


class ObjectsBreadcrumbsMixin(BreadcrumbsMixin):
    organization: Organization

    def build_breadcrumbs(self) -> list[Breadcrumb]:
        return [
            {
                "url": reverse_lazy("ooi_list", kwargs={"organization_code": self.organization.code}),
                "text": _("Objects"),
            }
        ]


class PostRedirect(HttpResponseRedirectBase):
    status_code = 307
