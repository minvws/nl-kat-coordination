import unittest

from scheduler import config
from scheduler.connectors import services
from scheduler.utils import remove_trailing_slash


class BytesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config.settings.Settings()
        self.service_bytes = services.Bytes(
            host=remove_trailing_slash(str(self.config.host_bytes)),
            user=self.config.host_bytes_user,
            password=self.config.host_bytes_password,
            source="scheduler_test",
        )

    def test_login(self):
        self.service_bytes.login()

        # TODO: check headers

    def test_login_expired_token(self):
        pass

    # TODO: do we want to mock the response here?
    def test_get_last_run_boefje(self):
        pass

    # TODO: do we want to mock the response here?
    def test_get_last_run_boefje_by_organisation_id(self):
        pass


class KatalogusTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config.settings.Settings()
        self.service_katalogus = services.Katalogus(
            host=remove_trailing_slash(str(self.config.host_katalogus)),
            source="scheduler_test",
            cache_ttl=self.config.katalogus_cache_ttl,
        )

    def test_get_organisations(self):
        orgs = self.service_katalogus.get_organisations()
        self.assertIsInstance(orgs, list)
        self.assertEqual(len(orgs), 0)
