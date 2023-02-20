import os
from unittest import TestCase, skipIf

import alembic.config

from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from boefjes.config import settings
from boefjes.katalogus.dependencies.encryption import IdentityMiddleware
from boefjes.katalogus.models import Organisation
from boefjes.sql.db import get_engine, SQL_BASE
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.setting_storage import SQLSettingsStorage


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestRepositories(TestCase):
    def test_setting_to_settings_json(self):
        engine = get_engine()
        SQL_BASE.metadata.drop_all(engine)

        alembicArgs = ["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "197672984df0"]
        alembic.config.main(argv=alembicArgs)

        session = sessionmaker(bind=engine)()

        organisation_storage = SQLOrganisationStorage(session, settings)

        with organisation_storage as storage:
            storage.create(Organisation(id="dev1", name="Test 1 "))
            storage.create(Organisation(id="dev2", name="Test 2 "))
            storage.create(Organisation(id="dev3", name="Test 3 "))

        with engine.connect() as connection:
            connection.execute(
                text(
                    "INSERT INTO setting (key, value, plugin_id, organisation_pk) values"
                    "('key1', 'val1', 'test-plugin1', 1),"
                    "('key2', 'val2', 'test-plugin1', 2),"
                    "('key3', 'val3', 'test-plugin1', 1),"
                    "('key4', 'val4', 'test-plugin2', 2),"
                    "('key5', 'val5', 'test-plugin2', 1),"
                    "('key6', 'val6', 'test-plugin2', 2),"
                    "('key7', 'val7', 'test-plugin2', 1)"
                )
            )

        alembicArgs = ["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"]
        alembic.config.main(argv=alembicArgs)

        settings_storage = SQLSettingsStorage(session, IdentityMiddleware())
        assert settings_storage.get_all("dev1", "test-plugin1") == {"key1": "val1", "key3": "val3"}
        assert settings_storage.get_all("dev1", "test-plugin2") == {"key5": "val5", "key7": "val7"}
        assert settings_storage.get_all("dev2", "test-plugin1") == {"key2": "val2"}
        assert settings_storage.get_all("dev3", "test-plugin1") == {}

        session.close()

        alembicArgs = ["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "-1"]
        alembic.config.main(argv=alembicArgs)

        with engine.connect() as connection:
            results = [x[1:] for x in connection.execute(text("SELECT * FROM setting")).fetchall()]

        assert len(results) == 7
        assert ("key5", "val5", 1, "test-plugin2") in results
        assert ("key7", "val7", 1, "test-plugin2") in results
        assert ("key1", "val1", 1, "test-plugin1") in results
        assert ("key3", "val3", 1, "test-plugin1") in results
        assert ("key4", "val4", 2, "test-plugin2") in results
        assert ("key6", "val6", 2, "test-plugin2") in results
        assert ("key2", "val2", 2, "test-plugin1") in results

        alembicArgs = ["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"]
        alembic.config.main(argv=alembicArgs)

        SQL_BASE.metadata.drop_all(engine)
