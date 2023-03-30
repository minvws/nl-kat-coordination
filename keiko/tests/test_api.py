from pathlib import Path
from unittest import TestCase

from fastapi.testclient import TestClient

from tempfile import gettempdir
from keiko.api import construct_api
from keiko.settings import Settings


class APITest(TestCase):
    maxDiff = None

    def setUp(self) -> None:
        settings = Settings(
            templates_folder=str(Path(__file__).parent / "fixtures" / "templates"), reports_folder=str(gettempdir())
        )

        self.api = construct_api(settings)
        self.client = TestClient(self.api)

    def test_health(self):
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertDictEqual(
            {
                "service": "keiko",
                "healthy": True,
                "version": "0.0.1.dev1",
                "additional": None,
                "results": [],
            },
            response.json(),
        )

    def test_templates(self):
        response = self.client.get("/templates")

        self.assertEqual(200, response.status_code)
        self.assertListEqual(["template1", "template2"], sorted(response.json()))
