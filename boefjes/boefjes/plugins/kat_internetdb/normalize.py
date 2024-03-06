import json
import logging
from collections.abc import Iterable

from boefjes.job_models import NormalizerMeta
from octopoes.models import OOI, Reference
from octopoes.models.ooi.dns.records import DNSPTRRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import CVEFindingType, Finding
from octopoes.models.ooi.network import IPPort, Network, PortState
from octopoes.models.ooi.software import Software, SoftwareInstance

DNS_PTR_STR = ".in-addr.arpa"


def cpe_to_name_version(cpe: str) -> tuple:
    """Fetch the software name and version from a CPE string."""
    cpe_split = cpe.split(":")
    cpe_split_len = len(cpe_split)
    name = None if cpe_split_len < 4 else cpe_split[3]
    version = None if cpe_split_len < 5 else cpe_split[4]
    return name, version


def run(normalizer_meta: NormalizerMeta, raw: bytes | str) -> Iterable[OOI]:
    """Normalize InternetDB output."""
    result = json.loads(raw)
    input_ = normalizer_meta.raw_data.boefje_meta.arguments["input"]
    input_ooi_reference = Reference.from_str(normalizer_meta.raw_data.boefje_meta.input_ooi)
    input_ooi_str = input_["address"]

    if not result:
        logging.info("No InternetDB results available for normalization.")
    elif "detail" in result:
        if result["detail"] == "No information available":
            logging.info("No information available for IP.")
        else:
            logging.warning("Unexpected detail: %s", str(result["detail"]))
    else:
        if result["ip"] != input_ooi_str:
            logging.warning("Returned IP different from input OOI.")
            logging.debug("Result IP: %s, Input IP: %s)", result["ip"], input_ooi_str)
        for hostname in result["hostnames"]:
            if hostname.endswith(DNS_PTR_STR):
                # Some parsing necessary to find the normal IP, could enrich DNSPTRRecord.
                # reverse_ip = hostname.replace(DNS_PTR_STR, "") # noqa: ERA001
                yield DNSPTRRecord(hostname=hostname, value=hostname, address=None)
            else:
                yield Hostname(name=hostname, network=Network(name=input_["network"]["name"]).reference)

        for port in result["ports"]:
            yield IPPort(address=input_ooi_reference, port=int(port), state=PortState("open"))

        for cve in result["vulns"]:
            source_url = f"https://internetdb.shodan.io/{input_ooi_str}"
            finding_type = CVEFindingType(id=cve, source=source_url)
            finding = Finding(
                finding_type=finding_type.reference,
                ooi=input_ooi_reference,
                proof=source_url,
            )
            yield finding_type
            yield finding

        for cpe in result["cpes"]:
            name, version = cpe_to_name_version(cpe=cpe)
            software = Software(name=name, version=version, cpe=cpe)
            yield software
            yield SoftwareInstance(software=software.reference, ooi=input_ooi_reference)
