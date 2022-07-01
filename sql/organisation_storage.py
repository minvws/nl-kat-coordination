import logging
from typing import Dict, List

from sqlalchemy.orm import Session

from config import Settings, settings
from katalogus.models import Organisation, Repository
from katalogus.storage.interfaces import OrganisationStorage, OrganisationNotFound
from sql.db import ObjectNotFoundException
from sql.db_models import OrganisationInDB, RepositoryInDB
from sql.repository_storage import SQLRepositoryStorage
from sql.session import SessionMixin

logger = logging.getLogger(__name__)


class SQLOrganisationStorage(SessionMixin, OrganisationStorage):
    def __init__(self, session: Session, app_settings: Settings):
        self.app_settings = app_settings

        super().__init__(session)

    def get_by_id(self, organisation_id: str) -> Organisation:
        instance = self._db_instance_by_id(organisation_id)

        return self.to_organisation(instance)

    def get_all(self) -> Dict[str, Organisation]:
        query = self.session.query(OrganisationInDB)

        return {
            organisation.id: self.to_organisation(organisation)
            for organisation in query.all()
        }

    def create(self, organisation: Organisation) -> None:
        logger.info("Saving organisation: %s", organisation.json())

        organisation_in_db = self.to_organisation_in_db(organisation)
        self.session.add(organisation_in_db)

    def add_repository(self, organisation_id: str, repository_id: str) -> None:
        logger.info(
            "Adding repository to organisation: %s -> %s",
            organisation_id,
            repository_id,
        )

        organisation_in_db = self._db_instance_by_id(organisation_id)
        repo_in_db = self._db_repo_instance_by_id(repository_id)
        organisation_in_db.repositories.append(repo_in_db)

    def get_repositories(self, organisation_id: str) -> List[Repository]:
        instance = self._db_instance_by_id(organisation_id)

        return [
            SQLRepositoryStorage.to_repository(repo) for repo in instance.repositories
        ]

    def delete_by_id(self, organisation_id: str) -> None:
        instance = self._db_instance_by_id(organisation_id)

        self.session.delete(instance)

    def _db_instance_by_id(self, organisation_id: str) -> OrganisationInDB:
        instance = (
            self.session.query(OrganisationInDB)
            .filter(OrganisationInDB.id == organisation_id)
            .first()
        )

        if instance is None:
            raise OrganisationNotFound(organisation_id) from ObjectNotFoundException(
                OrganisationInDB, id=organisation_id
            )

        return instance

    def _db_repo_instance_by_id(self, repository_id: str) -> RepositoryInDB:
        instance = (
            self.session.query(RepositoryInDB)
            .filter(RepositoryInDB.id == repository_id)
            .first()
        )

        if instance is None:
            raise ObjectNotFoundException(RepositoryInDB, repository_id=repository_id)

        return instance

    @staticmethod
    def to_organisation_in_db(organisation: Organisation) -> OrganisationInDB:
        return OrganisationInDB(
            id=organisation.id,
            name=organisation.name,
        )

    @staticmethod
    def to_organisation(organisation_in_db: OrganisationInDB) -> Organisation:
        return Organisation(
            id=organisation_in_db.id,
            name=organisation_in_db.name,
        )


def create_organisation_storage(session) -> SQLOrganisationStorage:
    return SQLOrganisationStorage(session, settings)
