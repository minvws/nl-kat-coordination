from typing import Dict, List, Optional

from boefjes.katalogus.models import RESERVED_LOCAL_ID, Organisation, Repository
from boefjes.katalogus.storage.interfaces import (
    OrganisationStorage,
    PluginEnabledStorage,
    RepositoryStorage,
    SettingsStorage,
)

# key = organisation id; value = organisation
organisations: Dict[str, Organisation] = {}

# key = organisation, repository/plugin id; value = enabled/ disabled
plugins_state: Dict[str, Dict[str, bool]] = {}

# key = organisation id, repository id; value = repository
repositories: Dict[str, Dict[str, Repository]] = {}


class OrganisationStorageMemory(OrganisationStorage):
    def __init__(self, defaults: Optional[Dict[str, Organisation]] = None):
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
        defaults: Optional[Dict[str, Repository]] = None,
    ):
        self._data = repositories.setdefault(organisation_id, {}) if defaults is None else defaults
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
    def __init__(self):
        self._data = {}

    def get_all(self, organisation_id: str, plugin_id: str) -> Dict[str, str]:
        if organisation_id not in self._data:
            return {}

        return self._data[organisation_id].get(plugin_id, {})

    def upsert(self, values: Dict, organisation_id: str, plugin_id: str) -> None:
        if organisation_id not in self._data:
            self._data[organisation_id] = {}

        if plugin_id not in self._data[organisation_id]:
            self._data[organisation_id][plugin_id] = {}

        self._data[organisation_id][plugin_id] = values

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        del self._data[organisation_id][plugin_id]


class PluginStatesStorageMemory(PluginEnabledStorage):
    def __init__(
        self,
        organisation: str,
        defaults: Optional[Dict[str, bool]] = None,
    ):
        self._data = plugins_state.setdefault(organisation, {}) if defaults is None else defaults
        self._organisation = organisation

    def get_by_id(self, plugin_id: str, repository_id: str, organisation_id: str) -> bool:
        return self._data[f"{organisation_id}.{plugin_id}"]

    def get_all_enabled(self, organisation_id: str) -> Dict[str, List[str]]:
        return {
            RESERVED_LOCAL_ID: [
                key.split(".", maxsplit=1)[1]
                for key, value in self._data.items()
                if value and key.split(".", maxsplit=1)[0] == organisation_id
            ]
        }

    def create(self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str) -> None:
        self._data[f"{organisation_id}.{plugin_id}"] = enabled

    def update_or_create_by_id(self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str) -> None:
        self._data[f"{organisation_id}.{plugin_id}"] = enabled
