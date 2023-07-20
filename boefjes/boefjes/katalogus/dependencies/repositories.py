import logging
from typing import Iterator

from boefjes.katalogus.storage.interfaces import RepositoryStorage
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.repository_storage import create_repository_storage

logger = logging.getLogger(__name__)


def get_repository_store(
    organisation_id: str,
) -> Iterator[RepositoryStorage]:
    yield from session_managed_iterator(create_repository_storage)
