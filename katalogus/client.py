import json
from io import BytesIO
from typing import Dict, Type, Set, List

import requests
from pydantic import BaseModel

from octopoes.models import OOI
from octopoes.models.types import type_by_name
from rocky.health import ServiceHealth
from rocky.settings import KATALOGUS_API
from tools.enums import SCAN_LEVEL


class Plugin(BaseModel):
    id: str
    type: str
    name: str
    description: str
    repository_id: str
    scan_level: SCAN_LEVEL
    consumes: Set[Type[OOI]]
    produces: Set[Type[OOI]]
    enabled: bool = True


class KATalogusClientV1:
    def __init__(self, base_uri: str, organization: str):
        self.base_uri = base_uri
        self.organization = organization
        self.organization_uri = f"{base_uri}/v1/organisations/{organization}"

    def organization_exists(self):
        try:
            response = requests.get(f"{self.organization_uri}")
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError:
            return False

    def create_organization(self, name: str):
        response = requests.post(f"{self.base_uri}/v1/organisations/", json={"id": self.organization, "name": name})
        response.raise_for_status()

    def delete_organization(self):
        response = requests.delete(f"{self.organization_uri}")
        response.raise_for_status()

    def get_all_plugins(self):
        response = requests.get(f"{self.organization_uri}/plugins")
        return response.json()

    def get_plugin_details(self, plugin_id):
        response = requests.get(f"{self.organization_uri}/plugins/{plugin_id}")
        return response.json()

    def get_plugin_schema(self, plugin_id):
        response = requests.get(f"{self.organization_uri}/plugins/{plugin_id}/schema.json")
        return response.json()

    def get_all_settings(self) -> Dict[str, str]:
        response = requests.get(f"{self.organization_uri}/settings")
        return response.json()

    def get_plugin_settings(self, plugin_id: str) -> Dict[str, str]:
        response = requests.get(f"{self.organization_uri}/{plugin_id}/settings")
        return response.json()

    def add_plugin_setting(self, plugin_id: str, name: str, value: str) -> None:
        body = {"value": value}
        response = requests.post(f"{self.organization_uri}/{plugin_id}/settings/{name}", json=body)
        response.raise_for_status()

    def get_plugin_setting(self, plugin_id: str, name: str) -> str:
        response = requests.get(f"{self.organization_uri}/{plugin_id}/settings/{name}")
        return response.json()

    def add_setting(self, name: str, value: str) -> None:
        body = {"value": value}
        response = requests.post(f"{self.organization_uri}/settings/{name}", json=body)
        response.raise_for_status()

    def update_plugin_setting(self, plugin_id: str, name: str, value: str) -> None:
        body = {"value": value}
        response = requests.put(f"{self.organization_uri}/{plugin_id}/settings/{name}", json=body)
        response.raise_for_status()

    def delete_plugin_setting(self, plugin_id: str, name: str) -> None:
        response = requests.delete(f"{self.organization_uri}/{plugin_id}/settings/{name}")
        return response

    def health(self) -> ServiceHealth:
        response = requests.get(f"{self.base_uri}/health")
        response.raise_for_status()

        return ServiceHealth.parse_obj(response.json())

    def get_boefjes(self) -> List[Plugin]:
        response = requests.get(f"{self.organization_uri}/plugins")
        response.raise_for_status()

        return [parse_plugin(boefje) for boefje in response.json() if boefje["type"] == "boefje"]

    def get_boefje(self, boefje_id: str) -> Plugin:
        response = requests.get(f"{self.organization_uri}/plugins/{boefje_id}")
        response.raise_for_status()

        return parse_plugin(response.json())

    def enable_boefje(self, boefje_id: str) -> None:
        self._patch_boefje_state(boefje_id, True)

    def disable_boefje(self, boefje_id: str) -> None:
        self._patch_boefje_state(boefje_id, False)

    def get_enabled_boefjes(self) -> List[Plugin]:
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
        response = requests.get(f"{self.organization_uri}/plugins/{boefje_id}/description.md")
        response.raise_for_status()

        return response.content.decode("utf-8")

    def get_cover(self, boefje_id: str) -> BytesIO:
        response = requests.get(f"{self.organization_uri}/plugins/{boefje_id}/cover.jpg")
        response.raise_for_status()
        return BytesIO(response.content)


def parse_plugin(plugin: Dict) -> Plugin:
    try:
        consumes = {type_by_name(consumes) for consumes in plugin["consumes"]}
    except StopIteration:
        consumes = set()

    produces = set()
    for ooi in plugin["produces"]:
        try:
            produces.add(type_by_name(ooi))
        except StopIteration:
            pass

    return Plugin(
        id=plugin["id"],
        type=plugin["type"],
        name=plugin.get("name") or plugin["id"],
        repository_id=plugin["repository_id"],
        description=plugin["description"],
        scan_level=SCAN_LEVEL(plugin["scan_level"]),
        consumes=consumes,  # TODO: check if we still want to support multiple
        produces=produces,
        enabled=plugin["enabled"],
    )


def get_katalogus(organization: str) -> KATalogusClientV1:
    return KATalogusClientV1(KATALOGUS_API, organization)
