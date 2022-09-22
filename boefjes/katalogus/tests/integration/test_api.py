import os
from unittest import TestCase, skipIf

import requests

from boefjes.config import settings
from boefjes.katalogus.models import Organisation


@skipIf(os.environ.get("CI") != "1", "Needs a CI database.")
class TestAPI(TestCase):
    """This tests the API when settings.enable_db=False."""

    def setUp(self) -> None:
        self.org = Organisation(id="test", name="Test Organisation")

        response = requests.post(
            f"{settings.katalogus_api}/v1/organisations/", self.org.json()
        )
        self.assertEqual(response.status_code, 201)

    def tearDown(self) -> None:
        response = requests.delete(
            f"{settings.katalogus_api}/v1/organisations/{self.org.id}"
        )
        self.assertEqual(response.status_code, 200)

    def test_plugin_api(self):
        response = requests.get(
            f"{settings.katalogus_api}/v1/organisations/{self.org.id}/plugins/dns-records"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual("dns-records", data["id"])
        self.assertEqual("LOCAL", data["repository_id"])
