import json
import logging

from sqlalchemy.orm import Session

from boefjes.config import settings as config_settings
from boefjes.dependencies.encryption import EncryptMiddleware, IdentityMiddleware, NaclBoxMiddleware
from boefjes.models import EncryptionMiddleware
from boefjes.sql.db import ObjectNotFoundException
from boefjes.sql.db_models import BoefjeConfigInDB, BoefjeInDB, NormalizerConfigInDB, NormalizerInDB, OrganisationInDB
from boefjes.sql.session import SessionMixin
from boefjes.storage.interfaces import ConfigNotFound, ConfigStorage, OrganisationNotFound, PluginNotFound

logger = logging.getLogger(__name__)


class SQLConfigStorage(SessionMixin, ConfigStorage):
    def __init__(self, session: Session, encryption: EncryptMiddleware):
        self.encryption = encryption

        super().__init__(session)

    def upsert(
        self, organisation_id: str, plugin_id: str, settings: dict | None = None, enabled: bool | None = None
    ) -> None:
        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)

            if settings is not None:
                if isinstance(instance, NormalizerConfigInDB):
                    raise ValueError("Normalizer config does not have settings")

                instance.settings = self.encryption.encode(json.dumps(settings))
            if enabled is not None:
                instance.enabled = enabled
        except ConfigNotFound:
            organisation = self.session.query(OrganisationInDB).filter(OrganisationInDB.id == organisation_id).first()

            if not organisation:
                raise OrganisationNotFound(organisation_id)

            boefje = self.session.query(BoefjeInDB).filter(BoefjeInDB.plugin_id == plugin_id).first()

            if boefje:
                config = BoefjeConfigInDB(boefje_id=boefje.id, organisation_pk=organisation.pk)

                if settings is not None:
                    config.settings = self.encryption.encode(json.dumps(settings))

                if enabled is not None:
                    config.enabled = enabled

                self.session.add(config)
                return

            normalizer = self.session.query(NormalizerInDB).filter(NormalizerInDB.plugin_id == plugin_id).first()

            if not normalizer:
                raise PluginNotFound(plugin_id)

            normalizer_config = NormalizerConfigInDB(normalizer_id=normalizer.id, organisation_pk=organisation.pk)

            if enabled is not None:
                normalizer_config.enabled = enabled

            self.session.add(normalizer_config)

    def get_all_settings(self, organisation_id: str, plugin_id: str) -> dict:
        try:
            instance = self._db_instance_by_id(organisation_id, plugin_id)
        except ConfigNotFound:
            return {}

        if not instance.settings or instance.settings == "{}":  # Handle empty settings and the server default of "{}"
            return {}

        return json.loads(self.encryption.decode(instance.settings))

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        self.session.delete(instance)

    def is_enabled_by_id(self, plugin_id: str, organisation_id: str) -> bool:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        return instance.enabled

    def get_enabled_boefjes(self, organisation_id: str) -> list[str]:
        enabled_boefjes = (
            self.session.query(BoefjeInDB)
            .join(BoefjeConfigInDB)
            .filter(BoefjeConfigInDB.boefje_id == BoefjeInDB.id)
            .join(OrganisationInDB)
            .filter(BoefjeConfigInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .filter(BoefjeConfigInDB.enabled)
        )

        return [x.plugin_id for x in enabled_boefjes.all()]

    def _db_instance_by_id(self, organisation_id: str, plugin_id: str) -> BoefjeConfigInDB | NormalizerConfigInDB:
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
            instance = (
                self.session.query(NormalizerConfigInDB)
                .join(OrganisationInDB)
                .join(NormalizerInDB)
                .filter(NormalizerConfigInDB.organisation_pk == OrganisationInDB.pk)
                .filter(NormalizerConfigInDB.normalizer_id == NormalizerInDB.id)
                .filter(NormalizerInDB.plugin_id == plugin_id)
                .filter(OrganisationInDB.id == organisation_id)
                .first()
            )

            if instance is None:
                raise ConfigNotFound(organisation_id, plugin_id) from ObjectNotFoundException(
                    BoefjeConfigInDB | NormalizerConfigInDB, organisation_id=organisation_id
                )

        return instance


def create_config_storage(session) -> ConfigStorage:
    encrypter = create_encrypter()
    return SQLConfigStorage(session, encrypter)


def create_encrypter():
    if config_settings.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        return NaclBoxMiddleware(config_settings.katalogus_private_key, config_settings.katalogus_public_key)

    return IdentityMiddleware()
