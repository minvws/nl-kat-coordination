import contextlib
import json
from io import BytesIO
from logging import getLogger
from typing import Dict, List, Optional, Set, Type

import requests
from django.conf import settings
from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator
from pydantic import BaseModel
from tools.enums import SCAN_LEVEL

from octopoes.models import OOI
from octopoes.models.types import type_by_name
from rocky.health import ServiceHealth

logger = getLogger(__name__)


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

    def dict(self, *args, **kwargs):
        """Pydantic does not stringify the OOI classes, but then templates can't render them"""
        plugin_dict = super().dict(*args, **kwargs)
        plugin_dict["consumes"] = {ooi_class.get_ooi_type() for ooi_class in plugin_dict["consumes"]}
        plugin_dict["produces"] = {ooi_class.get_ooi_type() for ooi_class in plugin_dict["produces"]}

        return plugin_dict


class Normalizer(BaseModel):
    id: str
    type: str
    name: str
    enabled: bool
    consumes: List[str]
    produces: Set[Type[OOI]]

    def dict(self, *args, **kwargs):
        plugin_dict = super().dict(*args, **kwargs)
        plugin_dict["produces"] = {ooi_class.get_ooi_type() for ooi_class in plugin_dict["produces"]}
        return plugin_dict


class KATalogusClientV1:
    def __init__(self, base_uri: str, organization: str):
        self.session = requests.Session()
        self.base_uri = base_uri
        self.organization = organization
        self.organization_uri = f"{base_uri}/v1/organisations/{organization}"

    def organization_exists(self) -> bool:
        response = self.session.get(f"{self.organization_uri}")

        return response.status_code != 404

    def create_organization(self, name: str):
        response = self.session.post(f"{self.base_uri}/v1/organisations/", json={"id": self.organization, "name": name})
        response.raise_for_status()

    def delete_organization(self):
        response = self.session.delete(f"{self.organization_uri}")
        response.raise_for_status()

    def get_all_plugins(self):
        response = self.session.get(f"{self.organization_uri}/plugins")
        response.raise_for_status()
        return [parse_plugin(plugin) for plugin in response.json()]

    def get_plugins_by_type(self, plugin_type):
        response = self.session.get(f"{self.organization_uri}/plugins?plugin_type={plugin_type}")
        response.raise_for_status()
        return [parse_plugin(plugin) for plugin in response.json()]

    def get_plugins(self, plugin_type: str = None):
        if plugin_type:
            return self.get_plugins_by_type(plugin_type)
        return self.get_all_plugins()

    def get_plugin(self, plugin_id: str) -> Plugin:
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}")
        response.raise_for_status()

        return parse_plugin(response.json())

    def get_plugin_schema(self, plugin_id) -> Optional[Dict]:
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}/schema.json")
        response.raise_for_status()

        schema = response.json()

        try:
            Draft202012Validator.check_schema(schema)
            return schema
        except SchemaError:
            logger.warning("Invalid schema found for plugin %s", plugin_id)

    def get_plugin_settings(self, plugin_id: str) -> Dict:
        response = self.session.get(f"{self.organization_uri}/{plugin_id}/settings")
        response.raise_for_status()
        return response.json()

    def upsert_plugin_settings(self, plugin_id: str, values: Dict) -> None:
        response = self.session.put(f"{self.organization_uri}/{plugin_id}/settings", json=values)
        response.raise_for_status()

    def delete_plugin_settings(self, plugin_id: str):
        response = self.session.delete(f"{self.organization_uri}/{plugin_id}/settings")
        response.raise_for_status()
        return response

    def clone_all_configuration_to_organization(self, to_organization: str):
        response = self.session.post(f"{self.organization_uri}/settings/clone/{to_organization}")
        response.raise_for_status()

        return response

    def health(self) -> ServiceHealth:
        response = self.session.get(f"{self.base_uri}/health")
        response.raise_for_status()

        return ServiceHealth.parse_obj(response.json())

    def get_normalizers(self) -> List[Normalizer]:
        response = self.session.get(f"{self.organization_uri}/plugins?plugin_type=normalizer")
        response.raise_for_status()
        return [parse_plugin(plugin) for plugin in response.json()]

    def get_boefjes(self) -> List[Plugin]:
        response = self.session.get(f"{self.organization_uri}/plugins?plugin_type=boefje")
        response.raise_for_status()
        return [parse_plugin(plugin) for plugin in response.json()]

    def enable_boefje(self, plugin: Plugin) -> None:
        self._patch_boefje_state(plugin.id, True, plugin.repository_id)

    def enable_boefje_by_id(self, boefje_id: str) -> None:
        self.enable_boefje(self.get_plugin(boefje_id))

    def disable_boefje(self, plugin: Plugin) -> None:
        self._patch_boefje_state(plugin.id, False, plugin.repository_id)

    def get_enabled_boefjes(self) -> List[Plugin]:
        return [boefje for boefje in self.get_boefjes() if boefje.enabled]

    def _patch_boefje_state(self, boefje_id: str, enabled: bool, repository_id: str) -> None:
        body = {"enabled": enabled}
        response = self.session.patch(
            f"{self.organization_uri}/repositories/{repository_id}/plugins/{boefje_id}",
            data=json.dumps(body),
        )
        response.raise_for_status()

    def get_description(self, boefje_id: str) -> str:
        response = self.session.get(f"{self.organization_uri}/plugins/{boefje_id}/description.md")
        response.raise_for_status()

        return response.content.decode("utf-8")

    def get_cover(self, boefje_id: str) -> BytesIO:
        response = self.session.get(f"{self.organization_uri}/plugins/{boefje_id}/cover.jpg")
        response.raise_for_status()
        return BytesIO(response.content)


def parse_normalizer(plugin: Dict) -> Normalizer:
    produces = set()
    for ooi in plugin["produces"]:
        with contextlib.suppress(StopIteration):
            produces.add(type_by_name(ooi))

    # TODO: give normalizers a proper name in backend
    name = plugin["id"].replace("_", " ").replace("kat", "").title()

    return Normalizer(
        id=plugin["id"],
        type=plugin["type"],
        name=name,
        enabled=plugin["enabled"],
        consumes=plugin["consumes"],
        produces=produces,
    )


def parse_plugin(plugin: Dict) -> Plugin:
    if plugin["type"] == "normalizer":
        return parse_normalizer(plugin)
    try:
        consumes = {type_by_name(consumes) for consumes in plugin["consumes"]}
    except StopIteration:
        consumes = set()

    produces = set()
    for ooi in plugin["produces"]:
        with contextlib.suppress(StopIteration):
            produces.add(type_by_name(ooi))

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
    return KATalogusClientV1(settings.KATALOGUS_API, organization)
