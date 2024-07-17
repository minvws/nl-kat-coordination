import contextlib
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

import structlog
from fastapi import Query
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from sqlalchemy.orm import Session

from boefjes.local_repository import LocalPluginRepository, get_local_repository
from boefjes.models import Boefje, FilterParameters, Normalizer, PaginationParameters, PluginType
from boefjes.sql.config_storage import create_config_storage
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.plugin_storage import create_plugin_storage
from boefjes.storage.interfaces import (
    ConfigStorage,
    ExistingPluginId,
    NotFound,
    PluginNotFound,
    PluginStorage,
    SettingsNotConformingToSchema,
)

logger = structlog.get_logger(__name__)


class PluginService:
    def __init__(
        self,
        plugin_storage: PluginStorage,
        config_storage: ConfigStorage,
        local_repo: LocalPluginRepository,
    ):
        self.plugin_storage = plugin_storage
        self.config_storage = config_storage
        self.local_repo = local_repo

    def __enter__(self):
        self.plugin_storage.__enter__()
        self.config_storage.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.plugin_storage.__exit__(exc_type, exc_val, exc_tb)
        self.config_storage.__exit__(exc_type, exc_val, exc_tb)

    def get_all(self, organisation_id: str) -> list[PluginType]:
        all_plugins = self._get_all_without_enabled()

        return [self._set_plugin_enabled(plugin, organisation_id) for plugin in all_plugins.values()]

    def _get_all_without_enabled(self):
        all_plugins = {plugin.id: plugin for plugin in self.local_repo.get_all()}

        for plugin in self.plugin_storage.get_all():
            all_plugins[plugin.id] = plugin

        return all_plugins

    def by_plugin_id(self, plugin_id: str, organisation_id: str) -> PluginType:
        all_plugins = self.get_all(organisation_id)

        for plugin in all_plugins:
            if plugin.id == plugin_id:
                return plugin

        raise KeyError(f"Plugin {plugin_id} not found for {organisation_id}")

    def by_plugin_ids(self, plugin_ids: list[str], organisation_id: str) -> list[PluginType]:
        all_plugins = self.get_all(organisation_id)
        plugin_map: dict[str, PluginType] = {plugin.id: plugin for plugin in all_plugins}

        found_plugins = []
        for plugin_id in plugin_ids:
            if plugin_id in plugin_map:
                found_plugins.append(plugin_map[plugin_id])
            else:
                raise KeyError(f"Plugin {plugin_id} not found for {organisation_id}")

        return found_plugins

    def get_all_settings(self, organisation_id: str, plugin_id: str):
        return self.config_storage.get_all_settings(organisation_id, plugin_id)

    def clone_settings_to_organisation(self, from_organisation: str, to_organisation: str):
        # One requirement is that only boefjes enabled in the from_organisation end up being enabled for the target.
        for plugin_id in self.config_storage.get_enabled_boefjes(to_organisation):
            self.set_enabled_by_id(plugin_id, to_organisation, enabled=False)

        for plugin in self.get_all(from_organisation):
            if all_settings := self.get_all_settings(from_organisation, plugin.id):
                self.upsert_settings(all_settings, to_organisation, plugin.id)

        for plugin_id in self.config_storage.get_enabled_boefjes(from_organisation):
            self.set_enabled_by_id(plugin_id, to_organisation, enabled=True)

    def upsert_settings(self, settings: dict, organisation_id: str, plugin_id: str):
        self._assert_settings_match_schema(settings, organisation_id, plugin_id)
        self._put_boefje(plugin_id)

        return self.config_storage.upsert(organisation_id, plugin_id, settings=settings)

    def create_boefje(self, boefje: Boefje) -> None:
        try:
            self.local_repo.by_id(boefje.id)
            raise ExistingPluginId(boefje.id)
        except KeyError:
            self.plugin_storage.create_boefje(boefje)

    def create_normalizer(self, normalizer: Normalizer) -> None:
        try:
            self.local_repo.by_id(normalizer.id)
            raise ExistingPluginId(normalizer.id)
        except KeyError:
            self.plugin_storage.create_normalizer(normalizer)

    def _put_boefje(self, boefje_id: str) -> None:
        """Check existence of a boefje, and insert a database entry if it concerns a local boefje"""

        try:
            self.plugin_storage.boefje_by_id(boefje_id)
        except PluginNotFound:
            try:
                plugin = self.local_repo.by_id(boefje_id)
            except KeyError:
                raise

            if plugin.type != "boefje":
                raise
            self.plugin_storage.create_boefje(plugin)

    def _put_normalizer(self, normalizer_id: str) -> None:
        """Check existence of a normalizer, and insert a database entry if it concerns a local normalizer"""

        try:
            self.plugin_storage.normalizer_by_id(normalizer_id)
        except PluginNotFound:
            try:
                plugin = self.local_repo.by_id(normalizer_id)
            except KeyError:
                raise

            if plugin.type != "normalizer":
                raise
            self.plugin_storage.create_normalizer(plugin)

    def delete_settings(self, organisation_id: str, plugin_id: str):
        self.config_storage.delete(organisation_id, plugin_id)

        try:
            self._assert_settings_match_schema({}, organisation_id, plugin_id)
        except SettingsNotConformingToSchema:
            logger.warning("Making sure %s is disabled for %s because settings are deleted", plugin_id, organisation_id)

            self.set_enabled_by_id(plugin_id, organisation_id, False)

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

    def set_enabled_by_id(self, plugin_id: str, organisation_id: str, enabled: bool):
        if enabled:
            all_settings = self.get_all_settings(organisation_id, plugin_id)
            self._assert_settings_match_schema(all_settings, organisation_id, plugin_id)

        try:
            self._put_boefje(plugin_id)
        except PluginNotFound:
            self._put_normalizer(plugin_id)

        self.config_storage.upsert(organisation_id, plugin_id, enabled=enabled)

    def _assert_settings_match_schema(self, all_settings: dict, organisation_id: str, plugin_id: str):
        schema = self.schema(plugin_id)

        if schema:  # No schema means that there is nothing to assert
            try:
                validate(instance=all_settings, schema=schema)
            except ValidationError as e:
                raise SettingsNotConformingToSchema(organisation_id, plugin_id, e.message) from e

    def _set_plugin_enabled(self, plugin: PluginType, organisation_id: str) -> PluginType:
        with contextlib.suppress(KeyError, NotFound):
            plugin.enabled = self.config_storage.is_enabled_by_id(plugin.id, organisation_id)

        return plugin


def get_plugin_service(organisation_id: str) -> Iterator[PluginService]:
    def closure(session: Session):
        return PluginService(
            create_plugin_storage(session),
            create_config_storage(session),
            get_local_repository(),
        )

    yield from session_managed_iterator(closure)


def get_pagination_parameters(offset: int = 0, limit: int | None = None) -> PaginationParameters:
    return PaginationParameters(offset=offset, limit=limit)


def get_plugins_filter_parameters(
    q: str | None = None,
    ids: list[str] | None = Query(None),
    plugin_type: Literal["boefje", "normalizer", "bit"] | None = None,
    state: bool | None = None,
) -> FilterParameters:
    return FilterParameters(q=q, ids=ids, type=plugin_type, state=state)
