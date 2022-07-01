from abc import ABC
from typing import Dict, Type

from katalogus.models import Organisation, Repository, Plugin


class StorageError(Exception):
    """Generic exception for persistence"""

    def __init__(self, message: str):
        self.message = message


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
            f"State for plugin with id '{plugin_id}' not found for organisation '{organisation_id}' and repostitory '{repository_id}'"
        )


class SettingNotFound(NotFound):
    def __init__(self, key: str, organisation_id: str):
        super().__init__(
            (f"Setting with key '{key}' not found for organisation '{organisation_id}'")
        )


class OrganisationStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc_value: str, exc_traceback: str
    ) -> None:
        pass

    def get_by_id(self, organisation_id: str) -> Organisation:
        raise NotImplementedError

    def get_all(self) -> Dict[str, Organisation]:
        raise NotImplementedError

    def create(self, organisation: Organisation) -> None:
        raise NotImplementedError

    def delete_by_id(self, organisation_id: str) -> None:
        raise NotImplementedError


class RepositoryStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc_value: str, exc_traceback: str
    ) -> None:
        pass

    def get_by_id(self, id_: str) -> Repository:
        raise NotImplementedError

    def get_all(self) -> Dict[str, Repository]:
        raise NotImplementedError

    def create(self, repository: Repository) -> None:
        raise NotImplementedError

    def delete_by_id(self, repository_id: str) -> None:
        raise NotImplementedError


class SettingsStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc_value: str, exc_traceback: str
    ) -> None:
        pass

    def get_by_key(self, key: str, organisation_id: str) -> str:
        raise NotImplementedError

    def get_all(self, organisation_id: str) -> Dict[str, str]:
        raise NotImplementedError

    def create(self, key: str, value: str, organisation_id: str) -> None:
        raise NotImplementedError

    def update_by_key(self, key: str, value: str, organisation_id: str) -> None:
        raise NotImplementedError

    def delete_by_key(self, key: str, organisation_id: str) -> None:
        raise NotImplementedError


class PluginEnabledStorage(ABC):
    def __enter__(self):
        return self

    def __exit__(
        self, exc_type: Type[Exception], exc_value: str, exc_traceback: str
    ) -> None:
        pass

    def get_by_id(
        self, plugin_id: str, repository_id: str, organisation_id: str
    ) -> bool:
        raise NotImplementedError

    def create(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        raise NotImplementedError

    def update_or_create_by_id(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        raise NotImplementedError
