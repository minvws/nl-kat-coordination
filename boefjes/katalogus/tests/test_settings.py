import base64
from unittest import TestCase

from fastapi.testclient import TestClient
from nacl.public import PrivateKey

from boefjes.katalogus.api import app
from boefjes.katalogus.dependencies.encryption import (
    IdentityMiddleware,
    NaclBoxMiddleware,
)
from boefjes.katalogus.dependencies.organisations import get_organisations_store
from boefjes.katalogus.dependencies.settings import (
    SettingsService,
    get_settings_service,
)
from boefjes.katalogus.models import Organisation, Base64Str
from boefjes.katalogus.storage.memory import (
    OrganisationStorageMemory,
    SettingsStorageMemory,
)


class TestSettings(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.storage = SettingsStorageMemory("test")
        self.storage.create("DUMMY_VAR", "123", "test", "test_plugin")

        def _mocked_get_settings_service(organisation_id: str):
            return SettingsService(
                storage=self.storage,
                encryption=IdentityMiddleware(),
            )

        self._store = OrganisationStorageMemory(
            {"test": Organisation(id="test", name="Test")}
        )
        app.dependency_overrides[get_organisations_store] = lambda: self._store
        app.dependency_overrides[get_settings_service] = _mocked_get_settings_service

    def tearDown(self) -> None:
        self.storage._data = {}

    def test_list(self):
        res = self.client.get("/v1/organisations/test/test_plugin/settings")
        self.assertEqual(200, res.status_code)
        self.assertDictEqual({"DUMMY_VAR": "123"}, res.json())

    def test_get_key(self):
        res = self.client.get("/v1/organisations/test/test_plugin/settings/DUMMY_VAR")
        self.assertEqual(200, res.status_code)
        self.assertEqual("123", res.json())

    def test_get_key_non_existing(self):
        res = self.client.get("/v1/organisations/test/test_plugin/settings/FUTURE_VAR")
        self.assertEqual(404, res.status_code)

    def test_add_key(self):
        res = self.client.post(
            "/v1/organisations/test/test_plugin/settings/NEW_VAR",
            json={"value": "new value"},
        )
        self.assertEqual(201, res.status_code)

        res = self.client.get("/v1/organisations/test/test_plugin/settings")
        self.assertEqual(200, res.status_code)
        self.assertListEqual(["DUMMY_VAR", "NEW_VAR"], list(res.json().keys()))
        self.assertListEqual(["123", "new value"], list(res.json().values()))

    def test_delete_key(self):
        res = self.client.delete(
            "/v1/organisations/test/test_plugin/settings/DUMMY_VAR"
        )
        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/test/test_plugin/settings")
        self.assertEqual(200, res.status_code)
        self.assertDictEqual({}, res.json())

    def test_update_key(self):
        res = self.client.put(
            "/v1/organisations/test/test_plugin/settings/DUMMY_VAR",
            json={"value": "new value"},
        )
        self.assertEqual(200, res.status_code)

        res = self.client.get("/v1/organisations/test/test_plugin/settings/DUMMY_VAR")
        self.assertEqual(200, res.status_code)
        self.assertEqual("new value", res.json())


class TestSettingsEncryption(TestCase):
    def setUp(self) -> None:
        sk = PrivateKey.generate()
        sk_b64 = base64.b64encode(bytes(sk)).decode()
        pub_b64 = base64.b64encode(bytes(sk.public_key)).decode()
        self.encryption = NaclBoxMiddleware(
            private_key=Base64Str(sk_b64), public_key=Base64Str(pub_b64)
        )

    def test_encode_decode(self):
        msg = "The president is taking the underpass"

        encrypted = self.encryption.encode(msg)
        decrypted = self.encryption.decode(encrypted)

        self.assertNotEqual(encrypted, msg)
        self.assertEqual(msg, decrypted)
