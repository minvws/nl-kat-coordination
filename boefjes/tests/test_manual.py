from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import Tuple
from unittest import TestCase

from pydantic_core import Url

from boefjes.job_models import NormalizerMeta, NormalizerOutput
from boefjes.katalogus.local_repository import LocalPluginRepository
from boefjes.local import LocalNormalizerJobRunner
from octopoes.models import Reference
from tests.test_snyk import get_dummy_data


class ManualTest(TestCase):
    TEST_DECLARATIONS_DATA = (
        b"["
        b'{"ooi": {"object_type": "Network", "scan_profile": null, "primary_key": "Network|net1", "name": "net1"}},'
        b'{"ooi": {"object_type": "Network", "scan_profile": null, "primary_key": "Network|net2", "name": "net2"}}'
        b"]"
    )
    CSV_EXAMPLES = [
        # hostname
        b"name,network\nexample.com,internet",
        # hostname without network
        b"name\nexample.net",
        # ipv4s
        b"""address,network
1.1.1.1,internet
2.2.2.2,internet
3.3.3.3,darknet""",
        # ipv6s
        b"""address,network
FE80:CD00:0000:0CDE:1257:0000:211E:729C,internet
FE80:CD00:0000:0CDE:1257:0000:211E:729D,darknet""",
        # urls
        b"""network,raw
internet,https://example.com/
darknet,https://openkat.nl/""",
        # url without network
        b"raw\nhttps://example.com/",
    ]

    def test_parse_manual_declarations(self):
        meta = NormalizerMeta.model_validate_json(get_dummy_data("manual-ooi.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")

        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, self.TEST_DECLARATIONS_DATA)

        self.assertEqual(2, len(output.declarations))
        self.assertEqual(0, len(output.observations))

        self.assertEqual(
            {"name": "net1", "object_type": "Network", "primary_key": "Network|net1", "scan_profile": None},
            output.declarations[0].ooi.dict(),
        )
        self.assertEqual(
            {"name": "net2", "object_type": "Network", "primary_key": "Network|net2", "scan_profile": None},
            output.declarations[1].ooi.dict(),
        )

    def test_parse_manual_hostname_csv(self):
        meta, output, runner = self.check_network_created(0)

        self.assertEqual(2, len(output.declarations))
        self.assertEqual(
            {
                "dns_zone": None,
                "name": "example.com",
                "network": Reference("Network|internet"),
                "object_type": "Hostname",
                "primary_key": "Hostname|internet|example.com",
                "registered_domain": None,
                "scan_profile": None,
            },
            output.declarations[1].ooi.dict(),
        )

        meta, output, runner = self.check_network_created(1)

        self.assertEqual(2, len(output.declarations))
        self.assertEqual(
            {
                "dns_zone": None,
                "name": "example.net",
                "network": Reference("Network|internet"),
                "object_type": "Hostname",
                "primary_key": "Hostname|internet|example.net",
                "registered_domain": None,
                "scan_profile": None,
            },
            output.declarations[1].ooi.dict(),
        )

    def test_parse_manual_ip_csv(self):
        meta, output, runner = self.check_network_created(2)
        self.assertEqual(6, len(output.declarations))
        self.assertEqual(
            {
                "address": IPv4Address("1.1.1.1"),
                "netblock": None,
                "network": Reference("Network|internet"),
                "object_type": "IPAddressV4",
                "primary_key": "IPAddressV4|internet|1.1.1.1",
                "scan_profile": None,
            },
            output.declarations[1].ooi.dict(),
        )

        meta, output, runner = self.check_network_created(3)
        self.assertEqual(
            {
                "address": IPv6Address("fe80:cd00:0:cde:1257:0:211e:729c"),
                "netblock": None,
                "network": Reference("Network|internet"),
                "object_type": "IPAddressV6",
                "primary_key": "IPAddressV6|internet|fe80:cd00:0:cde:1257:0:211e:729c",
                "scan_profile": None,
            },
            output.declarations[1].ooi.dict(),
        )

    def test_parse_url_csv(self):
        meta, output, runner = self.check_network_created(4)
        self.assertEqual(4, len(output.declarations))

        self.assertEqual(
            {
                "network": Reference("Network|internet"),
                "object_type": "URL",
                "primary_key": "URL|internet|https://example.com/",
                "raw": Url(
                    "https://example.com/",
                ),
                "scan_profile": None,
                "web_url": None,
            },
            output.declarations[1].ooi.model_dump(),
        )

        meta, output, runner = self.check_network_created(5)
        self.assertEqual(2, len(output.declarations))
        self.assertEqual(
            {
                "network": Reference("Network|internet"),
                "object_type": "URL",
                "primary_key": "URL|internet|https://example.com/",
                "raw": Url(
                    "https://example.com/",
                ),
                "scan_profile": None,
                "web_url": None,
            },
            output.declarations[1].ooi.dict(),
        )

    def check_network_created(self, csv_idx: int) -> Tuple[NormalizerMeta, NormalizerOutput, LocalNormalizerJobRunner]:
        meta = NormalizerMeta.model_validate_json(get_dummy_data("manual-csv.json"))
        local_repository = LocalPluginRepository(Path(__file__).parent.parent / "boefjes" / "plugins")
        runner = LocalNormalizerJobRunner(local_repository)
        output = runner.run(meta, self.CSV_EXAMPLES[csv_idx])

        self.assertEqual(0, len(output.observations))
        self.assertEqual(
            {"name": "internet", "object_type": "Network", "primary_key": "Network|internet", "scan_profile": None},
            output.declarations[0].ooi.dict(),
        )
        return meta, output, runner
