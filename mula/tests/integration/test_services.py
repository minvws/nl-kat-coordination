import unittest

from scheduler import config
from scheduler.connectors import services


class BytesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.config = config.settings.Settings()
        self.service_bytes = services.Bytes(
            host=str(self.config.host_bytes),
            user=self.config.host_bytes_user,
            password=self.config.host_bytes_password,
            source="scheduler_test",
        )

    def test_login(self):
        self.service_bytes.login()
