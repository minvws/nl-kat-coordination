from datetime import UTC, datetime

import pytest
from django.conf import settings


@pytest.fixture
def valid_time():
    return datetime.now(UTC)


@pytest.fixture(scope='session')
def django_db_setup(request: pytest.FixtureRequest, django_db_blocker):
    """
    Make sure openkat-test-api and openkat_integration in .ci/docker-compose.yml use the same database:
    Since openkat_integration calls pytest, it creates a test database by default within ci_postgres, where the
    openkat-test-api will use the regular database. This will result in the API not knowing about plugins, users or
    Authtokens created during the test, but we need this since plugins created during the test have openkat-test-api
    as a callback service.
    """
    settings.DATABASES["default"]["TEST"] = {"MIRROR": True}
    yield
