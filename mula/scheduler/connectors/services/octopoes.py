from typing import List

from scheduler.connectors.errors import exception_handler
from scheduler.models import OOI, Organisation

from .services import HTTPService


class Octopoes(HTTPService):
    name = "octopoes"
    health_endpoint = None

    def __init__(self, host: str, source: str, orgs: List[Organisation]):
        self.orgs: List[Organisation] = orgs
        super().__init__(host, source)

    @exception_handler
    def get_objects(self, organisation_id: str) -> List[OOI]:
        """Get all oois from octopoes"""
        url = f"{self.host}/{organisation_id}/objects"
        response = self.get(url)
        return [OOI(**ooi) for ooi in response.json()]

    # TODO: method needs to be added to octopoes_api
    @exception_handler
    def get_objects_by_object_types(self, organisation_id: str, object_types: List[str]) -> List[OOI]:
        """Get all oois from octopoes"""
        url = f"{self.host}/{organisation_id}/objects/"
        response = self.get(url)
        return [OOI(**ooi) for ooi in response.json()]

    @exception_handler
    def get_random_objects(self, organisation_id: str, n: int) -> List[OOI]:
        """Get `n` random oois from octopoes"""
        url = f"{self.host}/{organisation_id}/objects/random"
        response = self.get(url, params={"amount": str(n)})
        return [OOI(**ooi) for ooi in response.json()]

    @exception_handler
    def get_object(self, organisation_id: str, reference: str) -> OOI:
        """Get an ooi from octopoes"""
        url = f"{self.host}/{organisation_id}"
        response = self.get(url, params={"reference": reference})
        return OOI(**response.json())

    def is_healthy(self) -> bool:
        healthy = True
        for org in self.orgs:
            if not self.is_host_healthy(self.host, f"/{org.id}{self.health_endpoint}"):
                return False

        return healthy
