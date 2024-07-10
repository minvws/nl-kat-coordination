import os
from unittest import TestCase, skipIf

import alembic.config
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from boefjes.config import settings
from boefjes.models import Organisation
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestRemoveRepositories(TestCase):
    def setUp(self) -> None:
        self.engine = get_engine()

        # To reset autoincrement ids
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "base"])
        # Set state to revision cd34fdfafdaf
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "cd34fdfafdaf"])

        session = sessionmaker(bind=self.engine)()

        with SQLOrganisationStorage(session, settings) as storage:
            storage.create(Organisation(id="dev1", name="Test 1 "))
            storage.create(Organisation(id="dev2", name="Test 2 "))

        entries = [(1, "LOCAL", "Repository Local", "https://local.com/")]
        query = f"INSERT INTO repository (pk, id, name, base_url) values {','.join(map(str, entries))}"  # noqa: S608
        self.engine.execute(text(query))

        entries = [(1, "test_plugin_id", True, 1, 1)]  # New unique constraint fails
        query = (
            f"INSERT INTO plugin_state (id, plugin_id, enabled, organisation_pk, repository_pk)"
            f"values {','.join(map(str, entries))}"
        )  # noqa: S608

        self.engine.execute(text(query))

        entries = [(1, 1)]
        query = (
            f"INSERT INTO organisation_repository (repository_pk, organisation_pk) values {','.join(map(str, entries))}"  # noqa: S608
        )
        self.engine.execute(text(query))
        session.close()

    def test_fail_on_non_unique(self):
        session = sessionmaker(bind=self.engine)()

        entries = [(2, "test", "test", "https://test.co/")]  # Another non-local repository
        query = f"INSERT INTO repository (pk, id, name, base_url) values {','.join(map(str, entries))}"  # noqa: S608
        self.engine.execute(text(query))

        entries = [(2, "test_plugin_id", True, 1, 2)]  # New unique constraint fails
        query = (
            f"INSERT INTO plugin_state (id, plugin_id, enabled, organisation_pk, repository_pk)"
            f"values {','.join(map(str, entries))}"
        )  # noqa: S608
        self.engine.execute(text(query))

        with self.assertRaises(Exception) as ctx:
            alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "7c88b9cd96aa"])

        assert "remove plugin_states that refer to nonlocal repositories first" in str(ctx.exception)

        self.engine.execute(text("DELETE FROM plugin_state WHERE id = 2"))  # Fix unique constraint fails
        self.engine.execute(text("DELETE FROM repository WHERE pk = 2"))  # Fix unique constraint fails

        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "7c88b9cd96aa"])

        all_plugin_states = [x[1:] for x in self.engine.execute(text("SELECT * FROM plugin_state")).fetchall()]
        assert all_plugin_states == [("test_plugin_id", True, 1)]

        session.close()

    def test_downgrade(self):
        session = sessionmaker(bind=self.engine)()

        self.engine.execute(text("DELETE FROM plugin_state WHERE id = 2"))  # Fix unique constraint fails
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "7c88b9cd96aa"])
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "-1"])

        all_plugin_states = [x[1:] for x in self.engine.execute(text("SELECT * FROM plugin_state")).fetchall()]
        assert all_plugin_states == [("test_plugin_id", True, 1, 1)]
        assert self.engine.execute(text("SELECT * from repository")).fetchall() == [
            (1, "LOCAL", "Local Plugin Repository", "http://dev/null")
        ]

        session.close()

    def tearDown(self) -> None:
        self.engine.execute(text("DELETE FROM plugin_state"))  # Fix unique constraint fails

        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables:
            session.execute(f"DELETE FROM {table} CASCADE")  # noqa: S608

        session.commit()
        session.close()
