import json
import logging
from typing import Dict

from sqlalchemy.orm import Session

from boefjes.config import settings
from boefjes.katalogus.dependencies.context import get_context
from boefjes.katalogus.dependencies.encryption import EncryptMiddleware, IdentityMiddleware, NaclBoxMiddleware
from boefjes.katalogus.models import EncryptionMiddleware
from boefjes.katalogus.storage.interfaces import SettingsNotFound, SettingsStorage
from boefjes.katalogus.storage.memory import SettingsStorageMemory
from boefjes.sql.db import ObjectNotFoundException
from boefjes.sql.db_models import OrganisationInDB, SettingsInDB
from boefjes.sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLSettingsStorage(SessionMixin, SettingsStorage):
    def __init__(self, session: Session, encryption: EncryptMiddleware):
        self.encryption = encryption

        super().__init__(session)

    def get_by_key(self, key: str, organisation_id: str, plugin_id: str) -> str:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        if key not in instance.values:
            raise SettingsNotFound(organisation_id, plugin_id) from ObjectNotFoundException(
                SettingsInDB, organisation_id=organisation_id
            )

        return json.loads(self.encryption.decode(instance.values))[key]

    def get_all(self, organisation_id: str, plugin_id: str) -> Dict[str, str]:
        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
        except SettingsNotFound:
            return {}

        return {key: value for key, value in json.loads(self.encryption.decode(instance.values)).items()}

    def create(self, key: str, value, organisation_id: str, plugin_id: str) -> None:
        logger.info("Saving settings: %s for organisation %s", settings, organisation_id)

        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
            json_settings = json.dumps({**json.loads(self.encryption.decode(instance.values)), **{key: value}})
            instance.values = self.encryption.encode(json_settings)
        except SettingsNotFound:
            organisation = self.session.query(OrganisationInDB).filter(OrganisationInDB.id == organisation_id).first()
            all_settings = {key: value}

            setting_in_db = SettingsInDB(
                values=self.encryption.encode(json.dumps(all_settings)),
                plugin_id=plugin_id,
                organisation_pk=organisation.pk,
            )
            self.session.add(setting_in_db)

    def update_by_key(self, key: str, value, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        instance.values = self.encryption.encode(
            json.dumps({**json.loads(self.encryption.decode(instance.values)), **{key: value}})
        )

    def delete_by_key(self, key: str, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id, plugin_id)
        filtered_values = {
            instance_key: value
            for instance_key, value in json.loads(self.encryption.decode(instance.values)).items()
            if instance_key != key
        }

        instance.values = self.encryption.encode(json.dumps(filtered_values))

    def _db_instance_by_id(self, organisation_id: str, plugin_id: str) -> SettingsInDB:
        instance = (
            self.session.query(SettingsInDB)
            .join(OrganisationInDB)
            .filter(SettingsInDB.plugin_id == plugin_id)
            .filter(SettingsInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        if instance is None:
            raise SettingsNotFound(organisation_id, plugin_id) from ObjectNotFoundException(
                SettingsInDB, organisation_id=organisation_id
            )

        return instance


def create_setting_storage(session) -> SettingsStorage:
    if not settings.enable_db:
        return SettingsStorageMemory()

    encrypter = create_encrypter()

    return SQLSettingsStorage(session, encrypter)


def create_encrypter():
    encrypter = IdentityMiddleware()
    if get_context().env.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        encrypter = NaclBoxMiddleware(
            get_context().env.katalogus_private_key_b64,
            get_context().env.katalogus_public_key_b64,
        )

    return encrypter
