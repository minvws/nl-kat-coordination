from unittest import TestCase

from boefjes.config import BASE_DIR
from boefjes.katalogus.clients import MockPluginRepositoryClient
from boefjes.katalogus.dependencies.plugins import PluginService
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.katalogus.models import RESERVED_LOCAL_ID, Bit, Boefje, Normalizer, Repository
from boefjes.katalogus.storage.interfaces import SettingsNotConformingToSchema
from boefjes.katalogus.storage.memory import (
    PluginStatesStorageMemory,
    RepositoryStorageMemory,
    SettingsStorageMemory,
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
                environment_keys=[],
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
                environment_keys=[],
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
                environment_keys=[],
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
                environment_keys=[],
                related=None,
                type="normalizer",
                consumes=["text/html"],
                produces=["WebPage"],
                enabled=True,
            ),
        },
    }


def mock_plugin_service(organisation_id: str) -> PluginService:
    storage = SettingsStorageMemory()
    storage.upsert({"DUMMY_VAR": "123"}, "test", "test_plugin")

    repo_store = RepositoryStorageMemory(organisation_id)
    _mocked_repositories = {
        "test-repo": Repository(id="test-repo", name="Test", base_url="http://localhost:8080"),
        "test-repo-2": Repository(id="test-repo-2", name="Test2", base_url="http://localhost:8081"),
    }
    for id_, repo in _mocked_repositories.items():
        repo_store.create(repo)

    test_boefjes_dir = BASE_DIR / "katalogus" / "tests" / "boefjes_test_dir"

    return PluginService(
        PluginStatesStorageMemory(organisation_id),
        repo_store,
        storage,
        MockPluginRepositoryClient(get_plugin_seed()),
        LocalPluginRepository(test_boefjes_dir),
    )


