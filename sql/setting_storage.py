import logging
from typing import Dict, Optional

from sqlalchemy.orm import sessionmaker, Session

from config import Settings, settings
from katalogus.storage.interfaces import SettingsStorage, SettingNotFound
from sql.db import get_engine, ObjectNotFoundException
from sql.db_models import SettingInDB, OrganisationInDB
from sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLSettingsStorage(SessionMixin, SettingsStorage):
    def __init__(self, session: Session, app_settings: Settings):
        self.app_settings = app_settings

        super().__init__(session)

    def get_by_key(self, key: str, organisation_id: str) -> str:
        instance = self._db_instance_by_id(key, organisation_id)

        return instance.value

    def get_all(self, organisation_id: str) -> Dict[str, str]:
        query = (
            self.session.query(SettingInDB)
            .join(OrganisationInDB)
            .filter(SettingInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
        )
        return {setting.key: setting.value for setting in query.all()}

    def create(self, key: str, value: str, organisation_id: str) -> None:
        logger.info(
            "Saving setting: %s: %s for organisation %s", key, value, organisation_id
        )

        setting_in_db = self.to_setting_in_db(key, value, organisation_id)
        self.session.add(setting_in_db)

    def update_by_key(self, key: str, value: str, organisation_id: str) -> None:
        instance = self._db_instance_by_id(key, organisation_id)

        instance.value = value

    def delete_by_key(self, key: str, organisation_id: str) -> None:
        instance = self._db_instance_by_id(key, organisation_id)

        self.session.delete(instance)

    def _db_instance_by_id(self, key: str, organisation_id: str) -> SettingInDB:
        instance = (
            self.session.query(SettingInDB)
            .join(OrganisationInDB)
            .filter(SettingInDB.key == key)
            .filter(SettingInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        if instance is None:
            raise SettingNotFound(key, organisation_id) from ObjectNotFoundException(
                SettingInDB, key=key, organisation_id=organisation_id
            )

        return instance

    def to_setting_in_db(
        self, key: str, value: str, organisation_id: str
    ) -> SettingInDB:
        organisation = (
            self.session.query(OrganisationInDB)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        return SettingInDB(key=key, value=value, organisation_pk=organisation.pk)


def create_setting_storage(session: Session) -> SQLSettingsStorage:
    return SQLSettingsStorage(session, settings)
