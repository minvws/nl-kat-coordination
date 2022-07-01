from django.test import TestCase
from octopoes.models.types import (
    Hostname,
    IPAddressV6,
    IPAddressV4,
    DNSARecord,
    DNSAAAARecord,
    DNSTXTRecord,
    DNSMXRecord,
    NXDOMAIN,
    DNSNSRecord,
    DNSSOARecord,
    DNSCNAMERecord,
    DNSZone,
    Network,
)
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV6, IPAddressV4

from rocky.katalogus import Boefje, get_katalogus
from tools.models import Organization, SCAN_LEVEL


class KATalogusTestCase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            id=1, name="Development", code="_dev"
        )

        self.boefje = Boefje(
            id="dns-records",
            name="DnsRecords",
            repository_id="LOCAL",
            description="Fetch the DNS record(s) of a hostname",
            scan_level=SCAN_LEVEL.L1,
            consumes={Hostname},
            produces={
                DNSARecord,
                DNSAAAARecord,
                DNSTXTRecord,
                DNSMXRecord,
                DNSNSRecord,
                DNSSOARecord,
                DNSCNAMERecord,
                NXDOMAIN,
                Hostname,
                DNSZone,
                IPAddressV4,
                IPAddressV6,
                Network,
            },
        )

    def test_get_enabled_boefjes_v1(self):
        get_katalogus(self.organization.code).enable_boefje(self.boefje.id)
        boefjes = get_katalogus(self.organization.code).get_enabled_boefjes()
        self.assertListEqual([self.boefje], boefjes)
