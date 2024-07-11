import os
from unittest import TestCase, skipIf

import alembic.config
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from boefjes.config import settings
from boefjes.models import Organisation
from boefjes.sql.config_storage import SQLConfigStorage, create_encrypter
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.plugin_storage import SQLPluginStorage


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestSettingsToBoefjeConfig(TestCase):
    def setUp(self) -> None:
        self.engine = get_engine()

        # To reset autoincrement ids
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "base"])
        # Set state to revision 6f99834a4a5a
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "6f99834a4a5a"])

        session = sessionmaker(bind=self.engine)()

        with SQLOrganisationStorage(session, settings) as storage:
            storage.create(Organisation(id="dev1", name="Test 1 "))
            storage.create(Organisation(id="dev2", name="Test 2 "))

        encrypter = create_encrypter()
        entries = [
            (1, encrypter.encode('{"key1": "val1"}'), "dns-records", 1),
            (2, encrypter.encode('{"key1": "val1", "key2": "val2"}'), "dns-records", 2),
            (3, encrypter.encode('{"key2": "val2", "key3": "val3"}'), "nmap", 1),
        ]
        query = f"INSERT INTO settings (id, values, plugin_id, organisation_pk) values {','.join(map(str, entries))}"  # noqa: S608
        self.engine.execute(text(query))

        entries = [(1, "dns-records", True, 1)]
        query = (
            f"INSERT INTO plugin_state (id, plugin_id, enabled, organisation_pk) values {','.join(map(str, entries))}"  # noqa: S608
        )
        self.engine.execute(text(query))

        session.close()

    def test_fail_on_wrong_plugin_ids(self):
        session = sessionmaker(bind=self.engine)()

        encrypter = create_encrypter()
        entries = [
            (4, encrypter.encode('{"key2": "val2", "key3": "val3"}'), "test-unknown-plugin-id", 1),
            (5, encrypter.encode('{"key1": "val1"}'), "kat_nmap_normalize", 2),
        ]
        query = f"INSERT INTO settings (id, values, plugin_id, organisation_pk) values {','.join(map(str, entries))}"  # noqa: S608
        self.engine.execute(text(query))

        with self.assertRaises(Exception) as ctx:
            alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "f9de6eb7824b"])

        assert "Settings for normalizer or bit found: kat_nmap_normalize" in str(ctx.exception)

        self.engine.execute(text("DELETE FROM settings WHERE id = 5"))  # Fix normalizer setting

        with self.assertRaises(Exception) as ctx:
            alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "f9de6eb7824b"])

        assert "Invalid plugin id found: test-unknown-plugin-id" in str(ctx.exception)

        self.engine.execute(text("DELETE FROM settings WHERE id = 4"))  # Fix unknown plugin

        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "f9de6eb7824b"])

        assert SQLPluginStorage(session, settings).boefje_by_id("dns-records").id == "dns-records"

        settings_storage = SQLConfigStorage(session, encrypter)
        assert settings_storage.get_all_settings("dev1", "dns-records") == {"key1": "val1"}
        assert settings_storage.get_all_settings("dev2", "dns-records") == {"key1": "val1", "key2": "val2"}

        session.close()

    def test_downgrade(self):
        # No need to also create a Boefje entry, the seeded settings and migrations take care of that and
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "f9de6eb7824b"])
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "-1"])

        encrypter = create_encrypter()
        all_settings = list(self.engine.execute(text("select * from settings")).fetchall())
        self.assertSetEqual(
            {(encrypter.decode(x[1]), x[2], x[3]) for x in all_settings},
            {
                ('{"key1": "val1"}', "dns-records", 1),
                ('{"key1": "val1", "key2": "val2"}', "dns-records", 2),
                ('{"key2": "val2", "key3": "val3"}', "nmap", 1),
            },
        )

    def tearDown(self) -> None:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables:
            session.execute(f"DELETE FROM {table} CASCADE")  # noqa: S608

        session.commit()
        session.close()
