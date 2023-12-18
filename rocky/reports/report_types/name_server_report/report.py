from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from typing import Any, Dict, List

from django.utils.translation import gettext_lazy as _

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.findings import RiskLevelSeverity
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


@dataclass
class NameServerCheck:
    no_uncommon_ports: bool = False
    has_dnssec: bool = False
    has_valid_dnssec: bool = False

    def __bool__(self):
        return (
            self.no_uncommon_ports
            and self.has_dnssec
            and self.has_valid_dnssec
        )

@dataclass
class NameServerChecks:
    checks: List[NameServerCheck] = field(default_factory=list)

    @property
    def no_uncommon_ports(self):
        return sum([check.no_uncommon_ports for check in self.checks])

    @property
    def has_dnssec(self):
        return sum([check.has_dnssec for check in self.checks])

    @property
    def has_valid_dnssec(self):
        return sum([check.has_valid_dnssec for check in self.checks])

    def __bool__(self):
        return all(bool(check) for check in self.checks)

    def __len__(self):
        return len(self.checks)

    def __add__(self, other: "NameServerChecks"):
        return NameServerChecks(checks=self.checks + other.checks)


class NameServerSystemReport(Report):
    id = "name-server-report"
    name = _("Name server Report")
    description = _("Name server report checks name servers on basic security standards.")
    plugins = {
        "required": [
            "nmap",
            "dns-records",
            "dns-sec",
        ],
        "optional": [],
    }
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "name_server_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        hostnames = []

        if reference.class_type == Hostname:
            hostnames = [self.octopoes_api_connector.get(reference)]

        elif reference.class_type in (IPAddressV4, IPAddressV6):
            hostnames = self.octopoes_api_connector.query(
                "IPAddress.<address[is ResolvedHostname].hostname", valid_time, reference
            )

        name_server_checks = NameServerChecks()
        finding_types = {}

        for hostname in hostnames:
            check = NameServerCheck()

            port_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<hostname[is ResolvedHostname].address.<address[is IPPort].<ooi[is Finding].finding_type",
                    valid_time,
                    hostname.reference,
                )
                if x.id in ["KAT-UNCOMMON-OPEN-PORT", "KAT-OPEN-SYSADMIN-PORT", "KAT-OPEN-DATABASE-PORT"]
            ]
            check.no_uncommon_ports = not any(port_finding_types)

            hostname_finding_types = [
                x
                for x in self.octopoes_api_connector.query(
                    "Hostname.<ooi[is Finding].finding_type", valid_time, hostname.reference
                )
                if x.id in ["KAT-NO-DNSSEC", "KAT-INVALID-DNSSEC"]
            ]
            check.has_dnssec = "KAT-NO-DNSSEC" not in [x.id for x in hostname_finding_types]
            check.has_valid_dnssec = check.has_dnssec and "KAT-INVALID-DNSSEC" not in [
                x.id for x in hostname_finding_types
            ]

            name_server_checks.checks.append(check)

            for finding_type in port_finding_types + hostname_finding_types:
                if finding_type.risk_severity in [None, RiskLevelSeverity.PENDING] or not finding_type.description:
                    continue

                finding_types[finding_type.id] = finding_type

        return {
            "input_ooi": input_ooi,
            "name_server_checks": name_server_checks,
            "finding_types": sorted(finding_types.values(), reverse=True, key=lambda x: x.risk_severity),
        }
