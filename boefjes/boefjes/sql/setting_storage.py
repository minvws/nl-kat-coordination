import json
import logging

from sqlalchemy.orm import Session

from boefjes.config import settings
from boefjes.dependencies.encryption import EncryptMiddleware, IdentityMiddleware, NaclBoxMiddleware
from boefjes.models import EncryptionMiddleware
from boefjes.sql.db import ObjectNotFoundException
from boefjes.sql.db_models import BoefjeConfigInDB, BoefjeInDB, OrganisationInDB
from boefjes.sql.session import SessionMixin
from boefjes.storage.interfaces import SettingsNotFound, SettingsStorage, OrganisationNotFound, PluginNotFound

logger = logging.getLogger(__name__)


class SQLSettingsStorage(SessionMixin, SettingsStorage):
    def __init__(self, session: Session, encryption: EncryptMiddleware):
        self.encryption = encryption

        super().__init__(session)

    def upsert(self, values: dict, organisation_id: str, plugin_id: str) -> None:
        encrypted_values = self.encryption.encode(json.dumps(values))

        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
            instance.settings = encrypted_values
        except SettingsNotFound:
            organisation = self.session.query(OrganisationInDB).filter(OrganisationInDB.id == organisation_id).first()

            if not organisation:
                raise OrganisationNotFound(organisation_id)

            boefje = self.session.query(BoefjeInDB).filter(BoefjeInDB.plugin_id == plugin_id).first()

            if not boefje:
                raise PluginNotFound(plugin_id)

            setting_in_db = BoefjeConfigInDB(
                settings=encrypted_values,
                boefje_id=boefje.id,
                organisation_pk=organisation.pk,
            )
            self.session.add(setting_in_db)

    def get_all(self, organisation_id: str, plugin_id: str) -> dict:
        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
        except SettingsNotFound:
            return {}

        return json.loads(self.encryption.decode(instance.settings))

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        self.session.delete(instance)

    def _db_instance_by_id(self, organisation_id: str, plugin_id: str) -> BoefjeConfigInDB:
        instance = (
            self.session.query(BoefjeConfigInDB)
            .join(OrganisationInDB)
            .join(BoefjeInDB)
            .filter(BoefjeConfigInDB.organisation_pk == OrganisationInDB.pk)
            .filter(BoefjeConfigInDB.boefje_id == BoefjeInDB.id)
            .filter(BoefjeInDB.plugin_id == plugin_id)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        if instance is None:
            raise SettingsNotFound(organisation_id, plugin_id) from ObjectNotFoundException(
                BoefjeConfigInDB, organisation_id=organisation_id
            )

        return instance


def create_setting_storage(session) -> SettingsStorage:
    encrypter = create_encrypter()
    return SQLSettingsStorage(session, encrypter)


def create_encrypter():
    if settings.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        return NaclBoxMiddleware(settings.katalogus_private_key, settings.katalogus_public_key)

    return IdentityMiddleware()
