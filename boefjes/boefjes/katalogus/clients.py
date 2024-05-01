import logging

from httpx import Client
from pydantic import TypeAdapter

from boefjes.katalogus.models import PluginType, Repository

logger = logging.getLogger(__name__)


class PluginRepositoryClientInterface:
    def get_plugins(
        self, repository: Repository, plugin_type: PluginType | None = None, plugin_ids: list[str] | None = None
    ) -> dict[str, PluginType]:
        raise NotImplementedError

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        raise NotImplementedError


class MockPluginRepositoryClient(PluginRepositoryClientInterface):
    def __init__(self, plugin_types: dict[str, dict[str, PluginType]]):
        self.plugin_types = plugin_types

    def get_plugins(self, repository: Repository, plugin_type: PluginType | None = None) -> dict[str, PluginType]:
        return self.plugin_types[repository.id]

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        return self.plugin_types[repository.id][plugin_id]


class PluginRepositoryClient(PluginRepositoryClientInterface):
    def __init__(self):
        self._client = Client()

    def get_plugins(
        self, repository: Repository, plugin_type: PluginType | None = None, plugin_ids: list[str] | None = None
    ) -> dict[str, PluginType]:
        res = self._client.get(
            f"{repository.base_url}/plugins", params={"plugin_type": plugin_type, "plugin_ids": plugin_ids}
        )
        logger.error(f"Res is {res.status_code}")
        res.raise_for_status()

        plugins = TypeAdapter(dict[str, PluginType]).validate_json(res.content)

        for plugin in plugins.values():
            plugin.repository = repository.id

        return plugins

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        res = self._client.get(f"{repository.base_url}/plugins/{plugin_id}")
        res.raise_for_status()

        return PluginType.model_validate_json(res.content)  # type: ignore
