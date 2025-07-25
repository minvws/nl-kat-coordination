import json
from typing import Annotated
from urllib.parse import quote

import httpx
import structlog
from django.core.exceptions import ValidationError
from django.core.validators import validate_unicode_slug
from django.db import transaction
from django.db.models import FilteredRelation, Q
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _
from pydantic import AfterValidator, BaseModel, Field

from katalogus.models import Boefje, BoefjeConfig, Normalizer, NormalizerConfig
from openkat.models import Organization, OrganizationMember

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
    type: str
    enabled: bool


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


class KATalogusHTTPStatusError(KATalogusError):
    def __init__(self, error: httpx.HTTPStatusError):
        self.error = error

        super().__init__(_("An HTTP %d error occurred. Check logs for more info.").format(error.response.status_code))


class KATalogusHTTPError(KATalogusError):
    def __init__(self, error: httpx.HTTPError):
        self.error = error

        super().__init__(_("An HTTP error occurred. Check logs for more info."))


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
    def __init__(self, error_message: str):
        super().__init__(error_message)


class KATalogusClient:
    def get_plugins(
        self,
        organization_code: str,
        plugin_type: str | None = None,
        state: bool | None = None,
        ids: list[str] | None = None,
        oci_image: str | None = None,
    ) -> list[Boefje | Normalizer]:
        boefjes = []
        organization = Organization.objects.get(code=organization_code)

        if not plugin_type or plugin_type == "boefje":
            # This adds an "enabled" field to the boefje model based on the given organization_code, defaulting to
            # False though the Coalesce.
            query = Boefje.objects.annotate(
                boefje_config=FilteredRelation(
                    "boefje_configs", condition=Q(boefje_configs__organization=organization)
                ),
                enabled=Coalesce("boefje_configs__enabled", False),
            ).distinct()

            if state is True:
                query = query.filter(enabled=True)
            if state is False:
                query = query.filter(enabled=False)

            if oci_image:
                query = query.filter(oci_image=oci_image)

            if ids:
                query = query.filter(plugin_id__in=ids)

            boefjes.extend(query.all())

        normalizers = []

        if not plugin_type or plugin_type == "normalizer":
            query = Normalizer.objects.annotate(
                normalizer_config=FilteredRelation(
                    "normalizer_configs", condition=Q(normalizer_configs__organization=organization)
                ),
                enabled=Coalesce("normalizer_configs__enabled", True),
            ).distinct()

            if state is True:
                query = query.filter(enabled=True)
            if state is False:
                query = query.filter(enabled=False)

            if ids:
                query = query.filter(plugin_id__in=ids)

            normalizers.extend(query.all())

        return boefjes + normalizers

    def get_plugin(self, organization_code: str, plugin_id: int, plugin_type: str = "boefje") -> Boefje | Normalizer:
        if plugin_type == "boefje":
            boefjes = (
                Boefje.objects.filter(id=plugin_id)
                .filter(Q(boefje_configs__organization__code=organization_code) | Q(boefje_configs__isnull=True))
                .annotate(enabled=Coalesce("boefje_configs__enabled", False))
            )

            if boefjes.exists():
                return boefjes.first()

        if plugin_type == "normalizer":
            normalizers = (
                Normalizer.objects.filter(id=plugin_id)
                .filter(
                    Q(normalizer_configs__organization__code=organization_code) | Q(normalizer_configs__isnull=True)
                )
                .annotate(enabled=Coalesce("normalizer_configs__enabled", True))
            )

            if normalizers.exists():
                return normalizers.first()

        raise KeyError(f"No plugin found for organization {organization_code} and plugin id {plugin_id}")

    def get_plugin_settings(self, organization_code: str, plugin_id: int) -> dict:
        config = BoefjeConfig.objects.filter(boefje__id=plugin_id, organization__code=organization_code).first()

        if not config:
            return {}

        return json.loads(config.settings)

    def upsert_plugin_settings(self, organization_code: str, plugin_id: int, values: dict) -> None:
        boefje, created = Boefje.objects.get_or_create(id=plugin_id)
        config, created = BoefjeConfig.objects.get_or_create(
            boefje=boefje, organization=Organization.objects.get(code=organization_code)
        )
        config.settings = json.dumps(values)
        config.save()

    def delete_plugin_settings(self, organization_code: str, plugin_id: int) -> None:
        BoefjeConfig.objects.get(boefje_id=plugin_id, organization__code=organization_code).delete()

    def clone_all_configuration_to_organization(self, from_organization_code: str, to_organization_code: str):
        to_organization = Organization.objects.get(code=quote(to_organization_code))
        from_organization = Organization.objects.get(code=quote(from_organization_code))
        logger.info("Cloning organization settings", event_code=910000, to_organization_code=to_organization.code)

        with transaction.atomic():
            BoefjeConfig.objects.filter(organization=to_organization).delete()
            NormalizerConfig.objects.filter(organization=to_organization).delete()

            for boefje_config in BoefjeConfig.objects.filter(organization__code=from_organization):
                BoefjeConfig(
                    settings=boefje_config.settings,
                    enabled=boefje_config.enabled,
                    organization=to_organization,
                    boefje=boefje_config.boefje,
                ).save()

            for normalizer_config in NormalizerConfig.objects.filter(organization__code=from_organization):
                NormalizerConfig(
                    settings=normalizer_config.settings,
                    enabled=normalizer_config.enabled,
                    organization=to_organization,
                    normalizer=normalizer_config.normalizer,
                ).save()

    def get_normalizers(self, organization_code: str) -> list[Normalizer]:
        return self.get_plugins(organization_code, plugin_type="normalizer")

    def get_boefjes(self, organization_code: str) -> list[Boefje]:
        return self.get_plugins(organization_code, plugin_type="boefje")

    def enable_plugin(self, organization_code: str, plugin: Boefje | Normalizer) -> None:
        logger.info("Enabling plugin", event_code=800021, plugin=plugin.id)

        self._patch_plugin_state(organization_code, plugin.id, True)

    def enable_boefje_by_id(self, organization_code: str, boefje_id: int) -> None:
        self.enable_plugin(organization_code, self.get_plugin(organization_code, boefje_id, "boefje"))

    def disable_plugin(self, organization_code: str, plugin: Boefje | Normalizer) -> None:
        logger.info("Disabling plugin", event_code=800022, plugin=plugin.id)
        self._patch_plugin_state(organization_code, plugin.id, False)

    def get_enabled_boefjes(self, organization_code: str) -> list[Boefje | Normalizer]:
        return self.get_plugins(organization_code, plugin_type="boefje", state=True)

    def _patch_plugin_state(self, organization_code: str, plugin_id: int, enabled: bool) -> None:
        logger.info("Toggle plugin state", id=plugin_id, enabled=enabled)

        boefje = Boefje.objects.filter(id=plugin_id).first()

        if boefje is not None:
            BoefjeConfig.objects.update_or_create(
                defaults={"enabled": enabled},
                boefje=boefje,
                organization=Organization.objects.get(code=organization_code),
            )

        normalizer = Normalizer.objects.filter(id=plugin_id).first()

        if normalizer is not None:
            NormalizerConfig.objects.update_or_create(
                defaults={"enabled": enabled},
                normalizer=normalizer,
                organization=Organization.objects.get(code=organization_code),
            )


