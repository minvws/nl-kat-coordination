import contextlib
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from sqlalchemy.orm import Session

from boefjes.katalogus.local_repository import LocalPluginRepository, get_local_repository
from boefjes.katalogus.models import FilterParameters, PaginationParameters, PluginType
from boefjes.katalogus.storage.interfaces import (
    NotFound,
    PluginEnabledStorage,
    SettingsNotConformingToSchema,
    SettingsStorage,
)
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.plugin_enabled_storage import create_plugin_enabled_storage
from boefjes.sql.setting_storage import create_setting_storage

logger = logging.getLogger(__name__)


class PluginService:
    def __init__(
        self,
        plugin_enabled_store: PluginEnabledStorage,
        settings_storage: SettingsStorage,
        local_repo: LocalPluginRepository,
    ):
        self.plugin_enabled_store = plugin_enabled_store
        self.settings_storage = settings_storage
        self.local_repo = local_repo

    def __enter__(self):
        self.plugin_enabled_store.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.plugin_enabled_store.__exit__(exc_type, exc_val, exc_tb)

    def get_all(self, organisation_id: str) -> list[PluginType]:
        return [self._set_plugin_enabled(plugin, organisation_id) for plugin in self.local_repo.get_all()]

    def by_plugin_id(self, plugin_id: str, organisation_id: str) -> PluginType:
        all_plugins = self.get_all(organisation_id)

        for plugin in all_plugins:
            if plugin.id == plugin_id:
                return plugin

        raise KeyError(f"Plugin {plugin_id} not found for {organisation_id}")

    def get_all_settings(self, organisation_id: str, plugin_id: str):
        return self.settings_storage.get_all(organisation_id, plugin_id)

    def clone_settings_to_organisation(self, from_organisation: str, to_organisation: str):
        # One requirement is that we also do not keep previously enabled boefjes enabled of they are not copied.
        for plugin_id in self.plugin_enabled_store.get_all_enabled(to_organisation):
            self.update_by_id(plugin_id, to_organisation, enabled=False)

        for plugin in self.get_all(from_organisation):
            if all_settings := self.get_all_settings(from_organisation, plugin.id):
                self.upsert_settings(all_settings, to_organisation, plugin.id)

        for plugin_id in self.plugin_enabled_store.get_all_enabled(from_organisation):
            self.update_by_id(plugin_id, to_organisation, enabled=True)

    def upsert_settings(self, values: dict, organisation_id: str, plugin_id: str):
        self._assert_settings_match_schema(values, organisation_id, plugin_id)

        return self.settings_storage.upsert(values, organisation_id, plugin_id)

    def delete_settings(self, organisation_id: str, plugin_id: str):
        self.settings_storage.delete(organisation_id, plugin_id)

        try:
            self._assert_settings_match_schema({}, organisation_id, plugin_id)
        except SettingsNotConformingToSchema:
            logger.warning("Making sure %s is disabled for %s because settings are deleted", plugin_id, organisation_id)

            self.update_by_id(plugin_id, organisation_id, False)

    def schema(self, plugin_id: str) -> dict | None:
        return self.local_repo.schema(plugin_id)

    def cover(self, plugin_id: str) -> Path:
        try:
            return self.local_repo.cover_path(plugin_id)
        except KeyError:
            return self.local_repo.default_cover_path()

    def description(self, plugin_id: str, organisation_id: str) -> str:
        local_path = self.local_repo.description_path(plugin_id)

        if local_path and local_path.exists():
            return local_path.read_text()

        try:
            return self.by_plugin_id(plugin_id, organisation_id).description or ""
        except KeyError:
            logger.error("Plugin not found: %s", plugin_id)
            return ""

    def update_by_id(self, plugin_id: str, organisation_id: str, enabled: bool):
        if enabled:
            all_settings = self.settings_storage.get_all(organisation_id, plugin_id)
            self._assert_settings_match_schema(all_settings, organisation_id, plugin_id)

        self.plugin_enabled_store.update_or_create_by_id(
            plugin_id,
            enabled,
            organisation_id,
        )

    def _assert_settings_match_schema(self, all_settings: dict, organisation_id: str, plugin_id: str):
        schema = self.schema(plugin_id)

        if schema:  # No schema means that there is nothing to assert
            try:
                validate(instance=all_settings, schema=schema)
            except ValidationError as e:
                raise SettingsNotConformingToSchema(organisation_id, plugin_id, e.message) from e

    def _set_plugin_enabled(self, plugin: PluginType, organisation_id: str) -> PluginType:
        with contextlib.suppress(KeyError, NotFound):
            plugin.enabled = self.plugin_enabled_store.get_by_id(plugin.id, organisation_id)

        return plugin


def get_plugin_service(organisation_id: str) -> Iterator[PluginService]:
    def closure(session: Session):
        return PluginService(
            create_plugin_enabled_storage(session),
            create_setting_storage(session),
            get_local_repository(),
        )

    yield from session_managed_iterator(closure)


def get_pagination_parameters(offset: int = 0, limit: int | None = None) -> PaginationParameters:
    return PaginationParameters(offset=offset, limit=limit)


def get_plugins_filter_parameters(
    q: str | None = None,
    plugin_type: Literal["boefje", "normalizer", "bit"] | None = None,
    state: bool | None = None,
) -> FilterParameters:
    return FilterParameters(q=q, type=plugin_type, state=state)
