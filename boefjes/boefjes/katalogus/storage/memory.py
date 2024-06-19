from boefjes.katalogus.models import Boefje, Normalizer, Organisation, PluginType
from boefjes.katalogus.storage.interfaces import (
    OrganisationStorage,
    PluginEnabledStorage,
    PluginStorage,
    SettingsStorage,
)

# key = organisation id; value = organisation
organisations: dict[str, Organisation] = {}

# key = organisation, repository/plugin id; value = enabled/ disabled
plugins_state: dict[str, dict[str, bool]] = {}


class OrganisationStorageMemory(OrganisationStorage):
    def __init__(self, defaults: dict[str, Organisation] | None = None):
        self._data = organisations if defaults is None else defaults

    def get_by_id(self, organisation_id: str) -> Organisation:
        return self._data[organisation_id]

    def get_all(self) -> dict[str, Organisation]:
        return self._data

    def create(self, organisation: Organisation) -> None:
        self._data[organisation.id] = organisation

    def delete_by_id(self, organisation_id: str) -> None:
        del self._data[organisation_id]


class PluginStorageMemory(PluginStorage):
    def __init__(self):
        self._boefjes = {}
        self._normalizers = {}

    def get_all(self) -> list[PluginType]:
        return list(self._boefjes.values()) + list(self._normalizers.values())

    def boefje_by_id(self, boefje_id: str) -> Boefje:
        return self._boefjes[boefje_id]

    def normalizer_by_id(self, normalizer_id: str) -> Normalizer:
        return self._normalizers[normalizer_id]

    def create_boefje(self, boefje: Boefje) -> None:
        self._boefjes[boefje.id] = boefje

    def create_normalizer(self, normalizer: Normalizer) -> None:
        self._normalizers[normalizer.id] = normalizer

    def delete_boefje_by_id(self, boefje_id: str) -> None:
        del self._boefjes[boefje_id]

    def delete_normalizer_by_id(self, normalizer_id: str) -> None:
        del self._normalizers[normalizer_id]


class SettingsStorageMemory(SettingsStorage):
    def __init__(self):
        self._data = {}

    def get_all(self, organisation_id: str, plugin_id: str) -> dict[str, str]:
        if organisation_id not in self._data:
            return {}

        return self._data[organisation_id].get(plugin_id, {})

    def upsert(self, values: dict, organisation_id: str, plugin_id: str) -> None:
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
        defaults: dict[str, bool] | None = None,
    ):
        self._data = plugins_state.setdefault(organisation, {}) if defaults is None else defaults
        self._organisation = organisation

    def get_by_id(self, plugin_id: str, organisation_id: str) -> bool:
        return self._data[f"{organisation_id}.{plugin_id}"]

    def get_all_enabled(self, organisation_id: str) -> list[str]:
        return [
            key.split(".", maxsplit=1)[1]
            for key, value in self._data.items()
            if value and key.split(".", maxsplit=1)[0] == organisation_id
        ]

    def create(self, plugin_id: str, enabled: bool, organisation_id: str) -> None:
        self._data[f"{organisation_id}.{plugin_id}"] = enabled

    def update_or_create_by_id(self, plugin_id: str, enabled: bool, organisation_id: str) -> None:
        self._data[f"{organisation_id}.{plugin_id}"] = enabled
