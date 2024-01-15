from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import Any, Dict

from django.utils.translation import gettext_lazy as _
from strenum import StrEnum

from octopoes.models import Reference
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6
from reports.report_types.definitions import Report

logger = getLogger(__name__)


class SystemType(StrEnum):
    WEB = "Web"
    MAIL = "Mail"
    DICOM = "Dicom"
    DNS = "DNS"
    OTHER = "Other"


@dataclass
class System:
    system_types: list
    oois: list


class SystemReport(Report):
    id = "systems-report"
    name = _("System Report")
    description = _("Combine IP addresses, hostnames and services into systems.")
    plugins = {"required": ["dns-records", "nmap"], "optional": ["nmap-udp"]}
    input_ooi_types = {Hostname, IPAddressV4, IPAddressV6}
    template_path = "systems_report/report.html"

    def generate_data(self, input_ooi: str, valid_time: datetime) -> Dict[str, Any]:
        reference = Reference.from_str(input_ooi)
        ips = []

        if reference.class_type == Hostname:
            ips = self.octopoes_api_connector.query(
                "Hostname.<hostname[is ResolvedHostname].address", valid_time, reference
            )
        elif reference.class_type in (IPAddressV4, IPAddressV6):
            ips = [self.octopoes_api_connector.get(reference, valid_time)]

        ip_services = {}

        service_mapping = {
            "http": SystemType.WEB,
            "http-alt": SystemType.WEB,
            "https": SystemType.WEB,
            "https-alt": SystemType.WEB,
            "domain": SystemType.DNS,
            "smtp": SystemType.MAIL,
            "smtps": SystemType.MAIL,
            "submission": SystemType.MAIL,
            "imap": SystemType.MAIL,
            "imaps": SystemType.MAIL,
            "pop3": SystemType.MAIL,
            "pop3s": SystemType.MAIL,
            "dicom": SystemType.DICOM,
            "dicom-tls": SystemType.DICOM,
            "dicom-iscl": SystemType.DICOM,
        }
        software_mapping = {
            "DICOM": SystemType.DICOM,
        }

        for ip in ips:
            ip_services[ip.reference] = {
                "hostnames": [
                    x.reference
                    for x in self.octopoes_api_connector.query(
                        "IPAddress.<address[is ResolvedHostname].hostname",
                        valid_time,
                        ip.reference,
                    )
                ],
                "services": list(
                    set(
                        [
                            service_mapping.get(str(x.name), SystemType.OTHER)
                            for x in self.octopoes_api_connector.query(
                                "IPAddress.<address[is IPPort].<ip_port [is IPService].service",
                                valid_time,
                                ip.reference,
                            )
                        ]
                    ).union(
                        set(
                            [
                                software_mapping[str(x.name)]
                                for x in self.octopoes_api_connector.query(
                                    "IPAddress.<address[is IPPort].<ooi [is SoftwareInstance].software",
                                    valid_time,
                                    ip.reference,
                                )
                                if str(x.name) in software_mapping
                            ]
                        )
                    ),
                ),
            }
            if (
                self.octopoes_api_connector.query(
                    "IPAddress.<address[is IPPort].<ip_port [is IPService].<ip_service [is Website]",
                    valid_time,
                    ip.reference,
                )
                and SystemType.WEB not in ip_services[ip.reference]["services"]
            ):
                ip_services[ip.reference]["services"].append(SystemType.WEB)

            ip_services[ip.reference]["services"].sort()

        total_systems = len(ip_services)
        total_domains = 0

        for data in ip_services.values():
            total_domains += len(data["hostnames"])

        summary = {"total_systems": total_systems, "total_domains": total_domains}

        return {"input_ooi": input_ooi, "services": ip_services, "summary": summary}
