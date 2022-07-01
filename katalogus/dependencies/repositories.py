import logging
from typing import Iterator

from config import settings
from katalogus.storage.interfaces import RepositoryStorage
from katalogus.storage.memory import RepositoryStorageMemory
from sql.db import session_managed_iterator
from sql.repository_storage import create_repository_storage


logger = logging.getLogger(__name__)


def get_repository_store(
    organisation_id: str,
) -> Iterator[RepositoryStorage]:
    if not settings.enable_db:
        yield RepositoryStorageMemory(organisation_id)
        return

    yield from session_managed_iterator(create_repository_storage)
