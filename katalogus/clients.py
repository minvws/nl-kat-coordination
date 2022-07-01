from typing import Optional, Dict

from pydantic.tools import parse_obj_as
from requests import Session

from katalogus.models import PluginType, Repository
from plugin_repository.models import PluginType


class PluginRepositoryClientInterface:
    def get_plugins(
        self, repository: Repository, plugin_type: Optional[PluginType] = None
    ) -> Dict[str, PluginType]:
        raise NotImplementedError

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        raise NotImplementedError


class MockPluginRepositoryClient(PluginRepositoryClientInterface):
    def __init__(self, plugin_types: Dict[str, Dict[str, PluginType]]):
        self.plugin_types = plugin_types

    def get_plugins(
        self, repository: Repository, plugin_type: Optional[PluginType] = None
    ) -> Dict[str, PluginType]:
        return self.plugin_types[repository.id]

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        return self.plugin_types[repository.id][plugin_id]


class PluginRepositoryClient(PluginRepositoryClientInterface):
    def __init__(self):
        self._session = Session()

    def get_plugins(
        self, repository: Repository, plugin_type: Optional[PluginType] = None
    ) -> Dict[str, PluginType]:
        res = self._session.get(
            f"{repository.base_url}/plugins", params={"plugin_type": plugin_type}
        )
        res.raise_for_status()

        plugins = parse_obj_as(Dict[str, PluginType], res.json())

        for plugin in plugins.values():
            plugin.repository = repository.id

        return plugins

    def get_plugin(self, repository: Repository, plugin_id: str) -> PluginType:
        res = self._session.get(f"{repository.base_url}/plugins/{plugin_id}")
        res.raise_for_status()

        return parse_obj_as(PluginType, res.json())
