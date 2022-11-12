import logging
from typing import Dict

from sqlalchemy.orm import Session

from boefjes.config import settings
from boefjes.katalogus.dependencies.context import get_context
from boefjes.katalogus.dependencies.encryption import (
    EncryptMiddleware,
    IdentityMiddleware,
    NaclBoxMiddleware,
)
from boefjes.katalogus.models import EncryptionMiddleware
from boefjes.katalogus.storage.interfaces import SettingsStorage, SettingNotFound
from boefjes.katalogus.storage.memory import SettingsStorageMemory
from boefjes.sql.db import ObjectNotFoundException
from boefjes.sql.db_models import SettingInDB, OrganisationInDB
from boefjes.sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLSettingsStorage(SessionMixin, SettingsStorage):
    def __init__(self, session: Session, encryption: EncryptMiddleware):
        self.encryption = encryption

        super().__init__(session)

    def get_by_key(self, key: str, organisation_id: str, plugin_id: str) -> str:
        instance = self._db_instance_by_id(key, organisation_id, plugin_id)

        return self.encryption.decode(instance.value)

    def get_all(self, organisation_id: str, plugin_id: str) -> Dict[str, str]:
        query = (
            self.session.query(SettingInDB)
            .join(OrganisationInDB)
            .filter(SettingInDB.organisation_pk == OrganisationInDB.pk)
            .filter(SettingInDB.plugin_id == plugin_id)
            .filter(OrganisationInDB.id == organisation_id)
        )
        return {
            setting.key: self.encryption.decode(setting.value)
            for setting in query.all()
        }

    def create(
        self, key: str, value: str, organisation_id: str, plugin_id: str
    ) -> None:
        logger.info(
            "Saving setting: %s: %s for organisation %s", key, value, organisation_id
        )

        setting_in_db = self.to_setting_in_db(
            key, self.encryption.encode(value), organisation_id, plugin_id
        )
        self.session.add(setting_in_db)

    def update_by_key(
        self, key: str, value: str, organisation_id: str, plugin_id: str
    ) -> None:
        instance = self._db_instance_by_id(key, organisation_id, plugin_id)

        instance.value = self.encryption.encode(value)

    def delete_by_key(self, key: str, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(key, organisation_id, plugin_id)

        self.session.delete(instance)

    def _db_instance_by_id(
        self, key: str, organisation_id: str, plugin_id: str
    ) -> SettingInDB:
        instance = (
            self.session.query(SettingInDB)
            .join(OrganisationInDB)
            .filter(SettingInDB.key == key)
            .filter(SettingInDB.plugin_id == plugin_id)
            .filter(SettingInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        if instance is None:
            raise SettingNotFound(
                key, organisation_id, plugin_id
            ) from ObjectNotFoundException(
                SettingInDB, key=key, organisation_id=organisation_id
            )

        return instance

    def to_setting_in_db(
        self, key: str, value: str, organisation_id: str, plugin_id: str
    ) -> SettingInDB:
        organisation = (
            self.session.query(OrganisationInDB)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        return SettingInDB(
            key=key, value=value, plugin_id=plugin_id, organisation_pk=organisation.pk
        )


def create_setting_storage(organisation_id: str, session) -> SettingsStorage:
    if not settings.enable_db:
        return SettingsStorageMemory(organisation_id)

    encrypter = IdentityMiddleware()
    if get_context().env.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        encrypter = NaclBoxMiddleware(
            get_context().env.katalogus_private_key_b64,
            get_context().env.katalogus_public_key_b64,
        )

    return SQLSettingsStorage(session, encrypter)
