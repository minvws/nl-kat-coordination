import os
import time
from unittest import TestCase, skipIf

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from boefjes.config import Settings
from boefjes.katalogus.api import app
from boefjes.katalogus.dependencies.encryption import IdentityMiddleware
from boefjes.katalogus.models import Organisation, Repository
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.plugin_enabled_storage import SQLPluginEnabledStorage
from boefjes.sql.repository_storage import SQLRepositoryStorage
from boefjes.sql.setting_storage import SQLSettingsStorage

settings = Settings()


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestAPI(TestCase):
    def setUp(self) -> None:
        self.engine = get_engine()

        # Some retries to handle db startup time in tests
        for i in range(3):
            try:
                SQL_BASE.metadata.create_all(self.engine)
                break
            except OperationalError as e:
                if i == 2:
                    raise e

                time.sleep(1)

        session = sessionmaker(bind=self.engine)()
        self.organisation_storage = SQLOrganisationStorage(session, settings)
        self.repository_storage = SQLRepositoryStorage(session, settings)
        self.settings_storage = SQLSettingsStorage(session, IdentityMiddleware())
        self.plugin_state_storage = SQLPluginEnabledStorage(session, settings)

        with self.repository_storage as store:
            store.create(
                Repository(
                    id="LOCAL",
                    name="Test",
                    base_url="http://test.url",
                )
            )

        self.org = Organisation(id="test", name="Test Organisation")

        self.client = TestClient(app)
        response = self.client.post("/v1/organisations/", content=self.org.json())
        self.assertEqual(response.status_code, 201)

    def tearDown(self) -> None:
        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables:
            session.execute(f"DELETE FROM {table} CASCADE")

        session.commit()
        session.close()

    def test_plugin_api(self):
        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/dns-records")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual("dns-records", data["id"])
        self.assertEqual("LOCAL", data["repository_id"])

    def test_basic_settings_api(self):
        plug = "dns-records"

        self.client.put(f"/v1/organisations/{self.org.id}/{plug}/settings", json={"new": "settings", "with integer": 5})
        response = self.client.get(f"/v1/organisations/{self.org.id}/{plug}/settings")
        assert response.json() == {"new": "settings", "with integer": 5}

        self.client.put(f"/v1/organisations/{self.org.id}/{plug}/settings", json={"with integer": 8})
        response = self.client.get(f"/v1/organisations/{self.org.id}/{plug}/settings")
        assert response.json() == {"with integer": 8}

        self.client.delete(f"/v1/organisations/{self.org.id}/{plug}/settings")
        response = self.client.get(f"/v1/organisations/{self.org.id}/{plug}/settings")
        assert response.json() == {}

    def test_clone_settings(self):
        plug = "dns-records"

        # Set a setting on the first organisation and enable dns-records
        self.client.put(
            f"/v1/organisations/{self.org.id}/{plug}/settings",
            json={"test_key": "test value", "test_key_2": "test value 2"},
        )
        self.client.patch(f"/v1/organisations/{self.org.id}/repositories/LOCAL/plugins/{plug}", json={"enabled": True})

        assert self.client.get(f"/v1/organisations/{self.org.id}/{plug}/settings").json() == {
            "test_key": "test value",
            "test_key_2": "test value 2",
        }
        assert self.client.get(f"/v1/organisations/{self.org.id}/plugins/{plug}").json()["enabled"] is True

        # Add the second organisation
        new_org_id = "org2"
        org2 = Organisation(id=new_org_id, name="Second test Organisation")
        self.client.post("/v1/organisations/", content=org2.json())
        self.client.put(f"/v1/organisations/{new_org_id}/{plug}/settings", json={"test_key": "second value"})

        # Show that the second organisation has no settings and dns-records is not enabled
        assert self.client.get(f"/v1/organisations/{new_org_id}/{plug}/settings").json() == {"test_key": "second value"}
        assert self.client.get(f"/v1/organisations/{new_org_id}/plugins/{plug}").json()["enabled"] is False

        # Enable two boefjes that should get disabled by the cloning
        self.client.patch(f"/v1/organisations/{new_org_id}/repositories/LOCAL/plugins/nmap", json={"enabled": True})
        assert self.client.get(f"/v1/organisations/{new_org_id}/plugins/nmap").json()["enabled"] is True

        # Call the clone endpoint
        self.client.post(f"/v1/organisations/{self.org.id}/settings/clone/{new_org_id}")

        # Verify that all settings are copied
        response = self.client.get(f"/v1/organisations/{new_org_id}/{plug}/settings")
        assert response.json() == {"test_key": "test value", "test_key_2": "test value 2"}

        # And that the enabled boefje from the original organisation got enabled
        response = self.client.get(f"/v1/organisations/{new_org_id}/plugins/{plug}")
        assert response.json()["enabled"] is True

        # And the originally enabled boefje got disabled
        response = self.client.get(f"/v1/organisations/{new_org_id}/plugins/nmap")
        assert response.json()["enabled"] is False
