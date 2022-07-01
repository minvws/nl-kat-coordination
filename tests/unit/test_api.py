from typing import Dict
from unittest import TestCase

from fastapi.testclient import TestClient

from bytes.api import app
from tests.loading import load_stub


class APITest(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.headers = self.get_headers()

    def test_healthcheck(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "service": "bytes",
                "healthy": True,
                "version": "0.0.1-development",
                "additional": None,
                "results": [],
            },
            response.json(),
        )

    def get_headers(self) -> Dict[str, str]:
        request = load_stub("login-request.json")
        response = self.client.post("/token", data=request)
        token = response.json()["access_token"]

        return {"Authorization": f"bearer {token}"}
