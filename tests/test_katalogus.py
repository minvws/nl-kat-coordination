from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from fastapi.testclient import TestClient

import boefjes.katalogus.api
from boefjes.config import settings
from boefjes.katalogus.api import app


class KATalogusTest(TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
        self.client = TestClient(app)

    def test_list_boefjes(self):
        response = self.client.get("/boefjes")

        self.assertEqual(200, response.status_code)
        self.assertEqual("application/json", response.headers["content-type"])
        self.assertGreater(len(response.json()), 0)

    def test_list_empty_boefjes(self):
        with patch.object(boefjes.katalogus.api, "BOEFJES_DIR", Path("non-existing")):
            response = self.client.get("/boefjes")

            self.assertEqual(200, response.status_code)
            self.assertListEqual([], response.json())

    def test_get_dns_boefje(self):
        response = self.client.get("/boefjes/dns-records")

        self.assertEqual(200, response.status_code)

        contents = response.json()
        contents["produces"] = sorted(contents["produces"])
        self.assertDictEqual(
            {
                "id": "dns-records",
                "name": "DnsRecords",
                "description": "Fetch the DNS record(s) of a hostname",
                "consumes": ["Hostname"],
                "produces": [
                    "DNSAAAARecord",
                    "DNSARecord",
                    "DNSCNAMERecord",
                    "DNSMXRecord",
                    "DNSNSRecord",
                    "DNSSOARecord",
                    "DNSTXTRecord",
                    "DNSZone",
                    "Hostname",
                    "IPAddressV4",
                    "IPAddressV6",
                    "NXDOMAIN",
                    "Network",
                ],
                "scan_level": 1,
            },
            contents,
        )

    def test_get_dns_cover(self):
        path = settings.base_dir / "plugins" / "kat_dns" / "cover.png"
        response = self.client.get("/boefjes/dns-records/cover.png")

        self.assertEqual(200, response.status_code)
        self.assertEqual(path.read_bytes(), response.content)

    def test_get_dns_description(self):
        path = settings.base_dir / "plugins" / "kat_dns" / "description.md"
        response = self.client.get("/boefjes/dns-records/description.md")

        self.assertEqual(200, response.status_code)
        self.assertEqual(path.read_bytes(), response.content)
