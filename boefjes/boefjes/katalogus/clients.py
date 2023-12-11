from typing import Dict, Optional

from pydantic import TypeAdapter
from requests import Session

from boefjes.katalogus.models import PluginType, Repository


class PluginRepositoryClientInterface:
    def get_plugins(self, repository: Repository, plugin_type: Optional[PluginType] = None) -> Dict[str, PluginType]:
        raise NotImplementedError

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        raise NotImplementedError


class MockPluginRepositoryClient(PluginRepositoryClientInterface):
    def __init__(self, plugin_types: Dict[str, Dict[str, PluginType]]):
        self.plugin_types = plugin_types

    def get_plugins(self, repository: Repository, plugin_type: Optional[PluginType] = None) -> Dict[str, PluginType]:
        return self.plugin_types[repository.id]

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        return self.plugin_types[repository.id][plugin_id]


class PluginRepositoryClient(PluginRepositoryClientInterface):
    def __init__(self):
        self._session = Session()

    def get_plugins(self, repository: Repository, plugin_type: Optional[PluginType] = None) -> Dict[str, PluginType]:
        res = self._session.get(f"{repository.base_url}/plugins", params={"plugin_type": plugin_type})
        res.raise_for_status()

        plugins = TypeAdapter(Dict[str, PluginType]).validate_json(res.content)

        for plugin in plugins.values():
            plugin.repository = repository.id

        return plugins

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        res = self._session.get(f"{repository.base_url}/plugins/{plugin_id}")
        res.raise_for_status()

        return PluginType.model_validate_json(res.content)
