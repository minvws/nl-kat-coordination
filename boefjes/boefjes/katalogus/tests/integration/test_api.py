import os
from unittest import TestCase, skipIf

import alembic.config
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from boefjes.config import settings
from boefjes.katalogus.api.root import app
from boefjes.katalogus.dependencies.encryption import IdentityMiddleware
from boefjes.katalogus.models import Boefje, Normalizer, Organisation
from boefjes.sql.db import SQL_BASE, get_engine
from boefjes.sql.organisation_storage import SQLOrganisationStorage
from boefjes.sql.plugin_enabled_storage import SQLPluginEnabledStorage
from boefjes.sql.setting_storage import SQLSettingsStorage


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestAPI(TestCase):
    def setUp(self) -> None:
        alembic.config.main(argv=["--config", "/app/boefjes/boefjes/alembic.ini", "upgrade", "head"])

        session = sessionmaker(bind=get_engine())()
        self.organisation_storage = SQLOrganisationStorage(session, settings)
        self.settings_storage = SQLSettingsStorage(session, IdentityMiddleware())
        self.plugin_state_storage = SQLPluginEnabledStorage(session, settings)

        self.org = Organisation(id="test", name="Test Organisation")
        self.client = TestClient(app)
        response = self.client.post("/v1/organisations/", content=self.org.json())
        self.assertEqual(response.status_code, 201)

    def tearDown(self) -> None:
        session = sessionmaker(bind=get_engine())()

        for table in SQL_BASE.metadata.tables:
            session.execute(f"TRUNCATE {table} CASCADE")  # noqa: S608

        session.commit()
        session.close()

    def test_get_local_plugin(self):
        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/dns-records")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual("dns-records", data["id"])

    def test_filter_plugins(self):
        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/")
        self.assertEqual(len(response.json()), 93)
        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins?plugin_type=boefje")
        self.assertEqual(len(response.json()), 41)

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins?limit=10")
        self.assertEqual(len(response.json()), 10)

    def test_cannot_add_plugin_reserved_id(self):
        boefje = Boefje(id="dns-records", name="My test boefje", static=False)
        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=boefje.json())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"message": "Plugin id 'dns-records' is already used"})

        normalizer = Normalizer(id="kat_nmap_normalize", name="My test normalizer", static=False)
        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=normalizer.json())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"message": "Plugin id 'kat_nmap_normalize' is already used"})

    def test_add_boefje(self):
        boefje = Boefje(id="test_plugin", name="My test boefje", static=False)
        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=boefje.json())
        self.assertEqual(response.status_code, 201)

        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", json={"a": "b"})
        self.assertEqual(response.status_code, 422)

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/?plugin_type=boefje")
        self.assertEqual(len(response.json()), 42)

        boefje_dict = boefje.dict()
        boefje_dict["consumes"] = list(boefje_dict["consumes"])
        boefje_dict["produces"] = list(boefje_dict["produces"])

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/test_plugin")
        self.assertEqual(response.json(), boefje_dict)

    def test_delete_boefje(self):
        boefje = Boefje(id="test_plugin", name="My test boefje", static=False)
        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=boefje.json())
        self.assertEqual(response.status_code, 201)

        response = self.client.delete(f"/v1/organisations/{self.org.id}/boefjes/test_plugin")
        self.assertEqual(response.status_code, 204)
        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/test_plugin")
        self.assertEqual(response.status_code, 404)

    def test_add_normalizer(self):
        normalizer = Normalizer(id="test_normalizer", name="My test normalizer", static=False)
        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=normalizer.json())
        self.assertEqual(response.status_code, 201)

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/?plugin_type=normalizer")
        self.assertEqual(len(response.json()), 53)

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/test_normalizer")
        self.assertEqual(response.json(), normalizer.dict())

    def test_delete_normalizer(self):
        normalizer = Normalizer(id="test_normalizer", name="My test normalizer", static=False)
        response = self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=normalizer.json())
        self.assertEqual(response.status_code, 201)

        response = self.client.delete(f"/v1/organisations/{self.org.id}/normalizers/test_normalizer")
        self.assertEqual(response.status_code, 204)
        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/test_normalizer")
        self.assertEqual(response.status_code, 404)

    def test_update_plugins(self):
        normalizer = Normalizer(id="norm_id", name="My test normalizer", static=False)
        boefje = Boefje(id="test_plugin", name="My test boefje", description="123", static=False)

        self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=boefje.json())
        self.client.patch(f"/v1/organisations/{self.org.id}/boefjes/{boefje.id}", json={"description": "4"})
        self.client.patch(f"/v1/organisations/{self.org.id}/plugins/{boefje.id}", json={"enabled": True})

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/{boefje.id}")
        self.assertEqual(response.json()["description"], "4")
        self.assertTrue(response.json()["enabled"])

        r = self.client.patch(f"/v1/organisations/{self.org.id}/boefjes/dns-records", json={"id": "4", "version": "s"})
        self.assertEqual(r.status_code, 404)
        r = self.client.patch(f"/v1/organisations/{self.org.id}/boefjes/dns-records", json={"name": "Overwrite name"})
        self.assertEqual(r.status_code, 404)

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/dns-records")
        self.assertEqual(response.json()["name"], "DnsRecords")
        self.assertIsNone(response.json()["version"])
        self.assertEqual(response.json()["id"], "dns-records")

        self.client.post(f"/v1/organisations/{self.org.id}/plugins", content=normalizer.json())
        self.client.patch(f"/v1/organisations/{self.org.id}/normalizers/{normalizer.id}", json={"version": "v1.2"})

        response = self.client.get(f"/v1/organisations/{self.org.id}/plugins/{normalizer.id}")
        self.assertEqual(response.json()["version"], "v1.2")

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
        self.client.patch(f"/v1/organisations/{self.org.id}/plugins/{plug}", json={"enabled": True})

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
        self.client.patch(f"/v1/organisations/{new_org_id}/plugins/nmap", json={"enabled": True})
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
