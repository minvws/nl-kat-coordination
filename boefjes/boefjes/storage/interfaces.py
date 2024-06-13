from abc import ABC

from boefjes.models import Boefje, Normalizer, Organisation, PluginType


class StorageError(Exception):
    """Generic exception for persistence"""

    def __init__(self, message: str):
        self.message = message


class SettingsNotConformingToSchema(StorageError):
    def __init__(self, organisation_id: str, plugin_id: str, validation_error: str):
        super().__init__(
            f"Settings for organisation {organisation_id} and plugin {plugin_id} are not conform the plugin schema: "
            f"{validation_error}"
        )


class NotFound(StorageError):
    """Generic exception for when objects are not found"""


class OrganisationNotFound(NotFound):
    def __init__(self, organisation_id: str):
        super().__init__(f"Organisation with id '{organisation_id}' not found")


class PluginNotFound(NotFound):
    def __init__(self, plugin_id: str):
        super().__init__(f"Plugin with id '{plugin_id}' not found")


class PluginStateNotFound(NotFound):
    def __init__(self, plugin_id: str, organisation_id: str):
        super().__init__(f"State for plugin with id '{plugin_id}' not found for organisation '{organisation_id}'")


class ConfigNotFound(NotFound):
    def __init__(self, organisation_id: str, plugin_id: str):
        super().__init__(f"Setting not found for organisation '{organisation_id}' and plugin '{plugin_id}'")


class NotAllowed(StorageError):
    """Generic exception for operations that are not allowed at a domain level"""


class CannotUpdateStaticPlugin(NotAllowed):
    def __init__(self, plugin_id: str):
        super().__init__(f"Plugin with id '{plugin_id}' is static, so updating it is not allowed")


class ExistingPluginId(NotAllowed):
    def __init__(self, plugin_id: str):
        super().__init__(f"Plugin id '{plugin_id}' is already used")


class OrganisationStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        pass

    def get_by_id(self, organisation_id: str) -> Organisation:
        raise NotImplementedError

    def get_all(self) -> dict[str, Organisation]:
        raise NotImplementedError

    def create(self, organisation: Organisation) -> None:
        raise NotImplementedError

    def delete_by_id(self, organisation_id: str) -> None:
        raise NotImplementedError


class PluginStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        pass

    def get_all(self) -> list[PluginType]:
        raise NotImplementedError

    def boefje_by_id(self, boefje_id: str) -> Boefje:
        raise NotImplementedError

    def normalizer_by_id(self, normalizer_id: str) -> Normalizer:
        raise NotImplementedError

    def create_boefje(self, boefje: Boefje) -> None:
        raise NotImplementedError

    def create_normalizer(self, normalizer: Normalizer) -> None:
        raise NotImplementedError

    def update_boefje(self, boefje_id: str, data: dict) -> None:
        raise NotImplementedError

    def update_normalizer(self, normalizer_id: str, data: dict) -> None:
        raise NotImplementedError

    def delete_boefje_by_id(self, boefje_id: str) -> None:
        raise NotImplementedError

    def delete_normalizer_by_id(self, normalizer_id: str) -> None:
        raise NotImplementedError


class ConfigStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        pass

    def get_all_settings(self, organisation_id: str, plugin_id: str) -> dict[str, str]:
        raise NotImplementedError

    def upsert(
        self, organisation_id: str, plugin_id: str, settings: dict | None = None, enabled: bool | None = None
    ) -> None:
        raise NotImplementedError

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        raise NotImplementedError

    def is_enabled_by_id(self, plugin_id: str, organisation_id: str) -> bool:
        raise NotImplementedError

    def get_enabled_boefjes(self, organisation_id: str) -> list[str]:
        raise NotImplementedError
