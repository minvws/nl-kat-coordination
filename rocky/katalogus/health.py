import logging

from httpx import RequestError

from katalogus.client import get_katalogus
from rocky.health import ServiceHealth

logger = logging.getLogger(__name__)


def get_katalogus_health() -> ServiceHealth:
    try:
        katalogus_client = get_katalogus("")  # For the health endpoint the organization has no effect
        katalogus_health = katalogus_client.health()
    except RequestError:
        logger.exception("Error while retrieving KATalogus health state")
        katalogus_health = ServiceHealth(
            service="katalogus",
            healthy=False,
            additional="Could not connect to KATalogus. Service is possibly down",
        )
    return katalogus_health
