import json
import logging
from collections.abc import Iterable
from ipaddress import ip_address

from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.records import DNSAAAARecord, DNSARecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import Network


def run(input_ooi: dict, raw: bytes) -> Iterable[OOI]:
    """Normalize AbuseIPDB output."""
    result = json.loads(raw)
    input_ooi_reference = Reference.from_str(input_ooi["primary_key"])
    address = input_ooi_reference.tokenized.address

    internet = Network(name="internet")

    if not result:
        logging.info("No AbuseIPDB results available for normalization.")
    elif "data" in result:
        data = result["data"]
        reportcount = int(data.get("totalReports", 0))
        if reportcount > 0:
            confidence = str(data.get("abuseConfidenceScore", "Unknown"))
            reportdate = str(data.get("lastReportedAt", "Unknown"))
            ft = KATFindingType("KAT-ABUSE-REPORTS-DETECTED")
            finding = Finding(
                finding_type=ft.reference,
                ooi=input_ooi_reference,
                description=(
                    f"IP {input_ooi_reference.human_readable} is listed {reportcount} times "
                    f"for abuse at AbuseIPDB.com, last reported at: {reportdate} with a "
                    f"confidence of: {confidence}."
                ),
            )
            yield ft
            yield finding
        # should we add these? Its not relevant unless there's security risks involved in shared hosting
        related_hostnames = data.get("hostnames", False)
        if related_hostnames:
            for hostname in related_hostnames:
                hostname_ooi = Hostname(network=internet.reference, name=hostname.rstrip("."))
                default_args = {"hostname": hostname_ooi.reference}
                # should we add these? We did not 'observe' them
                if ip_address(address).version == 4:
                    yield DNSARecord(address=input_ooi_reference, **default_args)
                else:
                    yield DNSAAAARecord(address=input_ooi_reference, **default_args)
