import json
import logging
from typing import Dict

from sqlalchemy.orm import Session

from boefjes.katalogus.dependencies.context import get_context
from boefjes.katalogus.dependencies.encryption import EncryptMiddleware, IdentityMiddleware, NaclBoxMiddleware
from boefjes.katalogus.models import EncryptionMiddleware
from boefjes.katalogus.storage.interfaces import SettingsNotFound, SettingsStorage
from boefjes.sql.db import ObjectNotFoundException
from boefjes.sql.db_models import OrganisationInDB, SettingsInDB
from boefjes.sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLSettingsStorage(SessionMixin, SettingsStorage):
    def __init__(self, session: Session, encryption: EncryptMiddleware):
        self.encryption = encryption

        super().__init__(session)

    def upsert(self, values: Dict, organisation_id: str, plugin_id: str) -> None:
        encrypted_values = self.encryption.encode(json.dumps(values))

        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
            instance.values = encrypted_values
        except SettingsNotFound:
            organisation = self.session.query(OrganisationInDB).filter(OrganisationInDB.id == organisation_id).first()

            setting_in_db = SettingsInDB(
                values=encrypted_values,
                plugin_id=plugin_id,
                organisation_pk=organisation.pk,
            )
            self.session.add(setting_in_db)

    def get_all(self, organisation_id: str, plugin_id: str) -> Dict:
        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
        except SettingsNotFound:
            return {}

        return json.loads(self.encryption.decode(instance.values))

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        self.session.delete(instance)

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
