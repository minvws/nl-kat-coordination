from abc import ABC

from boefjes.katalogus.models import Organisation, Repository


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


class RepositoryNotFound(NotFound):
    def __init__(self, repository_id: str):
        super().__init__(f"Repository with id '{repository_id}' not found")


class PluginNotFound(NotFound):
    def __init__(self, plugin_id: str, repository_id: str, organisation_id: str):
        super().__init__(
            f"State for plugin with id '{plugin_id}' not found for organisation '{organisation_id}' and repostitory "
            f"'{repository_id}'"
        )


class SettingsNotFound(NotFound):
    def __init__(self, organisation_id: str, plugin_id: str):
        super().__init__(f"Setting not found for organisation '{organisation_id}' and plugin '{plugin_id}'")


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


class RepositoryStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        pass

    def get_by_id(self, id_: str) -> Repository:
        raise NotImplementedError

    def get_all(self) -> dict[str, Repository]:
        raise NotImplementedError

    def create(self, repository: Repository) -> None:
        raise NotImplementedError

    def delete_by_id(self, repository_id: str) -> None:
        raise NotImplementedError


class SettingsStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        pass

    def get_all(self, organisation_id: str, plugin_id: str) -> dict[str, str]:
        raise NotImplementedError

    def upsert(self, values: dict, organisation_id: str, plugin_id: str) -> None:
        raise NotImplementedError

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        raise NotImplementedError


class PluginEnabledStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type[Exception], exc_value: str, exc_traceback: str) -> None:  # noqa: F841
        pass

    def get_by_id(self, plugin_id: str, repository_id: str, organisation_id: str) -> bool:
        raise NotImplementedError

    def get_all_enabled(self, organisation_id: str) -> dict[str, list[str]]:
        raise NotImplementedError

    def create(self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str) -> None:
        raise NotImplementedError

    def update_or_create_by_id(self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str) -> None:
        raise NotImplementedError
