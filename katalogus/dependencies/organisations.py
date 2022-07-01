import logging
from typing import Iterator

from config import settings
from katalogus.organisations import default_organisations
from katalogus.storage.interfaces import OrganisationStorage
from katalogus.storage.memory import OrganisationStorageMemory
from sql.db import session_managed_iterator
from sql.organisation_storage import create_organisation_storage


logger = logging.getLogger(__name__)


def get_organisations_store() -> Iterator[OrganisationStorage]:
    if not settings.enable_db:
        yield OrganisationStorageMemory(default_organisations)
        return

    yield from session_managed_iterator(create_organisation_storage)
