from unittest import TestCase

from boefjes.config import BASE_DIR
from boefjes.katalogus.dependencies.plugins import PluginService
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.katalogus.storage.interfaces import SettingsNotConformingToSchema
from boefjes.katalogus.storage.memory import PluginStatesStorageMemory, SettingsStorageMemory


def mock_plugin_service(organisation_id: str) -> PluginService:
    storage = SettingsStorageMemory()
    storage.upsert({"DUMMY_VAR": "123"}, "test", "test_plugin")

    test_boefjes_dir = BASE_DIR / "katalogus" / "tests" / "boefjes_test_dir"

    return PluginService(
        PluginStatesStorageMemory(organisation_id),
        storage,
        LocalPluginRepository(test_boefjes_dir),
    )


class TestPluginsService(TestCase):
    def setUp(self) -> None:
        self.organisation = "test"
        self.service = mock_plugin_service(self.organisation)

    def test_get_plugins(self):
        plugins = self.service.get_all(self.organisation)

        self.assertEqual(len(plugins), 5)

        kat_test = list(filter(lambda x: x.id == "kat_test", plugins)).pop()
        self.assertEqual("kat_test", kat_test.id)
        self.assertEqual("Kat test name", kat_test.name)
        self.assertEqual({"DNSZone"}, kat_test.consumes)
        self.assertSetEqual({"boefje/kat_test"}, set(kat_test.produces))

        kat_test_norm = list(filter(lambda x: x.id == "kat_test_normalize", plugins)).pop()
        self.assertIn("kat_test_normalize", kat_test_norm.id)
        self.assertListEqual(["text/html", "normalizer/kat_test_normalize"], kat_test_norm.consumes)
        self.assertListEqual([], kat_test_norm.produces)

    def test_get_plugin_by_id(self):
        plugin = self.service.by_plugin_id("kat_test_normalize", self.organisation)

        self.assertEqual(plugin.id, "kat_test_normalize")
        self.assertTrue(plugin.enabled)

    def test_update_by_id(self):
        self.service.update_by_id("kat_test_normalize", self.organisation, False)
        plugin = self.service.by_plugin_id("kat_test_normalize", self.organisation)
        self.assertFalse(plugin.enabled)

    def test_update_by_id_bad_schema(self):
        plugin_id = "kat_test"

        with self.assertRaises(SettingsNotConformingToSchema) as ctx:
            self.service.update_by_id(plugin_id, self.organisation, True)

        msg = (
            "Settings for organisation test and plugin kat_test are not conform the plugin schema: 'api_key' is a "
            "required property"
        )
        self.assertEqual(ctx.exception.message, msg)

        self.service.settings_storage.upsert({"api_key": 128 * "a"}, self.organisation, plugin_id)
        self.service.update_by_id(plugin_id, self.organisation, True)

        value = 129 * "a"
        self.service.settings_storage.upsert({"api_key": 129 * "a"}, self.organisation, plugin_id)
        with self.assertRaises(SettingsNotConformingToSchema) as ctx:
            self.service.update_by_id(plugin_id, self.organisation, True)

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

        schema = self.service.schema("kat_test_normalize")
        self.assertIsNone(schema)

    def test_removing_mandatory_setting_disables_plugin(self):
        plugin_id = "kat_test"

        self.service.settings_storage.upsert({"api_key": 128 * "a"}, self.organisation, plugin_id)
        self.service.update_by_id(plugin_id, self.organisation, True)

        plugin = self.service.by_plugin_id(plugin_id, self.organisation)
        self.assertTrue(plugin.enabled)

        self.service.delete_settings(self.organisation, plugin_id)

        plugin = self.service.by_plugin_id(plugin_id, self.organisation)
        self.assertFalse(plugin.enabled)

    def test_adding_integer_settings_within_given_constraints(self):
        plugin_id = "kat_test_2"

        self.service.settings_storage.upsert({"api_key": "24"}, self.organisation, plugin_id)

        with self.assertRaises(SettingsNotConformingToSchema) as ctx:
            self.service.update_by_id(plugin_id, self.organisation, True)

        self.assertIn("'24' is not of type 'integer'", ctx.exception.message)

        self.service.settings_storage.upsert({"api_key": 24}, self.organisation, plugin_id)

        self.service.update_by_id(plugin_id, self.organisation, True)

        plugin = self.service.by_plugin_id(plugin_id, self.organisation)
        self.assertTrue(plugin.enabled)
        self.service.update_by_id(plugin_id, self.organisation, False)

    def test_clone_one_setting(self):
        new_org_id = "org2"
        plugin_id = "kat_test"
        self.service.settings_storage.upsert({"api_key": "24"}, self.organisation, plugin_id)
        assert self.service.get_all_settings(self.organisation, plugin_id) == {"api_key": "24"}

        self.service.update_by_id(plugin_id, self.organisation, True)
        self.service.update_by_id("kat_test_normalize", new_org_id, True)

        assert "api_key" not in self.service.get_all_settings(new_org_id, plugin_id)

        new_org_plugins = self.service.get_all(new_org_id)
        assert len(new_org_plugins) == 5
        assert len([x for x in new_org_plugins if x.enabled]) == 2  # 4 Normalizers plus two boefjes enabled above
        assert plugin_id not in [x.id for x in new_org_plugins if x.enabled]

        self.service.clone_settings_to_organisation(self.organisation, new_org_id)

        assert self.service.get_all_settings(self.organisation, plugin_id) == {"api_key": "24"}
        assert self.service.get_all_settings(new_org_id, plugin_id) == {"api_key": "24"}

        new_org_plugins = self.service.get_all(new_org_id)
        assert len(new_org_plugins) == 5
        assert len([x for x in new_org_plugins if x.enabled]) == 2
        assert plugin_id in [x.id for x in new_org_plugins if x.enabled]

    def test_clone_many_settings(self):
        plugin_id_1 = "kat_test"

        all_settings_1 = {"api_key": "123"}
        self.service.upsert_settings(all_settings_1, self.organisation, plugin_id_1)

        self.service.clone_settings_to_organisation(self.organisation, "org2")

        all_settings_for_new_org = self.service.get_all_settings("org2", plugin_id_1)
        assert len(all_settings_for_new_org) == 1
        assert all_settings_for_new_org == {"api_key": "123"}
