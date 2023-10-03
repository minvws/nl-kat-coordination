import contextlib
import json
from io import BytesIO
from logging import getLogger
from typing import Dict, List, Optional, Set, Type, Union

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
    repository_id: Optional[str] = None
    name: str
    version: Optional[str] = None
    authors: Optional[str] = None
    created: Optional[str] = None
    description: Optional[str] = None
    environment_keys: List[str] = None
    related: List[str] = None
    enabled: bool
    type: str
    produces: Set[Type[OOI]]

    def dict(self, *args, **kwargs):
        """Pydantic does not stringify the OOI classes, but then templates can't render them"""
        plugin_dict = super().dict(*args, **kwargs)
        plugin_dict["produces"] = {ooi_class.get_ooi_type() for ooi_class in plugin_dict["produces"]}
        return plugin_dict

    def can_scan(self, member) -> bool:
        return member.has_perm("tools.can_scan_organization")


class Boefje(Plugin):
    scan_level: SCAN_LEVEL
    consumes: Set[Type[OOI]]
    options: List[str] = None
    runnable_hash: Optional[str] = None

    def dict(self, *args, **kwargs):
        """Pydantic does not stringify the OOI classes, but then templates can't render them"""
        boefje_dict = super().dict(*args, **kwargs)
        boefje_dict["consumes"] = {ooi_class.get_ooi_type() for ooi_class in boefje_dict["consumes"]}
        return boefje_dict

    def can_scan(self, member) -> bool:
        return super().can_scan(member) and member.acknowledged_clearance_level >= self.scan_level.value


class Normalizer(Plugin):
    consumes: Set[str]


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

    def get_plugins(self, **params):
        response = self.session.get(f"{self.organization_uri}/plugins", params=params)
        response.raise_for_status()
        return [parse_plugin(plugin) for plugin in response.json()]

    def get_plugin(self, plugin_id: str) -> Union[Boefje, Normalizer]:
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
        return self.get_plugins(plugin_type="normalizer")

    def get_boefjes(self) -> List[Boefje]:
        return self.get_plugins(plugin_type="boefje")

    def enable_boefje(self, plugin: Boefje) -> None:
        self._patch_boefje_state(plugin.id, True, plugin.repository_id)

    def enable_boefje_by_id(self, boefje_id: str) -> None:
        self.enable_boefje(self.get_plugin(boefje_id))

    def disable_boefje(self, plugin: Boefje) -> None:
        self._patch_boefje_state(plugin.id, False, plugin.repository_id)

    def get_enabled_boefjes(self) -> List[Boefje]:
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


def parse_boefje(boefje: Dict) -> Boefje:
    scan_level = SCAN_LEVEL(boefje["scan_level"])

    consumes = set()
    produces = set()
    for type_name in boefje.get("consumes", []):
        try:
            consumes.add(type_by_name(type_name))
        except StopIteration:
            logger.warning("Unknown OOI type %s for boefje consumes %s", type_name, boefje["id"])

    for type_name in boefje.get("produces", []):
        try:
            produces.add(type_by_name(type_name))
        except StopIteration:
            logger.warning("Unknown OOI type %s for boefje produces %s", type_name, boefje["id"])

    return Boefje(
        id=boefje["id"],
        repository_id=boefje["repository_id"],
        name=boefje.get("name") or boefje["id"],
        description=boefje["description"],
        enabled=boefje["enabled"],
        type=boefje["type"],
        scan_level=scan_level,
        consumes=consumes,
        produces=produces,
    )


def parse_normalizer(normalizer: Dict) -> Normalizer:
    # TODO: give normalizers a proper name in backend
    name = normalizer["id"].replace("_", " ").replace("kat ", "").title()

    consumes = set(normalizer["consumes"])
    produces = set()
    with contextlib.suppress(StopIteration):
        consumes.add(f"normalizer/{name.lower()}")
        produces.add(type_by_name(normalizer["produces"]))

    return Normalizer(
        id=normalizer["id"],
        repository_id=normalizer["repository_id"],
        name=name or normalizer["id"],
        description=normalizer["description"],
        enabled=normalizer["enabled"],
        type=normalizer["type"],
        consumes=consumes,
        produces=produces,
    )


def parse_plugin(plugin: Dict) -> Union[Boefje, Normalizer]:
    if plugin["type"] == "boefje":
        return parse_boefje(plugin)
    if plugin["type"] == "normalizer":
        return parse_normalizer(plugin)


def get_katalogus(organization: str) -> KATalogusClientV1:
    return KATalogusClientV1(settings.KATALOGUS_API, organization)
