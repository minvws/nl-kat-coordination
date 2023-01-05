import json
from datetime import datetime
from typing import Optional, List, Type, Set, Union

import requests
from pydantic.tools import parse_obj_as
from requests import Response, HTTPError

from octopoes.api.models import Observation, Declaration, ServiceHealth
from octopoes.connector import RemoteException
from octopoes.models import Reference, OOI, ScanProfile, ScanLevel, DEFAULT_SCAN_LEVEL_FILTER
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.origin import Origin
from octopoes.models.pagination import Paginated
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import OOIType


class OctopoesAPISession(requests.Session):
    def __init__(self, base_url: str, client: str):
        super().__init__()

        self._base_uri = f"{base_url}/{client}"

    @staticmethod
    def _verify_response(response: Response) -> None:
        try:
            response.raise_for_status()
        except HTTPError as error:
            if response.status_code == 404:
                data = response.json()
                raise ObjectNotFoundException(data["value"])
            if 500 <= response.status_code < 600:
                data = response.json()
                raise RemoteException(value=data["value"])
            raise error
        except json.decoder.JSONDecodeError:
            pass

    def request(
        self,
        method: str,
        url: Union[str, bytes],
        params: Optional[dict] = None,
        **kwargs,
    ) -> requests.Response:
        response = super().request(method, f"{self._base_uri}{url}", params, **kwargs)
        self._verify_response(response)
        return response


# todo: use request Session and set default headers (accept-content, etc.)
class OctopoesAPIConnector:

    """
    Methods on this Connector can throw
        - requests.exceptions.RequestException if HTTP connection to Octopoes API fails
        - connector.ObjectNotFoundException if the OOI node cannot be found
        - connector.RemoteException if an error occurs inside Octopoes API
    """

    def __init__(self, base_uri: str, client: str):
        self.session = OctopoesAPISession(base_uri, client)

    def health(self) -> ServiceHealth:
        return ServiceHealth.parse_obj(self.session.get("/health").json())

    def list(
        self,
        types: Set[Type[OOI]],
        valid_time: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 5000,
        scan_level: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
    ) -> Paginated[OOIType]:
        params = {
            "types": [t.__name__ for t in types],
            "valid_time": valid_time,
            "offset": offset,
            "limit": limit,
            "scan_level": {s.value for s in scan_level},
        }
        res = self.session.get("/objects", params=params)
        return Paginated[OOIType].parse_obj(res.json())

    def get(self, reference: Reference, valid_time: Optional[datetime] = None) -> OOI:
        res = self.session.get(
            "/object",
            params={"reference": str(reference), "valid_time": valid_time},
        )
        return parse_obj_as(OOIType, res.json())

    def get_tree(
        self,
        reference: Reference,
        types: Optional[Set] = None,
        depth: Optional[int] = 1,
        valid_time: Optional[datetime] = None,
    ) -> ReferenceTree:
        if types is None:
            types = set()
        res = self.session.get(
            "/tree",
            params={
                "reference": str(reference),
                "types": [t.__name__ for t in types],
                "depth": depth,
                "valid_time": valid_time,
            },
        )
        return ReferenceTree.parse_obj(res.json())

    def list_origins(self, reference: Reference, valid_time: Optional[datetime] = None) -> List[Origin]:
        params = {"reference": str(reference), "valid_time": valid_time}
        res = self.session.get("/origins", params=params)
        return parse_obj_as(List[Origin], res.json())

    def save_observation(self, observation: Observation) -> None:
        self.session.post("/observations", data=observation.json())

    def save_declaration(self, declaration: Declaration) -> None:
        self.session.post("/declarations", data=declaration.json())

    def save_scan_profile(self, scan_profile: ScanProfile, valid_time: datetime):
        params = {"valid_time": str(valid_time)}
        self.session.put("/scan_profiles", params=params, data=scan_profile.json())

    def delete(self, reference: Reference, valid_time: Optional[datetime] = None) -> None:
        params = {"reference": str(reference), "valid_time": valid_time}
        self.session.delete("/", params=params)
