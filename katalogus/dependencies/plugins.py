import logging

from pathlib import Path
from typing import Dict, Iterable, List, Iterator

from sqlalchemy.orm import sessionmaker, Session

from config import settings
from katalogus.clients import PluginRepositoryClient, PluginRepositoryClientInterface
from katalogus.local_repository import LocalPluginRepository, get_local_repository
from katalogus.models import Repository, PluginType
from katalogus.storage.interfaces import (
    RepositoryStorage,
    PluginEnabledStorage,
    NotFound,
)
from katalogus.storage.memory import PluginStatesStorageMemory, RepositoryStorageMemory
from sql.db import get_engine, session_managed_iterator
from sql.plugin_enabled_storage import create_plugin_enabled_storage
from sql.repository_storage import create_repository_storage

logger = logging.getLogger(__name__)


class PluginService:
    def __init__(
        self,
        plugin_enabled_store: PluginEnabledStorage,
        repository_storage: RepositoryStorage,
        client: PluginRepositoryClientInterface,
        local_repo: LocalPluginRepository,
    ):
        self.plugin_client = client
        self.repository_storage = repository_storage
        self.plugin_enabled_store = plugin_enabled_store
        self.local_repo = local_repo

    def __enter__(self):
        self.repository_storage.__enter__()
        self.plugin_enabled_store.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.repository_storage.__exit__(exc_type, exc_val, exc_tb)
        self.plugin_enabled_store.__exit__(exc_type, exc_val, exc_tb)

    def get_all(self, organisation_id: str) -> List[PluginType]:
        all_plugins = self._plugins_for_repos(
            self.repository_storage.get_all().values(), organisation_id
        )

        flat = []

        for plugins in all_plugins.values():
            flat.extend(plugins.values())

        flat.extend(
            [
                self._set_plugin_enabled(plugin, organisation_id)
                for plugin in self.local_repo.get_all()
            ]
        )

        return flat

    def by_plugin_id(self, plugin_id: str, organisation_id: str) -> PluginType:
        all_plugins = self.get_all(organisation_id)

        for plugin in all_plugins:
            if plugin.id == plugin_id:
                return plugin

        raise KeyError(f"Plugin {plugin_id} not found with id {plugin_id}")

    # These two methods should return this static info from remote repositories as well in the future

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

    def repository_plugins(
        self, repository_id: str, organisation_id: str
    ) -> Dict[str, PluginType]:
        return self._plugins_for_repos(
            [self.repository_storage.get_by_id(repository_id)], organisation_id
        ).get(repository_id, {})

    def repository_plugin(
        self, repository_id: str, plugin_id: str, organisation_id: str
    ) -> PluginType:
        plugin = self.repository_plugins(repository_id, organisation_id).get(plugin_id)
        if plugin is None:
            raise KeyError(
                f"Plugin '{plugin_id}' not found in repository '{repository_id}'"
            )

        return plugin

    def update_by_id(
        self, repository_id: str, plugin_id: str, organisation_id: str, enabled: bool
    ):
        self.plugin_enabled_store.update_or_create_by_id(
            plugin_id,
            repository_id,
            enabled,
            organisation_id,
        )

    def _plugins_for_repos(
        self, repositories: Iterable[Repository], organisation_id: str
    ) -> Dict[str, Dict[str, PluginType]]:
        plugins = {}

        for repository in repositories:
            if repository.id == LocalPluginRepository.RESERVED_ID:
                continue

            try:
                plugins[repository.id] = {}

                for plugin_id, plugin in self.plugin_client.get_plugins(
                    repository
                ).items():
                    plugins[repository.id][plugin_id] = self._set_plugin_enabled(
                        plugin, organisation_id
                    )
            except:
                logger.exception(
                    "Getting plugins from repository with id %s failed", repository.id
                )

        return plugins

    def _set_plugin_enabled(
        self, plugin: PluginType, organisation_id: str
    ) -> PluginType:
        try:
            plugin.enabled = self.plugin_enabled_store.get_by_id(
                plugin.id, plugin.repository_id, organisation_id
            )
        except (KeyError, NotFound):
            pass

        return plugin

    @staticmethod
    def _namespaced_id(repository_id: str, plugin_id: str) -> str:
        return f"{repository_id}/{plugin_id}"


def get_plugin_service(organisation_id: str) -> Iterator[PluginService]:
    if not settings.enable_db:
        store = PluginStatesStorageMemory(organisation_id)
        repository_storage = RepositoryStorageMemory(organisation_id)
        client = PluginRepositoryClient()
        local_repo = get_local_repository()

        yield PluginService(store, repository_storage, client, local_repo)
        return

    def closure(session: Session):
        return PluginService(
            create_plugin_enabled_storage(session),
            create_repository_storage(session),
            PluginRepositoryClient(),
            get_local_repository(),
        )

    yield from session_managed_iterator(closure)
