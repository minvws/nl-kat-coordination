from typing import Dict

from boefjes.katalogus.models import Organisation, Repository
from boefjes.katalogus.storage.interfaces import (
    OrganisationStorage,
    RepositoryStorage,
    SettingsStorage,
    PluginEnabledStorage,
)

# key = organisation id; value = organisation
organisations: Dict[str, Organisation] = {}

# key = organisation, repository/plugin id; value = enabled/ disabled
plugins_state: Dict[str, Dict[str, bool]] = {}

# key = organisation id, repository id; value = repository
repositories: Dict[str, Dict[str, Repository]] = {}


class OrganisationStorageMemory(OrganisationStorage):
    def __init__(self, defaults: Dict[str, Organisation] = None):
        self._data = organisations if defaults is None else defaults

    def get_by_id(self, organisation_id: str) -> Organisation:
        return self._data[organisation_id]

    def get_all(self) -> Dict[str, Organisation]:
        return self._data

    def create(self, organisation: Organisation) -> None:
        self._data[organisation.id] = organisation

    def delete_by_id(self, organisation_id: str) -> None:
        del self._data[organisation_id]


class RepositoryStorageMemory(RepositoryStorage):
    def __init__(
        self,
        organisation_id: str,
        defaults: Dict[str, Repository] = None,
    ):
        self._data = (
            repositories.setdefault(organisation_id, {})
            if defaults is None
            else defaults
        )
        self._organisation_id = organisation_id

    def get_by_id(self, id_: str) -> Repository:
        return self._data[id_]

    def get_all(self) -> Dict[str, Repository]:
        return self._data

    def create(self, repository: Repository) -> None:
        self._data[repository.id] = repository

    def delete_by_id(self, id_: str) -> None:
        del self._data[id_]


class SettingsStorageMemory(SettingsStorage):
    def __init__(
        self,
        organisation: str,
        defaults: Dict[str, str] = None,
    ):
        defaults = defaults or {}
        self._data = {organisation: defaults}
        self._organisation = organisation

    def get_by_key(self, key: str, organisation_id: str, plugin_id: str) -> str:
        return self._data[organisation_id][f"{plugin_id}.{key}"]

    def get_all(self, organisation_id: str, plugin_id: str) -> Dict[str, str]:
        return {
            k.split(".", maxsplit=1)[1]: v
            for k, v in self._data[organisation_id].items()
            if plugin_id in k
        }

    def create(
        self, key: str, value: str, organisation_id: str, plugin_id: str
    ) -> None:
        self._data[organisation_id][f"{plugin_id}.{key}"] = value

    def update_by_key(
        self, key: str, value: str, organisation_id: str, plugin_id: str
    ) -> None:
        self._data[organisation_id][f"{plugin_id}.{key}"] = value

    def delete_by_key(self, key: str, organisation_id: str, plugin_id: str) -> None:
        del self._data[organisation_id][f"{plugin_id}.{key}"]


class PluginStatesStorageMemory(PluginEnabledStorage):
    def __init__(
        self,
        organisation: str,
        defaults: Dict[str, bool] = None,
    ):
        self._data = (
            plugins_state.setdefault(organisation, {}) if defaults is None else defaults
        )
        self._organisation = organisation

    def get_by_id(
        self, plugin_id: str, repository_id: str, organisation_id: str
    ) -> bool:
        return self._data[plugin_id]

    def create(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        self._data[plugin_id] = enabled

    def update_or_create_by_id(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        self._data[plugin_id] = enabled
