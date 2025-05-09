import json
import logging
from collections.abc import Iterator

from sqlalchemy.orm import Session

from boefjes.config import settings as config_settings
from boefjes.dependencies.encryption import EncryptMiddleware, IdentityMiddleware, NaclBoxMiddleware
from boefjes.models import BoefjeConfig, EncryptionMiddleware
from boefjes.sql.db import ObjectNotFoundException, session_managed_iterator
from boefjes.sql.db_models import BoefjeConfigInDB, BoefjeInDB, NormalizerConfigInDB, NormalizerInDB, OrganisationInDB
from boefjes.sql.session import SessionMixin
from boefjes.storage.interfaces import ConfigNotFound, ConfigStorage, OrganisationNotFound, PluginNotFound

logger = logging.getLogger(__name__)


class SQLConfigStorage(SessionMixin, ConfigStorage):
    def __init__(self, session: Session, encryption: EncryptMiddleware):
        self.encryption = encryption

        super().__init__(session)

    def list_boefje_configs(
        self,
        offset: int,
        limit: int,
        organisation_id: str | None = None,
        boefje_id: str | None = None,
        enabled: bool | None = None,
    ) -> list[BoefjeConfig]:
        query = self.session.query(BoefjeConfigInDB)

        if organisation_id is not None:
            query = (
                query.join(OrganisationInDB)
                .filter(BoefjeConfigInDB.organisation_pk == OrganisationInDB.pk)
                .filter(OrganisationInDB.id == organisation_id)
            )

        if boefje_id is not None:
            query = (
                query.join(BoefjeInDB)
                .filter(BoefjeConfigInDB.boefje_id == BoefjeInDB.id)
                .filter(BoefjeInDB.plugin_id == boefje_id)
            )

        if enabled is not None:
            query = query.filter(BoefjeConfigInDB.enabled == enabled)

        return [
            BoefjeConfig(
                id=x.id,
                settings=self._convert_settings(x),
                enabled=x.enabled,
                boefje_id=x.boefje.plugin_id,
                organisation_id=x.organisation.id,
            )
            for x in query.offset(offset).limit(limit).all()
        ]

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

        settings = self._convert_settings(instance)

        return settings

    def _convert_settings(self, instance):
        if not instance.settings or instance.settings == "{}":  # Handle empty settings and the server default of "{}"
            settings = {}
        else:
            settings = json.loads(self.encryption.decode(instance.settings))
        return settings

    def delete(self, organisation_id: str, plugin_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        self.session.delete(instance)

    def is_enabled_by_id(self, plugin_id: str, organisation_id: str) -> bool:
        instance = self._db_instance_by_id(organisation_id, plugin_id)

        return instance.enabled

    def get_enabled_boefjes(self, organisation_id: str) -> list[str]:
        enabled_boefjes = (
            self.session.query(BoefjeInDB.plugin_id)
            .join(BoefjeConfigInDB)
            .filter(BoefjeConfigInDB.boefje_id == BoefjeInDB.id)
            .join(OrganisationInDB)
            .filter(BoefjeConfigInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .filter(BoefjeConfigInDB.enabled)
        )
        return [x[0] for x in enabled_boefjes.all()]

    def get_enabled_normalizers(self, organisation_id: str) -> list[str]:
        enabled_normalizers = (
            self.session.query(NormalizerInDB.plugin_id)
            .join(NormalizerConfigInDB)
            .filter(NormalizerConfigInDB.normalizer_id == NormalizerInDB.id)
            .join(OrganisationInDB)
            .filter(NormalizerConfigInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
            .filter(NormalizerConfigInDB.enabled)
        )

        return [plugin[0] for plugin in enabled_normalizers.all()]

    def get_states_for_organisation(self, organisation_id: str) -> dict[str, bool]:
        enabled_boefjes = (
            self.session.query(BoefjeInDB.plugin_id, BoefjeConfigInDB.enabled)
            .join(BoefjeConfigInDB)
            .filter(BoefjeConfigInDB.boefje_id == BoefjeInDB.id)
            .join(OrganisationInDB)
            .filter(BoefjeConfigInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
        )
        enabled_normalizers = (
            self.session.query(NormalizerInDB.plugin_id, NormalizerConfigInDB.enabled)
            .join(NormalizerConfigInDB)
            .filter(NormalizerConfigInDB.normalizer_id == NormalizerInDB.id)
            .join(OrganisationInDB)
            .filter(NormalizerConfigInDB.organisation_pk == OrganisationInDB.pk)
            .filter(OrganisationInDB.id == organisation_id)
        )

        return {plugin[0]: plugin[1] for plugin in enabled_boefjes.union_all(enabled_normalizers).all()}

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

    @staticmethod
    def to_boefje_config(boefe_config_in_db: BoefjeConfigInDB) -> BoefjeConfig:
        return BoefjeConfig(
            id=boefe_config_in_db.id,
            settings=boefe_config_in_db.settings,
            enabled=boefe_config_in_db.enabled,
            boefje_id=boefe_config_in_db.boefje.id,
            organisation_id=boefe_config_in_db.organisation.id,
        )


def create_config_storage(session) -> ConfigStorage:
    encrypter = create_encrypter()
    return SQLConfigStorage(session, encrypter)


def get_config_storage() -> Iterator[ConfigStorage]:
    yield from session_managed_iterator(create_config_storage)


def create_encrypter():
    if config_settings.encryption_middleware == EncryptionMiddleware.NACL_SEALBOX:
        return NaclBoxMiddleware(config_settings.katalogus_private_key, config_settings.katalogus_public_key)

    return IdentityMiddleware()
