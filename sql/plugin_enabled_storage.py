import logging
from typing import Optional

from sqlalchemy.orm import sessionmaker, Session

from config import Settings, settings
from katalogus.models import Plugin
from katalogus.storage.interfaces import PluginEnabledStorage, PluginNotFound
from sql.db import get_engine, ObjectNotFoundException
from sql.db_models import PluginStateInDB, OrganisationInDB, RepositoryInDB
from sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLPluginEnabledStorage(SessionMixin, PluginEnabledStorage):
    def __init__(self, session: Session, app_settings: Settings):
        self.app_settings = app_settings

        super().__init__(session)

    def create(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        logger.info(
            "Saving plugin state for plugin %s for organisation %s and repository %s",
            plugin_id,
            organisation_id,
            repository_id,
        )

        plugin_state_in_db = self.to_plugin_state_in_db(
            plugin_id, enabled, repository_id, organisation_id
        )
        self.session.add(plugin_state_in_db)

    def get_by_id(
        self, plugin_id: str, repository_id: str, organisation_id: str
    ) -> bool:
        instance = self._db_instance_by_id(plugin_id, repository_id, organisation_id)

        return instance.enabled

    def update_or_create_by_id(
        self, plugin_id: str, repository_id: str, enabled: bool, organisation_id: str
    ) -> None:
        try:
            instance = self._db_instance_by_id(
                plugin_id, repository_id, organisation_id
            )
            instance.enabled = enabled
        except PluginNotFound:
            logger.info("Plugin state not found, creating new instance")
            self.create(plugin_id, repository_id, enabled, organisation_id)

    def _db_instance_by_id(
        self, plugin_id: str, repository_id: str, organisation_id: str
    ) -> PluginStateInDB:
        instance = (
            self.session.query(PluginStateInDB)
            .join(OrganisationInDB, RepositoryInDB)
            .filter(PluginStateInDB.organisation_pk == OrganisationInDB.pk)
            .filter(PluginStateInDB.repository_pk == RepositoryInDB.pk)
            .filter(PluginStateInDB.plugin_id == plugin_id)
            .filter(OrganisationInDB.id == organisation_id)
            .filter(RepositoryInDB.id == repository_id)
            .first()
        )

        if instance is None:
            raise PluginNotFound(
                plugin_id, repository_id, organisation_id
            ) from ObjectNotFoundException(
                PluginStateInDB,
                plugin_id=plugin_id,
                organisation_id=organisation_id,
                repository_id=repository_id,
            )

        return instance

    def to_plugin_state_in_db(
        self, plugin_id: str, enabled: bool, repository_id: str, organisation_id: str
    ) -> PluginStateInDB:
        organisation = (
            self.session.query(OrganisationInDB)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )
        repository = (
            self.session.query(RepositoryInDB)
            .filter(RepositoryInDB.id == repository_id)
            .first()
        )

        return PluginStateInDB(
            plugin_id=plugin_id,
            enabled=enabled,
            organisation_pk=organisation.pk,
            repository_pk=repository.pk,
        )


def create_plugin_enabled_storage(
    session: Optional[Session] = None,
) -> SQLPluginEnabledStorage:
    if not session:
        session = sessionmaker(bind=get_engine())()

    return SQLPluginEnabledStorage(session, settings)
