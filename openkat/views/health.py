from typing import Any

import structlog
from django.http import HttpRequest, JsonResponse
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View

from account.mixins import OrganizationView
from octopoes.connector.octopoes import OctopoesAPIConnector
from openkat.health import ServiceHealth
from openkat.version import __version__

logger = structlog.get_logger(__name__)


class Health(OrganizationView, View):
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> JsonResponse:
        octopoes_connector = self.octopoes_api_connector
        openkat_health = get_openkat_health(self.organization.code, octopoes_connector)
        return JsonResponse(openkat_health.model_dump())


def get_openkat_health(organization_code: str, octopoes_api_connector: OctopoesAPIConnector) -> ServiceHealth:
    services = [
        ServiceHealth(service="octopoes", healthy=True),
        ServiceHealth(service="katalogus", healthy=True),
        ServiceHealth(service="scheduler", healthy=True),
        ServiceHealth(service="bytes", healthy=True),
    ]

    services_healthy = all(service.healthy for service in services)
    additional = None
    if not services_healthy:
        additional = "OpenKAT will not function properly. Not all services are healthy."
    openkat_health = ServiceHealth(
        service="openkat", healthy=services_healthy, version=__version__, results=services, additional=additional
    )
    return openkat_health


def flatten_health(health_: ServiceHealth) -> list[ServiceHealth]:
    results = [health_]
    for sub_result in health_.results:
        results.extend(flatten_health(sub_result))
    health_.results = []
    return results


class HealthChecks(OrganizationView, TemplateView):
    template_name = "health.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("health", kwargs={"organization_code": self.organization.code}), "text": _("Health")},
            {
                "url": reverse("health_beautified", kwargs={"organization_code": self.organization.code}),
                "text": _("Beautified"),
            },
        ]

        openkat_health = get_openkat_health(self.organization.code, self.octopoes_api_connector)
        context["health_checks"] = flatten_health(openkat_health)

        return context
