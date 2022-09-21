from pathlib import Path
from typing import Dict, Union

from diskcache import Cache

from katalogus.models import Organisation, Repository
from katalogus.storage.interfaces import (
    OrganisationStorage,
    RepositoryStorage,
    SettingsStorage,
    PluginEnabledStorage,
)


# todo: improve duplicate code


class OrganisationStorageDisk(OrganisationStorage):
    def __init__(self, directory: Union[str, Path]):
        self._cache = Cache(Path(directory).as_posix())
        if "organisations" not in self._cache:
            self._cache["organisations"] = {}

        self._organisations = self._cache["organisations"]

    def get_by_id(self, organisation_id: str) -> Organisation:
        return self._organisations[organisation_id]

    def get_all(self) -> Dict[str, Organisation]:
        return self._organisations

    def create(self, organisation: Organisation) -> None:
        self._organisations[organisation.id] = organisation

    def delete_by_id(self, organisation_id: str) -> None:
        del self._organisations[organisation_id]


class RepositoryStorageDisk(RepositoryStorage):
    def __init__(self, directory: Union[str, Path]):
        self._cache = Cache(Path(directory).as_posix())
        if "repositories" not in self._cache:
            self._cache["repositories"] = {}

        self._repositories = self._cache["repositories"]

    def get_by_id(self, id_: str) -> Repository:
        return self._repositories[id_]

    def get_all(self) -> Dict[str, Repository]:
        return self._repositories

    def create(self, repository: Repository) -> None:
        self._repositories[repository.id] = repository

    def delete_by_id(self, id_: str) -> None:
        del self._repositories[id_]


class PluginStatesStorageDisk(PluginEnabledStorage):
    def __init__(self, directory: Union[str, Path]):
        self._cache = Cache(Path(directory).as_posix())
        if "plugins_states" not in self._cache:
            self._cache["plugins_states"] = {}

        self._plugins_states = self._cache["plugins_states"]

    def get_by_id(
        self, plugin_id: str, repository_id: str, organisation_id: str
    ) -> bool:
        return self._plugins_states[plugin_id]

    def create(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        self._plugins_states[plugin_id] = enabled

    def update_or_create_by_id(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        self._plugins_states[plugin_id] = enabled
