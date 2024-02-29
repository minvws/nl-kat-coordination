import json
from collections.abc import Set
from datetime import datetime
from uuid import UUID

import requests
from pydantic import TypeAdapter
from requests import HTTPError, Response

from octopoes.api.models import Affirmation, Declaration, Observation, ServiceHealth
from octopoes.config.settings import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    DEFAULT_SCAN_LEVEL_FILTER,
    DEFAULT_SCAN_PROFILE_TYPE_FILTER,
)
from octopoes.connector import DecodeException, RemoteException
from octopoes.models import OOI, Reference, ScanLevel, ScanProfile, ScanProfileType
from octopoes.models.exception import ObjectNotFoundException
from octopoes.models.explanation import InheritanceSection
from octopoes.models.ooi.findings import Finding, RiskLevelSeverity
from octopoes.models.origin import Origin, OriginParameter, OriginType
from octopoes.models.pagination import Paginated
from octopoes.models.transaction import TransactionRecord
from octopoes.models.tree import ReferenceTree
from octopoes.models.types import OOIType


class OctopoesAPISession(requests.Session):
    def __init__(self, base_url: str):
        super().__init__()

        self._base_uri = base_url

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
        method: str | bytes,
        url: str | bytes,
        *args,
        **kwargs,
    ) -> requests.Response:
        response = super().request(method, f"{self._base_uri}{str(url)}", *args, **kwargs)
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
        base_uri = base_uri.rstrip("/")
        self.base_uri = base_uri
        self.client = client

        self.session = OctopoesAPISession(base_uri)

    def root_health(self) -> ServiceHealth:
        return ServiceHealth.model_validate_json(self.session.get("/health").content)

    def health(self) -> ServiceHealth:
        return ServiceHealth.model_validate_json(self.session.get(f"/{self.client}/health").content)

    def list_objects(
        self,
        types: set[type[OOI]],
        valid_time: datetime,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
        scan_level: set[ScanLevel] = DEFAULT_SCAN_LEVEL_FILTER,
        scan_profile_type: set[ScanProfileType] = DEFAULT_SCAN_PROFILE_TYPE_FILTER,
    ) -> Paginated[OOIType]:
        params: dict[str, str | int | list[str] | set[str]] = {
            "types": [t.__name__ for t in types],
            "valid_time": str(valid_time),
            "offset": offset,
            "limit": limit,
            "scan_level": {s.value for s in scan_level},
            "scan_profile_type": {s.value for s in scan_profile_type},
        }
        res = self.session.get(f"/{self.client}/objects", params=params)
        return TypeAdapter(Paginated[OOIType]).validate_json(res.content)

    def get(self, reference: Reference, valid_time: datetime) -> OOI:
        res = self.session.get(
            f"/{self.client}/object",
            params={"reference": str(reference), "valid_time": str(valid_time)},
        )
        return TypeAdapter(OOIType).validate_json(res.content)

    def get_history(
        self,
        reference: Reference,
        *,
        sort_order: str = "asc",  # Or: "desc"
        with_docs: bool = False,
        has_doc: bool | None = None,
        offset: int = 0,
        limit: int | None = None,
        indices: list[int] | None = None,
    ) -> list[TransactionRecord]:
        params: dict[str, str | int | list[int] | None] = {
            "reference": str(reference),
            "sort_order": sort_order,
            "with_docs": with_docs,
            "has_doc": has_doc,
            "offset": offset,
            "limit": limit,
            "indices": indices,
        }
        res = self.session.get(f"/{self.client}/object-history", params=params)
        return TypeAdapter(list[TransactionRecord]).validate_json(res.content)

    def get_tree(
        self,
        reference: Reference,
        valid_time: datetime,
        types: Set = frozenset(),
        depth: int = 1,
    ) -> ReferenceTree:
        params: dict[str, str | int | list[str]] = {
            "reference": str(reference),
            "types": [t.__name__ for t in types],
            "depth": depth,
            "valid_time": str(valid_time),
        }
        res = self.session.get(f"/{self.client}/tree", params=params)
        return ReferenceTree.model_validate_json(res.content)

    def list_origins(
        self,
        valid_time: datetime,
        source: Reference | None = None,
        result: Reference | None = None,
        task_id: UUID | None = None,
        origin_type: OriginType | None = None,
    ) -> list[Origin]:
        res = self.session.get(
            f"/{self.client}/origins",
            params={
                "valid_time": str(valid_time),
                "source": source,
                "result": result,
                "task_id": str(task_id) if task_id else None,
                "origin_type": origin_type,
            },
        )

        return TypeAdapter(list[Origin]).validate_json(res.content)

    def save_observation(self, observation: Observation) -> None:
        self.session.post(
            f"/{self.client}/observations",
            headers={"Content-Type": "application/json"},
            data=observation.model_dump_json().encode(),
        )

    def save_declaration(self, declaration: Declaration) -> None:
        self.session.post(
            f"/{self.client}/declarations",
            headers={"Content-Type": "application/json"},
            data=declaration.model_dump_json().encode(),
        )

    def save_affirmation(self, affirmation: Affirmation) -> None:
        self.session.post(
            f"/{self.client}/affirmations",
            headers={"Content-Type": "application/json"},
            data=affirmation.model_dump_json().encode(),
        )

    def save_scan_profile(self, scan_profile: ScanProfile, valid_time: datetime):
        params = {"valid_time": str(valid_time)}
        self.session.put(
            f"/{self.client}/scan_profiles",
            params=params,
            headers={"Content-Type": "application/json"},
            data=scan_profile.model_dump_json().encode(),
        )

    def save_many_scan_profiles(self, scan_profiles: list[ScanProfile], valid_time: datetime) -> None:
        params = {"valid_time": str(valid_time)}
        self.session.post(
            f"/{self.client}/scan_profiles/save_many",
            params=params,
            json=[json.loads(scan_profile.model_dump_json()) for scan_profile in scan_profiles],
        )

    def delete(self, reference: Reference, valid_time: datetime) -> None:
        params = {"reference": str(reference), "valid_time": str(valid_time)}
        self.session.delete(f"/{self.client}/", params=params)

    def delete_many(self, references: list[Reference], valid_time: datetime) -> None:
        params = {"valid_time": str(valid_time)}
        self.session.post(f"/{self.client}/objects/delete_many", params=params, json=[str(ref) for ref in references])

    def list_origin_parameters(self, origin_id: set[str], valid_time: datetime) -> list[OriginParameter]:
        params = {"origin_id": origin_id, "valid_time": str(valid_time)}
        res = self.session.get(f"/{self.client}/origin_parameters", params=params)
        return TypeAdapter(list[OriginParameter]).validate_json(res.content)

    def create_node(self):
        self.session.post(f"/{self.client}/node")

    def delete_node(self):
        self.session.delete(f"/{self.client}/node")

    def get_scan_profile_inheritance(self, reference: Reference, valid_time: datetime) -> list[InheritanceSection]:
        params = {"reference": str(reference), "valid_time": str(valid_time)}
        res = self.session.get(f"/{self.client}/scan_profiles/inheritance", params=params)
        return TypeAdapter(list[InheritanceSection]).validate_json(res.content)

    def count_findings_by_severity(self, valid_time: datetime) -> dict[str, int]:
        params = {"valid_time": str(valid_time)}
        res = self.session.get(f"/{self.client}/findings/count_by_severity", params=params)
        return res.json()

    def list_findings(
        self,
        severities: set[RiskLevelSeverity],
        valid_time: datetime,
        exclude_muted: bool = True,
        only_muted: bool = False,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> Paginated[Finding]:
        params: dict[str, str | int | list[str] | set[str]] = {
            "valid_time": str(valid_time),
            "offset": offset,
            "limit": limit,
            "severities": {s.value for s in severities},
            "exclude_muted": exclude_muted,
            "only_muted": only_muted,
        }
        res = self.session.get(f"/{self.client}/findings", params=params)
        return TypeAdapter(Paginated[Finding]).validate_json(res.content)

    def load_objects_bulk(self, references: set[Reference], valid_time):
        params = {
            "valid_time": valid_time,
        }
        res = self.session.post(
            f"/{self.client}/objects/load_bulk", params=params, json=[str(ref) for ref in references]
        )
        return TypeAdapter(dict[Reference, OOIType]).validate_json(res.content)

    def recalculate_bits(self) -> int:
        return self.session.post(f"/{self.client}/bits/recalculate").json()

    def query(
        self,
        path: str,
        valid_time: datetime,
        source: OOI | Reference | str | None = None,
        offset: int = DEFAULT_OFFSET,
        limit: int = DEFAULT_LIMIT,
    ) -> list[OOI]:
        params = {
            "path": path,
            "source": source.reference if isinstance(source, OOI) else source,
            "valid_time": str(valid_time),
            "offset": offset,
            "limit": limit,
        }
        return [
            TypeAdapter(OOIType).validate_python(ooi)
            for ooi in self.session.get(f"/{self.client}/query", params=params).json()
        ]

    def query_many(
        self,
        path: str,
        valid_time: datetime,
        sources: list[OOI | Reference | str],
    ) -> list[tuple[str, OOIType]]:
        if not sources:
            return []

        params = {
            "path": path,
            "sources": [str(ooi) for ooi in sources],
            "valid_time": str(valid_time),
        }

        result = self.session.get(f"/{self.client}/query-many", params=params).json()

        return TypeAdapter(list[tuple[str, OOIType]]).validate_python(result)
