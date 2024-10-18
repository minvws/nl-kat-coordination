import json
from io import BytesIO
from typing import Annotated
from urllib.parse import quote

import httpx
import structlog
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_unicode_slug
from django.utils.translation import gettext_lazy as _
from httpx import codes
from jsonschema.exceptions import SchemaError
from jsonschema.validators import Draft202012Validator
from pydantic import AfterValidator, BaseModel, Field, field_serializer
from tools.enums import SCAN_LEVEL

from octopoes.models import OOI
from octopoes.models.exception import TypeNotFound
from octopoes.models.types import type_by_name
from rocky.health import ServiceHealth

logger = structlog.get_logger("katalogus_client")


def valid_plugin_id(plugin_id: str) -> str:
    # plugin IDs should alphanumeric, including dashes, underscores and dots.
    if not plugin_id.replace("-", "").replace("_", "").replace(".", "").isalnum():
        raise ValueError("Plugin ID is not valid")

    return plugin_id


def valid_organization_code(organization_code: str) -> str:
    try:
        validate_unicode_slug(organization_code)
        return organization_code
    except ValidationError:
        raise ValueError("Organization code is not valid")


class Plugin(BaseModel):
    id: Annotated[str, AfterValidator(valid_plugin_id)]
    name: str
    version: str | None = None
    authors: str | None = None
    created: str | None = None
    description: str | None = None
    related: list[str] = Field(default_factory=list)
    enabled: bool
    type: str

    def can_scan(self, member) -> bool:
        return member.has_perm("tools.can_scan_organization")


class Boefje(Plugin):
    scan_level: SCAN_LEVEL
    consumes: set[type[OOI]] = Field(default_factory=set)
    produces: set[str] = Field(default_factory=set)
    options: list[str] | None = None
    runnable_hash: str | None = None
    interval: int | None = None
    boefje_schema: dict | None = None
    oci_image: str | None = None
    oci_arguments: list[str] = Field(default_factory=list)

    # use a custom field_serializer for `consumes`
    @field_serializer("consumes")
    def serialize_consumes(self, consumes: set[type[OOI]]):
        return {ooi_class.get_ooi_type() for ooi_class in consumes}

    def can_scan(self, member) -> bool:
        return super().can_scan(member) and member.has_clearance_level(self.scan_level.value)


class Normalizer(Plugin):
    consumes: set[str]
    produces: set[type[OOI]]

    # use a custom field_serializer for `produces`
    @field_serializer("produces")
    def serialize_produces(self, produces: set[type[OOI]]):
        return {ooi_class.get_ooi_type() for ooi_class in produces}


class KATalogusError(Exception):
    @property
    def message(self):
        return self._message

    def __init__(self, message: str | None = None):
        if message is None:
            message = _("The KATalogus has an unexpected error. Check the logs for further details.")

        self._message = message

        super().__init__(message)

    def __str__(self):
        return self._message


class DuplicatePluginError(KATalogusError):
    def __init__(self, error_message: str):
        super().__init__(error_message)


class DuplicateNameError(KATalogusError):
    def __init__(self):
        super().__init__(_("Boefje with this name already exists."))


class DuplicateIdError(KATalogusError):
    def __init__(self):
        super().__init__(_("Boefje with this ID already exists."))


class KATalogusNotAllowedError(KATalogusError):
    def __init__(self):
        super().__init__(_("Editing this boefje is not allowed because it is static."))


class KATalogusHTTPStatusError(KATalogusError):
    def __init__(self, error: httpx.HTTPStatusError):
        self.error = error

        super().__init__(_("An HTTP %d error occurred. Check logs for more info.").format(error.response.status_code))


