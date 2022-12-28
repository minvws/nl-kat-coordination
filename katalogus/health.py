import logging
from requests import RequestException
from rocky.health import ServiceHealth
from katalogus.client import get_katalogus


logger = logging.getLogger(__name__)


def get_katalogus_health() -> ServiceHealth:
    try:
        katalogus_client = get_katalogus("")  # For the health endpoint the organization has no effect
        katalogus_health = katalogus_client.health()
    except RequestException as ex:
        logger.exception(ex)
        katalogus_health = ServiceHealth(
            service="katalogus",
            healthy=False,
            additional="Could not connect to KATalogus. Service is possibly down",
        )
    return katalogus_health
