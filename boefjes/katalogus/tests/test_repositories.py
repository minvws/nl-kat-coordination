import json
from unittest import TestCase
from fastapi.testclient import TestClient

from boefjes.katalogus.api import app
from boefjes.katalogus.models import Repository
from boefjes.katalogus.routers.organisations import check_organisation_exists
from boefjes.katalogus.storage.memory import RepositoryStorageMemory
from boefjes.katalogus.dependencies.repositories import get_repository_store


class TestRepositories(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

        _mocked_repositories = {
            "test": Repository(id="test", name="Test", base_url="http://localhost:8080")
        }

        def _mocked_get_repository_store(
            organisation_id: str,
        ):
            return RepositoryStorageMemory(organisation_id, _mocked_repositories)

        app.dependency_overrides[get_repository_store] = _mocked_get_repository_store
        app.dependency_overrides[check_organisation_exists] = lambda: None

    def tearDown(self) -> None:
        app.dependency_overrides = {}

    def test_list(self):
        res = self.client.get("/v1/organisations/test/repositories")
        self.assertEqual(200, res.status_code)

    def test_get_repository(self):
        res = self.client.get("/v1/organisations/test/repositories/test")
        self.assertEqual(200, res.status_code)

    def test_non_existing_repository(self):
        res = self.client.get("/v1/organisations/test/repositories/future-repository")
        self.assertEqual(404, res.status_code)
        self.assertIn("unknown repository", res.text.lower())

    def test_add_repository(self):
        res = self.client.post(
            "/v1/organisations/test/repositories/",
            data=json.dumps(
                {"id": "new", "name": "New", "base_url": "http://plugin-repo"}
            ),
        )
        self.assertEqual(201, res.status_code)

        res = self.client.get("/v1/organisations/test/repositories")
        self.assertEqual(200, res.status_code)
        self.assertEqual(2, len(res.json()))

    def test_delete_repository(self):
        res = self.client.delete("/v1/organisations/test/repositories/test")
        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/test/repositories")
        self.assertEqual(200, res.status_code)
        self.assertEqual(0, len(res.json()))