class TestPluginsService(TestCase):
    def setUp(self) -> None:
        self.organisation = "test"
        self.service = mock_plugin_service(self.organisation)

    def test_get_plugins(self):
        plugins = self.service.get_all(self.organisation)

        self.assertEqual(len(plugins), 8)
        self.assertIn("test-boefje-1", [plugin.id for plugin in plugins])
        self.assertIn("test-repo", [plugin.repository_id for plugin in plugins])
        self.assertIn("Test Normalizer 1", [plugin.name for plugin in plugins])

        kat_test = list(filter(lambda x: x.id == "kat_test", plugins)).pop()
        self.assertEqual("kat_test", kat_test.id)
        self.assertEqual("Kat test name", kat_test.name)
        self.assertEqual({"DNSZone"}, kat_test.consumes)
        self.assertSetEqual({"boefje/kat_test"}, set(kat_test.produces))

        kat_test_norm = list(filter(lambda x: x.id == "kat_test_normalize", plugins)).pop()
        self.assertIn("kat_test_normalize", kat_test_norm.id)
        self.assertListEqual(["text/html", "normalizer/kat_test_normalize"], kat_test_norm.consumes)
        self.assertListEqual([], kat_test_norm.produces)

    def test_get_repository_plugins(self):
        plugins = self.service.repository_plugins("test-repo-2", self.organisation)

        self.assertEqual(len(plugins), 2)
        self.assertIn("test-normalizer-1", plugins)
        self.assertIn("Normalizer 1", plugins["test-normalizer-1"].name)

    def test_get_repository_plugin(self):
        plugin = self.service.repository_plugin("test-repo-2", "test-normalizer-1", self.organisation)

        self.assertIn("Normalizer 1", plugin.name)
        self.assertEqual(plugin.id, "test-normalizer-1")
        self.assertTrue(plugin.enabled)

    def test_update_by_id(self):
        self.service.update_by_id("test-repo-2", "test-normalizer-1", self.organisation, False)
        plugin = self.service.repository_plugin("test-repo-2", "test-normalizer-1", self.organisation)
        self.assertIn("Normalizer 1", plugin.name)
        self.assertFalse(plugin.enabled)

    def test_update_by_id_bad_schema(self):
        plugin_id = "kat_test"

        with self.assertRaises(SettingsNotConformingToSchema) as ctx:
            self.service.update_by_id("LOCAL", plugin_id, self.organisation, True)

        msg = (
            "Settings for organisation test and plugin kat_test are not conform the plugin schema: 'api_key' is a "
            "required property"
        )
        self.assertEqual(ctx.exception.message, msg)

        self.service.settings_storage.upsert({"api_key": 128 * "a"}, self.organisation, plugin_id)
        self.service.update_by_id("test-repo-2", plugin_id, self.organisation, True)

        value = 129 * "a"
        self.service.settings_storage.upsert({"api_key": 129 * "a"}, self.organisation, plugin_id)
        with self.assertRaises(SettingsNotConformingToSchema) as ctx:
            self.service.update_by_id("LOCAL", plugin_id, self.organisation, True)

        msg = (
            f"Settings for organisation test and plugin kat_test are not conform the plugin schema: "
            f"'{value}' is too long"
        )
        self.assertEqual(ctx.exception.message, msg)

    def test_get_schema(self):
        schema = self.service.schema("kat_test")
        self.assertDictEqual(
            {
                "title": "Arguments",
                "type": "object",
                "properties": {"api_key": {"title": "Api Key", "maxLength": 128, "type": "string"}},
                "required": ["api_key"],
            },
            schema,
        )

        schema = self.service.schema("test-boefje-1")
        self.assertIsNone(schema)

    def test_removing_mandatory_setting_disables_plugin(self):
        plugin_id = "kat_test"

        self.service.settings_storage.upsert({"api_key": 128 * "a"}, self.organisation, plugin_id)
        self.service.update_by_id("test-repo-2", plugin_id, self.organisation, True)

        plugin = self.service.by_plugin_id(plugin_id, self.organisation)
        self.assertTrue(plugin.enabled)

        self.service.delete_settings(self.organisation, plugin_id)

        plugin = self.service.by_plugin_id(plugin_id, self.organisation)
        self.assertFalse(plugin.enabled)

    def test_adding_integer_settings_within_given_constraints(self):
        plugin_id = "kat_test_2"

        self.service.settings_storage.upsert({"api_key": "24"}, self.organisation, plugin_id)

        with self.assertRaises(SettingsNotConformingToSchema) as ctx:
            self.service.update_by_id("test-repo-2", plugin_id, self.organisation, True)

        self.assertIn("'24' is not of type 'integer'", ctx.exception.message)

        self.service.settings_storage.upsert({"api_key": 24}, self.organisation, plugin_id)

        self.service.update_by_id("test-repo-2", plugin_id, self.organisation, True)

        plugin = self.service.by_plugin_id(plugin_id, self.organisation)
        self.assertTrue(plugin.enabled)
        self.service.update_by_id("test-repo-2", plugin_id, self.organisation, False)

    def test_clone_one_setting(self):
        new_org_id = "org2"

        plugin_id = "kat_test"
        self.service.settings_storage.upsert({"api_key": "24"}, self.organisation, plugin_id)
        assert self.service.get_all_settings(self.organisation, plugin_id) == {"api_key": "24"}

        self.service.update_by_id(RESERVED_LOCAL_ID, plugin_id, self.organisation, True)

        self.service.update_by_id(RESERVED_LOCAL_ID, "test-boefje-1", new_org_id, True)
        self.service.update_by_id(RESERVED_LOCAL_ID, "test-boefje-2", new_org_id, True)

        assert "api_key" not in self.service.get_all_settings(new_org_id, plugin_id)

        new_org_plugins = self.service.get_all(new_org_id)
        assert len(new_org_plugins) == 8
        assert len([x for x in new_org_plugins if x.enabled]) == 6  # 4 Normalizers plus two boefjes enabled above
        assert plugin_id not in [x.id for x in new_org_plugins if x.enabled]
        assert "test-boefje-1" in [x.id for x in new_org_plugins if x.enabled]

        self.service.clone_settings_to_organisation(self.organisation, new_org_id)

        assert self.service.get_all_settings(self.organisation, plugin_id) == {"api_key": "24"}
        assert self.service.get_all_settings(new_org_id, plugin_id) == {"api_key": "24"}

        new_org_plugins = self.service.get_all(new_org_id)
        assert len(new_org_plugins) == 8
        assert len([x for x in new_org_plugins if x.enabled]) == 5
        assert plugin_id in [x.id for x in new_org_plugins if x.enabled]
        assert "test-boefje-1" not in [x.id for x in new_org_plugins if x.enabled]

    def test_clone_many_settings(self):
        plugin_id_1 = "test-boefje-1"
        plugin_id_2 = "test-boefje-2"

        all_settings_1 = {str(x): str(x + 1) for x in range(0, 8, 2)}
        all_settings_2 = {str(x): str(x + 1) for x in range(1, 9, 2)}
        self.service.upsert_settings(all_settings_1, self.organisation, plugin_id_1)
        self.service.upsert_settings(all_settings_2, self.organisation, plugin_id_2)

        self.service.clone_settings_to_organisation(self.organisation, "org2")

        all_settings_for_new_org = self.service.get_all_settings("org2", "test-boefje-1")
        assert len(all_settings_for_new_org) == 4
        assert all_settings_for_new_org == {
            "0": "1",
            "2": "3",
            "4": "5",
            "6": "7",
        }
