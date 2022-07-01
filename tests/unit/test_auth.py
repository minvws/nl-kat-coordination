from unittest import TestCase

import datetime
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from bytes.api import app
from tests.loading import load_stub

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjotMzA1ODU4NTkyMDB9.ctXLBIXt6ewa8VsSiySXOfzIdPWjAl1O_gvzz0vHQ_s"


class APITest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("bytes.auth._get_expire_time")
    def test_login_get_token(self, get_expire_time_mock: MagicMock) -> None:
        get_expire_time_mock.return_value = datetime.datetime(1000, 10, 10)
        request = load_stub("login-request.json")

        response = self.client.post("/token", data=request)

        self.assertEqual(200, response.status_code)

        data = response.json()
        self.assertEqual("bearer", data["token_type"])
        self.assertEqual(ACCESS_TOKEN, data["access_token"])
        self.assertEqual("1000-10-10T00:00:00", data["expires_at"])

    def test_login_get_token_not_authorized(self) -> None:
        request = load_stub("login-request.json")
        request["username"] = "nivlac"

        response = self.client.post("/token", data=request)
        self.assertEqual(401, response.status_code)
