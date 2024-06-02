from boefjes.models import Boefje, Normalizer, Organisation, PluginType
from boefjes.storage.interfaces import ConfigStorage, OrganisationStorage, PluginNotFound, PluginStorage

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
        if boefje_id not in self._boefjes:
            raise PluginNotFound(boefje_id)

        return self._boefjes[boefje_id]

    def normalizer_by_id(self, normalizer_id: str) -> Normalizer:
        if normalizer_id not in self._normalizers:
            raise PluginNotFound(normalizer_id)

        return self._normalizers[normalizer_id]

    def create_boefje(self, boefje: Boefje) -> None:
        self._boefjes[boefje.id] = boefje

    def create_normalizer(self, normalizer: Normalizer) -> None:
        self._normalizers[normalizer.id] = normalizer

    def update_boefje(self, boefje_id: str, data: dict) -> None:
        if not data:
            return

        if boefje_id not in self._boefjes:
            raise PluginNotFound(boefje_id)

        boefje = self._boefjes[boefje_id]

        for key, value in data.items():
            setattr(boefje, key, value)

    def update_normalizer(self, normalizer_id: str, data: dict) -> None:
        if not data:
            return

        if normalizer_id not in self._normalizers:
            raise PluginNotFound(normalizer_id)

        normalizer = self._normalizers[normalizer_id]

        for key, value in data.items():
            setattr(normalizer, key, value)

    def delete_boefje_by_id(self, boefje_id: str) -> None:
        del self._boefjes[boefje_id]

    def delete_normalizer_by_id(self, normalizer_id: str) -> None:
        del self._normalizers[normalizer_id]


class ConfigStorageMemory(ConfigStorage):
    def __init__(self):
        self._data = {}
        self._enabled = {}

    def get_all_settings(self, organisation_id: str, plugin_id: str) -> dict[str, str]:
        if organisation_id not in self._data:
            return {}

        return self._data[organisation_id].get(plugin_id, {})

    def upsert(
        self, organisation_id: str, plugin_id: str, settings: dict | None = None, enabled: bool | None = None
    ) -> None:
        if organisation_id not in self._data:
            self._data[organisation_id] = {}

        if organisation_id not in self._enabled:
            self._enabled[organisation_id] = {}

        if plugin_id not in self._data[organisation_id]:
            self._data[organisation_id][plugin_id] = {}

        if settings is not None:
            self._data[organisation_id][plugin_id] = settings

        if enabled is not None:
            self._enabled[organisation_id][plugin_id] = enabled

        return

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        del self._data[organisation_id][plugin_id]

    def is_enabled_by_id(self, plugin_id: str, organisation_id: str) -> bool:
        if organisation_id not in self._enabled or plugin_id not in self._enabled[organisation_id]:
            raise PluginNotFound(plugin_id)

        return self._enabled[organisation_id][plugin_id]

    def get_enabled_boefjes(self, organisation_id: str) -> list[str]:
        return [
            plugin_id
            for plugin_id, enabled in self._enabled.get(organisation_id, {}).items()
            if enabled and "norm" not in plugin_id
        ]
