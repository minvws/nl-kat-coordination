import sys
from unittest import TestCase

from boefjes.config import settings
from boefjes.katalogus.clients import MockPluginRepositoryClient
from boefjes.katalogus.dependencies.plugins import PluginService
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.katalogus.models import Boefje, Normalizer, Bit, Repository
from boefjes.katalogus.storage.memory import (
    PluginStatesStorageMemory,
    RepositoryStorageMemory,
)


def get_plugin_seed():
    return {
        "test-repo": {
            "test-boefje-1": Boefje(
                id="test-boefje-1",
                name="Test Boefje 1",
                repository_id="test-repo",
                version="0.1",
                authors=None,
                created=None,
                description="Just a dummy boefje for demonstration purposes",
                environment_keys=None,
                related=None,
                type="boefje",
                scan_level=1,
                consumes={"WebPage"},
                options=None,
                produces=["text/html"],
            ),
            "test-boefje-2": Boefje(
                id="test-boefje-2",
                name="Test Boefje 2",
                repository_id="test-repo",
                version="0.1",
                authors=None,
                created=None,
                description="Just a dummy boefje for demonstration purposes",
                environment_keys=None,
                related=None,
                type="boefje",
                scan_level=1,
                consumes={"Hostname"},
                options=None,
                produces=["application/json"],
            ),
        },
        "test-repo-2": {
            "test-bit-1": Bit(
                id="test-bit-1",
                name="Test Bit 1",
                repository_id="test-repo-2",
                version="0.1",
                authors=None,
                created=None,
                description="Just a dummy bit for demonstration purposes",
                environment_keys=None,
                related=None,
                type="bit",
                consumes="WebPage",
                produces=["Finding"],
                parameters=["WebPage.address"],
                enabled=True,
            ),
            "test-normalizer-1": Normalizer(
                id="test-normalizer-1",
                name="Test Normalizer 1",
                repository_id="test-repo-2",
                version="0.1",
                authors=None,
                created=None,
                description="Just a dummy normalizer for demonstration purposes",
                environment_keys=None,
                related=None,
                type="normalizer",
                consumes=["text/html"],
                produces=["WebPage"],
                enabled=True,
            ),
        },
    }


def mock_plugin_service(organisation_id: str) -> PluginService:
    repo_store = RepositoryStorageMemory(organisation_id)
    _mocked_repositories = {
        "test-repo": Repository(
            id="test-repo", name="Test", base_url="http://localhost:8080"
        ),
        "test-repo-2": Repository(
            id="test-repo-2", name="Test2", base_url="http://localhost:8081"
        ),
    }
    for id_, repo in _mocked_repositories.items():
        repo_store.create(repo)

    test_boefjes_dir = settings.base_dir / "katalogus" / "tests" / "boefjes_test_dir"

    return PluginService(
        PluginStatesStorageMemory(organisation_id),
        repo_store,
        MockPluginRepositoryClient(get_plugin_seed()),
        LocalPluginRepository(test_boefjes_dir),
    )


class TestPluginsService(TestCase):
    def setUp(self) -> None:
        self.organisation = "test"
        self.service = mock_plugin_service(self.organisation)

    def test_get_plugins(self):
        plugins = self.service.get_all(self.organisation)

        self.assertEqual(len(plugins), 6)
        self.assertIn("test-boefje-1", [plugin.id for plugin in plugins])
        self.assertIn("test-repo", [plugin.repository_id for plugin in plugins])
        self.assertIn("Test Normalizer 1", [plugin.name for plugin in plugins])

        kat_test = list(filter(lambda x: x.id == "kat_test", plugins)).pop()
        self.assertEqual("kat_test", kat_test.id)
        self.assertEqual("Kat test name", kat_test.name)
        self.assertEqual({"DNSZone"}, kat_test.consumes)
        self.assertSetEqual({"Hostname", "Certificate"}, set(kat_test.produces))

        kat_test_norm = list(
            filter(lambda x: x.id == "kat_test_normalize", plugins)
        ).pop()
        self.assertIn("kat_test_normalize", kat_test_norm.id)
        self.assertEqual("kat_test_normalize", kat_test_norm.name)
        self.assertListEqual(["text/html"], kat_test_norm.consumes)
        self.assertListEqual([], kat_test_norm.produces)

    def test_get_repository_plugins(self):
        plugins = self.service.repository_plugins("test-repo-2", self.organisation)

        self.assertEqual(len(plugins), 2)
        self.assertIn("test-normalizer-1", plugins)
        self.assertIn("Normalizer 1", plugins["test-normalizer-1"].name)

    def test_get_repository_plugin(self):
        plugin = self.service.repository_plugin(
            "test-repo-2", "test-normalizer-1", self.organisation
        )

        self.assertIn("Normalizer 1", plugin.name)
        self.assertEqual(plugin.id, "test-normalizer-1")
        self.assertTrue(plugin.enabled)

    def test_update_by_id(self):
        self.service.update_by_id(
            "test-repo-2", "test-normalizer-1", self.organisation, False
        )
        plugin = self.service.repository_plugin(
            "test-repo-2", "test-normalizer-1", self.organisation
        )
        self.assertIn("Normalizer 1", plugin.name)
        self.assertFalse(plugin.enabled)
