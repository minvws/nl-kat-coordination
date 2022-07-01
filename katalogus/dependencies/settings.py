import logging
from typing import Dict, Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from config import settings
from katalogus.dependencies.context import get_context
from katalogus.dependencies.encryption import (
    EncryptMiddleware,
    NaclBoxMiddleware,
    IdentityMiddleware,
)
from katalogus.models import EncryptionMiddleware
from katalogus.storage.interfaces import SettingsStorage
from katalogus.storage.memory import SettingsStorageMemory
from sql.db import session_managed_iterator
from sql.setting_storage import create_setting_storage

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, storage: SettingsStorage, encryption: EncryptMiddleware):
        self.encryption = encryption
        self.storage = storage

    def get_by_key(self, key: str, organisation_id: str) -> str:
        return self.encryption.decode(self.storage.get_by_key(key, organisation_id))

    def get_all(self, organisation_id: str) -> Dict[str, str]:
        return {
            k: self.encryption.decode(v)
            for k, v in self.storage.get_all(organisation_id).items()
        }

    def create(self, key: str, value: str, organisation_id: str) -> None:
        with self.storage as storage:
            return storage.create(key, self.encryption.encode(value), organisation_id)

    def update_by_id(self, key: str, value: str, organisation_id: str) -> None:
        with self.storage as storage:
            return storage.update_by_key(
                key, self.encryption.encode(value), organisation_id
            )

    def delete_by_id(self, key: str, organisation_id: str) -> None:
        with self.storage as storage:
            storage.delete_by_key(key, organisation_id)


def get_settings_service(
    organisation_id: str, context=Depends(get_context)
) -> Iterator[SettingsService]:
    encrypter = IdentityMiddleware()
    if context.env.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        encrypter = NaclBoxMiddleware(
            context.env.katalogus_private_key_b64, context.env.katalogus_public_key_b64
        )

    if not settings.enable_db:
        yield SettingsService(
            storage=SettingsStorageMemory(organisation_id), encryption=encrypter
        )
        return

    def closure(session: Session):
        return SettingsService(
            storage=create_setting_storage(session), encryption=encrypter
        )

    yield from session_managed_iterator(closure)
