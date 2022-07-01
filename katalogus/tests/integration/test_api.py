import os
import time
from unittest import TestCase, skipIf

import requests
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError

from config import settings
from katalogus.models import Organisation, Repository, Boefje
from katalogus.storage.interfaces import (
    OrganisationNotFound,
    PluginNotFound,
    SettingNotFound,
    RepositoryNotFound,
)
from sql.db import get_engine, SQL_BASE
from sql.organisation_storage import SQLOrganisationStorage
from sql.repository_storage import SQLRepositoryStorage
from sql.setting_storage import SQLSettingsStorage
from sql.plugin_enabled_storage import SQLPluginEnabledStorage


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
            f"{settings.katalogus_api}/v1/organisations/{self.org.id}/plugins/dns-records/"
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual("dns-records", data["id"])
        self.assertEqual("LOCAL", data["repository_id"])
