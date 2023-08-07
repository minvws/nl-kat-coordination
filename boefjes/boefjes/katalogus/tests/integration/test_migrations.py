import os
from unittest import TestCase, skipIf

import alembic.config
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from boefjes.config import settings
from boefjes.katalogus.dependencies.encryption import NaclBoxMiddleware
from boefjes.katalogus.models import Organisation
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.setting_storage import SQLSettingsStorage, create_encrypter


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestRepositories(TestCase):
    def setUp(self) -> None:
        self.engine = get_engine()
        SQL_BASE.metadata.drop_all(self.engine)
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "197672984df0"])

    def test_setting_to_settings_json(self):
        session = sessionmaker(bind=self.engine)()

        with SQLOrganisationStorage(session, settings) as storage:
            storage.create(Organisation(id="dev1", name="Test 1 "))
            storage.create(Organisation(id="dev2", name="Test 2 "))
            storage.create(Organisation(id="dev3", name="Test 3 "))

        encrypter = create_encrypter()
        entries = self._collect_entries(encrypter)
        query = f"INSERT INTO setting (key, value, organisation_pk, plugin_id) values {','.join(map(str, entries))}"
        self.engine.execute(text(query))

        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        settings_storage = SQLSettingsStorage(session, encrypter)
        assert settings_storage.get_all("dev1", "test-plugin1") == {"key1": "val1", "key3": "val3"}
        assert settings_storage.get_all("dev1", "test-plugin2") == {"key5": "val5", "key7": "val7"}
        assert settings_storage.get_all("dev2", "test-plugin1") == {"key2": "val2"}
        assert settings_storage.get_all("dev3", "test-plugin1") == {}

        session.close()
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "-1"])

        results = [x[1:] for x in self.engine.execute(text("SELECT * FROM setting")).fetchall()]  # ignore pk's
        decoded_results = [(x[0], encrypter.decode(x[1]), x[2], x[3]) for x in results]  # compare decoded, since
        decoded_entries = [(x[0], encrypter.decode(x[1]), x[2], x[3]) for x in entries]  # encoding changes every time.

        assert set(decoded_entries) == set(decoded_results)

    def tearDown(self) -> None:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])
        SQL_BASE.metadata.drop_all(self.engine)

    @staticmethod
    def _collect_entries(encrypter: NaclBoxMiddleware):
        return [
            ("key1", encrypter.encode("val1"), 1, "test-plugin1"),
            ("key2", encrypter.encode("val2"), 2, "test-plugin1"),
            ("key3", encrypter.encode("val3"), 1, "test-plugin1"),
            ("key4", encrypter.encode("val4"), 2, "test-plugin2"),
            ("key5", encrypter.encode("val5"), 1, "test-plugin2"),
            ("key6", encrypter.encode("val6"), 2, "test-plugin2"),
            ("key7", encrypter.encode("val7"), 1, "test-plugin2"),
        ]
