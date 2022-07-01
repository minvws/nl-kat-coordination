import logging

from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse, HttpRequest
from django_otp.decorators import otp_required
from octopoes.connector.octopoes import OctopoesAPIConnector
from requests import RequestException

from rocky.flower import FlowerClient, FlowerException, State
from rocky.health import ServiceHealth
from rocky.settings import FLOWER_API
from rocky.version import __version__
from rocky.katalogus import get_katalogus
from tools.user_helpers import is_red_team

logger = logging.getLogger(__name__)


@user_passes_test(is_red_team)
@otp_required
def health(request: HttpRequest) -> HttpResponse:

    services = [
        get_octopoes_health(request.octopoes_api_connector),
        get_katalogus_health(),
        get_flower_health(),
    ]

    rocky_health = ServiceHealth(
        service="rocky",
        healthy=all((service.healthy for service in services)),
        version=__version__,
        results=services,
        additional={},
    )

    return JsonResponse(rocky_health.dict())


def get_flower_health() -> ServiceHealth:
    try:
        flower = FlowerClient(FLOWER_API)
        received_tasks = flower.get_tasks("tasks.handle_boefje", state=State.RECEIVED)
        started_tasks = flower.get_tasks("tasks.handle_boefje", state=State.STARTED)
        flower_health = ServiceHealth(
            service="flower",
            healthy=True,
            additional={
                "received_tasks": len(received_tasks),
                "started_tasks": len(started_tasks),
            },
        )
    except FlowerException:
        flower_health = ServiceHealth(
            service="flower",
            healthy=False,
            additional="Could not connect to Flower. Service is possibly down",
        )
    return flower_health


def get_katalogus_health() -> ServiceHealth:
    try:
        katalogus_client = get_katalogus(
            ""
        )  # For the health endpoint the organization has no effect
        katalogus_health = katalogus_client.health()
    except RequestException as ex:
        logger.exception(ex)
        katalogus_health = ServiceHealth(
            service="katalogus",
            healthy=False,
            additional="Could not connect to Katalogus. Service is possibly down",
        )
    return katalogus_health


def get_octopoes_health(octopoes_api_connector: OctopoesAPIConnector) -> ServiceHealth:
    try:
        octopoes_health = octopoes_api_connector.health()
    except RequestException as ex:
        logger.exception(ex)
        octopoes_health = ServiceHealth(
            service="octopoes",
            healthy=False,
            additional="Could not connect to Octopoes. Service is possibly down",
        )
    return octopoes_health
