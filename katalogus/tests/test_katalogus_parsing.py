from django.test import SimpleTestCase
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from katalogus.client import _parse_boefje_v1


class KATalogusTestCase(SimpleTestCase):
    def test_get_enabled_boefjes(self):
        api_boefje = {
            "id": "binaryedge",
            "name": "BinaryEdge",
            "repository_id": "LOCAL",
            "version": None,
            "authors": None,
            "created": None,
            "description": "Use BinaryEdge to find open ports with vulnerabilities that are found on that port",
            "environment_keys": None,
            "related": None,
            "type": "boefje",
            "scan_level": 2,
            "consumes": ["IPAddressV4", "IPAddressV6"],
            "options": None,
            "produces": [
                "Software",
                "KATFindingType",
                "Service",
                "SoftwareInstance",
                "CVEFindingType",
                "IPService",
                "IPPort",
                "Finding",
            ],
            "enabled": True,
        }

        boefje = _parse_boefje_v1(api_boefje)

        self.assertSetEqual({IPAddressV4, IPAddressV6}, boefje.consumes)
        self.assertEqual("binaryedge", boefje.id)