class KATalogusClient:
    def __init__(self, base_uri: str, organization: str | None):
        self.session = httpx.Client(base_url=base_uri)
        self.organization = valid_organization_code(organization) if organization else organization
        self.organization_uri = f"/v1/organisations/{organization}"

    def organization_exists(self) -> bool:
        response = self.session.get(self.organization_uri)

        return response.status_code != 404

    def create_organization(self, name: str):
        response = self.session.post("/v1/organisations/", json={"id": self.organization, "name": name})
        response.raise_for_status()

        logger.info("Created organization", name=name)

    def delete_organization(self):
        response = self.session.delete(self.organization_uri)
        response.raise_for_status()

        logger.info("Deleted organization", organization_code=self.organization)

    def get_plugins(self, **params) -> list[Plugin]:
        try:
            response = self.session.get(f"{self.organization_uri}/plugins", params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise KATalogusHTTPStatusError(error)
        return [parse_plugin(plugin) for plugin in response.json()]

    def get_plugin(self, plugin_id: str) -> Plugin:
        plugin_id = quote(plugin_id)
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}")
        response.raise_for_status()

        return parse_plugin(response.json())

    def get_plugin_schema(self, plugin_id: str) -> dict | None:
        plugin_id = quote(plugin_id)
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}/schema.json")
        response.raise_for_status()

        schema = response.json()
        if not schema:
            return None

        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            logger.warning("Invalid schema found for plugin %s, %s", plugin_id, error)
        else:
            return schema

        return None

    def get_plugin_settings(self, plugin_id: str) -> dict:
        plugin_id = quote(plugin_id)
        response = self.session.get(f"{self.organization_uri}/{plugin_id}/settings")
        response.raise_for_status()
        return response.json()

    def upsert_plugin_settings(self, plugin_id: str, values: dict) -> None:
        plugin_id = quote(plugin_id)
        response = self.session.put(f"{self.organization_uri}/{plugin_id}/settings", json=values)
        response.raise_for_status()

        logger.info("Upsert plugin settings", plugin_id=plugin_id)

    def delete_plugin_settings(self, plugin_id: str):
        plugin_id = quote(plugin_id)
        response = self.session.delete(f"{self.organization_uri}/{plugin_id}/settings")
        response.raise_for_status()

        logger.info("Delete plugin settings", plugin_id=plugin_id)

        return response

    def clone_all_configuration_to_organization(self, to_organization: str):
        to_organization = quote(to_organization)
        response = self.session.post(f"{self.organization_uri}/settings/clone/{to_organization}")
        response.raise_for_status()

        return response

    def health(self) -> ServiceHealth:
        response = self.session.get("/health")
        response.raise_for_status()

        return ServiceHealth.model_validate_json(response.content)

    def get_normalizers(self) -> list[Plugin]:
        return self.get_plugins(plugin_type="normalizer")

    def get_boefjes(self) -> list[Plugin]:
        return self.get_plugins(plugin_type="boefje")

    def enable_plugin(self, plugin: Plugin) -> None:
        self._patch_plugin_state(plugin.id, True)

    def enable_boefje_by_id(self, boefje_id: str) -> None:
        self.enable_plugin(self.get_plugin(boefje_id))

    def disable_plugin(self, plugin: Plugin) -> None:
        self._patch_plugin_state(plugin.id, False)

    def get_enabled_boefjes(self) -> list[Plugin]:
        return [plugin for plugin in self.get_boefjes() if plugin.enabled]

    def get_enabled_normalizers(self) -> list[Plugin]:
        return [plugin for plugin in self.get_normalizers() if plugin.enabled]

    def _patch_plugin_state(self, plugin_id: str, enabled: bool) -> None:
        logger.info("Toggle plugin state", plugin_id=plugin_id, enabled=enabled)
        plugin_id = quote(plugin_id)

        response = self.session.patch(f"{self.organization_uri}/plugins/{plugin_id}", json={"enabled": enabled})
        response.raise_for_status()

    def get_description(self, plugin_id: str) -> str:
        plugin_id = quote(plugin_id)
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}/description.md")
        response.raise_for_status()

        return response.content.decode("utf-8")

    def get_cover(self, plugin_id: str) -> BytesIO:
        plugin_id = quote(plugin_id)
        response = self.session.get(f"{self.organization_uri}/plugins/{plugin_id}/cover.jpg")
        response.raise_for_status()
        return BytesIO(response.content)

    def create_plugin(self, plugin: Plugin) -> None:
        try:
            response = self.session.post(
                f"{self.organization_uri}/plugins",
                headers={"Content-Type": "application/json"},
                content=plugin.model_dump_json(exclude_none=True),
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == codes.CREATED:
                logger.info("Plugin %s created", plugin.name)
            else:
                logger.info("Plugin %s could not be created", plugin.name)
            error_message = json.loads(error.response.text).get("detail")
            if error.response.status_code == codes.BAD_REQUEST and "Duplicate plugin" in error_message:
                raise DuplicatePluginError(error_message)
            else:
                raise error

    def edit_plugin(self, plugin: Plugin) -> None:
        try:
            response = self.session.patch(
                f"{self.organization_uri}/boefjes/{plugin.id}", content=plugin.model_dump_json(exclude_none=True)
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            if error.response.status_code == codes.CREATED:
                logger.info("Plugin %s updated", plugin.name)
            else:
                logger.info("Plugin %s could not be updated", plugin.name)
            if error.response.status_code == codes.BAD_REQUEST and "duplicate key" in error.response.text:
                raise DuplicatePluginError("Duplicate plugin name")
            if error.response.status_code in [codes.FORBIDDEN, codes.NOT_FOUND]:
                raise KATalogusNotAllowedError
            else:
                raise error


def parse_boefje(boefje: dict) -> Boefje:
    scan_level = SCAN_LEVEL(boefje["scan_level"])

    consumes = set()

    for type_name in boefje.get("consumes", []):
        try:
            consumes.add(type_by_name(type_name))
        except TypeNotFound:
            logger.warning("Unknown OOI type %s for boefje consumes %s", type_name, boefje["id"])

    return Boefje(
        id=boefje["id"],
        name=boefje.get("name") or boefje["id"],
        created=boefje.get("created"),
        description=boefje.get("description"),
        interval=boefje.get("interval"),
        enabled=boefje["enabled"],
        type=boefje["type"],
        scan_level=scan_level,
        consumes=consumes,
        produces=boefje["produces"],
        boefje_schema=boefje.get("boefje_schema"),
        oci_image=boefje.get("oci_image"),
        oci_arguments=boefje.get("oci_arguments", []),
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
        except TypeNotFound:
            logger.warning("Unknown OOI type %s for normalizer produces %s", type_name, normalizer["id"])

    return Normalizer(
        id=normalizer["id"],
        name=name,
        description=normalizer["description"],
        enabled=normalizer["enabled"],
        type=normalizer["type"],
        consumes=consumes,
        produces=produces,
    )


def parse_plugin(plugin: dict) -> Plugin:
    if plugin["type"] == "boefje":
        return parse_boefje(plugin)
    elif plugin["type"] == "normalizer":
        return parse_normalizer(plugin)
    else:
        raise Exception(f"Unknown plugin type: {plugin['type']}")


def get_katalogus(organization: str) -> KATalogusClient:
    return KATalogusClient(settings.KATALOGUS_API, organization)
