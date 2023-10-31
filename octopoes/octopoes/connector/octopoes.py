import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Type, Union
from uuid import UUID

import requests
from pydantic.tools import parse_obj_as
from requests import HTTPError, Response

from octopoes.api.models import Declaration, Observation, ServiceHealth
from octopoes.config.settings import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
)
from octopoes.connector import DecodeException, RemoteException
from octopoes.models import (
    OOI,
    Reference,
    ScanLevel,
    ScanProfile,
    ScanProfileType,
)
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.explanation import InheritanceSection
from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.origin import Origin, OriginParameter, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import OOIType


class OctopoesAPISession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()

        self._base_uri = f"{base_url}"

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
        except json.decoder.JSONDecodeError as error:
            raise DecodeException("JSON decode error") from error

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


# todo: set default headers (accept-content, etc.)
class OctopoesAPIConnector:

    """
    Methods on this Connector can throw
        - requests.exceptions.RequestException if HTTP connection to Octopoes API fails
        - connector.ObjectNotFoundException if the OOI node cannot be found
        - connector.RemoteException if an error occurs inside Octopoes API
    """

    def __init__(self, base_uri: str, client: str):
        self.base_uri = base_uri
        self.client = client
        self.session = OctopoesAPISession(base_uri)

    def root_health(self) -> ServiceHealth:
        return ServiceHealth.parse_obj(self.session.get("/health").json())

    def health(self) -> ServiceHealth:
        return ServiceHealth.parse_obj(self.session.get(f"/{self.client}/health").json())

    def list(
        self,
        types: Set[Type[OOI]],
        valid_time: Optional[datetime] = None,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        scan_level: Set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_type: Set[ScanProfileType] = DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    ) -> Paginated[OOIType]:
        params = {
            "types": [t.__name__ for t in types],
            "valid_time": valid_time,
            "offset": offset,
            "limit": limit,
            "scan_level": {s.value for s in scan_level},
            "scan_profile_type": {s.value for s in scan_profile_type},
        }
        res = self.session.get(f"/{self.client}/objects", params=params)
        return Paginated[OOIType].parse_obj(res.json())

    def get(self, reference: Reference, valid_time: Optional[datetime] = None) -> OOI:
        res = self.session.get(
            f"/{self.client}/object",
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
            f"/{self.client}/tree",
            params={
                "reference": str(reference),
                "types": [t.__name__ for t in types],
                "depth": depth,
                "valid_time": valid_time,
            },
        )
        return ReferenceTree.parse_obj(res.json())

    def list_origins(
        self,
        valid_time: Optional[datetime] = None,
        source: Optional[Reference] = None,
        result: Optional[Reference] = None,
        task_id: Optional[UUID] = None,
        origin_type: Optional[OriginType] = None,
    ) -> List[Origin]:
        res = self.session.get(
            f"/{self.client}/origins",
            params={
                "valid_time": valid_time,
                "source": source,
                "result": result,
                "task_id": str(task_id) if task_id else None,
                "origin_type": origin_type,
            },
        )
        return parse_obj_as(List[Origin], res.json())

    def save_observation(self, observation: Observation) -> None:
        self.session.post(f"/{self.client}/observations", data=observation.json())

    def save_declaration(self, declaration: Declaration) -> None:
        self.session.post(f"/{self.client}/declarations", data=declaration.json())

    def save_scan_profile(self, scan_profile: ScanProfile, valid_time: datetime):
        params = {"valid_time": str(valid_time)}
        self.session.put(f"/{self.client}/scan_profiles", params=params, data=scan_profile.json())

    def save_many_scan_profiles(self, scan_profiles: List[ScanProfile], valid_time: Optional[datetime] = None) -> None:
        params = {"valid_time": valid_time}
        self.session.post(
            f"/{self.client}/scan_profiles/save_many",
            params=params,
            json=[json.loads(scan_profile.json()) for scan_profile in scan_profiles],
        )

    def delete(self, reference: Reference, valid_time: Optional[datetime] = None) -> None:
        params = {"reference": str(reference), "valid_time": valid_time}
        self.session.delete(f"/{self.client}/", params=params)

    def delete_many(self, references: List[Reference], valid_time: Optional[datetime] = None) -> None:
        params = {"valid_time": valid_time}
        self.session.post(f"/{self.client}/objects/delete_many", params=params, json=[str(ref) for ref in references])

    def list_origin_parameters(self, origin_id: Set[str], valid_time: Optional[datetime] = None) -> List[str]:
        params = {"origin_id": origin_id, "valid_time": valid_time}
        res = self.session.get(f"/{self.client}/origin_parameters", params=params)
        return parse_obj_as(List[OriginParameter], res.json())

    def create_node(self):
        self.session.post(f"/{self.client}/node")

    def delete_node(self):
        self.session.delete(f"/{self.client}/node")

    def get_scan_profile_inheritance(
        self, reference: Reference, valid_time: Optional[datetime] = None
    ) -> List[InheritanceSection]:
        params = {"reference": str(reference), "valid_time": valid_time}
        res = self.session.get(f"/{self.client}/scan_profiles/inheritance", params=params)
        return parse_obj_as(List[InheritanceSection], res.json())

    def count_findings_by_severity(self, valid_time: Optional[datetime] = None) -> Dict[str, int]:
        params = {"valid_time": valid_time}
        res = self.session.get(f"/{self.client}/findings/count_by_severity", params=params)
        return res.json()

    def list_findings(
        self,
        severities: Set[RiskLevelSeverity],
        exclude_muted: bool = True,
        only_muted: bool = False,
        valid_time: Optional[datetime] = None,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> Paginated[Finding]:
        params = {
            "valid_time": valid_time,
            "offset": offset,
            "limit": limit,
            "severities": {s.value for s in severities},
            "exclude_muted": exclude_muted,
            "only_muted": only_muted,
        }
        res = self.session.get(f"/{self.client}/findings", params=params)
        return Paginated[Finding].parse_obj(res.json())

    def load_objects_bulk(self, references: Set[Reference], valid_time):
        params = {
            "valid_time": valid_time,
        }
        res = self.session.post(
            f"/{self.client}/objects/load_bulk", params=params, json=[str(ref) for ref in references]
        )
        return parse_obj_as(Dict[Reference, OOIType], res.json())

    def recalculate_bits(self) -> int:
        return self.session.post(f"/{self.client}/bits/recalculate").json()

    def query(
        self,
        path: str,
        valid_time: datetime,
        source: Optional[Reference] = None,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> List[OOI]:
        params = {
            "path": path,
            "source": source,
            "valid_time": valid_time,
            "offset": offset,
            "limit": limit,
        }
        return [parse_obj_as(OOIType, ooi) for ooi in self.session.get(f"/{self.client}/query", params=params).json()]
