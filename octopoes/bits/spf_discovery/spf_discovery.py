from collections.abc import Iterator

from bits.spf_discovery.internetnl_spf_parser import parse
from octopoes.models import OOI
from octopoes.models.ooi.dns.records import DNSTXTRecord
from octopoes.models.ooi.dns.zone import Hostname
from octopoes.models.ooi.email_security import DNSSPFMechanismHostname, DNSSPFMechanismIP, DNSSPFRecord
from octopoes.models.ooi.findings import Finding, KATFindingType
from octopoes.models.ooi.network import IPAddressV4, IPAddressV6, Network


def run(input_ooi: DNSTXTRecord, additional_oois, config: dict[str, str]) -> Iterator[OOI]:
    if input_ooi.value.startswith("v=spf1"):
        spf_value = input_ooi.value.replace("%(d)", input_ooi.hostname.tokenized.name)
        parsed = parse(spf_value)
        # check if spf record passes the internet.nl parser
        if parsed is not None:
            spf_record = DNSSPFRecord(dns_txt_record=input_ooi.reference, value=input_ooi.value, ttl=input_ooi.ttl)
            # walk through all mechanisms
            for mechanism in parsed[1]:
                # ip4 and ip6 mechanisms
                if mechanism.startswith(("ip4:", "ip6:")):
                    yield from parse_ip_qualifiers(mechanism, input_ooi, spf_record)
                # a mechanisms and mx mechanisms have the same syntax
                if mechanism.startswith("a") or mechanism.startswith("mx"):
                    yield from parse_a_mx_qualifiers(mechanism, input_ooi, spf_record)
                # exists ptr and include mechanisms have a similar syntax
                if (
                    mechanism.startswith("exists")
                    or mechanism.startswith("ptr")
                    or mechanism.startswith("include")
                    or mechanism.startswith("?include")
                ):
                    yield from parse_ptr_exists_include_mechanism(mechanism, input_ooi, spf_record)
                # redirect mechanisms
                if mechanism.startswith("redirect"):
                    yield from parse_redirect_mechanism(mechanism, input_ooi, spf_record)
                # exp mechanism is handled separately because does not necessarily have a hostname
                if mechanism.startswith("exp"):
                    spf_record.exp = mechanism.split("=", 1)[1]
                if mechanism.endswith("all"):
                    spf_record.all = mechanism.strip("all")
            yield spf_record
        else:
            ft = KATFindingType(id="KAT-INVALID-SPF")
            yield ft
            yield Finding(finding_type=ft.reference, ooi=input_ooi.reference, description="This SPF record is invalid")


def parse_ip_qualifiers(mechanism: str, input_ooi: DNSTXTRecord, spf_record: DNSSPFRecord) -> Iterator[str]:
    # split mechanism into qualifier and ip
    qualifier, ip = mechanism.split(":", 1)
    ip = mechanism[4:]
    # split ip in ip and mask
    mask = None
    if "/" in ip:
        ip, mask = ip.split("/")
    if mask is None:
        if qualifier == "ip4":
            ip_address = IPAddressV4(
                address=ip, network=Network(name=input_ooi.hostname.tokenized.network.name).reference
            )
            yield ip_address
            yield DNSSPFMechanismIP(spf_record=spf_record.reference, ip=ip_address.reference, mechanism="ip4")
        if qualifier == "ip6":
            ip_address = IPAddressV6(
                address=ip, network=Network(name=input_ooi.hostname.tokenized.network.name).reference
            )
            yield ip_address
            yield DNSSPFMechanismIP(
                spf_record=spf_record.reference, ip=ip_address.reference, qualifier=qualifier, mechanism="ip6"
            )


def parse_a_mx_qualifiers(mechanism: str, input_ooi: DNSTXTRecord, spf_record: DNSSPFRecord) -> Iterator[str]:
    if mechanism == "a" or mechanism == "mx":
        yield DNSSPFMechanismHostname(spf_record=spf_record.reference, hostname=input_ooi.hostname, mechanism=mechanism)
    else:
        mechanism_type, domain = mechanism.split(":", 1)
        # remove prefix-length for now
        # TODO: fix prefix lengths
        domain = domain.split("/")[0]
        hostname = Hostname(name=domain, network=Network(name=input_ooi.hostname.tokenized.network.name).reference)
        yield hostname
        yield DNSSPFMechanismHostname(
            spf_record=spf_record.reference, hostname=hostname.reference, mechanism=mechanism_type
        )
    if mechanism.startswith("a/") or mechanism.startswith("mx/"):
        mechanism_type, domain = mechanism.split("/", 1)[1]
        # TODO: fix prefix lengths
        domain = domain.split("/")[0]
        hostname = Hostname(name=domain, network=Network(name=input_ooi.hostname.tokenized.network.name).reference)
        yield hostname
        yield DNSSPFMechanismHostname(
            spf_record=spf_record.reference, hostname=hostname.reference, mechanism=mechanism_type
        )


def parse_ptr_exists_include_mechanism(
    mechanism: str, input_ooi: DNSTXTRecord, spf_record: DNSSPFRecord
) -> Iterator[str]:
    if mechanism == "ptr":
        yield DNSSPFMechanismHostname(spf_record=spf_record.reference, hostname=input_ooi.hostname, mechanism="ptr")
    else:
        mechanism_type, domain = mechanism.split(":", 1)
        # currently, the model only supports hostnames and not domains
        if domain.startswith("_"):
            return
        hostname = Hostname(name=domain, network=Network(name=input_ooi.hostname.tokenized.network.name).reference)
        yield hostname
        yield DNSSPFMechanismHostname(
            spf_record=spf_record.reference, hostname=hostname.reference, mechanism=mechanism_type
        )


def parse_redirect_mechanism(mechanism: str, input_ooi: DNSTXTRecord, spf_record: DNSSPFRecord) -> Iterator[str]:
    mechanism_type, domain = mechanism.split("=", 1)
    # currently, the model only supports hostnames and not domains
    if domain.startswith("_"):
        return
    hostname = Hostname(name=domain, network=Network(name=input_ooi.hostname.tokenized.network.name).reference)
    yield hostname
    yield DNSSPFMechanismHostname(
        spf_record=spf_record.reference, hostname=hostname.reference, mechanism=mechanism_type
    )
