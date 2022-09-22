import json
from unittest import TestCase

from fastapi.testclient import TestClient

from boefjes.katalogus.api import app
from boefjes.katalogus.dependencies.organisations import (
    get_organisations_store,
)
from boefjes.katalogus.models import Organisation
from boefjes.katalogus.storage.memory import OrganisationStorageMemory


class TestOrganisations(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

        self._store = OrganisationStorageMemory(
            {"test": Organisation(id="test", name="Test")}
        )

        app.dependency_overrides[get_organisations_store] = lambda: self._store

    def tearDown(self) -> None:
        app.dependency_overrides = {}

    def test_list(self):
        res = self.client.get("/v1/organisations")
        self.assertEqual(200, res.status_code)

    def test_get_organisation(self):
        res = self.client.get("/v1/organisations/test")
        self.assertEqual(200, res.status_code)

    def test_non_existing_organisation(self):
        res = self.client.get("/v1/organisations/future-organisation")
        self.assertEqual(404, res.status_code)
        self.assertIn("unknown organisation", res.text.lower())

    def test_add_organisation(self):
        res = self.client.post(
            "/v1/organisations/", data=json.dumps({"id": "new", "name": "New"})
        )
        self.assertEqual(201, res.status_code)

        res = self.client.get("/v1/organisations")
        self.assertEqual(200, res.status_code)
        self.assertEqual(2, len(res.json()))

    def test_delete_organisation(self):
        res = self.client.delete("/v1/organisations/test")
        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations")
        self.assertEqual(200, res.status_code)
        self.assertEqual(0, len(res.json()))
