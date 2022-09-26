import json
from io import BytesIO
from typing import Dict, Type, Set, List

import requests
from django.urls import reverse_lazy
from octopoes.models import OOI
from octopoes.models.types import type_by_name
from pydantic import BaseModel

from rocky.health import ServiceHealth
from rocky.settings import KATALOGUS_API
from tools.models import SCAN_LEVEL, Organization
from tools.view_helpers import BreadcrumbsMixin


class KATalogusBreadcrumbsMixin(BreadcrumbsMixin):
    breadcrumbs = [{"text": "KAT-alogus", "url": reverse_lazy("katalogus")}]


class Boefje(BaseModel):
    id: str
    name: str
    description: str
    repository_id: str
    scan_level: SCAN_LEVEL
    consumes: Set[Type[OOI]]
    produces: Set[Type[OOI]]
    enabled: bool = True


class KATalogusClientInterface:
    def health(self) -> ServiceHealth:
        raise NotImplementedError()

    def get_boefjes(self) -> List[Boefje]:
        raise NotImplementedError()

    def get_boefje(self, boefje_id: str) -> Boefje:
        raise NotImplementedError()

    def enable_boefje(self, boefje_id: str) -> None:
        raise NotImplementedError()

    def disable_boefje(self, boefje_id: str) -> None:
        raise NotImplementedError()

    def get_enabled_boefjes(self) -> List[Boefje]:
        raise NotImplementedError()

    def get_description(self, boefje_id: str) -> str:
        raise NotImplementedError()

    def get_cover(self, boefje_id: str) -> BytesIO:
        raise NotImplementedError()


class KATalogusClientV1(KATalogusClientInterface):
    def __init__(self, base_uri: str, organization: str):
        self.base_uri = base_uri
        self.organization_uri = f"{base_uri}/v1/organisations/{organization}"

    def get_all_settings(self) -> Dict[str, str]:
        response = requests.get(f"{self.organization_uri}/settings")
        return response.json()

    def get_plugin_settings(self, plugin_id: str) -> Dict[str, str]:
        response = requests.get(f"{self.organization_uri}/{plugin_id}/settings")
        return response.json()

    def add_plugin_setting(self, plugin_id: str, name: str, value: str) -> None:
        body = {"value": value}
        response = requests.post(
            f"{self.organization_uri}/{plugin_id}/settings/{name}", json=body
        )
        response.raise_for_status()

    def get_plugin_setting(self, plugin_id: str, key: str) -> str:
        response = requests.get(f"{self.organization_uri}/{plugin_id}/settings/{key}")
        return response.json()

    def add_setting(self, name: str, value: str) -> None:
        body = {"value": value}
        response = requests.post(f"{self.organization_uri}/settings/{name}", json=body)
        response.raise_for_status()

    def update_plugin_setting(self, plugin_id: str, name: str, value: str) -> None:
        body = {"value": value}
        response = requests.put(
            f"{self.organization_uri}/{plugin_id}/settings/{name}", json=body
        )
        response.raise_for_status()

    def delete_plugin_setting(self, plugin_id: str, name: str) -> None:
        response = requests.delete(
            f"{self.organization_uri}/{plugin_id}/settings/{name}"
        )
        return response

    def health(self) -> ServiceHealth:
        response = requests.get(f"{self.base_uri}/health")
        response.raise_for_status()

        return ServiceHealth.parse_obj(response.json())

    def get_boefjes(self) -> List[Boefje]:
        response = requests.get(f"{self.organization_uri}/plugins")
        response.raise_for_status()

        return [
            _parse_boefje_v1(boefje)
            for boefje in response.json()
            if boefje["type"] == "boefje"
        ]

    def get_boefje(self, boefje_id: str) -> Boefje:
        response = requests.get(f"{self.organization_uri}/plugins/{boefje_id}")
        response.raise_for_status()

        return _parse_boefje_v1(response.json())

    def enable_boefje(self, boefje_id: str) -> None:
        self._patch_boefje_state(boefje_id, True)

    def disable_boefje(self, boefje_id: str) -> None:
        self._patch_boefje_state(boefje_id, False)

    def get_enabled_boefjes(self) -> List[Boefje]:
        return [boefje for boefje in self.get_boefjes() if boefje.enabled]

    def _patch_boefje_state(self, boefje_id: str, enabled: bool) -> None:
        boefje = self.get_boefje(boefje_id)

        body = {"enabled": enabled}
        response = requests.patch(
            f"{self.organization_uri}/repositories/{boefje.repository_id}/plugins/{boefje_id}",
            data=json.dumps(body),
        )
        response.raise_for_status()

    def get_description(self, boefje_id: str) -> str:
        response = requests.get(
            f"{self.organization_uri}/plugins/{boefje_id}/description.md"
        )
        response.raise_for_status()

        return response.content.decode("utf-8")

    def get_cover(self, boefje_id: str) -> BytesIO:
        response = requests.get(
            f"{self.organization_uri}/plugins/{boefje_id}/cover.png"
        )
        response.raise_for_status()
        return BytesIO(response.content)


def _parse_boefje_v1(boefje: Dict) -> Boefje:
    try:
        consumes = {type_by_name(consumes) for consumes in boefje["consumes"]}
    except StopIteration:
        consumes = set()

    produces = set()
    for ooi in boefje["produces"]:
        try:
            produces.add(type_by_name(ooi))
        except StopIteration:
            pass

    return Boefje(
        id=boefje["id"],
        name=boefje.get("name") or boefje["id"],
        repository_id=boefje["repository_id"],
        description=boefje["description"],
        scan_level=SCAN_LEVEL(boefje["scan_level"]),
        consumes=consumes,  # TODO: check if we still want to support multiple
        produces=produces,
        enabled=boefje["enabled"],
    )


def get_katalogus(organization: str) -> KATalogusClientInterface:
    return KATalogusClientV1(KATALOGUS_API, organization)


def get_enabled_boefjes_for_ooi_class(
    ooi_class: Type[OOI], organization: Organization
) -> List[Boefje]:
    return [
        boefje
        for boefje in get_katalogus(organization.code).get_enabled_boefjes()
        if ooi_class in boefje.consumes
    ]
