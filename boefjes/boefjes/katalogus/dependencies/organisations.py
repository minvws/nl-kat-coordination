import logging
from typing import Iterator

from boefjes.config import settings
from boefjes.katalogus.organisations import default_organisations
from boefjes.katalogus.storage.interfaces import OrganisationStorage
from boefjes.katalogus.storage.memory import OrganisationStorageMemory
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.organisation_storage import create_organisation_storage


logger = logging.getLogger(__name__)


def get_organisations_store() -> Iterator[OrganisationStorage]:
    if not settings.enable_db:
        yield OrganisationStorageMemory(default_organisations)
        return

    yield from session_managed_iterator(create_organisation_storage)
