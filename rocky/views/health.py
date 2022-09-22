import logging
from typing import List
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse, HttpRequest
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django_otp.decorators import otp_required
from two_factor.views.utils import class_view_decorator
from octopoes.connector.octopoes import OctopoesAPIConnector
from requests import RequestException
from rocky.health import ServiceHealth
from rocky.keiko import keiko_client
from rocky.version import __version__
from katalogus.health import get_katalogus_health
from tools.user_helpers import is_red_team
from rocky.scheduler import client
from django.views.generic import TemplateView
from rocky.bytes_client import get_bytes_client

logger = logging.getLogger(__name__)


@user_passes_test(is_red_team)
@otp_required
def health(request: HttpRequest) -> HttpResponse:
    rocky_health = get_rocky_health(request.octopoes_api_connector)
    return JsonResponse(rocky_health.dict())


def get_bytes_health() -> ServiceHealth:
    try:
        bytes_health = get_bytes_client().health()
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
        additional = _(
            "Rocky will not function properly. Not all services are healthy."
        )
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
class HealthChecks(TemplateView):
    template_name = "health.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = [
            {"url": reverse("health"), "text": _("Health")},
            {"url": reverse("health_beautified"), "text": _("Beautified")},
        ]
        rocky_health = get_rocky_health(self.request.octopoes_api_connector)
        context["health_checks"] = flatten_health(rocky_health)
        return context
