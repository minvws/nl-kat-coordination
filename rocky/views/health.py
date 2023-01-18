import logging
from typing import List

from django.http import JsonResponse
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import TemplateView, View
from django_otp.decorators import otp_required
from requests import RequestException
from two_factor.views.utils import class_view_decorator

from katalogus.health import get_katalogus_health
from octopoes.connector.octopoes import OctopoesAPIConnector
from rocky.bytes_client import get_bytes_client
from rocky.health import ServiceHealth
from rocky.keiko import keiko_client
from rocky.scheduler import client
from rocky.version import __version__
from rocky.views.mixins import OctopoesView

logger = logging.getLogger(__name__)


@class_view_decorator(otp_required)
class Health(OctopoesView, View):
    def get(self, request, *args, **kwargs) -> JsonResponse:
        octopoes_connector = self.octopoes_api_connector
        rocky_health = get_rocky_health(octopoes_connector)
        return JsonResponse(rocky_health.dict())


def get_bytes_health() -> ServiceHealth:
    try:
        bytes_health = get_bytes_client("").health()  # For the health endpoint the organization has no effect
    except RequestException as ex:
        logger.exception(ex)
        bytes_health = ServiceHealth(
            service="bytes",
            healthy=False,
            additional=_("Could not connect to Bytes. Service is possibly down"),
        )
    return bytes_health


def get_octopoes_health(octopoes_api_connector: OctopoesAPIConnector) -> ServiceHealth:
    try:
        octopoes_health = octopoes_api_connector.health()
    except RequestException as ex:
        logger.exception(ex)
        octopoes_health = ServiceHealth(
            service="octopoes",
            healthy=False,
            additional=_("Could not connect to Octopoes. Service is possibly down"),
        )
    return octopoes_health


def get_scheduler_health() -> ServiceHealth:
    try:
        scheduler_health = client.health()
    except RequestException as ex:
        logger.exception(ex)
        scheduler_health = ServiceHealth(
            service="scheduler",
            healthy=False,
            additional=_("Could not connect to Scheduler. Service is possibly down"),
        )
    return scheduler_health


def get_keiko_health() -> ServiceHealth:
    try:
        return keiko_client.health()
    except RequestException as ex:
        logger.exception(ex)
        return ServiceHealth(
            service="keiko",
            healthy=False,
            additional="Could not connect to Keiko. Service is possibly down",
        )


def get_rocky_health(octopoes_api_connector: OctopoesAPIConnector) -> ServiceHealth:
    services = [
        get_octopoes_health(octopoes_api_connector),
        get_katalogus_health(),
        get_scheduler_health(),
        get_bytes_health(),
        get_keiko_health(),
    ]

    services_healthy = all((service.healthy for service in services))
    additional = None
    if not services_healthy:
        additional = _("Rocky will not function properly. Not all services are healthy.")
    rocky_health = ServiceHealth(
        service="rocky",
        healthy=services_healthy,
        version=__version__,
        results=services,
        additional=additional,
    )
    return rocky_health


def flatten_health(health_: ServiceHealth) -> List[ServiceHealth]:
    results = [health_]
    for sub_result in health_.results:
        results.extend(flatten_health(sub_result))
    health_.results = []
    return results


@class_view_decorator(otp_required)
class HealthChecks(OctopoesView, TemplateView):
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
        rocky_health = get_rocky_health(self.octopoes_api_connector)
        context["health_checks"] = flatten_health(rocky_health)
        return context
