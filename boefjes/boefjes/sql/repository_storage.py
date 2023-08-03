import logging
from typing import Dict

from sqlalchemy.orm import Session

from boefjes.config import Settings
from boefjes.katalogus.models import Repository
from boefjes.katalogus.storage.interfaces import RepositoryNotFound, RepositoryStorage
from boefjes.sql.db import ObjectNotFoundException
from boefjes.sql.db_models import RepositoryInDB
from boefjes.sql.session import SessionMixin

settings = Settings()
logger = logging.getLogger(__name__)


class SQLRepositoryStorage(SessionMixin, RepositoryStorage):
    def __init__(self, session: Session, app_settings: Settings):
        self.app_settings = app_settings

        super().__init__(session)

    def get_by_id(self, repository_id: str) -> Repository:
        instance = self._db_instance_by_id(repository_id)

        return self.to_repository(instance)

    def get_all(self) -> Dict[str, Repository]:
        query = self.session.query(RepositoryInDB)

        return {repository.id: self.to_repository(repository) for repository in query.all()}

    def create(self, repository: Repository) -> None:
        logger.info("Saving repository: %s", repository.json())

        repository_in_db = self.to_repository_in_db(repository)
        self.session.add(repository_in_db)

    def delete_by_id(self, repository_id: str) -> None:
        logger.info("Deleting repository %s", repository_id)
        instance = self._db_instance_by_id(repository_id)

        self.session.delete(instance)

    def _db_instance_by_id(self, repository_id: str) -> RepositoryInDB:
        instance = self.session.query(RepositoryInDB).filter(RepositoryInDB.id == repository_id).first()

        if instance is None:
            raise RepositoryNotFound(repository_id) from ObjectNotFoundException(
                RepositoryInDB, repository_id=repository_id
            )

        return instance

    @staticmethod
    def to_repository_in_db(repository: Repository) -> RepositoryInDB:
        return RepositoryInDB(
            id=repository.id,
            name=repository.name,
            base_url=repository.base_url,
        )

    @staticmethod
    def to_repository(repository_in_db: RepositoryInDB) -> Repository:
        return Repository(
            id=repository_in_db.id,
            name=repository_in_db.name,
            base_url=repository_in_db.base_url,
        )


def create_repository_storage(session) -> SQLRepositoryStorage:
    return SQLRepositoryStorage(session, settings)
