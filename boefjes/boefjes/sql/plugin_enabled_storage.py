import logging

from sqlalchemy.orm import Session, sessionmaker

from boefjes.config import Settings, settings
from boefjes.katalogus.storage.interfaces import OrganisationNotFound, PluginEnabledStorage, PluginStateNotFound
from boefjes.sql.db import ObjectNotFoundException, get_engine
from boefjes.sql.db_models import OrganisationInDB, PluginStateInDB
from boefjes.sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLPluginEnabledStorage(SessionMixin, PluginEnabledStorage):
    def __init__(self, session: Session, app_settings: Settings):
        self.app_settings = app_settings

        super().__init__(session)

    def create(self, plugin_id: str, enabled: bool, organisation_id: str) -> None:
        logger.info(
            "Saving plugin state for plugin %s for organisation %s",
            plugin_id,
            organisation_id,
        )

        plugin_state_in_db = self.to_plugin_state_in_db(plugin_id, enabled, organisation_id)
        self.session.add(plugin_state_in_db)

    def get_by_id(self, plugin_id: str, organisation_id: str) -> bool:
        instance = self._db_instance_by_id(plugin_id, organisation_id)

        return instance.enabled

    def get_all_enabled(self, organisation_id: str) -> list[str]:
        query = (
            self.session.query(PluginStateInDB)
            .join(OrganisationInDB)
            .filter(PluginStateInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .filter(PluginStateInDB.enabled)
        )

        return [x.plugin_id for x in query.all()]

    def update_or_create_by_id(self, plugin_id: str, enabled: bool, organisation_id: str) -> None:
        try:
            instance = self._db_instance_by_id(plugin_id, organisation_id)
            instance.enabled = enabled
        except PluginStateNotFound:
            logger.info("Plugin state not found, creating new instance")
            self.create(plugin_id, enabled, organisation_id)

    def _db_instance_by_id(self, plugin_id: str, organisation_id: str) -> PluginStateInDB:
        instance = (
            self.session.query(PluginStateInDB)
            .join(OrganisationInDB)
            .filter(PluginStateInDB.organisation_pk == OrganisationInDB.pk)
            .filter(PluginStateInDB.plugin_id == plugin_id)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        if instance is None:
            raise PluginStateNotFound(plugin_id, organisation_id) from ObjectNotFoundException(
                PluginStateInDB,
                plugin_id=plugin_id,
                organisation_id=organisation_id,
            )

        return instance

    def to_plugin_state_in_db(self, plugin_id: str, enabled: bool, organisation_id: str) -> PluginStateInDB:
        organisation = self.session.query(OrganisationInDB).filter(OrganisationInDB.id == organisation_id).first()

        if organisation is None:
            raise OrganisationNotFound(organisation_id) from ObjectNotFoundException(
                OrganisationInDB, id=organisation_id
            )

        return PluginStateInDB(
            plugin_id=plugin_id,
            enabled=enabled,
            organisation_pk=organisation.pk,
        )


def create_plugin_enabled_storage(
    session: Session | None = None,
) -> SQLPluginEnabledStorage:
    if not session:
        session = sessionmaker(bind=get_engine())()

    return SQLPluginEnabledStorage(session, settings)
