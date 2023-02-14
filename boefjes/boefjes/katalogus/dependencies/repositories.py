import logging
from typing import Iterator

from boefjes.config import settings
from boefjes.katalogus.storage.interfaces import RepositoryStorage
from boefjes.katalogus.storage.memory import RepositoryStorageMemory
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.repository_storage import create_repository_storage


logger = logging.getLogger(__name__)


def get_repository_store(
    organisation_id: str,
) -> Iterator[RepositoryStorage]:
    if not settings.enable_db:
        yield RepositoryStorageMemory(organisation_id)
        return

    yield from session_managed_iterator(create_repository_storage)
