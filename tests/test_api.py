from unittest import TestCase

import requests
import requests_mock
from fastapi.testclient import TestClient

from octopoes.api.api import app
from octopoes.api.router import xtdb_client
from octopoes.xtdb.client import XTDBHTTPClient


class APITest(TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.client = TestClient(app)
        app.dependency_overrides[xtdb_client] = lambda: XTDBHTTPClient("http://localhost:3000/_crux")

    def tearDown(self) -> None:
        app.dependency_overrides = {}

    @requests_mock.Mocker(real_http=True)
    def test_health(self, mocker) -> None:

        crux_status = {
            "version": "21.05-1.17.0-beta",
            "revision": None,
            "indexVersion": 18,
            "consumerState": None,
            "kvStore": "crux.mem_kv.MemKv",
            "estimateNumKeys": 25,
            "size": None,
        }

        mocker.get("http://localhost:3000/_crux/status", json=crux_status, status_code=200)

        response = self.client.get("/_dev/health")

        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "service": "octopoes",
                "healthy": True,
                "version": "0.0.1-development",
                "additional": None,
                "results": [
                    {
                        "healthy": True,
                        "service": "xtdb",
                        "version": "21.05-1.17.0-beta",
                        "additional": crux_status,
                        "results": [],
                    },
                ],
            },
            response.json(),
        )

    @requests_mock.Mocker(real_http=True)
    def test_health_no_crux_connection(self, mocker) -> None:

        mocker.get("http://localhost:3000/_crux/status", exc=requests.exceptions.ConnectTimeout)

        response = self.client.get("/_dev/health")

        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "service": "octopoes",
                "healthy": False,
                "version": "0.0.1-development",
                "additional": None,
                "results": [
                    {
                        "healthy": False,
                        "service": "xtdb",
                        "version": None,
                        "additional": "Cannot connect to XTDB at. Service possibly down",
                        "results": [],
                    },
                ],
            },
            response.json(),
        )

    def test_openapi_schema(self) -> None:
        response = self.client.get("/openapi.json")

        self.assertEqual(200, response.status_code)
