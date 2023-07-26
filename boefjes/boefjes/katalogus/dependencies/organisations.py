import logging
from typing import Iterator

from boefjes.katalogus.storage.interfaces import OrganisationStorage
from boefjes.sql.db import session_managed_iterator
from boefjes.sql.organisation_storage import create_organisation_storage

logger = logging.getLogger(__name__)


def get_organisations_store() -> Iterator[OrganisationStorage]:
    yield from session_managed_iterator(create_organisation_storage)
