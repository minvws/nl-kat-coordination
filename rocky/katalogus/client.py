import json
from io import BytesIO
from logging import getLogger

import requests
from django.conf import settings
from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator
from pydantic import BaseModel, Field, field_serializer
from tools.enums import SCAN_LEVEL

from octopoes.models import OOI
from octopoes.models.types import type_by_name
from rocky.health import ServiceHealth

logger = getLogger(__name__)


class Plugin(BaseModel):
    id: str
    repository_id: str | None = None
    name: str
    version: str | None = None
    authors: str | None = None
    created: str | None = None
    description: str | None = None
    environment_keys: list[str] | None = None
    related: list[str] = Field(default_factory=list)
    enabled: bool
    type: str

    # def dict(self, *args, **kwargs):
    #     """Pydantic does not stringify the OOI classes, but then templates can't render them"""
    #     # todo: use field_serializer instead

    def can_scan(self, member) -> bool:
        return member.has_perm("tools.can_scan_organization")


class Boefje(Plugin):
    scan_level: SCAN_LEVEL
    consumes: set[type[OOI]]
    options: list[str] = None
    runnable_hash: str | None = None
    produces: set[str]

    # use a custom field_serializer for `consumes`
    @field_serializer("consumes")
    def serialize_consumes(self, consumes: set[type[OOI]]):
        return {ooi_class.get_ooi_type() for ooi_class in consumes}

    def can_scan(self, member) -> bool:
        return super().can_scan(member) and member.acknowledged_clearance_level >= self.scan_level.value


class Normalizer(Plugin):
    consumes: set[str]
    produces: set[type[OOI]]

    # use a custom field_serializer for `produces`
    @field_serializer("produces")
    def serialize_produces(self, produces: set[type[OOI]]):
        return {ooi_class.get_ooi_type() for ooi_class in produces}


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

    def get_plugin(self, plugin_id: str) -> Boefje | Normalizer:
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}")
        response.raise_for_status()
        return parse_plugin(response.json())

    def get_plugin_schema(self, plugin_id) -> dict | None:
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}/schema.json")
        response.raise_for_status()

        schema = response.json()

        try:
            Draft202012Validator.check_schema(schema)
            return schema
        except SchemaError as error:
            logger.warning("Invalid schema found for plugin %s, %s", plugin_id, error)

    def get_plugin_settings(self, plugin_id: str) -> dict:
        response = self.session.get(f"{self.organization_uri}/{plugin_id}/settings")
        response.raise_for_status()
        return response.json()

    def upsert_plugin_settings(self, plugin_id: str, values: dict) -> None:
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

        return ServiceHealth.model_validate_json(response.content)

    def get_normalizers(self) -> list[Normalizer]:
        return self.get_plugins(plugin_type="normalizer")

    def get_boefjes(self) -> list[Boefje]:
        return self.get_plugins(plugin_type="boefje")

    def enable_boefje(self, plugin: Boefje) -> None:
        self._patch_boefje_state(plugin.id, True, plugin.repository_id)

    def enable_boefje_by_id(self, boefje_id: str) -> None:
        self.enable_boefje(self.get_plugin(boefje_id))

    def disable_boefje(self, plugin: Boefje) -> None:
        self._patch_boefje_state(plugin.id, False, plugin.repository_id)

    def get_enabled_boefjes(self) -> list[Boefje]:
        return [plugin for plugin in self.get_boefjes() if plugin.enabled]

    def get_enabled_normalizers(self) -> list[Normalizer]:
        return [plugin for plugin in self.get_normalizers() if plugin.enabled]

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


def parse_boefje(boefje: dict) -> Boefje:
    scan_level = SCAN_LEVEL(boefje["scan_level"])

    consumes = set()

    for type_name in boefje.get("consumes", []):
        try:
            consumes.add(type_by_name(type_name))
        except StopIteration:
            logger.warning("Unknown OOI type %s for boefje consumes %s", type_name, boefje["id"])

    return Boefje(
        id=boefje["id"],
        repository_id=boefje["repository_id"],
        name=boefje.get("name") or boefje["id"],
        description=boefje["description"],
        enabled=boefje["enabled"],
        type=boefje["type"],
        scan_level=scan_level,
        consumes=consumes,
        produces=boefje["produces"],
    )


def parse_normalizer(normalizer: dict) -> Normalizer:
    # TODO: give normalizers a proper name in backend
    name = normalizer["id"].replace("_", " ").replace("kat ", "").title()

    consumes = set(normalizer["consumes"])
    consumes.add(f"normalizer/{normalizer['id']}")
    produces = set()
    for type_name in normalizer.get("produces", []):
        try:
            produces.add(type_by_name(type_name))
        except StopIteration:
            logger.warning("Unknown OOI type %s for normalizer produces %s", type_name, normalizer["id"])

    return Normalizer(
        id=normalizer["id"],
        repository_id=normalizer["repository_id"],
        name=name,
        description=normalizer["description"],
        enabled=normalizer["enabled"],
        type=normalizer["type"],
        consumes=consumes,
        produces=produces,
    )


def parse_plugin(plugin: dict) -> Boefje | Normalizer:
    if plugin["type"] == "boefje":
        return parse_boefje(plugin)
    if plugin["type"] == "normalizer":
        return parse_normalizer(plugin)


def get_katalogus(organization: str) -> KATalogusClientV1:
    return KATalogusClientV1(settings.KATALOGUS_API, organization)
