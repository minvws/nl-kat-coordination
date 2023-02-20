"""Katalogys HTTP Client."""

from typing import List

from octopoes.connectors.errors import exception_handler
from octopoes.models.organisation import Organisation
from .services import HTTPService


class Katalogus(HTTPService):
    """Katalogus HTTP Client."""

    name = "katalogus"

    @exception_handler
    def get_organisation(self, organisation_id: str) -> Organisation:
        """Get organisation by id from katalogus."""
        url = f"{self.host}/v1/organisations/{organisation_id}"
        response = self.get(url)
        return Organisation(**response.json())

    @exception_handler
    def get_organisations(self) -> List[Organisation]:
        """Get all organisations from katalogus."""
        url = f"{self.host}/v1/organisations"
        response = self.get(url)
        return [Organisation(**organisation) for organisation in response.json().values()]
