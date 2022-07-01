from boefjes.models import Boefje, Normalizer, SCAN_LEVEL

DnsZone = Boefje(
    id="dns-zone",
    name="DnsZone",
    description="Fetch the parent DNS zone of a DNS zone",
    consumes={"DNSZone"},
    produces=["DNSSOARecord", "Hostname", "DNSZone"],
    scan_level=SCAN_LEVEL.L1,
)

BOEFJES = [DnsZone]
NORMALIZERS = [
    Normalizer(
        name="kat_dns_zone_normalize",
        module="kat_dns_zone.normalize",
        consumes=[DnsZone.id],
        produces=DnsZone.produces,
    )
]
