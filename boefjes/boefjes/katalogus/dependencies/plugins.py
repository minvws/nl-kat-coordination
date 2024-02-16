import contextlib
import logging
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Literal, Optional

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from sqlalchemy.orm import Session

from boefjes.katalogus.clients import (
    PluginRepositoryClient,
    PluginRepositoryClientInterface,
)
from boefjes.katalogus.local_repository import (
    LocalPluginRepository,
    get_local_repository,
)
from boefjes.katalogus.models import RESERVED_LOCAL_ID, PluginType, Repository
from boefjes.katalogus.storage.interfaces import (
    NotFound,
    PluginEnabledStorage,
    RepositoryStorage,
    SettingsNotConformingToSchema,
    SettingsStorage,
)
from boefjes.katalogus.types import LIMIT, FilterParameters, PaginationParameters
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.plugin_enabled_storage import create_plugin_enabled_storage
from boefjes.sql.repository_storage import create_repository_storage
from boefjes.sql.setting_storage import create_setting_storage

logger = logging.getLogger(__name__)


class PluginService:
    def __init__(
        self,
        plugin_enabled_store: PluginEnabledStorage,
        repository_storage: RepositoryStorage,
        settings_storage: SettingsStorage,
        client: PluginRepositoryClientInterface,
        local_repo: LocalPluginRepository,
    ):
        self.plugin_enabled_store = plugin_enabled_store
        self.repository_storage = repository_storage
        self.settings_storage = settings_storage
        self.plugin_client = client
        self.local_repo = local_repo

    def __enter__(self):
        self.repository_storage.__enter__()
        self.plugin_enabled_store.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.repository_storage.__exit__(exc_type, exc_val, exc_tb)
        self.plugin_enabled_store.__exit__(exc_type, exc_val, exc_tb)

    def get_all(self, organisation_id: str) -> List[PluginType]:
        all_plugins = self._plugins_for_repos(self.repository_storage.get_all().values(), organisation_id)

        flat: List[PluginType] = []

        for plugins in all_plugins.values():
            flat.extend(plugins.values())

        flat.extend([self._set_plugin_enabled(plugin, organisation_id) for plugin in self.local_repo.get_all()])

        return flat

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
        for repository_id, plugins in self.plugin_enabled_store.get_all_enabled(to_organisation).items():
            for plugin_id in plugins:
                self.update_by_id(repository_id, plugin_id, to_organisation, enabled=False)

        for plugin in self.get_all(from_organisation):
            if all_settings := self.get_all_settings(from_organisation, plugin.id):
                self.upsert_settings(all_settings, to_organisation, plugin.id)

        for repository_id, plugins in self.plugin_enabled_store.get_all_enabled(from_organisation).items():
            for plugin_id in plugins:
                self.update_by_id(repository_id, plugin_id, to_organisation, enabled=True)

    def upsert_settings(self, values: Dict, organisation_id: str, plugin_id: str):
        self._assert_settings_match_schema(values, organisation_id, plugin_id)

        return self.settings_storage.upsert(values, organisation_id, plugin_id)

    def delete_settings(self, organisation_id: str, plugin_id: str):
        self.settings_storage.delete(organisation_id, plugin_id)

        try:
            self._assert_settings_match_schema({}, organisation_id, plugin_id)
        except SettingsNotConformingToSchema:
            logger.warning("Making sure %s is disabled for %s because settings are deleted", plugin_id, organisation_id)

            plugin = self.by_plugin_id(plugin_id, organisation_id)
            self.update_by_id(plugin.repository_id, plugin_id, organisation_id, False)

    # These three methods should return this static info from remote repositories as well in the future

    def schema(self, plugin_id: str) -> Optional[Dict]:
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

    def repository_plugins(self, repository_id: str, organisation_id: str) -> Dict[str, PluginType]:
        return self._plugins_for_repos([self.repository_storage.get_by_id(repository_id)], organisation_id).get(
            repository_id, {}
        )

    def repository_plugin(self, repository_id: str, plugin_id: str, organisation_id: str) -> PluginType:
        plugin = self.repository_plugins(repository_id, organisation_id).get(plugin_id)
        if plugin is None:
            raise KeyError(f"Plugin '{plugin_id}' not found in repository '{repository_id}'")

        return plugin

    def update_by_id(self, repository_id: str, plugin_id: str, organisation_id: str, enabled: bool):
        if enabled:
            all_settings = self.settings_storage.get_all(organisation_id, plugin_id)
            self._assert_settings_match_schema(all_settings, organisation_id, plugin_id)

        self.plugin_enabled_store.update_or_create_by_id(
            plugin_id,
            repository_id,
            enabled,
            organisation_id,
        )

    def _plugins_for_repos(
        self, repositories: Iterable[Repository], organisation_id: str
    ) -> Dict[str, Dict[str, PluginType]]:
        plugins: Dict[str, Dict[str, PluginType]] = {}

        for repository in repositories:
            if repository.id == RESERVED_LOCAL_ID:
                continue

            try:
                plugins[repository.id] = {}

                for plugin_id, plugin in self.plugin_client.get_plugins(repository).items():
                    plugins[repository.id][plugin_id] = self._set_plugin_enabled(plugin, organisation_id)
            except:  # noqa
                logger.exception("Getting plugins from repository with id %s failed", repository.id)

        return plugins

    def _assert_settings_match_schema(self, all_settings: Dict, organisation_id: str, plugin_id: str):
        schema = self.schema(plugin_id)

        if schema:  # No schema means that there is nothing to assert
            try:
                validate(instance=all_settings, schema=schema)
            except ValidationError as e:
                raise SettingsNotConformingToSchema(organisation_id, plugin_id, e.message) from e

    def _set_plugin_enabled(self, plugin: PluginType, organisation_id: str) -> PluginType:
        with contextlib.suppress(KeyError, NotFound):
            plugin.enabled = self.plugin_enabled_store.get_by_id(plugin.id, plugin.repository_id, organisation_id)

        return plugin

    @staticmethod
    def _namespaced_id(repository_id: str, plugin_id: str) -> str:
        return f"{repository_id}/{plugin_id}"


def get_plugin_service(organisation_id: str) -> Iterator[PluginService]:
    def closure(session: Session):
        return PluginService(
            create_plugin_enabled_storage(session),
            create_repository_storage(session),
            create_setting_storage(session),
            PluginRepositoryClient(),
            get_local_repository(),
        )

    yield from session_managed_iterator(closure)


def get_pagination_parameters(offset: int = 0, limit: Optional[int] = LIMIT) -> PaginationParameters:
    return PaginationParameters(offset=offset, limit=limit)


def get_plugins_filter_parameters(
    q: Optional[str] = None,
    plugin_type: Optional[Literal["boefje", "normalizer", "bit"]] = None,
    state: Optional[bool] = None,
) -> FilterParameters:
    return FilterParameters(q=q, type=plugin_type, state=state)
