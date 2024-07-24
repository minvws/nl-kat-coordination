import json
from collections.abc import Iterable

from boefjes.job_models import NormalizerOutput
from octopoes.models import Reference
from octopoes.models.ooi.findings import CVEFindingType, Finding
from octopoes.models.ooi.software import Software, SoftwareInstance
from packaging.version import Version

cves = {
    "bind": {
        "CVE-2024-0760": "A flood of DNS messages over TCP may make the server unstable https://kb.isc.org/docs/cve-2024-0760",
        "CVE-2024-1737": "BIND's database will be slow if a very large number of RRs exist at the same name https://kb.isc.org/docs/cve-2024-1737",
        "CVE-2024-1975": "SIG(0) can be used to exhaust CPU resources https://kb.isc.org/docs/cve-2024-1975",
        "CVE-2024-4076": "Assertion failure when serving both stale cache data and authoritative zone content https://kb.isc.org/docs/cve-2024-4076",
    }
}


def run(input_ooi: dict, raw: bytes) -> Iterable[NormalizerOutput]:
    input_ooi_reference = Reference.from_str(input_ooi["primary_key"])
    input_ip = input_ooi["address"]["address"]
    input_port = input_ooi["port"]

    results = json.loads(raw)
    for version in results:
        name = None
        versionnumber = None

        if version.startswith("bind"):
            name = "bind"
            versionnumber = version.split("-")[1]
        if version.startswith("9."):
            name = "bind"
            versionnumber = version
        elif version.startswith("Microsoft DNS"):
            name = "Microsoft DNS"
            versionnumber = version.replace("Microsoft DNS ", "").split(" ")[0]
        elif version.startswith("dnsmasq"):
            name = "dnsmasq"
            versionnumber = version.split("-")[1]
        elif version.startswith("PowerDNS"):
            name = "PowerDNS"
            versionnumber = version.replace("PowerDNS Authoritative Server ", "").split(" ")[0]

        if name and versionnumber:
            software = Software(name=name, version=versionnumber)
            software_instance = SoftwareInstance(ooi=input_ooi_reference, software=software.reference)
            yield from [software, software_instance]

        # TODO move this to a generic boefje that enriches SoftwareOOIs
        if name == "bind" and is_vulnerable(versionnumber.lower()):
            for cveid, description in cves.items():
                # Create instances of CVEFindingType and Finding classes
                cve_finding_type = CVEFindingType(id=cveid)
                yield cve_finding_type

                finding = Finding(
                    finding_type=cve_finding_type.reference,
                    ooi=input_ooi_reference,
                    proof=None,
                    description=description,
                    reproduce=f"dig -t TXT -c chaos VERSION.BIND @{input_ip} -p {input_port}",
                )
                yield finding


def is_vulnerable(versionnumber: str) -> bool:
    """Attempts to parse the version string and match against known broken versions

    # examples

    9.11.4-P2-RedHat-9.11.4-26.P2.el7_9.9
    9.11.36-RedHat-9.11.36-8.el8_8.2
    9.8.2rc1-RedHat-9.8.2-0.68.rc1.el6_10.3

    9.11.5-P4-5.1+deb10u2-Debian

    9.10.3-P4-Ubuntu
    9.18.18-0ubuntu0.22.04.2-Ubuntu
    """

    # maybe use https://github.com/ihiji/version_utils ?
    broken = "9.18.27"

    # simple match if not annotated by vendor
    if len(versionnumber) == 7 and Version(versionnumber) >= Version(broken):
        return False

    if "redhat" in versionnumber:
        version, security_update = versionnumber.split("-redhat-")
        security_update = security_update.split(".el")[0].replace(version + "-", "")

        if Version(security_update) >= Version("1.1"):
            return False

    if "ubuntu" in versionnumber:
        version, security_update, _ = versionnumber.split("-")
        if Version(security_update) >= Version("1"):
            return False

    if "debian" in versionnumber:
        version, security_update = versionnumber.split("deb10u")
        security_update = security_update.split("-")[0]
        if Version(security_update) >= Version("1"):
            return False

    return True
