import os

import alembic.config
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from boefjes.config import settings
from boefjes.models import Organisation
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage

pytestmark = pytest.mark.skipif(os.environ.get("CI") != "1", reason="Needs a CI database.")


@pytest.fixture
def migration_cd34fdfafdaf() -> Session:
    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])
    # To reset autoincrement ids
    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "base"])
    # Set state to revision cd34fdfafdaf
    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "cd34fdfafdaf"])

    engine = get_engine()
    session = sessionmaker(bind=engine)()

    with SQLOrganisationStorage(session, settings) as storage:
        storage.create(Organisation(id="dev1", name="Test 1 "))
        storage.create(Organisation(id="dev2", name="Test 2 "))

    entries = [(1, "LOCAL", "Repository Local", "https://local.com/")]
    query = text(
        "INSERT INTO repository (pk, id, name, base_url) "
        "VALUES (:pk, :id, :name, :base_url)"
        )
    for entry in entries:
        engine.execute(
            query,
            {
                "pk": entry[0],
                "id": entry[1],
                "name": entry[2],
                "base_url": entry[3]
            }
        )

    entries = [(1, "test_plugin_id", True, 1, 1)]  # New unique constraint fails
    query = text(
        "INSERT INTO plugin_state (id, plugin_id, enabled, organisation_pk, repository_pk) "
        "VALUES (:id, :plugin_id, :enabled, :organisation_pk, :repository_pk)"
    )
    for entry in entries:
        engine.execute(
            query,
            {
                "id": entry[0],
                "plugin_id": entry[1],
                "enabled": entry[2],
                "organisation_pk": entry[3],
                "repository_pk": entry[4]
            }
        )

    entries = [(1, 1)]
    query = text(
        "INSERT INTO organisation_repository (repository_pk, organisation_pk) "
        "VALUES (:repository_pk, :organisation_pk)"
    )
    for entry in entries:
        engine.execute(
            query,
            {
                "repository_pk": entry[0],
                "organisation_pk": entry[1]
            }
        )

    yield session
    session.commit()

    engine.execute(text("DELETE FROM plugin_state"))

    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

    engine.execute(";".join([f"TRUNCATE TABLE {t} CASCADE" for t in SQL_BASE.metadata.tables]))


def test_fail_on_non_unique(migration_cd34fdfafdaf):
    session = migration_cd34fdfafdaf

    entries = [(2, "test", "test", "https://test.co/")]  # Another non-local repository
    query = text(
        "INSERT INTO repository (pk, id, name, base_url) "
        "VALUES (:pk, :id, :name, :base_url)"
    )
    for entry in entries:
        session.get_bind().execute(
            query,
            {
                "pk": entry[0],
                "id": entry[1],
                "name": entry[2],
                "base_url": entry[3]
            }
        )
    entries = [(2, "test_plugin_id", True, 1, 2)]  # New unique constraint fails
    query = text(
        "INSERT INTO plugin_state (id, plugin_id, enabled, organisation_pk, repository_pk) "
        "VALUES (:id, :plugin_id, :enabled, :organisation_pk, :repository_pk)"
    )
    for entry in entries:
        session.get_bind().execute(
            query,
            {
                "id": entry[0],
                "plugin_id": entry[1],
                "enabled": entry[2],
                "organisation_pk": entry[3],
                "repository_pk": entry[4]
            }
        )

    with pytest.raises(Exception) as ctx:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "7c88b9cd96aa"])

    assert "remove plugin_states that refer to nonlocal repositories first" in str(ctx.value)

    # Fix unique constraint failures
    session.get_bind().execute(text("DELETE FROM plugin_state WHERE id = 2; DELETE FROM repository WHERE pk = 2"))

    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "7c88b9cd96aa"])

    all_plugin_states = [x[1:] for x in session.get_bind().execute(text("SELECT * FROM plugin_state")).fetchall()]
    assert all_plugin_states == [("test_plugin_id", True, 1)]


def test_downgrade(migration_cd34fdfafdaf):
    session = migration_cd34fdfafdaf
    session.get_bind().execute(text("DELETE FROM plugin_state WHERE id = 2"))  # Fix unique constraint fails

    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "7c88b9cd96aa"])
    alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "downgrade", "-1"])

    all_plugin_states = [x[1:] for x in session.get_bind().execute(text("SELECT * FROM plugin_state")).fetchall()]

    assert all_plugin_states == [("test_plugin_id", True, 1, 1)]
    assert session.get_bind().execute(text("SELECT * from repository")).fetchall() == [
        (1, "LOCAL", "Local Plugin Repository", "http://dev/null")
    ]