class KATalogus:
    """
    An adapter between the full KATalogusClient and the organization-specific context of most views. This restricts
    the set of available methods on the KATalogusClient and simplifies the interface by "currying" the organization
    into the relevant methods as an argument. We should use this class in the views to avoid making calls exposing
    information from other organizations users are not allowed to see.
    """

    def __init__(self, katalogus_client: KATalogusClient, member: OrganizationMember):
        self._katalogus_client = katalogus_client
        self._member = member

    def get_plugins(self, **params) -> list[Boefje | Normalizer]:
        return self._katalogus_client.get_plugins(self._member.organization.code, **params)

    def get_plugin(self, plugin_id: int, plugin_type: str = "boefje") -> Boefje | Normalizer:
        return self._katalogus_client.get_plugin(self._member.organization.code, plugin_id, plugin_type)

    def get_plugin_settings(self, plugin_id: int) -> dict:
        if not self._member.has_perm("openkat.can_view_katalogus_settings"):
            raise KATalogusNotAllowedError(_("User is not allowed to see plugin settings"))

        return self._katalogus_client.get_plugin_settings(self._member.organization.code, plugin_id)

    def upsert_plugin_settings(self, plugin_id: int, values: dict) -> None:
        if not self._member.has_perm("openkat.can_set_katalogus_settings"):
            raise KATalogusNotAllowedError(_("User is not allowed to set plugin settings"))

        return self._katalogus_client.upsert_plugin_settings(self._member.organization.code, plugin_id, values)

    def delete_plugin_settings(self, plugin_id: int) -> None:
        if not self._member.has_perm("openkat.can_set_katalogus_settings"):
            raise KATalogusNotAllowedError(_("User is not allowed to delete plugin settings"))

        return self._katalogus_client.delete_plugin_settings(self._member.organization.code, plugin_id)

    def clone_all_configuration_to_organization(self, to_organization: str):
        if not self._member.has_perm("openkat.can_view_katalogus_settings"):
            raise KATalogusNotAllowedError(_("User is not allowed to view plugin settings"))

        try:
            to_member = OrganizationMember.objects.get(user=self._member.user, organization__code=to_organization)
        except Organization.DoesNotExist:
            raise
        except OrganizationMember.DoesNotExist:
            if not self._member.user.has_perm("openkat.can_access_all_organizations"):
                raise KATalogusNotAllowedError(_("User is not allowed to access the other organization"))
            if not self._member.user.has_perm("openkat.can_set_katalogus_settings"):
                raise KATalogusNotAllowedError(_("User is not allowed to set plugin settings"))
        else:
            if to_member.blocked:
                raise KATalogusNotAllowedError(_("User is not allowed to access the other organization"))

            if not to_member.has_perm("openkat.can_set_katalogus_settings"):
                raise KATalogusNotAllowedError(_("User is not allowed to set plugin settings"))

        return self._katalogus_client.clone_all_configuration_to_organization(
            self._member.organization.code, to_organization
        )

    def get_normalizers(self) -> list[Normalizer]:
        return self._katalogus_client.get_normalizers(self._member.organization.code)

    def get_boefjes(self) -> list[Boefje]:
        return self._katalogus_client.get_boefjes(self._member.organization.code)

    def enable_plugin(self, plugin: Boefje | Normalizer) -> None:
        if not self._member.has_perm("openkat.can_enable_disable_plugin"):
            raise KATalogusNotAllowedError(_("User is not allowed to enable plugins"))

        return self._katalogus_client.enable_plugin(self._member.organization.code, plugin)

    def enable_boefje_by_id(self, boefje_id: int) -> None:
        if not self._member.has_perm("openkat.can_enable_disable_plugin"):
            raise KATalogusNotAllowedError(_("User is not allowed to enable plugins"))

        return self._katalogus_client.enable_boefje_by_id(self._member.organization.code, boefje_id)

    def disable_plugin(self, plugin: Boefje | Normalizer) -> None:
        if not self._member.has_perm("openkat.can_enable_disable_plugin"):
            raise KATalogusNotAllowedError(_("User is not allowed to disable plugins"))

        return self._katalogus_client.disable_plugin(self._member.organization.code, plugin)

    def get_enabled_boefjes(self) -> list[Boefje]:
        return self._katalogus_client.get_plugins(self._member.organization.code, plugin_type="boefje", state=True)


def get_katalogus_client() -> KATalogusClient:
    return KATalogusClient()


def get_katalogus(member: OrganizationMember) -> KATalogus:
    return KATalogus(get_katalogus_client(), member)
