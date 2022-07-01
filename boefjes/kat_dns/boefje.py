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

from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

DnsRecords = Boefje(
    id="dns-records",
    name="DnsRecords",
    description="Fetch the DNS record(s) of a hostname",
    consumes={"Hostname"},
    produces={
        "DNSARecord",
        "DNSAAAARecord",
        "DNSTXTRecord",
        "DNSMXRecord",
        "DNSNSRecord",
        "DNSSOARecord",
        "DNSCNAMERecord",
        "NXDOMAIN",
        "Hostname",
        "DNSZone",
        "IPAddressV4",
        "IPAddressV6",
        "Network",
    },
    scan_level=SCAN_LEVEL.L1,
)

BOEFJES = [DnsRecords]
NORMALIZERS = [
    Normalizer(
        name="kat_dns_normalize",
        module="kat_dns.normalize",
        consumes=[DnsRecords.id],
        produces=DnsRecords.produces,
    ),
]
