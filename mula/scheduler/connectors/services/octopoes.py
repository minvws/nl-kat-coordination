from datetime import datetime, timezone

from pydantic import BaseModel

from scheduler.connectors.errors import exception_handler
from scheduler.models import OOI, Organisation

from .services import HTTPService


class ListObjectsResponse(BaseModel):
    count: int
    items: list[OOI]


class Octopoes(HTTPService):
    """A class that provides methods to interact with the Octopoes API."""

    name = "octopoes"
    health_endpoint = None

    def __init__(
        self,
        host: str,
        source: str,
        orgs: list[Organisation],
        pool_connections: int,
        timeout: int = 10,
    ):
        self.orgs: list[Organisation] = orgs
        super().__init__(host, source, timeout, pool_connections)

    @exception_handler
    def get_objects_by_object_types(
        self, organisation_id: str, object_types: list[str], scan_level: list[int]
    ) -> list[OOI]:
        """Get all oois from octopoes"""
        if scan_level is None:
            scan_level = []

        url = f"{self.host}/{organisation_id}/objects"

        params = {
            "types": object_types,
            "scan_level": [s for s in scan_level],
            "offset": 0,
            "limit": 1,
            "valid_time": datetime.now(timezone.utc),
        }

        # Get the total count of objects
        response = self.get(url, params=params)
        list_objects = ListObjectsResponse(**response.json())
        count = list_objects.count

        # Update the limit for the paginated results
        limit = 1000
        params["limit"] = limit

        # Loop over the paginated results
        oois = []
        for offset in range(0, count, limit):
            params["offset"] = offset
            response = self.get(url, params=params)
            list_objects = ListObjectsResponse(**response.json())
            oois.extend([ooi for ooi in list_objects.items])

        return oois

    @exception_handler
    def get_random_objects(self, organisation_id: str, n: int, scan_level: list[int]) -> list[OOI]:
        """Get `n` random oois from octopoes"""
        if scan_level is None:
            scan_level = []

        url = f"{self.host}/{organisation_id}/objects/random"

        params = {
            "amount": str(n),
            "scan_level": [s for s in scan_level],
            "valid_time": datetime.now(timezone.utc),
        }

        response = self.get(url, params=params)

        return [OOI(**ooi) for ooi in response.json()]

    @exception_handler
    def get_object(self, organisation_id: str, reference: str) -> OOI:
        """Get an ooi from octopoes"""
        url = f"{self.host}/{organisation_id}"
        response = self.get(
            url,
            params={"reference": reference, "valid_time": datetime.now(timezone.utc)},
        )
        return OOI(**response.json())

    def is_healthy(self) -> bool:
        healthy = True
        for org in self.orgs:
            if not self.is_host_healthy(self.host, f"{org.id}/health"):
                return False

        return healthy
